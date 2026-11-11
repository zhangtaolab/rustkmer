# Phase 5: Measurement & Regression Harness - Context

**Gathered:** 2026-11-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the standing, reproducible measurement gates that every later v2.0 phase claims against, and close the known measurement gaps with recorded evidence. This phase delivers harness/tests/baselines ONLY — it does not change the counting hot path (that is Phase 6+). It extends the shipped v1.0 harness (`scripts/bench/`) and the milestone profiling scripts (`.planning/research/profiling/`), not a new framework.

Requirements: PROF-01 (slice bench + parity gate + provenance), PROF-02 (--threads pool-size test + scaling gate), PROF-03 (contention microbench), PROF-04 (Python baseline), PROF-05 (CLI-vs-Python N-read differential). Also: install Rust 1.80 toolchain (absent locally) and capture pre-refactor golden `.rkdb` sha256 baselines (consumed by OUT-02 in Phase 8).

</domain>

<decisions>
## Implementation Decisions

### Infrastructure phase — research-derived defaults (Claude's Discretion within these)

This is a pure-infrastructure phase (all success criteria technical, no user-facing behavior). The key decisions were already made by the milestone research (`.planning/research/SUMMARY.md`, HIGH-confidence empirical evidence) and ratified guardrails; implementation choices within them are at Claude's discretion:

- **Slice representativeness (PROF-01):** use random-record subslices of the real CRR1936095 data, NOT head-of-file (the profiling head-of-file 4M-read slice is repeat-rich: distinct/instance 2.26 vs v1.0's 7.3). Pin the parity reference (Distinct 229,694,874 / Total 519,271,168 on the measured 4M-read slice) and re-validate on random subslices + the full dataset before any verdict.
- **Provenance (PROF-01):** every result artifact records binary sha256 + git commit + build profile; parity checked BEFORE timing.
- **--threads reality (PROF-02):** the pool-size test must assert the ACTUAL rayon pool size and be observably RED on the current tree (17 OS threads at `--threads 1`); the scaling gate records t1/t4/t16 wall and is RED while the flag is a no-op. These are the standing gates Phase 6 turns green. Reuse/extend `.planning/research/profiling/verify_threads.py`.
- **Contention microbench (PROF-03):** isolate the global-atomics vs memory-bandwidth share of the ~9.4x in-vivo increment multiplier; persist as evidence tuning Phase 7. Extend the profiling microbench (`microbench_main.rs`).
- **Python baseline (PROF-04):** measure the sequential PyO3 file-counting pipeline and commit a baseline so Phase 9 proves a win by measurement. Rebuild extension first (`maturin develop --release`, .venv313, unset CONDA_PREFIX) — the installed .so is prebuilt.
- **N-read differential (PROF-05):** run and record the CLI-vs-Python divergence on N-containing reads (CLI skips N-windows; Python strips N + joins flanks → chimeric k-mers). D2 already ratified skip-N unification (Phase 9 implements); this phase only quantifies the divergence.
- **Toolchain:** install Rust 1.80 via rustup so MSRV-aware clippy on BOTH crates gates every later phase (dev-host stable clippy is not MSRV evidence).
- **Goldens:** capture pre-refactor golden `.rkdb` sha256 across the k × canonical matrix BEFORE any Phase 6/7 hot-path change; never regenerate to make a diff green (v1.0 D-10 / DENSE-02 discipline).

### Claude's Discretion
Harness file layout, exact slice sizes/counts, microbench parameterization, and baseline file formats are at Claude's discretion — extend existing `scripts/bench/` conventions (schema-versioned results.json, stdlib-only Python, /usr/bin/time dual-platform parser) rather than inventing new ones.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/bench/bench.py` + `compare.py` — v1.0 stdlib-only harness: wall + peak RSS under /usr/bin/time, schema-versioned results.json, deterministic synthetic generator, full/slice/synthetic degradation ladder, threshold comparator (exit 0/1/2).
- `scripts/bench/make_slice.sh`, `gen_synthetic.py`, `baselines/`, `tests/` — slice extraction + committed per-platform baselines + harness tests.
- `.planning/research/profiling/` — this milestone's empirical scripts: `run_matrix.py` (14-arm matrix), `run_profiles.py` (samply), `verify_threads.py` (live thread count), `collect_parity.py`, `analyze_profile.py`, `microbench_main.rs` + `microbench_Cargo.toml`, `evidence.json`, `results.jsonl`, `parity_report.json`.
- `tests/golden_sha256_tests.rs` (v1.0 golden discipline) — template for pre-refactor golden capture.
- samply 0.13.1 (no-sudo profiling, already used); /usr/bin/sample + xctrace fallbacks.

### Established Patterns
- Parity-before-timing; medians of counterbalanced reps; honest per-rep cache_state (no-sudo warm-cache reality recorded).
- CI baselines only from the CI runner class; binary/module provenance on every artifact.
- Goldens captured BEFORE refactor; differentials prove gates can fail (mutation RED).

### Integration Points
- Real data: `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/` (part_001, part_006) + `CRR1936095_r1.part_001.fq.gz`.
- jellyfish 2.3.1 at /opt/homebrew/bin/jellyfish (parity reference). KMC3 NOT installed (Phase 10).
- Counter hot path under measurement: `src/cli/commands/count.rs` (resolve_thread_count:845, per-chunk par_iter), `src/hash/table.rs`, `pyo3/src/counter.rs` (sequential add_from_*).
- CI gate: `.github/workflows/benchmark.yml` (ubuntu+macOS) + `performance-regression.yml`.

</code_context>

<specifics>
## Specific Ideas

- The pool-size test is the milestone's smoking-gun regression: it must fail on the current tree and pass after Phase 6. The v1.0 1-vs-N count differential passed for a year while --threads did nothing — count-invariance is not pool-size evidence.
- Keep the harness stdlib-only and reproducible; degrade gracefully to slices/synthetic where the real dataset is absent (CI).
- Record the contention sub-attribution (atomics vs bandwidth) as a persisted artifact Phase 7 consumes — do not leave it as inline prose.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope. (Hot-path changes are Phase 6+; engine is Phase 7; KMC3 install is Phase 10; minimizer is conditional Phase 11.)

</deferred>