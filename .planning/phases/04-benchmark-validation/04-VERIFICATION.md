---
phase: 04-benchmark-validation
verified: 2026-10-17T15:49:47Z
status: gaps_found
score: 8/10 must-haves verified
covered_files: [".github/workflows/benchmark.yml", ".gitignore", ".planning/phases/04-benchmark-validation/04-01-PLAN.md", ".planning/phases/04-benchmark-validation/04-01-SUMMARY.md", ".planning/phases/04-benchmark-validation/04-02-PLAN.md", ".planning/phases/04-benchmark-validation/04-02-SUMMARY.md", ".planning/phases/04-benchmark-validation/04-03-PLAN.md", ".planning/phases/04-benchmark-validation/04-03-SUMMARY.md", ".planning/phases/04-benchmark-validation/04-04-PLAN.md", ".planning/phases/04-benchmark-validation/04-04-SUMMARY.md", ".planning/phases/04-benchmark-validation/04-pilot-calibration.md", ".planning/phases/04-benchmark-validation/04-results-full-k21.json", ".planning/phases/04-benchmark-validation/04-results-full-k31.json", ".planning/phases/04-benchmark-validation/04-results-slice.json", "docs/benchmark-report.md", "scripts/__init__.py", "scripts/bench/README.md", "scripts/bench/__init__.py", "scripts/bench/baselines/bench_baseline.darwin.json", "scripts/bench/baselines/bench_baseline.linux.json", "scripts/bench/bench.py", "scripts/bench/compare.py", "scripts/bench/gen_synthetic.py", "scripts/bench/make_slice.sh", "scripts/bench/tests/__init__.py", "scripts/bench/tests/fixtures/time_l_macos.txt", "scripts/bench/tests/fixtures/time_v_linux.txt", "scripts/bench/tests/test_cmd_matrix.py", "scripts/bench/tests/test_compare.py", "scripts/bench/tests/test_degradation.py", "scripts/bench/tests/test_generator.py", "scripts/bench/tests/test_merge_input.py", "scripts/bench/tests/test_render_report.py", "scripts/bench/tests/test_schema.py", "scripts/bench/tests/test_time_parser.py"]
covered_digest: "v3:sha256:46e07f82f01d4dae6fc985582630ec2caf7d4c58130b3c73cb8134e58d2b4b17"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 10/10
  gaps_closed: []   # prior report carried no gaps: frontmatter (status was human_needed); its human items resolved below
  gaps_remaining: []
  regressions:
    - "CR-02: windows-latest clippy merge gate red at HEAD — introduced after the 2026-10-10 pass by 8f23225 (ungated Windows-off test helpers) + b514331/0c90f4d (windows added to the clippy matrix); CI run 39018676504, re-verified first-hand this pass"
    - "Report byte-identity broken — bb5ccb0 (the CR-01 fix, 2026-10-11) changed bench.py and docs/benchmark-report.md in one commit, leaving the committed provenance line stale by exactly one commit (7eb510d vs bb5ccb0)"
