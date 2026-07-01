# Phase 2: Parallel Counting - Pattern Map

**Mapped:** 2026-07-01
**Files analyzed:** 10 (new + modified)
**Analogs found:** 10 / 10 (all files have a concrete in-repo analog; 1 NEW test file leans on the test-helper layer)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `Cargo.toml` (root) | config | n/a (manifest) | existing `Cargo.toml` `[dependencies]` block + `[profile.release]` | exact (self-edit) |
| `src/hash/table.rs` | model (concurrent data structure) | event-driven (atomic upserts) | current `src/hash/table.rs` `KmerCounter` (the pre-refactor baseline) | exact (self-rewrite) |
| `src/cli/commands/count.rs` | controller (CLI handler) | request-response + streaming (per-record loop) | current `count.rs` `execute_count` / `process_fastq_file` / `process_fasta_file` | exact (self-rewrite) |
| `src/cli/args.rs` | config (clap derive) | request-response | existing `Commands::Count` struct + `Commands::Merge::num_threads` field | exact (self-edit) |
| `src/config/manager.rs` | config (env-layered) | request-response | existing env-var read block at `manager.rs:333` (`RUSTKMER_THREADS`) + `:302-320` siblings | exact (self-edit) |
| `src/cli/commands/merge.rs` | controller (CLI handler) | request-response (thread-pool init) | existing `merge.rs:340-363` `ThreadPoolBuilder` block (the established precedence pattern) | exact (self-edit — make `.expect()` tolerant) |
| `pyo3/src/counter.rs` | provider (PyO3 binding) | request-response | current `pyo3/src/counter.rs` `PyCounter::new` + `add_from_fastq` | exact (self-edit) |
| `pyo3/Cargo.toml` | config | n/a (manifest) | existing `pyo3/Cargo.toml` (no change needed — path dep flows dashmap) | exact (no-op) |
| `tests/parallel_count_tests.rs` (NEW) | test (integration, differential) | event-driven (concurrency) | `tests/round_trip_tests.rs` (binary structure + `mod common`) + `tests/golden_generate.rs` (capture-first) + `tests/common/mod.rs` factories | role-match (NEW file follows established test-binary conventions) |
| `tests/fixtures/parallel_count_baseline/` (NEW) | test fixtures | file-I/O | existing `tests/fixtures/golden_*.rkdb` + `golden_generate.rs` capture pattern | role-match (NEW fixtures follow golden-capture-first discipline) |
| `pyo3/tests/test_counter.py` (extend) | test (Python, pytest) | request-response | existing `pyo3/tests/test_counter.py` class structure + import guard | exact (self-extend) |

> **Note on `KmerCounter::new` signature:** the `_num_threads` param already exists at `table.rs:44` (currently ignored). D-06/D-07 make thread count a *rayon-pool* concern, configured at the command/init level — NOT inside the counter constructor. The planner should treat `KmerCounter::new(.., num_threads)` as a stats/reporting slot only; the real pool config is `rayon::ThreadPoolBuilder::build_global()` called once from `execute_count` and from `PyCounter::new`.

---

## Pattern Assignments

### `Cargo.toml` (root) — add `dashmap` dep

**Analog:** existing `[dependencies]` block (lines 12-87) + `[profile.release]` (lines 107-110).

**Pattern to follow — dependency insertion** (mirrors how `rayon = "1.8"` at line 58-59 is declared):
```toml
# Existing precedent (Cargo.toml:58-59):
# Parallel processing
rayon = "1.8"

# NEW — insert adjacent to rayon (same concern: concurrency):
# Concurrent sharded hash map (Phase 2; PCOUNT-02)
dashmap = "6.2.1"   # pins hashbrown ^0.14.5 — no duplicate-version bloat
```

**Preserve verbatim — `[profile.release]` (Cargo.toml:107-110):**
```toml
[profile.release]
lto = true
codegen-units = 1
panic = "abort"
```
Per STACK.md these are tuned for the production binary; the dashmap addition must NOT touch this block.

> **Planner note:** confirm `dashmap 6.2.1` resolves to `hashbrown 0.14.5` (already in `Cargo.lock:1525`) and pulls no new `hashbrown` major. `num_cpus` is transitive via `rayon` — do NOT add it directly (RESEARCH.md Open Question 3 + Assumption A1).

---

### `src/hash/table.rs` — `RwLock<HashMap>` → `DashMap` swap

**Analog:** the CURRENT `KmerCounter` in this same file (exact self-rewrite; PCOUNT-04 requires identical counts so the existing code IS the spec).

