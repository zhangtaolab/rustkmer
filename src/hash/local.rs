//! Per-worker thread-local k-mer accumulation for the counting hot path.
//!
//! **PAR-02 (Phase 6, plan 06-02).** The Phase 5 contention evidence
//! (`contention_evidence.json`) attributes 120.22 ns per window — about 115 %
//! of the measured shared-versus-local gap — to the per-window `total_kmers` /
//! `unique_kmers` `fetch_add`s inside [`KmerCounter::increment`]. The fix is to
//! stop touching shared state per window: every rayon worker accumulates into
//! its own [`LocalKmerCounts`] table, and the shared `DashMap` is updated once
//! per file by a checked end-of-file reduction
//! ([`KmerCounter::merge_local_counts`] / [`KmerCounter::reduce_local_counts`]).
//!
//! # Exactness contract
//!
//! A local accumulator reproduces [`KmerCounter::increment`]'s per-key
//! semantics **exactly**:
//!
//! - a count already at [`u32::MAX`] is an overflow that returns the verbatim
//!   contract error (`K-mer count overflow reached maximum value <max>`);
//! - a successful increment advances the local total by one; a failed one does
//!   not (the WR-03 rule, carried over);
//! - a fresh key advances the local unique count by one.
//!
//! The reduction is a **new summation site**, so it uses `checked_add` for the
//! per-key `u32` sum and never wraps or saturates. The shared total is also
//! accumulated with checked `u64` arithmetic.
//!
//! # Thread-local handle registry
//!
//! [`LocalHandleRegistry`] is owned by one [`KmerCounter`] and hands each rayon
//! worker the *same* [`LocalKmerCounts`] for the lifetime of a "generation".
//! [`LocalHandleRegistry::drain`] takes every registered local and bumps the
//! generation; the next [`LocalHandleRegistry::handle`] call on a worker
//! creates a fresh local. That is what makes a multi-file CLI run exact: a
//! local drained for file 1 can never be reused (and double-counted) on file 2.
//!
//! The fast path is lock-free: a TLS lookup keyed by the counter's unique id
//! compares a cached generation against an atomic. Only a miss (first use on a
//! worker, or first use after a reduction) takes the registry mutex and
//! allocates.

use std::cell::RefCell;
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, MutexGuard};

use crate::error::{ProcessingError, ProcessingResult};
use crate::kmer::encoding::MAX_KMER_SIZE_IN_U64;

/// Per-worker preallocation hint for the dense/wide local table.
///
/// Deliberately small: every rayon worker gets its own table, so mirroring the
/// shared table's `-s` capacity per worker would multiply memory by the worker
/// count. The table grows on demand; the end-of-file reduction releases it.
const LOCAL_INITIAL_CAPACITY: usize = 8192;

/// Next unique counter id handed to a [`LocalHandleRegistry`].
static NEXT_COUNTER_ID: AtomicU64 = AtomicU64::new(1);

/// One worker's cached handle for a counter: `(generation, local accumulator)`.
type WorkerLocalHandle = (u64, Arc<Mutex<LocalKmerCounts>>);

/// The thread-local cache: counter id -> that counter's per-worker handle.
type WorkerLocalMap = HashMap<u64, WorkerLocalHandle>;

// Thread-local map: counter id -> (generation, this worker's local).
//
// The key is the counter's unique id rather than its address because a
// dropped counter's address can be reused; the id never repeats.
thread_local! {
    static WORKER_LOCALS: RefCell<WorkerLocalMap> = RefCell::new(WorkerLocalMap::new());
}