gaps:
  - truth: "04-01 core: dead-infra deletion with cargo clippy --all-targets -- -D warnings plus cargo test staying green"
    status: failed
    reason: "clippy (root) (windows-latest) is RED at HEAD: CI run 39018676504 fails that one job while all 9 other jobs succeed (re-verified via gh this pass). HEAD (971c110) is 6 docs-only commits ahead of the CI-tested 0c90f4d — code-identical, so the red applies to HEAD. 8f23225 gated the RSS measurement test off on Windows without gating its seven exclusive helpers; b514331/0c90f4d then added windows-latest to the clippy matrix where -D warnings turns the dead_code into errors. Local darwin clippy exits 0 (verifier-run) and the full cargo test suite is green (direct exit 0 this session) — the failure is Windows-only and mechanically proven."
    artifacts:
      - path: "tests/merge_bounded_memory_tests.rs"
        issue: "CHUNK_ENTRIES (102), KMER_ENTRY_BYTES (107), CHUNK_BYTES (110), RSS_BOUND_BYTES (125), MEASUREMENT_ENTRIES (136), non-Linux current_rss_kb (178), and run_tracking_peak_rss (199) have their ONLY usages inside the #[cfg(not(target_os = \"windows\"))] test at line 363 — dead code on Windows, 7 dead_code errors under -D warnings"
      - path: ".github/workflows/ci.yml"
        issue: "clippy-root matrix includes windows-latest (line 46) running cargo clippy --all-targets -- -D warnings (line 69); every subsequent push/PR to dev fails the merge gate until fixed"
    missing:
      - "Gate the seven measurement items to match their consumer — or the one-liner from 04-REVIEW.md CR-02: #![cfg_attr(target_os = \"windows\", allow(dead_code))] at the top of tests/merge_bounded_memory_tests.rs (if gating per-item instead, also handle the std::sync::atomic/Arc imports only run_tracking_peak_rss uses)"
      - "Push and confirm the windows-latest clippy leg goes green (the 6 unpushed commits are docs-only; run 39018676504 is the red baseline)"
  - truth: "04-04: docs/benchmark-report.md is rendered mechanically from the committed results JSONs — re-running the renderer reproduces a byte-identical file (T-04-07 tamper evidence)"
    status: partial
    reason: "A fresh render differs from the committed report on exactly ONE line (105, the harness provenance hash: committed 7eb510d… vs fresh bb5ccb0…). bb5ccb0 (the CR-01 fix) changed bench.py and the re-rendered report in a single commit, so the committed provenance line went stale the moment the commit landed — harness_source_commit() (bench.py:977) resolves to the last commit touching bench.py, which is now bb5ccb0 itself. Every measurement number in the report is identical to the fresh render; the defect is the DETECTION property: the byte-identity check now fires on a clean tree, so it can no longer discriminate a hand-edit from a legitimate render. Note: 04-REVIEW-DISPOSITION.md's 're-render byte-identical' claim for CR-01 held only pre-commit (the fix was then uncommitted, so git log still resolved 7eb510d)."
    artifacts:
      - path: "docs/benchmark-report.md"
        issue: "Line 105 carries the pre-bb5ccb0 provenance hash 7eb510dae56194a4059afc65e886ee9d9be34ff2; the renderer now emits bb5ccb083d06cf23f2936fae00c353f2c438e60b"
    missing:
      - "Re-render and recommit docs/benchmark-report.md (python3 scripts/bench/bench.py --render-report --results <the three 04-results-*.json> --out docs/benchmark-report.md); the provenance then re-stabilizes at bb5ccb0 until bench.py next changes — and never bundle a bench.py change and its re-rendered report in one commit again"
      - "Optional hardening: record the harness commit inside the results JSONs at measurement time and render from that field, removing the self-reference paradox for any future bench.py+report commit"
advisory:
  - finding: "WR-08 (open review finding, warning): render_report's methodology note indexes first[\"input_fingerprint\"][0] unguarded (bench.py:1275) and takes the figure from files_data[0] — the first file as given, which may be a mode=slice file"
    category: other
    reason: "Latent robustness defect, not a must-have failure: an empty/absent fingerprint on a schema-valid file crashes with a bare IndexError, and a slice-first --results order attaches the figure to the wrong run. The committed report is unaffected (full file listed first; fingerprint non-empty and internally consistent). Fix sketch in 04-REVIEW.md WR-08."
    evidence_status: "none provided — no failing test; latent only"
  - finding: "IN-08 (open review finding, info): compare.py's advisory-mode PASS summary line is not pinned by any test"
    category: other
    reason: "test_compare.py asserts only the 'GATE: PASS' prefix, which the plain all-axes PASS line also matches; a regression swapping the advisory summary for the plain line would not be caught. One assertIn(\"wall breach(es) advisory, not gating\", out) closes it."
    evidence_status: "none provided — missing-test gap, no observed failure"
---

# Phase 4: Benchmark & Validation Verification Report

**Phase Goal:** Reproducible performance measurement and validation against Jellyfish2 on human-scale data
**Verified:** 2026-10-17T15:49:47Z
**Status:** gaps_found
**Re-verification:** Yes — stale-verification regeneration after covered-input changes (bb5ccb0, 6cffc30, 375fac5, 8f23225, b514331, 0c90f4d)

## Goal Achievement

