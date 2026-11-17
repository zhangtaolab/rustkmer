---
status: complete
phase: 13-producer-attribution-research
source: [13-VERIFICATION.md]
started: 2026-11-17T15:10:00Z
updated: 2026-11-17T15:27:52.538Z
---

## Current Test

[testing complete]

## Tests

### 1. Memo soundness
expected: Read .planning/phases/13-producer-attribution-research/13-GATE-MEMO.md end to end and confirm (a) both ceilings are named with values and arithmetic, (b) every input number carries a citation to a named full-scale run record, (c) the fresh-base statement uses arm-A medians and the v2.0 walls appear only as disclosed-fingerprint corroboration, (d) the NO-GO is consistent with the pre-registered 10.0% bar applied at both k, and (e) the revisit conditions are the ones you are willing to hold Phase 14 to.
result: pass
reported: "Agent audit performed at user's request (2026-11-17)."
notes: "Evidence chain reproduced from 13-ATTRIBUTION.json with committed scripts/bench/phase13.py: build_attribution and build_predicted_win match the published blocks exactly at both k (0 mismatches, 60 gate records all scale=full); 16/16 stage-row citation lists match the evidence; memo re-renders byte-identically (sha256 428d6040…, matches first_render_sha256); derive_gate_decision returns NO-GO under the pinned 10.0% derated both-k conjunction. Non-blocking caveats: (i) 13-RENDER-PROOF.json evidence.sha256 (4a0ad6e7…) is stale vs the committed 13-ATTRIBUTION.json (94494ba5…) — the only change is scratch_cleaned false→true from the D-04 wrap-up commit, and the memo is unaffected; (ii) the memo intro's 'every number … cites a named full-scale run record' overclaims for the pinned v2.0/Python disclosure constants and derived diagnostics (gate inputs are all cited); (iii) §3 names the ceilings' divisors and the max()+output composition but does not spell out the intermediate serial+parse/extractors addition."

### 2. PEXT-01 parse vs extract granularity
expected: Either accept the combined parse_extract_s as PEXT-01's parse+extract measurement at the decision-recorded granularity (the phase is measurement-only and explicitly forbids Rust changes), or carry a follow-up requirement for parse/extract instrumentation; either way the attribution's answer to "where does the wall go" stands (inflate 26.25/21.02 s, parse+extract 20.96/20.85 s, route-send 91.80/92.99 s, output stage 22.39/41.84 s).
result: pass
reported: "Agent audit performed at user's request (2026-11-17); combined granularity ACCEPTED."
notes: "Accepted at the pre-registered D-09 granularity. Verified: EngineDiagnostics exposes only wall_nanos / producer_nanos (open+parse+extract+routing+sends combined) / per-worker busy_nanos (src/count/engine.rs:185-204); the arm-D null consumer times the whole Reader->for_each_window loop as one instrument, with no separate read/parse/extract timers (scripts/bench/phase13.py:445-520); P-3's 'no Rust source change' covers src/, pyo3/src/, examples/ only (13-VERIFICATION.md). Decision robustness: under the pre-registered derated model (parallelizable floor = serial_terms + parse_extract/(16*0.5)), splitting out any serial parse term can only INCREASE the predicted wall, so the granularity choice cannot flip NO-GO; and the combined term already answers 'where the wall goes' — route-send is ~82% of the plain producer probe (91.80/92.99 s vs 20.96/20.85 s parse+extract), so parse vs extract is not the dominant unknown. Optional (not a gap, not gate-blocking): if a revisit condition ever fires and Phase 14 is re-planned, add read-only vs read+extract timing to the probe fixture (probe-only, no engine change) to split the term."

### 3. Prohibition sign-off
expected: Every prohibition is acknowledged as respected (27 declared, 15 unique after dedupe; table in 13-VERIFICATION.md); any that cannot be so acknowledged is re-opened as a gap before the phase is closed. In particular: no slice-scale number in the gate, no Rust source change, no v2.0 wall as a denominator, no rep skipped, no plain-input deletion before the memo commit, no threshold other than D-05.
result: pass
reported: "Agent audit performed at user's request (2026-11-17); all 15 deduped prohibitions verified respected."
notes: "Independently verified against code/data/git, not the report table. P-1/P-11: 76/76 records scale=full, 0 rehearsal. P-2: no profile/self-time table in memo or evidence. P-3: git diff 078556c..HEAD -- src/ pyo3/src/ examples/ empty; working tree clean. P-4: _assert_memo_contract pins both ceilings + citations; memo passes. P-5: inflate_s = raw_a_minus_b_s - delta_correction_s, no clamp (both k present). P-6: commit order 733da76 (prep/provenance) -> ff16c08 (memo) -> a46b9ea (deletion); CRR1936095-plain no longer exists. P-7: C k=31 records all binary e56082ed and probe k==31; k=21 committed probe has no k field and is governed by registry build-time k=21 (parse_probe_output). P-8: derive_gate_decision reads predicted_improvement_pct only, >= at both k, idealized never read. P-9: 12/12 A/B command lines carry -o, 0 zero output_bytes. P-10: Python walls appear only in render text; no Python arm exists. P-12: reps {1,2,3} present for every arm x k. P-13: memo re-renders byte-identically. P-14: memo commit's ROADMAP diff is one modified line. P-15: no Cargo.toml/Cargo.lock change in the phase range. Declaration count matches: 10+10+7 = 27 statements, 15 unique after semantic dedupe."

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
