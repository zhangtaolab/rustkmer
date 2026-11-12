# Phase 9: Python Parity - Context

**Gathered:** 2026-11-13
**Status:** Ready for planning

<domain>
## Phase Boundary

The Python surface reaches structural parity with the CLI counting path: `PyCounter`'s file methods count through the one shared `CountEngine` (no sequential line loop), the D2 skip-N semantics applies to every Python counting input with the output change documented, `save_database` sorts once under a released GIL, and the measured wall-clock win against the committed Phase 5 baseline is recorded with provenance. The public `PyCounter` API is frozen — no signature changes, no new required arguments.

Out of scope: CI-class baselines and the full-human-scale verdict (Phase 10); minimizer/disk-backed work (Phase 11, conditional); any non-counting `PyDatabase` / query / fuzzy / prefix performance work.

</domain>

<decisions>
## Implementation Decisions

### Engine Integration
- `add_from_fasta` / `add_from_fastq` build a per-call `CountEngine` from the counter's own `k`, `canonical`, and resolved `threads`, call `count_file`, then fold the result in with `CountResult::merge_into(&shared KmerCounter)` — no engine state is added to `PyCounter`, and the path matches the CLI exactly.
- Record format comes from the method name (`add_from_fasta` → `SequenceKind::Fasta`, `add_from_fastq` → `SequenceKind::Fastq`). No extension/content sniffing and no move of `detect_sequence_kind` into the core.
- The per-call `EngineConfig` gets `initial_capacity = 0`. Repeated calls must not re-reserve a large hint into every partition; the persistent `KmerCounter` already holds the capacity.
- Parsing goes through `count_file`'s `bio` readers — the same strict, error-reporting parser the CLI uses. Malformed input surfaces as a Python `ValueError` carrying the parse context, replacing the old lenient `line % 4 == 2` loop.

### D2 Skip-N Scope and Documentation
- Skip-N applies to every Python counting input: `add_from_fasta`, `add_from_fastq`, and `add_sequence`. The non-ACGT pre-filter (strip-N + join flanks) is removed everywhere; no strip-and-join remnant may survive in the Python surface.
- The user-visible change is documented in all three places: `PyCounter` method/module docstrings, a `docs/` page covering N-read semantics, and a migration note in `pyo3/README.md`. The differential artifact additionally carries the exact before/after counts.
- `total_kmers` drops on N-containing reads because skipped windows no longer advance the total. The exact before/after values are recorded in the PROF-05 differential re-run and stated in the docs. The old total is NOT preserved by adding flank-joined windows back.
- The contract is proven against the CLI on the same bytes: the N-free control must match exactly, and the real-N arm must match after D2. The cross-surface differential is the contract, not per-method unit assertions alone.

### `save_database` Sorting and GIL
- The double sort is removed by sorting the pairs exactly once with `rayon::par_sort_unstable_by_key` (the Phase 8 unstable/parallel mandate), then handing them to a new `format.rs` constructor that marks the header `sorted = true` without sorting again. A stable, allocating re-sort and a public-field `header.sorted = true` shortcut are both rejected.
- `save_database` releases the GIL: `py.detach` with owned `Send` captures (the `String` path and a cloned `Arc`). Sorting and writing hundreds of millions of entries under the GIL is a hard block on every Python thread, so this is a requirement, not an optimization.
- Byte identity is proven by a new test: on the same input, `PyCounter.save_database` and the CLI `count` produce an identical `.rkdb` sha256, and the 1-vs-N invariant holds. The existing Phase 8 four-arm differential stays as-is.
- The empty-counter behavior is unchanged: `ValueError("Cannot save empty database. Add k-mers first.")`.

