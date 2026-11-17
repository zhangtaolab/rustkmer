---
phase: 12-full-scale-merge-verdict
verified: 2026-11-17T09:59:54Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - .planning/phases/12-full-scale-merge-verdict/12-01-PLAN.md
  - .planning/phases/12-full-scale-merge-verdict/12-01-SUMMARY.md
  - .planning/phases/12-full-scale-merge-verdict/12-02-PLAN.md
  - .planning/phases/12-full-scale-merge-verdict/12-02-SUMMARY.md
  - .planning/phases/12-full-scale-merge-verdict/12-03-PLAN.md
  - .planning/phases/12-full-scale-merge-verdict/12-03-SUMMARY.md
  - .planning/phases/12-full-scale-merge-verdict/12-04-PLAN.md
  - .planning/phases/12-full-scale-merge-verdict/12-04-SUMMARY.md
  - .planning/phases/12-full-scale-merge-verdict/12-MERGE-REPORT.md
  - .planning/phases/12-full-scale-merge-verdict/12-PARITY-K21.json
  - .planning/phases/12-full-scale-merge-verdict/12-PARITY-K31.json
  - .planning/phases/12-full-scale-merge-verdict/12-RENDER-PROOF.json
  - .planning/phases/12-full-scale-merge-verdict/12-RESULTS-FULL-K21.json
  - .planning/phases/12-full-scale-merge-verdict/12-RESULTS-FULL-K31.json
  - .planning/phases/12-full-scale-merge-verdict/12-REVALIDATE.json
  - .planning/phases/12-full-scale-merge-verdict/12-VERDICT.json
  - .planning/phases/12-full-scale-merge-verdict/12-WRAPUP.md
  - docs/benchmark-report.md
  - scripts/bench/phase11.py
  - scripts/bench/tests/test_phase11_verdict.py
covered_digest: "v4:sha256:99e37516bd5346f020f9e8691ecf320d5c14411a80a17e5b5bb4dc0181a2a881"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 12: Full-Scale Merge Verdict — Verification Report

**Phase Goal:** The user has a measured merge verdict: at both k, `rustkmer merge` and `jellyfish merge` have run counterbalanced at full scale over identical, parity-validated inputs, and an invest/no-invest decision is recorded via the exit-code contract in a mechanically rendered report — the milestone's headline deliverable, completed before any PEXT implementation could change the binary.
**Verified:** 2026-11-17T09:59:54Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

