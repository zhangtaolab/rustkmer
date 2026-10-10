---
phase: 04
review: 04-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Renderer hard-codes a measurement literal, violating the T-04-07 \"zero measurement literals\" contract it implements"
  - id: WR-01
    severity: warning
    disposition: open
    title: "make_slice.sh swallows gunzip failure — corrupt input yields exit 0 and a partial slice"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`--render-report` without `--out` clobbers the default measurement results file"
  - id: WR-03
    severity: warning
    disposition: open
    title: "A typo'd or missing explicit `--input` silently degrades to a synthetic run"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`total_sequence_length` and `average_quality` bypass the compressed opener — `.fq.gz` parsed as raw deflate bytes"
  - id: WR-05
    severity: warning
    disposition: open
    title: "benchmark.yml cache key hashes a file that does not exist in CI (Cargo.lock is gitignored)"
  - id: WR-06
    severity: warning
    disposition: open
    title: "MultiGzDecoder hard-fails on trailing bytes after the last member — stricter than GzDecoder and than gzip itself"
  - id: WR-07
    severity: warning
    disposition: open
    title: "NaN/Infinity medians pass the gate as \"ok\" — comparator fails open on non-finite data"
  - id: IN-01
    severity: info
    disposition: open
    title: "Dead validation branch in gen_synthetic.py"
  - id: IN-02
    severity: info
    disposition: open
    title: "bench.py exit-code contract is ambiguous at the edges"
  - id: IN-03
    severity: info
    disposition: open
    title: "Methodology schedule sorts round keys lexicographically"
  - id: IN-04
    severity: info
    disposition: open
    title: "Duplicate or tool-less arms collapse silently in compare.py's dict build"
  - id: IN-05
    severity: info
    disposition: open
    title: "test_schema.py's real-run test fails confusingly on a fresh clone"
  - id: IN-06
    severity: info
    disposition: open
    title: "No timeout on measured subprocesses"
  - id: IN-07
    severity: info
    disposition: open
    title: "Leading-hyphen paths pass validate_path and reach argv positions where tools parse options"
open: 15
total: 15
recorded: 2026-10-10T19:08:52.731Z
---

# Phase 04: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
