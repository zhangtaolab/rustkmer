---
phase: 03-memory-safety
reviewed: 2026-10-07T04:07:16Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - Cargo.toml
  - pyo3/src/database.rs
  - pyo3/tests/test_database_merge.py
  - src/cli/commands/merge.rs
  - src/database/format.rs
  - src/database/mod.rs
  - src/database/prefix_cache_merge.rs
  - src/database/streaming_merge.rs
  - src/database/temp_lifecycle.rs
  - src/hash/key.rs
  - src/hash/mod.rs
  - src/hash/table.rs
  - src/io/fasta.rs
  - src/io/fastq.rs
  - src/lib.rs
  - tests/dense_differential_tests.rs
  - tests/dense_merge_integration_tests.rs
  - tests/dense_proptest_tests.rs
  - tests/golden_sha256_tests.rs
  - tests/merge_cleanup_tests.rs
  - tests/merge_routing_tests.rs
findings:
  critical: 2
  warning: 8
  info: 3
  total: 13
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-10-07T04:07:16Z
**Depth:** standard (from `workflow.code_review_depth`)
**Files Reviewed:** 21
**Status:** issues_found

## Scope Resolution

Scope was resolved by the workflow's three-tier precedence, not by hand-picking:

- **Tier 2 (SUMMARY.md):** 23 unique paths extracted from the five `03-0N-SUMMARY.md`
  artifacts (`key_files.created` / `key_files.modified`).
- **Tier 3 (`gsd check evaluation-scope --phase 03`):** `status: resolved`,
  `source: task-commits`, 9 task commits, 21 files. `outsideUnion: []`,
  `unreachable: []`, `missingOnDisk: []`.