The milestone headline is landed and independently reproducible at HEAD: the committed evidence records rustkmer merge median walls **63.34 s (k=21)** and **82.86 s (k=31)** vs jellyfish-merge **88.44 s / 114.70 s** → overall YES → decision **NO-INVEST**, exit_code **0**. This verifier re-ran the verdict stage and the render stage live against the committed docs: the verdict stage exits 0 and reproduces the recorded verdict, and the render stage reproduces the committed report byte-for-byte (sha256 `9adcc892…60cc7`, matching 12-RENDER-PROOF.json).

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | At BOTH k=21/31, ≥3 counterbalanced full-scale reps per arm with three-way parity green BEFORE any timing; inputs fingerprint- and Total-revalidated at round 0 (SC1) | ✓ VERIFIED | 12-REVALIDATE.json anchors exact both k (8967099203/8275694030, `exact: true`), binary identities match the ladder tripwires; parity docs record all three legs (`leg1-aggregate-conservation`, `leg2-recount-vs-merged`, `leg3-dump-vs-dump`), `anchors.exact: true`, warmup-marked merges; created-timestamp ordering revalidate 02:44 < parity 04:13/07:18 < results 08:05/09:02; both results docs pass `bench.validate_schema` with 3 arms × exactly 3 reps and rotation-verified arm_order (round r starts at arm r mod 3) |
| 2 | Invest/no-invest verdict recorded via the 0/1/2 exit-code contract from recorded medians; wall primary, RSS/footprint + disk recorded as context; both outcomes valid results (SC2) | ✓ VERIFIED | 12-VERDICT.json: overall YES, decision NO-INVEST, exit_code 0 == observed process exit (commit 727eba5 message records it); per-k blocks carry k/result/rustkmer_wall_s/jellyfish_wall_s with the rule verbatim in every block; merge-t1 only under `scaling`; reps carry wall_s (primary) + peak_rss_bytes/peak_footprint_bytes/peak_bytes + output_bytes + honest cache_state/route. **Live re-run by this verifier:** verdict stage on the committed docs exits 0 and prints the same verdict lines. Unit tests pin the 0/1/2 paths incl. the exit-1/INVEST case |
| 3 | Methodology block captures threads/flags/merge-route/sha256 per arm incl. the like-for-like `--num-threads 1` arm, asymmetry sentence disclosed (SC3) | ✓ VERIFIED | 12-MERGE-REPORT.md per-arm methodology rows carry tool/threads/argv/route/output sha256/binary sha256 for merge, merge-t1 (`--num-threads 1` in argv), jellyfish-merge at both k; the pre-agreed sentence "each tool merges its own representation of identical, parity-validated input data" appears verbatim |
| 4 | Mechanical report with byte-identical re-render proof (no measurement literals in code), entry-rate/byte-rate metrics, predicted-vs-measured check (SC4) | ✓ VERIFIED | **This verifier re-ran the render stage to a temp path at HEAD**: output sha256 `9adcc892…60cc7` == committed report == both digests in 12-RENDER-PROOF.json (`byte_identical: true`); rates tables render entry rate/byte rate/output B-per-entry showing the 20 vs 10/12 B/entry asymmetry; predicted-vs-measured table values (53.84865958547661 / 77.26391787523114 / 73.36277547930045) appear verbatim in 11-LADDER-RESULTS.json — data provably flows from the ladder doc; caveat carried verbatim; source-hygiene unit gates prove zero measurement literals |
| 5 | Controller pins the five-stage contract by construction: STAGES tuple, 0/1/2 exit codes, total dispatch, infra failure → 2 with no artifact (12-01) | ✓ VERIFIED | phase11.py defines `STAGES == ("revalidate","parity","timed","verdict","render")`, EXIT_OK/NO/INVALID = 0/1/2; live: `--help` exit 0 (stderr clean), unknown `--stage bogus` exits 2; TestStageContract/TestVerdictRule (73-test suite, all green) |
| 6 | Session-stage gates unit-proven GREEN/RED: Leg-2 recount diff, EXACT anchor equality, rotation schedule, cross-rep conservation, doc key layouts (12-04) | ✓ VERIFIED | TestRecountVsMergedEqual, TestAnchorEquality, TestSessionBudget, TestRotationSchedule, TestCrossRepConservation, TestRound0DocBuilder, TestParityDocBuilder, TestResultsDocBuilder all green in the 73-test run; grep gates: `normalize_dump_lines`=0 (WR-01 clean), `shell=True`=0, `rotation_schedule`=4, `leg2-recount-vs-merged`=1; **live:** `--stage timed` without `--parity-doc` exits 2 (parity-before-timing structural) |
| 7 | docs/benchmark-report.md rewritten exactly once with number discipline; banner + stale CRR2044018 prose gone (12-03 D-04) | ✓ VERIFIED | SUPERSEDED=0, CRR2044018=0, CRR1936095 named (19×); numbers gate green (every decimal greppable in 12-MERGE-REPORT.md or one of the seven pinned context numbers with committed provenance); `git show HEAD:docs/benchmark-report.md` names CRR1936095 and carries no SUPERSEDED (banner-gone-from-HEAD) |
| 8 | The 8 merge-input artifacts deleted strictly after ALL evidence commits; manifest retained; rebuild path documented (12-03 D-03) | ✓ VERIFIED | 0 `.rkdb`/`.jf` files remain under CRR1936095-merge-inputs/ (only manifest.json); `rebuild` in 12-WRAPUP.md; git history ordering observable: evidence commits (e9df71a/727eba5/10c12cf) → docs rewrite df81ba1 → cleanup 7c608e9 |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Deferred Items

None — no gaps identified; nothing to defer.

### Required Artifacts

`verify.artifacts` run against all four plans: **14/14 passed, zero issues**.

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `scripts/bench/phase11.py` | Five-stage controller (1949 lines) | ✓ VERIFIED | All pinned symbols present (STAGES, exit codes, run_revalidate/parity/timed/verdict/render, recount_vs_merged_equal, merge_arm_argv, verdict_block/line, render_report_text, assert_binary_identity, session_budget) |
| `scripts/bench/tests/test_phase11_verdict.py` | Contract suite (1615 lines) | ✓ VERIFIED | 73 tests, all pass in 0.52 s, hermetic |
| 12-REVALIDATE.json | Round-0 gate record | ✓ VERIFIED | anchors exact both k, binary identities, session_budget 282 GiB, df sample |
| 12-PARITY-K21/K31.json | Three-leg parity evidence | ✓ VERIFIED | All legs green, anchors.exact, warmup-marked merges, distinct conserved (897,266,581 / 1,146,353,600) |
| 12-RESULTS-FULL-K21/K31.json | Schema-v1 timed results | ✓ VERIFIED | validate_schema passes; 3 arms × 3 reps; route/cache_state/round/arm_order/wall/rss/footprint/output_bytes per rep; medians match verdict doc exactly |
| 12-VERDICT.json | Verdict carrier | ✓ VERIFIED | overall/decision/exit_code/rule + per-k blocks; exit_code 0 == observed exit |
| 12-MERGE-REPORT.md | Mechanical MBENCH-04 report | ✓ VERIFIED | All sections present; sha256 matches the render proof |
| 12-RENDER-PROOF.json | Byte-identity proof | ✓ VERIFIED | byte_identical true, digests equal, both == committed report's sha256 |
| docs/benchmark-report.md | v2.0+verdict rewrite | ✓ VERIFIED | All D-04 gates green |
| 12-WRAPUP.md | D-03/D-04 wrap-up record | ✓ VERIFIED | Manifest-matched inventory, df samples, retained manifest, rebuild path |