The phase goal remains **substantially achieved in the codebase**: the harness exists and is fully tested (128 Python tests green, verifier-run), the CI benchmark regression gate is live and green at the latest run (39018676486, success on both legs — gh-verified this pass), the milestone comparison evidence is committed, schema-valid, and internally consistent, and the report's verdict content (k=31 YES / k=21 NO / overall NO, substitute label, cold-cache PARTIALLY SATISFIED) is intact.

**Two gaps introduced AFTER the 2026-10-10 verification now fail must-have clauses** (both by the post-verification follow-on commits, not by the original phase plans):

1. **CR-02 — the dev-branch CI merge gate is red at HEAD.** `clippy (root) (windows-latest)` fails (CI run 39018676504, re-verified first-hand via gh this pass; all 9 other jobs green). 8f23225 gated the RSS measurement test off on Windows without gating its seven exclusive helpers in `tests/merge_bounded_memory_tests.rs`; b514331/0c90f4d then added windows-latest to the clippy matrix where `-D warnings` turns the dead_code into errors. Local darwin clippy exits 0 and the full cargo test suite is green — the failure is Windows-only and mechanically proven (fail-log quoted in 04-REVIEW.md CR-02).
2. **The report's byte-identity tamper-evidence property is broken.** A fresh re-render differs from the committed `docs/benchmark-report.md` on exactly one line — the harness provenance hash (committed `7eb510d`, fresh `bb5ccb0`). bb5ccb0 (the CR-01 fix) bundled the bench.py change and the re-rendered report in one commit, making the committed provenance stale-by-one forever. All measurement numbers are identical; the detection property itself is what broke. One-command fix: re-render and recommit.

