---
phase: 03-memory-safety
reviewed: 2026-10-20T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/io/fastq.rs
  - tests/merge_bounded_memory_tests.rs
  - pyo3/pyproject.toml
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 3: Code Review Report (incremental re-review, round 5)

**Reviewed:** 2026-10-20
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Incremental re-review of the three files changed since the round-4 review (commit
`a8fc26f`) via quick tasks 261019-d1y and 261019-dwf. Every carried finding that
touched these files was re-verified against the current tree, and every quick-task
fix was traced through code and confirmed by running the tests — not assumed from
green CI.

**Delta verification (traced, executed, not assumed):**

- **`src/io/fastq.rs` (quick task 261019-d1y):** all four carried findings on this
  file are RESOLVED and are not re-reported.
  - **WR-15 (resolved):** `total_sequence_length` (fastq.rs:453-462) and
    `average_quality` (fastq.rs:492-501) now route through
    `DefaultCompressedFileReader::open_compressed`, matching every sibling helper.
    The regression test `test_total_length_and_average_quality_gzipped`
    (fastq.rs:699-726) pins exact decompressed values for both statistics.
  - **WR-16 (resolved):** `count_sequences` (fastq.rs:425-433) now binds each
    record `Result` and propagates with file-naming context instead of tallying
    malformed records. Pinned by `test_count_sequences_truncated_record_is_err`
    (fastq.rs:733-750), which asserts both the error context and the file path in
    the message.
  - **WR-17 (resolved via the documented non-breaking option):** the parameter is
    renamed `min_quality_ascii` and both doc comments (fastq.rs:288-298, 483) now
    state the raw Phred+33 ASCII byte semantics with a worked Q20=55 example;
    `test_filter_by_quality_compares_raw_ascii_bytes` (fastq.rs:757-773) pins the
    behavior. Verified no caller-level residue: `filter_by_quality`,
    `average_quality`, `total_sequence_length`, and `FastqProcessor` have zero
    callers anywhere in `src/`, `pyo3/src/`, `tests/`, or `examples/` (grep), so
    no call site passes a Phred-scale value into the raw-ASCII comparison.
  - **IN-12 (resolved):** the MultiGzDecoder comment (fastq.rs:68-77) now
    accurately describes the loud trailing-garbage failure instead of overclaiming
    byte-identical behavior, and
    `test_read_all_errors_on_trailing_garbage_after_gzip_member` (fastq.rs:782-809)
    pins the behavior while asserting only this module's own error wording (not
    flate2 internals).
  - Execution: all 13 `io::fastq` unit tests pass; `cargo clippy --all-targets`
    is clean.
- **`tests/merge_bounded_memory_tests.rs` (quick task fixes + Windows gating):**
  **IN-13 (resolved):** both GUARD sites (lines 417-424 and 731-738) now assert
  `estimated > 0` BEFORE `let budget = estimated - 1;`. The tautology is gone and
  the latent u64 underflow is unreachable — and since `assert!` (unlike
  `debug_assert!`) is compiled in release builds, the guard protects both
  profiles. The Windows cfg-gating added alongside is consistent:
  `current_rss_kb` is `not(any(linux, windows))`, the sampler machinery and
  measurement constants are `not(windows)`, and `backdate` has a correct Windows
  variant (FILE_WRITE_ATTRIBUTES 0x100 + FILE_FLAG_BACKUP_SEMANTICS 0x02000000 —
  verified values) used by the non-gated sweep test. All 6 tests in the binary
  pass single-threaded, including the measurement.
- **`pyo3/pyproject.toml` (quick task 261019-dwf, newly in scope):** the coverage
  flags were removed from `addopts` (now just `["-v"]`) with a comment claiming
  "The 80% gate is enforced in CI (pyo3-pytest job in ci.yml)". **Verified true:**
  `.github/workflows/ci.yml:183` runs
  `pytest tests/ --cov=pyrustkmer --cov-report=term-missing --cov-fail-under=80`
  with `pytest-cov` explicitly installed at ci.yml:153. The stated rationale
  (coverage of a compiled extension measures only the maturin shim; baked-in cov
  flags break plain pytest in venvs without pytest-cov) is sound. No defect in
  the change itself.

