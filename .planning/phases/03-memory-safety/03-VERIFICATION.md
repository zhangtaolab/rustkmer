---
phase: 03-memory-safety
verified: 2026-10-07T04:20:00Z
status: gaps_found
score: 4/7 must-haves verified
covered_files:
  - ".planning/phases/03-memory-safety/03-01-PLAN.md"
  - ".planning/phases/03-memory-safety/03-01-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-02-PLAN.md"
  - ".planning/phases/03-memory-safety/03-02-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-03-PLAN.md"
  - ".planning/phases/03-memory-safety/03-03-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-04-PLAN.md"
  - ".planning/phases/03-memory-safety/03-04-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-05-PLAN.md"
  - ".planning/phases/03-memory-safety/03-05-SUMMARY.md"
  - "pyo3/src/database.rs"
  - "src/database/format.rs"
  - "src/database/merge_config.rs"
  - "src/database/prefix_cache_merge.rs"
  - "src/database/streaming_merge.rs"
  - "src/database/temp_lifecycle.rs"
  - "src/hash/key.rs"
  - "src/hash/mod.rs"
  - "src/hash/table.rs"
  - "tests/dense_differential_tests.rs"
  - "tests/dense_merge_integration_tests.rs"
  - "tests/dense_proptest_tests.rs"
  - "tests/golden_sha256_tests.rs"
  - "tests/merge_cleanup_tests.rs"
  - "tests/merge_routing_tests.rs"
