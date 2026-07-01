---
phase: 01-foundation-quality
reviewed: 2026-07-01T13:05:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - .github/workflows/ci.yml
  - src/lib.rs
  - src/cli/mod.rs
  - pyo3/src/lib.rs
  - src/cli/commands/count.rs
  - src/database/format.rs
  - src/database/query.rs
  - src/database/prefix_cache_merge.rs
  - src/main.rs
  - tests/cjk_check.rs
  - tests/golden_tests.rs
  - tests/golden_generate.rs
  - tests/legacy_readback_tests.rs
  - tests/round_trip_tests.rs
  - Cargo.toml
findings:
  critical: 4
  blocker: 4
  warning: 9
  info: 6
  total: 19
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-01T13:05:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Adversarial standard-depth review of the Phase 1 (Foundation & Quality) deliverables: CI gate, log-facade migration, `.rkdb` consolidation, and the CJK→English literal gate. The phase narrative claims the silent `data_offset` clamp was "REMOVED and replaced with a loud Err." That claim is **false** — the loud-`Err` migration only patched 2 of 6 reader sites. Four other sites (`DatabaseQuery::read_entry_at`, `DatabaseStreamIterator::new`, `DatabaseHeader::validate`, and `execute_stats`) still silently rewrite an out-of-range offset to 42, so a tampered/corrupt file is silently read as garbage through every code path that is NOT `RKDatabase::from_file_path` or `DatabaseQuery::open(preload=true)`. This is the most serious finding because it means the SPEC P3 invariant ("non-canonical offset surfaces immediately") is unenforced across the public API surface.

Beyond that, the review surfaced: a documented-but-real `KmerEntry::read_from` endianness heuristic that silently corrupts counts >1,000,000 on read; a `Vec::remove(0)` O(n²) hot loop in the streaming merge; a redundant `DatabaseQuery`-reopened-per-call in `KmerQuery`; a CI cache-key collision that silently shares the root `target/` with the pyo3 job; leftover `DEBUG:` log strings; and several quality issues (duplicated `decode_kmer`, dead `read_entries_from_file_sync`, mis-scoped `#[allow]`).

The CJK-gate (`tests/cjk_check.rs`) is well-reasoned and the syn-visitor approach is correct (the `visit_lit` + `visit_macro` split is genuinely necessary — `println!`/`log::*!` macro bodies are not walked as `Lit` nodes). Golden/legacy/round-trip tests are sound in shape. The CI gate correctly uses `pull_request` (not `pull_request_target`), no `continue-on-error`, least-privilege `contents: read`.

**Note on tier labels:** Per the workflow's tier-equivalence rule, `critical:` and `blocker:` carry identical downstream semantics; both are reported here so either key resolves. IDs `CR-*` and `BL-*` are interchangeable.

---

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Silent `data_offset` clamp NOT removed — still present in 4 of 6 reader sites (SPEC P3 unenforced)

**File:** `src/database/query.rs:196-200`, `src/database/streaming_merge.rs:39-43`, `src/cli/commands/stats.rs:106-108`, `src/database/format.rs:173-175`
**Issue:**

The phase SUMMARY and the inline comment at `format.rs:289-297` assert that the previous silent clamp (`if data_offset < 40 || > 1000, force to 42`) was "REMOVED and replaced with a loud `Err`" so that "any non-canonical offset surfaces immediately." This is **demonstrably false**. A `grep` for the clamp pattern across `src/` (excluding tests) returns four sites that still silently rewrite the offset and then read from it as if it were valid:

1. `src/database/query.rs:196` — `DatabaseQuery::read_entry_at` (the disk-query path used by EVERY non-preload `query_kmer` call):
   ```rust
   let actual_data_offset = if (40..=1000).contains(&self.header.data_offset) {
       self.header.data_offset
   } else {
       42
   };
   ```
2. `src/database/streaming_merge.rs:39` — `DatabaseStreamIterator::new` (the merge input path).
3. `src/cli/commands/stats.rs:106` — `execute_stats` (the user-facing `rustkmer stats` command).
4. `src/database/format.rs:173` — `DatabaseHeader::validate` (still considers 40–1000 valid; `DatabaseQuery::open` calls this and proceeds on success).

