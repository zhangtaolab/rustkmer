---
phase: 04-benchmark-validation
verified: 2026-10-10T19:18:51Z
status: human_needed
score: 10/10 must-haves verified
covered_files: [".github/workflows/benchmark.yml", ".gitignore", ".planning/phases/04-benchmark-validation/04-01-PLAN.md", ".planning/phases/04-benchmark-validation/04-01-SUMMARY.md", ".planning/phases/04-benchmark-validation/04-02-PLAN.md", ".planning/phases/04-benchmark-validation/04-02-SUMMARY.md", ".planning/phases/04-benchmark-validation/04-03-PLAN.md", ".planning/phases/04-benchmark-validation/04-03-SUMMARY.md", ".planning/phases/04-benchmark-validation/04-04-PLAN.md", ".planning/phases/04-benchmark-validation/04-04-SUMMARY.md", ".planning/phases/04-benchmark-validation/04-pilot-calibration.md", ".planning/phases/04-benchmark-validation/04-results-full-k21.json", ".planning/phases/04-benchmark-validation/04-results-full-k31.json", ".planning/phases/04-benchmark-validation/04-results-slice.json", "docs/benchmark-report.md", "scripts/__init__.py", "scripts/bench/README.md", "scripts/bench/__init__.py", "scripts/bench/baselines/bench_baseline.darwin.json", "scripts/bench/baselines/bench_baseline.linux.json", "scripts/bench/bench.py", "scripts/bench/compare.py", "scripts/bench/gen_synthetic.py", "scripts/bench/make_slice.sh", "scripts/bench/tests/__init__.py", "scripts/bench/tests/fixtures/time_l_macos.txt", "scripts/bench/tests/fixtures/time_v_linux.txt", "scripts/bench/tests/test_cmd_matrix.py", "scripts/bench/tests/test_compare.py", "scripts/bench/tests/test_degradation.py", "scripts/bench/tests/test_generator.py", "scripts/bench/tests/test_merge_input.py", "scripts/bench/tests/test_render_report.py", "scripts/bench/tests/test_schema.py", "scripts/bench/tests/test_time_parser.py"]
covered_digest: "v3:sha256:718dfadabc2cc942d3c4fbac91862cbd2bbd58513a3714798297a8011b7ff30b"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Decide the BENCH-02 milestone outcome at milestone close (/gsd-complete-milestone)"
    expected: "A human decision on the measured NO verdict: ship v1.0 on the k=31 result with k=21 documented, or plan a k=21 performance investigation first. The phase's own decision rule (every rustkmer count-arm median wall <= jellyfish median wall in every full-scale table) yields k=31 YES (-41.4%/-42.4% wall, -34% RSS) and k=21 NO (+420%/+408% wall), overall NO, measured on the user-approved CRR2044018 substitute with cold-cache partially satisfied."
    why_human: "The verdict direction is an empirical product criterion, not an implementation defect — the plan (04-04 flagged assumptions) pre-declares either direction as a valid phase outcome requiring user escalation. No gap-closure plan can close it; REQUIREMENTS.md already records BENCH-02 as the lone unchecked requirement."
  - test: "Triage the red benchmark.yml darwin leg on origin/dev (run 38047563014 at 437cec6, 2026-10-10)"
    expected: "count-B median_peak_rss_bytes breached +24.56% (2.34 GB -> 2.91 GB, threshold 15%) while walls dropped 39-55% on the same run — consistent with darwin runner-class variance, the documented weakness whose escape hatches (documented baseline regeneration in scripts/bench/README.md, or the same-job base-ref upgrade path) exist. Note: local dev is 9 commits ahead of origin/dev (the phase's evidence commits, including the 8102985 src/io/fastq.rs MultiGzDecoder fix, are unpushed), so the final tree has not yet been gated in CI."
    why_human: "Requires a push and a maintainer judgment (regenerate baseline vs investigate a real RSS change) on an external CI system; the red run itself is the gate working as designed — fail-loud, breach fully named."
  - test: "Treat the flagged prohibition P7 (04-04: report contains no hand-edited measurement numbers) as partially unverified — review CR-01 in 04-REVIEW-DISPOSITION.md"
    expected: "A human accepts, fixes, or waives CR-01 (severity critical, disposition open): the renderer's _methodology_lines hard-codes '220,028 k-mers' — a measured count from the discarded attempt-1 run that exists in no committed JSON. All headline medians, verdict inputs, and per-rep figures DO render mechanically (byte-identity verified independently this pass); the literal sits in a narrative methodology sentence about a superseded attempt and cannot influence the verdict."
    why_human: "Judgment-tier prohibition; the byte-identity property holds but the 'every figure renders mechanically' clause has one documented exception. LLM-judge verdict recorded here is non-authoritative."
