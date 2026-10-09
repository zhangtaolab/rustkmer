---
phase: 04
slug: benchmark-validation
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-09
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `04-RESEARCH.md` §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `cargo test` (Rust, existing) + Python 3 stdlib `unittest` for the bench harness (zero-install; deliberately NOT pytest — dodges the repo's known pyo3 pytest/addopts breakage in STATE.md blockers) |
| **Config file** | none needed for stdlib unittest (Rust: cargo defaults; existing suites unaffected) |
| **Quick run command** | `python3 -m unittest discover -s scripts/bench/tests && cargo test` |
| **Full suite command** | `cargo test && cargo clippy --all-targets -- -D warnings && python3 -m unittest discover -s scripts/bench/tests` |
| **Estimated runtime** | ~60–120 seconds (Rust suites + harness units; harness is stdlib-only) |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest discover -s scripts/bench/tests && cargo test`
- **After every plan wave:** Full suite command + one local `python3 scripts/bench/bench.py --mode synthetic --self-check`
- **Before `/gsd-verify-work`:** full suite green; CI `benchmark.yml` green on a PR; slice-scale parity gate green on dev host; milestone `results.json` + rendered report committed (mode=full, CRR2044018)
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

Seeded from RESEARCH.md's requirements→test map; task IDs to be reconciled with final PLAN.md numbering at validate-phase.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-TBD | 01 | 0 | BENCH-01 | T-04-xx / — | Time-output parser handles BOTH platform formats (macOS `-l` bytes vs Linux `-v` kbytes ×1024 trap), rejects garbage | unit | `python3 -m unittest scripts.bench.tests.test_time_parser` | ❌ W0 | ⬜ pending |
| 04-01-TBD | 01 | 0 | BENCH-01 | — | Comparator flags regression beyond threshold, passes within (wall + RSS axes) | unit | `python3 -m unittest scripts.bench.tests.test_compare` | ❌ W0 | ⬜ pending |
| 04-01-TBD | 01 | 1 | BENCH-01 | — | Harness measures count+merge wall-clock and peak RSS on a real invocation (synthetic ≥100k reads through release binary; `wall_s > 0`, `peak_rss_bytes > 0`, distinct == generator expectation) | integration | `python3 scripts/bench/bench.py --mode synthetic --self-check` | ❌ W0 | ⬜ pending |
| 04-02-TBD | 02 | 0 | BENCH-02 | — | Matched-settings command construction (k/canonical/threads mirrored; gz piped for jellyfish only) | unit | `python3 -m unittest scripts.bench.tests.test_cmd_matrix` | ❌ W0 | ⬜ pending |
| 04-02-TBD | 02 | 1 | BENCH-02 | T-04-xx / — | Count parity on real slice before any timing (jf Distinct == rk Unique; Total == Total) | integration (dev host) | `python3 scripts/bench/bench.py --mode slice --parity-only` | ❌ W0 | ⬜ pending |
| 04-03-TBD | 03 | 0 | BENCH-03 | — | results.json carries `peak_rss_bytes` alongside `wall_s` for every arm and median (schema_version, per-rep list) | unit | `python3 -m unittest scripts.bench.tests.test_schema` | ❌ W0 | ⬜ pending |
| 04-03-TBD | 03 | 0 | BENCH-04 | — | Mode ladder: missing path → synthetic; present path → slice; explicit override honored | unit | `python3 -m unittest scripts.bench.tests.test_degradation` | ❌ W0 | ⬜ pending |
| 04-03-TBD | 03 | 0 | BENCH-04 | — | Synthetic generator deterministic given seed (same seed → identical bytes; distinct read count) | unit | `python3 -m unittest scripts.bench.tests.test_generator` | ❌ W0 | ⬜ pending |
| 04-04-TBD | 04 | 1 | BENCH-02 | — | Milestone verdict on full dataset (dev host; ~1–2 h incl. reps; committed results.json + report) | manual-only (documented milestone evidence artifact) | `python3 scripts/bench/bench.py --mode full --out results.json` then report render | ❌ by design | ⬜ pending |
| 04-TBD | 01 | 2 | BENCH-01/04 | — | CI gate workflow green on synthetic input | e2e | push a PR; `benchmark.yml` must pass | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/bench/tests/test_time_parser.py` (+ `fixtures/time_l_macos.txt`, `fixtures/time_v_linux.txt`) — BENCH-01
- [ ] `scripts/bench/tests/test_degradation.py` — BENCH-04
- [ ] `scripts/bench/tests/test_compare.py`, `test_schema.py`, `test_cmd_matrix.py`, `test_generator.py` — BENCH-01/02/03/04
- [ ] `scripts/bench/baselines/bench_baseline.json` — committed after first green synthetic run (documented regen command)
- [ ] `.github/workflows/benchmark.yml` — CI gate job
- [ ] Rust suites: no new gaps — existing `cargo test` infrastructure covers Rust-side additions

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Milestone verdict (rustkmer vs Jellyfish2, counting speed + peak RSS) on full human-scale dataset | BENCH-02 | ~5 GB input, ~1–2 h wall incl. ≥3 counterbalanced reps; CI has no jellyfish and no dataset — gate is rustkmer-vs-baseline by design | Dev host: `python3 scripts/bench/bench.py --mode full --parity-only=false --out results.json`; verify parity gate passed first (`--mode slice --parity-only`); render report; commit results.json + report. Dataset: CRR2044018 (user-approved substitute for CRR1936095, 2026-10-09) — report must label it substitute |
| Cold-cache protocol application | BENCH-02 | Page-cache purge needs sudo/root on Linux; macOS purge available but destructive to cache state of running machine | Between arms: `sudo purge` (macOS) / drop_caches (Linux CI, if ever enabled); interleaved+counterbalanced ≥3 rounds, report median + CV; flag CV > 10% |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
