# Phase 11: Three-Way Merge Parity Gate — Written Specification

**Requirement:** MBENCH-02 (phase-11 scope: gate defined in writing, implemented, GREEN/RED-proven, proven live at slice scale; its full-scale execution belongs to Phase 12 per the MBENCH-02/03 split)
**Status:** Authoritative gate definition for every rustkmer-merge vs jellyfish-merge comparison in this milestone
**Created:** 2026-11-16 (before any timed merge round trusted its medians)
**Implementation:** `scripts/bench/bench.py` — `assert_merge_parity` (aggregate legs), `normalize_dump_lines` + `dump_vs_dump_equal` (deep leg); unit proof in `scripts/bench/tests/test_merge_arms.py`

---

## 1. Scope

This gate governs EVERY comparison of a rustkmer merge output against a jellyfish
merge output: the slice-scale rehearsal and proof runs (Phase 11), the
intermediate characterization ladder (Plan 11-06), and the Phase 12 full-scale
counterbalanced session. It executes and passes BEFORE any timed round's medians
are trusted — the locked parity-before-timing precedent (v2.0) extended to the
merge operation. A results document containing merge-arm timings may only be
accepted after every leg below is green.

At full scale the deep per-k-mer leg (Leg 3) runs inside Phase 12's protocol —
that is the user-selected MBENCH-02/03 split: Phase 11 defines, implements, and
proves the gate at slice scale; Phase 12 executes it where the rep artifacts
live.

## 2. Leg 1 — Pre-gate (fast, before any timing is trusted)

Run before (and independent of) the deep legs; a failure aborts the run before
any median is computed.

1. **Input Totals reconcile to the committed Phase-10 union anchors.** The
   per-part input Totals must sum to the committed Phase-10 union Totals:
   **8,967,099,203 at k=21** and **8,275,694,030 at k=31**. These anchors are
   recorded constants from the committed Phase-10 results JSONs
   (`.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k{21,31}.json`),
   not new measurements. The Totals compared here are the **sum-of-counts**
   definition — read from the `rustkmer stats -f json` keys
   `unique_kmers`/`total_kmers` (the sanctioned reader, `bench.py` `stats()`)
   or the equivalent jellyfish stats — NEVER the `DatabaseHeader.total_kmers`
   field (see §5).
2. **Merged Distinct >= max input Distinct.** A merge cannot lose the largest
   input's key space: `merged.distinct_kmers >= max(count-A.distinct_kmers,
   count-B.distinct_kmers)`. The boundary case — merged Distinct exactly equal
   to the max input Distinct — PASSES (the gate is `>=`); one count short on
   either side raises (GREEN/RED unit-proven).
3. **Source fingerprints match the manifest.** Input artifact sha256 + size
   must match the prepare-inputs manifest records (D-04) — a silently swapped
   or regenerated input invalidates everything downstream (Pitfall 8).

Aggregate conservation invariants enforced before any results doc is accepted
(the implemented gate raises `RuntimeError` when any of these fail):

- rustkmer-merge Total == jellyfish-merge Total == (count-A Total + count-B Total)
- rustkmer-merge Distinct == jellyfish-merge Distinct
- merged Distinct >= max input Distinct (boundary exact-at-max passes)

## 3. Leg 2 — Ground-truth leg (once per k)

An **independent recount of the union**: one count over both parts as a single
input list — exactly what the count-A-style arm produces when fed the part pair
— diffed against the merged database **per k-mer**. The merge of two disjoint
part databases must equal one count over all their reads; this is the only leg
anchored outside the two merge tools. Disjoint key-spaces make merged Distinct
equal the union Distinct. If the inputs are NOT a clean partition of one read
set, this leg is redesigned — never skipped silently (Pitfall 2).

## 4. Leg 3 — Cross-tool leg (the verdict gate): dump vs dump

`rustkmer dump` of the merged `.rkdb` vs `jellyfish dump -c` of the merged
`.jf`:

1. Run both dumps (list-form subprocesses, fail-loud on non-zero exit).
2. Strip `#`-prefixed rustkmer comment header lines.
3. Normalize both outputs to `(k-mer, count)` pairs: split each data line on
   whitespace; any line that does not parse into exactly a k-mer and an integer
   count is a loud `RuntimeError` naming the offending line (a tolerant parser
   would let the gate run against nothing — T-11-09).
4. A zero-line or absent dump from either side is a loud `RuntimeError` — an
   empty dump can never pass (probe MBENCH-02/empty: the vacuous-gate class).
