---
phase: 11
review: 11-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Full-scale comparison path runs the in-memory dump-vs-dump gate — OOM after hours of measurement, results lost"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`--render-report` without `--out` writes the Markdown report over the default results.json"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`--merge-input` is silently ignored in synthetic mode, violating the helper's never-silent contract"
  - id: WR-04
    severity: warning
    disposition: open
    title: "README rehearsal Stage A/B commands are not runnable as documented and cannot reproduce the recorded rehearsal"
  - id: IN-01
    severity: info
    disposition: open
    title: "Real-run tests in test_schema.py lack the release-binary skip guard"
  - id: IN-02
    severity: info
    disposition: open
    title: "Non-dict JSON evidence/manifest files crash with AttributeError instead of the exit-2 contract"
  - id: IN-03
    severity: info
    disposition: open
    title: "Disk-floor protocol test mocks attempt_cache_purge with the wrong return shape"
  - id: IN-04
    severity: info
    disposition: open
    title: "Contradictory Python floor claims — README says 3.10+, Phase-11 scripts require 3.11+"
  - id: IN-05
    severity: info
    disposition: open
    title: "`cleanup_scratch` rmtree's the entire `--scratch` root with no ownership guard"
open: 9
total: 9
recorded: 2026-11-16T17:38:14.740Z
---

# Phase 11: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved.
