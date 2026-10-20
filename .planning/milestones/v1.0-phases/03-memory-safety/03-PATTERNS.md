# Phase 3: Memory Safety - Pattern Map

**Mapped:** 2026-07-02
**Files analyzed:** 17 (10 modified, 1 dep move, 6 new test files)
**Analogs found:** 16 / 17 (1 no-analog: new `KmerKey` enum — net-new type)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/database/format.rs::merge_databases` / `should_use_streaming` / `merge_databases_inmemory` | service (dispatch+estimator) | transform | same file (dispatch already present) | exact (in-place edit) |
| `src/database/format.rs::DatabaseHeader` (header-only `total_kmers` read) | model (binary header) | file-I/O | `DatabaseHeader::read_from` (`format.rs:112-165`) — already reads 42 bytes | exact (reuse the existing reader) |
| `src/database/prefix_cache_merge.rs::ExternalSortMerger` (RAII + subdir + sweep + `RECORD_SIZE`) | service (external sort) | file-I/O / batch | `streaming_merge.rs::TempFileManager` (`:113-176`) | role-match (the canonical RAII pattern to mirror) |
| `src/database/streaming_merge.rs::TempFileManager` (the analog — read-only reference) | service | file-I/O | itself | exact (reference, not modified) |
| `src/database/merge_config.rs::MergeConfig` / `get_default_memory_limit` | config | request-response | same file | exact (in-place edit) |
| `src/hash/table.rs::KmerCounter` (`u128` → `KmerKey` width-selected) | model (in-memory store) | CRUD / event-driven | Phase 2 history: `RwLock<HashMap>` → `DashMap` swap (commits `7ccfd11`..`a545a2d`) | role-match (the API-stable internal-swap discipline) |
| `src/kmer/encoding.rs` (u64 encode/decode/reverse_complement primitives) | utility | transform | itself — u64 + u128 primitives already exist (`:37-160`, `:209-350`) | exact (reuse, no new code) |
| `src/cli/commands/merge.rs` (`--max-memory` / `--merge-mode` plumbing) | controller (CLI) | request-response | same file (`MergeArgs`, `parse_memory_size`) — flags already exist | exact (no new flag) |
| `pyo3/src/database.rs::PyDatabase::merge` (kwargs: `max_memory=`, `merge_mode=`) | controller (PyO3 binding) | request-response | `pyo3/src/counter.rs::PyCounter::new(threads=...)` (`:131-189`) | role-match (Phase 2 kwargs + signature attribute analog) |
| `Cargo.toml` (move `tempfile` dev→dep) | config | — | itself | exact (one-line move) |
| `tests/merge_routing_tests.rs` (NEW) | test (integration) | request-response | `tests/parallel_count_tests.rs` (D-10/D-13 differential shape) | role-match |
| `tests/merge_cleanup_tests.rs` (NEW) | test (integration) | file-I/O | `tests/common/temp_files.rs::TempFileManager` (test-side RAII) | role-match |
| `tests/dense_differential_tests.rs` (NEW) | test (integration) | transform | `tests/parallel_count_tests.rs::differential_threads_1_vs_n` + `tests/golden_tests.rs` | role-match (decoded-level variant) |
| `tests/dense_proptest_tests.rs` (NEW) | test (property) | transform | `tests/property/` + `proptest` usage | role-match |
| `tests/golden_sha256_tests.rs` (NEW) | test (regression) | file-I/O | `tests/golden_tests.rs::assert_golden_matches_manifest` (`:57-74`) | exact (same fixture + manifest) |
| `pyo3/tests/test_database_merge.py` (NEW) | test (Python contract) | request-response | `pyo3/tests/test_counter.py` (PyValueError/`pytest.raises` shape) | role-match |
| `src/hash/key.rs` or inline `KmerKey` enum (NEW type, D-03) | model | — | none (net-new); derived-`Hash+Eq+Copy` enum → `DashMap<KmerKey,u32>` | NO ANALOG (RESEARCH Pattern 1 is the design) |

## Pattern Assignments

### `src/database/format.rs` — `merge_databases`, `should_use_streaming`, `merge_databases_inmemory` (D-01, D-02)

**Analog:** the same file — the dispatch and three merge paths already exist; this is an in-place edit.

**Current OOM-on-estimate bug** (`format.rs:640-652`, `:692-708`):
```rust
// merge_databases: estimator loads EVERY entry to count kmers — defeats the purpose
let total_kmers: u64 = input_paths
    .iter()
    .map(|path| {
        let db = Self::from_file_path(path)?;   // <-- materializes all entries
        Ok(db.total_kmers())
    })
    .collect::<crate::error::ProcessingResult<Vec<_>>>()?
    .iter()
    .sum();