covered_digest: "v3:sha256:5f9fb1fde360ce4dec1340e588df6da678b704000b1a42b8cdadbe8f1aca1794"
gaps:
  - truth: "DENSE-01: K-mers for k <= 32 are stored as u64 instead of u128 — roughly halving counting memory for the common case"
    status: failed
    reason: >
      The requirement is not merely unverified — it is empirically INVERTED.
      KmerKey is an enum carrying a u128 variant, so Rust gives it u128's
      16-byte alignment and pads it to 32 bytes. Measured directly:
      size_of::<KmerKey>() = 32, and the (K, V) slot the DashMap actually
      stores grows from 32 B to 48 B. A 4M-entry RSS probe against the
      project's own dashmap 6.2.1 gives 102.89 B/entry dense vs 69.34 B/entry
      for the pre-Phase-3 DashMap<u128,u32> — a ratio of 1.487, i.e. counting
      memory INCREASED ~49% for exactly the k<=32 case DENSE-01 is about.
      DENSE-01 claims a ratio near 0.5-0.6.
    artifacts:
      - path: "src/hash/key.rs"
        issue: "Enum declaration at :37-50 has no niche-free layout; U128(u128) forces align 16 / size 32. The doc rationale at :31-34 ('the discriminant never adds live storage cost') is false — the discriminant is paid on every entry because layout is fixed at compile time."
      - path: "src/hash/table.rs"
        issue: ":361 key_bytes() derives width from self.kmer_length, never from a stored KmerKey, so memory_usage() (:352) is a restatement of the branch condition, not an observation of it."
      - path: "src/hash/table.rs"
        issue: ":1018 dense_counter_memory_usage_halved_for_k21 asserts a model constant. Mutation-tested: forcing every k<=32 key to the wide variant leaves it green."
      - path: "tests/dense_differential_tests.rs"
        issue: ":237 and :247 repeat the same model assertion; both stay green under the same mutation."
      - path: "tests/dense_merge_integration_tests.rs"
        issue: ":457 repeats it a third time; same result."
    missing:
      - "Reopen RESEARCH Pattern 1 Option A. Use a width-generic KmerCounter<K> over u64/u128, or two concrete counter types, so the dense key has no u128 variant in its layout."
      - "Add a real memory assertion: size_of::<K>(), or an RSS/heap-delta measurement, so the test can observe the stored key rather than restate k."
      - "Any fix must preserve get_all_counts() -> Vec<(u128, u32)> so DENSE-02 and the count.rs / pyo3 call sites still compile."
  - truth: "Merge respects a memory budget via admission control — bounded merge, no OOM at human scale"
    status: partial
    reason: >
      The admission-control LOGIC is correct and genuinely well tested
      (header-only estimator, hard route, D-02 reject). But the thing the
      budget admits is not bounded: all three strategies materialize whole
      databases in RAM. The route selected precisely because the inputs do
      not fit is the one that peaks highest.
    artifacts:
      - path: "src/database/format.rs"
        issue: ":852 merge_databases_streaming loads input_paths[0] in full via from_file_path just to read kmer_size + canonical — two header fields — on the over-budget path."
      - path: "src/database/format.rs"
        issue: ":869-876 accumulates the entire merged output into a Vec<(u128,u32)>, then :887 from_kmer_pairs builds a third full copy. Peak is ~3x the dataset on the path chosen because it does not fit."
      - path: "src/database/format.rs"
        issue: ":739 estimated_memory = total_kmers * 24 models roughly a quarter of the actual peak (~3-4x), so a merge the gate admits can still OOM."
      - path: "src/database/prefix_cache_merge.rs"
        issue: ":76 and :82-86 load every input twice; format.rs:1048-1052 holds all inputs alive through the final output read."
    missing:
      - "Header-only read at format.rs:852 and prefix_cache_merge.rs:76/:82-86 (the same one-line change estimate_total_kmers already demonstrates)."
      - "Stream sorted_kmers to the output file instead of accumulating it — the substantive part of making 'streaming' true."
      - "Re-calibrate the x24 constant per route so admission control bounds the term it is meant to bound."
  - truth: "Merge routes produce identical data (in-memory vs streaming) for the same input"
    status: failed
    reason: >
      KmerEntry::read_from applies an endianness heuristic while write_to
      always writes little-endian, so any count above 1,000,000 is read back
      byte-swapped. The phase made this route-dependent by hard-routing large
      merges to streaming, and the two routes apply the heuristic a different
      number of times. Reproduced arithmetically and by route simulation:
      true count 2,000,000 -> in-memory route 2,156,142,080, streaming route
      2,000,000. The same input under the same budget yields different data
      depending only on which route the budget picked.
    artifacts:
      - path: "src/database/format.rs"
        issue: ":216-238 read_from swaps any count_le > 1_000_000 to big-endian; :211 write_to always emits write_u32::<LittleEndian>."
      - path: "src/database/streaming_merge.rs"
        issue: ":94 reads the input (swap 1), :272 writes the chunk LE, :314 reads the chunk back (swap 2) — two swaps cancel by accident. The in-memory route swaps once at format.rs:328."
      - path: "pyo3/tests/test_database_merge.py"
        issue: ":230 test_streaming_and_inmemory_routes_produce_identical_data is a correct contract that cannot reach the bug — every fixture count is far below 1,000,000."
    missing:
      - "Delete the heuristic in read_from; it must be a plain u32::from_le_bytes matching write_to."
      - "Add a write_to -> read_from round-trip test at and above the old threshold (1_000_000, 1_000_001, 2_000_000, 16_777_216)."
      - "Extend the streaming-vs-in-memory parity test with at least one fixture count above 1,000,000."
deferred:
  - truth: "prefix-cache partial-merge: merge_prefix_buckets swallows bucket failures and concatenates a partial .rkdb"
    addressed_in: "Not scheduled in the current milestone roadmap"
    evidence: >
      Worsened by this phase and now carries two aggravators that make it a
      correctness risk rather than a robustness nit: (a) the D-06 edit moved
      shard deletion onto the failure path (prefix_cache_merge.rs:399-408), so
      a failed bucket's shards are deleted BEFORE the error is swallowed at
      :485, destroying the last recovery path; (b) the integrity check at
      :871-874 comparing total_kmers to total_kmers_in_files is a tautology —
      both are derived from the same merged bucket files — so it can never
      fire. Not scored as a gap (it predates Phase 3 and is already recorded),
      but it should not survive into a release that claims bounded merges.
  - truth: "external_sort_merge_output.tmp written outside the subdir and never deleted; streaming chunks not covered by the orphan sweep"
    addressed_in: "Not scheduled in the current milestone roadmap"
    evidence: "Recorded in deferred-items.md / WINDOWS.md; confirmed accurate against format.rs:1072 and temp_lifecycle.rs:125. Correctly scoped as temp-hygiene, not correctness."