Prior human items: #3 (CR-01) is **fixed and verified** (no `220,028` literal anywhere; the figure now derives from `fp0['size_bytes']`; report line 111 shows the mechanical 2,637,234,342-byte figure). #2 (red darwin benchmark leg) is **operationally resolved** (baseline regenerated in 6cffc30; wall axis demoted to advisory per the pre-locked README contingency in 375fac5; latest benchmark.yml runs green). #1 (BENCH-02 milestone decision) **remains open by design** — see Milestone Product Criterion Status.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC-1/BENCH-01: Reproducible harness measures counting and merge wall-clock AND peak memory, runnable in CI as a regression gate | ✓ VERIFIED | `scripts/bench/bench.py` (1,497 lines: measure, parse_time_output, validate_schema, resolve_mode, run_comparison_protocol, render_report); 128/128 stdlib-unittest tests pass (verifier-run, exit 0); `benchmark.yml` builds `--release`, runs synthetic mode, uploads artifact, gates via compare.py; latest run 39018676486 at 0c90f4d = success (gh-verified this pass) |
| 2 | SC-1/04-03: Gate decision logic proven at boundaries, independent axes, per-platform baselines | ✓ VERIFIED | compare.py imports validate_schema from scripts.bench.bench (compare.py:55 — single schema source, verified); 31 comparator tests incl. 4 new TestWallAdvisory; both baselines self-compare GATE: PASS (verifier-run, exit 0 x2); wall-advisory CI mode keeps full wall bookkeeping, RSS still hard-gates at 15% — matches the pre-locked README contingency ("Wall advisory activated 2026-10-17") |
| 3 | SC-2 methodology: Fair comparison — parity gate before timing, matched settings, interleaved counterbalanced protocol | ✓ VERIFIED | Golden-argv tests pin -k/-m, -C, threads, gz-pipe-for-jellyfish-only (suite green); committed JSONs show counterbalanced arm_order per round and per-rep cache_state; params record hash_size 10G, decompressor gzcat, release binary path (verifier-inspected this pass) |
| 4 | SC-2 evidence: Committed full k=31 + k=21 results with >=3 reps, per-rep cache_state, medians on both axes, input fingerprints | ✓ VERIFIED | Verifier ran validate_schema over all three 04-results-*.json this pass: VALID; 3 reps/arm (count-A/count-B/jellyfish-count-A [+ merge in slice]); cache_state recorded; fingerprints internally consistent (2,637,234,342 bytes / sha256 131ca561b851… matches the report figure). Disk re-verification no longer possible — the dataset is ABSENT from /Users/forrest/Downloads this pass; the 2026-10-10 pass verified it on disk (T-04-08) |
| 5 | SC-2/04-04: Report mechanically rendered — re-running the renderer reproduces a byte-identical file | ✗ FAILED | Fresh re-render diff vs committed report: exactly one line differs (105 — provenance hash 7eb510d vs bb5ccb0). Root cause: bb5ccb0 bundled bench.py + report in one commit. Every measurement line is identical; the tamper-evidence DETECTION property is what fails — see gap 2 |
| 6 | SC-3/BENCH-03: Peak memory reported alongside wall-clock — memory as visible as speed | ✓ VERIFIED | Every arm in every results JSON and every report table carries median peak RSS + per-rep RSS + RSS delta vs jellyfish (k=31: rustkmer 55.2 GiB vs jellyfish 84.0 GiB, -34%) |
| 7 | SC-4/BENCH-04: Graceful degradation to slice/synthetic; CI runs without the dataset | ✓ VERIFIED | resolve_mode ladder unit-pinned (15-row table, suite green); benchmark.yml synthetic-only — no jellyfish, no dataset, no pip installs (grep 0), green on both runners at 0c90f4d |
| 8 | 04-01 core: Dual-platform parser, deterministic generator, schema v1, self-check, dead-infra deletion with gates green | ✗ FAILED | Deletion holds (benchmark.rs and performance-regression.yml both ABSENT, 0 module references — verifier-checked); parser/generator/schema tests green; local darwin clippy --all-targets -D warnings exit 0 (verifier-run); full cargo test green this session. BUT the clause "cargo clippy --all-targets -- -D warnings … stays green" is violated in CI: clippy (root) (windows-latest) RED at HEAD (run 39018676504, re-verified first-hand) — see gap 1 / CR-02 |
| 9 | 04-02 protocol: Warmup discard, counterbalanced rounds, cooldown, honest cache_state, median+CV reduction, disk guardrail | ✓ VERIFIED | Committed data shows 3 measured reps with alternating first-position tools; median/CV/cv_warning present; verifier reproduced the disk guardrail live this pass: --disk-floor-gb 9999999 exits 3 before any provisioning/measurement |
| 10 | 04-04 prohibitions: No CI/synthetic run presented as BENCH-02 evidence; report numbers mechanically rendered | ✓ VERIFIED | All BENCH-02 verdict numbers trace to mode=full committed JSONs (CI appears nowhere as milestone evidence); CR-01 FIXED and verified: the "220,028 k-mers" literal is gone everywhere (grep clean), the methodology figure now derives mechanically from the fingerprinted input size (bench.py:1275,1283; report line 111 = 2,637,234,342 bytes = the committed JSON fingerprint). P7 flag from the prior pass is resolved; note the detection mechanism itself is degraded by gap 2 |

**Score:** 8/10 truths verified (0 present, behavior-unverified)

### Milestone Product Criterion Status (NOT a gaps_found trigger — escalated by design)

