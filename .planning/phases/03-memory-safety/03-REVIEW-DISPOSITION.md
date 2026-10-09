---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "The failed-bucket \"shard files PRESERVED for recovery\" promise is voided by RAII Drop before the error reaches the caller (carried, still open; the abort message making the false promise is new this round)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "u32 count accumulation can overflow — debug panic, silent wrap in release; the in-memory route saturates (carried, still open)"
  - id: WR-11
    severity: warning
    disposition: open
    title: "The metadata JSON sidecar is written to a path the to-path route guarantees to delete (new this round)"
  - id: WR-12
    severity: warning
    disposition: open
    title: "`ExternalSortMerger::new` panics on an empty input list — public API, unguarded index (new this round; same class as carried WR-06 but a distinct, in-scope site)"
  - id: WR-13
    severity: warning
    disposition: open
    title: "Zero-length merged buckets are deleted even under `--keep-intermediate`, contradicting the flag's documented \"keeps everything\" contract (new this round)"
  - id: WR-14
    severity: warning
    disposition: open
    title: "No k-mer-size range validation — headers with `kmer_size` in 65..=127 or 0 pass every check, then shift-overflow (debug panic) or silently collapse every canonical key to 0 (new this round)"
  - id: IN-02
    severity: info
    disposition: open
    title: "`Drop` logs the wrong directory when `TempDir::close()` fails (carried, still open)"
  - id: IN-03
    severity: info
    disposition: open
    title: "Phase-1 log claims parallel bucketing; the loop is serial (carried, still open)"
  - id: IN-04
    severity: info
    disposition: open
    title: "Dead duplicate shard readers masked by an impl-level `#[allow(dead_code)]` (carried, still open)"
  - id: IN-05
    severity: info
    disposition: open
    title: "`total_kmers` reflects the FIRST input only; `estimated_kmers_per_file` and `num_threads` are never read (carried, still open)"
  - id: IN-07
    severity: info
    disposition: open
    title: "`is_multiple_of` raises the effective MSRV above the documented Rust 1.80+ baseline (carried, still open)"
  - id: IN-08
    severity: info
    disposition: open
    title: "Final prefix-cache output is flushed but never fsync'd, unlike every other artifact in the route (carried, still open)"
  - id: IN-09
    severity: info
    disposition: open
    title: "The 03-16 \"canonicalization failure propagates with `?`\" claim is vacuous (carried, still open)"
  - id: IN-10
    severity: info
    disposition: open
    title: "A streaming-writer refusal aborts the whole merge with no fallback and no remediation hint (new this round)"
  - id: IN-11
    severity: info
    disposition: open
    title: "Two vacuous tests in the module's test module (new this round)"
  - id: CR-01
    severity: critical
    disposition: open
    title: "The 03-16 canonicalization fix holds only for the hashmap bucket writer — the streaming bucket writer still emits non-ascending, un-summed mixed-canonical output under an unconditional `sorted: true` header"
  - id: WR-04
    severity: warning
    disposition: open
    title: "The CLI `--batch-size` flag is a silent no-op (carried from 03-12..03-15 round; file outside this round's scope, unchanged by the delta)"
  - id: WR-05
    severity: warning
    disposition: open
    title: "`--check-compatibility --use-prefix-cache` rejects mixed-canonical input sets that the merge with the same flags accepts (carried; file outside this round's scope, unchanged)"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`validate_merge_compatibility` panics on an empty input slice (carried; file outside this round's scope, unchanged)"
  - id: IN-01
    severity: info
    disposition: open
    title: "`merge_prologue` runs twice on the materializing delegating path (carried; file outside this round's scope, unchanged)"
  - id: IN-06
    severity: info
    disposition: open
    title: "Stale \"24 B/k-mer\" comments contradict the 96 model the same test file asserts (carried, still open)"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Mixed-canonical route writes RAW records while the output header claims canonical (from ANY input) — plus swallowed canonicalization errors (open re-report, prior WR-04)"
  - id: CR-02
    severity: critical
    disposition: open
    title: "Prefix-cache output is bucketed by the LOW byte but written with `sorted: true` — every binary-search consumer silently returns wrong results"
  - id: CR-03
    severity: critical
    disposition: open
    title: "Streaming merge route performs no cross-input k-mer-size/canonical validation — Python API silently merges incompatible databases"
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
open: 28
total: 28
recorded: 2026-10-09T12:21:37.511Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-11 | warning | open | - |
| WR-12 | warning | open | - |
| WR-13 | warning | open | - |
| WR-14 | warning | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |
| IN-10 | info | open | - |
| IN-11 | info | open | - |
| CR-01 | critical | open | - (not in the current review) |
| WR-04 | warning | open | - (not in the current review) |
| WR-05 | warning | open | - (not in the current review) |
| WR-06 | warning | open | - (not in the current review) |
| IN-01 | info | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |
| WR-03 | warning | open | - (not in the current review) |
| CR-02 | critical | open | - (not in the current review) |
| CR-03 | critical | open | - (not in the current review) |
| WR-07 | warning | open | - (not in the current review) |
| WR-08 | warning | open | - (not in the current review) |
| WR-09 | warning | open | - (not in the current review) |
| WR-10 | warning | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