**Imports pattern** (current lines 6-10 — `parking_lot::RwLock` import becomes obsolete; `HashMap` import may stay for the `get_all_counts` return type):
```rust
// CURRENT (table.rs:6-7):
use parking_lot::RwLock as ParkingLotRwLock;
use std::collections::HashMap;
use super::filtering::{CountFilter, FilteringResult};
use crate::error::{KmerError, ProcessingError, ProcessingResult};

// POST-REFACTOR: add dashmap import; RwLock import can be dropped if no other field uses it
use dashmap::DashMap;
```

**Struct field swap** (current `table.rs:14-27`):
```rust
// CURRENT (table.rs:16):
table: ParkingLotRwLock<HashMap<u128, u32>>,

// POST-REFACTOR:
table: DashMap<u128, u32>,
```
Keep `total_kmers`, `unique_kmers` (atomics), `kmer_length`, `canonical_mode`, `max_count` UNCHANGED (D-05).

**Constructor** (current `table.rs:40-58`) — `DashMap::with_capacity` mirrors `HashMap::with_capacity`:
```rust
// CURRENT (table.rs:51):
table: ParkingLotRwLock::new(HashMap::with_capacity(initial_capacity)),

// POST-REFACTOR:
table: DashMap::<u128, u32>::with_capacity(initial_capacity),
```

**Core pattern — `increment` rewrite** (current `table.rs:67-91` is the PRE-refactor baseline; PCOUNT-04 demands identical counts). Use the flag-then-check entry pattern (RESEARCH Pattern 1 / Pitfall 6 — `and_modify` is `FnOnce(&mut V) -> ()` and CANNOT `return Err`):
```rust
// POST-REFACTOR increment (preserve exact overflow message from table.rs:76-79):
pub fn increment(&self, kmer_encoded: u128) -> ProcessingResult<()> {
    self.total_kmers
        .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

    // CRITICAL (Pitfall 1 + 2): the entry chain holds the shard lock for its
    // whole lifetime — atomic per-key. Do NOT split into get()+insert() (lost
    // update + deadlock risk). The overflow check MUST be inline inside
    // and_modify; the flag-then-check is the workaround for the FnOnce(&mut V)->() signature.
    let mut overflow = false;
    self.table
        .entry(kmer_encoded)
        .and_modify(|count| {
            if *count == self.max_count {
                overflow = true;
            } else {
                *count += 1;
            }
        })
        .or_insert_with(|| {
            self.unique_kmers
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            1
        });

    if overflow {
        return Err(ProcessingError::new(format!(
            "K-mer count overflow reached maximum value {}",   // <-- verbatim from table.rs:77-78
            self.max_count
        )));
    }
    Ok(())
}
```

**Read-side methods** — change `self.table.write()` / `self.table.read()` to direct `DashMap` calls. The borrow pattern shifts from `let table = self.table.read(); table.get(..)` to `self.table.get(..)` / `self.table.iter()`:
```rust
// CURRENT (table.rs:100-102, 109-112, 121-123, 139-145, 224-230, 237-240, 290-307):
let table = self.table.read();
table.get(&kmer_encoded).copied()
// ...
let table = self.table.read();
table.iter().map(|(&k, &v)| (k, v)).collect()

// POST-REFACTOR (DashMap iter yields RefMulti<K,V>; dereference the refs):
self.table.get(&kmer_encoded).map(|r| *r)                 // get_count
self.table.iter().map(|r| (*r.key(), *r.value())).collect() // get_all_counts
self.table.clear();                                        // reset (table.rs:225)
self.table.len()                                           // memory_usage (table.rs:240)
```

**`merge` method** (current `table.rs:276-316`) — the `let mut table = self.table.write();` becomes a per-entry `entry().and_modify().or_insert()` loop, mirroring `increment`'s pattern (overflow check inline).

**Validation to preserve** (current `table.rs:46-48`):
```rust
if !(1..=64).contains(&kmer_length) {
    return Err(KmerError::InvalidKmerSize(kmer_length as u32).into());
}
```

**Testing pattern** — extend the inline `#[cfg(test)] mod tests` block (current `table.rs:376-495`). Existing tests use `KmerCounter::new(31, false, 1000, 1).unwrap()` and must continue to pass UNCHANGED (D-05 API preservation). Add the two Wave-0 tests from VALIDATION.md:
```rust
// Existing tests use this constructor form (table.rs:382, etc.) — keep it working:
let counter = KmerCounter::new(31, false, 1000, 1).unwrap();

// NEW (VALIDATION.md Wave 0): test_increment_atomic_under_concurrency + test_overflow_preserved.
// Pattern: spawn N threads (std::thread) incrementing the same kmer; assert count == N.
```