### Measurement and Gating
- `scripts/bench/python_bench.py` gains the reserved exit-1 `--compare-baseline` mode: it compares medians against the committed `scripts/bench/baselines/python_bench_baseline.darwin.json` on the N-free control. Exit 1 is the genuine "did not beat baseline" verdict; exit 2 stays reserved for invalid measurement.
- Both thread configurations are reported: `threads=1` isolates the engine against the sequential baseline, and `threads=<default>` is the real user win. Both must be non-regressive and the default configuration must reach at least 1.2x on the N-free control.
- This phase produces dev-host evidence only. No CI comparison gate is added, because no CI-class baseline exists; CI baselines remain Phase 10's responsibility per the Phase 5 decision.
- The N-read differential is re-run with `--expect-unified`: all four cells must be equal, divergence must be zero, and the artifact is committed.

### Claude's Discretion
- Exact mechanism for exporting and asserting the extension version (`__version__` in `pyo3/src/lib.rs` vs a `PYRUSTKMER_VERSION` constant), and where the version-assert test lives.
- Naming of the new `format.rs` sorted-input constructor.
- Whether the engine helper lives inside `pyo3/src/counter.rs` or a new module under `pyo3/src/`.
- Organization of the new PyO3 tests across the existing `pyo3/tests/` files.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CountEngine` / `EngineConfig` / `SequenceKind` / `CountResult` — `src/count/engine.rs` (persistent workers, `count_file(path, kind)`, `merge_into(&KmerCounter)`).
- `for_each_window` — `src/kmer/extract.rs`; the ONE window extractor with skip-N and canonicalization for k 1..=64.
- `KmerCounter::new_local_counts` / `merge_local_counts` — `src/hash/table.rs`; checked end-of-call reduction.
- `DefaultCompressedFileReader::open_compressed` — `src/io/fastq.rs`; gzip/bzip2/xz/multi-member aware.
- `RKDatabase::from_kmer_pairs(..., sorted)` — `src/database/format.rs:640`; currently re-sorts when `sorted=true`.
- `scripts/bench/python_bench.py` — fresh-worker rusage protocol, module fingerprinting, `EXIT_COMPARISON_RESERVED = 1` already reserved for this phase.
- `scripts/bench/n_read_differential.py` — `--expect-unified` mode already implemented.
- `scripts/bench/baselines/python_bench_baseline.darwin.json` — committed Phase 5 sequential baseline (slice mode, N-free control).

### Established Patterns
- PyO3 parallel/blocking work: extract owned `Send` values, then `py.detach(move || ...)`; never capture `Bound<'_, _>` across the detach (T-02-11 / Pitfall 4).
- Engine errors map to `PyValueError` with the Rust error string preserved; `RustKmerError` remains the custom exception type.
- Tests skip when the extension is absent (`pyo3/tests/test_counter.py` guard) and `conftest.py` exposes `PyCounter` / `PyDatabase` fixtures.

### Integration Points
- `pyo3/src/counter.rs` — `add_from_fasta`, `add_from_fastq`, `add_sequence`, `save_database`.
- `pyo3/src/lib.rs` — module registration; add the version export here.
- `pyo3/pyproject.toml` — version mirror that the assert must agree with.
- `docs/` — MkDocs Material site (root `mkdocs.yml`, `docs/mkdocs.yml`); N-read page goes here.
- `pyo3/README.md` — migration note for the N-read output change.

</code_context>

<specifics>
## Specific Ideas

- The N-read change must follow the WR-04 precedent: never silent. A user reading the old `total_kmers` for an N-containing file will see a smaller number, and the docs must say why before they hit it.
- The Phase 5 baseline explicitly labels its real-N arm `timing-only-real-N-pre-D2` — that arm's counts are expected to change and must never be used as a post-D2 parity gate. Only the N-free control is a parity invariant.
- The extension must be rebuilt (`maturin develop --release -m pyo3/Cargo.toml` in `.venv313`, with `CONDA_PREFIX` unset) and version-asserted before any pytest run; stale `.so` shadowing is a known trap from Phase 03 UAT.

</specifics>

<deferred>
## Deferred Ideas

- Parallel record extraction in the engine (the measured producer-bound lever from Phase 7) — not needed for Python parity, and it is a core-engine change, not a Python one.
- CI-class Python baselines and any CI comparison gate — Phase 10 owns CI baseline regeneration.
- Backlog 999.1/999.2/999.3 — opportunistic only if this work touches them.

</deferred>
