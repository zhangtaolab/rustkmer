# Phase 9: Python Parity - Research

**Researched:** 2026-11-13
**Domain:** PyO3 0.27.2 binding cutover to the shared Rust counting engine, D2 skip-N semantics unification, `.rkdb` writer reuse, benchmark-baseline comparison
**Confidence:** HIGH (engine/writer/PyO3 mechanisms read from source and exercised); MEDIUM on the unmeasured ≥1.2x benchmark outcome and on the Phase 8 blob-pin reinterpretation (see Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Engine Integration
- `add_from_fasta` / `add_from_fastq` build a per-call `CountEngine` from the counter's own `k`, `canonical`, and resolved `threads`, call `count_file`, then fold the result in with `CountResult::merge_into(&shared KmerCounter)` — no engine state is added to `PyCounter`, and the path matches the CLI exactly.
- Record format comes from the method name (`add_from_fasta` → `SequenceKind::Fasta`, `add_from_fastq` → `SequenceKind::Fastq`). No extension/content sniffing and no move of `detect_sequence_kind` into the core.
- The per-call `EngineConfig` gets `initial_capacity = 0`. Repeated calls must not re-reserve a large hint into every partition; the persistent `KmerCounter` already holds the capacity.
- Parsing goes through `count_file`'s `bio` readers — the same strict, error-reporting parser the CLI uses. Malformed input surfaces as a Python `ValueError` carrying the parse context, replacing the old lenient `line % 4 == 2` loop.

#### D2 Skip-N Scope and Documentation
- Skip-N applies to every Python counting input: `add_from_fasta`, `add_from_fastq`, and `add_sequence`. The non-ACGT pre-filter (strip-N + join flanks) is removed everywhere; no strip-and-join remnant may survive in the Python surface.
- The user-visible change is documented in all three places: `PyCounter` method/module docstrings, a `docs/` page covering N-read semantics, and a migration note in `pyo3/README.md`. The differential artifact additionally carries the exact before/after counts.
- `total_kmers` drops on N-containing reads because skipped windows no longer advance the total. The exact before/after values are recorded in the PROF-05 differential re-run and stated in the docs. The old total is NOT preserved by adding flank-joined windows back.
- The contract is proven against the CLI on the same bytes: the N-free control must match exactly, and the real-N arm must match after D2. The cross-surface differential is the contract, not per-method unit assertions alone.

#### `save_database` Sorting and GIL
- The double sort is removed by sorting the pairs exactly once with `rayon::par_sort_unstable_by_key` (the Phase 8 unstable/parallel mandate), then handing them to a new `format.rs` constructor that marks the header `sorted = true` without sorting again. A stable, allocating re-sort and a public-field `header.sorted = true` shortcut are both rejected.
- `save_database` releases the GIL: `py.detach` with owned `Send` captures (the `String` path and a cloned `Arc`). Sorting and writing hundreds of millions of entries under the GIL is a hard block on every Python thread, so this is a requirement, not an optimization.
- Byte identity is proven by a new test: on the same input, `PyCounter.save_database` and the CLI `count` produce an identical `.rkdb` sha256, and the 1-vs-N invariant holds. The existing Phase 8 four-arm differential stays as-is.
- The empty-counter behavior is unchanged: `ValueError("Cannot save empty database. Add k-mers first.")`.

#### Measurement and Gating
- `scripts/bench/python_bench.py` gains the reserved exit-1 `--compare-baseline` mode: it compares medians against the committed `scripts/bench/baselines/python_bench_baseline.darwin.json` on the N-free control. Exit 1 is the genuine "did not beat baseline" verdict; exit 2 stays reserved for invalid measurement.
- Both thread configurations are reported: `threads=1` isolates the engine against the sequential baseline, and `threads=<default>` is the real user win. Both must be non-regressive and the default configuration must reach at least 1.2x on the N-free control.
- This phase produces dev-host evidence only. No CI comparison gate is added, because no CI-class baseline exists; CI baselines remain Phase 10's responsibility per the Phase 5 decision.
- The N-read differential is re-run with `--expect-unified`: all four cells must be equal, divergence must be zero, and the artifact is committed.

### Claude's Discretion
- Exact mechanism for exporting and asserting the extension version (`__version__` in `pyo3/src/lib.rs` vs a `PYRUSTKMER_VERSION` constant), and where the version-assert test lives.
- Naming of the new `format.rs` sorted-input constructor.
- Whether the engine helper lives inside `pyo3/src/counter.rs` or a new module under `pyo3/src/`.
- Organization of the new PyO3 tests across the existing `pyo3/tests/` files.

### Deferred Ideas (OUT OF SCOPE)
- Parallel record extraction in the engine (the measured producer-bound lever from Phase 7) — not needed for Python parity, and it is a core-engine change, not a Python one.
- CI-class Python baselines and any CI comparison gate — Phase 10 owns CI baseline regeneration.
- Backlog 999.1/999.2/999.3 — opportunistic only if this work touches them.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PY-01 | `PyCounter` file methods route through the shared engine (no longer a sequential line loop); the public `PyCounter` API is frozen; every parallel/blocking path uses `py.detach` with owned Send captures; the `save_database` double-sort is fixed. | Engine API verified (`CountEngine::new`/`count_file`/`finish`/`CountResult::merge_into`); `PyCounter` needs one private `threads: usize` field because `KmerCounter::new` discards `_num_threads`; `py.detach` bounds verified for PyO3 0.27.2; new sorted-input constructor design + Phase 8 blob-pin scoping; byte identity already proven on the golden input (session probe). |
| PY-02 | The D2 skip-N semantics is implemented in Python and the output change for N-containing reads is documented; the Python benchmark shows a measured win against the PROF-04 baseline. | `for_each_window` is the one skip-N extractor; current `--expect-unified` run is RED (exit 1, 4 divergent cases); committed Phase 5 differential supplies exact before/after counts; baseline JSON supplies the comparison median and exact-count invariant; `--compare-baseline` design specified below. |
</phase_requirements>

## Summary

Phase 9 is a cutover phase: the Rust core already contains every mechanism it needs (the Phase 7 `CountEngine`, the Phase 8 sorted/streaming writer, and the D2 `for_each_window` extractor), and the PyO3 surface is the last consumer still using its own sequential loops. The two `add_from_*` methods currently read lines, strip non-ACGT bytes, accumulate into one `LocalKmerCounts`, and merge once (`pyo3/src/counter.rs:707-828`); `add_sequence` keeps the same non-ACGT pre-filter (`pyo3/src/counter.rs:288-297`); `save_database` materializes the counter, sorts once with `sort_by_key`, and passes `sorted=true` to `RKDatabase::from_kmer_pairs`, which sorts a second time (`pyo3/src/counter.rs:450-476`, `src/database/format.rs:640-653`). Each of these has a verified replacement in the core.

Three findings reshape planning. First, the engine's per-call shape fits `PyCounter` exactly: `CountEngine::new(EngineConfig::new(k, canonical, threads, 0))` → `count_file(path, kind)` → `finish()` → `CountResult::merge_into(&KmerCounter)`, and `merge_into` deliberately reuses `merge_local_counts`' checked per-key `u32` sums and atomic total publication (`src/count/engine.rs:488-510`, `src/hash/table.rs:373-380`). Second, `PyCounter` does not currently store its resolved thread count — `KmerCounter::new` accepts `_num_threads` and discards it — so a private `threads: usize` field must be added to `PyCounter` (invisible to Python). Third, the Phase 8 frozen-contract pin is a whole-file `git hash-object` of `src/database/format.rs` (`eb0d5bf2…`); adding the locked new constructor necessarily changes that blob. No standing test pins the file hash (only the Phase 8 plan/evidence record does), so the plan must explicitly re-scope that check to "writer functions and emitted bytes unchanged", not silently drop it.

The user-visible risk is D2. On the nine-case differential fixture, Python currently emits **33 chimeric k-mers** across four cases and a total of **70** vs the CLI's **37**; after D2 every case must be equal, Python's totals drop to the CLI values, and the 33 chimeric keys disappear. This must be documented before users hit it. A related, easily-missed consequence of "remove the non-ACGT pre-filter everywhere": whitespace (and any other non-ACGT byte) in `add_sequence` stops being stripped and starts breaking windows. Existing tests at `pyo3/tests/test_counter.py:138-148` and the two Phase 7 parity classes assert the old behavior and must be rewritten, not merely extended.

**Primary recommendation:** Implement the locked design exactly, in four workstreams — (1) engine routing + private `threads` field + version export; (2) `save_database` `par_sort_unstable_by_key` + `RKDatabase::from_sorted_kmer_pairs` under `py.detach`; (3) D2 pre-filter removal + differential re-run + three-place documentation; (4) `--compare-baseline` benchmark mode with a host/fingerprint guard. Prove each with the concrete gates in the Validation Architecture section, and update (not delete) the Phase 8 frozen-contract check.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FASTA/FASTQ record parsing and window extraction | Rust core (`CountEngine::count_file` + `for_each_window`) | — | ENGINE-01/ENGINE-03 already made this the single implementation; Python must not own a second parser or window loop. |
| Counting accumulation | Rust core (`LocalKmerCounts` partitions → `KmerCounter`) | PyO3 boundary | The engine owns exactness; `PyCounter` only supplies k/canonical/threads and merges once. |
| GIL release and Send ownership | PyO3 FFI boundary (`py.detach`) | Rust core (all captured values are owned/Send) | The core has no Python dependency; only the binding knows about Python threads. |
| `.rkdb` header/entry serialization | Rust core (`src/database/format.rs`) | PyO3 binding (calls it) | Phase 8 froze the format.rs writer; the binding must not duplicate the header literal. |
| Sorting for binary search | Rust core (rayon `par_sort_unstable_by_key`) | PyO3 binding (invokes it in `save_database`) | Phase 8's in-place pdqsort mandate applies to every output sort. |
| Extension version identity | PyO3 module registration (`pyo3/src/lib.rs`) | Python packaging (`pyo3/pyproject.toml`) | `m.add` registers the attribute and appends it to `__all__`; the manifest is the expected-value source. |
| Benchmark comparison / verdict | Python dev harness (`scripts/bench/python_bench.py`) | CI (Phase 10 only) | Dev-host-only evidence this phase; exit codes are the contract. |
| N-read user documentation | Docs surfaces (`docs/`, `pyo3/README.md`, docstrings) | — | WR-04 precedent: a user-visible output change is never silent. |

## Standard Stack

### Core (all existing — this phase installs no packages)

| Library / Component | Version | Purpose | Why Standard |
|---------------------|---------|---------|--------------|
| `CountEngine` / `EngineConfig` / `SequenceKind` / `CountResult` | in-tree (`src/count/engine.rs`) | ONE counting entry point for CLI and Python | ENGINE-01; persistent workers, bounded queues, checked reductions. `[VERIFIED: src/count/engine.rs:225-274,505-510,780,935]` |
| `for_each_window` | in-tree (`src/kmer/extract.rs:90`) | ONE skip-N window extractor for k 1..=64 | ENGINE-03/D2; Python currently pre-filters before calling it. `[VERIFIED: src/kmer/extract.rs:24-56,90]` |
| `KmerCounter` / `LocalKmerCounts` | in-tree (`src/hash/table.rs`, `src/hash/local.rs`) | Shared mutable counter + exact per-call accumulators | `merge_local_counts` is the checked merge path the engine delegates to. `[VERIFIED: src/hash/table.rs:332-334,373-502]` |
| `RKDatabase` / `DatabaseHeader` / `KmerEntry` | in-tree (`src/database/format.rs`) | Frozen `.rkdb` v2 writer | Phase 8 froze the header/entry codecs; all writers must go through them. `[VERIFIED: src/database/format.rs:101-139,179-207,294-311,402-406,640-673]` |
| `rayon` | 1.8 (root `Cargo.toml:57`; `pyo3/Cargo.toml:50`) | In-place parallel unstable sort | Phase 8 mandate: `par_sort_unstable_by` (pdqsort) over the merge-sort family. `[VERIFIED: Cargo.toml:57, pyo3/Cargo.toml:50]` |
| `bio` | 2.0 (root `Cargo.toml:23`; resolved 2.0.3) | Strict FASTA/FASTQ readers | Same parser the CLI uses; wrapped FASTQ supported, inconsistent wrapping errors. `[VERIFIED: Cargo.toml:23; ~/.cargo/registry/src/…/bio-2.0.3/src/io/fastq.rs:249-285,495-509]` |
| `pyo3` | 0.27.2 (`pyo3/Cargo.toml:22`) | Python bindings; `py.detach` | `detach` is the non-deprecated GIL-release API in 0.27.2. `[VERIFIED: pyo3/Cargo.toml:22; docs.rs/pyo3/0.27.2/pyo3/marker/struct.Python.html]` |
| maturin | 1.11.5 in `.venv313` | Build/install the extension | The measured `.so` must be rebuilt from source. `[VERIFIED: session probe]` |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| pytest | 9.0.2 in `.venv313` | PyO3 behavior tests | Every PyO3 plan task; `pytest(pyo3/tests)`. `[VERIFIED: session probe]` |
| Python | 3.13.11 in `.venv313` (symlink to `/Users/forrest/miniconda3/envs/py313/bin/python`) | Bench + pytest interpreter | Matches the committed baseline's `python_version: "3.13.11"`. `[VERIFIED: session probe; scripts/bench/baselines/python_bench_baseline.darwin.json]` |
| numpy | 2.4.1 in `.venv313` | `pyrustkmer` runtime dependency | Required by the installed wheel metadata. `[VERIFIED: session probe]` |
| `unittest` (stdlib) | — | `scripts/bench/tests` harness suite | Standing gate: 361 tests, `OK (skipped=1)`. `[VERIFIED: session probe]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `CountEngine::new` per call | Cache an engine on `PyCounter` | Locked out: engine state would diverge from `k`/`canonical`/`threads` and add non-cloneable state to a `#[pyclass]`. |
| `py.detach` | `py.allow_threads` | Deprecated since PyO3 0.26.0; would fail the `-D warnings` clippy gate. `[VERIFIED: docs.rs/pyo3/0.27.2/…struct.Python.html]` |
| `RKDatabase::from_sorted_kmer_pairs` in `format.rs` | Construct `RKDatabase` in `pyo3/src/counter.rs` (fields are `pub`) | Duplicates the header literal outside the single writer, violating the Phase 8 single-writer discipline (`src/database/format.rs:402-406` shows the fields are public, but duplication is worse). |
| `par_sort_unstable_by_key` | `sort_by_key` (stable) | Allocates a slice-sized temporary buffer and is single-threaded; directly contradicts the Phase 8 mandate. |
| `m.add("__version__", …)` | A hand-written Python shim / `__init__.py` | The project has `python-source` disabled; `m.add` already appends to `__all__` so the maturin shim star-imports it. `[VERIFIED: ~/.cargo/registry/src/…/pyo3-0.27.2/src/types/module.rs:470-493]` |

**Installation:** none. The phase must leave `Cargo.toml`, `Cargo.lock`, `pyo3/Cargo.toml`, and `pyo3/Cargo.lock` byte-identical to the Phase 8 blobs (`fb5c8395…`, `7f24f3f3…`, `5b01979c…`, `6da3805f…`) — assert with an empty `git diff --stat` over the four files.

## Package Legitimacy Audit

**No external packages are installed or upgraded in this phase.** The entire implementation uses the existing locked graph (`pyo3` 0.27.2, `rayon` 1.8, `bio` 2.0.3, `maturin` 1.11.5). Consequently the Package Legitimacy Gate (registry lookup / postinstall scan) is not applicable. The supply-chain control for this phase is the opposite: **prove the manifests and lockfiles did not move** (see the gate above), and prove the measured `.so` came from the current tree via the module fingerprint plus the `__version__` assert.

## Architecture Patterns

### System Architecture Diagram

```
Python caller (GIL held)
  │
  ├─ PyCounter.add_from_fastq / add_from_fasta
  │     │  extract owned Send captures: String path, Arc<KmerCounter>, usize threads
  │     ▼
  │   py.detach(move || ...)                      ← GIL released
  │     │
  │     ├─ CountEngine::new(EngineConfig{k, canonical, threads, initial_capacity: 0})
  │     │       threads == 1 → sequential caller-thread path (0 workers)
  │     │       threads > 1  → N named OS workers + bounded sync_channel queues
  │     ├─ count_file(path, SequenceKind::{Fasta|Fastq})
  │     │       DefaultCompressedFileReader (gz/bz2/xz/multi-member gz)
  │     │       bio reader → for_each_window (skip-N) → partition routing
  │     └─ finish() → CountResult
  │            └─ merge_into(&KmerCounter)
  │                   └─ merge_local_counts: checked u32 per key +
  │                      atomic compare-exchange total publication
  ▼
PyResult<()> (GIL reacquired; errors → PyValueError)

PyCounter.save_database
  │  extract owned Send captures: String path, Arc<KmerCounter>
  ▼
py.detach(move || ...)                            ← GIL released
  ├─ counter.get_all_counts() → Vec<(u128, u32)>
  ├─ pairs.par_sort_unstable_by_key(|&(k, _)| k)  ← exactly ONE sort (pdqsort, in place)
  ├─ RKDatabase::from_sorted_kmer_pairs(pairs, k, canonical)  ← marks sorted=true, no re-sort
  └─ DatabaseHeader::write_to + KmerEntry::write_to → BufWriter → flush
  ▼
PyResult<()> (errors mapped to the existing ValueError messages)
```

### Recommended Project Structure (files to touch/create)

```
src/database/format.rs                  # ADD `RKDatabase::from_sorted_kmer_pairs` (pure addition)
tests/sorted_pairs_constructor_tests.rs # NEW: byte equality vs from_kmer_pairs(sorted=true)
pyo3/src/counter.rs                     # engine routing, threads field, D2 add_sequence, save_database
pyo3/src/lib.rs                         # m.add("__version__", env!("CARGO_PKG_VERSION"))
pyo3/tests/test_counter.py              # rewrite pre-D2 tests; add concurrency + skip-N parity
pyo3/tests/test_save_database_byte_identity.py  # NEW: CLI vs Py vs golden sha, 1-vs-N
pyo3/tests/test_version.py              # NEW: stale-extension/version assert
scripts/bench/python_bench.py           # --threads, --compare-baseline, exit 1, label updates
scripts/bench/tests/test_python_bench.py# NEW: comparison-mode tests (0/1/2 paths)
scripts/bench/n_read_differential.py    # EXPECTED_SEMANTICS + --previous before/after block
scripts/bench/tests/test_n_read_differential.py
scripts/bench/README.md                 # .venv313 command, compare mode, exit contract
docs/user-guide/n-read-semantics.md     # NEW page
docs/user-guide/index.md + mkdocs.yml   # link + nav entry
pyo3/README.md                          # migration note with before/after counts
```

### Pattern 1: Per-call engine routing (the CLI path, reused verbatim)

**What:** Build a throwaway engine from the counter's immutable parameters, count one file, merge the exact result into the persistent counter.
**When to use:** Every `add_from_fasta` / `add_from_fastq` call.
**Evidence:** `EngineConfig` fields and `count_file`/`finish`/`merge_into` are the exact API.

```rust
// Proposed skeleton (values quoted from src/count/engine.rs:225-240,254-264,268-274,780,935
// and src/count/engine.rs:505 for merge_into).
fn count_file_into_counter(
    counter: &Arc<RustPyCounter>,
    path: &str,
    kind: SequenceKind,
    threads: usize,
) -> Result<(), rustkmer::ProcessingError> {
    let config = EngineConfig::new(
        counter.kmer_length(),
        counter.canonical_mode(),
        threads,
        0, // initial_capacity: locked decision — the persistent counter holds capacity
    );
    let mut engine = CountEngine::new(config)?;
    engine.count_file(Path::new(path), kind)?;
    engine.finish()?.merge_into(counter)?;
    Ok(())
}
```

Notes:
- `CountResult::merge_into` is documented as "the Phase 9 PyO3 bridge" and reuses `merge_local_counts`; it uses rayon `par_iter` over the partition tables. `[VERIFIED: src/count/engine.rs:488-510]`
- `merge_local_counts` documents concurrent merges as a supported configuration: "Each per-key checked sum is serialized by the `DashMap` shard lock, and the aggregate total is published with an atomic compare-exchange loop, so concurrent merges cannot lose updates." `[VERIFIED: src/hash/table.rs:373-380]`
- Parse/IO errors return before `merge_into`, so the shared counter is unchanged on failure (same as the old path, which merged only after the full file). Preserve and test this.
- The skipped-window count lives in `FileStats`/`CountResult::stats()` but is **not** merged into `KmerCounter`; nothing in the PyO3 surface reads `local_skipped()`. Do not add a Python-visible skipped counter (API freeze). `[VERIFIED: src/hash/table.rs:354; grep over src/ and pyo3/src/ finds no reader]`

### Pattern 2: `save_database` — one sort, one writer, GIL released

**What:** Snapshot pairs, sort exactly once in place, hand them to a new sorted-input constructor, write through the frozen header/entry writers.
**When to use:** `PyCounter.save_database` only.

```rust
// Proposed skeleton. The new constructor's header literal mirrors the quoted
// `from_kmer_pairs` body (src/database/format.rs:646-666).
pub fn from_sorted_kmer_pairs(
    kmer_pairs: Vec<(u128, u32)>,
    kmer_size: u8,
    canonical: bool,
) -> crate::error::ProcessingResult<Self> {
    debug_assert!(
        kmer_pairs.windows(2).all(|w| w[0].0 <= w[1].0),
        "from_sorted_kmer_pairs requires a non-decreasing key order"
    );
    let entries: Vec<KmerEntry> = kmer_pairs
        .into_iter()
        .map(|(kmer, count)| KmerEntry::new(kmer, count))
        .collect();
    let header = DatabaseHeader {
        magic: *crate::database::format::DATABASE_MAGIC,
        version: crate::database::format::DATABASE_VERSION,
        kmer_size,
        total_kmers: entries.len() as u64,
        canonical,
        sorted: true,
        data_offset: 42, // Standard header size for version 2
        index_offset: 0,
        unique_kmers: entries.len() as u64,
        file_size: 0, // Will be calculated when writing
    };
    Ok(Self { header, entries, file_path: None })
}
```

The binding side (the Python-visible signature is unchanged: PyO3 injects `py: Python<'_>`, which Python callers never see):

```rust
// Proposed skeleton.
enum SaveDatabaseError { Empty, Database(String), CreateFile(String), Write(String) }

fn save_database_on_counter(
    counter: &Arc<RustPyCounter>,
    path: &str,
) -> Result<(), SaveDatabaseError> {
    let mut pairs = counter.get_all_counts();
    if pairs.is_empty() {
        return Err(SaveDatabaseError::Empty);
    }
    pairs.par_sort_unstable_by_key(|&(kmer, _)| kmer);
    let db = RKDatabase::from_sorted_kmer_pairs(
        pairs,
        counter.kmer_length() as u8,
        counter.canonical_mode(),
    )
    .map_err(|e| SaveDatabaseError::Database(e.to_string()))?;
    let file = File::create(Path::new(path))
        .map_err(|e| SaveDatabaseError::CreateFile(e.to_string()))?;
    let mut writer = BufWriter::new(file);
    db.write_to(&mut writer).map_err(|e| SaveDatabaseError::Write(e.to_string()))?;
    writer.flush().map_err(|e| SaveDatabaseError::Write(e.to_string()))?;
    Ok(())
}
```

- The existing error strings must survive: `"Cannot save empty database. Add k-mers first."`, `"Failed to create database: …"`, `"Failed to create file: …"`, `"Failed to write database: …"` (`pyo3/tests/test_counter.py:784-800` matches the first and third). A Send error enum returned through `detach` and mapped afterwards avoids constructing `PyErr` without the GIL.
- `RKDatabase` fields are `pub` (`src/database/format.rs:402-406`), but the binding must not build the header itself — that is the single-writer rule.
- `py.detach` requires both the closure and its return type to be `Ungil`, and on stable Rust `Ungil` is exactly `Send` (`impl<T: Send> Ungil for T`). `Result<(), SaveDatabaseError>` with `String` payloads is `Send`. `[VERIFIED: docs.rs/pyo3/0.27.2/pyo3/marker/struct.Python.html; docs.rs/pyo3/0.27.2/pyo3/marker/trait.Ungil.html]`
- `Arc<KmerCounter>` is already moved into existing `detach` closures (`pyo3/src/counter.rs:358,373,409,418`), which is in-repo proof that `Arc<KmerCounter>: Send`.

### Pattern 3: Version export through `m.add`

**What:** Export the crate version as a module attribute; `m.add` appends the name to `__all__`, so the maturin shim's `from .pyrustkmer import *` imports it.
**When to use:** `pyo3/src/lib.rs` module init; assert in a pytest and in every plan's pre-pytest command.

```rust
// pyo3/src/lib.rs, after the class registrations (proposed).
m.add("__version__", env!("CARGO_PKG_VERSION"))?;
```

Verified mechanism: PyO3 0.27.2's `PyModuleMethods::add` does `module.index()?.append(name)` and `add_class` delegates to `add`, which is how the current `__all__` (15 classes) is built. `[VERIFIED: ~/.cargo/registry/src/…/pyo3-0.27.2/src/types/module.rs:470-501]` The installed package currently has `pyrustkmer.__all__` with exactly those 15 class names and no `pyrustkmer.__version__` — so the attribute's presence is itself the stale-`.so` tripwire. `[VERIFIED: session probe of .venv313]`

### Pattern 4: `--compare-baseline` comparison

**What:** Re-run the N-free control, prove parity and exact counts, measure `threads=1` and `threads=default`, compare medians to the committed baseline, exit 0/1/2.
**When to use:** Phase 9's measurement gate only (no CI gate this phase).

Baseline contract (read from the committed file):

| Field | Value |
|-------|-------|
| `comparison_basis` | `"n-free-control"` `[VERIFIED: scripts/bench/baselines/python_bench_baseline.darwin.json]` |
| `baseline_scope` / `host_class` | `"dev-host-local-comparison"` / `"dev-host Apple M4 Max (16 cores, 128 GiB)"` |
| `params` | `k=21`, `canonical=true`, `threads=1`, `slice_reads=1000000`, `slice_seed=20261112` |
| control median | `n_free_control.arms[0].medians.wall_s = 32.14` |
| control exact counts | `{"total_kmers": 129579577, "unique_kmers": 73476107}` |
| control kept/dropped | `998117` / `1883` |
| control fingerprint sha256 | `5cc933331d4bfaf7f7b8380723a178f468c92ea9b0ba79bed8d47fa32f0d50a4` |
| source input fingerprint sha256 | `712cdf86007825bc3fc138ffaaa030a794f797be28619cd10d14235544ae82b7` |
| file sha256 (record in the new artifact) | `42bb480de7f139d5597015b4502fd749156ce97723020d0f661ca4f2e89f8d84` |

Comparison math (locked thresholds, no noise band unless the user says otherwise):
`baseline_t1 = 32.14`; `speedup_t1 = baseline_t1 / new_t1`; `speedup_default = baseline_t1 / new_default`; PASS iff `speedup_t1 >= 1.0` (non-regressive) **and** `speedup_default >= 1.2`. Record both medians, both speedups, CV%, and the raw reps. Exit 1 when the measured verdict fails; exit 2 for anything invalid; write the evidence doc on both 0 and 1 (never on 2).

Before any timing, the mode must assert BOTH: (a) CLI-vs-Python parity on the same control bytes (`parity_counts` already raises on mismatch), and (b) the new Python `exact_counts` equal the baseline's `{"total_kmers": 129579577, "unique_kmers": 73476107}`. A failure of either is exit 2 (invalid measurement / correctness regression), never a performance verdict.

Comparison artifact shape (keep it `validate_schema`-clean by putting the two measured control arms under `arms`):

```json
{
  "schema_version": 1,
  "mode": "compare-baseline",
  "created": "<utc>",
  "params": {"k": 21, "canonical": true, "slice_reads": 1000000, "slice_seed": 20261112,
             "reps": 3, "python": ".venv313/bin/python", "rustkmer": "target/release/rustkmer",
             "compare_baseline": "scripts/bench/baselines/python_bench_baseline.darwin.json"},
  "baseline": {"path": "...", "sha256": "42bb480d…", "created": "...", "host_class": "...",
               "comparison_basis": "n-free-control", "control_wall_s": 32.14,
               "exact_counts": {"total_kmers": 129579577, "unique_kmers": 73476107}},
  "arms": [{"name": "py21-n-free-control-t1", "...": "..."},
           {"name": "py21-n-free-control-tdefault", "...": "..."}],
  "n_free_control": {"exact_counts": {...}, "parity_control": {"equal": true, "...": "..."},
                     "input_fingerprint": {...}, "kept_reads": 998117, "dropped_reads": 1883,
                     "arms": ["the same two arms"]},
  "comparison": {"threads_1": {"speedup": 0.0, "non_regressive": true},
                 "threads_default": {"speedup": 0.0, "min_speedup": 1.2, "pass": true},
                 "result": "PASS"},
  "verdict": {"result": "PASS", "exit_code": 0},
  "provenance": {"binary": {...}, "git_commit": "...", "git_dirty": false,
                 "build_profile": "release", "rust_toolchain": "...", "platform": "darwin-arm64",
                 "created": "...", "module": {"path": "...", "sha256": "...", "size_bytes": 0},
                 "python_executable": "...", "python_version": "3.13.11", "maturin_version": "..."}
}
```

Reuse `binary_provenance` + `fingerprint`; the module fingerprint must be the inner native `.so` (the existing `_native_module_file` resolves maturin's shim). `validate_schema` tolerates extra keys, so the added blocks are safe. `[VERIFIED: scripts/bench/bench.py:268-340,386-417]`

### Pattern 5: N-read differential before/after

`n_read_differential.py --expect-unified` already asserts "all cases equal"; the current tree is RED: exit 1, divergent cases `['n_at_window_end', 'n_at_window_start', 'multiple_n', 'lowercase_n']`. `[VERIFIED: session probe 2026-11-13]` The committed Phase 5 artifact supplies the exact before counts:

| Case | CLI distinct/total | Python pre-D2 distinct/total | Python post-D2 (required) |
|------|--------------------|------------------------------|---------------------------|
| `control_no_n` | 2 / 10 | 2 / 10 | 2 / 10 |
| `n_at_first` | 2 / 9 | 2 / 9 | 2 / 9 |
| `n_at_window_end` | 0 / 0 | 9 / 9 | 0 / 0 |
| `n_at_window_start` | 1 / 1 | 9 / 9 | 1 / 1 |
| `n_at_last` | 2 / 9 | 2 / 9 | 2 / 9 |
| `multiple_n` | 0 / 0 | 7 / 7 | 0 / 0 |
| `lowercase_n` | 0 / 0 | 9 / 9 | 0 / 0 |
| `record_boundary` | 2 / 8 | 2 / 8 | 2 / 8 |
| `short_read` | 0 / 0 | 0 / 0 | 0 / 0 |
| **Totals** | **37** | **70** | **37** |

`python_only_total = 33`, `cli_only_total = 0`, `count_delta_total = 0`. `[VERIFIED: .planning/phases/05-measurement-regression-harness/n_read_differential.json]` These are the exact before/after numbers the docs must state: 33 chimeric k-mers eliminated; Python's nine-case total drops 70 → 37.

Two script details must change with D2: `EXPECTED_SEMANTICS` currently records `{"cli": "skip-N-windows", "python": "strip-and-join-pre-Phase-9"}` (`scripts/bench/n_read_differential.py:71-72`) and must record the unified semantics; the module docstring's "record-only — neither surface's semantics is changed" and "pre-Phase-9" language must be updated to reflect that Phase 9 lands the change. The four "equal cells" per case are `cli.distinct == python.distinct` and `cli.total == python.total`; the required totals are `python_only_total = cli_only_total = count_delta_total = 0` and `divergent_cases = []`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FASTA/FASTQ parsing in Python | A third line loop or extension sniffing | `CountEngine::count_file(path, SequenceKind)` | Same strict parser as the CLI; multi-member gzip / bz2 / xz already handled. |
| K-mer window extraction | A second skip-N/canonical loop | `for_each_window` | ENGINE-03: one implementation; rolling path for k ≤ 32, u128 for 33..=64. |
| Per-file accumulation and reduction | A new counter or merge routine | `CountEngine` + `CountResult::merge_into` | Checked per-key `u32`, atomic total publication, verbatim overflow messages. |
| Sorting for `.rkdb` | Stable sort, or a second sort | `par_sort_unstable_by_key` + `from_sorted_kmer_pairs` | Phase 8 in-place pdqsort mandate; the double sort is the bug being fixed. |
| `.rkdb` header/entry encoding | A header literal in the PyO3 crate | `DatabaseHeader::write_to` / `KmerEntry::write_to` | Single frozen writer; byte identity is the gate. |
| GIL release | `allow_threads`, or a custom thread | `py.detach` | Deprecated API; `Ungil`/`Send` is the compile-time safety check. |
| Python package version plumbing | A new shim package / `__init__.py` | `m.add("__version__", env!("CARGO_PKG_VERSION"))` | `add` appends to `__all__`; the maturin shim already star-imports. |
| Benchmark comparison | A new harness | Extend `python_bench.py`'s fresh-worker protocol | Provenance, parity-first, exit-code contract already exist. |

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing user `.rkdb` files are **not** migrated or invalidated (format v2 unchanged). Files previously written by Python from N-containing reads contain chimeric k-mers; new writes from the same input differ only in counts/keys. | None (documentation only). Do not rewrite existing databases. |
| Live service config | None — no services, daemons, or registries. | None. |
| OS-registered state | None — no launchd/systemd/Task Scheduler entries. | None. |
| Secrets/env vars | No secrets. `CONDA_PREFIX` must be **unset** for `maturin develop`, and `VIRTUAL_ENV`/`PATH` pinned to `.venv313`. | Rebuild command must use `env -u CONDA_PREFIX`. |
| Build artifacts / installed packages | `.venv313/lib/python3.13/site-packages/pyrustkmer/` holds a pre-Phase-9 `.so` (sha256 `c7701806…` at research time); `pyo3/target/` holds stale objects. | Rebuild with `maturin develop --release -m pyo3/Cargo.toml`; the new `__version__` attribute is the stale-build tripwire; record the new module path/sha256 in evidence. |

**Canonical question:** After every source edit, what runtime systems still have the old behavior cached? The installed native extension (until rebuilt) is the only one; no stored data or service config embeds this phase's behavior.

## Common Pitfalls

### Pitfall 1: `total_kmers` drops on N-containing reads — never silent
**What goes wrong:** Users see a smaller `get_stats().total_kmers` for the same N-containing file and assume data loss.
**Why it happens:** Skipped windows never reach `increment`, so neither the local nor the shared total advances. `for_each_window` documents "a window containing any non-ACGT byte is skipped and counted".
**How to avoid:** State the exact before/after counts (70 → 37 on the differential fixture; 33 chimeric keys) in the docstring, the docs page, and `pyo3/README.md`; record them in the differential artifact.
**Warning signs:** Docs say "counts may differ" without numbers; the real-N benchmark arm is used as a post-D2 parity gate.

### Pitfall 2: The skipped counter is not a Python-visible field
**What goes wrong:** A planner tries to expose `skipped_windows` on `PyCounterStats` to explain the drop.
**Why it happens:** The engine tracks it in `FileStats`/`ResultStats`, but `merge_into` does not merge it and `PyCounter`'s public surface is frozen.
**How to avoid:** Do not add API. Document the semantics; assert skip behavior through totals/count maps in tests.

### Pitfall 3: Whitespace and other non-ACGT bytes in `add_sequence`
**What goes wrong:** `add_sequence("ACG TACG ACGT")` previously joined the flanks; after removing the pre-filter every window containing the space is skipped (for k=7 that is all windows).
**Why it happens:** "Remove the non-ACGT pre-filter everywhere" includes whitespace, not just N.
**How to avoid:** Rewrite `pyo3/tests/test_counter.py:138-148` to assert skip-N semantics (e.g. `is_empty()` for those inputs / a skip-N reference map); document that any non-ACGT byte breaks a window. This is a second user-visible change and belongs in the migration note.

### Pitfall 4: Pre-D2 tests will fail by design
**What goes wrong:** The plan treats the red tests as regressions and weakens them.
**Why it happens:** Three clusters pin the old behavior: `test_add_sequence_with_whitespace/newlines` (`:138-148`), `TestPyCounterRollingPathParity` (`:1176`, `_clean` strips N), and `TestPyCounterNReadPreFilterParity` (`:1264`, pure-Python strip-and-join reference).
**How to avoid:** Rewrite them as skip-N parity tests with a pure-Python reference that excludes windows containing any non-ACGT byte, and keep an explicit "strip-and-join would differ here" assertion so the test cannot pass with the old pre-filter.

### Pitfall 5: FASTQ/FASTA parsing semantics change
**What goes wrong:** A 4-line assumption or a lenient line filter hides malformed input.
**Why it happens:** bio's FASTQ reader supports consistently wrapped records and errors on inconsistent wrapping / missing `@` / incomplete records; the old `line_num % 4 == 2` loop misparsed wrapped records. FASTA `record.seq()` preserves internal spaces (only trailing whitespace is trimmed).
**How to avoid:** Map parse errors to `PyValueError` with the existing `"Failed to process FASTA/FASTQ: …"` prefix; add a malformed-FASTQ test; document the stricter parser in the migration note.

### Pitfall 6: Global rayon pool is first-call-wins — benchmark arms must be fresh processes
**What goes wrong:** A comparison run constructs `PyCounter(threads=1)` and then `PyCounter()` in one process; `build_global` on the second call fails silently and the pool stays at 1 thread.
**Why it happens:** `PyCounter::new` calls `rayon::ThreadPoolBuilder::build_global()` and discards the "already initialized" error (`pyo3/src/counter.rs:190-199`).
**How to avoid:** The existing fresh-worker-per-rep protocol already isolates each arm; keep it. Never measure two thread configurations in one worker process.

### Pitfall 7: Engine thread-spawn cost on repeated small calls
**What goes wrong:** A loop calling `add_from_fastq` on tiny files becomes slower than the old path because each call spawns `threads` OS workers and 64 partition tables.
**Why it happens:** Locked decision: per-call engine, no caching; `PartitionLayout` uses `P = min(256, max(64, threads))`.
**How to avoid:** Accept and document; recommend one call per file / large inputs. Do not add a cached engine (re-litigates a locked decision).

### Pitfall 8: Concurrent `add_from_*` is safe but oversubscribed
**What goes wrong:** N Python threads × M engine workers oversubscribe the CPU; a concurrency test without a timeout can hang the suite if a regression deadlocks.
**Why it happens:** Each call owns an engine; the shared counter's `merge_local_counts` is concurrent-safe.
**How to avoid:** Add a concurrency test with a bounded `future.result(timeout=…)` and exact-count assertions; document the oversubscription. A concurrent `save_database` snapshot is safe but not linearizable — do not promise atomicity.

### Pitfall 9: Stale `.so` shadowing
**What goes wrong:** pytest/bench imports an old extension and passes/fails for the wrong reason.
**Why it happens:** `maturin develop` installs into site-packages; a stale build survives source edits.
**How to avoid:** Rebuild and assert before every pytest run; assert `__version__` exists (old builds lack it) and equals the `pyproject.toml`/`Cargo.toml` version; record `pyrustkmer.__file__`.

### Pitfall 10: The Phase 8 frozen `format.rs` blob pin
**What goes wrong:** The plan re-runs the literal 08-04 gate and fails on `git hash-object src/database/format.rs`, or quietly deletes the check.
**Why it happens:** Phase 8 pinned the whole file to `eb0d5bf29330301930d98d801480cf73d1cf826a`; a new constructor changes the blob by design.
**How to avoid:** See the dedicated conflict section below. Re-scope to "writer functions and emitted bytes unchanged", prove with a pure-addition diff plus the golden/byte tests, and record the new blob.

### Pitfall 11: `mkdocs build --strict` is not a usable gate here
**What goes wrong:** The docs gate fails for environmental reasons.
**Why it happens:** The installed `mkdocs` environment lacks the `section-index` plugin (observed exit 1: `Config value 'plugins': The "section-index" plugin is not installed`).
**How to avoid:** Validate docs with file-existence + nav-grep + content-grep gates; do not make mkdocs availability a phase blocker.

### Pitfall 12: Cross-host baseline comparison
**What goes wrong:** The committed dev-host baseline (M4 Max) is compared to numbers from a different machine.
**Why it happens:** Baselines are per-class, and only the OS flavor is in the filename.
**How to avoid:** `--compare-baseline` must reject (exit 2) when `baseline["platform"] != flavor`, `baseline["provenance"]["platform"] != f"{sys.platform}-{platform.machine()}"`, k/canonical differ, or the control/input fingerprints differ.

### Pitfall 13: Real-N arm labels go stale after D2
**What goes wrong:** New `python_bench.py` runs still label the real-N arm `timing-only-real-N-pre-D2` and say counts "WILL change when Phase 9 lands".
**Why it happens:** The constant is code, not data; committed baselines keep their historical text.
**How to avoid:** Update `REAL_N_EVIDENCE_CLASS`/`REAL_N_SEMANTICS_NOTE` for post-D2 runs (e.g. `timing-only-real-N-post-D2`, "not comparable to the pre-D2 committed baseline"); committed artifacts are immutable.

## Critical Conflict: the Phase 8 frozen `format.rs` blob pin

**Fact:** Phase 8's final gate asserts `git hash-object src/database/format.rs == eb0d5bf29330301930d98d801480cf73d1cf826a`, and the current tree still hashes to that value. `[VERIFIED: .planning/phases/08-output-pipeline-rkdb-v2-parity/08-04-PLAN.md:159; session `git hash-object`]` No standing test or CI step pins the file blob — the pin exists only in the Phase 8 plan/evidence. `[VERIFIED: grep over tests/ and scripts/]`

**Why the conflict is unavoidable:** The locked decision requires a new constructor in `format.rs`. Placing it anywhere else would either duplicate the 42-byte header literal outside the single writer (violating OUT-02's single-writer discipline) or use the explicitly rejected `header.sorted = true` field shortcut.

**Recommended resolution (must be explicit in the plan):**
1. Record pre-change and post-change blobs. `pre = eb0d5bf2…`; `post = <new blob>`.
2. Prove the diff is a pure addition: `git diff -U0 -- src/database/format.rs` contains **no removed lines** (the only `-` lines are the `--- a/...` header). The added region is exactly `RKDatabase::from_sorted_kmer_pairs` plus its doc comment.
3. Re-prove the byte contract with the existing tests, which are the real gate: `cargo test --locked --test golden_sha256_tests --test golden_tests --test rkdb_v2_byte_identity_tests --test output_pipeline_tests`. `from_kmer_pairs` remains untouched and is exercised by the four-arm differential. `[VERIFIED: tests/rkdb_v2_byte_identity_tests.rs:375-434; tests/output_pipeline_tests.rs:1-30]`
4. Add the new constructor's own byte-equality test (`from_sorted_kmer_pairs(sorted) == from_kmer_pairs(sorted, k, canonical, true)`) and the cross-surface pytest (CLI vs Py vs committed golden sha).
5. State in the phase evidence that the whole-file pin is **superseded for `format.rs` only** by (2)+(3)+(4); all other Phase 8 pins (Cargo.toml/Cargo.lock blobs, struct-definition location, count-path writer usage, fixture manifest `f010e42a…`) remain in force.

**Do not** delete the pin without replacement, and **do not** edit `from_kmer_pairs`, `DatabaseHeader::write_to`, or `KmerEntry::write_to/read_from`.

## Code Examples

### Version assert (command gate and pytest)

```python
# Proposed pyo3/tests/test_version.py core; also usable as a pre-pytest command.
import pathlib, tomllib
import pyrustkmer  # module-level import fails loudly if the extension is absent

REPO = pathlib.Path(__file__).resolve().parents[2]
expected = tomllib.loads((REPO / "pyo3" / "pyproject.toml").read_text())["project"]["version"]
assert getattr(pyrustkmer, "__version__", None) == expected, (
    "stale or mismatched extension: %r != %r — rebuild with maturin develop --release"
    % (getattr(pyrustkmer, "__version__", None), expected)
)
```

`pyo3/pyproject.toml:7` and `pyo3/Cargo.toml:3` both declare `version = "0.5.0"`; `env!("CARGO_PKG_VERSION")` reads the latter. `[VERIFIED: pyo3/pyproject.toml:7; pyo3/Cargo.toml:3]`

### Cross-surface byte identity (pytest) — already true today

The session probe (current Phase 8 tree) wrote the six-sequence `tests/golden_generate.rs::GOLDEN_INPUT` as FASTA, then produced four files with identical sha256:

```
a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7  PyCounter.save_database (threads=1)
a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7  rustkmer count --threads 1
a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7  rustkmer count --threads 4
a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7  tests/fixtures/golden_k21_canon_sorted.rkdb
```

`[VERIFIED: session probe 2026-11-13]` This makes the new byte-identity test both cross-surface and golden-anchored: it fails if the new constructor, the sort order, or the header literal drifts. Extend it to `threads=default` and to the 1-vs-N invariant (t1/t4/default all equal).

### Skip-N pure-Python reference for rewritten tests

```python
# Proposed reference: a window is emitted only if it contains no non-ACGT byte.
def reference_counts(sequences, k, canonical):
    counts = {}
    for raw in sequences:
        seq = raw.upper()
        for i in range(len(seq) - k + 1):
            window = seq[i:i + k]
            if any(base not in "ACGT" for base in window):
                continue
            if canonical:
                window = min(window, revcomp(window))
            counts[window] = counts.get(window, 0) + 1
    return counts
```

Keep an explicit anti-softening assertion in the rewritten class: the old strip-and-join map must **differ** on the fixture (`strip_join_counts != reference_counts`), proving the fixture still exercises D2.

### `--compare-baseline` (skeleton)

```python
# Proposed additions to scripts/bench/python_bench.py
def parse_threads(text):
    return None if text == "default" else int(text)   # worker: None => PyCounter(threads=None)

def compare_to_baseline(baseline, new_doc):
    b = baseline["n_free_control"]["arms"][0]["medians"]["wall_s"]
    t1 = new_doc["control"]["arms"]["t1"]["medians"]["wall_s"]
    td = new_doc["control"]["arms"]["default"]["medians"]["wall_s"]
    speedup_t1, speedup_default = b / t1, b / td
    verdict = "PASS" if speedup_t1 >= 1.0 and speedup_default >= 1.2 else "FAIL"
    return {"baseline_wall_s": b, "new_t1_wall_s": t1, "new_default_wall_s": td,
            "speedup_t1": speedup_t1, "speedup_default": speedup_default,
            "min_speedup_t1": 1.0, "min_speedup_default": 1.2, "result": verdict}
```

Exit contract: `0` valid measurement and PASS; `1` valid measurement and FAIL (doc still written); `2` invalid (no doc). `invalid()` already exits 2; the controller must return `EXIT_COMPARISON_RESERVED` (currently `1`, `python_bench.py:82`) on FAIL. `[VERIFIED: scripts/bench/python_bench.py:81-83,513-679]`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Python::allow_threads` | `Python::detach` | PyO3 0.26.0 (deprecation); 0.27.2 ships it | `allow_threads` fails a `-D warnings` gate; both enforce `Ungil` (= `Send` on stable). |
| Sequential `lines()` loop + strip-and-join | `CountEngine::count_file` + `for_each_window` skip-N | Phase 7 (engine), Phase 9 (Python cutover) | Same counts/semantics as the CLI; strict parse errors. |
| Stable `sort_by_key` twice | `par_sort_unstable_by_key` once + sorted-input constructor | Phase 8 (sort mandate), Phase 9 (PyO3) | In-place pdqsort; no second sort / temporary buffer. |
| `from_kmer_pairs(sorted=true)` re-sorts | `from_sorted_kmer_pairs` trusts the caller | Phase 9 | Removes the double sort; caller proves order (debug assert + tests). |
| Extension version invisible | `m.add("__version__", …)` in `__all__` | Phase 9 | Stale-.so tripwire and three-way version drift check. |
| Benchmark "reserved exit 1" | `--compare-baseline` dev-host comparison | Phase 9 | Measured win, not asserted; CI baselines remain Phase 10. |

**Deprecated/outdated:**
- `Python::allow_threads` — deprecated since 0.26.0; do not use.
- `pyo3/tests/test_counter.py`'s pre-D2 parity classes and whitespace tests — they encode the behavior this phase changes.
- `scripts/bench/README.md`'s `python3 scripts/bench/n_read_differential.py` command — the system `python3` has no `pyrustkmer` (observed ImportError); use `.venv313/bin/python`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The committed dev-host baseline (M4 Max, 16 cores) is comparable on the current measurement host. | Benchmark | Numbers would be incomparable; mitigate with the `provenance.platform` guard and record the host class. |
| A2 | Re-provisioning the 1M-read slice + N-free filter reproduces the baseline control fingerprint (`5cc93333…`) and exact counts (`129579577/73476107`). | Benchmark | Comparison invalid; the command must assert both and exit 2 on mismatch. |
| A3 | The new engine reaches ≥1.2x over the baseline at default threads and is non-regressive at t1. | Measurement | If not, the phase records an honest RED (exit 1); the plan must not tune the threshold or recapture the baseline. |
| A4 | "Non-regressive" means `speedup >= 1.0` with no noise band. | Measurement | A noise band would need user approval; the locked wording is plain "non-regressive". |
| A5 | Scoping the Phase 8 whole-file blob pin to writer-function/byte proofs is acceptable (the alternative is a sibling-module constructor, which duplicates the header literal). | Critical Conflict | If the user insists the blob must not change, only the sibling-module option remains; that was not the locked choice. |
| A6 | Removing the pre-filter makes whitespace/other non-ACGT bytes in `add_sequence` break windows (not just N). | D2 / Pitfalls | If unintended, the scope must be narrowed to N only; the locked text says "removed everywhere". |
| A7 | The real-N benchmark arm's label/note must change for post-D2 runs while committed baselines stay immutable. | Benchmark | Otherwise new artifacts carry a false "pre-D2" label. |

## Open Questions

1. **Where do Phase 9 evidence artifacts live?**
   - What we know: prior phases used `pre/`, `post/`, and top-level evidence JSONs.
   - What's unclear: naming convention for this phase's differential/bench/byte-identity artifacts.
   - Recommendation: `.planning/phases/09-python-parity/evidence/` with explicit names (`n_read_differential_d2.json`, `python_bench_after_d2.json`, `pyo3_byte_identity.json`, `phase9_gates_evidence.json`).

2. **Should `n_read_differential.py` gain `--previous`, or should the before/after live in a separate phase artifact?**
   - What we know: the locked context says "The differential artifact additionally carries the exact before/after counts"; the script currently emits only the current run.
   - What's unclear: whether extending the script's schema is preferred over a wrapper artifact.
   - Recommendation: add an optional `--previous PATH` that validates k/canonical/case names and embeds a `before` block (per-case `cli`/`python` counts + totals); keep top-level `cases` as "after". This is small, testable, and keeps the evidence self-contained.

3. **`__version__` vs `PYRUSTKMER_VERSION`?**
   - What we know: both work with `m.add` (appends to `__all__`); the package currently has neither.
   - What's unclear: whether a dunder in `__all__` is acceptable to the project.
   - Recommendation: `__version__` (idiomatic), plus an assertion on the native submodule's attribute; do not add a second constant unless a consumer needs it.

4. **How should the t1 "non-regressive" verdict treat a CV warning?**
   - What we know: `reduce_arm` records `cv_warning` without failing.
   - What's unclear: whether a high-CV t1 measurement should be re-run before a FAIL verdict.
   - Recommendation: keep the single measured verdict; record CV; a FAIL is honest RED, never re-rolled until green.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust toolchain (MSRV) | clippy/build gates | ✓ | `1.82.0-aarch64-apple-darwin` installed; default is nightly 1.101 | Use `cargo +1.82.0` explicitly as Phase 7/8 did. |
| Cargo | build/test | ✓ | 1.101.0-nightly | — |
| Python + venv | pytest/bench | ✓ | `.venv313` → Python 3.13.11 | `.venv311` (3.11.14) also has maturin/pytest, but the committed Python baseline used `.venv313`. |
| maturin | extension rebuild | ✓ | 1.11.5 in `.venv313` | Homebrew maturin exists but would target the wrong interpreter; use the venv binary. |
| pytest | PyO3 tests | ✓ | 9.0.2 in `.venv313` | — |
| numpy | pyrustkmer runtime | ✓ | 2.4.1 in `.venv313` | — |
| `target/release/rustkmer` | CLI parity / byte identity | ✓ | present (2966832 bytes, built 2026-11-13) | `cargo build --release --locked`. |
| Benchmark source FASTQ | dev-host comparison | ✓ | `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz` (2.6 GB) | None — comparison requires these exact bytes; exit 2 if absent. |
| `mkdocs` + `section-index` plugin | docs site build | ✗ | mkdocs present, plugin missing (strict build exit 1) | File/nav/content grep gates instead. |

**Missing dependencies with no fallback:**
- The human-data source gz for the dev-host comparison; without it the benchmark comparison is exit 2 (invalid), not a skip.

**Missing dependencies with fallback:**
- `mkdocs build --strict` — replace with existence/nav/content greps.

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json`; this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Rust: `cargo test` (built-in, `--locked`); Python: pytest 9.0.2 in `.venv313`; harness: stdlib `unittest` discovery |
| Config file | `pyo3/pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`, `addopts = ["-v"]`); no Rust test config (defaults) |
| Quick run command | `cargo test --locked --test count_engine_tests --test output_pipeline_tests && python3 -m unittest discover -s scripts/bench/tests -t .` |
| Full suite command | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings && cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings && cargo build --release --locked && cargo test --locked && .venv313/bin/python -m pytest pyo3/tests -q` |

Current baselines (before Phase 9 changes): pytest `158 passed, 63 skipped`; harness `Ran 361 tests … OK (skipped=1)`. `[VERIFIED: session probes 2026-11-13]`

### Phase Requirements → Test Map

| Req ID / Criterion | Behavior | Test Type | Automated Command | File Exists? |
|--------------------|----------|-----------|-------------------|--------------|
| PY-01 #1 | `add_from_*` route through `CountEngine`; no sequential loop | static + integration | `grep -q "CountEngine::new" pyo3/src/counter.rs && grep -q "count_file(" pyo3/src/counter.rs && grep -q "merge_into" pyo3/src/counter.rs && ! grep -n "reader.lines()" pyo3/src/counter.rs` | ✅ source change |
| PY-01 #1 | Public `PyCounter` API unchanged | unit | new `test_public_api_frozen` pins the 12-name surface: `add_from_fasta, add_from_fastq, add_kmer, add_sequence, canonical, get_all_counts, get_count, get_stats, is_empty, kmer_length, reset, save_database` | ❌ Wave 0 |
| PY-01 #1 | `save_database` sorts once and uses the sorted constructor | static + unit | `test "$(grep -c 'par_sort_unstable_by_key' pyo3/src/counter.rs)" -eq 1 && ! grep -n "from_kmer_pairs\|sort_by_key" pyo3/src/counter.rs`; Rust `sorted_pairs_constructor_tests` | ❌ Wave 0 |
| PY-01 #1 | `save_database` bytes == CLI == committed golden; 1-vs-N invariant | integration | `.venv313/bin/python -m pytest pyo3/tests/test_save_database_byte_identity.py -q` | ❌ Wave 0 |
| PY-01 #2 | `py.detach` with owned Send captures | static + compile | `test "$(grep -c 'py.detach' pyo3/src/counter.rs)" -ge 3 && ! grep -n "allow_threads" pyo3/src/counter.rs`; pyo3 clippy `-D warnings` (Ungil bound) | ✅ source change |
| PY-01 #2 | No GIL deadlock under concurrent use | integration | `.venv313/bin/python -m pytest pyo3/tests/test_counter_concurrency.py -q` (threads + `future.result(timeout=…)`, exact counts) | ❌ Wave 0 |
| PY-01 #2 | Rebuilt + version-asserted before pytest | command gate | `maturin develop …` then `python -c "… assert pyrustkmer.__version__ == tomllib version …"`; `pyo3/tests/test_version.py` | ❌ Wave 0 |
| PY-02 #3 | D2 skip-N unified on all three inputs | unit | rewritten `TestPyCounterNReadSkipParity` (FASTA/FASTQ/sequence × k 21/64 × canonical) + `test_add_sequence_with_whitespace/newlines` updated | ✅ update existing |
| PY-02 #3 | Cross-surface divergence eliminated | differential | `.venv313/bin/python scripts/bench/n_read_differential.py --expect-unified --previous .planning/phases/05-measurement-regression-harness/n_read_differential.json --rustkmer target/release/rustkmer --out .planning/phases/09-python-parity/evidence/n_read_differential_d2.json` (exit 0) | ❌ `--previous` Wave 0 |
| PY-02 #3 | Docs state the change with numbers | docs gate | `test -f docs/user-guide/n-read-semantics.md && grep -q "n-read-semantics.md" mkdocs.yml && grep -qi "skip-N" docs/user-guide/n-read-semantics.md pyo3/README.md pyo3/src/counter.rs && grep -q "33" docs/user-guide/n-read-semantics.md` | ❌ Wave 0 |
| PY-02 #4 | Measured win vs Phase 5 baseline (t1 ≥1.0x, default ≥1.2x) | benchmark | `.venv313/bin/python scripts/bench/python_bench.py … --compare-baseline scripts/bench/baselines/python_bench_baseline.darwin.json` (exit 0; artifact validate) | ❌ Wave 0 |
| PY-02 #4 | Comparison exit contract (0/1/2) | harness unit | `python3 -m unittest discover -s scripts/bench/tests -t .` (new `TestCompareBaseline*`) | ❌ Wave 0 |
| Regression | Frozen writer bytes / goldens | golden | `cargo test --locked --test golden_sha256_tests --test golden_tests --test rkdb_v2_byte_identity_tests --test output_pipeline_tests` | ✅ existing |
| Regression | Manifests/lockfiles unchanged | command | `test -z "$(git diff --stat -- Cargo.toml Cargo.lock pyo3/Cargo.toml pyo3/Cargo.lock)"` | ✅ existing |

### Sampling Rate
- **Per task commit:** quick run command above; plus the task-specific pytest file when the task touches PyO3.
- **Per wave merge:** rebuild the extension + version assert + `pytest pyo3/tests -q` + harness unittest discovery.
- **Phase gate:** full suite (clippy both crates, release build, `cargo test --locked`, harness unittest, pytest), the four golden/output test binaries, the `--expect-unified` differential, the `--compare-baseline` benchmark, the byte-identity pytest, the concurrency pytest, and the frozen-writer scoped audit. All exit 0 (the benchmark/differential verdicts are genuine gates).

### Wave 0 Gaps
- [ ] `pyo3/tests/test_save_database_byte_identity.py` — CLI/Py/golden sha + 1-vs-N (covers PY-01 #1).
- [ ] `pyo3/tests/test_version.py` — stale-extension/version assert (PY-01 #2).
- [ ] `pyo3/tests/test_counter_concurrency.py` — concurrent `add_from_*` with timeout (PY-01 #2).
- [ ] `tests/sorted_pairs_constructor_tests.rs` — `from_sorted_kmer_pairs` byte equality (PY-01 #1).
- [ ] `scripts/bench/tests/test_python_bench.py` — `--compare-baseline` exit 0/1/2 cases and host/fingerprint guards (PY-02 #4).
- [ ] `scripts/bench/tests/test_n_read_differential.py` — `--previous` loading/validation + updated `EXPECTED_SEMANTICS` (PY-02 #3).
- [ ] `docs/user-guide/n-read-semantics.md` + `mkdocs.yml` nav + `docs/user-guide/index.md` link (PY-02 #3).
- [ ] `pyo3/README.md` migration note (PY-02 #3).
- [ ] No framework install needed; pytest/maturin/numpy already present in `.venv313`.

## Security Domain

> `workflow.security_enforcement` is `true`, ASVS level 1; block on high.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | No authentication surface (native library). |
| V3 Session Management | No | No sessions. |
| V4 Access Control | No | Caller supplies its own filesystem paths by design; no privilege boundary is crossed. |
| V5 Input Validation | Yes | Validate k (1..=64) at `PyCounter::new`; convert Python strings with `to_str()?`; surface FASTA/FASTQ parse errors as `PyValueError`; skip non-ACGT windows; reject `threads < 1`. |
| V6 Cryptography | No (integrity only) | SHA-256 is used for evidence/fingerprints, not as a security control; never hand-roll crypto. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Capturing a GIL-bound reference (`Bound<'_, T>`, `PyString`) across `py.detach` | Tampering / Elevation | Extract owned `String`/`Arc`/`usize` before detach; the `Ungil` (= `Send`) bound makes a violation a compile error. |
| Stale or shadowed native extension measured/tested | Tampering / Supply chain | Rebuild with `maturin develop --release`; assert `__version__` (absent on old builds) equals the manifest; record module path/sha256; the harness rejects modules outside site-packages. |
| Malformed FASTA/FASTQ causing panic/abort (release `panic = "abort"`) | Denial of service | bio strict readers; every error mapped to `ProcessingError` → `PyValueError`; no `unwrap`/`expect` in new binding paths. |
| Concurrent mutation during a `save_database` snapshot | Tampering | Document the snapshot as non-linearizable; `merge_local_counts` is documented concurrent-safe; concurrency test with timeout. |
| Benchmark/baseline manipulation | Repudiation / Tampering | Parity before timing; provenance (binary/module sha256, git commit/dirty, build profile); pinned baseline sha256; do not edit committed baselines; exit 1 is a real verdict. |
| Dependency/supply-chain drift | Tampering | No new packages; assert the four manifests/lockfiles are byte-unchanged. |

## Sources

### Primary (HIGH confidence)
- `src/count/engine.rs` — `EngineConfig` 225-240, `SequenceKind` 268-274, `merge_into` 505-510, `count_file` 780, `finish` 935, checked-reduction messages 83-90.
- `src/hash/table.rs` — `new_local_counts` 332, `local_skipped` 354, `merge_local_counts` 373-502, `get_all_counts` 588.
- `src/hash/local.rs` — `increment` 152-208 (verbatim overflow), `record_skipped` 214, `LocalHandleRegistry` 416-427.
- `src/database/format.rs` — `DatabaseHeader` 101-139 (IN-03 record count), `write_to` 179-207, `KmerEntry` 294-311, `RKDatabase` 402-406, `write_to` 558-570, `from_kmer_pairs` 640-673.
- `src/kmer/extract.rs` — `WindowSummary` 31, skip-N contract 51-56, `for_each_window` 90.
- `pyo3/src/counter.rs` — struct 106-114, `new` 133-212, `add_sequence` 282-326, `add_from_fasta` 346-377, `add_from_fastq` 397-422, `save_database` 445-489, legacy helpers 671-828.
- `pyo3/src/lib.rs` — `#[pymodule]` 37-55.
- `pyo3/Cargo.toml:22,50`; `Cargo.toml:23,57`; `pyo3/pyproject.toml:7,30`.
- `docs.rs/pyo3/0.27.2/pyo3/marker/struct.Python.html` — `detach` signature/bounds; `allow_threads` deprecated.
- `docs.rs/pyo3/0.27.2/pyo3/marker/trait.Ungil.html` — `impl<T: Send> Ungil for T`.
- `~/.cargo/registry/src/…/pyo3-0.27.2/src/types/module.rs:470-501` — `add` appends to `__all__`; `add_class` delegates to `add`.
- `~/.cargo/registry/src/…/bio-2.0.3/src/io/fastq.rs:249-285,495-509` — wrapped FASTQ support, inconsistent wrapping errors, iterator does not call `check()`.
- `~/.cargo/registry/src/…/bio-2.0.3/src/io/fasta.rs:316-340` — `record.seq.push_str(self.line.trim_end())`.
- Phase 8 plan/evidence: `.planning/phases/08-output-pipeline-rkdb-v2-parity/08-04-PLAN.md:147-160` (frozen blob pin); `phase8_gates_evidence.json` (manifest/lockfile blobs).
- Committed baseline: `scripts/bench/baselines/python_bench_baseline.darwin.json` (sha256 `42bb480d…`).
- Committed D2 evidence: `.planning/phases/05-measurement-regression-harness/n_read_differential.json` (sha256 `6d929a45…`).

### Secondary (MEDIUM confidence)
- `scripts/bench/README.md:157-203` — `.venv313` rebuild, PROF-04 command, Phase 9 `--expect-unified` re-run.
- `scripts/bench/python_bench.py` — `EXIT_COMPARISON_RESERVED` 82, `DEFAULT_PYTHON` 88, `measure_arm` 430-486, controller 513-679.
- `scripts/bench/n_read_differential.py` — `EXPECTED_SEMANTICS` 71-72, `evaluate` 158-197.
- `scripts/bench/bench.py` — `fingerprint` 268, `binary_provenance` 309, `validate_schema` 386, `reduce_arm` 1203.
- Session probes: `--expect-unified` RED (exit 1); byte-identity sha `a5da813e…`; pytest 158/63; unittest 361 OK (skipped=1); `mkdocs build --strict` exit 1 (missing `section-index`).

### Tertiary (LOW confidence)
- None relied upon for decisions. The ≥1.2x outcome and the baseline fingerprint reproduction are marked `[ASSUMED]` until measured.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every component/version read from the manifests and source this session; no new dependencies.
- Architecture: HIGH for engine routing, `merge_into`, `detach`/`Ungil`, `m.add`/`__all__`, writer/sort design, and byte identity (source + docs + executed probe); MEDIUM for the benchmark comparison outcome (unmeasured) and the Phase 8 blob-pin scoping interpretation (needs planner/user acknowledgment).
- Pitfalls: HIGH — the pre-D2 tests, the whitespace consequence, the rayon first-call-wins behavior, the strict-parser behavior, and the mkdocs failure were all observed in-repo.

**Research date:** 2026-11-13
**Valid until:** 2026-12-13 for the in-repo APIs; re-check the PyO3 docs only if the pin changes from 0.27.2.