---

# Phase 03: Memory Safety — Verification Report

**Phase Goal:** Bounded-memory merge operations and dense k-mer storage for the common k ≤ 32 case
**Verified:** 2026-10-07T04:20:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

The phase goal has two halves. **The merge half is delivered in form but not in
substance.** The routing logic is real, correct, and genuinely well tested —
but the merge it routes *to* is not bounded, so the goal's first clause is not
achieved. **The dense half is inverted.** DENSE-01's stated effect (halving
counting memory for k ≤ 32) is measurably the opposite of what shipped.

Two prior audits flagged this phase. I independently reproduced both load-bearing
claims rather than inheriting them, and **both hold**. One is understated — see
DENSE-01 below.

### Success Criteria Verdicts

| # | Success criterion (ROADMAP.md) | Verdict | Basis |
|---|-------------------------------|---------|-------|
| 1 | Merge defaults to streaming/external-sort — human-scale merges no longer OOM | **FAIL** | Routing is correct, but no route is memory-bounded. The over-budget path peaks ~3× the dataset. See CR-02. |
| 2 | Merge respects a memory budget via admission control | **PARTIAL** | Estimator is header-only and the hard route + D-02 reject are real and sound. The model is ~3–4× below the peak it bounds, so admission does not prevent the OOM it promises. |
| 3 | Failed/interrupted streaming merges clean up temp shards (RAII) | **PASS** | Genuinely sound. RAII on the prefix-cache path, process-unique subdir, startup sweep, symlink-safe. Only the pre-existing .tmp leak remains (deferred). |
| 4 | K-mers k ≤ 32 stored as u64, roughly halving counting memory | **FAIL — INVERTED** | Measured 1.487× *more* memory than pre-Phase-3 for k ≤ 32. The only criterion whose measured effect runs opposite to its claim. |
| 5 | Dense storage maintains correctness — canonicalization and counts match u128 exactly | **PASS** | Mutation-tested: a genuine narrowing bug makes the differential FAIL. The tests discriminate; they are not vacuous. |
| 6 | pyrustkmer PyDatabase merge uses the same bounded path as the CLI | **PASS** | Threads max_memory/merge_mode into the same MergeConfig and the same core. Inherits the criterion-1 defect, but the requirement is about parity, which holds. |

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | k ≤ 32 stored as u64, ~halving counting memory (DENSE-01) | ✗ FAILED | Measured 102.89 vs 69.34 B/entry — ratio 1.487, an increase |
| 2 | Streaming route is memory-bounded (MERGE-01) | ✗ FAILED | format.rs:852 loads input[0]; :869-876 accumulates full output |
| 3 | Routes produce identical data | ✗ FAILED | 2,000,000 → 2,156,142,080 (in-memory) vs 2,000,000 (streaming) |
| 4 | Temp shards cleaned on any exit incl. sweep (MERGE-03) | ✓ VERIFIED | temp_lifecycle.rs:100-140, prefix_cache_merge.rs RAII |
| 5 | u64/u128 counts + canonicalization match (DENSE-03) | ✓ VERIFIED | Mutation B caught — differential discriminates |
| 6 | PyDatabase merge shares the CLI path (MERGE-04) | ✓ VERIFIED | pyo3/src/database.rs:1367+ |
| 7 | .rkdb v2 byte-identity preserved (DENSE-02) | ✓ VERIFIED | Zero-extension is lossless; format.rs:211-213 untouched since Phase 1 |

**Score:** 4/7 must-haves verified (3 failed/partial, 4 verified)

## Independent Verification of the Two Prior Audits

I re-derived both audits' central claims from source and by measurement.

### Nyquist BLOCKER-1 (DENSE-01) — CONFIRMED, and UNDERSTATED

Nyquist measured `size_of::<KmerKey>() = 32` from a standalone probe and
concluded the real footprint is 36 B/entry vs 20 B pre-Phase-3. **Both of those
figures understate the regression.** I measured the actual `(K, V)` slot the
DashMap stores:

```
size_of::<KmerKey>()          = 32   (align 16)
size_of::<(u128, u32)>()      = 32   <- pre-Phase-3 slot
size_of::<(KmerKey, u32)>()   = 48   <- post-Phase-3 slot
```

The correct comparison is 48 vs 32, not 36 vs 20. Then, end-to-end against the
project's own `dashmap 6.2.1` with 4M entries, reading `/proc/self/status`:

```
DashMap<u128,   u32>  (PRE-Phase-3):  69.34 B/entry
DashMap<KmerKey, u32> (POST, k<=32) : 102.89 B/entry
>>> ratio = 1.487
```

Re-run with the measurement order reversed (dense first, to rule out
allocator-fragmentation ordering artifacts): 102.90 vs 69.21, ratio **1.487**.
Stable.

So the shipped change **increases counting memory by ~49%** for exactly the
k ≤ 32 case DENSE-01 targets. The requirement is not "unverified" — it is
inverted, which is worse than a coverage gap.

I also reproduced the vacuity claim by mutation, not by reading:

- **Mutation A** — forced every k ≤ 32 key to the wide `U128` variant (defeating
  DENSE-01 completely): `dense_counter_memory_usage_halved_for_k21` **still
  passes**, and `dense_differential_tests` (6) + `dense_merge_integration_tests`
  (3) stay green. The three assertions cannot detect the defect.
- **Mutation B** — decoupled width from `kmer_length` so k>32 aliases onto u64
  keys (a *genuine* narrowing bug): `dense_u128_unchanged_k64_canon` and
  `..._noncanon` **FAIL**. DENSE-03's differential is genuinely sound.

The repo was restored to a clean `git diff` after both mutations.

### Code review CR-01 (route-dependent count corruption) — CONFIRMED

`read_from` (format.rs:216-238) swaps any count above 1,000,000 while `write_to`
(:211) always writes LE. Reproduced:

```
true=     999999  -> 999999     OK
true=    1000001  -> 1094848256  CORRUPTED
true=    2000000  -> 2156142080  CORRUPTED
true=   16777216  -> 1           CORRUPTED
```

And the route divergence, simulated against the real read/write pattern:

```
true=2000000  in-memory=2156142080  streaming=2000000   *** ROUTES DISAGREE ***
```

The review's mechanism is exactly right: the in-memory route swaps once
(format.rs:328); the streaming route swaps twice (streaming_merge.rs:94 read,
:272 LE write, :314 read-back) and the double swap cancels by accident. Note
16,777,216 is wrong on **both** routes — the parity test at
test_database_merge.py:230 cannot catch this because no fixture count exceeds
1M.

### Code review CR-02 (no bounded merge) — CONFIRMED

format.rs:852 loads `input_paths[0]` in full via `from_file_path` for two
header fields, on the over-budget path. :869-876 accumulates the entire merged
output, :887 builds a third copy. The D-01 fix was applied precisely to the
estimator; the same materialization survives in all three strategies it routes
into.

### Code review WR-03 / WR-04 — CONFIRMED

- WR-03: `git diff --stat 6230ba9..HEAD -- tests/fixtures/` is **empty**; last
  touched by `12caa42` (Phase 1). The golden sha256 test re-hashes static
  Phase-1 files — it cannot detect write-path drift. (The underlying claim is
  nonetheless true by construction — zero-extension is lossless — so this is a
  verification-rigor gap, not a live format break.)
- WR-04: shards are deleted at prefix_cache_merge.rs:399-408 before the error is
  swallowed at :485, and the "duplicates or loss" check at :871-874 compares two
  values derived from the same inputs — it can never fire.

## Mutation Testing Summary

| Mutation | Target | Result | Interpretation |
|----------|--------|--------|----------------|
| A: force all keys to `KmerKey::U128` | DENSE-01 | **GREEN** | Assertion is vacuous — cannot observe stored width |
| B: decouple width from `kmer_length` | DENSE-03 | **RED (2 failed)** | Differential is sound and discriminating |
| route sim: count 2,000,000 | merge parity | **routes disagree** | CR-01 is a live correctness defect |

## What Is Genuinely Sound — Do Not Re-Litigate

