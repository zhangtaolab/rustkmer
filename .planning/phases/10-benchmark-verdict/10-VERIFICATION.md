---
phase: 10-benchmark-verdict
verified: 2026-11-14T04:07:45Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - .planning/phases/10-benchmark-verdict/10-01-PLAN.md
  - .planning/phases/10-benchmark-verdict/10-01-SUMMARY.md
  - .planning/phases/10-benchmark-verdict/10-02-PLAN.md
  - .planning/phases/10-benchmark-verdict/10-02-SUMMARY.md
  - .planning/phases/10-benchmark-verdict/10-03-PLAN.md
  - .planning/phases/10-benchmark-verdict/10-03-SUMMARY.md
  - .planning/phases/10-benchmark-verdict/10-04-PLAN.md
  - .planning/phases/10-benchmark-verdict/10-04-SUMMARY.md
  - .planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md
  - .planning/phases/10-benchmark-verdict/10-REVIEW-DISPOSITION.md
  - .planning/phases/10-benchmark-verdict/10-REVIEW-FIX.md
  - .planning/phases/10-benchmark-verdict/10-REVIEW.md
  - .planning/phases/10-benchmark-verdict/10-python-preflight.json
  - .planning/phases/10-benchmark-verdict/10-results-full-k21.json
  - .planning/phases/10-benchmark-verdict/10-results-full-k31.json
  - .planning/phases/10-benchmark-verdict/10-results-python-k21.json
  - .planning/phases/10-benchmark-verdict/10-results-python-k31.json
  - .planning/phases/10-benchmark-verdict/10-slice-gate.json
  - .planning/phases/10-benchmark-verdict/10-verdict.json
  - .planning/phases/10-benchmark-verdict/evidence/historical_cli_k21.json
  - .planning/phases/10-benchmark-verdict/evidence/historical_cli_k31.json
  - .planning/phases/10-benchmark-verdict/evidence/pre_gate_k21.json
  - .planning/phases/10-benchmark-verdict/evidence/pre_gate_k31.json
  - scripts/bench/README.md
  - scripts/bench/bench.py
  - scripts/bench/phase10.py
  - scripts/bench/python_bench.py
  - scripts/bench/tests/test_phase10_verdict.py
  - scripts/bench/tests/test_python_bench.py
  - scripts/bench/tests/test_python_full_arm.py
  - scripts/bench/tests/test_time_parser.py
covered_digest: "v4:sha256:7647be95e97a853d86fea4dc3d29128337f6bf5b2b930abe86eaff979dd5280f"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 10: Benchmark Verdict Verification Report