// should_use_streaming: SAME bug, second site
for path in input_paths {
    let db = RKDatabase::from_file_path(path)?;  // <-- materializes again
    total_kmers += db.total_kmers();
}
```

**Header-only read pattern to use** (`DatabaseHeader::read_from`, `format.rs:112-165`):
```rust
// Reads EXACTLY 42 bytes — magic(4)+version(2)+kmer_size(1)+pad(3)+total_kmers(8)+flags(1)+pad(7)+data_offset(8)+index_offset(8)
// Returns WITHOUT touching any KmerEntry. This is the D-01 fix.
let mut reader = BufReader::new(File::open(path)?);
let header = DatabaseHeader::read_from(&mut reader)?;   // header.total_kmers is the persisted u64
```

**Dispatch shape to preserve** (`format.rs:656-689`): the `use_prefix_cache` short-circuit, then `should_use_streaming` branch, then `merge_databases_{streaming,inmemory}` — keep the structure. The D-01/D-02 edits are: (a) replace the `from_file_path` estimator calls with the header-only read; (b) when `merge_mode == "memory"` AND estimate > budget, return `Err(...)` instead of falling through (D-02 reject path); (c) when `merge_mode == "auto"` AND estimate > budget, hard-route to streaming (already the `should_use_streaming` behavior once the estimator is fixed).

**KmerEntry on-disk layout** (`format.rs:194-238`) — UNCHANGED (D-03 RAM-only):
```rust
pub struct KmerEntry { pub kmer: u128, pub count: u32 }  // 16 B + 4 B = 20 B, little-endian, v2
// write_to: write_u128::<LittleEndian>(kmer) + write_u32::<LittleEndian>(count)
```
The dense u64 path widens `u64 → u128` (zero-extension) when serializing — negligible cost, zero format risk. **Readers see identical v2 bytes (DENSE-02).**

---

### `src/database/prefix_cache_merge.rs::ExternalSortMerger` — RAII + process-unique subdir + sweep (D-06)

**Analog:** `src/database/streaming_merge.rs::TempFileManager` (lines 113-176).

**TempFileManager RAII pattern to MIRROR** (`streaming_merge.rs:113-176`):
```rust
pub struct TempFileManager {
    temp_dir: PathBuf,
    files: Vec<PathBuf>,
    prefix: String,            // "rustkmer_<operation>_<pid>"
    auto_cleanup: bool,
}

impl TempFileManager {
    pub fn create_temp_file(&mut self) -> Result<(PathBuf, BufWriter<File>), ProcessingError> {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH).unwrap().as_micros();
        let file_name = format!("{}_{}.chunk", self.prefix, timestamp);
        let file_path = self.temp_dir.join(&file_name);
        let file = File::create(&file_path).map_err(|e| /* io_error */)?;
        self.files.push(file_path.clone());              // <-- TRACK every path
        Ok((file_path, BufWriter::new(file)))
    }

    pub fn cleanup(&self) {
        for file_path in &self.files {
            let _ = std::fs::remove_file(file_path);    // <-- best-effort, all paths
        }
    }
}

impl Drop for TempFileManager {
    fn drop(&mut self) {
        if self.auto_cleanup {
            self.cleanup();                              // <-- runs on scope exit / panic=unwind
        }
    }
}
```

**The gap to close** (`prefix_cache_merge.rs:322-326` — success-only cleanup):
```rust
// CURRENT: only removes files when result.is_ok() && !keep_intermediate
if result.is_ok() && !self.keep_intermediate {
    for temp_file in files_to_delete {
        let _ = std::fs::remove_file(&temp_file);
    }
}
// PROBLEM: panic / early-return / kill leaks the shards. Replace with the TempFileManager-style RAII.
```

**Process-unique subdir via `tempfile::TempDir`** (D-06, requires Cargo.toml move — see below):
```rust
use tempfile::TempDir;
let merge_subdir: TempDir = tempfile::Builder::new()
    .prefix("rustkmer-merge-")     // unambiguous prefix for the startup sweep
    .rand_bytes(8)                  // process-unique + collision-free
    .tempdir_in(&config.temp_dir)?;