---

# Phase 4: Benchmark & Validation Verification Report

**Phase Goal:** Reproducible performance measurement and validation against Jellyfish2 on human-scale data
**Verified:** 2026-10-10T19:18:51Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

The phase goal — reproducible measurement and validation against Jellyfish2 on human-scale data — is **achieved in the codebase**: the harness exists and is fully tested (124 Python tests + 400 Rust tests green, both run by this verifier), the CI regression gate is live and demonstrably gating (all three exit codes observed in real runs), the milestone comparison ran on human-scale real data under the fair protocol, its evidence is committed and schema-valid, and the report is mechanically rendered from that evidence (byte-identical re-render independently reproduced this pass). **The milestone product criterion itself measured NO** (k=31 YES / k=21 NO, overall NO) — an honest empirical outcome the plan pre-declared valid, escalated to milestone close by design (see Milestone Product Criterion Status below).

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC-1/BENCH-01: Reproducible harness measures counting and merge wall-clock AND peak memory, runnable in CI as a regression gate | ✓ VERIFIED | `scripts/bench/bench.py` (1490 lines: measure, parse_time_output, validate_schema, resolve_mode, run_comparison_protocol, render_report); 124/124 stdlib-unittest tests pass (verifier-run); `benchmark.yml` builds `--release`, runs synthetic mode, uploads artifact, gates via compare.py; live runs observed exit 2 (missing baseline), exit 1 (breach), exit 0 (green) |
| 2 | SC-1/04-03: Gate decision logic proven at boundaries, independent axes, per-platform baselines | ✓ VERIFIED | `compare.py` imports `validate_schema` from `scripts.bench.bench` (single schema source — verified); 27 unit tests incl. one-ulp boundary probes; both baselines self-compare GATE: PASS (verifier-run); platform/schema_version=1 verified in both baseline files |
| 3 | SC-2 methodology: Fair comparison — parity gate before timing, matched settings, interleaved counterbalanced protocol | ✓ VERIFIED | Real-slice `PARITY OK distinct=23241904` recorded in 04-pilot-calibration.md before the full run; golden-argv tests pin `-k`/`-m`, `-C`, threads, gz-pipe-for-jellyfish-only; committed JSONs show counterbalanced arm_order alternating per round and per-rep cache_state from actual purge outcomes |
| 4 | SC-2 evidence: Committed full k=31 + k=21 results with >=3 reps, per-rep cache_state, medians on both axes, input fingerprints | ✓ VERIFIED | Verifier inspected all three 04-results-*.json: 3 reps/arm, rounds 0-2, cache_state recorded, medians wall+RSS, `mode: full`; all three pass validate_schema; sha256+size of the dataset on disk re-verified independently by this verifier — `131ca561…59ce9` / 2,637,234,342 bytes matches the recorded fingerprint exactly (T-04-08) |
| 5 | SC-2 verdict/report: Report states BENCH-02 verdict computed from recorded medians, labels the substitute dataset, states cold-cache partial | ✓ VERIFIED | docs/benchmark-report.md: k=31 YES / k=21 NO / overall NO with the rule stated; substitute sentence present; "Cold cache: PARTIALLY SATISFIED" stated plainly; verifier re-rendered from the committed JSONs — **byte-identical** (diff clean) |
| 6 | SC-3/BENCH-03: Peak memory reported alongside wall-clock — memory wins/losses as visible as speed | ✓ VERIFIED | Every arm in every results JSON and every report table carries median peak RSS + per-rep RSS + RSS delta vs jellyfish (e.g. k=31: rustkmer 55.2 GiB vs jellyfish 84.0 GiB, -34%) |
| 7 | SC-4/BENCH-04: Graceful degradation to slice/synthetic; CI runs without the dataset | ✓ VERIFIED | resolve_mode ladder unit-pinned (15-row table); deterministic gunzip-slice; benchmark.yml runs synthetic mode only — no jellyfish, no dataset, green on both runners at gate-verification commit |
| 8 | 04-01 core: Dual-platform parser, deterministic generator, schema v1, self-check, dead-infra deletion with gates green | ✓ VERIFIED | Linux fixture pinned to exactly 62384*1024 (units trap); generator determinism tests; `benchmark.rs` and `performance-regression.yml` confirmed absent with no module references; verifier ran full `cargo test` — 400 passed / 0 failed / 23 binaries, incl. the multi-member gzip regression test at src/io/fastq.rs:592 |
| 9 | 04-02 protocol: Warmup discard, counterbalanced rounds, cooldown, honest cache_state, median+CV reduction, disk guardrail | ✓ VERIFIED | Committed data shows exactly 3 measured reps (warmup excluded) with alternating first-position tools per round; median/CV/cv_warning present (k=31 jellyfish CV 14.8% flagged); verifier reproduced the disk guardrail live: `--disk-floor-gb 9999999` exits 3 before any provisioning/measurement |
| 10 | 04-04 prohibitions: No CI/synthetic run presented as BENCH-02 evidence; report numbers mechanically rendered | ✓ VERIFIED (P7 flagged) | All BENCH-02 verdict numbers trace to mode=full committed JSONs (CI appears nowhere as milestone evidence); byte-identity holds — but see flagged prohibition CR-01 (human item 3): one narrative literal ("220,028 k-mers") in the methodology section is not derived from a committed JSON |

