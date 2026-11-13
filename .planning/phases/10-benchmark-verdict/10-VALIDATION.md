---
phase: "10"
slug: "benchmark-verdict"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-13"
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

Baselines at phase start: harness `415 tests, OK (skipped=1)`; pytest `179 passed, 63 skipped`; Rust `508 passed`.

**Environment note:** use `python3` on PATH (3.13.11). `/usr/bin/python3` is 3.9.6 and fails 47 harness tests.

---

## Sampling Rate

- **After every task commit:** the quick run command; plus `cargo test --locked` only if Rust changed (this phase should not change Rust).
- **After every plan wave:** the full suite, plus one slice-gate run on the dev host.
- **Before `/gsd-verify-work`:** full suite green; both `mode=full` artifacts committed with provenance; the report re-renders byte-identically; no baseline file touched.
- **Max feedback latency:** 600 seconds per task.

---

## Per-Task Verification Map

Seed at requirement level; reconciled task-by-task at `validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | BENCH-V2-02 | T-10-integrity | Slice gate green, fingerprint-bound to `part_001` | integration | `python3 scripts/bench/bench.py --parity-only --mode slice --slice-selection head --slice-reads 4000000 --k 21 --threads 16 --hash-size 2G --input <part_001> --parity-reference scripts/bench/baselines/slice_parity.crr1936095.json --out <scratch>/gate.json` | ✅ existing | ⬜ pending |
| TBD | TBD | TBD | BENCH-V2-02 | — | Both-parts arm is ONE arm with two inputs (not two arms) | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestArmConstruction` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-V2-02 | T-10-integrity | Three-tool rotation; `t1` excluded from the acceptance rule | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestVerdict` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-V2-02 | T-10-integrity | Python full worker: two `add_from_fastq` calls accumulate exactly; zero counts rejected | unit + integration | `python3 -m unittest scripts.bench.tests.test_python_full_arm` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-V2-02 | — | `max(rss, phys_footprint)` parsed from both lines, pipeline and direct-child | unit (fixtures) | `python3 -m unittest scripts.bench.tests.test_time_parser` | ✅ extend | ⬜ pending |
| TBD | TBD | TBD | BENCH-V2-02 | T-10-truth | Report carries provenance, cache census, KMC3 descope, dev-host statement; re-render byte-identical | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestReport` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-V2-02 | — | No CI baseline modified | repository check | `git status --porcelain scripts/bench/baselines/` | ✅ existing | ⬜ pending |
| TBD | TBD | TBD | BENCH-V2-02 | T-10-truth | KMC3 descoped, not silently omitted | unit + grep | report contains the descope sentence; `grep -c "DESCOPED" .planning/REQUIREMENTS.md` = 1 | ✅ req text, ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BENCH-V2-02 | — | Full k=21/k=31 verdict from recorded medians | manual-only (dev host, ~4–6 h) | `python3 scripts/bench/bench.py --mode full --phase10 …` | ❌ by design | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/bench/tests/test_phase10_verdict.py` — arm construction, rotation, t1 exclusion, verdict truth table (equality = match), descope/cold-cache/dev-host statements, byte-identical re-render
- [ ] `scripts/bench/tests/test_python_full_arm.py` — worker stats schema/validation, two-input accumulation exactness, zero-count rejection, module-sha requirement
- [ ] Extend `scripts/bench/tests/test_time_parser.py` — `peak memory footprint` fixtures and the `max()` rule
- [ ] Phase-10 arm builder + renderer code (`scripts/bench/bench.py` or a `phase10` module), leaving the v1.0 renderer and its byte-identity tests untouched
- [ ] No Rust test gaps: the phase must not change `src/`, `pyo3/src/`, or the fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full k=21/k=31 human-scale verdict | BENCH-V2-02 | 4–6 hours of machine time on the dev host; the artifact IS the evidence | Run the two `--mode full --phase10` invocations, confirm both artifacts validate (schema + provenance + parity), then render the report and confirm the verdict matches the recorded medians |
| Cold-cache reality | BENCH-V2-02 | No sudo means no cache purge | Confirm each rep records its true `cache_state` and the report states the limitation |

*Everything else has automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 600s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