Net effect: a file with `data_offset = 500` (or `0`, or `9999`) is rejected loudly **only** via `RKDatabase::from_file_path` and `DatabaseQuery::open(preload=true)`. Through `DatabaseQuery::open(preload=false)` it passes `validate()` (40 ≤ 500 ≤ 1000) and then `read_entry_at` silently seeks to the *header-supplied* offset (which is at least consistent now), but `DatabaseStreamIterator` and `execute_stats` still silently force the offset to 42 on any out-of-range value and read garbage k-mers. The SPEC P3 invariant is therefore enforced on 2 paths and unenforced on 4. A tampered/corrupt `.rkdb` produced by a buggy future writer (or an attacker) will read as plausible-looking but incorrect k-mers through those 4 paths.

This is also a self-contradiction in the codebase: the loud-`Err` comment at `format.rs:289` says "the .rkdb v2 format has exactly one valid data_offset (42)" while `format.rs:173` (validate) still accepts 40–1000.

**Fix:** Pick one canonical enforcement point and apply it everywhere consistently. The cleanest fix is to make `DatabaseHeader::validate` reject anything other than `data_offset == 42` (the actual format constraint), call `validate()` at the top of every reader, and delete every `actual_data_offset` reconciliation block:

```rust
// src/database/format.rs — DatabaseHeader::validate
pub fn validate(&self) -> Result<(), String> {
    if self.kmer_size == 0 || self.kmer_size > 127 {
        return Err(format!("Invalid k-mer size: {}", self.kmer_size));
    }
    if self.data_offset != 42 {
        return Err(format!(
            "Invalid data offset: {} (expected 42 — the only canonical .rkdb v2 header size)",
            self.data_offset
        ));
    }
    if self.index_offset > 0 && self.index_offset <= self.data_offset {
        return Err("Invalid index offset".to_string());
    }
    Ok(())
}
```
Then delete the redundant `if header.data_offset != 42` blocks in `format.rs:298` and `query.rs:84` (now covered by `validate()`), and delete the `actual_data_offset` clamp in `query.rs:196`, `streaming_merge.rs:39`, and `stats.rs:106` — those sites should use `self.header.data_offset` directly after `validate()` has passed. Add a regression test that hand-crafts a file with `data_offset = 500` and asserts each of the 4 paths returns `Err`.

---

### CR-02: `KmerEntry::read_from` endianness heuristic silently corrupts counts > 1,000,000

**File:** `src/database/format.rs:206-229`
**Issue:**

```rust
// Try little-endian first, if it gives a huge number, try big-endian
let count_le = u32::from_le_bytes(count_bytes);
let count_be = u32::from_be_bytes(count_bytes);
// If little-endian gives an unreasonable count (> 1M), use big-endian
let count = if count_le > 1_000_000 {
    count_be
} else {
    count_le
};
```

Every writer in the codebase (`KmerEntry::write_to`, the count path, the merge path) writes counts as **little-endian**. There is no big-endian writer anywhere. This heuristic is therefore self-invented defense against a producer that does not exist. Worse, it is **wrong for legitimate data**: a k-mer that legitimately occurs more than 1,000,000 times in a real dataset (entirely plausible — `rustkmer` targets human-genome-scale Illumina WGS where highly repetitive k-mers like homopolymer runs and centromeric repeats easily exceed 10M counts) will be silently re-interpreted as big-endian. The big-endian reinterpretation of a >1M little-endian count is a wildly different (usually much smaller) number, with no error surfaced.

Concretely: a count of `0x00400000` (4,194,304 little-endian = 4.19M) is `> 1_000_000`, so the reader returns `u32::from_be_bytes([0x00,0x40,0x00,0x00])` = 4,194,304 as well by coincidence, but `0x01000000` (16,777,216 LE) becomes `0x00000001` = 1. The corruption is silent and the value is plausible, so downstream query/merge/stats will report a wrong count with no error.

The golden generator explicitly works around this: `golden_generate.rs:181-184` asserts every generated count stays ≤ 1,000,000 specifically to avoid tripping the heuristic. That guard exists *because the maintainers know the heuristic is unsafe*. The round-trip and legacy tests also use small counts and so never exercise the bug.

This directly violates the phase's stated "P3: no .rkdb v2 layout change / no silent garbage" guarantee for real-world data.