- **DENSE-03's decoded-level differential is correct and rigorous.** It is the
  right discipline (decoded `(String, u32)`, never raw integers across widths),
  it uses an independent oracle, and Mutation B proves it catches real bugs.
- **DENSE-02 byte-identity holds** — `KmerKey::U64 → u128` is lossless
  zero-extension and the encoder bound `2^(2k) ≤ 2^64` is exactly tight at k=32.
  Only the *test* is inert (WR-03), not the property.
- **MERGE-03's cleanup is solid** — `sweep_stale_merge_dirs` is symlink-safe
  (uses `file_type()`, refuses non-dirs), TTL underflow-clamped, missing dir is
  a no-op, and it correctly runs before any shard this merge creates.
- **The admission-control logic and its tests are genuinely non-vacuous.**
  `merge_routing_tests` discriminates by pointing `temp_dir` at a nonexistent
  directory, so removing the routing flips outcomes; `dense_merge_integration_tests`
  derives its budget from the production estimator rather than hard-coding it.
  The routing *works* — it just routes to an unbounded implementation.
- **MERGE-04 parity holds** — Python threads the same `MergeConfig` into the
  same core, with boundary validation for both kwargs.
- **Engine hygiene is real**: `cargo test` exits 0 (221 lib + all integration
  binaries), clippy `-D warnings` clean on both crates, no `#[ignore]` stubs left
  in any Phase-3 test file. No Phase-1/2 regression found.

## Requirements Traceability

All 7 IDs appear in PLAN frontmatter and in the REQUIREMENTS.md Phase-3
traceability table — no orphans. But REQUIREMENTS.md marks DENSE-01 "Complete",
which this verification contradicts.

| Requirement | Plans | Status | Evidence |
|-------------|-------|--------|----------|
| MERGE-01 | 03-01, 03-04 | **NOT MET** | Routing correct; destination unbounded (format.rs:852) |
| MERGE-02 | 03-01, 03-04 | **PARTIAL** | Admission logic sound; model ~3–4× under peak |
| MERGE-03 | 03-02 | **MET** | RAII + sweep verified |
| MERGE-04 | 03-05 | **MET** | Shared core, boundary validation |
| DENSE-01 | 03-03 | **NOT MET (inverted)** | Measured 1.487× memory increase |
| DENSE-02 | 03-03, 03-04 | **MET** | Byte-identity holds; test inert (WR-03) |
| DENSE-03 | 03-03, 03-04 | **MET** | Mutation-proven sound |

## Gaps Summary

Three gaps, two of which invert or defeat a headline criterion.

1. **DENSE-01 is inverted** (src/hash/key.rs:37-50). The enum's `u128` variant
   forces 32-byte keys and a 48-byte DashMap slot. Measured, counting memory for
   k ≤ 32 went **up 49%**, not down. Every assertion purporting to show the
   halving is green under a mutation that removes it entirely. The doc rationale
   at key.rs:31-34 is factually wrong.

2. **No merge strategy is bounded** (src/database/format.rs:852, :869-876;
   prefix_cache_merge.rs:76, :82-86). The phase's central deliverable. Fixing
   the two header-only reads is low-risk and immediate; streaming the output is
   the substantive follow-up.

3. **Routes silently disagree above 1M counts** (src/database/format.rs:216-238).
   Silent count corruption, made route-dependent by this phase's hard routing.
   The fix is a five-line deletion plus a threshold round-trip test.

Gaps 2 and 3 are pre-existing defects that this phase made newly load-bearing;
gap 1 was introduced by this phase.

## Deferred Items — Severity Judgement

The recorded deferrals were reviewed for blocking severity. None blocks the
phase on its own. The prefix-cache partial-merge silent loss (deferred above) is
the most serious: it is **worse than recorded**, because the D-06 cleanup change
removed the recovery path while the tautological integrity check gives false
assurance. It warrants a follow-up before any release claiming bounded merges,
but it predates this phase and is not scored as a Phase-3 gap.

The pyo3 maturin/python-source misconfiguration and the `--cov-fail-under=80`
exit-1 issue are pre-existing infrastructure defects, not Phase-3 correctness
failures.

---

_Verified: 2026-10-07T04:20:00Z_
_Verifier: the agent (gsd-verifier)_
