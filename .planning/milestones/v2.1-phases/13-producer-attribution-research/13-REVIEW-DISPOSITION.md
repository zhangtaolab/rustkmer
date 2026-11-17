---
phase: 13
review: 13-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Memo renders stored attribution/decision without re-deriving it from the cited run records"
  - id: CR-02
    severity: critical
    disposition: open
    title: "Evidence-document writes are non-atomic — a crash during any of the 77 writes destroys the whole session record"
  - id: WR-01
    severity: warning
    disposition: open
    title: "`--scratch` is parsed but never used; every scratch path is hardcoded"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Bounds mode still issues a GO/NO-GO from inputs the code declares invalid; a negative `output_stage_s` is accepted unflagged"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Memo renders an inverted wall interval in bounds mode"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Memo lifecycle/deletion record hardcodes `PLAIN_INPUTS_DIR` / `DATASET_DIR` instead of the recorded paths"
  - id: WR-05
    severity: warning
    disposition: open
    title: "Measure re-verifies the plain inputs against prep but never the gzip sources — `prep[\"gzip_inputs\"]` is dead provenance"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Probe binaries are hashed at prep and never re-verified at measure"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Disk guard checks the source volume, not the volume that receives the plain files"
  - id: WR-08
    severity: warning
    disposition: open
    title: "`main()` maps only OSError/RuntimeError/ValueError to exit 2; several malformed-evidence paths raise KeyError/AttributeError as tracebacks with exit 1"
  - id: WR-09
    severity: warning
    disposition: open
    title: "Predictable world-writable scratch root reused without an ownership/permission check"
  - id: IN-01
    severity: info
    disposition: open
    title: "`scratch_cleaned` is a dead field"
  - id: IN-02
    severity: info
    disposition: open
    title: "Null-consumer `windows` is not validated"
  - id: IN-03
    severity: info
    disposition: open
    title: "Machine-specific absolute paths as committed defaults"
  - id: IN-04
    severity: info
    disposition: open
    title: "(necessity) Duplicate `validate_provenance(doc)` with no mutation in between"
open: 15
total: 15
recorded: 2026-11-17T15:00:10.211Z
---

# Phase 13: Code Review Disposition

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
| WR-09 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