// All shards written under merge_subdir.path(). TempDir::drop removes the whole tree recursively.
// NOTE: under panic="abort" / SIGKILL, Drop does NOT run — the startup sweep is the real defense.
```

**Centralize the 20-byte `RECORD_SIZE` constant** (CONCERNS fragile-area fix): the 8 `try_into().unwrap()` sites at `prefix_cache_merge.rs:461,463,645,646,679,680,917,918` (per CONTEXT `<canonical_refs>`) all assume the 20-byte `KmerEntry` layout. While touching this file, hoist `const RECORD_SIZE: usize = 20;` and reference it. The constant value is sourced from `KmerEntry::write_to` / `read_from` (16-byte u128 + 4-byte u32, `format.rs:210-213`).

**`panic="abort"` caveat** (`Cargo.toml:112`, release profile): `Drop` does NOT run on abort/SIGKILL/`process::exit`. D-06 pairs RAII with a startup stale-shard sweep:
```rust
fn sweep_stale_merge_dirs(temp_dir: &Path, ttl: std::time::Duration) {
    let cutoff = std::time::SystemTime::now() - ttl;
    if let Ok(entries) = std::fs::read_dir(temp_dir) {
        for entry in entries.flatten() {
            let name = entry.file_name();
            if name.to_string_lossy().starts_with("rustkmer-merge-") {
                if let Ok(mtime) = entry.metadata().and_then(|m| m.modified()) {
                    if mtime < cutoff {
                        let _ = std::fs::remove_dir_all(entry.path());
                        log::info!("Swept stale merge temp dir: {}", entry.path().display());
                    }
                }
            }
        }
    }
}
```
**Location recommendation** (from RESEARCH): a small new `src/database/temp_lifecycle.rs` module, or inline in `prefix_cache_merge.rs` — planner's call.

---

### `src/hash/table.rs::KmerCounter` — `u128` → width-selected `KmerKey` (D-03, DENSE-01)

**Analog:** the Phase 2 `RwLock<HashMap>` → `DashMap` swap (commits `7ccfd11`..`a545a2d` on this file). The discipline: swap the internal storage type while preserving the public API byte-for-byte (Phase 2 D-05 carry-forward, CONTEXT `<decisions>`).

**Current swap site** (`table.rs:11-34`):
```rust
pub struct KmerCounter {
    table: DashMap<u128, u32>,          // <-- THE SWAP SITE: becomes DashMap<KmerKey, u32>
    total_kmers: std::sync::atomic::AtomicU64,
    unique_kmers: std::sync::atomic::AtomicU64,
    kmer_length: usize,                 // <-- width is selected from this in new()
    canonical_mode: bool,
    max_count: u32,
}
```

**Public API to preserve** (`table.rs:49-145`):
```rust
pub fn new(kmer_length: usize, canonical_mode: bool, initial_capacity: usize, _num_threads: usize) -> ProcessingResult<Self>
pub fn increment(&self, kmer_encoded: u128) -> ProcessingResult<()>   // <-- stays u128 externally
pub fn get_count(&self, kmer_encoded: u128) -> Option<u32>
pub fn get_all_counts(&self) -> Vec<(u128, u32)>
```
**Width-selection site** (`table.rs:49-67`): `new()` already validates `kmer_length ∈ 1..=64`. Add: if `kmer_length <= MAX_KMER_SIZE_IN_U64` (32), the counter stores `KmerKey::U64`; else `KmerKey::U128`. The public `increment(u128)` signature stays — narrow internally with a `debug_assert!(kmer_encoded <= u64::MAX as u128)` for the u64 path (zero-cost in release).

**Atomicity-critical increment pattern to preserve** (`table.rs:93-114`) — the `entry().and_modify().or_insert_with()` chain holds the shard lock for the entry's whole lifetime; do NOT split into `get()+insert()`:
```rust
let mut overflow = false;
self.table
    .entry(kmer_encoded)
    .and_modify(|count| {
        if *count == self.max_count { overflow = true; } else { *count += 1; }
    })
    .or_insert_with(|| { self.unique_kmers.fetch_add(1, Relaxed); 1 });
