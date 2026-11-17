---
status: testing
phase: 13-producer-attribution-research
source: [13-VERIFICATION.md]
started: 2026-11-17T15:10:00Z
updated: 2026-11-17T15:10:00Z
---

## Current Test

number: 1
name: Memo soundness
expected: |
  The memo reads as a decision you accept as the D-02 gate deliverable: NO-GO under the pre-registered 10.0% derated both-k conjunction (9.6235% at k=21, 10.7965% at k=31), with Phase 14 remaining conditional and PEXT-03/PEXT-04 unexecuted by recorded decision.
awaiting: user response

## Tests

### 1. Memo soundness
expected: Read .planning/phases/13-producer-attribution-research/13-GATE-MEMO.md end to end and confirm (a) both ceilings are named with values and arithmetic, (b) every input number carries a citation to a named full-scale run record, (c) the fresh-base statement uses arm-A medians and the v2.0 walls appear only as disclosed-fingerprint corroboration, (d) the NO-GO is consistent with the pre-registered 10.0% bar applied at both k, and (e) the revisit conditions are the ones you are willing to hold Phase 14 to.
result: [pending]

### 2. PEXT-01 parse vs extract granularity
expected: Either accept the combined parse_extract_s as PEXT-01's parse+extract measurement at the decision-recorded granularity (the phase is measurement-only and explicitly forbids Rust changes), or carry a follow-up requirement for parse/extract instrumentation; either way the attribution's answer to "where does the wall go" stands (inflate 26.25/21.02 s, parse+extract 20.96/20.85 s, route-send 91.80/92.99 s, output stage 22.39/41.84 s).
result: [pending]

### 3. Prohibition sign-off
expected: Every prohibition is acknowledged as respected (27 declared, 15 unique after dedupe; table in 13-VERIFICATION.md); any that cannot be so acknowledged is re-opened as a gap before the phase is closed. In particular: no slice-scale number in the gate, no Rust source change, no v2.0 wall as a denominator, no rep skipped, no plain-input deletion before the memo commit, no threshold other than D-05.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