---

### `src/cli/commands/count.rs` — parallelize per-record loop + thread plumbing + default-sort flip

**Analog:** current `execute_count` (lines 20-313) and `process_fastq_file` / `process_fasta_file` (lines 317-416) in this same file.

**Imports to add** (current import block at lines 5-17):
```rust
use rayon::prelude::*;   // NEW — for par_iter / try_for_each on record chunks
```

**Pattern A — thread-count resolution + global pool init** (mirror the established `merge.rs:340-363` precedence pattern, but tolerate `Err` per Pitfall 3):
```rust
// EXISTING TEMPLATE (merge.rs:340-363) — the project's only ThreadPoolBuilder site today.
// Phase 2 must (a) generalize to the D-07 precedence chain and (b) drop the .expect() (Pitfall 3).
//
// POST-REFACTOR (insert at the top of execute_count, BEFORE the file loop at count.rs:128):
fn resolve_thread_count(args_threads: Option<usize>) -> usize {
    // Precedence (D-07): --threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus
    if let Some(t) = args_threads.filter(|&n| n >= 1) { return t; }
    if let Ok(v) = std::env::var("RUSTKMER_THREADS") {
        if let Ok(t) = v.parse::<usize>() { if t >= 1 { return t; } }
    }
    if let Ok(v) = std::env::var("RAYON_NUM_THREADS") {
        if let Ok(t) = v.parse::<usize>() { if t >= 1 { return t; } }
    }
    rayon::current_num_threads()  // or num_cpus::get() — both reachable; rayon's is consistent with the pool
}

// In execute_count:
let threads = resolve_thread_count(/* args.command.threads() */);
if *verbose { eprintln!("Using {} threads", threads); }
// PITFALL 3: build_global returns Err on 2nd call (tests, embed, count→merge pipeline).
// IGNORE the Err — do NOT .expect() (merge.rs:349 currently does; that's the bug to fix).
let _ = rayon::ThreadPoolBuilder::new()
    .num_threads(threads)
    .build_global();
```

**Pattern B — counter construction** (current `count.rs:121-123`):
```rust
// CURRENT (the hardcoded `1` to be replaced):
let counter = Arc::new(KmerCounter::new(
    *k, *canonical, *size, 1, // num_threads: fixed to 1 for sequential processing
)?);

// POST-REFACTOR: Arc<KmerCounter> already exists — rayon workers share it via Arc clone.
// Pass the resolved thread count for stats/reporting; the real pool config is build_global above.
let counter = Arc::new(KmerCounter::new(*k, *canonical, *size, threads)?);
```

**Pattern C — per-record loop parallelization** (current `process_fastq_file` lines 368-416 + `process_fasta_file` lines 317-365). The current loops close over `counter: &Arc<KmerCounter>` inside `processor.process_file(|record| { ... })`. The `bio` reader is sequential (D-02), so records must be buffered into bounded chunks then `par_iter`'d:
```rust
// CURRENT (count.rs:377-415) — sequential, per-record closure passed to FastqProcessor::process_file:
processor.process_file(|record| {
    let sequence = record.seq();
    // ... encode → canonicalize → counter.increment(final_kmer) ...
    Ok(())
})

// POST-REFACTOR (D-01, D-discretion buffering):
// 1. Read records sequentially (gzip stays single-threaded, D-02) into a bounded Vec<Record>.
// 2. par_iter the chunk; each rayon task does encode → canonicalize → counter.increment.
// 3. try_for_each propagates ProcessingResult<()> (counter.increment may now Err on overflow).
//
// NOTE: bio::io::fastq::Record is owned (no lifetime param) — safe to push into a Vec and par_iter.
// The `counter: &Arc<KmerCounter>` is captured by reference into each task; DashMap gives interior
// mutability so increment takes &self (no Mutex needed).
const CHUNK_SIZE: usize = 4096;   // Claude-discretion; planner can tune
```

**Pattern D — default-sort flip** (D-09). Current logic at `count.rs:47`:
```rust
// CURRENT (count.rs:47):
let should_sort = if *no_sort { false } else { *sort };

// POST-REFACTOR (D-09: --sort becomes default; --no-sort disables; --sort kept as alias):
let should_sort = !*no_sort;
```
`output_text_format` (lines 419-470) and `output_binary_format` (lines 473-547) consume `should_sort` unchanged — no edits needed there.