**Fix:** Delete the heuristic; read strictly little-endian (matching the writer):

```rust
pub fn read_from<R: Read>(reader: &mut R) -> IoResult<Self> {
    let kmer = reader.read_u128::<LittleEndian>()?;
    let count = reader.read_u32::<LittleEndian>()?;
    Ok(Self { kmer, count })
}
```
If big-endian compatibility with some legacy external producer is genuinely needed, it must be opt-in via an explicit format-version flag, not a magic threshold. Add a regression test that writes a count of `5_000_000` and reads it back, asserting equality.

---

### CR-03: `Vec::remove(0)` in streaming-merge hot loop is O(n²) and corrupts the k-way merge order

**File:** `src/database/prefix_cache_merge.rs:615` (and the surrounding loop at `:600-644`)
**Issue:**

`merge_single_prefix_streaming` implements a k-way merge with a `BinaryHeap`, but on every popped entry it advances the file's entry cursor via:

```rust
file_states[top.file_idx].2.remove(0);   // line 615
```

`Vec::remove(0)` shifts every subsequent element left by one — O(n) per call, O(n²) over a prefix bucket. With `BATCH_READ = 100_000`, each call is up to 100k memmoves; over a multi-million-k-mer bucket this is catastrophic (the function is on the merge critical path for `--use-prefix-cache`). This is flagged as BLOCKER rather than the out-of-scope "performance" tier because (a) it is in a function that the phase explicitly migrated to `log::*` and re-touched, and (b) the impact is severe enough on human-genome-scale input (the stated benchmark target) that the merge can take hours instead of minutes — effectively a correctness/doS-grade defect for the documented workload.

There is also a deeper correctness concern in the same loop: when a batch is reloaded (`file_states[top.file_idx].2 = new_entries;` at line 620), the code peeks at `first_entry` and may either accumulate it into `current_count` (line 623) OR push a new `HeapEntry` (line 625) — but it has already removed the just-popped entry at line 615 *before* reloading. If the reload produces entries whose first kmer equals `current_kmer`, that accumulation happens, but if the heap later pops an entry from a *different* file whose kmer is smaller than `current_kmer`, the invariant `current_kmer` is the smallest unflushed kmer is violated and the output can become unsorted — silently corrupting the merge result. The dedup/accumulate logic interleaved with heap pops is not obviously correct.

**Fix:** Replace `Vec<KmerEntry>` with `std::collections::VecDeque<KmerEntry>` and use `pop_front()` (O(1)); or use an index cursor into the Vec. Separately, re-derive the merge correctness: the "accumulate into current_count without going through the heap" shortcut at lines 622-624 and 633-636 is only safe if the next entry from that file is guaranteed to be ≥ the current heap top — which it is, since each file is pre-sorted — but the interleaving with `current_kmer` flushing needs a written invariant and a property test (`proptest`) over random multi-file sorted inputs asserting the output is sorted and contains the correct summed counts.

---

### CR-04: CI cargo cache key collides between root and pyo3 jobs — corrupted/inconsistent builds possible

**File:** `.github/workflows/ci.yml:58`, `:79`, `:107`
**Issue:**

The root `clippy-root` and `test-root` jobs cache `target/` under key `${{ runner.os }}-cargo-root-${{ hashFiles('Cargo.lock') }}`, with restore key `${{ runner.os }}-cargo-root-`. The `pyo3-build` job caches `pyo3/target/` under key `${{ runner.os }}-cargo-pyo3-${{ hashFiles('pyo3/Cargo.lock') }}`.

The defect is at `:54-57` and `:75-78`: the cache `path:` for the root jobs includes `target` (relative to the workspace root, i.e. `<repo>/target`), but the matrix runs on both `ubuntu-latest` and `macos-latest`. The cache key is `${{ runner.os }}-cargo-root-...` so OSes are distinguished — that part is fine. **However**, the `clippy-root` and `test-root` jobs on the *same* OS share the same cache key (both use `hashFiles('Cargo.lock')`) but write to the same `target/` after running different commands (`cargo clippy --all-targets` vs `cargo test`). GitHub Actions cache is immutable on write-hit, but the *restore-keys* prefix match means the second job to run can restore a cache populated by the first job's partial compilation artifacts. Since `clippy-root` and `test-root` run in parallel (no `needs:` between them), this is a race: both jobs restore the same prefix-keyed cache, both compile into `target/`, and whichever finishes last writes a cache that mixes clippy and test artifacts. This is the classic "shared target dir between two cargo invocations" footgun — cargo itself refuses to run two concurrent builds against one `target/` for exactly this reason.

