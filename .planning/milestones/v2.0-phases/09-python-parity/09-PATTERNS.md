# Phase 9: Python Parity - Pattern Map

**Mapped:** 2026-11-13
**Files analyzed:** 18 (3 modified/new Rust source, 7 tests, 4 harness scripts + 2 harness tests, 4 docs/config)
**Analogs found:** 18 / 18 (16 exact/role-match, 2 partial — see "No Analog Found")

**Source of file list:** `09-CONTEXT.md` (Decisions + Integration Points), `09-RESEARCH.md`
(Recommended Project Structure, Wave 0 Gaps, Code Examples).

## Corrections to the supplied file list

| Supplied as | Actual state | Consequence for the planner |
|---|---|---|
| NEW `scripts/bench/tests/test_python_bench.py` | **Already exists and is git-tracked** (570 lines, `TestNFreeFilter` … `TestRealWorkerIntegration`) | **MODIFY**: add new test classes for `--compare-baseline`; do not create a second file |
| MODIFY `docs/mkdocs.yml` | **`docs/mkdocs.yml` does not exist** (`ls` errors); only root `mkdocs.yml` exists | Edit root `mkdocs.yml` only; do not create a second config |
| NEW `scripts/bench/tests/test_n_read_differential.py` | Exists (266 lines) | MODIFY (as the context already says) |
| Not listed | `scripts/bench/README.md` is in the RESEARCH structure | MODIFY: `.venv313` command, compare mode, exit contract |

Also note: `pyo3/README.md:272` still declares "Current Version: 0.4.1" while the manifests say
`0.5.0`. That is pre-existing and **out of scope** — the Phase 9 migration note is a new
subsection under `## Migration Guide` (`pyo3/README.md:307`), not a version-history rewrite.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `pyo3/src/counter.rs` | binding / FFI service | file-I/O + batch pipeline + request-response | itself (existing `py.detach` methods) + `src/count/engine.rs` (target API) | exact |
| `pyo3/src/lib.rs` | module registration (config) | request-response (module init) | itself, lines 37-55 | exact |
| `src/database/format.rs` | model / binary serializer | file-I/O + transform | itself, `from_kmer_pairs` lines 640-673 | exact |
| `pyo3/tests/test_counter.py` | test (PyO3 behavior) | request-response | itself, `TestPyCounterRollingPathParity` / `TestPyCounterNReadPreFilterParity` | exact |
| `pyo3/tests/test_public_api.py` | test (API-surface pin) | request-response | `pyo3/tests/test_core.py:166-180` `TestModuleCompleteness` | role-match |
| `pyo3/tests/test_save_database_byte_identity.py` | test (cross-surface integration) | file-I/O | `tests/rkdb_v2_byte_identity_tests.rs` + `tests/output_pipeline_tests.rs` + `pyo3/tests/test_export.py:507-549` | role-match |
| `pyo3/tests/test_version.py` | test (build tripwire) | request-response | `pyo3/tests/test_core.py:166-180` (availability asserts) — no version precedent | partial |
| `pyo3/tests/test_counter_concurrency.py` | test (concurrency) | event-driven (threads) | `scripts/bench/tests/test_verify_threads.py:263-284` (threads + timeout) — no PyO3 precedent | partial |
| `tests/sorted_pairs_constructor_tests.rs` | test (Rust integration) | transform + file-I/O | `tests/output_pipeline_tests.rs` + `tests/rkdb_v2_byte_identity_tests.rs` | exact |
| `scripts/bench/python_bench.py` | harness controller (CLI tool) | batch (fresh-worker benchmark) | itself + `scripts/bench/compare.py` (exit contract) + `scripts/bench/thread_scaling.py:126-208` (verdict) | exact |
| `scripts/bench/n_read_differential.py` | harness (differential) | batch | itself, `run_differential` / doc shape | exact |
| `scripts/bench/tests/test_python_bench.py` | test (harness unit) | request-response | itself, `ControllerHarness` lines 361-414 | exact |
| `scripts/bench/tests/test_n_read_differential.py` | test (harness unit) | request-response | itself, `ImplementedGate` lines 28-34 | exact |
| `scripts/bench/README.md` | docs | — | itself (exit-contract / Phase 9 sections) | role-match |
| `docs/user-guide/n-read-semantics.md` | docs (semantics page) | — | `docs/user-guide/error-recovery.md` (behavior + code blocks) | role-match |
| `mkdocs.yml` | config (nav) | — | itself, `nav:` lines 43-58 | exact |
| `docs/user-guide/index.md` | docs (index) | — | itself, "Guide Overview" bullets lines 5-10 | exact |
| `pyo3/README.md` | docs (migration note) | — | itself, `## Migration Guide` lines 307-330 | exact |

---

## Pattern Assignments

### `pyo3/src/counter.rs` (binding, file-I/O + batch pipeline)

**Analog:** itself — the existing `add_from_fasta` / `add_from_fastq` detach methods
(`pyo3/src/counter.rs:346-422`); the target core API is `src/count/engine.rs`.