**Validation helpers to preserve** (current `count.rs:42-67`): `*k < 1 || *k > 64` re-check, `validate_filtering()`, `validate_input()` — keep as-is. The new `--threads < 1` rejection (D-discretion: "mirror InvalidKmerSize style") should land in the same boundary-validation block.

---

### `src/cli/args.rs` — add `--threads` field to `Commands::Count`

**Analog:** the existing `Commands::Count` struct (lines 19-96) for field style, AND `Commands::Merge::num_threads` (lines 295-301) for the exact thread-flag precedent.

**Pattern — clap derive field** (mirror `Commands::Merge::num_threads` at `args.rs:295-301`):
```rust
// EXISTING PRECEDENT (args.rs:295-301) — Merge's thread flag:
/// Number of threads for parallel processing (0 = all cores)
#[arg(
    long,
    default_value = "0",
    help = "Number of threads for parallel processing (0 = use all cores)."
)]
num_threads: usize,

// POST-REFACTOR — add to Commands::Count. Use Option<usize> (default None = all cores),
// NOT default_value="0", so the precedence chain (D-07) can distinguish "unset" from "0".
// Adjacent to the existing --sort/--no_sort pair (args.rs:75-81):
/// Number of threads for parallel counting (default: all cores; precedence: --threads > RUSTKMER_THREADS > RAYON_NUM_THREADS)
#[arg(long)]
threads: Option<usize>,
```

**Match-arm update** — `execute_count` destructures every field of `Commands::Count` (count.rs:22-40). The new `threads` field MUST be added to that match arm (or use `..` to ignore). Pattern is the existing `sort, no_sort,` pair at `count.rs:35-36`.

**Validation pattern** — `Commands::validate_input()` / `validate_filtering()` (args.rs:420-507) is the established place to collect multiple errors before failing. A `threads < 1` check (D-discretion) mirrors the `min_count > max_count` check at args.rs:442-446:
```rust
// EXISTING PATTERN (args.rs:442-446) — collect-then-fail:
if let (Some(min), Some(max)) = (min_count, max_count) {
    if min > max {
        errors.push("Minimum count cannot exceed maximum count".to_string());
    }
}
// NEW: validate threads inside validate_input() (or a new validate_threads() helper):
if let Some(t) = threads { if *t < 1 { errors.push("--threads must be >= 1".to_string()); } }
```

---

### `src/config/manager.rs` — wire `RUSTKMER_THREADS` through (already parsed at line 333)

**Analog:** the env-var read block at `manager.rs:333-337` (already parses `RUSTKMER_THREADS`) and the sibling reads at `:302-320` (memory) / `:323-327` (default_k) / `:329-331` (canonical).

**The parse already exists** (manager.rs:333-337):
```rust
if let Ok(val) = env::var(format!("{}_THREADS", ENV_PREFIX)) {
    if let Ok(threads) = val.parse::<usize>() {
        config.kmer_counting.threads = Some(threads);
    }
}
```
> **Planner note (RESEARCH Open Question 3):** `merge.rs` reads `RAYON_NUM_THREADS` directly via `std::env::var`, NOT through `ConfigManager`. For consistency with merge, the planner may have `execute_count` read BOTH env vars directly (`resolve_thread_count` in Pattern A above does this). `manager.rs` change is OPTIONAL — only if the planner routes through ConfigManager. If so, expose a getter matching the existing pattern (e.g. `config.kmer_counting.threads`).

**Anti-pattern to avoid:** do NOT add a new `env::set_var` for `RUSTKMER_THREADS` — CONCERNS.md flags the existing `unsafe { env::set_var }` soundness note. The new read uses immutable `env::var` (safe).

---

### `src/cli/commands/merge.rs` — make `build_global().expect()` tolerant (Pitfall 3)