### Key Link Verification

The mechanical `verify.key-links` verb reported 3/9; the six "not referenced" findings are verb false-negatives on behavioral links — each was hand-verified WIRED below. **All 9 links are wired.**

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| phase11.py | 12-VERDICT.json | run_verdict writes the 0/1/2-carrier doc | WIRED | **Live-proven**: verdict stage re-run wrote a `phase11-merge-verdict` doc with exit_code; committed doc carries the kind/layout |
| phase11.py | 11-LADDER-RESULTS.json | render reads summary.slopes/extrapolated_full_scale, caveat verbatim | WIRED | Report's predicted values appear verbatim in the ladder JSON; renderer refuses a caveat != FULL_SCALE_CAVEAT (unit-proven) |
| 12-REVALIDATE.json | CRR1936095-merge-inputs/ | revalidate_stage re-hashes all 8 artifacts | WIRED | Verb-verified; input_revalidation + manifest_digest + source_fingerprints recorded |
| 12-PARITY-K21.json | 12-RESULTS-FULL-K21.json | timed refuses to start without validated parity doc | WIRED | **Live-proven**: `--stage timed` without `--parity-doc` exits 2; created-timestamp ordering confirms parity preceded timing |
| 12-VERDICT.json | 0/1/2 exit-code contract | run_verdict returns 0/1 and records the code | WIRED | **Live-proven**: exit 0 == recorded exit_code; unit tests pin exit 1 |
| 12-MERGE-REPORT.md | 11-LADDER-RESULTS.json | predicted-vs-measured reads ladder slopes + caveat | WIRED | Same data-flow proof as row 2 — report values match ladder JSON exactly |
| docs/benchmark-report.md | 12-MERGE-REPORT.md | every number greppable in the mechanical report | WIRED | Verb-verified + numbers-ok gate green |
| 12-WRAPUP.md | CRR1936095-merge-inputs/ | deleted-inventory record vs retained manifest | WIRED | Verb-verified + on-disk state matches (0 artifacts, manifest retained) |
| phase11.py | merge_characterize.py | Legs 2-3 run ONLY the streaming pipeline | WIRED | Literal import at phase11.py:77 (`_normalized_sorted_dump`, `dump_vs_dump_equal_streaming`); zero in-process-normalizer refs |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| 12-MERGE-REPORT.md | medians, rates, predicted | results/parity/verdict/ladder JSONs | Yes — committed session records | ✓ FLOWING |
| 12-VERDICT.json | per-k walls | results docs' reduce_arm medians | Yes — 63.34/88.44/82.86/114.7 identical across results → verdict → report | ✓ FLOWING |
| 12-RESULTS-FULL-K*.json | wall_s, rss, output_bytes | live measured reps | Yes — 18 reps with honest variance (k31 rep-0 outlier 101.51 s + cv_warning recorded, not smoothed); output_bytes == distinct×20B+42 header exactly (k21: 17,945,331,662 = 897,266,581×20+42) | ✓ FLOWING |
| docs/benchmark-report.md | all decimals | 12-MERGE-REPORT.md + pinned provenance | Yes — numbers-ok gate | ✓ FLOWING |

