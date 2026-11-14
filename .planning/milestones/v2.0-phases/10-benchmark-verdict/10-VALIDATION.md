---
phase: "10"
slug: "benchmark-verdict"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-13"
validated: "2026-11-14"
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust: `cargo test`; harness: Python 3 stdlib `unittest`; bindings: pytest in `.venv313` |
| **Config file** | none for the stdlib harness; `pyo3/pyproject.toml` for pytest |
| **Quick run command** | `python3 -m unittest discover -s scripts/bench/tests -t .` |
| **Full suite command** | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings && cargo test --locked && python3 -m unittest discover -s scripts/bench/tests -t . && .venv313/bin/python -m pytest pyo3/tests -q` |
| **Estimated runtime** | ~3 min (full suite); ~10 s (harness quick) |

Baselines at phase start: harness `415 tests, OK (skipped=1)`; pytest `179 passed, 63 skipped`; Rust `508 passed`. Final phase state: harness `571 tests, OK (skipped=1)` (47 tests from plan 10-01/10-02, plus 59 regression tests from the three code-review fix rounds); pytest `179 passed, 63 skipped`; Rust `508 passed`. The harness baseline remains **flaky**: `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` failed intermittently across the phase (macOS `sample` race). Gates allow exactly that one failure and require it to pass on an isolated rerun; it passed 3/3 isolated reruns at closeout.

**Environment note:** use `python3` on PATH (3.13.11). `/usr/bin/python3` is 3.9.6 and fails 47 harness tests.

---

## Sampling Rate

- **After every task commit:** the quick run command; plus `cargo test --locked` only if Rust changed (this phase did not change Rust).
- **After every plan wave:** the full suite, plus one slice-gate run on the dev host.
- **Before `/gsd-verify-work`:** full suite green; both `mode=full` artifacts committed with provenance; the report re-renders byte-identically; no baseline file touched.
- **Max feedback latency:** 600 seconds per task.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-T1 | 10-01 | 1 | BENCH-V2-02 | T-10-integrity | Four-arm synthetic end-to-end: every arm carries both parts, 3 reps, `peak_bytes >= peak_rss_bytes`, positive medians | integration | `python3 scripts/bench/phase10.py --stage synthetic --out <scratch>.json --report-out <scratch>.md` | ✅ existing | ✅ green |
| 10-01-T2 | 10-01 | 1 | BENCH-V2-02 | — | `max(rss, phys_footprint)` parsed from both time-output lines; pipeline and direct-child | unit | `python3 -m unittest scripts.bench.tests.test_time_parser` | ✅ existing | ✅ green |
| 10-01-T3 | 10-01 | 1 | BENCH-V2-02 | T-10-integrity | `ceil(86.5 × distinct)` projection is a true upper bound; budget gate passes equality, rejects above | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestMemoryModel` | ✅ existing | ✅ green |
| 10-02-T1 | 10-02 | 2 | BENCH-V2-02 | T-10-integrity | Fresh-worker `py-t16` arm: positive counts, native module under site-prefix, `threads_resolved == 16`, two ordered inputs, per-rep module sha256/mtime, cross-rep and cross-session parity | unit + integration | `python3 -m unittest scripts.bench.tests.test_python_full_arm` | ✅ existing | ✅ green |
| 10-02-T2 | 10-02 | 2 | BENCH-V2-02 | T-10-truth | Mechanical renderer: per-session schedule, mandatory statements, pinned k set `{21,31}`, byte-identical re-render, no measurement literals | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestReport` | ✅ existing | ✅ green |
| 10-02-T3 | 10-02 | 2 | BENCH-V2-02 | T-10-integrity | Slice-gate record pins the k=21 reference sha; README stage contract matches behavior (exit-2 BLOCKED-preflight exception documented) | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestSliceGateRecord` | ✅ existing | ✅ green |
| 10-03-T1 | 10-03 | 3 | BENCH-V2-02 | T-10-integrity | Real-data slice gate: k=21 pinned reference 229,694,874 / 519,271,168 bound to part_001 `dae91042…`; k=31 live parity only; baselines byte-unchanged; per-session gate k validated | integration | `python3 -c` assertions on `10-slice-gate.json` + `git status --porcelain scripts/bench/baselines/` | ✅ existing | ✅ green |
| 10-03-T2 | 10-03 | 3 | BENCH-V2-02 | T-10-integrity | CLI k=21 over both parts as ONE arm: `rk-t16`/`rk-t1`/`jf-t16`, 3 counterbalanced reps, exact three-way parity, `.rkdb` identity t16==t1 | integration | `python3 -c` assertions on `10-results-full-k21.json` | ✅ existing | ✅ green |
| 10-03-T3 | 10-03 | 3 | BENCH-V2-02 | T-10-integrity | CLI k=31 same discipline; pre-gate re-run green immediately before the stage | integration | `python3 -c` assertions on `10-results-full-k31.json` | ✅ existing | ✅ green |
| 10-03-T4 | 10-03 | 3 | BENCH-V2-02 | — | Checkpoint 1: user reviewed CLI evidence and authorized the Python arm (`proceed`) | manual | Recorded in `10-03-SUMMARY.md` (checkpoint outcome) | ✅ existing | ✅ green |
| 10-04-T1 | 10-04 | 4 | BENCH-V2-02 | T-10-integrity | Preflight re-derives `ceil(86.5 × distinct)` from the MEASURED CLI `rk-t16` counts, pins the harness budget constant, cross-checks the source document sha and requires the `{21,31}` pair | unit + integration | `python3 -m unittest scripts.bench.tests.test_phase10_verdict` (preflight tests) | ✅ existing | ✅ green |
| 10-04-T2 | 10-04 | 4 | BENCH-V2-02 | T-10-integrity | Python sessions k=21/k=31: `jf-t16` + `py-t16` over both parts, 3 counterbalanced reps, exact parity, cross-session jellyfish/count/fingerprint identity, committed pre-gate copies verify their pins | integration | `python3 -m unittest scripts.bench.tests.test_python_full_arm` + artifact assertions | ✅ existing | ✅ green |
| 10-04-T3 | 10-04 | 4 | BENCH-V2-02 | T-10-truth | Verdict computed only from recorded t16 medians (re-derived from raw reps; non-finite rejected); report byte-identical on re-render; cross-session divergence disclosed mechanically; D3 returned to the user, Phase 11 not triggered | unit + manual-only full-scale | `python3 scripts/bench/phase10.py --stage render --docs <4 docs> --verdict-out <v> --out <r>` + `test_phase10_verdict.TestReport` | ✅ existing | ✅ green |
| 10-FIX-R1 | 10-01..04 | 1-4 | BENCH-V2-02 | T-10-truth / T-10-integrity | Code-review regressions: pinned k set, non-finite rejection, median-vs-reps agreement, preflight budget/source pin, per-session schedule, historical CLI pins, atomic publish, CLI-session identity, warmup-order guard | unit | `python3 -m unittest discover -s scripts/bench/tests -t .` (571 tests) | ✅ existing | ✅ green |
| T-10-integrity (live) | all | 4 | BENCH-V2-02 | T-10-integrity | Full k=21/k=31 human-scale verdict from recorded medians, both surfaces | manual-only (dev host, ~4 h) | `phase10.py --stage cli` / `--stage python` / `--stage render` on the dev host | ❌ by design | ✅ evidence committed |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `scripts/bench/tests/test_phase10_verdict.py` — arm construction, rotation, t1 exclusion, verdict truth table (equality = match), pinned k set, non-finite rejection, median re-derivation, descope/cold-cache/dev-host statements, byte-identical re-render
- [x] `scripts/bench/tests/test_python_full_arm.py` — worker stats schema/validation, two-input accumulation exactness, zero-count rejection, module-sha requirement, same-path rebuild detection
- [x] Extend `scripts/bench/tests/test_time_parser.py` — `peak memory footprint` fixtures and the `max()` rule
- [x] Phase-10 arm builder + renderer code (`scripts/bench/phase10.py`), leaving the v1.0 renderer and its byte-identity tests untouched
- [x] No Rust test gaps: the phase did not change `src/`, `pyo3/src/`, or the fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full k=21/k=31 human-scale verdict | BENCH-V2-02 | ~4 hours of machine time on the dev host; the artifact IS the evidence | Run `phase10.py --stage cli --k <21\|31>` and `--stage python --k <21\|31>`, confirm each artifact validates (schema + provenance + parity), then run `--stage render` and confirm the verdict matches the recorded medians |
| Cold-cache reality | BENCH-V2-02 | No sudo means no cache purge | Confirm each rep records its true `cache_state` and the report states the limitation (30/30 reps recorded `unavailable`) |
| Checkpoint 2 / D3 decision | BENCH-V2-02 | The milestone answer and whether Phase 11 is worth building are the user's to accept | Confirm the user has seen the per-k per-surface verdict, the raw medians, peak memory, parity evidence, and the KMC3 descope, and that Phase 11 was not auto-triggered (D3: not executed; MINIM-* deferred) |

*Everything else has automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (the full-scale measurement is manual-only by design and its evidence is committed)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 600s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-14 — 0 gaps found; 571 harness tests green (1 known flake, isolated reruns green); pytest 179 passed; Rust 508 passed; verdict artifacts re-render byte-identically.

## Validation Audit 2026-11-14

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
