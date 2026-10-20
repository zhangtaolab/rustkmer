---
status: completed
phase: 04-benchmark-validation
source: [04-VERIFICATION.md]
started: 2026-10-10T19:20:51Z
updated: 2026-10-20T12:45:00Z
---

## Current Test

number: 1
name: Decide the BENCH-02 milestone outcome at milestone close (/gsd-complete-milestone)
expected: |
  A human decision on the measured NO verdict: ship v1.0 on the k=31 result with k=21 documented, or plan a k=21 performance investigation first. The phase's own decision rule (every rustkmer count-arm median wall <= jellyfish median wall in every full-scale table) yields k=31 YES (-41.4%/-42.4% wall, -34% RSS) and k=21 NO (+420%/+408% wall), overall NO, measured on the user-approved CRR2044018 substitute with cold-cache partially satisfied.
awaiting: none (resolved 2026-10-20 at /gsd-complete-milestone)

## Tests

### 1. Decide the BENCH-02 milestone outcome at milestone close (/gsd-complete-milestone)
expected: A human decision on the measured NO verdict: ship v1.0 on the k=31 result with k=21 documented, or plan a k=21 performance investigation first. The phase's own decision rule (every rustkmer count-arm median wall <= jellyfish median wall in every full-scale table) yields k=31 YES (-41.4%/-42.4% wall, -34% RSS) and k=21 NO (+420%/+408% wall), overall NO, measured on the user-approved CRR2044018 substitute with cold-cache partially satisfied.
result: Passed — user decision 2026-10-20 (milestone close): accept as tech debt and ship v1.0 on the k=31 result; k=21 (~5x slower than jellyfish2) recorded as a Known Gap in MILESTONES.md. REQUIREMENTS.md BENCH-02 checkbox reverted to unchecked with the measured outcome noted (W2 contradiction resolved); v2 candidates already staged (MINIM-01..03 minimizer partitioning, BENCH-V2-01 KMC3 comparison).

### 2. Triage the red benchmark.yml darwin leg on origin/dev (run 38047563014 at 437cec6, 2026-10-10)
expected: count-B median_peak_rss_bytes breached +24.56% (2.34 GB -> 2.91 GB, threshold 15%) while walls dropped 39-55% on the same run — consistent with darwin runner-class variance, the documented weakness whose escape hatches (documented baseline regeneration in scripts/bench/README.md, or the same-job base-ref upgrade path) exist. Note: local dev is 9 commits ahead of origin/dev (the phase's evidence commits, including the 8102985 src/io/fastq.rs MultiGzDecoder fix, are unpushed), so the final tree has not yet been gated in CI.
result: Passed — accepted as darwin runner-class variance (user decision 2026-10-20): RSS breach with simultaneous wall improvement on the same run matches the documented weakness; escape hatches in scripts/bench/README.md remain available. dev pushed 2026-10-20 (764f53f..659162f, 46 commits); the first post-push CI run on the full tip is authoritative.

### 3. Treat the flagged prohibition P7 (04-04: report contains no hand-edited measurement numbers) as partially unverified — review CR-01 in 04-REVIEW-DISPOSITION.md
expected: A human accepts, fixes, or waives CR-01 (severity critical, disposition open): the renderer's _methodology_lines hard-codes '220,028 k-mers' — a measured count from the discarded attempt-1 run that exists in no committed JSON. All headline medians, verdict inputs, and per-rep figures DO render mechanically (byte-identity verified independently); the literal sits in a narrative methodology sentence about a superseded attempt and cannot influence the verdict.
result: Passed — resolved by fix before close: CR-01 disposition is `fixed` in 04-REVIEW-DISPOSITION.md (commit bb5ccb0, user-approved during UAT — the figure is now derived from the fingerprinted input size; re-render is byte-identical). No hand-edited measurement literal remains; user confirmed no further action needed (2026-10-20).

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
