---
phase: 04
slug: benchmark-validation
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-10-09
validated: 2026-10-11
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

Audited 2026-10-11 (validate-phase, post-execution): every row cross-referenced against the file on disk and the test run at HEAD `29ae679`. Task IDs attributed by introducing commit (`git log --diff-filter=A`).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-T1 | 01 | 1 | BENCH-01 | T-04-xx | Time-output parser handles BOTH platform formats (macOS `-l` bytes vs Linux `-v` kbytes ×1024 trap), rejects garbage | unit | `python3 -m unittest scripts.bench.tests.test_time_parser` | ✅ (8685e9e) | ✅ green |
| 04-01-T1 | 01 | 1 | BENCH-01 | — | Harness measures count+merge wall-clock and peak RSS on a real invocation (synthetic ≥100k reads through release binary; distinct == generator expectation) | integration | `python3 scripts/bench/bench.py --mode synthetic --self-check` | ✅ | ✅ green (RC=0, 24M distinct == expectation) |
| 04-01-T1 | 01 | 1 | BENCH-04 | — | Mode ladder: missing path → synthetic; present path → slice; explicit override honored | unit | `python3 -m unittest scripts.bench.tests.test_degradation` | ✅ (28411ad) | ✅ green |
| 04-01-T1 | 01 | 1 | BENCH-04 | — | Synthetic generator deterministic given seed | unit | `python3 -m unittest scripts.bench.tests.test_generator` | ✅ (8685e9e) | ✅ green |
| 04-02-T1 | 02 | 2 | BENCH-02 | T-04-03 | Matched-settings command construction (k/canonical/threads mirrored; gz piped for jellyfish only; hash_size/decompressor path screening) | unit | `python3 -m unittest scripts.bench.tests.test_cmd_matrix` | ✅ (22b62a3) | ✅ green |
| 04-02-T1 | 02 | 2 | BENCH-02 | — | Count parity on real slice before any timing (jf Distinct == rk Unique; Total == Total) | integration (dev host) | `python3 scripts/bench/bench.py --slice --parity-only` (parity gate also fires inside every full run) | ✅ (bench.py:540) | ✅ green — pilot PASS (3831d8b); full-run gate PASS post-8102985; caught a real truncation bug on attempt 1 (recorded methodology finding) |
| 04-03-T1 | 03 | 3 | BENCH-03 | — | results.json carries `peak_rss_bytes` alongside `wall_s` for every arm and median (schema_version, per-rep list) | unit | `python3 -m unittest scripts.bench.tests.test_schema` | ✅ (8685e9e) | ✅ green |
| 04-03-T1 | 03 | 3 | BENCH-01 | — | Comparator flags regression beyond threshold, passes within (wall + RSS axes; boundary-proven, exit 0/1/2) | unit | `python3 -m unittest scripts.bench.tests.test_compare` | ✅ (8acd514) | ✅ green |
| 04-04-T1 | 04 | 4 | BENCH-02/03 | T-04-08 | merge-input/skip-merge arms; count conservation on measured input | unit | `python3 -m unittest scripts.bench.tests.test_merge_input` | ✅ (3831d8b) | ✅ green |
| 04-04-T3 | 04 | 4 | BENCH-02/03 | — | Mechanical report renderer: zero measurement literals, byte-identical re-render, substitute labeling | unit | `python3 -m unittest scripts.bench.tests.test_render_report` | ✅ (f31d0b5) | ✅ green |
| 04-03-T1 | 03 | 3 | BENCH-01/04 | — | CI gate workflow green on synthetic input (rustkmer-vs-committed-baseline; both platform baselines committed) | e2e | push; `benchmark.yml` must pass | ✅ | ✅ green on 3ae8ab3 (04-03 close); ⚠ one variance-driven count-B RSS breach on 437cec6 (jellyfish-less CI arm, runner noise suspected — see phase 04 issues; rerun pending) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `scripts/bench/tests/test_time_parser.py` (+ fixtures) — BENCH-01 (8685e9e)
- [x] `scripts/bench/tests/test_degradation.py` — BENCH-04 (28411ad)
- [x] `scripts/bench/tests/test_compare.py`, `test_schema.py`, `test_cmd_matrix.py`, `test_generator.py` — BENCH-01/02/03/04 (8685e9e, 22b62a3, 8acd514)
- [x] `scripts/bench/baselines/bench_baseline.json` — committed as platform pair `bench_baseline.{darwin,linux}.json` with documented bootstrap/regeneration procedures (3ae8ab3)
- [x] `.github/workflows/benchmark.yml` — CI gate job (d02ae75)
- [x] Rust suites: no new gaps — `cargo test` green at phase HEAD (23 binaries, 0 failures; includes the multi-member gzip regression test added by 8102985)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Outcome |
|----------|-------------|------------|-------------------|---------|
| Milestone verdict (rustkmer vs Jellyfish2, counting speed + peak RSS) on full human-scale dataset | BENCH-02 | ~2.6 GB gz input, hours of wall incl. ≥3 counterbalanced reps; CI has no jellyfish and no dataset — gate is rustkmer-vs-baseline by design | Dev host full run; parity gate first; render report; commit results + report | **DONE 2026-10-11** — evidence committed (04-results-*.json, 8d63b91); report `docs/benchmark-report.md`; verdict k=31 YES / k=21 NO (overall NO, escalated to milestone close) |
| Cold-cache protocol application | BENCH-02 | Page-cache purge needs sudo/root | Between arms: `sudo purge` (macOS); interleaved+counterbalanced ≥3 rounds, median + CV; flag CV > 10% | **RESOLVED as option (b)** — user-approved no-sudo run (plan 04-04 lines 101/111/146); every rep records `cache_state: "unavailable"`; report states cold-cache PARTIALLY satisfied; counterbalanced interleave preserved |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-10-11 — post-execution audit at HEAD `29ae679`: 8/8 test modules green (incl. 2 added beyond the seeded map), synthetic self-check RC=0, parity gate exercised on real data (twice), CI e2e green at 04-03 close (one variance breach flagged open), milestone manual rows closed with committed evidence.

## Validation Audit 2026-10-10

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