/// A single worker's private k-mer count table.
///
/// The storage width mirrors [`crate::hash::table::KmerCounter`]: a plain
/// `hashbrown` dense map keyed by `u64` for `k <= 32`, and a wide map keyed by
/// `u128` for `33..=64`. Using `hashbrown`'s default (AHash) builder matters:
/// this is the hot path, and the map stays cache-resident per worker.
#[derive(Debug)]
pub struct LocalKmerCounts {
    /// Width-selected accumulation table (no locking — the value is private to
    /// one worker and only reachable through a `Mutex<LocalKmerCounts>`).
    table: LocalTable,
    /// Successful increments only (WR-03 semantics).
    total_kmers: u64,
    /// Distinct keys successfully observed.
    unique_kmers: u64,
    /// Windows skipped because the window contained a non-ACGT byte.
    skipped_windows: u64,
    /// K-mer length, fixed at construction.
    kmer_length: usize,
    /// Canonical mode, fixed at construction.
    canonical_mode: bool,
    /// Maximum per-key count (`u32::MAX`), kept for the verbatim error text.
    max_count: u32,
}

/// Width-selected local storage. Mirrors the private `CounterTable` enum in
/// `table.rs`, but with plain (non-concurrent) maps.
#[derive(Debug)]
enum LocalTable {
    /// k <= 32: an 8-byte key plus a 4-byte count.
    Dense(hashbrown::HashMap<u64, u32>),
    /// 33..=64: the wide layout.
    Wide(hashbrown::HashMap<u128, u32>),
}

impl LocalKmerCounts {
    /// Create an empty accumulator for `kmer_length` in the given mode.
    ///
    /// # Arguments
    /// * `kmer_length` - K-mer length (must be 1..=64; the owning
    ///   `KmerCounter` has already validated it)
    /// * `canonical_mode` - Whether inputs are canonicalized before counting
    ///
    /// # Panics
    /// Debug builds assert the `1..=64` range; release builds assume the
    /// owning counter enforced it.
    pub fn new(kmer_length: usize, canonical_mode: bool) -> Self {
        debug_assert!(
            (1..=64).contains(&kmer_length),
            "LocalKmerCounts::new called with k={} outside 1..=64",
            kmer_length
        );
        Self::with_capacity(kmer_length, canonical_mode, LOCAL_INITIAL_CAPACITY)
    }

    /// Create an empty accumulator with an explicit capacity hint.
    pub fn with_capacity(kmer_length: usize, canonical_mode: bool, capacity: usize) -> Self {
        let table = if kmer_length <= MAX_KMER_SIZE_IN_U64 {
            LocalTable::Dense(hashbrown::HashMap::with_capacity(capacity))
        } else {
            LocalTable::Wide(hashbrown::HashMap::with_capacity(capacity))
        };
        Self {
            table,
            total_kmers: 0,
            unique_kmers: 0,
            skipped_windows: 0,
            kmer_length,
            canonical_mode,
            max_count: u32::MAX,
        }
    }

    /// Increment one encoded k-mer, reproducing the shared counter's semantics.
    ///
    /// # Errors
    /// Returns the verbatim `K-mer count overflow reached maximum value
    /// <max>` error when this key is already at `u32::MAX`; the local total is
    /// not advanced in that case.
    pub fn increment(&mut self, kmer_encoded: u128) -> ProcessingResult<()> {
        // Compute the new total BEFORE mutating the table so a total overflow
        // can never leave a key advanced while the total is not (fail-loud,
        // never partial).
        let new_total = self.total_kmers.checked_add(1).ok_or_else(|| {
            ProcessingError::new("Total k-mer count overflow during local accumulation")
        })?;
        let new_unique = self.unique_kmers.checked_add(1);

        match &mut self.table {
            LocalTable::Dense(map) => {
                debug_assert!(
                    kmer_encoded <= u64::MAX as u128,
                    "LocalKmerCounts selected the dense u64 width for k={} but the \
                     encoded value has bits set above bit 64",
                    self.kmer_length
                );
                match map.get_mut(&(kmer_encoded as u64)) {
                    Some(count) => {
                        if *count == self.max_count {
                            return Err(Self::overflow_error(self.max_count));
                        }
                        *count += 1;
                    }
                    None => {
                        let unique = new_unique.ok_or_else(|| {
                            ProcessingError::new(
                                "Unique k-mer count overflow during local accumulation",
                            )
                        })?;
                        map.insert(kmer_encoded as u64, 1);
                        self.unique_kmers = unique;
                    }
                }
            }
            LocalTable::Wide(map) => match map.get_mut(&kmer_encoded) {
                Some(count) => {
                    if *count == self.max_count {
                        return Err(Self::overflow_error(self.max_count));
                    }
                    *count += 1;
                }
                None => {
                    let unique = new_unique.ok_or_else(|| {
                        ProcessingError::new(
                            "Unique k-mer count overflow during local accumulation",
                        )
                    })?;
                    map.insert(kmer_encoded, 1);
                    self.unique_kmers = unique;
                }
            },
        }

        self.total_kmers = new_total;
        Ok(())
    }