**Analog:** the existing `merge.rs:340-363` block (the project's only `ThreadPoolBuilder` site today).

**Current code (merge.rs:346-360)** — two `.expect("Failed to set rayon thread pool")` calls that WILL panic if `execute_count` already initialized the global pool:
```rust
rayon::ThreadPoolBuilder::new()
    .num_threads(args.num_threads)
    .build_global()
    .expect("Failed to set rayon thread pool");   // <-- PITFALL 3
```

**Post-refactor (Pitfall 3 mitigation):** replace both `.expect()` with a tolerate-Err helper. The `Err` is benign (pool already initialized by an earlier command in the same process):
```rust
// POST-REFACTOR (mirror what count.rs's resolve_thread_count should do):
if let Err(e) = rayon::ThreadPoolBuilder::new()
    .num_threads(args.num_threads)
    .build_global()
{
    if args.verbose {
        eprintln!("Note: global thread pool already initialized ({}); using existing pool", e);
    }
    // Non-fatal: fall back to the existing pool's thread count.
}
```
> Apply to BOTH call sites (merge.rs:346-349 and merge.rs:357-360). The `config.num_threads` assignment stays so downstream stats reporting is accurate.

---

### `pyo3/src/counter.rs` — `PyCounter` `threads` kwarg + `pyo3::allow_threads` GIL release

**Analog:** current `PyCounter::new` (lines 124-146) for the kwarg; `add_from_fastq` (lines 370-444) for the GIL-release site.

**Pattern A — `#[new]` signature extension** (current `counter.rs:124-146`). Add `threads=None` to the existing `#[pyo3(signature = (...))]`:
```rust
// CURRENT (counter.rs:124-126):
#[new]
#[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000))]
fn new(kmer_length: i64, canonical: bool, initial_capacity: usize) -> PyResult<Self> {

// POST-REFACTOR (D-08):
#[new]
#[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000, threads=None))]
fn new(
    kmer_length: i64,
    canonical: bool,
    initial_capacity: usize,
    threads: Option<usize>,
    py: Python<'_>,                 // needed for pool init side-effects if any (or omit)
) -> PyResult<Self> {
    // ... existing 1..=64 validation (counter.rs:129-134) preserved ...
    let resolved = threads.unwrap_or_else(num_cpus::get);   // None == all cores (parity with CLI)
    // build_global ONCE; tolerate Err (pool may already be init from a prior PyCounter)
    let _ = rayon::ThreadPoolBuilder::new()
        .num_threads(resolved)
        .build_global();
    let counter = RustPyCounter::new(kmer_length_usize, canonical, initial_capacity, resolved)
        .map_err(|e| PyErr::new::<PyValueError, _>(format!("Failed to create counter: {}", e)))?;
    Ok(Self { counter })
}
```

**Pattern B — internal field swap to `Arc<RustPyCounter>`** (RESEARCH Pattern 4 planner note (1)). Current field at `counter.rs:105-108`:
```rust
// CURRENT (counter.rs:104-108):
#[pyclass(name = "PyCounter")]
pub struct PyCounter {
    counter: RustPyCounter,        // owned — rayon workers cannot share an &mut
}

// POST-REFACTOR:
#[pyclass(name = "PyCounter")]
pub struct PyCounter {
    counter: std::sync::Arc<RustPyCounter>,   // Arc — clone into each allow_threads closure
}
```
> This is an INTERNAL field swap; the Python-visible API is unchanged. Every `&mut self` method that currently does `self.counter.increment(..)` must become `self.counter.increment(..)` through the Arc (DashMap gives interior mutability, so `increment` already takes `&self`).

**Pattern C — GIL release around heavy counting methods** (RESEARCH Pattern 4 + Pitfall 4). Current `add_from_fastq` (counter.rs:370-444):
```rust
// CURRENT (counter.rs:370) — holds the GIL the whole time:
fn add_from_fastq(&mut self, file_path: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
    let path_str = file_path.to_str()?;
    let path = Path::new(path_str);
    // ... uses self.counter.increment directly under the GIL ...

// POST-REFACTOR (CRITICAL — Pitfall 4: extract ALL PyString/Python args to owned Rust types FIRST):
fn add_from_fastq(&self, py: Python<'_>, file_path: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
    let path_str = file_path.to_str()?.to_owned();   // owned String — Send-safe
    let counter = self.counter.clone();              // Arc clone — Send
    py.allow_threads(move || {
        // GIL released — rayon workers run in parallel here
        process_fastq_owned(&counter, &path_str)
            .map_err(|e| rustkmer::ProcessingError::with_context("FASTQ processing", Box::new(e)))
    })
    .map_err(|e: rustkmer::ProcessingError| {
        PyErr::new::<PyValueError, _>(format!("Failed to process FASTQ: {}", e))
    })
}
```

> **API VERSION (VERIFIED):** the project pins `pyo3 = "0.27.2"` (pyo3/Cargo.toml:21). In 0.27.2 the method is `Python::allow_threads`. `Python::detach` is the 0.28+ rename and is NOT available — compiling with `detach` will fail. Do NOT migrate mid-phase.

> **Open Question 1 (RESEARCH):** `add_kmer` (single k-mer) and `add_sequence` (short string) may not warrant `allow_threads` overhead. Recommendation: wrap only `add_from_fastq` / `add_from_fasta` (clear win); leave `add_kmer` / `add_sequence` holding the GIL. Planner to document the decision.

---

### `pyo3/Cargo.toml` — NO change (path dep flows dashmap through)

**Analog:** existing `pyo3/Cargo.toml:23-24`:
```toml
# RustKmer core library
rustkmer = { path = ".." }
```
Adding `dashmap` to the ROOT `Cargo.toml` flows it through this path dep automatically (RESEARCH Assumption A6). The pyo3 crate does NOT need `dashmap` as a direct dep — it only touches `RustPyCounter` (a re-export of `rustkmer::hash::KmerCounter`) via the public API, never `DashMap` directly.

> **Planner note:** verify `maturin develop` picks up the new dep in a clean build (CI smoke step).

---

### `tests/parallel_count_tests.rs` (NEW) — `--threads 1` vs `N` differential test

**Analog:** `tests/round_trip_tests.rs` (binary structure: `mod common; use common::*; anyhow::Result<()>` test bodies) + `tests/golden_generate.rs` (capture-first pattern + D-13 matrix) + `tests/common/mod.rs` factories.

**Test-binary skeleton** (mirror `round_trip_tests.rs:1-28`):
```rust
//! Phase 2 differential correctness test: --threads 1 vs --threads N produce
//! identical count maps (PCOUNT-04). Uses the commutativity of integer addition
//! as a high-signal bug detector — ANY divergence is a concurrency bug.

mod common;

use common::*;
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;

// Adapter pattern (round_trip_tests.rs:20-28): TestResult<T> = Result<T, Box<dyn Error>>
// is not Send+Sync; bridge to anyhow via a centralized .a() extension.
trait TestResultExt<T> { fn a(self) -> anyhow::Result<T>; }
impl<T> TestResultExt<T> for Result<T, Box<dyn std::error::Error>> {
    fn a(self) -> anyhow::Result<T> { self.map_err(|e| anyhow::anyhow!("{}", e)) }
}
```

**Factory reuse** (from `tests/common/mod.rs`):
- `create_test_database`, `encode_test_kmer` — for synthesizing known k-mer sets.
- `databases_have_same_kmers` (common/mod.rs:114-130) — the SET/MAP comparison helper (already order-independent — perfect for the differential assertion, since sharded iteration order differs from HashMap).

**D-13 coverage matrix** (mirror `golden_generate.rs:55-69`):
```rust
// EXISTING (golden_generate.rs:55-69):
fn all_cells() -> Vec<Cell> {
    let mut out = Vec::new();
    for &k in &[21usize, 32, 64] {
        for &canonical in &[true, false] {
            for &sorted in &[true, false] { out.push(Cell { k, canonical, sorted }); }
        }
    }
    out
}
// NEW test reuses k ∈ {21,32,64} × canonical ∈ {true,false} × threads ∈ {1, 2, N}.
```

**Temp-file scaffolding** (from `tests/common/temp_files.rs` + the `temp_file!`/`temp_fasta!` macros at lines 226-244):
```rust
// EXISTING (temp_files.rs:95-115): create_temp_fasta / create_temp_fastq helpers.
// NEW test uses these to build small synthetic FASTA/FASTQ inputs.
use rustkmer::temp_fasta;   // macro_export — crate-level
```

**Differential assertion pattern** (the heart of D-10 / PCOUNT-04):
```rust
#[test]
fn differential_threads_1_vs_n() -> anyhow::Result<()> {
    for &k in &[21usize, 32, 64] {
        for &canonical in &[true, false] {
            let input = fixed_dna_input();   // deterministic — mirror GOLDEN_INPUT (golden_generate.rs:39-46)
            let map_1 = count_with_threads(&input, k, canonical, 1)?;
            let map_n = count_with_threads(&input, k, canonical, num_cpus::get());
            // The sharp assertion: addition is commutative → maps MUST be equal.
            assert_eq!(map_1, map_n, "divergence at k={} canonical={} (concurrency bug)", k, canonical);
        }
    }
    Ok(())
}
```

**Thread-spawning pattern for inline `table.rs` test** (`test_increment_atomic_under_concurrency`): use `std::thread::scope` (Rust 1.63+; project is 1.80+) to spawn N threads incrementing the same k-mer; assert final count == N. This complements the integration-level differential test.

---

### `tests/fixtures/parallel_count_baseline/` (NEW) — golden-capture-first JSON baselines

**Analog:** existing `tests/fixtures/golden_*.rkdb` (12 committed binary fixtures) + `golden_generate.rs` (the `#[ignore]`d capture generator).

**Capture discipline** (D-10 / Phase 1 carry-forward): capture the count MAPS from the CURRENT sequential code BEFORE the dashmap swap. Persist as JSON (not bytes — the differential compares count maps, not file bytes; sharded iteration order would make byte-comparison flaky).

**Capture-first template** (mirror `golden_generate.rs:168-200`):
```rust
// Mirror golden_generate.rs:168-200 — a #[ignore]d one-shot generator:
#[test]
#[ignore = "one-shot pre-refactor baseline capture (D-10); run with --ignored"]
fn capture_parallel_count_baseline() -> Result<(), Box<dyn std::error::Error>> {
    let dir = Path::new("tests/fixtures/parallel_count_baseline");
    fs::create_dir_all(dir)?;
    for cell in all_cells() {
        let kmers = count_input(cell.k, cell.canonical)?;   // reuses golden_generate.rs:79-103
        // Serialize as a count MAP (JSON), not raw bytes — order-independent.
        let map: std::collections::BTreeMap<String, u32> = kmers.into_iter()
            .map(|(k, c)| (format!("{}", k), c)).collect();
        fs::write(dir.join(format!("k{}_{}.json", cell.k, canon_str(cell.canonical))),
                  serde_json::to_string_pretty(&map)?)?;
    }
    Ok(())
}
```

> **CRITICAL (D-10 sequencing):** this capture runs as the FIRST task of plan 02-04, BEFORE any `table.rs` edit lands. After the dashmap swap, the differential test asserts post-refactor counts match these committed baselines.

---

### `pyo3/tests/test_counter.py` (extend) — `threads` kwarg + GIL-release parallel case

**Analog:** existing `pyo3/tests/test_counter.py` (class structure, import guard, assertion style).

**Import guard** (counter.py:10-13 — preserve verbatim):
```python
try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)
```

**Existing creation-test pattern** (counter.py:19-38) — the `threads` kwarg tests follow this shape:
```python
# EXISTING (counter.py:33-38):
def test_create_counter_with_custom_capacity(self):
    counter = pyrustkmer.PyCounter(21, canonical=True, initial_capacity=5000)
    assert counter is not None

# NEW — threads kwarg (PCOUNT-03):
def test_create_counter_with_threads(self):
    counter = pyrustkmer.PyCounter(21, canonical=True, threads=4)
    assert counter is not None
    assert counter.kmer_length == 21

def test_threads_none_uses_all_cores(self):
    counter = pyrustkmer.PyCounter(21, threads=None)   # default — all cores
    assert counter is not None
```

**Parallel-counting differential test** (NEW) — mirrors the Rust differential at the Python layer:
```python
class TestPyCounterParallel:
    """PCOUNT-03: GIL-release delivers parallel speedup; counts match sequential."""

    def test_parallel_counts_match_sequential(self, tmp_path):
        # Write a FASTQ fixture, count with threads=1 and threads=N, assert maps equal.
        # Reuses the commutativity property — any divergence is a concurrency bug.
        ...
```

**Assertion idiom** (counter.py:48-60) — `pytest.raises(ValueError, match="...")`:
```python
# EXISTING (counter.py:48-50):
with pytest.raises(ValueError, match="Invalid k-mer size"):
    pyrustkmer.PyCounter(0)
# NEW (mirror for threads validation):
with pytest.raises(ValueError, match="..."):
    pyrustkmer.PyCounter(21, threads=0)
```

---

## Shared Patterns

### Thread-pool configuration (apply to `count.rs`, `merge.rs`, `pyo3/src/counter.rs`)
**Source:** `src/cli/commands/merge.rs:340-363` (the only existing `ThreadPoolBuilder` site)
**Apply to:** all three call sites must (a) use `build_global()` and (b) tolerate `Err` (Pitfall 3).
```rust
// The shared idiom — extract into a helper if the planner prefers:
let _ = rayon::ThreadPoolBuilder::new()
    .num_threads(resolved)
    .build_global();   // ignore Err: pool may already be initialized
```
**Verified:** `grep` confirms only `merge.rs:346-349` and `merge.rs:357-360` call `build_global` today. After Phase 2, `count.rs::execute_count` and `pyo3/src/counter.rs::PyCounter::new` add two more sites — ALL must tolerate Err.

### Overflow-error semantics (apply to `table.rs::increment`, `table.rs::merge`)
**Source:** current `table.rs:75-80` (verbatim message)
**Apply to:** the new dashmap `and_modify` closure must emit the IDENTICAL error message (`"K-mer count overflow reached maximum value {}"`) so PCOUNT-04 (identical counts) and existing tests are preserved.
```rust
// Preserve this exact string (table.rs:76-79):
return Err(ProcessingError::new(format!(
    "K-mer count overflow reached maximum value {}",
    self.max_count
)));
```

### Precedence chain resolution (apply to `count.rs`, optionally `config/manager.rs`)
**Source:** `merge.rs:350-363` (RAYON_NUM_THREADS fallback) + D-07 (add --threads and RUSTKMER_THREADS)
**Apply to:** `resolve_thread_count` in `count.rs`; same precedence for `PyCounter::new` (D-08 parity).
```
--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus
```

### Boundary validation (apply to `args.rs::validate_input`, `pyo3/src/counter.rs::new`)
**Source:** `args.rs:420-507` (collect-then-fail) + `count.rs:42-44` (`InvalidKmerSize`) + `counter.rs:129-134`
**Apply to:** new `--threads < 1` rejection (D-discretion: "mirror InvalidKmerSize style"). CLI side: append to `errors` Vec in `validate_input`. PyO3 side: `PyErr::new::<PyValueError, _>` mirroring the existing k-mer-size check.

### Test-binary conventions (apply to `tests/parallel_count_tests.rs`)
**Source:** `tests/round_trip_tests.rs:1-28` (binary header + `mod common` + `TestResultExt` adapter)
**Apply to:** the NEW differential test binary. Reuse `tests/common/mod.rs` factories (`encode_test_kmer`, `databases_have_same_kmers` for map equality) and `tests/common/temp_files.rs` (`temp_fasta!`, `create_temp_fastq`).

### Golden-capture-first sequencing (apply to `tests/fixtures/parallel_count_baseline/`)
**Source:** `tests/golden_generate.rs` (the `#[ignore]`d one-shot capture template)
**Apply to:** the pre-refactor baseline capture for plan 02-04. Capture JSON count MAPS (order-independent), not raw bytes.

---

## No Analog Found

All 10 files have concrete in-repo analogs. The two NEW artifacts (`tests/parallel_count_tests.rs`, `tests/fixtures/parallel_count_baseline/`) are role-match analogs — they follow the established test-binary / golden-capture conventions rather than copying a single existing file.

| File | Closest Analog | Gap | Resolution |
|------|----------------|-----|------------|
| `tests/parallel_count_tests.rs` | `tests/round_trip_tests.rs` + `tests/common/mod.rs` | NEW differential-test concept (1-vs-N) | Follow RESEARCH Pattern (commutativity assertion); reuse `databases_have_same_kmers` for map equality |
| `tests/fixtures/parallel_count_baseline/` | `tests/fixtures/golden_*.rkdb` + `golden_generate.rs` | JSON baselines (not binary) | Capture as `BTreeMap` JSON for order-independent comparison; reuses `golden_generate.rs::count_input` logic |

> **No external-pattern files:** RESEARCH.md §Code Examples (Patterns 1-4) already provides the dashmap/rayon/pyo3 patterns; the planner should cross-reference those excerpts when the in-repo analog is the PRE-refactor code being replaced.

---

## Metadata

**Analog search scope:**
- `src/` (full): `hash/table.rs`, `cli/commands/{count,merge}.rs`, `cli/args.rs`, `config/manager.rs`, `io/fastq.rs`, `database/prefix_cache_merge.rs`
- `pyo3/src/`: `counter.rs`, `lib.rs`, `Cargo.toml`
- `tests/`: `common/{mod,temp_files}.rs`, `round_trip_tests.rs`, `golden_generate.rs`, `golden_tests.rs`, `fixtures/`
- `Cargo.toml` (root), `Cargo.lock` (hashbrown version verification)

**Files scanned:** 14 source files + 2 manifests + Cargo.lock
**Pattern extraction date:** 2026-07-01
**Cross-references:** RESEARCH.md §Code Examples (Patterns 1-4), §Common Pitfalls (1-6); CONTEXT.md §decisions (D-01..D-10); VALIDATION.md §Wave 0 Gaps
