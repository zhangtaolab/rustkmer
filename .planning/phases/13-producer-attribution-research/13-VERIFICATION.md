---
phase: 13-producer-attribution-research
verified: 2026-11-17T15:05:55Z
status: passed
score: 28/28 must-haves verified
covered_files:
  - .planning/phases/13-producer-attribution-research/13-01-PLAN.md
  - .planning/phases/13-producer-attribution-research/13-01-SUMMARY.md
  - .planning/phases/13-producer-attribution-research/13-02-PLAN.md
  - .planning/phases/13-producer-attribution-research/13-02-SUMMARY.md
  - .planning/phases/13-producer-attribution-research/13-03-PLAN.md
  - .planning/phases/13-producer-attribution-research/13-03-SUMMARY.md
  - scripts/bench/fixtures/phase13_null_consumer.Cargo.lock
  - scripts/bench/fixtures/phase13_probe_k31.Cargo.lock
  - scripts/bench/phase13.py
  - scripts/bench/tests/test_phase13_driver.py
covered_digest: "v4:sha256:c734fbc0d6f5e418c2e94e54dbba18379de6d584fdcdad7c78fc89a8acd33663"
behavior_unverified: 0
overrides_applied: 0
decision_coverage:
  honored: 10
  total: 10
  not_honored: []
human_verification:
  - test: "Read .planning/phases/13-producer-attribution-research/13-GATE-MEMO.md end to end and confirm (a) both ceilings are named with values and arithmetic, (b) every input number carries a citation to a named full-scale run record, (c) the fresh-base statement uses arm-A medians and the v2.0 walls appear only as disclosed-fingerprint corroboration, (d) the NO-GO is consistent with the pre-registered 10.0% bar applied at both k, and (e) the revisit conditions are the ones you are willing to hold Phase 14 to."
    expected: "The memo reads as a decision you accept as the D-02 gate deliverable: NO-GO under the pre-registered 10.0% derated both-k conjunction (9.6235% at k=21, 10.7965% at k=31), with Phase 14 remaining conditional and PEXT-03/PEXT-04 unexecuted by recorded decision."
    why_human: "The plan's own Task 1 <human-check> (13-03-PLAN.md:184) makes memo soundness an explicit human judgment; automation proves the token/citation contract, not whether the decision is one a human will stand behind. 13-03-SUMMARY records this coverage item as human_judgment: true, status unknown."
  - test: "Decide whether the recorded stage granularity satisfies PEXT-01: parse and extract are recorded as one combined term, parse_extract_s (20.9629 s at k=21, 20.8475 s at k=31), per locked decision D-09. Confirm that this is acceptable for closing PEXT-01, or record that splitting parse from extract requires new Rust instrumentation in a later phase."
    expected: "Either accept the combined parse_extract_s as PEXT-01's parse+extract measurement at the decision-recorded granularity (the phase is measurement-only and explicitly forbids Rust changes), or carry a follow-up requirement for parse/extract instrumentation; either way the attribution's answer to 'where does the wall go' stands (inflate 26.25/21.02 s, parse+extract 20.96/20.85 s, route-send 91.80/92.99 s, output stage 22.39/41.84 s)."
    why_human: "PEXT-01's wording lists parse and extract separately, but the shipped engine exposes only producer_nanos (documented at src/count/engine.rs:191-196 as open+parse+extract+route+send combined) and per-worker busy_nanos; the null consumer times read+parse+extract as one instrument. No code path can separate the two without Rust changes the phase forbids. This is a scope/interpretation decision, not a code check."
  - test: "Resolve the plan prohibitions (27 declared, 15 unique after dedupe — table below). Confirm each must-NOT is accepted as respected by the recorded evidence, in particular: no slice-scale number in the gate, no Rust source change, no v2.0 wall as a denominator, no per-rep skipped, no plain-input deletion before the memo commit, no threshold other than D-05."
    expected: "Every prohibition is acknowledged as respected; any that cannot be so acknowledged is re-opened as a gap before the phase is closed."
    why_human: "The plans declare these as verification: judgment prohibitions. The evidence below is deterministic for each, but the must-NOT tier requires explicit human resolution at the end-of-phase checkpoint rather than a silent pass."
---

# Phase 13: Producer Attribution Research Verification Report

**Phase Goal:** The user knows where the producer wall actually goes on the SHIPPED engine at full scale — inflate vs parse vs extract vs route-send — and whether parallel extraction's predicted win clears the D3 bar, recorded as a go/no-go memo that either triggers Phase 14 or closes PEXT with evidence.
**Verified:** 2026-11-17T15:05:55Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

