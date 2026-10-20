---
phase: 04
review: 04-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "README ships eight `count` commands the CLI rejects (positional input)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "README documents a nonexistent `--kmer-size` long flag"
  - id: WR-03
    severity: warning
    disposition: open
    title: "CONTRIBUTING.md states the opposite of what CI now does (stale within the same review window)"
  - id: WR-04
    severity: warning
    disposition: open
    title: "docs/mkdocs.yml nav references four files that do not exist — docs build cannot pass"
  - id: WR-05
    severity: warning
    disposition: open
    title: "docs site footer PyPI link is a 404"
  - id: WR-06
    severity: warning
    disposition: open
    title: "\"Verify Installation\" snippet is a Python syntax error"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Migration table documents CLI commands the CLI rejects"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Example scripts point users at guide documents that do not exist"
  - id: IN-01
    severity: info
    disposition: open
    title: "docs/mkdocs.yml declares the `search` plugin twice; most of the docs tree is absent from nav"
  - id: IN-02
    severity: info
    disposition: open
    title: "docs/README.md example treats a PyQueryResult as always-truthy"
  - id: IN-03
    severity: info
    disposition: open
    title: "demo_performance.py — misleading unit name and inconsistent zero-guard"
  - id: IN-04
    severity: info
    disposition: open
    title: "Inconsistent GitHub org across the doc corpus"
  - id: IN-05
    severity: info
    disposition: open
    title: "mkdocs preview server binds all interfaces"
  - id: IN-06
    severity: info
    disposition: open
    title: "Uninterpolated `{route}` placeholders in expect_err messages"
  - id: IN-09
    severity: info
    disposition: open
    title: "Fingerprint-less results files now pass through the fingerprints section silently"
  - id: CR-02
    severity: critical
    disposition: open
    title: "Windows clippy gate is red at HEAD — un-gated measurement helpers are dead code under the Windows test gating (CI merge gate failing)"
  - id: IN-08
    severity: info
    disposition: open
    title: "The advisory-mode PASS summary line is not pinned by any test"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Renderer hard-codes a measurement literal, violating the T-04-07 \"zero measurement literals\" contract it implements"
  - id: IN-07
    severity: info
    disposition: open
    title: "Leading-hyphen paths pass validate_path and reach argv positions where tools parse options"
open: 18
total: 19
recorded: 2026-10-20T11:37:14.347Z
---

# Phase 04: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
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
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-09 | info | open | - (not in the current review) |
| CR-02 | critical | open | - (not in the current review) |
| IN-08 | info | open | - (not in the current review) |
| CR-01 | critical | fixed | bb5ccb0 (user-approved during UAT: figure now derived from fingerprinted input size; re-render byte-identical) (not in the current review) |
| IN-07 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