**Score:** 10/10 truths verified (0 present, behavior-unverified)

### Milestone Product Criterion Status (NOT a gaps_found trigger — escalated by design)

**BENCH-02's product outcome is NOT MET: rustkmer does not match-or-beat Jellyfish2 on counting speed overall.** Measured verdict: **NO** — k=31 YES (rustkmer 494.19/485.89 s vs jellyfish 843.02 s; -34% RSS), k=21 NO (rustkmer 505.77/494.14 s vs jellyfish 97.26 s), on the user-approved CRR2044018 substitute, cold-cache partially satisfied (option b, no sudo — recorded per rep). This is not an implementation gap: plan 04-04's flagged assumptions pre-declare "A NO verdict is a valid phase outcome — it fails the milestone criterion and MUST be reported honestly and escalated to the user, never tuned away." The verification requirement (measurement executed under fair methodology + verdict computed and recorded from evidence) is met; the acceptance decision is queued for milestone close, and REQUIREMENTS.md honestly records BENCH-02 as the sole unchecked requirement (Pending). Phase 4 is the milestone's final phase — no later-phase deferral applies.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/bench/bench.py` | Measurement core + protocol + renderer | ✓ VERIFIED | 1490 lines, all claimed functions present, stdlib-only imports |
| `scripts/bench/gen_synthetic.py` | Seeded deterministic FASTQ generator | ✓ VERIFIED | 60 lines, determinism unit-pinned |
| `scripts/bench/make_slice.sh` | Deterministic slice tool | ✓ VERIFIED | 35 lines, gunzip -c pipeline (never zcat) |
| `scripts/bench/tests/` (8 modules + 2 fixtures) | 124 unit tests | ✓ VERIFIED | All pass (verifier-run); fixtures git-tracked via .gitignore negations |
| `scripts/bench/compare.py` | Gate comparator, exit 0/1/2 | ✓ VERIFIED | 243 lines; imports shared validate_schema |
| `scripts/bench/baselines/bench_baseline.{darwin,linux}.json` | Per-platform committed baselines | ✓ VERIFIED | platform + schema_version 1; both self-compare GATE: PASS |
| `scripts/bench/README.md` | Bootstrap/regeneration/threshold procedures | ✓ VERIFIED | bootstrap (4), regeneration (5), threshold (9) mentions with commands |
| `.github/workflows/benchmark.yml` | CI regression gate | ✓ VERIFIED | branches [dev,main], contents: read, concurrency, fail-fast:false 2-OS matrix, release build, artifact upload before gate, compare.py 0.25/0.15 |
| `.planning/.../04-pilot-calibration.md` | Parity line + calibration | ✓ VERIFIED | PARITY OK distinct=23241904 recorded with full extrapolation |
| `.planning/.../04-results-full-k31.json` | k=31 full evidence | ✓ VERIFIED | 3 reps/arm, validate_schema-clean, fingerprint matches disk |
| `.planning/.../04-results-full-k21.json` | k=21 full evidence | ✓ VERIFIED | Same checks green |
| `.planning/.../04-results-slice.json` | Slice + merge evidence | ✓ VERIFIED | Merge conservation holds in data: 239,912,072 == 119,972,170 + 119,939,902 |
| `docs/benchmark-report.md` | Mechanically rendered milestone report | ✓ VERIFIED | Byte-identical re-render reproduced by this verifier |
| Deleted: `src/cli/commands/benchmark.rs`, `.github/workflows/performance-regression.yml` | Dead infra gone | ✓ VERIFIED | Both absent; no module references remain; clippy/test-suite green |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| compare.py | bench.py | `from scripts.bench.bench import validate_schema` | ✓ WIRED | Single schema validator shared (compare.py:50) |
| benchmark.yml | compare.py | gate step invokes CLI with 0.25/0.15 thresholds | ✓ WIRED | Step present after artifact upload |
| Results JSONs | render_report | `--render-report --results <jsons>` | ✓ WIRED | Re-render byte-identical to committed report |
| Parity gate | Full-run trust | Pilot PARITY OK precedes full run; attempt-1 halt recorded (fix 8102985) | ✓ WIRED | Calibration file + report methodology block |
| Dataset file | Results fingerprint | size + sha256 per input | ✓ WIRED | Independently re-verified on disk by this verifier |
| Test fixtures | .gitignore negations | `!scripts/bench/tests/fixtures/*.txt` | ✓ WIRED | Fresh clone can run the suite (all files git-tracked) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| docs/benchmark-report.md | all medians/reps/deltas | committed 04-results-*.json | Yes | ✓ FLOWING |
| 04-results-*.json | wall_s / peak_rss_bytes | /usr/bin/time on real runs (mode=full, CRR2044018) | Yes | ✓ FLOWING |
| baselines | medians | real CI runner artifacts (run 37951280461, sha256s recorded in 04-03-SUMMARY) | Yes | ✓ FLOWING |
| bench_baseline.darwin.json | current gate input | live CI run results.json | Yes | ✓ FLOWING (live: gate compared and caught a real breach) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full harness unit suite | `python3 -m unittest discover -s scripts/bench/tests -t .` | 124 tests, OK, exit 0 | ✓ PASS |
| Rust workspace suite (deletions + MultiGzDecoder regression) | `cargo test` | 400 passed / 0 failed, 23 binaries | ✓ PASS |
| Report tamper-evidence | re-render from committed JSONs + `diff` | byte-identical | ✓ PASS |
| Committed evidence schema | `validate_schema` over all three 04-results-*.json | all VALID | ✓ PASS |
| Baseline self-compare (both platforms) | `compare.py --baseline X --current X` | GATE: PASS x2 | ✓ PASS |
| Dataset fingerprint binding (T-04-08) | `shasum -a 256` + `stat` on CRR2044018_r1.fq.gz | `131ca561…59ce9` / 2,637,234,342 bytes — exact match | ✓ PASS |
| Disk guardrail | `bench.py --mode full --disk-floor-gb 9999999` | exit 3 before any measurement | ✓ PASS |
| Workflow hygiene (no error-swallowing) | negative greps (continue-on-error / `\|\| true` / pull_request_target) | 0 / 0 / 0 | ✓ PASS |
| CI gate live behavior | `gh run view 38047563014 --log-failed` | breach named with arm/metric/values/threshold, exit 1 | ✓ PASS (gate working; current state red — human item 2) |