The phase deliverable exists in the codebase and is self-consistent: the driver is committed and unit-green, the full-scale evidence document carries a complete 60-record gate matrix plus 16 excluded context records at both k, the attribution and predicted-win blocks recompute exactly from the recorded run records, and the committed memo is byte-identical to a fresh render from that evidence with the recorded decision NO-GO. Two items need a human: the plan's own memo soundness check, and one granularity decision (parse vs extract).

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Stage-attribution table exists for the shipped engine at BOTH k from fingerprinted builds — inflate / parse / extract / route-send shares measured at FULL scale via the plain-vs-gzip differential plus a pure-read control; no slice-scale number and no pre-Phase-7 profile feeds the gate (PEXT-01). | ✓ VERIFIED | `13-ATTRIBUTION.json` `attribution.per_k` at k=21/31: inflate_s 26.2500/21.0200 s, parse_extract_s 20.9629/20.8475 s, route_send_s 91.7979/92.9878 s, output_stage_s 22.3887/41.8384 s; 60 gate records all `scale='full'`; 12 control records (both pinned-pair parts per invocation); `build_attribution` refuses context/rehearsal records; memo §2. **Granularity note:** parse and extract are one combined term per locked D-09 (see Human Verification #2). |
| 2 | The predicted-win model names BOTH ceilings — parallelizable share and worker-side scaling — with every input number cited to a named full-scale source run (PEXT-02). | ✓ VERIFIED | `predicted_win.per_k['21'/'31']` carries `parallelizable_floor_derated_s` 120.6683/116.6138, `parallelizable_floor_idealized_s` 119.3581/115.3108, `worker_floor_s` 25.7262/24.7543, `serial_terms_s`, `predicted_full_wall_s`, `predicted_improvement_pct`, `worker_scaling_ceiling: 16`, plus 7 citation lists; all citation keys resolve to records (0 unresolved); memo §3 names both ceilings with citations. |
| 3 | The D3 go/no-go decision is recorded as the research deliverable: either Phase 14 executes with cited evidence, or it does not fire and PEXT-03/PEXT-04 remain unexecuted by recorded decision (PEXT-02). | ✓ VERIFIED | `13-GATE-MEMO.md` line 7 `DECISION: NO-GO`; `13-RENDER-PROOF.json` decision NO-GO, bar 10.0; ROADMAP Phase 14 Conditional paragraph names the memo and the recorded NO-GO; `REQUIREMENTS.md` PEXT-03/PEXT-04 remain Pending (gated). |
| 4 | The D-03/D-10 fingerprint gate branches on exact sha256 equality, records both hashes and the branch, and never silently defaults. | ✓ VERIFIED | `fingerprint_gate` = {current 4539b893…d6d023b, v2_0 8f38d20c…c87c3d23, branch `re-measure`}; the v2.0 value matches `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k21.json` provenance binary sha exactly; `fingerprint_gate()` returns 'cite' only on equality (unit tests). |
| 5 | Every arm, stage share, and model input is computed per k and never shared across k; attribution/predicted_win keyed by string k, run records by integer k. | ✓ VERIFIED | `attribution.per_k` / `predicted_win.per_k` keys are `'21'`/`'31'`; run records carry integer `k`; `build_attribution`/`build_predicted_win` take one k at a time; independent recompute per k matched. |
| 6 | D-09: zero/negative delta-corrected shares are recorded exactly as measured — never clamped or rounded away; raw A−B delta AND read-delta correction are both reported with sign preserved. | ✓ VERIFIED | k=21: raw 25.1200, correction −1.1300, inflate 26.2500; k=31: raw 19.7300, correction −1.2900, inflate 21.0200. The negative correction is preserved and subtracted (raising inflate above the raw delta). Unit tests cover a negative corrected share (−30.0) unclamped and both correction directions. |
| 7 | A run record missing a required provenance field, an incomplete gate matrix, a materialized-probe JSON missing/mismatching k, and zeroed nanos all fail loud. | ✓ VERIFIED | `validate_memo_inputs` has distinct refusals (incomplete matrix, non-full scale, missing provenance); `parse_probe_output` enforces the per-instrument k contract; `_pair_sum_median` and `_guard_zero` refuse zero nanos; all covered by the 80-test module (green). |
| 8 | The attribution row set is exactly the four D-09 stage names plus the control correction; a missing term fails loud rather than rendering a partial table. | ✓ VERIFIED | `build_attribution` returns exactly inflate_s / parse_extract_s / route_send_s / output_stage_s (plus raw delta, correction and the three probe inputs); missing arm/C/D/control records raise naming the missing input; `render_memo_text` raises if any per-k attribution block is absent. |
| 9 | Full precision from recorded values; arm wall medians via `bench.reduce_arm`; every probe-nanos value via the input-type-scoped `_pair_sum_median` (never ad-hoc, never `reduce_arm` on probe JSON). | ✓ VERIFIED | Code paths read exactly `reduce_arm` (walls) and `_pair_sum_median` (probe nanos); `pair_sum_per_rep_s` is recorded; the verifier independently recomputed all four probe terms, the medians, the floors and the composition from the raw run records and matched the stored values to 9 decimal places. |
| 10 | The evidence doc carries a top-level provenance block that `bench.validate_provenance` accepts, set after a clean rebuild with `git_dirty: false` asserted. | ✓ VERIFIED | `provenance` has all seven PROVENANCE_KEYS; `git_dirty: false`, build_profile `release`, platform `darwin-arm64`; `validate_provenance(doc)` passed live during verification. `run_prep` builds, then computes provenance, then asserts clean, then stores it (code order at phase13.py:2196-2201). |
| 11 | D-05: bar 10.0 on the conservative (derated E=0.5) model with `>=` semantics, applied at BOTH k as a conjunction; the idealized E=M bound is reported but never the bar input; both outcomes are first-class (exit 0). | ✓ VERIFIED | Constants pinned (10.0 / 16 / 0.5); `derive_gate_decision` consumes only `predicted_improvement_pct`; live values 9.6235% (k=21) and 10.7965% (k=31) → NO-GO; idealized 10.4512% / 11.5300% reported only; unit tests pin exactly-10.0 GO, 9.99 NO-GO, and idealized-only-clearance NO-GO; `main` maps only OSError/RuntimeError/ValueError to exit 2. |
| 12 | The predicted-win model defines every input: serial_terms_s = inflate_s + route_send_s; worker_floor_s = worker_busy_total_s / WORKER_SCALING_CEILING (16); composition = max(floors) + output_stage_s. | ✓ VERIFIED | Recomputed: serial 118.047905/114.007834, worker floor 25.726166/24.754316, predicted wall 143.057010/158.452144 — exact matches; `worker_scaling_ceiling` 16 recorded; citations present for every model input. |
| 13 | The A3/A4 anomaly criteria are pinned (PROBE_VS_CLI_RATIO_BAND, WORKER_BUSY_RATIO_MAX) and drive mode='bounds', with the conservative end still the D-05 bar input. | ✓ VERIFIED | Constants (0.25, 1.0) and 1.0; live ratios 0.8586/0.7645 and 0.1893/0.1823 → mode `point` at both k; bounds branch unit-tested incl. conservative-end decision and what-would-need-to-be-true list. |
| 14 | Rehearsal records carry scale='rehearsal' and can never feed the committed memo; the committed evidence is full-scale only. | ✓ VERIFIED | `validate_memo_inputs` refuses any non-`full` gate record; all 76 committed records are `scale='full'`; rehearsal writes under scratch (deleted); run_memo refuses partial/invalid evidence. |
| 15 | Every scratch probe crate is built `--release --locked` only after its Cargo.lock is seeded from a committed fixture and sha256-verified; the k=31 manifest enables rustkmer's `profiling` feature. | ✓ VERIFIED | Both fixtures committed (1847/1848 lines); `seed_and_verify_lockfile` → `verify_scratch_lockfile` before `build_fn`; manifest template contains `rustkmer = { path = "@REPO_ROOT@", features = ["profiling"] }` (phase13.py:335); unit tests cover fixture mismatch refusal. |
| 16 | Plain-part decompression streams each part's bytes directly to its output path (no in-memory buffering) and fingerprints the written part. | ✓ VERIFIED | `_decompress_part` calls `_run_fail_loud(["gunzip","-c",part], stdout_path=target)`; prep records each part's size_bytes + sha256 immediately after write; all six entries present. |
| 17 | The pure-read control measures the same byte volume as the A/B arms: one invocation per input type per rep reading BOTH pinned-pair parts. | ✓ VERIFIED | All 12 control records carry `pair_parts=['part_001','part_006']`, 2 `input_paths`, command `cat <part_001> <part_006>`; unit test asserts the argv shape. |
| 18 | The prep block pins disk_check_passed, free_bytes_before_decompression, required_free_bytes, decompression_commands, six gzip fingerprints, six plain entries {part,path,size_bytes,sha256,decompression_command}, probes (provenance + k/k_source), probe_scratch_root. | ✓ VERIFIED | All keys present; disk check 463,239,852,032 B free vs 81,419,827,839 B required; six plain entries (76,290,905,669 B total) and six gzip entries (16,712,215,954 B total); three probes fingerprinted; `probe_scratch_root: /tmp/phase13-probe-scratch`. |
| 19 | The gate matrix is complete: A 3 / B 3 / C 12 / D 6 / control 6 per k, every record scale='full' with wall_s, peak_rss_bytes, binary_sha256, input_sha256s, command_line, cache_state, thermal. | ✓ VERIFIED | Counts exact at both k; zero records missing any required field; input fingerprints all match the prep block; A/B binary = rebuilt stock sha; C/D binary = their probe shas. |
| 20 | D-07: all six gzip parts decompressed and provenanced; the pinned pair gates, the four non-pinned parts form an excluded context matrix structurally invisible to attribution and the decision. | ✓ VERIFIED | 16 context records on part_002…part_005 × gzip+plain × both k × 1 rep, all `context: true` / `excluded: true`; `build_attribution` raises on any context record (unit-tested); gate uses pinned pair only. |
| 21 | D-08: every arm-A/B rep writes a `.rkdb` via `-o` to scratch, deleted immediately after that rep's stats are recorded. | ✓ VERIFIED | All 12 A/B command lines contain `-o`; every record carries output_bytes 17,945,331,662 (k=21) / 22,927,072,042 (k=31); `_pair_arm_records` deletes before building the record; delete seam test fires exactly 12 times; `/tmp/phase13-probe-scratch/session-out/` was empty at session end and the whole scratch root is now gone. |
| 22 | D-06: the decision surface is the CLI count wall only; no Python-surface arm is measured and no Python wall enters attribution/model/decision; the memo carries the Python context block. | ✓ VERIFIED | No Python-run records exist; `derive_gate_decision` reads only `predicted_improvement_pct`; memo §5 contains 165.05, 178.22, module sha `6d526431…558ae3`, "context only", "binary-fingerprint caveat", and states the decision surface is the CLI wall. |
| 23 | Arm C at k=31 was measured by the materialized k-from-argv probe whose JSON asserts k=31; the committed k=21 probe is keyed by instrument identity (no k field demanded). | ✓ VERIFIED | All 20 excluded+gate C k=31 records have `probe_output_json.k == 31` and the materialized probe's binary sha; C k=21 records have no k field and the committed probe's binary sha; D records' k always match their record k. |
| 24 | `13-GATE-MEMO.md` is a deterministic render of `13-ATTRIBUTION.json` with a byte-identical re-render proof, and the proof's decision matches the evidence decision. | ✓ VERIFIED | Verifier re-rendered `render_memo_text(doc)` twice from the committed evidence: both renders identical and byte-for-byte equal to the committed memo; sha256 `428d6040…acced48` equals the memo file hash and both proof hashes; proof decision NO-GO == evidence decision. (The proof's `evidence.sha256` is the pre-`scratch_cleaned`-flip blob; re-render from the post-flip doc is still byte-identical.) |
| 25 | The memo content contract: both ceilings with values and D-09 composition; four stage names with per-cell citations; D-05 bar with >= and both-k; fresh-base statement + v2.0 corroboration 144.69/147.08 as disclosed-fingerprint only; D-03/D-10 provenance block; probe-vs-CLI topology note; D-04 lifecycle pointer. | ✓ VERIFIED | Every required token present in the committed memo; citations per stage row point at arm/k/rep/part/input-type keys; composition rule printed; NO-GO branch (revisit conditions) present. |
| 26 | ROADMAP §Phase 14 carries the conditional annotation pointing at the memo and the recorded decision, and a NO-GO memo carries revisit conditions (a GO memo would carry the six-part per-part sizing block). | ✓ VERIFIED | Scoped one-line diff in commit ff16c08: the Conditional paragraph now names the memo and "recorded Phase-13 decision is NO-GO, recorded 2026-11-17"; nothing else in ROADMAP changed; memo §6 carries the revisit conditions. The GO per-part branch is unit-proven (`TestMemoBranches.test_go_memo_lists_all_six_parts`) but not live (decision is NO-GO). |
| 27 | The memo stage refuses partial evidence: missing attribution/predicted_win blocks or any memo-cited record lacking scale='full' or provenance fields exits 2 with the offending record named. | ✓ VERIFIED | `run_memo` requires both blocks, `validate_provenance`, and `validate_memo_inputs`; three distinct refusal messages; missing-block test exits 2; verified live code path by reading and by the green unit suite. |
| 28 | D-04 lifecycle: the six plain-input parts and the pinned probe scratch root are deleted only AFTER the memo commit, with provenance surviving in the committed evidence and the deletion recorded. | ✓ VERIFIED | `CRR1936095-plain/` absent; `/tmp/phase13-probe-scratch` absent; gzip root still holds six parts; prep block still carries 6/6 sha256+size entries; `scratch_cleaned: true`; `13-WRAPUP.md` names explicit paths, 76,290,905,669 B, regeneration command; memo commit ff16c08 precedes wrap-up a46b9ea. |