- **Cross-check (#2666):** all 21 resolver paths were already present in the
  SUMMARY scope — `MISSING_FROM_SUMMARY` was empty, so the SUMMARY extract did not
  mask part of the phase. The two extra SUMMARY entries were `.planning/` paths,
  dropped by the D-03 exclusion step.
- `LAST_REVIEW_COMMIT` was empty (first review of this phase), so no incremental
  narrowing applied. `DIFF_BASE = 6230ba9ddc1b313a0b284ecb6b67d25ca84a3438`.

**Deviation recorded for auditability.** The workflow's `resolve_depth` guard
returned `DEPTH_OK=false` with `{"reason":"not_an_array"}` and, read literally,
mandates `exit 1` with no REVIEW.md. That false positive is a quoting artifact of
the guard's own default injection: `workflow.code_review_depth_overrides` is unset
here (`config-get` → "Key not found"; global `~/.gsd/defaults.json` carries only
`resolve_model_ids`/`runtime`), so the `|| echo '[]'` path is not taken, and
`config-get ... --default '[]' --raw` emits the JSON-*string* `"[]"`, which
`JSON.parse` yields as a string rather than an array. Proof that this is not a
configured-sensitive-path policy being downgraded: (a) with a correctly-typed
empty array the resolver returns `{ok:true, depth:"standard", source:"config"}`;
(b) the guard still fires correctly on a genuinely malformed policy
(`src/**` → `paths_malformed`). The guard's documented intent — never silently
review a *configured* depth policy at `standard` — does not apply when no policy
exists. Review proceeded at `standard`, the depth the project's own
`workflow.code_review_depth: "standard"` selects. **This is a GSD tooling bug
worth filing separately: the guard makes `/gsd-code-review` unable to run in any
project that has not opted into per-path depth overrides.**

## Summary

Twenty-one files reviewed at standard depth, spanning the merge-routing core
(`src/database/format.rs`), the external-sort merge
(`src/database/prefix_cache_merge.rs`), the streaming merge
(`src/database/streaming_merge.rs`), the new temp lifecycle
(`src/database/temp_lifecycle.rs`), the dense key (`src/hash/key.rs`,
`src/hash/table.rs`), the PyO3 surface (`pyo3/src/database.rs`), and six test
binaries.

The engineering quality is high and unusually well-documented. `KmerKey`'s
narrowing contract is stated with its exact preconditions and its failure mode
(`src/hash/key.rs:59-73`); `temp_lifecycle.rs` explains *why* RAII alone is
insufficient under `panic = "abort"` before providing the sweep (lines 10-26);
`merge_cleanup_tests.rs` is candid that it cannot test the abort half and names
the sweep test as the real protection. `dense_differential_tests.rs` compares at
the decoded-string level against an independent oracle with the reasoning for
each choice recorded. The two pre-existing streaming data-loss bugs fixed in
03-01 (heap-refill ordering, microsecond chunk-name collision) are both genuinely
correct in the current code — I traced the refill-before-emit reordering at
`streaming_merge.rs:379-424` and it is right.

Two Critical findings undercut the phase's two headline claims.

**CR-01** is the more serious: the two merge routes that this phase deliberately
unified behind one `max_memory` / `merge_mode` API return **different count
values for the same input**, depending only on which route the budget selects.
This is not a hypothetical — it follows from `KmerEntry::read_from`'s
endianness heuristic interacting with the streaming path's double read, and it is
reproducible arithmetically from the source with no execution required. It is
pre-existing in origin, but the phase is what made both routes reachable through
one budget-driven entry point, so it is newly load-bearing.

**CR-02** is that "bounded-memory merge" is not achieved: every one of the three
merge strategies materializes whole databases in RAM, so the route chosen for
over-budget merges is *not* the memory-safe one. The D-01 fix was applied
precisely and only to the estimator — `estimate_total_kmers` — while the same
`from_file_path` materialization the fix removed from the estimator survives
unaltered in the three functions the estimator routes into. `WR-01` quantifies
why this is not caught by the admission check.

The `.rkdb` v2 byte-identity claim is **true by construction but not actually
verified by the test that claims to verify it** (`WR-03`). I did not take it on
faith and it does hold — `KmerKey::U64 → u128` is a lossless zero-extension, and
for k ≤ 32 the encoder bound is `2^(2k) ≤ 2^64`, so `value <= u64::MAX` holds
with equality at k=32 — but `golden_sha256_tests.rs` re-hashes committed Phase-1
fixture *files* against a committed Phase-1 *manifest*. I confirmed by `git` that
neither was touched anywhere in `6230ba9..HEAD` (last modified in `12caa42`,
Phase 1). The test therefore passes identically whether or not the write path is
correct, and its own doc comment's claim that the pre/post passes form "a
differential rather than a tautology" is false.

Seven of the eight known deferred items were re-examined rather than assumed;
one (`merge_prefix_buckets` swallowing bucket failures) is **worse than recorded**
and is escalated as `WR-04` with two aggravating factors the record omits.

No source file, test, `Cargo.toml`, `STATE.md`, or `ROADMAP.md` was modified by
this review. `cargo check --all-targets` was run read-only and passes clean.

---

## Critical Issues

### CR-01: The two merge routes silently disagree on any k-mer count above 1,000,000

**File:** `src/database/format.rs:216-238` (origin), route divergence surfaces at `src/database/streaming_merge.rs:94` + `:314`
**Severity:** Critical — silent data corruption, and a route-dependent divergence between two code paths this phase unified behind one API.

`KmerEntry::read_from` does not perform a plain little-endian read. It reads four
bytes and applies a heuristic:

```rust
let count_le = u32::from_le_bytes(count_bytes);
let count_be = u32::from_be_bytes(count_bytes);
// If little-endian gives an unreasonable count (> 1M), use big-endian
let count = if count_le > 1_000_000 { count_be } else { count_le };
```

`write_to` (line 211) always emits `write_u32::<LittleEndian>` — the documented
v2 layout. So for any count above 1,000,000 the reader reinterprets
correctly-written bytes and returns a byte-swapped value. Confirmed
arithmetically against the actual on-disk encoding:

| true count | on-disk bytes | `read_from` returns |
|---|---|---|
| 1,000,000 | `40420f00` | 1,000,000 (ok) |
| 1,000,001 | `41420f00` | 1,094,848,256 |
| 2,000,000 | `80841e00` | 2,156,142,080 |
| 16,777,216 | `00000001` | 1 |
| 4,000,000,000 | `00286bee` | 2,649,070 |

The phase then makes this a **route-dependent** bug. `PyDatabase.merge` (MERGE-04)
and `--merge-mode` both select between the in-memory and streaming routes using
one budget. Those two routes apply the heuristic a *different number of times*:

- **In-memory route:** `from_file_path` → one `read_from` (`format.rs:328`).
  A single swap. Count 2,000,000 → **2,156,142,080**.
- **Streaming route:** `DatabaseStreamIterator::next` reads the input
  (`streaming_merge.rs:94`, swap #1), writes the sorted chunk little-endian
  (`streaming_merge.rs:272`), and `merge_sorted_chunks` reads the chunk back
  (`streaming_merge.rs:314`, swap #2). Two swaps cancel — accidentally correct.

Result: for count 2,000,000 the in-memory route returns 2,156,142,080 and the
streaming route returns 2,000,000. **The same input merged under the same
`max_memory` yields different data depending only on which route the budget
picked.** Both routes are also individually wrong in some cases (16,777,216 →
`01000000` swaps to 1, and 1 is not > 1M so it does not swap back — both routes
return 1).

This is precisely the failure mode the phase's own contract test is built to
catch: `pyo3/tests/test_database_merge.py:230`
`test_streaming_and_inmemory_routes_produce_identical_data` asserts
`streaming_counts == inmemory_counts`. It passes only because every fixture count
is far below 1,000,000, so the heuristic never engages. The test is correct; it
just cannot reach the bug.

Origin is pre-existing (`a4f13bb0`, 2025-11-28) and is **not** a defect this
phase introduced. It is raised as Critical because the phase routes large merges
through this reader by default, because a `.rkdb` merge that silently rewrites
counts is a data-loss risk by the taxonomy, and because the phase's verification
strategy structurally cannot see it.

**Fix.** Delete the heuristic — `read_from` must be a plain little-endian read
matching `write_to`:

```rust
let mut count_bytes = [0u8; 4];
reader.read_exact(&mut count_bytes)?;
let count = u32::from_le_bytes(count_bytes);
```

Then add a regression test that round-trips counts at and above the old
threshold (`1_000_000`, `1_000_001`, `2_000_000`, `16_777_216`) through
`write_to` → `read_from`, and extend the streaming-vs-in-memory parity test to
use at least one fixture whose count exceeds 1,000,000. If a legacy
big-endian-written file genuinely must be readable, that compatibility belongs in
an explicit, opt-in migration keyed off the header version — not in an
unannounced per-record heuristic that fires on valid input.

### CR-02: No merge strategy is memory-bounded; the streaming route is not a memory escape

**File:** `src/database/format.rs:852` (primary), plus `:870-877`, `:941-945`, `src/database/prefix_cache_merge.rs:76` and `:82-86`
**Severity:** Critical — the phase's central deliverable is not delivered, and over-budget merges are routed to a path that OOMs at least as hard as the one they avoided.

D-01 correctly diagnosed that "the function whose whole job is to prevent OOM
was itself the OOM": `estimate_total_kmers` used to call `from_file_path` per
input. `from_file_path` loads every entry (`format.rs:326-335`,
`Vec::with_capacity(total_kmers)` then a read loop). The fix made the estimator
header-only — excellent, and correctly unit-tested.

But the same materialization survives in all three strategies the estimator
routes into:

1. **Streaming** (`format.rs:852`):
   ```rust
   let first_db = RKDatabase::from_file_path(&input_paths[0])?;
   let kmer_size = first_db.kmer_size();
   let canonical = first_db.is_canonical();
   ```
   The *only* reason the first database is loaded is to read two header fields.
   This is the path chosen precisely when the inputs **do not fit** in the budget.
   It then also accumulates the entire merged output in RAM at `:870-877`
   (`sorted_kmers: Vec<(u128, u32)>`), and `from_kmer_pairs` builds a third
   full copy (`:466-469`). So "streaming" holds roughly 2–3× the whole dataset
   at peak — strictly worse than the in-memory path it replaced.

2. **In-memory** (`format.rs:941-945`) loads *every* input into a `Vec<RKDatabase>`
   and holds them alive while building the accumulator, the sorted vector, and
   the entry vector.

3. **Prefix cache** loads every input at `format.rs:1048-1052` into `db_refs`,
   which stays in scope through the final `from_file_path(&temp_output)` at
   `:1078` — so peak is all inputs *plus* the full merged output — and then
   `ExternalSortMerger::new` loads them all a second time
   (`prefix_cache_merge.rs:76` and `:82-86`).

Net effect: there is no bounded-memory merge anywhere in this phase. Every route
scales with total dataset size. The external-sort *sharding* is genuinely
bounded, but the wrappers around it are not.

**Fix.** Both header-only reads are the same one-line change D-01 already
demonstrated:

```rust
// format.rs:852 — replace with a header-only read
let (kmer_size, canonical) = {
    let f = File::open(&input_paths[0])?;
    let mut r = BufReader::new(f);
    let h = DatabaseHeader::read_from(&mut r)?;
    (h.kmer_size, h.canonical)
};
```

Do the same at `prefix_cache_merge.rs:76`/`:82-86` and `format.rs:1048-1052`.
For the streaming route, `sorted_kmers` must additionally be streamed to the
output file rather than accumulated — that is the substantive part, and it is
the only way the "streaming" label becomes true. Track it as a follow-up; the
header-only reads alone are a large, low-risk first step.

---

## Warnings

### WR-01: The admission-control model is ~3–4× below the peak it is meant to bound

**File:** `src/database/format.rs:739` and `:833`
**Severity:** Warning.

`estimated_memory = total_kmers * 24` models one 20-byte record plus 4 bytes of
slack. The actual peak of `merge_databases_inmemory` for N input k-mers holds
simultaneously: all inputs as `Vec<KmerEntry>` (32 B each after `u128`
alignment), a `hashbrown` `HashMap<u128, u32>`, a `Vec<(u128, u32)>` (32 B each),
and finally a `Vec<KmerEntry>` from `from_kmer_pairs`. That is roughly 3–4× the
model. A merge the check admits can therefore still OOM, which is precisely the
outcome MERGE-01 promises to prevent and D-02's rejection message claims to
prevent. `WR-01` is the quantitative reason `CR-02` is not caught by the
admission gate.

**Fix.** Model the dominant peak term explicitly and document it as an
over-estimate, e.g. charge `total_kmers * 96` for the in-memory route, or
switch on `merge_mode`/`use_prefix_cache` and use a per-route constant. Also fix
`format.rs:737`: `.iter().sum()` there is non-saturating while its sibling at
`:830` uses `saturating_add` — inconsistent, and it would panic in a debug build
rather than saturate.

### WR-02: `merge_mode` is silently ignored — and the D-02 rejection is unreachable — whenever `--use-prefix-cache` is set

**File:** `src/database/format.rs:742-751` (vs. `:759-766`)
**Severity:** Warning — a phase-introduced contract that is unreachable on one path.

```rust
if config.use_prefix_cache {
    ...
    return Self::merge_databases_prefix_cache(input_paths, config);
}
let over_budget = estimated_memory > config.max_memory_usage as u64;
if config.merge_mode == "memory" && over_budget { return Err(...); }
```

The prefix-cache early return precedes both the D-02 rejection and every
`merge_mode` decision. `--use-prefix-cache` is a real, documented CLI flag
(`src/cli/args.rs:289-294`, set at `src/cli/commands/merge.rs:336`, with
`config.merge_mode` assigned one line later at `:337`). Consequences:

- `rustkmer merge --use-prefix-cache --merge-mode memory --max-memory 1GB` over
  budget runs anyway instead of returning the actionable rejection. The error
  message and the PyO3 docstring (`pyo3/src/database.rs:1339-1341`: *"'memory'
  refuses to run over budget"*) both promise otherwise.
- `merge_mode` still reaches `ExternalSortMerger` (`format.rs:1067`) but there
  means something entirely different — a *per-bucket* strategy selector
  (`prefix_cache_merge.rs:386-397`), not a route selector. So
  `--merge-mode streaming` on this path selects streaming per bucket while the
  whole merge still runs the prefix-cache algorithm.

**Fix.** Either hoist the D-02 rejection above the `use_prefix_cache` early
return, or explicitly reject the incompatible flag combination
(`--use-prefix-cache` + `--merge-mode != auto`) with a message explaining that
the prefix-cache strategy owns its own per-bucket memory policy. Document the
dual meaning of `merge_mode` on the CLI help either way.

### WR-03: `golden_sha256_tests.rs` cannot detect the format drift it claims to guard

**File:** `tests/golden_sha256_tests.rs:116-121`, with the claim at `:27-29`
**Severity:** Warning — the phase's load-bearing DENSE-02 verification is inert.

The test hashes the twelve committed fixture files on disk and compares them to
`tests/fixtures/golden_manifest.sha256`. Verified by git: neither the fixtures
nor the manifest is touched anywhere in this phase — `git diff --stat
6230ba9..HEAD -- tests/fixtures/` is empty, and the last commit to affect either
is `12caa42` (Phase 1, plan 01-03). The bytes under test are therefore static
Phase-1 artifacts that no Phase-3 code path touches at test time.

The consequence is that this test passes identically regardless of whether
`KmerKey::to_u128` still zero-extends, whether `KmerEntry::write_to` still
emits 16 + 4 bytes, or whether the write path is correct at all. It verifies
that nobody hand-edited a committed fixture — useful, but not what it claims.

Lines 27-29 assert the opposite: *"it was GREEN before the KmerKey swap landed —
that pre-swap pass is what makes the post-swap pass meaningful as a differential
rather than a tautology."* Because the test never invokes the swapped code, the
pre-swap and post-swap passes are green for the same reason, and there is no
differential. (`tests/golden_tests.rs` reads the same manifest and has the same
property; the file is candid that both binaries read the same manifest, but not
that both are static.)

For the record, **the byte-identity claim itself is true**, just not proven here:
`KmerKey::U64 → u128` is a lossless zero-extension (`src/hash/key.rs:96-101`), and
for k ≤ 32 the encoder bound is `2^(2k) ≤ 2^64`, so the narrowing contract at
`from_u128:74-87` holds with equality at k=32. `KmerEntry`'s layout is untouched
since `0fa16cf`, pre-dating this phase. The gap is verification rigor plus a
misleading comment, not a live format break.

**Fix.** Make the test actually exercise the write path: build a database
through `KmerCounter` for each cell of the k ∈ {21, 32, 64} × canonical × sorted
matrix, write it, and assert the resulting bytes hash to the manifest entry. Then
the pre/post comparison is a real differential. Failing that, retitle the test
and delete the differential claim so the comment stops misleading a future
maintainer into trusting it.

### WR-04: `merge_prefix_buckets` failure swallowing is worse than the record states

**File:** `src/database/prefix_cache_merge.rs:461-485`; aggravators at `:404-408` and `:872`
**Severity:** Warning (already-known item, escalated with two new aggravating factors).

This is the recorded deferred item — bucket failures are counted, logged, and
`Ok(())` is returned regardless, so `concatenate_final_output` writes a partial
`.rkdb`. That part of the record is accurate and I am not re-reporting it as new.

Two aggravating factors the record does not record:

1. **The D-06 change destroyed the recovery data first.** Lines 399-408
   deliberately moved shard deletion off the success branch so it also runs on
   failure ("this is only a peak-disk optimization, so it runs on the failure path
   too"). For a *failed* bucket that now deletes the bucket's shard files before
   the error is swallowed at `:485`. There is no longer any on-disk artifact from
   which the lost k-mers could be recovered or the bucket retried. The phase
   improved peak-disk behaviour and, in the same edit, closed the last recovery
   path for the silent-loss case. The two changes interact badly.

2. **The existing integrity check is itself a tautology, so it gives false
   assurance.** Lines 871-874:
   ```rust
   // Check for duplicates
   if total_kmers != total_kmers_in_files {
       log::warn!("   ⚠️  Warning: data size mismatch! Possible duplicates or loss");
   }
   ```
   `total_kmers` is `data_size / RECORD_SIZE` (`:860`) where `data_size` sums the
   buffers of the merged bucket files (`:835`); `total_kmers_in_files` sums
   `file_size / RECORD_SIZE` over those *same* merged bucket files (`:827-828`).
   The two are computed from identical inputs, so the comparison can never
   differ. A bucket that failed simply has no merged file (or an empty one, which
   is skipped at `:821-825`), and both counters exclude it identically. The check
   named "Possible duplicates or loss" cannot detect loss.

**Fix.** Return `Err` when `error_count > 0` (the record's suggestion is correct),
and delete the `total_kmers != total_kmers_in_files` check rather than leaving a
warning that can never fire. If a real integrity signal is wanted, compare the
concatenated record count against the sum of the *bucket-phase* counts recorded
before phase 2 discards the shards — which requires not deleting shards on the
failure path.

### WR-05: `parse_memory_size` overflows before it validates, and is now reachable from Python

**File:** `src/cli/commands/merge.rs:507-525`
**Severity:** Warning.

The unit multipliers are applied before the range check:

```rust
let bytes = match unit {
    "TB" => number * 1024 * 1024 * 1024 * 1024,
    ...
};
if bytes < 1024 { return Err("Memory size too small (minimum 1KB)".to_string()); }
if bytes > 1024 * 1024 * 1024 * 1024 { return Err("Memory size too large (maximum 1TB)".to_string()); }
```

Verified by compilation with and without overflow checks (this repo's
`[profile.release]` sets `panic = "abort"` and leaves `overflow-checks` off):

- **dev / `cargo test` profile** (`overflow-checks=on`): `--max-memory 99999999TB`
  panics with `attempt to multiply with overflow`, exit 101.
- **release** (`overflow-checks=off`): the multiply wraps silently. For
  `16777217TB` and `17179869185GB` the wrapped value is exactly 2^40, which
  **passes** the 1 TB upper bound that the same function advertises. The cap is
  defeated by the very input it exists to reject.

Inputs this large are unrealistic, which bounds the impact — but 03-05 made this
function `pub` and routed arbitrary Python strings through it
(`pyo3/src/database.rs:1411`), where an unhandled panic aborts the host
interpreter rather than a short-lived CLI.

**Fix.** Use checked arithmetic and map the overflow to the existing
"Memory size too large" error:

```rust
let bytes = number.checked_mul(mult).ok_or_else(|| {
    format!("Memory size too large: {} {}", number_str, unit)
})?;
```

### WR-06: `merge_databases_streaming` indexes `input_paths[0]` with no empty guard

**File:** `src/database/format.rs:852`
**Severity:** Warning (latent).

`merge_databases` is a public library API. Its three strategies disagree on
empty input: `merge_databases_inmemory` validates explicitly (`:905-909`) and
`merge_databases_prefix_cache` does too (`:1041-1045`), but
`merge_databases_streaming` reaches `&input_paths[0]` immediately and panics
with an index-out-of-bounds. A library consumer calling
`RKDatabase::merge_databases(&[], &config)` gets a panic rather than the
`Err("At least one input database is required")` the sibling paths return.

I confirmed both shipped front-ends guard this (`src/cli/commands/merge.rs:145`
rejects `len() < 2`; `pyo3/src/database.rs:1377` rejects an empty list), so it is
not reachable through the CLI or the Python API today. That is why this is a
Warning and not a Critical — but the guard belongs at the top of
`merge_databases` itself, where it protects all three strategies at once.

### WR-07: `MergeConfig::use_streaming` is a dead, silently-ignored public field

**File:** `src/database/merge_config.rs:15-16`; never read in `src/database/format.rs`
**Severity:** Warning.

The field is documented `/// Force streaming mode` and is `pub`, but a
repo-wide search shows it is only ever *written* (its `Default` and test
fixtures) — `merge_databases` decides routing purely from `config.merge_mode`
(`:770`) and `should_use_streaming` (`:823`). A library consumer who sets
`use_streaming = true` gets silently different behavior than they asked for,
with no diagnostic. Either honor it (treat `use_streaming || merge_mode ==
"streaming"`) or delete it; a public knob that does nothing is worse than no
knob.

### WR-08: `concatenate_final_output` loads each entire merged bucket into memory

**File:** `src/database/prefix_cache_merge.rs:831-832`
**Severity:** Warning.

```rust
let mut buffer = Vec::new();
input_file.read_to_end(&mut buffer)?;
```

Each merged prefix bucket is read wholly into RAM before being appended. Peak is
therefore bounded by the *largest single bucket*, not by the merge buffer. With
256 buckets (`num_buckets = 1 << 8`, `:74`) a merge whose k-mers concentrate in
few prefixes produces very large individual buckets, so this is unbounded in
practice on the path advertised as "memory-efficient". Copying in fixed-size
blocks — the same `RECORD_SIZE * 100_000` pattern already used at `:909` — would
keep it bounded.

---

## Info

### IN-01: A 1 GB floor silently overrides a smaller `--max-memory` on the prefix-cache path

**File:** `src/database/format.rs:1056` and `:1065`
`merge_buffer_mb = config.max_memory_usage / 1024 / 1024` is then passed as
`merge_buffer_mb.max(1024)` ("At least 1GB buffer"). That value is the per-bucket
threshold at `prefix_cache_merge.rs:391-396`, so a user who sets
`--max-memory 256MB` still gets up to 1 GB loaded per bucket via
`merge_single_prefix_hashmap`. The floor may be deliberate; if so it deserves a
comment explaining the tradeoff, since it reads as an oversight next to a
memory-budget flag.

### IN-02: The `deferred-items.md` clippy entry is stale

**File:** `.planning/phases/03-memory-safety/deferred-items.md:5-16`
The entry records 4 `clippy::useless_borrows_in_formatting` errors in
`src/io/{fasta,fastq}.rs` as `status: open`. Commit `fc8da65` fixed exactly those
(`&self.file_path` → `self.file_path` at `fasta.rs:56`, `fastq.rs:153`, `:215`,
`:342`), so the status field is stale and the entry is closed in substance. Worth
correcting so the disposition step does not re-open a fixed item.

### IN-03: `total_kmers` carries two different meanings across the codebase

**File:** `src/database/format.rs:478` vs. `src/database/index.rs:98`
`from_kmer_pairs` sets the header's `total_kmers` to `entries.len()` (the number
of records), while `DatabaseIndex` and the metadata/stats path treat
`total_kmers` as the sum of counts. `pyo3/tests/test_database_merge.py:182`
correctly asserts `stats.total_kmers == EXPECTED_UNIQUE`, i.e. the record-count
reading. Pre-existing and not exercised incorrectly by this phase, but the name
carries two incompatible meanings in one binary format and will mislead a future
change to `estimate_total_kmers`.

---

## Known Deferred Items — Re-Examination

Recorded in `deferred-items.md` / `WINDOWS.md`; not re-reported as new findings.

| # | Item | Verdict |
|---|---|---|
| a | `merge_prefix_buckets` swallows bucket failures | **Worse than recorded** — escalated to `WR-04`. The D-06 edit deleted failed buckets' shards before the error was swallowed (`:404-408`), and the integrity check at `:872` is itself a tautology. |
| b | `external_sort_merge_output.tmp` outside the subdir, never deleted | Confirmed accurate. `format.rs:1072` writes it to the shared `temp_dir` with a fixed name and `:1078` reads it back with no delete. Adjacent finding not in the record: `merge_databases_prefix_cache` holds every input database in `db_refs` (`:1048-1052`) through that final read, so peak is all-inputs-plus-full-output — folded into `CR-02`. |
| c | `rustkmer_sort_*.chunk` loose in `temp_dir`, not swept | Confirmed accurate and correctly scoped by the 03-04 narrowing note. `sweep_stale_merge_dirs` selects on `rustkmer-merge-` directories only (`temp_lifecycle.rs:125`) and `TempFileManager` writes into `config.temp_dir` (`streaming_merge.rs:254`). Normal-path RAII cleanup is fine; only the sweep gap is open. |
| d | Dense width only in `KmerCounter` | Confirmed accurate. `merge_databases_inmemory` uses `HashMapBrown<u128, u32>` (`format.rs:912`) and the `RKDatabase` read path is `Vec<KmerEntry>`. Correctly scoped as out of 03-03's DENSE-01 scope; it is also a contributing cause of `CR-02`'s peak. |
| e | `cargo fmt --all --check` pre-existing drift | Not re-verified this run (outside review scope); consistent with the record's file list. |
| f | `pyo3/pyproject.toml` `python-source` blocks `maturin` | Not re-verified this run; consistent with the record. |
| g | `--cov-fail-under=80` makes every `pyo3` pytest run exit 1 | Not re-verified this run; consistent with the record. |

## Deliberately Not Raised

- **`KmerCounter::merge`'s overflow-poisoning and non-concurrent-`merge` contracts**
  (`table.rs:395-432`) — both are documented at the definition site with the
  reasoning and a recommended recovery. Flagging documented, intentional API
  contracts as warnings would be noise, not signal.
- **Clippy/rustfmt style drift and the `mod common;` test-count noise** — recorded
  as deferred items (e) and the 03-04 stub-grep entry; not code-quality defects.
- **`merge_databases_inmemory`'s `HashMap<u128, u32>` not using `KmerKey`** — this
  is known item (d). I mention it only as a contributing factor to `CR-02`, not as
  an independent finding, to avoid double-counting a documented deferral.
- **The streaming merge's silent `if let Ok(next_entry)` at
  `streaming_merge.rs:394`** — a corrupt chunk *is* silently truncated rather than
  erroring. This is a real latent issue, but it is pre-existing, unchanged in
  structure by the refill reordering, and strictly less severe than `CR-01`
  (which corrupts data on a normal path rather than only on a damaged input).
  Recorded here rather than as a numbered finding so the count stays honest.
- **`unwrap()` in the phase's own tests** — the agent contract excludes test-file
  issues unless they affect reliability, and these are self-contained fixtures.
  The tests are, on inspection, unusually well-built: `over_budget_config`
  (`dense_merge_integration_tests.rs:422`) derives its budget from the production
  estimator rather than hard-coding one, and `assert_route` (`:402`) proves the
  route was actually taken — which is precisely the vacuous-test trap the 03-04
  deferred note records having been found and fixed.

---

_Reviewed: 2026-10-07T04:07:16Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_