**BENCH-02's product outcome is NOT MET: rustkmer does not match-or-beat Jellyfish2 on counting speed overall.** Measured verdict: **NO** — k=31 YES (rustkmer 494.19/485.89 s vs jellyfish 843.02 s; -34% RSS), k=21 NO (rustkmer 505.77/494.14 s vs jellyfish 97.26 s), on the user-approved CRR2044018 substitute, cold-cache partially satisfied. This is not an implementation gap: plan 04-04's flagged assumptions pre-declare a NO verdict a valid phase outcome that MUST be escalated, never tuned away. The verification requirement (fair measurement + verdict computed and recorded from evidence) is met; REQUIREMENTS.md honestly records BENCH-02 as the sole unchecked requirement (Pending). Phase 4 is the milestone's final phase — no later-phase deferral applies. The user decision (ship v1.0 on the k=31 result with k=21 documented, or plan a k=21 investigation first) belongs at `/gsd-complete-milestone`.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/bench/bench.py` | Measurement core + protocol + renderer | ✓ VERIFIED | 1,497 lines; all claimed functions present; stdlib-only imports (verified this pass) |
| `scripts/bench/gen_synthetic.py` | Seeded deterministic FASTQ generator | ✓ VERIFIED | Determinism unit-pinned (suite green) |
| `scripts/bench/make_slice.sh` | Deterministic slice tool | ✓ VERIFIED | gunzip -c pipeline (never zcat) |
| `scripts/bench/tests/` (9 modules + 2 fixtures) | Unit tests | ✓ VERIFIED | 128 tests, verifier-run, exit 0; fixtures git-tracked via .gitignore negations (lines 70-71, verified) |
| `scripts/bench/compare.py` | Gate comparator, exit 0/1/2 (+ advisory mode) | ✓ VERIFIED | 281 lines; imports shared validate_schema; 31 tests green |
| `scripts/bench/baselines/bench_baseline.{darwin,linux}.json` | Per-platform committed baselines | ✓ VERIFIED | Both self-compare GATE: PASS (verifier-run); darwin baseline regenerated from run 38098134712 artifact with provenance note (6cffc30) |
| `scripts/bench/README.md` | Bootstrap/regeneration/threshold procedures | ✓ VERIFIED | bootstrap/regeneration/threshold + the wall-advisory contingency and its 2026-10-17 activation record |
| `.github/workflows/benchmark.yml` | CI regression gate | ✓ VERIFIED | Hygiene greps 0/0/0 (continue-on-error / \|\| true / pull_request_target); gate step carries --wall-advisory per the documented contingency; latest run green |
| `.planning/.../04-pilot-calibration.md` | Parity line + calibration | ✓ VERIFIED | PARITY OK distinct=23241904 recorded with full extrapolation |
| `.planning/.../04-results-full-k31.json` | k=31 full evidence | ✓ VERIFIED | 3 reps/arm, validate_schema VALID (verifier-run) |
| `.planning/.../04-results-full-k21.json` | k=21 full evidence | ✓ VERIFIED | Same checks green |
| `.planning/.../04-results-slice.json` | Slice + merge evidence | ✓ VERIFIED | VALID; merge conservation holds (239,912,072 == 119,972,170 + 119,939,902) |
| `docs/benchmark-report.md` | Mechanically rendered milestone report | ✗ STALE-BY-ONE-LINE | Verdict content intact; byte-identity broken on line 105 (provenance) — gap 2 |
| Deleted: `src/cli/commands/benchmark.rs`, `.github/workflows/performance-regression.yml` | Dead infra gone | ✓ VERIFIED | Both absent, 0 module references (verifier-checked this pass) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| compare.py | bench.py | `from scripts.bench.bench import validate_schema` | ✓ WIRED | compare.py:55, verified this pass |
| benchmark.yml | compare.py | gate step invokes CLI with 0.25/0.15 + --wall-advisory | ✓ WIRED | Step present after artifact upload (line 82-87) |
| Results JSONs | render_report | `--render-report --results <jsons>` | ⚠️ WIRED (identity broken) | Render succeeds; output differs from committed report on the provenance line only — gap 2 |
| Parity gate | Full-run trust | Pilot PARITY OK precedes full run; attempt-1 halt recorded (fix 8102985) | ✓ WIRED | Calibration file + report methodology block (lines 111+) |
| Dataset file | Results fingerprint | size + sha256 per input | ⚠️ PARTIAL | Internally consistent (JSON == report figure); dataset absent from disk this pass — on-disk binding verified by the 2026-10-10 pass only |
| Test fixtures | .gitignore negations | `!scripts/bench/tests/fixtures/time_*.txt` | ✓ WIRED | Lines 70-71 present |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| docs/benchmark-report.md | all medians/reps/deltas | committed 04-results-*.json | Yes | ✓ FLOWING (provenance line excepted — gap 2) |
| 04-results-*.json | wall_s / peak_rss_bytes | /usr/bin/time on real runs (mode=full, CRR2044018) | Yes | ✓ FLOWING |
| baselines | medians | real CI runner artifacts (linux: run 37951280461; darwin: regenerated from run 38098134712 in 6cffc30) | Yes | ✓ FLOWING |
| bench_baseline.darwin.json | current gate input | live CI run results.json | Yes | ✓ FLOWING (latest run 39018676486 green with the advisory wall axis) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full harness unit suite | `python3 -m unittest discover -s scripts/bench/tests -t .` | Ran 128 tests, OK, exit 0 | ✓ PASS |
| Report tamper-evidence | re-render from committed JSONs + `diff` | 1 line differs (line 105, provenance hash) | ✗ FAIL — gap 2 |
| Committed evidence schema | `validate_schema` over all three 04-results-*.json | all VALID | ✓ PASS |
| Baseline self-compare (both platforms) | `compare.py --baseline X --current X` | GATE: PASS x2, exit 0 | ✓ PASS |
| Disk guardrail | `bench.py --mode full --disk-floor-gb 9999999` | exit 3 before any measurement | ✓ PASS |
| Local Rust lint gate | `cargo clippy --all-targets -- -D warnings` (darwin) | exit 0, 0 errors | ✓ PASS |
| Windows clippy merge gate | `gh run view 39018676504` (at 0c90f4d, code-identical to HEAD) | `clippy (root) (windows-latest): failure`; all 9 other jobs success | ✗ FAIL — gap 1 (CR-02) |
| Benchmark CI gate liveness | `gh run list --workflow=benchmark.yml --branch dev` | latest 39018676486 @ 0c90f4d = success | ✓ PASS |
| Workflow hygiene | negative greps (continue-on-error / `\|\| true` / pull_request_target) | 0 / 0 / 0 | ✓ PASS |
| Dataset fingerprint on disk | shasum + stat on CRR2044018_r1.fq.gz | dataset absent from disk | ? SKIP — internal consistency verified; on-disk binding rests on the 2026-10-10 pass |
| Rust workspace tests | `cargo test` | green, direct exit 0 | ✓ PASS (run this session per orchestrator context; consistent with the green windows test legs of run 39018676504) |

