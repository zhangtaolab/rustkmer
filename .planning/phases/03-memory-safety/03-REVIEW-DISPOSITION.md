---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "`read_batch_from_file_sync` drops the partial-record tail at every batch boundary and swallows read errors — silent shard corruption above ~4 MB"
  - id: CR-02
    severity: critical
    disposition: open
    title: "Prefix-cache output is bucketed by the LOW byte but written with `sorted: true` — every binary-search consumer silently returns wrong results"
  - id: CR-03
    severity: critical
    disposition: open
    title: "Streaming merge route performs no cross-input k-mer-size/canonical validation — Python API silently merges incompatible databases"
  - id: WR-01
    severity: warning
    disposition: open
    title: "`StreamingMergeIterator`'s `pending_error` machinery is dead code and the iterator is not actually finished after an `Err`"
  - id: WR-02
    severity: warning
    disposition: open
    title: "u32 count overflow in prefix-cache bucket merges — panics in debug, wraps in release; in-memory route saturates"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`merge_single_prefix_streaming` peek-and-add strands the rest of a file's run on within-file duplicate k-mers"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Prefix-cache mixed-canonical merge writes raw (non-canonical) records while the output header claims `canonical` from input[0]"
  - id: WR-05
    severity: warning
    disposition: open
    title: "CLI merge fully materializes every input database just to validate — including on `--use-prefix-cache`, the memory-bounded route it exists for"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Compat-shim fallback file leaks on error and is never swept"
  - id: WR-07
    severity: warning
    disposition: open
    title: "`PyDatabase.dump(limit=None, offset>0)` overflows `offset + usize::MAX` — panic in debug, empty result in release"
  - id: WR-08
    severity: warning
    disposition: open
    title: "`PyDatabase.query_exact` in MemoryMapped mode always returns count 0 / found False"
  - id: WR-09
    severity: warning
    disposition: open
    title: "`from_file_path` pre-reserves `header.total_kmers` entries — crafted header aborts the process instead of returning an error"
  - id: WR-10
    severity: warning
    disposition: open
    title: "`frequency_distribution` zero-fills `min_count..=max_count` — unbounded allocation up to ~4.3 billion entries"
  - id: IN-01
    severity: info
    disposition: open
    title: "`Drop for ExternalSortMerger` logs the wrong directory when `close()` fails"
  - id: IN-02
    severity: info
    disposition: open
    title: "`merge_databases` runs `merge_prologue` twice per call via delegation"
  - id: IN-03
    severity: info
    disposition: open
    title: "Stale admission-model constant copied into the integration tests"
  - id: IN-04
    severity: info
    disposition: open
    title: "Dead magic-number clamp in `get_entry_by_index`"
  - id: IN-05
    severity: info
    disposition: open
    title: "`DatabaseStreamIterator::header()` fabricates an invalid header"
  - id: IN-06
    severity: info
    disposition: open
    title: "`extract_by_prefix` reloads the entire database from disk on every call"
  - id: IN-07
    severity: info
    disposition: open
    title: "`test_prefix_extraction_values` tests nothing about the production prefix extraction"
open: 20
total: 20
recorded: 2026-10-08T16:02:21.748Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| CR-02 | critical | open | - |
| CR-03 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| WR-09 | warning | open | - |
| WR-10 | warning | open | - |
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