**Phase Goal:** The milestone's acceptance question is answered with honest, reproducible measurement at full human scale on both surfaces — the jellyfish parity verdict from medians of counterbalanced reps, with every claim drawn from recorded evidence. (KMC3 is out of scope: BENCH-V2-01 was descoped by user decision on 2026-11-13.)
**Verified:** 2026-11-14T04:07:45Z
**Status:** passed
**Re-verification:** No — initial verification (no prior `10-VERIFICATION.md` exists)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | KMC3 descope is explicit, not silent: verdict and report state the 2026-11-13 user decision, and no KMC3 binary was downloaded, installed, or executed | ✓ VERIFIED | `10-verdict.json` `descoped` block; report line 62; REQUIREMENTS.md:47; ROADMAP.md:146/148. No `kmc` on PATH or in `/opt/homebrew/bin`; no KMC tarball or kmc invocation anywhere in `scripts/`; the phase's 62 commits add no binaries |
| 2 | Full human-scale verdict on BOTH surfaces: slice gate green before each stage; both split parts = ONE measured input per arm; 3 counterbalanced reps; honest `cache_state`; `max(rss,phys_footprint)`; verdict from recorded medians with the `<=` rule, equality = match, t1 excluded | ✓ VERIFIED | Slice gate `10-slice-gate.json` (created 10:00:02Z 11-13) precedes CLI sessions (10:55Z, 13:14Z); committed pre-gates (`evidence/pre_gate_k21.json` 01:22:56Z, `pre_gate_k31.json` 01:51:06Z) precede the Python sessions (01:48:03Z, 02:16:55Z). Every arm in all four result docs lists `part_001` + `part_006` in order; every arm has exactly 3 reps with recorded `round`/`arm_order` matching the round-robin schedule; 30/30 measured reps record `cache_state: unavailable`; every rep satisfies `peak_bytes == max(peak_rss_bytes, peak_footprint_bytes)`; `10-verdict.json` rule text + `surface_result()` `<=` with equality = YES |
| 3 | Acceptance answered by measurement: k=21 and k=31 both YES on both surfaces from the committed medians; exact count parity; two-part fingerprints; report re-renders byte-identically | ✓ VERIFIED | Recomputed independently: k=21 — rk 144.69 ≤ jf 194.85, py 165.05 ≤ jf 197.95; k=31 — rk 147.08 ≤ jf 1380.92, py 178.22 ≤ jf 187.14 (all YES). Counts equal across all five arm records per k: 897,266,581 / 8,967,099,203 and 1,146,353,600 / 8,275,694,030. Fingerprints `dae91042…` / `b197f16c…` identical in all four docs. Fresh `--stage render` output is `cmp`-identical to the committed report; regenerated verdict is deep-equal except `created` |
| 4 | Provenance and honesty: every artifact carries binary/module provenance (sha256 + commit + profile); no CI baseline regenerated/written; report states cold-cache limitation and dev-host-only | ✓ VERIFIED | Provenance blocks present on slice gate, both CLI docs, both Python docs (incl. `module` block), preflight, verdict, and committed evidence copies; report has CLI binary + Python module + build provenance. `git diff 01d1291..HEAD -- scripts/bench/baselines/` empty; `slice_parity.crr1936095.json` sha `9826bd59…` matches its pin; `git status` clean for baselines; `docs/benchmark-report.md` untouched. Report: "partially satisfied" + `unavailable x30` census + "Dev-host evidence only" |
| 5 | Cross-session disclosure: 7.38x k=31 jellyfish divergence disclosed mechanically; no cross-session timing claim | ✓ VERIFIED | Report line 54: "CLI session median 1380.92 s vs Python session median 187.14 s (ratio 7.38x) … each surface is judged only against its own session's jellyfish median; no cross-session timing claim is made." Arithmetic 1380.92/187.14 = 7.3791. k=21 line reports 1.02x within the documented 2.0x factor. Renderer code emits this mechanically (`phase10.py` `_verdict_lines`, `CROSS_SESSION_JELLYFISH_MAX_RATIO`) |
| 6 | Code-review integrity: three rounds converged; disposition 0 open; committed report/verdict are the fixed renderer's output; no measured number or verdict changed | ✓ VERIFIED | `10-REVIEW-DISPOSITION.md`: `open: 0`, `total: 19`, 19 fixed (iter2 26 findings → iter3 6 → final 5, all fixed per fix reports). Re-render byte-identical; verdict `verdicts` deep-equal to the original publication (`10075ce`) and to pre-iteration-3 (`dce3e8b`). CLI docs byte-identical to `dce3e8b`; Python docs differ from `dce3e8b` only by the 4 declared `committed_copy`/`supersession_note` additions; versus original publication the docs differ only in `schedule.warmup_order` (corrected false claim) + `schedule_correction` + Python pin metadata. Fix-report artifact shas match the delivered files |
| 7 | No scope creep: no changes to `src/`, `pyo3/src/`, `tests/fixtures/`, manifests/lockfiles, or `.rkdb`; public APIs unchanged; `cargo test --locked` green (508); pytest 179 passed / 63 skipped | ✓ VERIFIED | `git diff --name-only 01d1291..HEAD` outside `.planning/` and `scripts/bench/` is empty; protected-path diff empty (62 phase commits). `cargo test --locked` exit 0: 508 passed, 0 failed, 4 ignored (32 suites). `.venv313/bin/python -m pytest pyo3/tests -q`: 179 passed, 63 skipped. Harness: 571 tests, OK (skipped=1), exit 0 |
| 8 | D3: Phase 11 NOT auto-triggered; user decided (2026-11-14) not to execute Phase 11 and defer MINIM-* | ✓ VERIFIED (with record note) | No `.planning/phases/11-*` directory, no Phase 11 plan/summary, `state.json` phase 11 `pending`, ROADMAP "Not started (conditional — D3)", no MINIM work artifacts. `10-VALIDATION.md` records "Phase 11 was not auto-triggered (D3: not executed; MINIM-* deferred)"; REQUIREMENTS keeps MINIM-01..03 pending/conditional. The dated user decision itself lives in the orchestration context, not a standalone planning record |