```
This verbatim pattern must survive the key-type swap (the `KmerKey` derives `Hash+Eq+Copy`, so `entry(KmerKey)` works identically to `entry(u128)`).

**`memory_usage()` to branch on width** (`table.rs:283-286`):
```rust
// CURRENT: self.table.len() * (24 + 20)   // 24 HashMap overhead + 20 (u128+u32)
// POST-SWAP: branch — U64 path: 24 + 12 (u64+u32); U128 path: 24 + 20.
// The DENSE-01 test asserts ~50% reduction for k=21.
```

**Phase 2 D-05 discipline (the meta-pattern):** every public signature stays `u128`; only internal storage swaps. The same approach made the `RwLock→DashMap` swap invisible to `count.rs`/`pyo3/src/counter.rs` callers.

---

### `src/kmer/encoding.rs` — u64 primitives (DENSE-01 wiring, NO new code)

**Analog:** itself. All u64 encode/decode/reverse_complement primitives already exist and are tested.

**Boundary constant** (`encoding.rs:13-17`):
```rust
pub const MAX_KMER_SIZE_IN_U64: usize = 32;    // <-- width-selection threshold
pub const MAX_KMER_SIZE_IN_U128: usize = 64;
```

**u64 path (use for k ≤ 32)** (`encoding.rs:49-160`):
```rust
pub fn encode_kmer_bytes(sequence: &[u8]) -> Result<u64, KmerError>   // bit-64 aligned (line 78: encoded <<= pos * 2)
pub fn decode_kmer(encoded: u64, length: usize) -> String              // bits_to_shift = 64 - length*2
pub fn reverse_complement(encoded: u64, length: usize) -> u64
```

**u128 path (current, k ≤ 64)** (`encoding.rs:221-350`):
```rust
pub fn encode_kmer_bytes_u128(sequence: &[u8]) -> Result<u128, KmerError>  // bit-128 aligned (line 230: bits_to_shift = 128 - length*2)
pub fn decode_kmer_u128(encoded: u128, length: usize) -> String            // bits_to_shift = 128 - length*2
pub fn reverse_complement_u128(encoded: u128, length: usize) -> u128
```

**CRITICAL D-04 caveat (bit-alignment mismatch):** the same k-mer `"ATGC"` packs to `57 << 56` in u64 but `57 << 120` in u128 — **different raw integers**. Cross-width comparison MUST decode to strings first (see `tests/dense_differential_tests.rs` below). `encode_kmer_auto` (`:299-307`) already picks u64 for k ≤ 32 but is unused in production; Phase 3 either uses it or does width-selection inside `KmerCounter::new`.

**Canonical path** (`src/kmer/canonical.rs`): `canonical_kmer` (u64, `:20`) and `canonical_kmer_u128` (u128, `:72`) both exist. The dense counter wires the u64 pair.

---

### `src/database/merge_config.rs::MergeConfig` / `get_default_memory_limit` (D-01)

**Analog:** itself — in-place edit; the structure and the auto-budget already exist.

**Current config** (`merge_config.rs:7-43`):
```rust
pub struct MergeConfig {
    pub max_memory_usage: usize,        // <-- the budget the estimator compares against
    pub chunk_size: usize,
    pub temp_dir: PathBuf,              // <-- parent for the new rustkmer-merge-* subdir
    pub use_streaming: bool,
    pub use_prefix_cache: bool,
    pub num_threads: usize,
    pub merge_mode: String,             // "auto" | "memory" | "streaming"
    pub keep_intermediate: bool,
    pub verbose: bool,
}
impl Default for MergeConfig {
    fn default() -> Self {
        Self { max_memory_usage: get_default_memory_limit(), /* ... */ }
    }
}
```

**Budget source** (`merge_config.rs:142-163`) — Linux-only `/proc/meminfo` + 32 GB fallback:
```rust
fn get_default_memory_limit() -> usize {
    #[cfg(unix)]
    { /* reads /proc/meminfo → MemTotal × 0.5 */ }
    32 * 1024 * 1024 * 1024 // 32GB fallback (macOS de-facto behavior)
}
```
**Note:** D-01 does NOT require changing this. The 32 GB ceiling is defensible (any merge whose estimate exceeds 32 GB routes to streaming regardless of actual RAM). `sys-info 0.9` is already a dep if cross-platform accuracy is wanted — planner's discretion (CONTEXT `<decisions>`).

---

### `src/cli/commands/merge.rs` — `--max-memory` / `--merge-mode` plumbing (analog for PyDatabase)

**Analog:** itself — `MergeArgs`, `parse_memory_size`, and `MergeConfig` assembly (~`:302-338` per CONTEXT) all exist. The CLI surface is unchanged; Phase 3's work here is minimal (the bounded-routing flows from the core `merge_databases` fix). This file is the **reference pattern** for how `MergeConfig` is assembled from user-facing params, which `pyo3/src/database.rs::PyDatabase::merge` must mirror.

---

### `pyo3/src/database.rs::PyDatabase::merge` — kwargs `max_memory=` / `merge_mode=` (MERGE-04)

**Analog:** `pyo3/src/counter.rs::PyCounter::new(threads=...)` (`:131-189`) — the Phase 2 kwargs + `#[pyo3(signature)]` + validation pattern.