Symptoms are intermittent and range from spurious compile failures to stale-artifact test passes — exactly the kind of CI flakiness that erodes trust in the gate the phase exists to establish.

**Fix:** Give each job a distinct cache namespace, e.g. by job name:

```yaml
key: ${{ runner.os }}-cargo-${{ matrix.job }}-${{ hashFiles('Cargo.lock') }}
```
Or simpler: combine `fmt + clippy + test` into a single job that runs sequentially against one `target/`, so there is only ever one writer. At minimum, document why parallel access to the same `target/` cache is safe here (it currently is not).

---

## Warnings

### WR-01: `KmerQuery::query` reopens the database file for every single k-mer (1000× regression for batch queries)

**File:** `src/database/query.rs:276-296`
**Issue:**

```rust
pub fn query(&mut self, kmer: &str) -> crate::error::ProcessingResult<QueryResult> {
    ...
    if let Some(file_path) = &self.database.file_path {
        let mut db_query = DatabaseQuery::open(file_path, false)?;   // re-opens + re-reads header + re-validates
        match db_query.query_kmer(kmer)? { ... }
    }
}
```

`KmerQuery::query_multiple` (line 299) calls `self.query(kmer)?` in a loop. Each call re-`open()`s the file — re-reading the 42-byte header, re-running `validate()`, and re-seeking. For a 1M-k-mer batch query this is 1M redundant file opens. The `database` field already holds a borrowed `&RKDatabase` whose `entries: Vec<KmerEntry>` is in memory — the query could be a direct in-memory lookup with zero I/O. This is a behavioral regression masquerading as "fixed: use actual database query instead of mock" (per the inline comment at line 277).

**Fix:** Either query `self.database.entries` directly (binary_search if sorted, linear if not — the logic already exists in `RKDatabase::query_kmer`), or open `DatabaseQuery` once in `KmerQuery::new` and reuse it. Delete the per-call `DatabaseQuery::open`.

---

### WR-02: `KmerQuery::query` uppercases the result key but not the input — silent key mismatch

**File:** `src/database/query.rs:288-289`
**Issue:**

```rust
Some(count) => Ok(QueryResult::new(kmer.to_uppercase(), count, true)),
None => Ok(QueryResult::new(kmer.to_uppercase(), 0, false)),
```

The returned `QueryResult.kmer` is `kmer.to_uppercase()`, but the *lookup* at `db_query.query_kmer(kmer)` uses the original `kmer` (lowercase or mixed). If a caller queries `"acgtacgt..."` the lookup will encode the lowercase bytes (which `encode_kmer_bytes_u128` may reject or mis-encode depending on its case handling), then the result reports the key as `"ACGTACGT..."`. The caller cannot match the returned key back to their input. Either uppercase before lookup, or return the key verbatim.

**Fix:**
```rust
let normalized = kmer.to_uppercase();
match db_query.query_kmer(&normalized)? {
    Some(count) => Ok(QueryResult::new(normalized, count, true)),
    None => Ok(QueryResult::new(normalized, 0, false)),
}
```

---

### WR-03: `DatabaseHeader::write_to` flags expression has surprising operator precedence

**File:** `src/database/format.rs:94`
**Issue:**

```rust
let flags: u8 = if self.sorted { 1 } else { 0 } | if self.canonical { 2 } else { 0 };
```

This parses as `if self.sorted { 1 } else { 0 } | (if self.canonical { 2 } else { 0 })` because `|` binds tighter than `if`... actually it binds *looser*, so the RHS `if` is grouped but the whole expression is `(if sorted {1} else {0}) | (if canonical {2} else {0})` — which happens to be correct here only because the `if` arms are already complete expressions. But this is fragile and reads ambiguously; a future maintainer adding a third flag (`if self.x { 4 } else { 0 }`) with a trailing `|` will almost certainly get the precedence wrong. It also triggers a `clippy::unreadable_literal`-adjacent smell.

