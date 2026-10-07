---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "The two merge routes silently disagree on any k-mer count above 1,000,000"
  - id: CR-02
    severity: critical
    disposition: open
    title: "No merge strategy is memory-bounded; the streaming route is not a memory escape"
  - id: WR-01
    severity: warning
    disposition: open
    title: "The admission-control model is ~3–4× below the peak it is meant to bound"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`merge_mode` is silently ignored — and the D-02 rejection is unreachable — whenever `--use-prefix-cache` is set"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`golden_sha256_tests.rs` cannot detect the format drift it claims to guard"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`merge_prefix_buckets` failure swallowing is worse than the record states"
  - id: WR-05
    severity: warning
    disposition: open
    title: "`parse_memory_size` overflows before it validates, and is now reachable from Python"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`merge_databases_streaming` indexes `input_paths[0]` with no empty guard"
  - id: WR-07
    severity: warning
    disposition: open
    title: "`MergeConfig::use_streaming` is a dead, silently-ignored public field"
  - id: WR-08
    severity: warning
    disposition: open
    title: "`concatenate_final_output` loads each entire merged bucket into memory"
  - id: IN-01
    severity: info
    disposition: open
    title: "A 1 GB floor silently overrides a smaller `--max-memory` on the prefix-cache path"
  - id: IN-02
    severity: info
    disposition: open
    title: "The `deferred-items.md` clippy entry is stale"
  - id: IN-03
    severity: info
    disposition: open
    title: "`total_kmers` carries two different meanings across the codebase"
open: 13
total: 13
recorded: 2026-10-07T04:15:07.284Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| CR-02 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