**PyCounter kwargs analog** (`counter.rs:131-158`):
```rust
#[new]
#[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000, threads=None))]
fn new(kmer_length: i64, canonical: bool, initial_capacity: usize, threads: Option<usize>) -> PyResult<Self> {
    // Validate at the boundary (mirrors InvalidKmerSize style):
    if !(1..=64).contains(&kmer_length) {
        return Err(PyErr::new::<PyValueError, _>(format!("Invalid k-mer size: {}. Must be between 1 and 64", kmer_length)));
    }
    if let Some(t) = threads {
        if t < 1 {
            return Err(PyErr::new::<PyValueError, _>(format!("Invalid thread count: {}. Must be >= 1", t)));
        }
    }
    // ... resolve and build
}
```

**Current PyDatabase.merge — the MERGE-04 site** (`database.rs:1346-1392`):
```rust
#[staticmethod]
#[pyo3(signature = (databases, output))]              // <-- MUST extend to (databases, output, *, max_memory=None, merge_mode="auto")
fn merge(databases: Vec<String>, output: String) -> PyResult<()> {
    if databases.is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("databases list cannot be empty"));
    }
    for db_path in &databases {
        if !Path::new(db_path).exists() {
            return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(format!("Database file not found: {}", db_path)));
        }
    }
    let input_paths: Vec<PathBuf> = databases.into_iter().map(PathBuf::from).collect();
    let config = MergeConfig::default();               // <-- MUST thread max_memory / merge_mode in
    let merged_db = RKDatabase::merge_databases(&input_paths, &config).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Merge operation failed: {}", e))
    })?;
    merged_db.write_to_file(Path::new(&output)).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to save merged database to {}: {}", output, e))
    })?;
    Ok(())
}
```
**Edit:** extend the `#[pyo3(signature = (...))]` with `*, max_memory: Option<String>, merge_mode: String` (mirror the CLI string-typed `--max-memory` parsed via `parse_memory_size`); build `MergeConfig` from the kwargs (defaulting via `MergeConfig::default()` then overriding `merge_mode` / `max_memory_usage`); route through the SAME `RKDatabase::merge_databases` core (the D-01 fix in core flows to PyO3 automatically — MERGE-04 satisfied by inheritance, not duplication).

**PyO3 registration** (`pyo3/src/lib.rs:39`): `PyDatabase` is already registered (`m.add_class::<PyDatabase>()?`). No new class to register — only the method signature changes.

---

### `Cargo.toml` — promote `tempfile` dev→dep (D-06 enabler)

**Analog:** itself (one-line move). `tempfile` is currently at `Cargo.toml:96` under `[dev-dependencies]` (`tempfile = "3.12"`, resolved to `3.24.0` per `Cargo.lock`). Move to `[dependencies]`. Cargo permits a crate in both sections; tests inherit from `[dependencies]`. **Pitfall 6**: if this move is skipped, `use tempfile::TempDir;` in `src/database/prefix_cache_merge.rs` fails to compile in `cargo build --release` (tests pass because dev-deps are available to the test harness, but `src/` is not a test).