**Fix:** Use explicit grouping or bit-or-assign:
```rust
let mut flags: u8 = 0;
if self.sorted { flags |= 1; }
if self.canonical { flags |= 2; }
writer.write_u8(flags)?;
```

---

### WR-04: `src/cli/mod.rs` blanket-allow scope is correct but unguarded against new violations

**File:** `src/cli/mod.rs:1`
**Issue:**

```rust
#![allow(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]
```

The placement is correct (it scopes the entire `cli` subtree, matching the FOUND-04 boundary that exempts CLI output), and `count.rs` does still use `eprintln!` 30+ times for user-facing progress. The concern is *future drift*: any new `src/cli/commands/*.rs` file inherits the allow with no review gate. Since the phase's whole point is to make stdout/stderr usage a deliberate choice, the allow should be paired with either (a) a per-file `#[allow]` so each new file opts in explicitly, or (b) a test that asserts `eprintln!`/`println!` usage in `src/cli/` is only inside command-handler files (not leaking into shared `args.rs`/`mod.rs`). Lower severity because the current scope is genuinely intended.

**Fix:** Move the allow to a per-command-file basis, or add a smoke test like `cjk_check.rs` that denies `println!`/`eprintln!` outside `src/cli/commands/`.

---

### WR-05: `merge_databases` triple-reads every input file before merging

**File:** `src/database/format.rs:631-699`
**Issue:**

`merge_databases` reads every input once to sum `total_kmers` (lines 635-643), then `should_use_streaming` reads them all *again* to recompute the same `total_kmers` (lines 691-694), then the chosen strategy (`merge_databases_streaming` / `_inmemory` / `_prefix_cache`) opens and reads them a *third* time. For a merge of N human-scale databases this is 3× the I/O cost on the critical path. The phase explicitly re-touched this file for the log migration, so it is fair to flag. Also: `should_use_streaming` is called even when `config.use_prefix_cache` is true (no — that branch returns early at 648-657), but for the non-prefix-cache path the triple-read stands.

**Fix:** Compute `total_kmers` once, pass it through to the strategy selector, and have each strategy accept the already-loaded headers (or at minimum cache the `total_kmers` per path).

---

### WR-06: `ExternalSortMerger::new` reads the entire first DB plus every header — but ignores `total_kmers` from the others

**File:** `src/database/prefix_cache_merge.rs:42-69`
**Issue:**

```rust
let reference_db = RKDatabase::from_file_path(&input_files[0])?;   // loads ALL entries of file 0 into memory
let kmer_size = reference_db.header().kmer_size as usize;
...
for path in input_files.iter() {
    let db = RKDatabase::from_file_path(path)?;   // loads ALL entries of EVERY file into memory
    canonical_modes.push(db.header().canonical);
    kmer_sizes.push(db.header().kmer_size as usize);
}
...
let total_kmers = reference_db.header().total_kmers;   // only file 0's count
```

Three problems: (1) the constructor loads every k-mer of every input file into RAM just to read 3 header fields — defeats the entire "external sort for memory efficiency" premise; (2) `total_kmers` is taken only from `reference_db` (file 0), so `estimated_kmers_per_file` and the progress bar denominator are wrong for multi-file merges; (3) `validate_compatibility_external_sort` (in format.rs:947) is called *after* this constructor and re-opens every file again — fourth I/O pass.