**No critical findings and no warnings this round.** Three Info-level defects in
the current state of the in-scope files are reported below.

**Out-of-scope carried findings:** WR-01, WR-02, WR-11, WR-12, WR-13, WR-14 and
IN-02/03/04/05/07/08/09/10/11 all live in `src/database/prefix_cache_merge.rs`,
which is not among this round's three changed files (its production code is
untouched since round 4). They remain open in the standing round-4 report and are
neither re-verified nor re-reported here.

## Narrative Findings (AI reviewer)

## Info

### IN-01: `process_file_with_progress` doc mislabels the callback's second argument — "total_estimate" is actually raw file size in bytes (and always `None` for compressed inputs)

**File:** `src/io/fastq.rs:183` (doc: "progress_callback - Optional progress callback (record_count, total_estimate)"), `:213-218` (`total_size = self.file_size().ok()`, and only when `CompressionType::None`), `:241` (`callback(record_count, total_size)`)
**Issue:** Same doc/behavior mismatch class as the just-fixed WR-17, but display-only. The documented `total_estimate` is in fact the input file's size in BYTES (uncompressed files only). A caller following the doc would compute progress as `record_count / total_estimate` — a units mismatch that never reaches 100% — and for `.fastq.gz`/`.bz2`/`.xz` inputs (most real FASTQ data, per this module's own transparent-compression contract) the callback receives `None` with no documented explanation. No in-crate callers exist today (verified by grep), so the defect is latent public-API surface only.
**Fix:** Document the actual contract: "progress_callback - Optional progress callback (record_count, total_bytes) where total_bytes is the uncompressed input file's size in bytes, or None for compressed inputs (size cannot be known without decompression)". If a record estimate is intended, compute and pass one instead.

### IN-02: Literal `{route}` placeholder in `expect_err` messages — `expect_err` takes a plain string, not a format string

**File:** `tests/merge_bounded_memory_tests.rs:670` and `:679`
**Issue:** Both sites read `.expect_err("{route}: the streaming route must fail on a nonexistent temp_dir")` (and the prefix-cache analogue). Unlike `assert!`, `expect_err` does not format its argument, so on failure the panic message displays the literal text `{route}: ...` instead of the route name — degrading exactly the diagnostics a route-parity failure needs most (the surrounding asserts do name the route, but the first panic a debugger sees is the un-substituted one).
**Fix:**
```rust
.expect_err(&format!("{route:?}: the streaming route must fail on a nonexistent temp_dir"));
```
or move the route context into the `assert_*_route_proved` asserts exclusively and use a plain descriptive `expect_err` message.

### IN-03: Dead `[tool.setuptools]` sections reference a `pyrustkmer` Python source package that does not exist, contradicting the file's own layout comment

**File:** `pyo3/pyproject.toml:166-171` (`[tool.setuptools.packages.find]` with `include = ["pyrustkmer*"]`, `[tool.setuptools.package-data]` with `pyrustkmer = ["py.typed"]`)
**Issue:** The build backend is maturin (pyproject.toml:1-3), so both `[tool.setuptools]` tables are inert; moreover the in-file comment at lines 76-80 states `pyo3/pyrustkmer/` "has never existed" and that `python-source` is deliberately unset for exactly that reason. The leftover tables advertise a Python package layout (including a `py.typed` marker file) that contradicts the file's own statement — misleading to anyone wiring up type-checker support or switching build backends, and a trap if setuptools tooling ever resolves them.
**Fix:** Delete both `[tool.setuptools.packages.find]` and `[tool.setuptools.package-data]` sections.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