**Score:** 28/28 truths verified (0 present, behavior-unverified)

### Prohibitions (must-NOT checks)

27 prohibitions are declared across the three plans (10 + 10 + 7); after dedupe they reduce to 15 unique statements. Each was checked against code/data/git evidence and is respected. These are judgment-tier items and are surfaced for explicit human sign-off in Human Verification #3.

| # | Prohibition (deduped) | Evidence | Status |
|---|-----------------------|----------|--------|
| P-1 | No slice-scale or rehearsal number feeds the memo derivation or the D3 decision. | `validate_memo_inputs` refuses non-`full`; all 76 records `scale='full'`; rehearsal writes to scratch only. | Respected |
| P-2 | No pre-Phase-7 profile or sampling self-time table feeds the gate. | Evidence contains only /usr/bin/time walls and on-CPU probe JSON; no profile table anywhere in the doc or driver math. | Respected |
| P-3 | No Rust source change lands; `src/`, `pyo3/src/`, `examples/` stay clean. | `git diff 078556c..HEAD -- src/ pyo3/src/ examples/` empty; working tree clean. | Respected |
| P-4 | The memo never states GO/NO-GO without both ceilings named and every input cited. | `_assert_memo_contract` requires both ceiling tokens; render shows citations; proof byte-identical. | Respected |
| P-5 | No inflate share without the control correction; no clamping of zero/negative. | Both k carry delta_correction_s and control citations; code stores sign unclamped; tests. | Respected |
| P-6 | No plain-input deletion before provenance / the memo commit. | Provenance committed in 733da76 (prep); memo ff16c08 precedes deletion a46b9ea. | Respected |
| P-7 | No k=31 stage share from the committed k=21 probe. | C k=31 binary = materialized probe sha; every C k=31 JSON asserts k=31. | Respected |
| P-8 | No threshold other than the D-05 bar; idealized never the bar input. | `derive_gate_decision` consumes only the derated `predicted_improvement_pct`; constant 10.0; tests. | Respected |
| P-9 | No A/B rep without the D-08 `-o` output. | 12/12 A/B command lines include `-o`; all carry output_bytes > 0. | Respected |
| P-10 | No Python-surface wall as a decision denominator or dual-surface headline. | No Python arm; decision function reads no Python wall; memo frames Python as context only. | Respected |
| P-11 | No rehearsal number in the gate matrix. | Committed evidence: 0 rehearsal records; rehearsal path writes scratch docs only. | Respected |
| P-12 | No rep skipped; 3 counterbalanced reps per gate arm-k. | 3 reps present for every arm×k; `rotation_schedule` used (3 rounds over five arms). | Respected |
| P-13 | No hand-typed measurement number in the memo. | Memo is byte-identical to a fresh render from the evidence doc (verifier reproduced it). | Respected |
| P-14 | No ROADMAP edit outside the scoped Phase 14 annotation. | Memo commit's ROADMAP diff is exactly one line in the Conditional paragraph. | Respected |
| P-15 | No zlib-rs switch decision in this phase. | No dependency/build change; memo records the revisit condition only. | Respected |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/bench/phase13.py` | Staged stdlib-only measurement driver | ✓ EXISTS + SUBSTANTIVE | 2538 lines; all pinned symbols present; imports bench/merge_characterize/output_stage/preparation helpers; zero `shell=True`. |
| `scripts/bench/tests/test_phase13_driver.py` | Wave-0 unit module | ✓ EXISTS + SUBSTANTIVE | 1349 lines, 80 test methods; executed live: `Ran 80 tests ... OK`, 0 skipped. |
| `scripts/bench/fixtures/phase13_probe_k31.Cargo.lock` | Committed lock fixture | ✓ EXISTS + SUBSTANTIVE | 1847 lines; seeded + sha256-verified before the `--locked` probe build. |
| `scripts/bench/fixtures/phase13_null_consumer.Cargo.lock` | Committed lock fixture | ✓ EXISTS + SUBSTANTIVE | 1848 lines; same provisioning contract. |
| `.planning/phases/13-producer-attribution-research/13-ATTRIBUTION.json` | Full-scale evidence doc | ✓ EXISTS + SUBSTANTIVE | kind `phase13-producer-attribution`, 76 runs (60 gate + 16 excluded), attribution/predicted_win/provenance/prep blocks complete; recomputes exactly. |
| `.planning/phases/13-producer-attribution-research/13-GATE-MEMO.md` | D-02 gate memo | ✓ EXISTS + SUBSTANTIVE | 13,324 B; DECISION: NO-GO; all contract sections present; byte-identical to fresh render. |
| `.planning/phases/13-producer-attribution-research/13-RENDER-PROOF.json` | Byte-identical proof | ✓ EXISTS + SUBSTANTIVE | `byte_identical: true`, matching render sha256s, decision NO-GO, bar 10.0. |
| `.planning/phases/13-producer-attribution-research/13-WRAPUP.md` | D-04 lifecycle record | ✓ EXISTS + SUBSTANTIVE | Explicit deleted paths, sizes, ordering, disk delta, regeneration path, surviving evidence pointers. |
| `.planning/ROADMAP.md` §Phase 14 | Conditional annotation | ✓ EXISTS + SUBSTANTIVE | Names the memo and the recorded NO-GO; one-line scoped diff. |

**Artifacts:** 9/9 verified (0 missing, 0 stubs, 0 orphaned)

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `13-ATTRIBUTION.json` | `scripts/bench/phase13.py` | `run_prep` → `run_measure` → `build_attribution` → `build_predicted_win` → `derive_gate_decision` | ✓ WIRED | Doc is the recorded output of these pure functions; verifier recomputed both blocks from the doc's own records and matched exactly. |
| `13-ATTRIBUTION.json` | v2.0 provenance record | `fingerprint_gate.v2_0_sha256` | ✓ WIRED | 8f38d20c…c87c3d23 equals the binary sha in `10-results-full-k21.json`. |
| `13-GATE-MEMO.md` | `13-ATTRIBUTION.json` | `render_memo_text` (deterministic projection) | ✓ WIRED | Two renders identical and equal to the committed memo; proof hashes match the file. |
| `.planning/ROADMAP.md` | `13-GATE-MEMO.md` | Phase 14 Conditional annotation | ✓ WIRED | Annotation inside the Phase 14 section (between heading and `## Progress`). |
| `scripts/bench/phase13.py` | `merge_characterize.py` / `bench.py` / `output_stage.py` / `prepare_inputs.py` | named imports | ✓ WIRED | Module imports and executes (rehearsal/render/tests all exercised the imported primitives). |
| `materialize_probe_binaries` | committed lock fixtures | seed + sha256 verify before `cargo build --locked` | ✓ WIRED | Code path at phase13.py:578-651; unit tests cover the mismatch refusal. |
| arm A/B/C/D/control records | measured binaries + dataset paths | `command_line`, `binary_sha256`, `input_sha256s` | ✓ WIRED | All input shas match the prep fingerprints; binary shas match each instrument's provenance. |