    /// Record one window skipped because it contained a non-ACGT byte.
    ///
    /// Skipped windows never advance the total, matching the pre-PAR-02
    /// per-chunk warning accounting in `count.rs`.
    pub fn record_skipped(&mut self) {
        self.skipped_windows = self.skipped_windows.saturating_add(1);
    }

    /// Total k-mers successfully accumulated (sum of counts).
    pub fn total_kmers(&self) -> u64 {
        self.total_kmers
    }

    /// Number of distinct keys accumulated locally.
    pub fn unique_kmers(&self) -> u64 {
        self.unique_kmers
    }

    /// Number of skipped invalid windows accumulated locally.
    pub fn skipped(&self) -> u64 {
        self.skipped_windows
    }

    /// Number of entries currently held by the local table.
    pub fn key_count(&self) -> usize {
        match &self.table {
            LocalTable::Dense(map) => map.len(),
            LocalTable::Wide(map) => map.len(),
        }
    }

    /// Look up one encoded k-mer's count in this local table.
    ///
    /// Additive accessor (Phase 7): [`crate::count::CountResult::get_count`]
    /// routes a key to its single owning partition and reads it back through
    /// the width-correct arm. The dense arm looks up the narrowed `u64` the
    /// same way [`Self::increment`] stores it; the wide arm looks up the
    /// `u128` directly. No behavior change to increment or reduction.
    ///
    /// # Arguments
    /// * `kmer_encoded` - Encoded k-mer at the public `u128` width
    ///
    /// # Returns
    /// `Some(count)` when this table holds the key, `None` otherwise.
    pub fn get_count(&self, kmer_encoded: u128) -> Option<u32> {
        match &self.table {
            LocalTable::Dense(map) => {
                debug_assert!(
                    kmer_encoded <= u64::MAX as u128,
                    "LocalKmerCounts selected the dense u64 width for k={} but the \
                     looked-up value has bits set above bit 64",
                    self.kmer_length
                );
                map.get(&(kmer_encoded as u64)).copied()
            }
            LocalTable::Wide(map) => map.get(&kmer_encoded).copied(),
        }
    }

    /// K-mer length this accumulator was built for.
    pub fn kmer_length(&self) -> usize {
        self.kmer_length
    }

    /// Whether this accumulator canonicalizes (mirrors the owning counter).
    pub fn canonical_mode(&self) -> bool {
        self.canonical_mode
    }

    /// Whether the live table is the dense `u64` width (k <= 32).
    pub fn uses_dense_storage(&self) -> bool {
        matches!(&self.table, LocalTable::Dense(_))
    }

    /// Bytes occupied by one stored key, read from the live variant.
    pub fn stored_key_bytes(&self) -> usize {
        match &self.table {
            LocalTable::Dense(_) => core::mem::size_of::<u64>(),
            LocalTable::Wide(_) => core::mem::size_of::<u128>(),
        }
    }