### Probe Execution

None declared — no `probe-*.sh` scripts exist under `scripts/` and no plan declares probe-based verification for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|---------------------|----------|----------|
| BENCH-01 | 04-01, 04-03 | Reproducible harness measuring count+merge wall + peak RSS, CI regression gate | ✓ SATISFIED | Harness + gate live, tested, and green at the latest run; REQUIREMENTS.md [x] |
| BENCH-02 | 04-02, 04-04 | rustkmer matches or beats Jellyfish2 on counting speed on human-scale data, fair methodology | ✓ MEASURED, ✗ OUTCOME NOT MET — escalated | Measurement + fair methodology + verdict produced and committed honestly; verdict is NO (k=21 fails ~4-5x); REQUIREMENTS.md honestly Pending; user decision at milestone close (see Milestone Product Criterion Status) |
| BENCH-03 | 04-01, 04-04 | Peak memory reported alongside wall-clock | ✓ SATISFIED | Every rep/arm/table carries both metrics; REQUIREMENTS.md [x] |
| BENCH-04 | 04-01, 04-03 | Graceful degradation to slice/synthetic; CI without the dataset | ✓ SATISFIED | Resolver ladder tested; CI synthetic-only, green on both runners; REQUIREMENTS.md [x] |

Orphaned requirements: none — all four phase-4 IDs (BENCH-01..04) are claimed by plans and map to verified evidence.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| test_time_parser.py | BENCH-01 | yes | 0 | no | Value (exact 62384*1024) | Strong |
| test_generator.py | BENCH-04 | yes | 0 | no | Value (sha256 equality) | Strong |
| test_schema.py | BENCH-03 | yes | 0 | no | Value (negative + real-run cases) | Strong |
| test_degradation.py | BENCH-04 | yes | 0 | no | Behavioral (15-row ladder) | Strong |
| test_cmd_matrix.py | BENCH-02 | yes | 0 | no | Value (golden argv, 16 hostile paths) | Strong |
| test_compare.py | BENCH-01 | yes | 0 | no | Value (one-ulp boundaries, all exit-2 classes, 4 advisory cases) | Strong — note IN-08: the advisory PASS summary line itself is not pinned |
| test_merge_input.py | BENCH-02/03 | yes | 0 | no | Behavioral | Strong |
| test_render_report.py | BENCH-03 | yes | 0 | no | Value (byte-identity, verdict truth table, JSON-sensitivity) | Strong — note: cannot catch a stale COMMITTED report (this pass's gap 2 is exactly that class) |

Disabled tests on requirements: 0 (the two grep hits for "skip" are docstring prose). Circular patterns: 0. No BLOCKERs from test quality.

### Decision Coverage

Skipped cleanly — no `04-CONTEXT.md` exists in the phase directory (no `<decisions>` block to check).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| tests/merge_bounded_memory_tests.rs | 102-219 | Ungated Windows-dead measurement helpers behind a windows-gated consumer (CR-02, review disposition open) | 🛑 Blocker | windows-latest clippy merge gate red at HEAD — every push/PR to dev fails CI until gated |
| docs/benchmark-report.md | 105 | Stale provenance hash — byte-identity re-render fails by one line | 🛑 Blocker | T-04-07 tamper-evidence property non-discriminating until re-rendered and recommitted |
| scripts/bench/bench.py | 1275 | WR-08: unguarded `first["input_fingerprint"][0]` + files_data[0] ordering sensitivity | ⚠️ Warning | Latent; committed report unaffected; open review finding |
| scripts/bench/tests/test_compare.py | 190-236 | IN-08: advisory-mode PASS summary line not pinned by any test | ℹ️ Info | Missing-test gap; one assertIn closes it |
| src/cli/commands/count.rs | 27 | Stale prose comment "Phase 4's benchmark will sweep this" | ℹ️ Info | Carried from prior pass; doc comment only |

Debt-marker gate: clean — 0 hits for TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER across all phase files and the post-verification delta files (verifier-run, per-pattern counts). Carried open review findings WR-01..WR-07 and IN-01..IN-07 (04-REVIEW-DISPOSITION.md) remain non-blocking advisory inventory with open dispositions; the review gate is advisory.

### Advisory (New Scope, Unevidenced)

Reported, not blocking — no deterministic failing test behind either row.

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | WR-08: renderer's unguarded input_fingerprint[0] / files_data[0] ordering (bench.py:1275) | other | Latent robustness defect; no failing test; committed report unaffected |
| 2 | IN-08: advisory-mode PASS summary line not pinned by a test (test_compare.py) | other | Missing-test gap; no observed failure |

### Re-verification Context (2026-10-10 → 2026-10-17)

Prior report: human_needed, 10/10, three human items. Resolution this pass:

| Prior human item | Resolution |
|------------------|------------|
| #1 BENCH-02 milestone decision | Still open BY DESIGN — escalated to /gsd-complete-milestone (see Milestone Product Criterion Status) |
| #2 Red darwin benchmark leg + unpushed tree | RESOLVED operationally: darwin baseline regenerated from run 38098134712 (6cffc30), wall axis demoted to advisory per the pre-locked README contingency (375fac5), tree pushed through 0c90f4d, latest benchmark.yml runs green (39018676486) |
| #3 Flagged prohibition P7 / CR-01 | RESOLVED: fixed in bb5ccb0 — literal gone, figure now mechanical (verified this pass); disposition recorded in 04-REVIEW-DISPOSITION.md — but the fix commit itself introduced gap 2 |

### Gaps Summary

Two gaps, both introduced by post-verification follow-on commits, both cheap to close, both mechanically proven:

1. **CR-02 (windows clippy red at HEAD)** — one gating attribute (or file-top cfg_attr) in `tests/merge_bounded_memory_tests.rs` plus a push to verify the leg green. Until then the dev-branch merge gate fails every push/PR.
2. **Report byte-identity broken** — re-render `docs/benchmark-report.md` from the committed JSONs and recommit (docs-only). The provenance line then re-stabilizes; consider rendering provenance from the results JSONs to kill the self-reference paradox permanently.

Neither gap touches a measurement, the verdict, or the committed evidence — all numbers remain mechanically sourced and internally consistent. The BENCH-02 product decision (verdict NO on the substitute dataset) remains the milestone-close escalation it was designed to be, not a phase gap.

---

_Verified: 2026-10-17T15:49:47Z_
_Verifier: Claude (gsd-verifier)_