No static returns, hardcoded literals, or mocks feed any rendered value.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Controller contract suite | `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` | 73 passed in 0.52 s | ✓ PASS |
| Full harness suite (run once) | `python3 -m unittest discover -s scripts/bench/tests -t .` | Ran 717 tests, OK (skipped=1 — pre-existing flake guard) | ✓ PASS |
| Verdict stage reproduces recorded verdict | `phase11.py --stage verdict --results <k21> <k31> --out /tmp/…` | exit 0; prints k=21 YES 63.34/88.44, k=31 YES 82.86/114.7, overall YES NO-INVEST exit_code=0 | ✓ PASS |
| Byte-identity at HEAD | `phase11.py --stage render … --out /tmp/p12-verify-report.md --proof-out /tmp/…` | exit 0; output sha256 `9adcc892…60cc7` == committed report == proof digests | ✓ PASS |
| Total dispatch (unknown stage) | `phase11.py --stage bogus` | exit 2 | ✓ PASS |
| Parity-before-timing structural | `phase11.py --stage timed --k 21` (no --parity-doc) | exit 2 | ✓ PASS |
| `--help` script-execution path | `python3 scripts/bench/phase11.py --help` | exit 0, stderr clean | ✓ PASS |
| MBENCH-04 report sections | python section checks | All 17 checks pass (asymmetry sentence, caveat, 3 arm rows, rates, B/entry, sha256, RSS-context, pool label, parity, decision) | ✓ PASS |
| D-04 gates | SUPERSEDED/CRR2044018 counts, numbers gate, committed-content gate | 0 / 0 / numbers-ok / banner-gone-from-HEAD | ✓ PASS |
| D-03 gates | artifact count, manifest retention, rebuild mention | 0 remain / manifest-retained / rebuild≥1 | ✓ PASS |

### Probe Execution

N/A — no probe scripts exist (`scripts/*/tests/probe-*.sh` scan empty) and none are declared; the phase's verification gates are the pytest/unittest/python-c commands executed above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| MBENCH-03 | 12-01, 12-02, 12-03, 12-04 | Full-scale merge verdict measured and recorded at both k — counterbalanced ≥3 reps, wall primary, max(rss, phys_footprint) + disk context, 0/1/2 exit-code verdict, methodology incl. like-for-like t1 arm | ✓ SATISFIED | Truths 1-3 above; results docs carry wall/rss/footprint/output_bytes per rep; verdict exit 0 recorded and live-reproduced; REQUIREMENTS.md marks it Complete for Phase 12 |
| MBENCH-04 | 12-01, 12-02, 12-03, 12-04 | Mechanical report — byte-identical re-render proof, entry-rate/byte-rate, asymmetry disclosed, predicted-vs-measured check | ✓ SATISFIED | Truth 4 above; live re-render byte-identical at HEAD; rates + asymmetry + predicted-vs-measured all rendered |

No orphaned requirements: REQUIREMENTS.md maps exactly MBENCH-03/MBENCH-04 to Phase 12, and both are declared in all four plans' frontmatter. MBF-01 (flag sweep) stays v2.2+ deferred by design — the NO-INVEST verdict is precisely its gate condition not firing.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | — | Zero TBD/FIXME/XXX markers; zero placeholders; zero stub/empty implementations in any phase-modified file | — | — |

(The single "placeholder" grep hit in the test file at line 311 is a comment documenting that the 12-01-era "not implemented yet" placeholder test was replaced by a total-dispatch pin — the opposite of a stub.)

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| scripts/bench/tests/test_phase11_verdict.py | MBENCH-03/04 | 73 | 0 | 0 | Behavioral (exit codes, GREEN/RED gates, byte-identity, doc layouts) | PASS |

Disabled tests on requirements: 0. Circular patterns: 0. Insufficient assertions: 0.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (5/5 honored, gate enabled).

### Human Verification Required

None. This is an infrastructure/tooling phase (benchmark session + evidence + report) with no user-facing elements, and no behavior-dependent truth is left unexercised: the verdict computation, the exit-code contract, the byte-identity proof, and the structural stage-ordering gate were all re-executed live by this verifier at HEAD, on top of the 73-test behavioral suite and the 717-test full harness run.

### Notes (informational, non-blocking)

- The rendered report labels its rate rows "entry rate"/"byte rate" (space form) where plan 12-02's gate text used hyphenated "entry-rate" — substance fully present; wording variance only.
- The working tree carries uncommitted modifications outside this phase's deliverables (`.planning/config.json`, `.planning/phases/11-…/11-VERIFICATION.md`, `.planning/state.json`). The phase-12 directory itself is clean and fully committed; those files belong to the orchestrator's state flow, not the phase goal.

### Gaps Summary

None. The phase goal is achieved with independently reproducible evidence: the measured verdict (NO-INVEST, exit 0) is recorded through the exit-code contract in a mechanically rendered, byte-stable report, computed from parity-validated, counterbalanced full-scale measurements at both k, with the wrap-up (public doc rewrite + artifact cleanup) landed in the required order. Every SUMMARY claim this verifier tested against the codebase held up, including the headline medians, the exit code, the byte-identity proof, and the git-history ordering.

---

_Verified: 2026-11-17T09:59:54Z_
_Verifier: Claude (gsd-verifier)_