5. Sort both normalized line sets with **LC_ALL=C** byte ordering
   (deterministic; probe MBENCH-02/ordering). Keys are unique within each dump,
   so byte equality after sorting is per-k-mer count equality — the two dumps
   must agree at every shared key, and the gate accepts nothing less than exact
   identity (probe MBENCH-02/adjacency).
6. Byte-compare the sorted sides. Any first differing line pair — or a length
   mismatch — is a loud `RuntimeError` naming the difference.

Aggregate equality alone NEVER satisfies the gate: Distinct/Total equality is
Leg 1's fast check; per-k-mer dump equality is the verdict (prohibition:
"no aggregate-only comparison is presented as parity"). This is the structural
defense against jellyfish merge's silent canonicality mixing (§6), which
conserves every aggregate while corrupting the key space.

## 5. total_kmers definition naming (the IN-03 collision)

Two colliding definitions of "total kmers" exist in this codebase, and every
check in this document names which one it uses:

| Definition | Source | Meaning |
|---|---|---|
| **sum-of-counts** | `rustkmer stats -f json` keys `unique_kmers`/`total_kmers` (the sanctioned reader, `bench.py` `stats()`); `jellyfish stats` Distinct/Total | Sum of per-k-mer counts (what counting/merging conserve) |
| **record count** | `DatabaseHeader.total_kmers` field (`format.rs`) — the header record count (`entries.len()`) | Number of stored entries, NOT the sum of their counts |

Every Leg 1 conservation check uses **sum-of-counts** values carried on the arm
dicts by the protocol's stats readers. No conservation check ever reads the
header record-count field, and the two definitions are never mixed in one
comparison (IN-03; milestone Pitfall 2). Conservation sums either stream
entries or read the stats JSON — never the header.

## 6. Canonicality assertion

All merge inputs are canonical, pinned structurally — not by discipline: ONE
`BenchmarkConfig` (canonical=True) drives both tools' command lines, so every
count arm on both sides derives from the same config object. jellyfish merge
silently accepts canonicality-mixed inputs (demonstrated on the pinned 2.3.1
binary: a non-canonical + canonical merge of the same reads exits 0 with a
plausibly-shaped database whose key space is meaningless — milestone Pitfall 1).
Conservation checks cannot catch this; the per-k-mer dump comparison of Leg 3
structurally cannot pass a mixed key space, because forward/canonical key
variants appear as distinct keys and fail exact identity.

## 7. Scope conditions (recorded, not engineered)

- **Saturating add:** rustkmer merge uses `saturating_add` at u32 (WR-02
  triaged debt) while jellyfish counters are variable-length. At two
  human-scale parts (k=21/31, max counts ~1e4–1e5) overflow is unreachable.
  This is a stated scope condition of the gate, not something the gate
  engineers around; if a future input class approaches u32::MAX, the gate's
  Total equality must be re-examined before trust.
- **Phase 12 execution order:** the gate stage runs BEFORE round 0 of the
  Phase 12 full-scale session — no timed round is trusted before the gate is
  green on that session's artifacts. At full scale, Leg 3 executes inside the
  Phase 12 protocol (MBENCH-02/03 split, §1).

## 8. Implementation mapping (check-for-check)

| Spec check | Implementation | Unit proof |
|---|---|---|
| Leg 1 aggregate invariants | `assert_merge_parity(by_name)` in `bench.py`, wired after `run_comparison_protocol` before the results doc is written | `test_merge_arms.py::TestAssertMergeParity` (GREEN on conserved fixture; RED on rustkmer-total mismatch, jellyfish-total mismatch, distinct inequality, distinct below max input) |
| Leg 3 normalization | `normalize_dump_lines(text)` — skips `#` comments, splits on whitespace, fails loud on malformed/empty | `test_merge_arms.py::TestNormalizeDumpLines` |
| Leg 3 dump-vs-dump | `dump_vs_dump_equal(rkdb_path, jf_path, rustkmer, workdir)` — list-form dumps, fail-loud rc, LC_ALL=C-ordered sort, byte comparison, first-difference reporting | `test_merge_arms.py::TestDumpVsDumpEqual` (equal pair passes; altered count fails with the mismatch; empty side fails loudly); live slice-scale proof on real data (Plan 11-04 Task 3) |
| merge-t1 conservation | self-check extension: the merge-t1 arm, when present, satisfies the same Total-conservation and Distinct-union invariants as merge | full-suite run (Plan 11-04) |

---
*Phase: 11-merge-characterization-harness-prep — MBENCH-02*
*This document is the gate's definition of record; the implementation is checked against it (check-for-check).*
