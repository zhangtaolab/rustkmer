---
phase: 10
review: 10-REVIEW.md
titles: json
findings:
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "The rendered report stated the CLI warmup order and rotation as report-wide methodology"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "Python session documents pinned CLI-document bytes that no longer existed in the tree"
  - id: WR-07
    severity: warning
    disposition: fixed
    title: "The Plan-10-04 summary still reported the superseded 86 B preflight values"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "\"Last commit touching this renderer\" actually named bench.py's last commit"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "README exit contract said exit 2 writes no artifact, but a BLOCKED preflight writes one"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "The published report and verdict are the pre-fix render; the required WR-01 disclosure is absent"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Committed result documents record a warmup order their sessions never ran"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Committed preflight records use the superseded 86 B model"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "The module-identity guard is inert on `python_bench.py`'s controller path"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Committed Python documents pin pre-gate artifacts that are not in the repository"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "Consumed-evidence stages do not pin the k identity of what they consume"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "Non-finite recorded medians are accepted and Infinity yields YES"
  - id: CR-03
    severity: critical
    disposition: fixed
    title: "Verdict trusts recorded medians without checking them against the raw reps"
  - id: CR-04
    severity: critical
    disposition: fixed
    title: "Python preflight gate can be converted from BLOCKED to PROCEED"
  - id: WR-08
    severity: warning
    disposition: fixed
    title: "`threads_resolved` is the requested value, not an observed pool size"
  - id: WR-09
    severity: warning
    disposition: fixed
    title: "Python memory projection is not the \"conservative upper bound\" it claims to be"
  - id: WR-10
    severity: warning
    disposition: fixed
    title: "Full-scale stages do not pin the split-part identity"
  - id: WR-11
    severity: warning
    disposition: fixed
    title: "Atomic publish deletes pre-existing artifacts and its cleanup can mask the real failure"
  - id: WR-12
    severity: warning
    disposition: fixed
    title: "`load_cli_document` accepts a non-CLI session document"
open: 0
total: 19
unparsed: 5
recorded: 2026-11-14T04:00:38.540Z
---

# Phase 10: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-05 | warning | fixed | 10-REVIEW-FIX.md (not in the current review) |
| WR-06 | warning | fixed | 10-REVIEW-FIX.md (not in the current review) |
| WR-07 | warning | fixed | 10-REVIEW-FIX.md (not in the current review) |
| IN-02 | info | fixed | 10-REVIEW-FIX.md (not in the current review) |
| IN-03 | info | fixed | 10-REVIEW-FIX.md (not in the current review) |
| CR-01 | critical | fixed | 10-REVIEW-FIX.iter3.md (not in the current review) |
| WR-01 | warning | fixed | 10-REVIEW-FIX.iter3.md (not in the current review) |
| WR-02 | warning | fixed | 10-REVIEW-FIX.iter3.md (not in the current review) |
| WR-03 | warning | fixed | 10-REVIEW-FIX.iter3.md (not in the current review) |
| WR-04 | warning | fixed | 10-REVIEW-FIX.iter3.md (not in the current review) |
| IN-01 | info | fixed | 10-REVIEW-FIX.iter3.md (not in the current review) |
| CR-02 | critical | fixed | 10-REVIEW-FIX.iter2.md (not in the current review) |
| CR-03 | critical | fixed | 10-REVIEW-FIX.iter2.md (not in the current review) |
| CR-04 | critical | fixed | 10-REVIEW-FIX.iter2.md (not in the current review) |
| WR-08 | warning | fixed | 10-REVIEW-FIX.iter2.md (not in the current review) |
| WR-09 | warning | fixed | 10-REVIEW-FIX.iter2.md (not in the current review) |
| WR-10 | warning | fixed | 10-REVIEW-FIX.iter2.md (not in the current review) |
| WR-11 | warning | fixed | 10-REVIEW-FIX.iter2.md (not in the current review) |
| WR-12 | warning | fixed | 10-REVIEW-FIX.iter2.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