**Wiring:** 7/7 connections verified

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `13-GATE-MEMO.md` | decision, per-k improvements, stage table, ceilings | `doc['attribution']` / `doc['predicted_win']` ← run records | Yes — recomputed exactly from 60 gate records; no static fallback | ✓ FLOWING |
| `13-ATTRIBUTION.json` | wall_s, probe nanos, peaks | `/usr/bin/time` + probe JSON on the rebuilt stock binary and three fingerprinted probes over real 2.78 GB dataset parts | Yes — 130–178 s walls, 10–113 s probe terms, matching input/binary fingerprints | ✓ FLOWING |
| `13-RENDER-PROOF.json` | render sha256s | `render_memo_text` output | Yes — two independent renders hashed; file hash matches | ✓ FLOWING |
| prep `plain_inputs` | path/size/sha256 | streaming `gunzip -c` writes to disk, then fingerprint | Yes — 76,290,905,669 B total; on-disk sizes matched before deletion; provenance retained | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Driver unit behaviors (gate branches, D-09 arithmetic, model, memo branches, probes, seams) | `python3 -m unittest scripts.bench.tests.test_phase13_driver` | `Ran 80 tests in 0.503s` → `OK` | ✓ PASS |
| Memo determinism + purity of projection | call `render_memo_text(doc)` twice on the committed evidence and diff against the committed memo | identical; sha256 `428d6040…acced48` matches proof and file | ✓ PASS |
| Evidence arithmetic re-derivation | recompute attribution + predicted_win from the committed run records with the documented formulas | every term matched the stored block (9 decimals); decision recomputes to NO-GO | ✓ PASS |
| Provenance validation | `bench.validate_provenance(doc)` on the committed evidence | PASS (7 keys, git_dirty false, sha matches gate) | ✓ PASS |
| Citation integrity | resolve every attribution/predicted-win citation key against the run records | 0 unresolved, 0 k-mismatched | ✓ PASS |