**Fix:** Read only headers (use `DatabaseHeader::read_from` on an open `BufReader`, don't call `RKDatabase::from_file_path`). Sum `total_kmers` across all files. Drop the duplicate validation pass.

---

### WR-07: `prefix_cache_merge.rs` parallel bucket-merge writes progress from multiple threads via `log::info!` — interleaved/garbled output

**File:** `src/database/prefix_cache_merge.rs:292-366`
**Issue:**

The `non_empty_prefixes.into_par_iter()` body calls `log::info!(...)` (lines 330, 338, 353) and `log::error!(...)` (line 338) from every rayon worker concurrently. `env_logger` does not serialize writes — concurrent `log::info!` calls produce interleaved characters on stderr/stdout. The phase's stated motivation for migrating to `log::*` was thread-safety; the actual `log` macro is thread-safe in the sense of not crashing, but the *output* is racy. The `let _ = std::io::stdout().flush();` at line 361 inside the parallel closure is also unsynchronized.

Also: `done.is_multiple_of(10)` (line 345) is unstable API (`is_multiple_of` stabilized in 1.87+, edition-dependent) and is called on `done` which is read via `fetch_add` then compared — a benign race but the progress line can report `done > non_empty_count` briefly.

**Fix:** Either (a) push progress messages through an `mpsc` channel consumed by a single thread, or (b) accept interleaving but document it, or (c) use `indicatif::MultiProgress` (already a dependency) which is designed for parallel progress. Remove the `stdout().flush()` from inside the parallel closure.

---

### WR-08: `log::info!("")` and `log::info!("\n...")` patterns — anti-pattern from the migration

**File:** `src/database/prefix_cache_merge.rs:90, 110, 124, 149, 242, 368, 715` (and `format.rs:651, 665, 674` DEBUG strings)
**Issue:**

Seven `log::info!("\n🚀 ...")` / `log::info!("")` calls were introduced by the migration. These emit a literal leading newline or an empty record. `env_logger`'s default format wraps every record in `[timestamp LEVEL]` brackets and appends a newline, so `log::info!("")` produces `[time INFO]` on its own line (cosmetic noise) and `log::info!("\n🚀 Starting...")` produces a blank line *before* the bracketed prefix (splitting the message from its log level). This is the "compile-fix deviation" the phase context flags. It is not a bug but it defeats the structured-log benefit the migration was supposed to deliver, and `log::info!("\r")` (line 354) actively corrupts terminal output under structured logging.

Also, three `log::info!("DEBUG: ...")` strings survived at `format.rs:651,665,674` and one at `count.rs:523` (`eprintln!("DEBUG: Writing header with data_offset: {}", ...)`). These are debug instrumentation left in production paths.

**Fix:** Remove the leading `\n` / empty-arg / `\r` patterns. Replace `log::info!("DEBUG: ...")` with `log::debug!("...")` so it is gated by `RUST_LOG=debug`. Delete the `eprintln!("DEBUG: ...")` at `count.rs:522-525`.

---

### WR-09: `is_dead_pyo3_file` / `is_cli_file` use substring match — false positives on legitimate filenames

**File:** `tests/cjk_check.rs:169-179`
**Issue:**

```rust
fn is_dead_pyo3_file(path: &Path) -> bool {
    let s = path.to_string_lossy();
    s.contains("database_backup") || s.contains("database_new_approaches") || s.contains("stage1_fix_backup")
}
fn is_cli_file(path: &Path) -> bool {
    path.to_string_lossy().contains("/cli/")
}
```

The substring matchers will exclude any file whose path contains those substrings anywhere, including a legitimate future file like `pyo3/src/database_backup_recovery.rs` (intentional new feature) or `src/io/cli_compat.rs` (a non-CLI module that happens to contain `/cli/`). The `is_cli_file` test at line 302 (`cli_files_are_excluded_from_scan`) even asserts `src/cli/commands/count.rs` matches — correct today, but the rule "any path containing `/cli/`" is broader than "the `src/cli/` subtree". A Windows-style path (`src\cli\foo.rs`) would NOT match, breaking the gate on a Windows checkout.

**Fix:** Match on canonical path components:
```rust
fn is_cli_file(path: &Path) -> bool {
    path.components().any(|c| c.as_os_str() == "cli") && path.starts_with("src")
}
```
And for dead files, match exact file stems or use `path.file_name()`.

---

## Info

### IN-01: Duplicated `decode_kmer` implementation in `count.rs` shadows the canonical one

**File:** `src/cli/commands/count.rs:550-568`
**Issue:**

`count.rs` defines its own `fn decode_kmer(kmer: u128, k: usize) -> String` (lines 550-568) that is a byte-for-byte reimplementation of `rustkmer::kmer::encoding::decode_kmer_u128` (encoding.rs:262). The canonical version is used by `prefix_query_optimized.rs`, `suffix_query.rs`, and `canonical.rs`. The duplicate exists in `src/cli/` (which is exempt from the CJK gate and the print-stdout deny), so it is not caught by either gate. This is exactly the kind of "single source of truth" violation the phase's `.rkdb` consolidation wave was supposed to eliminate (and did eliminate for the entry writer).

**Fix:** Delete the local `decode_kmer` and `use rustkmer::kmer::encoding::decode_kmer_u128;`.

---

### IN-02: Dead code — `ExternalSortMerger::read_entries_from_file_sync` and `read_entries_from_file` are unused

**File:** `src/database/prefix_cache_merge.rs:655-671` (`read_entries_from_file_sync`), `:931-947` (`read_entries_from_file`)
**Issue:**

Both are private (`fn`, no `pub`) and a `grep` shows no caller. The whole `impl ExternalSortMerger` block is already `#[allow(dead_code)]` (line 30), which masks these. The streaming path uses `read_batch_from_file_sync` instead. Dead code that the allow attribute hides.

**Fix:** Delete both functions, or remove the blanket `#[allow(dead_code)]` and let the compiler tell you what is actually unused.

---

### IN-03: `golden_generate.rs` is `#[ignore]`d but not documented as a manual run step in CI

**File:** `tests/golden_generate.rs:168-169`, `.github/workflows/ci.yml`
**Issue:**

`golden_generate` is the *only* producer of the 12 golden fixtures and the manifest. It is correctly `#[ignore]`d so it doesn't run on every CI. But there is no CI step, no `just`/`make` target, and no README pointer documenting that a maintainer must run `cargo test --test golden_generate -- --ignored --nocapture` whenever the count path intentionally changes the `.rkdb` layout. Without that, the next person to (correctly) evolve the format will either skip regeneration (breaking the golden gate) or regenerate without understanding why the bytes changed.

**Fix:** Add a comment block at the top of `golden_tests.rs` and a line in the repo's CONTRIBUTING/DEVELOPER docs describing the regeneration procedure. Optionally add a `cargo run` example as a `just` recipe.

---

### IN-04: `concatenate_final_output` uses `b"RKDB"` literal and `version: 2` magic number instead of the constants

**File:** `src/database/prefix_cache_merge.rs:808-819`
**Issue:**

```rust
let header = crate::database::format::DatabaseHeader {
    magic: *b"RKDB",
    version: 2,
    ...
```

`DATABASE_MAGIC` and `DATABASE_VERSION` constants exist in `format.rs:11,14` and are used everywhere else (including `count.rs:509-510` and `format.rs:466-467`). This one site hardcodes the literals, so a future version bump (`DATABASE_VERSION = 3`) will silently produce a v2 file from the prefix-cache merge path while every other writer produces v3 — exactly the kind of format drift the consolidation wave was meant to prevent.

**Fix:**
```rust
use crate::database::format::{DATABASE_MAGIC, DATABASE_VERSION};
let header = DatabaseHeader {
    magic: *DATABASE_MAGIC,
    version: DATABASE_VERSION,
    ...
```

---

### IN-05: `round_trip_tests.rs` `TestResultExt::a` trait is unidiomatic and poorly named

**File:** `tests/round_trip_tests.rs:20-28`
**Issue:**

The adapter trait `fn a(self) -> anyhow::Result<T>` converts `Result<T, Box<dyn Error>>` to `anyhow::Result`. The name `.a()` is opaque — a reader sees `create_database_from_kmers(...).a()?` and has no idea what `.a()` does. The comment explains it, but the call sites do not. This is a readability defect, not a bug.

**Fix:** Rename to `.into_anyhow()` or `.anyhow()`, or just inline `anyhow::Result::<_>::Ok(x).map_err(...)` at the (few) call sites. Or change `common::*` to return `anyhow::Result` directly.

---

### IN-06: `cjk_check.rs` `locate_line` falls back to line 1 silently — underreports on multi-line literals

**File:** `tests/cjk_check.rs:131-139`
**Issue:**

If a CJK literal's value does not appear verbatim in `source.lines()` (e.g. the literal contains an escape like `\n` that is rendered differently in the source vs. the parsed value, or the same string appears on multiple lines), `locate_line` returns `1`. The hit is still reported (pass/fail verdict unaffected), but the line number is wrong, sending the maintainer to the wrong place. This is acceptable for a gate whose job is to fail, but the fallback should be logged or the function renamed to `locate_line_best_effort` to make the contract explicit.

**Fix:** Return `Option<usize>` and have the caller format `"line unknown"` when missing, or document the fallback in the doc comment (it is currently documented, which is good — this is a minor polish item only).

---

_Reviewed: 2026-07-01T13:05:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