    /// Iterate `(kmer_encoded, count)` pairs at the public `u128` width.
    ///
    /// The dense arm zero-extends its `u64` keys, exactly like
    /// `KmerCounter::get_all_counts` (D-03 / DENSE-02: lossless because every
    /// k <= 32 encoder leaves the upper 64 bits zero).
    pub fn iter(&self) -> Box<dyn Iterator<Item = (u128, u32)> + '_> {
        match &self.table {
            LocalTable::Dense(map) => {
                Box::new(map.iter().map(|(key, count)| (*key as u128, *count)))
            }
            LocalTable::Wide(map) => Box::new(map.iter().map(|(key, count)| (*key, *count))),
        }
    }

    /// Consuming drain: append every `(kmer_encoded, count)` pair to `out`.
    ///
    /// This is the output-stage collector (Phase 8 OUT-01): the owning map
    /// iterator is consumed inside the match arm and dropped when the arm
    /// ends, so the table's allocation is released during the drain instead
    /// of after a second full copy of the entries exists. The dense arm
    /// zero-extends its `u64` keys exactly like [`Self::iter`].
    ///
    /// # Arguments
    /// * `out` - Destination pair buffer; existing contents are preserved and
    ///   the drained pairs are appended
    ///
    /// # Returns
    /// Nothing; `out` receives every pair the table held.
    ///
    /// # Errors
    /// This method is infallible: pair collection has no error path.
    pub fn into_pairs_into(self, out: &mut Vec<(u128, u32)>) {
        match self.table {
            LocalTable::Dense(map) => {
                out.extend(map.into_iter().map(|(key, count)| (key as u128, count)));
            }
            LocalTable::Wide(map) => out.extend(map),
        }
    }

    /// Seed one key directly at an arbitrary count, for tests and benchmarks.
    ///
    /// This bypasses the four-billion-increment cost of reaching a count near
    /// `u32::MAX` while keeping the accumulator internally consistent: the
    /// total advances by the seeded count (or by the difference when the key
    /// already exists) and a fresh key advances the unique count. Production
    /// code must still reach counts through [`Self::increment`] so the WR-03
    /// "failed increments do not advance the total" rule holds.
    ///
    /// # Panics
    /// Debug builds assert the key fits the selected storage width. Panics on
    /// a `u64` total overflow, which requires seeding more than `u64::MAX`
    /// counts.
    pub fn seed_count(&mut self, kmer_encoded: u128, count: u32) {
        let (delta_total, is_new_key) = match &mut self.table {
            LocalTable::Dense(map) => {
                debug_assert!(
                    kmer_encoded <= u64::MAX as u128,
                    "seed_count on the dense u64 width received a key above bit 64"
                );
                Self::seed_in_map(map, kmer_encoded as u64, count)
            }
            LocalTable::Wide(map) => Self::seed_in_map(map, kmer_encoded, count),
        };

        self.total_kmers = self
            .total_kmers
            .checked_add(delta_total)
            .expect("seed_count total overflow");
        if is_new_key {
            self.unique_kmers = self
                .unique_kmers
                .checked_add(1)
                .expect("seed_count unique overflow");
        }
    }

    /// Width-generic seeding body: returns `(total delta, inserted new key)`.
    fn seed_in_map<K>(map: &mut hashbrown::HashMap<K, u32>, key: K, count: u32) -> (u64, bool)
    where
        K: std::hash::Hash + Eq,
    {
        match map.get_mut(&key) {
            Some(existing) => {
                let delta = count.saturating_sub(*existing) as u64;
                *existing = count;
                (delta, false)
            }
            None => {
                map.insert(key, count);
                (count as u64, true)
            }
        }
    }

    /// Release the local table's memory after a reduction.
    ///
    /// Replacing the map (rather than `clear()`ing it) drops the allocation so
    /// a reduced local behind a stale TLS handle holds no heap memory.
    pub(crate) fn release(&mut self) {
        *self = Self::with_capacity(self.kmer_length, self.canonical_mode, 0);
    }

    /// The verbatim overflow error text preserved from `KmerCounter::increment`.
    fn overflow_error(max_count: u32) -> ProcessingError {
        ProcessingError::new(format!(
            "K-mer count overflow reached maximum value {}",
            max_count
        ))
    }
}