**Score:** 8/8 truths verified (0 present, behavior-unverified). No overrides needed.

> Note on truth 8: the current repo state proves Phase 11 was not triggered and MINIM-* remain deferred/conditional. The 2026-11-14 decision timestamp is asserted by the orchestrator context and reflected in the validation doc; it is not separately minute-recorded in `.planning/` — a bookkeeping observation, not a phase-goal gap.

### Deferred Items

None. No must-have is deferred to a later phase (BENCH-V2-02 is answered in this phase; Phase 11 remains conditional on D3 and out of this phase's scope).

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `10-slice-gate.json` | k=21 pinned reference + k=31 live-parity gate, both parts fingerprinted, provenance | ✓ VERIFIED | k=21 229,694,874/519,271,168 with reference sha `9826bd59…` matching committed bytes; k=31 261,863,892/479,271,168 with `live-parity-only` label; binary sha/commit/profile present |
| `10-results-full-k21.json` | CLI session (`rk-t16`,`rk-t1`,`jf-t16`), 3 reps, parity, provenance | ✓ VERIFIED | Three arms; medians 144.69/493.86/194.85 s; counts 897,266,581/8,967,099,203 across all three; `.rkdb` sha equal t16/t1; per-rep peak 4-key record; both parts per arm |
| `10-results-full-k31.json` | Same at k=31 | ✓ VERIFIED | Medians 147.08/474.31/1380.92 s; counts 1,146,353,600/8,275,694,030; `.rkdb` sha equal |
| `10-python-preflight.json` | Projection from measured CLI distinct counts, budget, PROCEED/BLOCKED, source pins | ✓ VERIFIED | `ceil(86.5 × distinct)` = 77,613,559,257 / 99,159,586,400 B vs 118,111,600,640 budget; both PROCEED; source shas equal current CLI docs |
| `10-results-python-k21.json` | Python session (`jf-t16`,`py-t16`), both parts, 3 reps, exact parity, provenance | ✓ VERIFIED | Medians 197.95/165.05 s; counts equal to CLI; per-rep module sha/threads/inputs; cross-session block pinned to committed historical bytes |
| `10-results-python-k31.json` | Same at k=31 | ✓ VERIFIED | Medians 187.14/178.22 s; counts equal; `git_dirty: true` truthfully recorded (honest flag) |
| `10-verdict.json` | Per-k per-surface YES/NO from medians, rule, input shas, KMC3 descope, dev-host flag | ✓ VERIFIED | 4 YES results; overall YES; rule text; four input shas match current docs; `kmc3_executed: false`, `ci_baseline_written: false`, `dev_host_only: true` |
| `10-BENCHMARK-REPORT.md` | Mechanically rendered, mandatory statements, byte-identical re-render | ✓ VERIFIED | Re-render `cmp` clean; contains descope, cold-cache census (`unavailable x30`), dev-host, t16-only rule, equality, cross-session 7.38x disclosure, per-session schedules, provenance |
| `evidence/pre_gate_k21.json`, `pre_gate_k31.json` | Committed pre-gate copies verify their pins | ✓ VERIFIED | sha `4f958c19…` / `b9f3d850…` match the Python docs' `pre_gate.sha256`; k=21 pinned counts and k=31 live parity |
| `evidence/historical_cli_k21.json`, `historical_cli_k31.json` | Historical CLI bytes behind the Python docs' pins | ✓ VERIFIED | sha `757c923a…` / `90804c50…` match `memory_preflight.source_sha256` and `cross_session.cli_doc_sha256`; contents differ from current docs only in warmup-order metadata |
| `scripts/bench/phase10.py`, `bench.py`, `python_bench.py`, tests, `README.md` | Harness extension, v1.0 renderer untouched | ✓ VERIFIED | 2,622-line controller; `parse_time_output` gains footprint/max; repeatable `--inputs` worker; v1.0 `test_render_report` 22/22 OK; README stage/exit contract present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| slice gate | committed `slice_parity.crr1936095.json` | reference sha256 pinned before consumption | ✓ WIRED | Gate pin `9826bd59…` equals live baseline sha |
| slice gate | CLI full run | must be green before the stage | ✓ WIRED | Gate created 10:00:02Z; CLI k=21 doc 10:55:31Z, k=31 13:14:27Z |
| Python pre-gate | Python sessions | committed pre-gate sha pinned in each doc | ✓ WIRED | Pre-gate shas match committed copies; pre-gate creation precedes both session docs |
| four result docs | `10-verdict.json` | `verdict_block` from recorded medians | ✓ WIRED | Independent recomputation of every median/rule matches the verdict |
| `10-verdict.json` + four docs | `10-BENCHMARK-REPORT.md` | `phase10.py --stage render` | ✓ WIRED | Fresh render byte-identical; verdict deep-equal except `created` |
| measured CLI distinct | `10-python-preflight.json` | `ceil(86.5 × distinct)` vs pinned budget | ✓ WIRED | Arithmetic exact; source path + sha pinned |
| py-t16 rep | `python_bench.run_worker` → `validate_worker_stats` | one fresh process, two ordered `--inputs` | ✓ WIRED | Per-rep module sha/threads/inputs recorded; `threads_resolved == 16` on all 6 reps |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `10-results-*.json` | `reps[].wall_s`, `peak_bytes`, counts | `/usr/bin/time` over measured commands; post-run `stats` | Yes — per-rep measured values with 3 reps per arm | ✓ FLOWING |
| `10-verdict.json` | `verdicts[].*_wall_s` | medians of the four result docs | Yes — every value equals a recorded median | ✓ FLOWING |
| `10-BENCHMARK-REPORT.md` | all tables/statements | four committed result docs | Yes — renderer holds no measurement literals; `cmp`-identical re-render | ✓ FLOWING |
| `10-python-preflight.json` | `projected_bytes` | `10-results-full-k*.json` `rk-t16.unique_kmers` | Yes — measured distinct × 86.5 B, sha-pinned source | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Report is byte-deterministic | `python3 scripts/bench/phase10.py --stage render --docs <4 docs> --verdict-out /tmp/v --out /tmp/r` then `cmp` | exit 0; `REPORT BYTE-IDENTICAL`; verdict deep-equal except `created` | ✓ PASS |
| Equality is match-or-beat | `python3 -m unittest ...TestSurfaceResult.test_truth_table ...TestVerdictBlock.test_equality_is_match_or_beat` | Ran 2 tests, OK (10.0 vs 10.0 → YES) | ✓ PASS |
| Renderer test | `...TestReport.test_re_render_is_byte_identical` | Ran 1 test, OK | ✓ PASS |
| Per-session schedules rendered | `...TestReport.test_each_session_schedule_is_rendered_from_its_own_document` | Ran 1 test, OK | ✓ PASS |
| Harness suite | `python3 -m unittest discover -s scripts/bench/tests -t .` | Ran 571 tests in 10.093s; OK (skipped=1); exit 0 | ✓ PASS |
| Rust suite | `cargo test --locked` | exit 0; 508 passed, 0 failed, 4 ignored (32 suites) | ✓ PASS |
| Python bindings | `.venv313/bin/python -m pytest pyo3/tests -q` | 179 passed, 63 skipped in 0.23s; exit 0 | ✓ PASS |
| v1.0 renderer untouched | `python3 -m unittest scripts.bench.tests.test_render_report` | Ran 22 tests, OK | ✓ PASS |

### Probe Execution

N/A — no probe script is declared in the plans and no `scripts/*/tests/probe-*.sh` exists. The phase's runnable evidence is the harness suite plus the render stage, both executed above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BENCH-V2-02 | 10-01, 10-02, 10-03, 10-04 | Full human-scale jellyfish parity verdict on BOTH surfaces (slice gate, counterbalanced medians, honest cache_state, verdict from measured medians) | ✓ SATISFIED | Four result docs + verdict + report; arithmetic independently recomputed: all four surface results YES |
| BENCH-V2-01 | — | KMC3 comparison | ⊘ DESCOPED (recorded) | REQUIREMENTS.md:47, ROADMAP.md:146/148, `10-verdict.json` `descoped`, report line 62; no KMC3 binary/execution anywhere |
| MINIM-01..03 | — | Phase 11 (conditional — D3) | Not in this phase | Remains pending/conditional; no work artifacts |

No orphaned requirements: BENCH-V2-02 is claimed by all four plans; BENCH-V2-01 is explicitly descoped, and MINIM-* belong to conditional Phase 11.

## Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|------------|--------|---------|----------|-----------------|---------|
| `scripts/bench/tests/test_phase10_verdict.py` | BENCH-V2-02 | 99 | 0 | No | Behavioral/value (truth table, byte identity, exact medians) | ✓ PASS |
| `scripts/bench/tests/test_python_full_arm.py` | BENCH-V2-02 | 42 | 0 | No | Behavioral/value (worker argv, exact counts, rejection paths) | ✓ PASS |
| `scripts/bench/tests/test_time_parser.py` | BENCH-V2-02 | 14 | 0 | No | Value (max rule, darwin fail-loud, linux None) | ✓ PASS |
| `scripts/bench/tests/test_python_bench.py` | BENCH-V2-02 | 92 | 1 (env-gated `TestRealWorkerIntegration`, opt-in `RUSTKMER_PYBENCH_VENV`) | No | Behavioral/value | ✓ PASS — skip is not the only coverage; the full-scale Python arm ran and its evidence is committed |
| `scripts/bench/tests/test_render_report.py` | v1.0 contract | 22 | 0 | No | Byte-identity | ✓ PASS (regression) |

**Disabled tests on requirements:** 1 opt-in env-gated integration test; other active tests plus the executed full-scale sessions cover the requirement → no BLOCKER.
**Circular patterns detected:** 0. The parity oracle is the external jellyfish binary and the pinned slice reference; report/verdict consistency was independently recomputed, not compared against values produced by the same renderer.
**Insufficient assertions:** 0. The measured claims are exact-value and behavioral, and the acceptance rule has a truth-table test including equality.

## Decision Coverage

No trackable decisions in CONTEXT.md (`check.decision-coverage-verify` → `{skipped: true, blocking: false, reason: "no trackable decisions", total: 0, honored: 0, not_honored: []}`). CONTEXT.md's decisions are prose bullets, so the gate abstained; `decision_coverage: {honored: 0, total: 0, not_honored: []}`.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX` in any phase-modified file | — | None |
| — | — | No placeholder/stub markers in `phase10.py`, `bench.py`, `python_bench.py` | — | None |
| — | — | No hardcoded empty-data stub in the verdict/report path; all values flow from committed docs | — | None |

Debt-marker gate: clean.

## Human Verification Required

N/A. The phase deliverable is committed measurement evidence, independently re-derived here (medians, parity, fingerprints, preflight arithmetic, verdict rule, byte-identical re-render). The two planned human checkpoints are recorded as completed — Checkpoint 1 selection `proceed` (2026-11-14, 10-03-SUMMARY) and Checkpoint 2 delivered (10-04-SUMMARY) — and the D3/Phase-11 call is the user's post-phase decision, already exercised (not executed; MINIM-* deferred). No new human-verification items are needed to establish the phase goal.

## Gaps Summary

None. All 8 must-haves are verified from committed artifacts, not from SUMMARY claims: the KMC3 descope is stated and no KMC3 execution exists; the slice gate is green before every measured stage; both split parts form one arm; 3 counterbalanced reps per arm with honest `unavailable` cache state and `max(rss, footprint)`; exact count parity and fingerprints across all arms/sessions; the verdict arithmetic independently recomputes to YES at both k on both surfaces; every artifact carries provenance; no CI baseline was written; the cross-session divergence is disclosed mechanically; the review rounds converged with 0 open and no measured value changed; and no protected source/format/API change landed.

### Observations (Info — non-blocking)

1. **Planning bookkeeping is stale, by design.** `ROADMAP.md` still shows Phase 10 "2/4 plans executed", `STATE.md` still says wave 3 of 4, and `REQUIREMENTS.md` still marks BENCH-V2-02 Pending. The plan summaries explicitly left these for the orchestrator transition; verification does not modify them.
2. **CLI k=31 slice-gate re-run is summary-only.** 10-03-SUMMARY claims a green gate re-run immediately before the k=31 stage, but no separate artifact was committed; the committed `10-slice-gate.json` (created before the whole CLI stage) and both Python pre-gate copies are the durable evidence. This satisfies the roadmap's "slice gate green at every step before the full run" but the re-run itself is not independently auditable.
3. **The dated 2026-11-14 D3 decision** is recorded only in the orchestration context / validation doc, not a standalone `.planning/` decision record. Phase 11 remains unexecuted and conditional, so the D3 outcome itself is not in doubt.
4. **Four review-iteration files are untracked** (`10-REVIEW*.iter2.md`, `iter3.md`); they document the earlier rounds and do not affect the committed disposition.

---

_Verified: 2026-11-14T04:07:45Z_
_Verifier: Claude (gsd-verifier)_