### Probe Execution

None declared — no `probe-*.sh` scripts exist under `scripts/` and no plan declares probe-based verification for this phase. Verification ran through the unit/integration suites and CI evidence above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|---------------------|----------|
| BENCH-01 | 04-01, 04-03 | Reproducible harness measuring count+merge wall + peak RSS, CI regression gate | ✓ SATISFIED | Harness + gate live and tested; REQUIREMENTS.md [x] |
| BENCH-02 | 04-02, 04-04 | rustkmer matches or beats Jellyfish2 on counting speed on human-scale data, fair methodology | ✓ MEASURED, ✗ OUTCOME NOT MET — escalated | Measurement + fair methodology + verdict produced and committed honestly; verdict is NO (k=21 fails ~4-5x); REQUIREMENTS.md honestly Pending; user decision at milestone close (human item 1) |
| BENCH-03 | 04-01, 04-04 | Peak memory reported alongside wall-clock | ✓ SATISFIED | Every rep/arm/table carries both metrics; REQUIREMENTS.md [x] |
| BENCH-04 | 04-01, 04-03 | Graceful degradation to slice/synthetic; CI without the dataset | ✓ SATISFIED | Resolver ladder tested; CI synthetic-only, green on both runners at gate commit; REQUIREMENTS.md [x] |