**Imports pattern** (current lines 6-14; add the engine + rayon lines):

```rust
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rustkmer::hash::KmerCounter as RustPyCounter;
use rustkmer::hash::LocalKmerCounts;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use rustkmer::kmer::extract::{for_each_window, WindowError};
use std::path::Path;
use std::sync::Arc;

// Phase 9 additions — both re-exported/available to this crate:
use rayon::prelude::*;                       // pyo3/Cargo.toml:50 rayon = "1.8"
use rustkmer::count::{CountEngine, EngineConfig, SequenceKind}; // src/count/mod.rs re-exports
```

**The GIL-release + owned-`Send` pattern to copy verbatim** (lines 346-377, FASTA; FASTQ is the
same shape at 397-422):

```rust
fn add_from_fasta(
    &self,
    py: Python<'_>,
    file_path: &Bound<'_, pyo3::types::PyString>,
) -> PyResult<()> {
    // CRITICAL (T-02-11 / Pitfall 4): extract ALL Python arguments into
    // owned, `Send` Rust types BEFORE entering the detach closure.
    let path_str = file_path.to_str()?.to_owned();
    let counter = self.counter.clone();

    py.detach(move || process_fasta_file_on_counter(&counter, &path_str))
        .map_err(|e: rustkmer::ProcessingError| {
            PyErr::new::<PyValueError, _>(format!("Failed to process FASTA: {}", e))
        })
}
```

**Target engine API — exact signatures** (`src/count/engine.rs`):

```rust
// EngineConfig::new(k, canonical, threads, initial_capacity) — engine.rs:254-264
// CountEngine::new(config) -> ProcessingResult<Self>  — engine.rs:598
// count_file(&mut self, path: &Path, kind: SequenceKind) -> ProcessingResult<FileStats> — engine.rs:780
// finish(self) -> ProcessingResult<CountResult> — engine.rs:935
// CountResult::merge_into(&self, counter: &KmerCounter) -> ProcessingResult<()> — engine.rs:505-510
// SequenceKind::{Fasta, Fastq} — engine.rs:268-274
```

**Per-call engine helper** (replaces `process_fasta_file_on_counter` / `process_fastq_file_on_counter`,
lines 707-763 / 776-828):

```rust
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
        0, // locked: initial_capacity = 0; the persistent counter holds capacity
    );
    let mut engine = CountEngine::new(config)?;
    engine.count_file(Path::new(path), kind)?;
    engine.finish()?.merge_into(counter)?;
    Ok(())
}
```

Note: `CountResult::merge_into` is documented in-repo as "the Phase 9 PyO3 bridge"
(`src/count/engine.rs:488-494`) and reuses `merge_local_counts` (checked per-key `u32` sums).
Parse/open errors return before `merge_into`, so the shared counter is unchanged on failure —
preserve and test that property.

**New private `threads` field + struct pattern** (struct at lines 105-114):

```rust
#[pyclass(name = "PyCounter")]
pub struct PyCounter {
    /// Internal Rust counter, `Arc` so it can move into `py.detach` closures.
    counter: Arc<RustPyCounter>,
    /// Phase 9: resolved thread count. `KmerCounter::new` DISCARDS its
    /// `_num_threads` argument (`src/hash/table.rs:143,163`), so the binding
    /// must remember the value it resolved here (`resolved_threads`,
    /// `pyo3/src/counter.rs:171-175`) to size the per-call `EngineConfig`.
    threads: usize,
}
```

`new` already computes `resolved_threads` (lines 171-175) and passes it to
`RustPyCounter::new` (line 201-206) where it is unused; store it in `Ok(Self { counter, threads: resolved_threads })`.
A private field is invisible to Python and does not change the constructor signature.

**D2: remove the non-ACGT pre-filter in `add_sequence`** (current lines 286-297, the
`cleaned: Vec<u8>` filter). Replace with the raw bytes so the shared extractor owns skip-N:

```rust
// Current (lines 294-297) — REMOVE:
let cleaned: Vec<u8> = seq_str
    .bytes()
    .filter(|&b| matches!(b.to_ascii_uppercase(), b'A' | b'C' | b'G' | b'T'))
    .collect();

// Current (line 309) — keep the extractor call, feed raw bytes:
for_each_window(seq_str.as_bytes(), k, self.counter.canonical_mode(), |value| {
    self.counter.increment(value).map_err(|e| { /* unchanged lines 310-312 */ })
})
```

`for_each_window` skip-N contract quote (`src/kmer/extract.rs:51-56`): "Any window containing a
byte outside `A`, `C`, `G`, `T` (case-insensitive) is skipped and counted … every call starts
fresh, so no window spans a record boundary." This is why whitespace now breaks windows
(RESEARCH Pitfall 3) — document, do not special-case.

**`save_database`: sort once, write through the frozen writers, GIL released** (current lines 445-489).

Analog for the sort+write shape: Phase 8 `output_binary_format`, `src/cli/commands/count.rs:429-512`,
and `sort_pairs_ascending`, `src/cli/commands/count.rs:346-360`:

```rust
// count.rs:358-360 — the existing sort analog. RESEARCH mandates the _by_key form
// for the binding; no `par_sort_unstable_by_key` exists in the tree yet.
fn sort_pairs_ascending(pairs: &mut [(u128, u32)]) {
    pairs.par_sort_unstable_by(|(a, _), (b, _)| a.cmp(b));
}
```

```rust
// count.rs:455-505 — writer skeleton the binding mirrors (sort, BufWriter,
// header.write_to, KmerEntry::write_to loop, explicit flush).
let file = std::fs::File::create(output_path)...;
let mut writer = std::io::BufWriter::new(file);
header.write_to(&mut writer)...;
for &(kmer, count) in kmers.iter() {
    KmerEntry::new(kmer, count).write_to(&mut writer)?;
}
writer.flush()...;   // "a failed final write must never be silent (T-08-04)"
```

**Do not copy** count.rs's inline `DatabaseHeader { .. }` literal (lines 468-479). The binding must
call the new `format.rs` constructor (single-writer rule). The detach shape:

```rust
fn save_database(&self, py: Python<'_>, file_path: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
    let path_str = file_path.to_str()?.to_owned();
    let counter = self.counter.clone();
    py.detach(move || save_database_on_counter(&counter, &path_str))
        .map_err(|e| /* match on the Send error enum -> the four existing messages */)
}
```

`PyErr` cannot be constructed without the GIL, so the closure returns a private, `Send` error enum
(`Empty` / `Database(String)` / `CreateFile(String)` / `Write(String)`) mapped after `detach`.
Precedent that a Rust error type is a legal detach return: `ProcessingError` is returned from the
existing closures (`counter.rs:373-376`); it is `String` + `Option<anyhow::Error>`, both `Send`
(`src/error.rs:63-77`). `Arc<KmerCounter>: Send` is already proven by the same closures.

**Error strings that must survive verbatim** (asserted by `pyo3/tests/test_counter.py:789, 798`):

```rust
"Cannot save empty database. Add k-mers first."   // current line 457-459
"Failed to create database: {e}"                  // line 474-476
"Failed to create file: {e}"                      // line 479-480
"Failed to write database: {e}"                   // line 484-486
```

Also remove the now-dead local `DatabaseHeader::new` call at line 471.

---

### `src/database/format.rs` (model / binary serializer)

**Analog:** `from_kmer_pairs`, same file, lines 639-673. Copy this body and change exactly two
things: no sort, and `sorted: true`.

```rust
// lines 640-673 (verbatim reference)
pub fn from_kmer_pairs(
    kmer_pairs: Vec<(u128, u32)>,
    kmer_size: u8,
    canonical: bool,
    sorted: bool,
) -> crate::error::ProcessingResult<Self> {
    let mut entries: Vec<KmerEntry> = kmer_pairs
        .into_iter()
        .map(|(kmer, count)| KmerEntry::new(kmer, count))
        .collect();

    if sorted && !entries.is_empty() {
        entries.sort_by_key(|entry| entry.kmer);
    }

    let header = DatabaseHeader {
        magic: *crate::database::format::DATABASE_MAGIC,
        version: crate::database::format::DATABASE_VERSION,
        kmer_size,
        total_kmers: entries.len() as u64,
        canonical,
        sorted,
        data_offset: 42, // Standard header size for version 2
        index_offset: 0,
        unique_kmers: entries.len() as u64,
        file_size: 0, // Will be calculated when writing
    };

    Ok(Self { header, entries, file_path: None })
}
```