The rehearsal (`python3 scripts/bench/phase13.py --rehearsal`) was deliberately **not** re-run: it rebuilds Rust and would recreate `/tmp/phase13-probe-scratch`, contradicting the phase's committed end state (`scratch_cleaned: true`, scratch root absent). Its chain-proof behaviors are covered by the green unit module (including the full-scale record-count/incremental-write and delete-seam tests) and by the committed full-scale evidence it rehearsed.

### Probe Execution

Not applicable — this phase declares no `scripts/*/tests/probe-*.sh` probes; "probe" in this phase names the measurement instruments (engine probe / null consumer), which are exercised by the driver and whose outputs are recorded in the evidence document (checked above).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `scripts/bench/tests/test_phase13_driver.py` | PEXT-01, PEXT-02 | 80 | 0 | 0 | Value / Behavioral | PASS (two warning-level notes below) |

**Disabled tests on requirements:** 0 → no blocker
**Circular patterns detected:** 0 → no blocker. Expected values are hand-derived for pure functions (e.g. 30+12=42, 120/16=7.5), which proves the formula; the full-scale numbers come from the external measurement run, not from the system under test.
**Insufficient assertions:** 0 blockers. Notes: (a) `test_no_go_fixture_also_exits_zero` flips only `decision` while leaving improvement values inconsistent — it proves the exit-code contract but encodes the unguarded render noted in CR-01 (WARNING); (b) `test_zero_busy_total_bounds_with_interval_and_assumptions` asserts `upper_s <= lower_s`, encoding the inverted wall interval noted in WR-03 (WARNING). Neither affects the committed point-mode evidence.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PEXT-01 | 13-01, 13-02 | Producer stage attribution measured at FULL scale on the shipped engine, both k, fingerprinted builds — stage table (inflate / parse / extract / route-send) via plain-vs-gzip differential plus a pure-read control; slice-scale and pre-Phase-7 profiles never feed the gate | ✓ SATISFIED (granularity decision in Human Verification #2) | 60 full-scale gate records; attribution at both k; pure-read control pair-volume; context/rehearsal structurally excluded; `REQUIREMENTS.md` marks PEXT-01 Complete for Phase 13. |
| PEXT-02 | 13-01, 13-02, 13-03 | Predicted-win model names both ceilings and the D3 go/no-go decision is recorded as the research deliverable | ✓ SATISFIED | Two-ceiling model with citations at both k; committed memo + byte-identical proof, decision NO-GO; ROADMAP annotation; `REQUIREMENTS.md` marks PEXT-02 Complete. |

**Orphaned requirements:** none for Phase 13 — the only IDs mapped to this phase are PEXT-01 and PEXT-02, and both are claimed by plans and accounted for above.

**Coverage:** 2/2 requirements satisfied

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts.
`decision_coverage: {honored: 10, total: 10, not_honored: []}` (gate exit 0, non-blocking).

### Anti-Patterns Found

No debt markers (`TBD`/`FIXME`/`XXX`), no TODO/HACK/PLACEHOLDER, no stub phrases, no empty implementations, and no `shell=True` in the driver or test module. The phase's code-review report (13-REVIEW.md, all 15 findings recorded open in 13-REVIEW-DISPOSITION.md) is advisory for this verification; the verifier judged each against the committed deliverable:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/bench/phase13.py` | 2412-2469 | CR-01: `run_memo` renders stored attribution/decision without re-deriving from cited records | ⚠️ Warning | Does not invalidate this phase: the verifier independently re-derived both blocks from the run records (exact match), the memo re-renders byte-identically, and 80 tests are green. Leaves a future stale/hand-edited-math risk. |
| `scripts/bench/phase13.py` | 859-865 | CR-02: `write_doc` truncates then streams (non-atomic) | ⚠️ Warning | Did not occur: the committed evidence parses and all 76 records are intact. Leaves a crash-during-write risk for future sessions. |
| `scripts/bench/phase13.py` | 1080, 1191-1199, 1568-1573 | WR-02/WR-03: bounds mode can issue a decision from a negative `output_stage_s` and renders an inverted wall interval | ⚠️ Warning | Committed evidence is `mode: point` at both k, so neither path is used by the recorded decision or memo. Affects only a future bounds-mode session. |
| `scripts/bench/phase13.py` | 1686-1692, 2100, 2210-2215, 2297-2354, 2497-2499, 2533-2534 | WR-01/WR-04/WR-05/WR-06/WR-07/WR-08 (unused `--scratch`, hardcoded lifecycle paths, no gzip/probe re-verification at measure, disk guard on the wrong volume, exit-code gaps) | ⚠️ Warning | All confirmed by reading; none manifested in the committed session (input shas all match prep, binaries match their provenance, disk check passed, no malformed-evidence path was taken). Recorded for follow-up. |
| `scripts/bench/phase13.py` | 173, 598-651, 2048 | WR-09: predictable world-writable `/tmp` scratch root without ownership/permission check | ⚠️ Warning | Precondition is a hostile local user on this machine during the session; no evidence of compromise, and the scratch tree is now deleted. |

**Anti-patterns:** 0 blockers, 5 warning-level review findings (advisory; recorded open by the phase's own review disposition).

### Human Verification Required

### 1. Gate memo soundness (D-02 deliverable)

**Test:** Read `.planning/phases/13-producer-attribution-research/13-GATE-MEMO.md` end to end and confirm (a) both ceilings are named with values and arithmetic, (b) every input number carries a citation to a named full-scale run record, (c) the fresh-base statement uses arm-A medians and the v2.0 walls appear only as disclosed-fingerprint corroboration, (d) the NO-GO is consistent with the pre-registered 10.0% bar applied at both k, and (e) the revisit conditions are ones you are willing to hold Phase 14 to.
**Expected:** The memo reads as the decision you accept: NO-GO under the pre-registered 10.0% derated both-k conjunction (9.6235% at k=21, 10.7965% at k=31); Phase 14 stays conditional; PEXT-03/PEXT-04 remain unexecuted by recorded decision.
**Why human:** This is the plan's own Task 1 `<human-check>` (13-03-PLAN.md:184). Automation proves the token/citation contract and byte-identical render, not whether a human will stand behind the decision.

### 2. PEXT-01 parse vs extract granularity

**Test:** Decide whether the combined `parse_extract_s` term (20.9629 s k=21 / 20.8475 s k=31, per locked decision D-09) satisfies PEXT-01's "parse / extract" wording for closure, or whether a future phase must add instrumentation to split them.
**Expected:** Either accept the combined term as the decision-recorded granularity, or carry a follow-up requirement for a parse/extract split. The attribution's answer to where the wall goes remains: inflate 26.25/21.02 s, parse+extract 20.96/20.85 s, route-send 91.80/92.99 s, output stage 22.39/41.84 s.
**Why human:** The shipped engine exposes only `producer_nanos` (documented at `src/count/engine.rs:191-196` as open+parse+extract+routing+sends combined) and per-worker `busy_nanos`; the null consumer times read+parse+extract as one instrument. Separating parse from extract requires Rust changes this measurement-only phase forbids. The choice is scope interpretation, not a code check.

### 3. Prohibition sign-off

**Test:** Review the Prohibitions table above (27 declared statements, 15 unique after dedupe) and confirm each must-NOT is respected by the recorded evidence.
**Expected:** All prohibitions acknowledged as respected; any exception reopened as a gap before the phase closes.
**Why human:** The plans declare these as `verification: judgment`; the must-NOT tier requires explicit human resolution at the end-of-phase checkpoint rather than a silent pass.

### Gaps Summary

**No blocking gaps found.** The phase goal is achieved in the codebase: the full-scale stage attribution exists at both k from fingerprinted builds with a pair-volume pure-read control; the predicted-win model names both ceilings with every input resolved to a named full-scale record; and the D3 decision is a committed, mechanically rendered NO-GO memo whose numbers reproduce exactly from the committed run records.

Three items are surfaced for human decision, none of which is a missing deliverable: the memo's own soundness check (required by the plan), the PEXT-01 parse/extract granularity (a recorded decision, not an implementation gap), and the plan prohibitions' sign-off. The open code-review findings (2 Critical, 9 Warning, 4 Info in 13-REVIEW.md) are robustness gaps in the driver that did not manifest in the committed artefacts; none invalidates the phase goal or the recorded decision, and all remain recorded open in 13-REVIEW-DISPOSITION.md.

---

_Verified: 2026-11-17T15:05:55Z_
_Verifier: Claude (gsd-verifier)_