/// Lock a local handle, recovering the data if a worker panicked while holding it.
pub(crate) fn lock_local(handle: &Arc<Mutex<LocalKmerCounts>>) -> MutexGuard<'_, LocalKmerCounts> {
    handle
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
}

/// Registry of the worker-local accumulators owned by one `KmerCounter`.
///
/// See the module docs for the generation protocol that prevents a drained
/// local from being reused on a later file.
#[derive(Debug)]
pub(crate) struct LocalHandleRegistry {
    /// Unique id for this counter, used as the TLS map key.
    counter_id: u64,
    /// K-mer length handed to freshly created locals.
    kmer_length: usize,
    /// Canonical mode handed to freshly created locals.
    canonical_mode: bool,
    /// Current generation. Bumped (under `state`) by [`Self::drain`].
    generation: AtomicU64,
    /// Registered locals for the current generation, oldest first.
    state: Mutex<Vec<Arc<Mutex<LocalKmerCounts>>>>,
}

impl LocalHandleRegistry {
    /// Create a registry for a counter with the given k / canonical mode.
    pub(crate) fn new(kmer_length: usize, canonical_mode: bool) -> Self {
        Self {
            counter_id: NEXT_COUNTER_ID.fetch_add(1, Ordering::Relaxed),
            kmer_length,
            canonical_mode,
            generation: AtomicU64::new(0),
            state: Mutex::new(Vec::new()),
        }
    }

    /// Return this worker thread's accumulator, creating one on first use.
    ///
    /// Fast path: TLS lookup keyed by counter id + generation, no mutex.
    pub(crate) fn handle(&self) -> Arc<Mutex<LocalKmerCounts>> {
        let counter_id = self.counter_id;
        let generation = self.generation.load(Ordering::Acquire);

        if let Some(handle) = WORKER_LOCALS.with(|cell| {
            let map = cell.borrow();
            map.get(&counter_id)
                .filter(|(cached_generation, _)| *cached_generation == generation)
                .map(|(_, handle)| Arc::clone(handle))
        }) {
            return handle;
        }

        // Miss: register a fresh local under the registry lock. Re-read the
        // generation under the lock because a concurrent `drain` bumps it
        // while holding the same lock.
        let mut locals = self
            .state
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        let generation = self.generation.load(Ordering::Acquire);

        WORKER_LOCALS.with(|cell| {
            let mut map = cell.borrow_mut();
            if let Some((cached_generation, handle)) = map.get(&counter_id) {
                if *cached_generation == generation {
                    return Arc::clone(handle);
                }
            }
            let local = Arc::new(Mutex::new(LocalKmerCounts::new(
                self.kmer_length,
                self.canonical_mode,
            )));
            locals.push(Arc::clone(&local));
            map.insert(counter_id, (generation, Arc::clone(&local)));
            local
        })
    }

    /// Take every registered local and move to a fresh generation.
    ///
    /// The returned handles are the caller's to reduce. After this returns,
    /// the next [`Self::handle`] call on any worker creates a new, empty local
    /// (the stale TLS entry has a different generation).
    pub(crate) fn drain(&self) -> Vec<Arc<Mutex<LocalKmerCounts>>> {
        let mut locals = self
            .state
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        let drained = std::mem::take(&mut *locals);
        // Release-store while still holding the lock, so the miss path in
        // `handle` cannot interleave a fresh local into the old generation.
        self.generation.store(
            self.generation.load(Ordering::Acquire) + 1,
            Ordering::Release,
        );
        drained
    }

    /// Sum the skipped-window counters across all registered locals.
    pub(crate) fn skipped_total(&self) -> u64 {
        let locals = self
            .state
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        locals
            .iter()
            .map(|handle| lock_local(handle).skipped())
            .sum()
    }
}