New constructor (name is Claude's discretion; RESEARCH proposes `from_sorted_kmer_pairs`):

- body identical except **no `entries.sort_by_key`** and `sorted: true`;
- a `debug_assert!(kmer_pairs.windows(2).all(|w| w[0].0 <= w[1].0), ...)` documenting the
  caller-proves-order contract (note: `debug_assert` is compiled out in `--release`, so the
  byte-equality tests — not the assert — are the gate);
- place it **immediately after `from_kmer_pairs`** and add doc comment only → the Phase 8
  frozen-`format.rs` audit becomes "`git diff -U0` has no removed lines".

Do **not** touch: `DatabaseHeader::write_to` (179-207), `KmerEntry::write_to` (308-311),
`RKDatabase::write_to` (558-570), `from_kmer_pairs` itself. `RKDatabase` fields are `pub`
(402-406) but the PyO3 crate must not build a header (single-writer rule).

---

### `pyo3/src/lib.rs` (module registration)

**Analog:** itself, `#[pymodule]` lines 37-55.

```rust
#[pymodule]
fn pyrustkmer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDatabase>()?;
    /* ... 15 add_class calls ... */
    m.add_class::<RustKmerError>()?;
    // Phase 9: m.add appends the name to __all__, which the maturin shim
    // star-imports, so `pyrustkmer.__version__` exists on rebuilt wheels only.
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
```

The attribute is the stale-`.so` tripwire: old builds have no `__version__`. Expected value source
is `pyo3/Cargo.toml:3` (`0.5.0`), mirrored by `pyo3/pyproject.toml:7`.

---

### `pyo3/tests/test_counter.py` (test rewrite, not extension)

**Analog:** itself. Keep the file's conventions exactly.

**Module guard** (lines 10-13) — every new PyO3 test file copies this:

```python
try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)
```

**Rewrite targets (pre-D2 behavior, must be rewritten — RESEARCH Pitfall 4):**

| Lines | Current behavior pinned | Required replacement |
|---|---|---|
| 138-148 | `test_add_sequence_with_whitespace` / `_with_newlines` assert the flank-join (`"ACG TACG ACGT"` → `ACGTACG`) | Assert skip-N: a whitespace-containing window is skipped; for k=7 `add_sequence("ACG TACG ACGT")` yields only windows free of the space (here `is_empty()`), and `get_count("ACGTACG") == 0` |
| 1176-1261 | `TestPyCounterRollingPathParity._clean` strips non-ACGT before building the reference | Keep the class/parametrization; change `_clean`/`_reference_counts` to the skip-N reference below |
| 1264-1396 | `TestPyCounterNReadPreFilterParity` — pure-Python strip-and-join reference, asserts N-reads match the OLD semantics | Convert to `TestPyCounterNReadSkipParity`: same fixtures (`N_READS`, `N_SEQUENCES`), reference excludes any window containing a non-ACGT byte; add the anti-softening assertion (`strip_join_counts != reference_counts`) so it cannot pass with the old filter |

**Skip-N pure-Python reference** (from RESEARCH "Code Examples", adapted to the file's helper style):

```python
@classmethod
def _reference_counts(cls, sequences, k, canonical):
    """A window is emitted only if it contains no non-ACGT byte."""
    counts = {}
    for raw_sequence in sequences:
        sequence = raw_sequence.upper()
        for i in range(len(sequence) - k + 1):
            kmer = sequence[i : i + k]
            if any(base not in "ACGT" for base in kmer):
                continue
            if canonical:
                kmer = min(kmer, cls._revcomp(kmer))
            counts[kmer] = counts.get(kmer, 0) + 1
    return counts
```

**Assertion style to keep** (lines 1348-1355): exact `get_all_counts() == expected`, then
`stats.total_kmers == sum(expected.values())` and `stats.unique_kmers == len(expected)`, with an
f-string failure message naming the phase marker. The drop in `total_kmers` on N input is the
documented consequence — assert the NEW totals, never preserve the old total.

---

### `pyo3/tests/test_public_api.py` (test, API freeze)

**Analog:** `pyo3/tests/test_core.py:166-180`:

```python
class TestModuleCompleteness:
    """Test that all expected classes exist."""

    def test_core_classes_available(self):
        """Test that all core classes are available."""
        import pyrustkmer

        assert hasattr(pyrustkmer, "PyDatabase")
        ...
```

Pin the 12-name `PyCounter` surface (RESEARCH validation map): `add_from_fasta, add_from_fastq,
add_kmer, add_sequence, canonical, get_all_counts, get_count, get_stats, is_empty, kmer_length,
reset, save_database`. Filter dunders (`not name.startswith("_")`) so `__repr__`/`__class__`
don't matter, and assert **equality** on the public set rather than `hasattr` so a *new* method
also fails (the API is frozen in both directions). Use the module guard from `test_counter.py:10-13`.

---

### `pyo3/tests/test_save_database_byte_identity.py` (test, cross-surface integration)

**Analogs:**
- golden anchor + six-sequence input: `tests/output_pipeline_tests.rs:29-43`
- CLI-vs-reference sha arms: `tests/rkdb_v2_byte_identity_tests.rs:1-39`
- subprocess CLI call from pytest: `pyo3/tests/test_export.py:510-547`

```python
# tests/output_pipeline_tests.rs:32-43 — the literal input + golden sha to reuse
GOLDEN_INPUT = [
    "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
    "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
    "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
    "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
]
GOLDEN_K21_CANON_SORTED_SHA256 = (
    "a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7")
```

```python
# pyo3/tests/test_export.py:522-526 — subprocess shape (do NOT rely on PATH like this;
# resolve REPO_ROOT / "target" / "release" / "rustkmer" and pytest.skip if absent)
result = subprocess.run(
    ["rustkmer", "dump", tiny_db_path, "--output", str(cli_output)],
    capture_output=True, text=True,
)
assert result.returncode == 0
```

Test arms (RESEARCH "Cross-surface byte identity"): write the six sequences as FASTA, then
`PyCounter.save_database` (threads=1, threads=4/default) and `rustkmer count -k 21 -C --threads N`
must all hash to `a5da813e…` **and** to `tests/fixtures/golden_k21_canon_sorted.rkdb`. Assert the
1-vs-N invariant (t1/t4/default all equal) and re-assert the empty-counter `ValueError`.

---

### `pyo3/tests/test_version.py` (test, stale-extension tripwire)

**Analog:** none for version assertions; nearest is the availability-assert style in
`pyo3/tests/test_core.py:166-180`. Use the RESEARCH snippet verbatim:

```python
import pathlib, tomllib
import pyrustkmer  # module-level import fails loudly if the extension is absent

REPO = pathlib.Path(__file__).resolve().parents[2]
expected = tomllib.loads((REPO / "pyo3" / "pyproject.toml").read_text())["project"]["version"]
assert getattr(pyrustkmer, "__version__", None) == expected, (
    "stale or mismatched extension: %r != %r — rebuild with maturin develop --release"
    % (getattr(pyrustkmer, "__version__", None), expected)
)
```

Deliberate divergence from the other test files: **no skip guard** — an absent/old extension must
fail here, not skip (that is the point of the tripwire). `parents[2]` from
`pyo3/tests/test_version.py` is the repo root. Also record `pyrustkmer.__file__` in the message.

---

### `pyo3/tests/test_counter_concurrency.py` (test, concurrency)

**Analog:** no PyO3 concurrency test exists. Nearest threading/timeout discipline:
`scripts/bench/tests/test_verify_threads.py:263-284` (daemon `threading.Thread` + bounded wait).

Requirements from RESEARCH Pitfall 8 / validation map:
- `concurrent.futures.ThreadPoolExecutor` with several `add_from_fastq` / `add_from_fasta` calls
  on distinct temp files;
- every future collected with `future.result(timeout=…)` so a deadlock fails the suite instead
  of hanging it;
- exact per-thread and aggregate counts (no "non-empty" assertions);
- construct one counter per thread or one shared counter — the shared path is the interesting one
  because `merge_local_counts` documents concurrent merges as safe (`src/hash/table.rs:373-380`);
- do not assert linearizability of a concurrent `save_database` snapshot (RESEARCH: safe but
  not linearizable — do not promise atomicity).

Beware the global-pool first-call-wins behavior (Pitfall 6): do not mix `threads=1` and
`threads=None` counters in one test expecting different pools; the pool is process-global.

---

### `tests/sorted_pairs_constructor_tests.rs` (Rust integration test)

**Analog:** `tests/output_pipeline_tests.rs` (helpers) + `tests/rkdb_v2_byte_identity_tests.rs`
(sha arms, fixture guarding).

Copy the import block (`tests/output_pipeline_tests.rs:21-27`) and helpers
(`write_fasta` 46-52, `golden_fasta` 55-59, `sha256_hex` 61-65):

```rust
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use rustkmer::kmer::encoding::{decode_kmer_u128, encode_kmer_bytes_u128};
use sha2::{Digest, Sha256};
```

`sha2` and `tempfile` are **production** deps of the root crate (`Cargo.toml:77,92`), so a
`tests/*.rs` binary can use them without a manifest change (and the manifests must stay
byte-identical).

Required assertions:
1. `from_sorted_kmer_pairs(pairs, k, canonical)` emits bytes identical to
   `from_kmer_pairs(pairs_sorted, k, canonical, true)` — compare `Vec<u8>` via `write_to` into a
   `Vec<u8>` (or `Cursor`), and via `TempDir` files.
2. Empty input and single-entry input.
3. The k21/canonical case equals `tests/fixtures/golden_k21_canon_sorted.rkdb`
   (sha `a5da813e…`) and the header's `sorted == true` / `total_kmers == entries.len()` (IN-03).
4. Order is trusted, not fixed: a caller-supplied ascending vector is written in that order; the
   header's sorted flag must not be set for an unsorted input (do not call this constructor there).
5. If testing the `debug_assert`, gate it with `#[cfg(debug_assertions)]` — `cargo test --release`
   would not panic.

Doc-comment style: a `//!` header that states what the binary observes and what it does not
(see `tests/golden_sha256_tests.rs:13-39` for the table format). Note `tests/*.rs` are separate
binaries, so helpers are deliberately duplicated (`tests/golden_sha256_tests.rs:80-83`).

---

### `scripts/bench/python_bench.py` (harness controller)

**Analog:** itself (fresh-worker protocol) + the two verdict scripts.

**Exit contract and helpers to extend** (lines 81-114):

```python
EXIT_OK = 0
EXIT_COMPARISON_RESERVED = 1  # Phase 9 baseline-comparison mode; never used here
EXIT_INVALID = 2
...
def invalid(message):
    """Print an input/infra problem and exit 2 — never a measurement."""
    print(f"python_bench.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)
```

**Verdict pattern to copy** — `scripts/bench/thread_scaling.py:126-208` (`scaling_verdict`):
validate schema + provenance first, return `(exit_code, lines, verdict_block)` with
`verdict_block is None` on every exit-2 path, inclusive threshold boundaries, and a
machine-greppable verdict line (211-216). `compare.py:104-120` supplies the platform-flavor
normalization to copy for the host guard; `compare.py:238-247` shows the mismatch → exit 2 shape.

**Places that must change:**
- worker: line 411 hardcodes `threads=1` (`pyrustkmer.PyCounter(args.k, canonical=True, threads=1)`)
  → accept `--threads default|N` (`parse_threads`: `None` for `"default"`);
- `measure_arm`: line 476 hardcodes `"threads": 1`; emit the actual config;
- control block: lines 609-623 currently build one arm (`arms = [control_arm]`); compare mode
  needs both `py{k}-n-free-control-t1` and `py{k}-n-free-control-tdefault`;
- `params` (632-640) must record `threads_default`, `compare_baseline`, `reps`, python, rustkmer;
- controller returns `EXIT_COMPARISON_RESERVED` (1) on a valid FAIL, writes the doc on 0 and 1,
  never on 2 (`invalid()` already exits 2);
- `write_json` (501-510) validates schema + provenance before writing — reuse; the comparison doc
  keeps measured arms under `arms` so `validate_schema` stays clean (it tolerates extra keys).

**Baseline contract to hard-code as guards** (from the committed file):

```python
# scripts/bench/baselines/python_bench_baseline.darwin.json
baseline["platform"] == "darwin"                       # flavor
baseline["provenance"]["platform"] == f"{sys.platform}-{platform.machine()}"
baseline["n_free_control"]["arms"][0]["medians"]["wall_s"] == 32.14
baseline["n_free_control"]["exact_counts"] == {"total_kmers": 129579577,
                                               "unique_kmers": 73476107}
baseline["n_free_control"]["input_fingerprint"]["sha256"] == "5cc93333..."
```

Comparison math (locked): `speedup_t1 = 32.14 / new_t1`, `speedup_default = 32.14 / new_default`;
PASS iff `speedup_t1 >= 1.0` **and** `speedup_default >= 1.2`. Parity and exact-count equality
are asserted BEFORE timing; either failing is exit 2 (invalid/correctness), never exit 1.
`parity_counts` (239-258) is the ready-made CLI-vs-Python gate.

Also update the stale real-N labels (`REAL_N_EVIDENCE_CLASS`, `REAL_N_SEMANTICS_NOTE`, lines
97-102) to post-D2 wording (Pitfall 13) — committed baselines are immutable, in-code labels are not.

---

### `scripts/bench/n_read_differential.py` (harness, differential)

**Analog:** itself. Shapes to preserve: exit codes 62-64, `invalid()` 76-79, `evaluate` 158-197,
doc shape 257-281, `main` 296-311.

Changes:
- `EXPECTED_SEMANTICS` (71-72) → `{"cli": "skip-N-windows", "python": "skip-N-windows"}`;
- module docstring 14-17 ("record-only … neither surface's semantics is changed") and the
  argparse description (298-299) must say Phase 9 landed the change;
- new `--previous PATH` (optional): load a prior artifact, validate `k`, `canonical`, and case-name
  set match `build_cases()` (92-115), then embed a `before` block of per-case
  `{cli: {distinct,total}, python: {distinct,total}}` + totals. Keep top-level `cases` as "after".
  Validate-before-embed follows the `compare.py::load_results` habit (82-101): unreadable/malformed
  prior = `ValueError` → exit 2.
- The committed before/after numbers to state (RESEARCH Pattern 5): Python nine-case total
  70 → 37, CLI 37, 33 chimeric keys eliminated; per-case table is in the RESEARCH doc.

---

### `scripts/bench/tests/test_python_bench.py` (MODIFY — harness unit tests)

**Analog:** itself. Classes are one behavior each; controller tests go through
`ControllerHarness` (lines 361-414) with `mock.patch.object(pb, ...)` and `run_main(argv)`
returning `(code, stdout, stderr)`; fixtures `make_fake_measure`, `make_rep`, `make_arm`,
`make_doc`, `make_control` (45-133) already model every doc block.

Add (mirroring `scripts/bench/tests/test_thread_scaling.py:130-228` `TestVerdictMatrix`):
- a pure verdict-function matrix: PASS (t1 ≥ 1.0, default ≥ 1.2), FAIL on t1 regression,
  FAIL on default < 1.2, threshold-equality PASS, one-ULP-below FAIL;
- exit-2 guards: platform mismatch, k/canonical mismatch, control fingerprint mismatch,
  exact-count mismatch, missing baseline file, unparsable baseline;
- controller: exit 1 writes the doc with `verdict.exit_code == 1`; exit 2 writes nothing;
- assert `validate_schema` + `validate_provenance` on the comparison doc.

---

### `scripts/bench/tests/test_n_read_differential.py` (MODIFY — harness unit tests)

**Analog:** itself. Keep the guarded import + `ImplementedGate.require()` pattern (17-34) and the
pure-helper class style (36-90).

Add a `TestPreviousLoading` class: valid prior embeds the `before` block; k mismatch raises;
canonical mismatch raises; missing/extra case name raises; malformed JSON raises (all mapped by
the caller to exit 2). Update any assertion that pins `EXPECTED_SEMANTICS` to the new unified text.

---

### `scripts/bench/README.md` (docs)

**Analog:** itself. Sections to update: the exact rebuild command block (161-166), the Phase 9
`--expect-unified` re-run block (199-203, whose `python3` is known-broken — must become
`.venv313/bin/python`, RESEARCH "Deprecated/outdated"), the exit-contract section (223-240), and
the baseline/comparison section (287, 316-360) with the new `--compare-baseline` mode.

---

### `docs/user-guide/n-read-semantics.md` (docs, user-visible change)

**Analog:** `docs/user-guide/error-recovery.md` — plain Markdown, starts with a `#` H1, `##`
sections, fenced code blocks, no front matter and no `!!!` admonitions (grep over
`docs/user-guide/*.md` finds none). `docs/user-guide/counting-kmers.md:1-30` shows the
table-of-contents-at-top habit.

Must contain (validation map gate greps for `skip-N` and `33`):
- what skip-N means: any length-k window containing a non-ACGT byte is skipped and never counted;
- the exact before/after evidence: nine-case Python total **70 → 37** (CLI 37), **33 chimeric
  k-mers eliminated**, `control_no_n` unchanged at 2/10;
- `total_kmers` drops on N-containing input by design (WR-04: never silent);
- whitespace/other non-ACGT bytes break windows in `add_sequence` (Pitfall 3 / A6);
- the stricter `bio` FASTA/FASTQ parser and that malformed input raises `ValueError` with context;
- no new API: there is no Python-visible skipped counter (Pitfall 2).

---

### `mkdocs.yml` (config, nav)

**Analog:** itself, `nav:` lines 43-58. Insert after the Counting entry (`mkdocs.yml:52`):

```yaml
  - User Guide:
    - user-guide/index.md
    - Counting k-mers: user-guide/counting-kmers.md
    - N-read Semantics: user-guide/n-read-semantics.md   # Phase 9 addition
```

Do not gate on `mkdocs build --strict`: the installed environment lacks `section-index`
(RESEARCH Pitfall 11). Use file-existence + nav-grep + content-grep instead.

---

### `docs/user-guide/index.md` (docs, index link)

**Analog:** itself, "Guide Overview" (lines 5-10):

```markdown
- **[Counting k-mers](counting-kmers.md)** - Complete guide to k-mer counting operations
- **[Querying Databases](querying.md)** - Database operations and querying strategies
- **[Fuzzy Search](fuzzy-search.md)** - Pattern matching and advanced search techniques
- **[Performance Tips](performance-tips.md)** - Optimization strategies and best practices
```

Add one bullet: `- **[N-read Semantics](n-read-semantics.md)** - How non-ACGT bases affect counts`.

---

### `pyo3/README.md` (docs, migration note)

**Analog:** itself, `## Migration Guide` (lines 307-330), which uses an old-vs-new subsection per
version. Add a new subsection (under the existing guide, not a new top-level section):

- Python counting now skips windows containing any non-ACGT byte (D2), matching the CLI;
- exact numbers: the differential fixture's Python total drops 70 → 37, 33 chimeric k-mers gone;
- `total_kmers` is therefore smaller on N-containing reads;
- whitespace/other non-ACGT bytes break windows (no more strip-and-join);
- FASTA/FASTQ parsing is now strict `bio` parsing; malformed input raises `ValueError`;
- `pyrustkmer.__version__` now exists (rebuild with the documented `.venv313` / `unset
  CONDA_PREFIX` command, lines 36-44).

---

## Shared Patterns

### GIL release with owned `Send` captures
**Source:** `pyo3/src/counter.rs:351-376` and `402-421`
**Apply to:** every new or changed `add_from_*` / `save_database` method

```rust
let path_str = file_path.to_str()?.to_owned(); // owned String
let counter = self.counter.clone();            // Arc<KmerCounter>
py.detach(move || helper(&counter, &path_str))
```

Never capture `Bound<'_, _>` / `PyString` / `PyErr` across `detach`; `Ungil == Send` on stable
makes a violation a compile error. `Python::allow_threads` is deprecated since PyO3 0.26 and fails
the `-D warnings` clippy gate.

### Error → `PyValueError` mapping (messages are the contract)
**Source:** `pyo3/src/counter.rs:374-376`, `419-421`, `456-486`; asserted by
`pyo3/tests/test_counter.py:784-800`
**Apply to:** all binding methods

```rust
.map_err(|e: rustkmer::ProcessingError| {
    PyErr::new::<PyValueError, _>(format!("Failed to process FASTA: {}", e))
})
```

Keep `RustKmerError` (`pyo3/src/errors.rs:9-42`) untouched as the custom exception type.

### Exact counts, never "non-empty"
**Source:** `pyo3/tests/test_counter.py:1348-1355`, `scripts/bench/python_bench.py:209-236`
**Apply to:** every rewritten/new counting test

Compare full decoded count maps and assert `total_kmers == sum(map.values())` and
`unique_kmers == len(map)`; a zero/invalid count is a failure, never a skip.

### Cross-surface parity on the same bytes
**Source:** `scripts/bench/n_read_differential.py:200-224`, `scripts/bench/python_bench.py:239-258`
**Apply to:** D2 proof and the benchmark control

CLI `count` and Python `add_from_fastq` are run on identical temp bytes; the CLI map is read back
via `PyDatabase(..., LoadMode.Preload).export_all_kmers()` — never a second decoder.

### Golden sha256 anchoring
**Source:** `tests/output_pipeline_tests.rs:41-43,61-65`; `tests/golden_sha256_tests.rs:106-110`
**Apply to:** `tests/sorted_pairs_constructor_tests.rs`, `test_save_database_byte_identity.py`

```rust
fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}
```

Goldens are ground truth, never regenerated (`tests/golden_sha256_tests.rs:29-31`).

### Exit-code contract 0 / 1 / 2
**Source:** `scripts/bench/compare.py:9-23`, `scripts/bench/thread_scaling.py:83-97,126-208`,
`scripts/bench/n_read_differential.py:62-79`
**Apply to:** `python_bench.py --compare-baseline`, `n_read_differential.py --previous`

0 = valid + PASS; 1 = valid measurement whose verdict is FAIL (artifact still written); 2 =
invalid measurement (no artifact). Never convert 1 to 0, never best-effort-parse inputs.

### Params/provenance blocks in artifacts
**Source:** `scripts/bench/python_bench.py:489-498,632-667`; `scripts/bench/bench.py:386-417`
**Apply to:** both new artifact shapes

Every doc carries `schema_version`, `params`, `created` (UTC ISO), `provenance` (binary + module
sha256 + git commit/dirty + platform) and is passed through `validate_schema` +
`validate_provenance` before write.

### Version synchronization
**Source:** `pyo3/pyproject.toml:7`, `pyo3/Cargo.toml:3`, `Cargo.toml:3` (all `0.5.0`)
**Apply to:** `test_version.py`, the plan's pre-pytest command

The test asserts the **installed extension** against `pyproject.toml`; the plan must not bump any
version, and the four manifests/lockfiles must stay byte-identical.

---

## No Analog Found

Files/patterns with no close existing match; the planner should use the RESEARCH.md designs
directly.

| File / pattern | Role | Data Flow | Reason |
|---|---|---|---|
| `pyo3/tests/test_version.py` | test | request-response | The package has no `__version__` today and no test asserts a build version. Use the RESEARCH snippet; only the availability-assert style (`test_core.py:169-190`) transfers. Deliberately **no** module skip guard. |
| `pyo3/tests/test_counter_concurrency.py` | test | event-driven | No Python-thread test exists for any binding. Use `ThreadPoolExecutor` + `future.result(timeout=…)` per RESEARCH Pitfall 8; the nearest timeout discipline is `scripts/bench/tests/test_verify_threads.py:263-284` (stdlib threads, bounded wait). |
| Send error enum returned through `py.detach` | binding internal | request-response | No in-repo precedent for a *custom* detach error type; `ProcessingError` is the only proven detach-safe return (`counter.rs:373-376`). Define a private enum with `String` payloads (all `Send`), map to `PyErr` after the detach. |
| `--compare-baseline` comparison math | harness | batch | No existing script compares Python medians to a committed Python baseline; `compare.py` compares CLI arms by relative delta and `thread_scaling.py` compares arms within one run. Use RESEARCH "Pattern 4" (absolute speedup ratios, locked 1.0 / 1.2 thresholds). |
| `n_read_differential.py --previous` | harness | batch | The script has no cross-run loading; nearest habit is `compare.py::load_results` (validate first, exit 2 on malformed). Design in RESEARCH Open Question 2. |
| `__version__` attribute | config | request-response | `pyo3/src/lib.rs` exposes no non-class attributes today; `m.add` is the RESEARCH-verified mechanism. |

## Metadata

**Analog search scope:** `pyo3/src/`, `pyo3/tests/`, `src/` (`count/`, `database/`, `hash/`, `kmer/`,
`cli/commands/`), `tests/` (byte-identity/golden/engine binaries), `scripts/bench/` (+ `tests/`,
`baselines/`), `docs/user-guide/`, `mkdocs.yml`, both READMEs.
**Files scanned/read:** 30+; 18 target files classified.
**Tracked-source gate:** every analog path named here was verified with
`git ls-files --error-unmatch` (all TRACKED). No gitignored mirror paths are used.
The two target paths that do not exist yet (`tests/sorted_pairs_constructor_tests.rs`,
`docs/user-guide/n-read-semantics.md`) are new files, not analogs.
**Key facts confirmed this session:** `par_sort_unstable_by_key` does not exist in the tree (only
`par_sort_unstable_by` at `src/cli/commands/count.rs:358-360`); `KmerCounter::new` discards
`_num_threads` (`src/hash/table.rs:143,163`); `get_all_counts` returns unsorted DashMap order
(`src/hash/table.rs:588-595`); `ProcessingError` is `Send` (`src/error.rs:63-77`); `sha2` and
`tempfile` are production deps (`Cargo.toml:77,92`); `scripts/bench/tests/test_python_bench.py`
already exists; `docs/mkdocs.yml` does not.
**Pattern extraction date:** 2026-11-13