Orphaned requirements: none — all four phase-4 IDs (BENCH-01..04) are claimed by plans and map to verified evidence.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| test_time_parser.py | BENCH-01 | yes | 0 | no | Value (exact 62384*1024) | Strong |
| test_generator.py | BENCH-04 | yes | 0 | no | Value (sha256 equality) | Strong |
| test_schema.py | BENCH-03 | yes | 0 | no | Value (negative + real-run cases) | Strong |
| test_degradation.py | BENCH-04 | yes | 0 | no | Behavioral (15-row ladder) | Strong |
| test_cmd_matrix.py | BENCH-02 | yes | 0 | no | Value (golden argv, 16 hostile paths) | Strong |
| test_compare.py | BENCH-01 | yes | 0 | no | Value (one-ulp boundaries, all exit-2 classes) | Strong |
| test_merge_input.py | BENCH-02/03 | yes | 0 | no | Behavioral | Strong |
| test_render_report.py | BENCH-03 | yes | 0 | no | Value (byte-identity, verdict truth table, JSON-sensitivity) | Strong — note: byte-identity + JSON-sensitivity cannot catch a constant literal (CR-01's point) |

Disabled tests on requirements: 0. Circular patterns: 0 (fixture writes in tests construct inputs, never system-derived expected values). Expected-value provenance: macOS time fixture is a real capture; Linux fixture is assembled from documented GNU time output (plan-specified) while real Linux parsing is exercised end-to-end by the ubuntu CI leg on every run. No BLOCKERs.

### Decision Coverage

Skipped cleanly — no `04-CONTEXT.md` exists in the phase directory (no `<decisions>` block to check).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| scripts/bench/bench.py | ~1290 | Hard-coded narrative measurement literal "220,028 k-mers" in `_methodology_lines` (CR-01, review disposition open) | ⚠️ Warning (flagged prohibition P7) | One methodology-sentence figure not derivable from committed JSONs; not verdict-bearing; byte-identity property unaffected; human review recommended |
| src/cli/commands/count.rs | 27 | Stale prose comment "Phase 4's benchmark will sweep this" (references deleted benchmark concept) | ℹ️ Info | Doc comment only; no module reference; no gate impact |

Debt-marker gate: clean — no TBD/FIXME/XXX anywhere in the phase's files. No blocker anti-patterns.

### Human Verification Required

Three items need human action — see the `human_verification` frontmatter list for full detail:

1. **BENCH-02 milestone decision** — the measured verdict is NO (k=31 YES / k=21 NO) on the substitute dataset with cold-cache partially satisfied; decide at `/gsd-complete-milestone` whether v1.0 ships on the k=31 result with k=21 documented, or a k=21 investigation is planned first.
2. **Red benchmark.yml darwin leg on origin/dev** (run 38047563014: RSS +24.56% breach with walls -39..-55% — runner-class variance suspected; local dev is 9 commits ahead and unpushed, so the final tree is not yet CI-gated). Push, then regenerate the baseline (documented procedure) or investigate.
3. **Flagged prohibition P7 / CR-01** — the renderer hard-codes one narrative measurement figure; accept, fix, or waive (all 15 review findings remain disposition open; the review gate is advisory).

### Gaps Summary

No implementation gaps. All artifacts exist, are substantive, wired, and data-flowing; both test suites pass under this verifier's own runs; the tamper-evidence, fingerprint-binding, and disk-guardrail properties were independently reproduced. The two open threads are (a) the BENCH-02 product outcome — measured NO and escalated by design to milestone close, exactly as the plan's flagged assumptions prescribe, and (b) operational triage of the red darwin CI leg plus the advisory review findings. Neither is closable by a phase gap-closure plan; both are recorded as human decisions.

---

_Verified: 2026-10-10T19:18:51Z_
_Verifier: Claude (gsd-verifier)_