**Release profile to preserve** (`Cargo.toml:101-104` per STACK.md): `lto = true`, `codegen-units = 1`, `panic = "abort"` — do NOT change these (the `panic="abort"` setting is load-bearing for D-06's design, see `prefix_cache_merge.rs` assignment above).

---

### `tests/merge_routing_tests.rs` (NEW — MERGE-01, MERGE-02)

**Analog:** `tests/parallel_count_tests.rs` (the Phase 2 differential/test-binary shape) + `tests/golden_tests.rs` (anyhow + fixture-loading).

**Test-file skeleton to copy** (`parallel_count_tests.rs:1-47`):
```rust
//! <module purpose — link to the MERGE-* requirement and decision>
use rustkmer::error::{ProcessingError, ProcessingResult};
use std::path::Path;
// `mod common;` if factories are needed (see golden_tests.rs:19)
```

**Bounding-proof strategy** (RESEARCH §"How to PROVE MERGE-01 without a human-scale dataset"): construct a synthetic `.rkdb` pair whose summed `total_kmers × 24 B` exceeds a tiny test budget (`config.max_memory_usage = 1024`), then assert: (a) the estimator reads the header only (no entry materialization), (b) `merge_databases` selects the streaming path, (c) the merge completes without allocating an unbounded hashmap. The routing LOGIC is size-independent — proven at toy scale, valid at human scale.

**Helpers available** (`tests/common/mod.rs:21-39`): `create_test_database(num_kmers, kmer_size, canonical, sorted)` → writes a small `.rkdb` for the synthetic-input setup.

---

### `tests/merge_cleanup_tests.rs` (NEW — MERGE-03)

**Analog:** `tests/common/temp_files.rs::TempFileManager` (test-side RAII, lines 31-48) — shows the project's existing `tempfile::TempDir` test idiom.

**TempDir test pattern** (`tests/common/temp_files.rs:10-48`):
```rust
use tempfile::{NamedTempFile, TempDir};
pub struct TempFileManager {
    _temp_dir: Option<TempDir>,   // owns the dir; dropped on struct drop
    files: Vec<PathBuf>,
}
impl TempFileManager {
    pub fn new() -> TempFileResult<Self> {
        let temp_dir = TempDir::new().map_err(|e| /* ... */)?;
        Ok(Self { _temp_dir: Some(temp_dir), files: Vec::new() })
    }
}
```

**What MERGE-03 tests must assert** (per RESEARCH §Validation MERGE-03): (a) panic-injection leaves no shards (inject a panic inside the prefix-cache merge, assert the subdir is empty/gone on the next inspection); (b) orphan `rustkmer-merge-*` subdir is swept on next merge start (create a stale subdir with an old mtime, call the sweep fn, assert removal); (c) process-unique subdir isolates concurrent merges (two `TempDir`s with `rand_bytes(8)` never collide). The `panic="abort"` case cannot be tested via `cargo test` (tests use `panic=unwind`) — document this and test the sweep separately.

---

### `tests/dense_differential_tests.rs` (NEW — DENSE-03, D-04/D-05)

**Analog:** `tests/parallel_count_tests.rs::differential_threads_1_vs_n` (the 1-vs-N commutativity differential — the direct template for the u64-vs-u128 differential) + `tests/golden_tests.rs` (golden-fixture loading).

**Count-to-map factory to mirror** (`parallel_count_tests.rs:102-120`):
```rust
fn count_input_to_map(k: usize, canonical: bool, input: &str) -> ProcessingResult<BTreeMap<u128, u32>> {
    let counter = KmerCounter::new(k, canonical, 4096, 1)?;
    let bytes = input.as_bytes();
    if bytes.len() >= k {
        for window in bytes.windows(k) {
            let kmer = encode_kmer_bytes_u128(window)?;           // <-- u128 path
            let final_kmer = if canonical { canonical_kmer_u128(kmer, k)? } else { kmer };
            counter.increment(final_kmer)?;
        }
    }
    Ok(counter.get_all_counts().into_iter().collect())
}
```

**CRITICAL D-04 adaptation — decode to strings before comparing** (the baseline-format caveat, RESEARCH Pattern 4):
The parallel_count_baseline JSON stores raw u128 integer keys (`tests/fixtures/parallel_count_baseline/k21_canon.json`: `{"5749079041": 6, ...}`). A raw-integer `assert_eq!(u64_map, u128_map)` is WRONG and will fail — u64 packs `"ATGC"` to `57 << 56`, u128 to `57 << 120`. The differential MUST:
```rust
fn counter_to_decoded_map(counter: &KmerCounter, k: usize, width_is_u64: bool) -> HashMap<String, u32> {
    counter.get_all_counts().into_iter().map(|(kmer_int, count)| {
        let kmer_str = if width_is_u64 {
            decode_kmer(kmer_int as u64, k)              // u64 decoder
        } else {
            decode_kmer_u128(kmer_int, k)                // u128 decoder
        };
        (kmer_str, count)
    }).collect()
}
// Then: assert_eq!(u64_decoded_map, u128_decoded_map);
```

**D-13 coverage matrix** (`parallel_count_tests.rs:75-83`): `k ∈ {21, 32, 64}` × `{canon, noncanon}`. k=21 and k=32 exercise u64; k=64 exercises u128 (unchanged path — the regression guard). Sorted/unsorted is not a capture axis for count maps (order-independent).

---

### `tests/golden_sha256_tests.rs` (NEW — DENSE-02)

**Analog:** `tests/golden_tests.rs::assert_golden_matches_manifest` (lines 57-74) — verbatim reuse of the same 12 fixtures + manifest.

**Pattern to copy** (`golden_tests.rs:24-74`):
```rust
fn load_golden_manifest() -> anyhow::Result<HashMap<String, String>> {
    let text = std::fs::read_to_string("tests/fixtures/golden_manifest.sha256")?;
    // parse "<filename> <sha256-hex>" lines into a map
}
fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new(); hasher.update(bytes); format!("{:x}", hasher.finalize())
}
fn assert_golden_matches_manifest(name: &str) -> anyhow::Result<()> {
    let manifest = load_golden_manifest()?;
    let expected = manifest.get(name).unwrap();
    let bytes = std::fs::read(format!("tests/fixtures/{}", name))?;
    let actual = sha256_hex(&bytes);
    assert_eq!(actual, *expected, "golden sha256 mismatch for {}", name);
    Ok(())
}
```
**What DENSE-02 re-verifies:** the 12 `tests/fixtures/golden_k{21,32,64}_{canon,noncanon}_{sorted,unsorted}.rkdb` files MUST hash identically post-dense-swap (D-03 RAM-only — disk stays v2). If the u64→u128 widening on write ever drifts, this test catches it. **No new baseline capture** (Phase 1 D-10 carry-forward — the baselines exist and are ground truth).

**Fixtures present** (`tests/fixtures/`): all 12 golden `.rkdb` + `golden_manifest.sha256` confirmed via `ls`.

---

### `tests/dense_proptest_tests.rs` (NEW — DENSE-03, property-based)

**Analog:** `tests/property/` directory + `proptest 1.5` (already a dev-dep, `Cargo.toml:97`). Generate random short DNA sequences, count through both the u64 (k ≤ 32) and u128 (any k) paths, assert decoded-map equality. Catches random-input packing/canonicalization bugs the fixed golden fixtures miss.

---

### `pyo3/tests/test_database_merge.py` (NEW — MERGE-04)

**Analog:** `pyo3/tests/test_counter.py` — the PyValueError + `pytest.raises(match=...)` shape.

**Python contract pattern to mirror** (per CLAUDE.md error-bridging convention):
```python
import pytest
import pyrustkmer

def test_merge_threads_kwargs_through():
    # merge_mode/max_memory must thread into MergeConfig and reach the bounded core
    pyrustkmer.PyDatabase.merge([db1, db2], "out.rkdb", merge_mode="streaming", max_memory="1024")
    # assert the merge selected streaming (e.g. via a side-effect or a too-small-budget routing)

def test_merge_rejects_bad_merge_mode():
    with pytest.raises(ValueError, match="merge_mode"):
        pyrustkmer.PyDatabase.merge([db1, db2], "out.rkdb", merge_mode="bogus")
```
**Import guard convention** (CLAUDE.md): `try: import pyrustkmer / except ImportError: pytest.skip(...)`.

---

### `src/hash/key.rs` or inline `KmerKey` enum (NEW type — D-03, NO ANALOG)

**No analog** — net-new type. RESEARCH Pattern 1 (§"Pattern 1: PackedKmer Width-Selection — Recommend Option A") is the design.

**Recommended definition** (RESEARCH Pattern 1, lines 211-219):
```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum KmerKey {
    U64(u64),     // k ≤ 32 — dense path (DENSE-01)
    U128(u128),   // 32 < k ≤ 64 — legacy width
}
```
**Why an enum, not a generic or parallel type:** RESEARCH's blast-radius analysis — Option A (enum) is LOW blast-radius (one concrete `DashMap<KmerKey, u32>` type, no `T: Hash+Eq+Copy` bound pollution, no PyO3 generic-`#[pyclass]` friction). Option B (parallel `KmerCounterU64`) duplicates ~400 LOC; Option C (generic) pollutes the public API. **Planner picks the location** (new `src/hash/key.rs` small module vs inline in `table.rs`) — CONTEXT `<decisions>` Claude's Discretion.

**DashMap enum-key behavior** (RESEARCH A1, ASSUMED): derived `Hash`/`Eq` discriminate by variant first, so `KmerKey::U64(5)` and `KmerKey::U128(5)` hash to different buckets. Within a single counter only one variant is ever inserted (width fixed at construction) — correct by construction.

## Shared Patterns

### Internal-swap-preserves-public-API (Phase 2 D-05 carry-forward)
**Source:** `src/hash/table.rs` git history (`7ccfd11`..`a545a2d`) — the `RwLock<HashMap>`→`DashMap` swap kept public signatures identical.
**Apply to:** `src/hash/table.rs` (the `u128`→`KmerKey` swap), `pyo3/src/database.rs::PyDatabase::merge` (kwargs addition is additive, not breaking).
**Discipline:** every public fn (`new`, `increment`, `get_count`, `get_all_counts`, `merge`) stays `u128`-typed externally; only the internal `DashMap` key swaps. Callers in `src/cli/commands/count.rs:393-406` and `pyo3/src/counter.rs:238,297,572,666` are unchanged.

### log-facade diagnostics (Phase 1 FOUND-02)
**Source:** every merge module already uses `log::info!`/`log::warn!`/`log::error!` (e.g. `format.rs:623-633`, `prefix_cache_merge.rs:330-362`, `streaming_merge.rs`).
**Apply to:** the new `sweep_stale_merge_dirs` fn, the D-02 reject path, the estimator's routing decision log.
**Constraint:** `src/cli/` is the only module with a print-macro allowlist (CLAUDE.md); new code in `src/database/` MUST use `log::`, not `println!`/`eprintln!`.

### Error taxonomy (single source of truth)
**Source:** `src/error.rs` — `KmerError`, `ProcessingError`, `ProcessingResult<T>`.
**Apply to:** all new fallible core fns (`estimate_total_kmers`, `sweep_stale_merge_dirs`, the D-02 reject path). Return `ProcessingResult<T>`; convert with `?` or `.into()`. PyO3 layer converts to `PyErr` via the existing `PyErr::new::<PyValueError/PyRuntimeError, _>` pattern (see `database.rs:1353,1376,1385`).

### KmerEntry 20-byte on-disk layout (D-03 — UNCHANGED)
**Source:** `src/database/format.rs::KmerEntry::write_to` / `read_from` (lines 210-213, 216-238).
**Apply to:** the dense u64 write path widens `u64 → u128` (zero-extension) before calling `KmerEntry::new(kmer as u128, count)`. Readers are untouched (DENSE-02 — disk stays v2 byte-identical). The 12 golden `.rkdb` sha256 baselines MUST still match post-swap (`tests/golden_sha256_tests.rs`).

### Temp-file RAII + process-unique subdir + startup sweep (D-06)
**Source:** `src/database/streaming_merge.rs::TempFileManager` (lines 113-176) — the canonical RAII pattern.
**Apply to:** `src/database/prefix_cache_merge.rs::ExternalSortMerger` (mirror the RAII); both paths write under `rustkmer-merge-*` subdirs created via `tempfile::Builder::new().prefix("rustkmer-merge-").rand_bytes(8).tempdir_in(&config.temp_dir)`. The startup sweep is shared (one fn, called at the entry of `merge_databases`).
**Constraint:** `panic="abort"` (release profile) means `Drop` does NOT run on abort/SIGKILL — the sweep is the real defense, not RAII.

### Dual-surface shared core (CLI + PyO3 inherit core fixes)
**Source:** ARCHITECTURE — counter/merge changes in `src/hash/` + `src/database/` flow to both `src/cli/commands/{count,merge}.rs` and `pyo3/src/{counter,database}.rs` via the shared `rustkmer` core crate.
**Apply to:** MERGE-04 — the D-01 estimator fix in `src/database/format.rs::merge_databases` lands once in core; `PyDatabase::merge` inherits the bounded path automatically because it calls `RKDatabase::merge_databases`. The PyO3 kwargs work is purely additive param-threading, not reimplementation.

### Validation matrix (Phase 1 D-13 carry-forward)
**Source:** `tests/parallel_count_tests.rs:75-83` — `k ∈ {21, 32, 64}` × `{canon, noncanon}`.
**Apply to:** `tests/dense_differential_tests.rs` (k=21, k=32 exercise u64; k=64 exercises u128 — the regression guard). The same matrix spans both widths, so no new fixtures are needed.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/hash/key.rs` (or inline `KmerKey` enum) | model | — | Net-new type. RESEARCH Pattern 1 IS the design (enum `KmerKey::U64(u64)`/`U128(u128)`). No existing enum-as-DashMap-key precedent in this codebase; derived `Hash+Eq+Copy` is standard Rust (RESEARCH assumption A1, LOW risk). |

## Metadata

**Analog search scope:** `src/database/{format,streaming_merge,prefix_cache_merge,merge_config}.rs`, `src/hash/table.rs`, `src/kmer/{encoding,canonical}.rs`, `src/cli/commands/{merge,count}.rs`, `pyo3/src/{database,counter,lib}.rs`, `tests/{parallel_count_tests,golden_tests,common/*}.rs`, `tests/fixtures/`, `Cargo.toml`.
**Files scanned:** 17 source + 4 test-helper + fixture inventory.
**Pattern extraction date:** 2026-07-02.
