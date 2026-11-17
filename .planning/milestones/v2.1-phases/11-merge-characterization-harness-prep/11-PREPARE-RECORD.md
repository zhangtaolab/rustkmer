# Phase 11: Full-Scale Prepare-Inputs Record (11-05)

**Plan:** 11-05 (wave 2, depends on 11-02)
**Purpose:** Recorded derivation evidence for the 8 full-scale merge input artifacts (D-01/D-04) — the inputs term of Plan 11-07's disk-floor derivation (D-10). Evidence, not prose: every number below is stage-computed (no manual transcription, D-04) or read verbatim from the manifest the stage wrote.
**Stage:** `scripts/bench/prepare_inputs.py` (built by Plan 11-02)
**Artifacts root:** `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` (outside the repo, D-03)
**Manifest:** `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/manifest.json` (schema_version 1, kind `merge-input-manifest`)

---

## 1. Source fingerprints (stage-recorded; match committed Phase-10 values)

| Part | size_bytes | sha256 | Phase-10 committed match |
|------|------------|--------|--------------------------|
| part_001 | 2,785,381,389 | `dae91042e42c1a05…1b0de` | exact |
| part_006 | 2,785,388,289 | `b197f16c31dd3409…7f07e` | exact |

## 2. Per-part .rkdb build (`build --stage rkdb`, 2026-11-16T14:18–14:34 UTC, wall ~16 min)

| Artifact | size_bytes | sha256 | k | distinct | total | GiB |
|---|---|---|---|---|---|---|
| part_001.k21.rkdb | 13,292,834,822 | `409b76362e37f379…25383c63` | 21 | 664,641,739 | 4,483,548,820 | 12.38 |
| part_006.k21.rkdb | 13,294,483,202 | `9748ef7798b54bba…03ffcc409d` | 21 | 664,724,158 | 4,483,550,383 | 12.38 |
| part_001.k31.rkdb | 16,641,359,442 | `c2c7ebdf6bb15f96…fd5c07f23` | 31 | 832,067,970 | 4,137,846,285 | 15.50 |
| part_006.k31.rkdb | 16,642,703,542 | `9ab882e29c5a35ac…a3eb4f7d` | 31 | 832,135,175 | 4,137,847,745 | 15.50 |

**.rkdb measured total: 59,871,381,008 bytes = 55.75 GiB** (first-ever per-part Distinct measurements — previously only union values existed)

## 3. Union-anchor reconciliation (the parity pre-gate's first live green)

| k | part_001.Total + part_006.Total | committed Phase-10 union anchor | verdict |
|---|---|---|---|
| 21 | 4,483,548,820 + 4,483,550,383 = **8,967,099,203** | 8,967,099,203 | EXACT |
| 31 | 4,137,846,285 + 4,137,847,745 = **8,275,694,030** | 8,275,694,030 | EXACT |

Enforced mid-build by `reconcile_anchors` (per-k, before the next k's counts and before any -s derivation); re-proven post-build from the completed manifest by the plan verify (`revalidate` green + the sums above asserted from `manifest.json`). Totals are the **sum-of-counts** definition (`rustkmer stats -f json` keys `unique_kmers`/`total_kmers`), never the header record-count field (PARITY-GATE.md §5).

## 4. Derived jellyfish -s per k-pair (stage `derive_hash_size`, occupancy target 0.75)

| k-pair | max per-part distinct | derived -s | slots | occupancy = distinct/slots | 0.75 × slots |
|---|---|---|---|---|---|
| k=21 | 664,724,158 (part_006) | **1G** | 1,073,741,824 | 0.6191 | 805,306,368 |
| k=31 | 832,135,175 (part_006) | **2G** | 2,147,483,648 | 0.3875 | 1,610,612,736 |

Derivation rule: smallest standard ladder size with `max_per_part_distinct <= 0.75 × slots`; auto-grow territory unreachable by a full-rung margin. k=21: 500M fails (0.75 × 524,288,000 = 393,216,000 < 664,724,158), 1G is the first satisfying rung. k=31: 1G fails (805,306,368 < 832,135,175), 2G is the first satisfying rung. Both parts of a k-pair share the identical -m/-s/-C (merge hash-size equality precondition, D-01/MBENCH-01).

## 5. Projected .jf sizes + total artifact budget arithmetic (A1: ~5–9 B/slot)

| Component | Low (5 B/slot) | High (9 B/slot) |
|---|---|---|
| k=21 pair: 2 × 1,073,741,824 slots | 10.74 GB | 19.33 GB |
| k=31 pair: 2 × 2,147,483,648 slots | 21.47 GB | 38.65 GB |
| .jf subtotal | 32.21 GB | 57.99 GB (54.00 GiB) |
| .rkdb measured | 59.87 GB | 59.87 GB |
| **Total artifact budget** | **92.08 GB (85.75 GiB)** | **117.86 GB (109.81 GiB)** |

**vs D-01's ~70 GiB estimate:** the measured .rkdb half alone is 55.75 GiB; either end of the A1 projection puts the total at 85.8–109.8 GiB, above ~70 GiB. D-01's figure was estimated before per-part Distinct existed (A2 guessed 450–920M per part; measured 664–832M). Task-2 checkpoint input, not a blocker — actual .jf sizes replace the A1 band the moment the jf stage finishes.

## 6. Disk headroom at record time (df, /System/Volumes/Data — single volume backing repo + data)

- Before the build (14:17 UTC): 415 GiB free. After the build: **359.42 GiB free** (artifact writes account for ~55.75 GiB).
- Transient observation (recorded for honesty, T-11-11): an intermediate df sample moments after the build exited read 0.35 GiB free; it recovered to 359.42 GiB within ~2 minutes with no local APFS snapshots (`tmutil listlocalsnapshots` empty), no swap growth, memory 90% free, and no other writer identified — APFS accounting lag during post-write reclamation, not real exhaustion. Budget reviews must re-sample df after writes settle.
- Headroom vs the projected budget: 359.42 − 54.0 GiB (high-end .jf projection) ≈ 305 GiB remaining post-build — comfortable for Phase 12 transients. Plan 11-07 consumes these numbers for the floor re-derivation (D-10).

## 7. Checkpoint outcome (Task 2 — recorded before any .jf build runs)

**Decision: option-a — the derived -s values are approved as computed. .jf builds commit at `-s 1G` for the k=21 pair and `-s 2G` for the k=31 pair. No adjustment.**

- **Resolved at:** 2026-11-16, Task 2 of plan 11-05. Execution mode: auto (`auto_advance=true` + `_auto_chain_active=true` in `.planning/config.json`; checkpoint gate is `blocking`, not `blocking-human`; plan `auto_select="option-a"` per RESEARCH Open Question 1's resolution). ⚡ Auto-selected: option-a.
- **Approved values:** -s 1G (k=21 pair, occupancy 0.6191) / -s 2G (k=31 pair, occupancy 0.3875) — derived in §4, both ≤ the 0.75 occupancy target with a full-rung auto-grow margin.
- **Budget approval:** approved against measured reality, not the D-01 estimate. Measured .rkdb 55.75 GiB + projected .jf 30.0–54.0 GiB ⇒ total 85.8–109.8 GiB, which **exceeds D-01's ~70 GiB estimate** — the estimate predates per-part Distinct (research A2 guessed 450–920M per part; measured 664–832M). Affordability governs: 359.42 GiB free at decision time ⇒ ~250 GiB headroom even at the high-end projection (§6). Option-b (-s one rung up / 10G everywhere) was rejected as the research anti-pattern (RESEARCH Pitfall 3: four per-part 10G artifacts ≈ hundreds of GiB) — strictly worse on disk, floor, and build time, with no correctness benefit (merge requires hash-size *equality*, not any particular size).
- **Consequence accepted (option-a cons):** the merge-output occupancy consequence is measured-in-advance from the Phase-10 union Distinct anchors riding input-0 capacity (jellyfish merge takes no `-s`; output slots derive from the first input): k=21 merged occupancy = 897,266,581 / 1,073,741,824 = **0.836** (above the 0.75 count-time target — expected, this is the plan option-a con "merge output occupancy roughly doubles"; PARITY-GATE.md Leg-1 Distinct conservation + the Phase 12 deep dump-vs-dump leg are the structural checks there); k=31 merged occupancy = 1,146,353,600 / 2,147,483,648 = **0.534** (comfortable). These two numbers are Plan 11-07 floor-derivation inputs (D-10).
- **A4 closed:** research assumption A4 (`-s 10G` fairness reading vs D-01 budget) resolves as: per-part -s is **derived** (1G/2G), not 10G-everywhere; fairness is preserved by the merge-equality precondition (identical -m/-s/-C within each k-pair) plus recorded occupancy, not by oversized hashes. Research Open Question 1 closes with this record.
- **Disk plan impact:** none negative — Plan 11-07's floor derivation consumes the as-measured numbers (D-10); free-space recheck before each .jf build is Task 3's precondition.

## 8. Provenance (stage-recorded, D-04 — zero manual transcription)

- `command_line` per artifact (sample, part_001.k21): `/Users/forrest/GitHub/rustkmer/target/release/rustkmer count -k 21 -C --threads 16 -o /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.rkdb -i /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz` (16 = all cores)
- `binary_provenance`: release profile, git_commit, rust_toolchain, platform — recorded verbatim by `binary_provenance`; manifest `created` 2026-11-16T14:34:12.648643+00:00, `stage: rkdb`
- `source_fingerprints`: recorded by the stage at build time (§1)

## 9. Retention (D-02)

All artifacts stay on disk until the Phase 12 verdict lands, then cleanup. No early `.jf` deletion — regeneration costs more than ~22 GiB of disk and forces re-running the jellyfish merge arms.

## 10. Per-part .jf build (`build --stage jf`, 2026-11-16T14:42–15:07 UTC, wall ~25 min incl. the stage's pre-build .rkdb identity re-verification)

**Executed -s matches the Task 2 approved values exactly** (asserted against §7 in the plan verify): -s 1G for the k=21 pair, -s 2G for the k=31 pair; no jellyfish auto-grow occurred (occupancy confirmed from records, below).

| Artifact | size_bytes | sha256 | k | -s | occupancy (distinct/slots) | B/entry (measured) | B/slot (measured) |
|---|---|---|---|---|---|---|---|
| part_001.k21.jf | 6,646,418,886 | `5f14f78eaee40591…f00bc309e` | 21 | 1G | 0.6190 | 10.0000 | 6.190 |
| part_006.k21.jf | 6,647,243,076 | `136803aca29972cc…943e6729` | 21 | 1G | 0.6191 | 10.0000 | 6.191 |
| part_001.k31.jf | 9,984,817,368 | `a6a40944ba783fcb…23c8c369` | 31 | 2G | 0.3875 | 12.0000 | 4.650 |
| part_006.k31.jf | 9,985,623,828 | `41647a68e729eeba…504c812c61` | 31 | 2G | 0.3875 | 12.0000 | 4.650 |

.jf measured total: 33,264,103,158 bytes = 30.98 GiB (A1 band was 30.0–54.0 GiB — actual at the low end; B/entry is exactly 10.000 at k=21 and 12.000 at k=31 — 6-byte/4-byte-counter vs 8-byte/4-byte-counter layouts).

## 11. Final inventory + actual vs estimate (manifest `stage: complete`)

| Component | Measured | Projected (§5) |
|---|---|---|
| .rkdb ×4 | 59,871,381,008 B (55.75 GiB) | — (measured pre-checkpoint) |
| .jf ×4 | 33,264,103,158 B (30.98 GiB) | 32.21–57.99 GB (30.0–54.0 GiB) |
| **Total** | **93,135,484,166 B = 86.74 GiB** | 85.75–109.81 GiB |

- **vs D-01's ~70 GiB estimate:** actual 86.74 GiB (+24% over the estimate, inside the recorded projection band, near its low end). The estimate was superseded by measured numbers at the Task 2 checkpoint, as designed.
- **Revalidation proof (Task 3 verify):** `revalidate` green — 4 artifacts + 4 jellyfish inputs re-hashed and re-stat'd against the manifest; k-pair hash-size equality `{21: ['1G'], 31: ['2G']}`; occupancy numeric and ≤ 0.75 on all four (max 0.6191); `jellyfish info` parsed fail-loud on all four (command/where/when/canonical present); approved-vs-executed -s asserted.
- **Free space after the full build:** 372.50 GiB (re-sample taken after APFS settled, per the §6 lesson).
- **Deviation note (verify-command only):** the plan's Task 3 verify snippet expected `occupancy` inside the per-.jf `jellyfish_info` records; the Plan 11-02 stage deliberately keeps occupancy in `hash_size_plan` (jellyfish 2.3.1 `info` carries no occupancy field — probed verbatim, 11-02 decision). The verify was corrected to compute per-.jf occupancy from the manifest's own records (`hash_size_plan.distinct_per_part / slots`) with identical fails_when semantics (non-numeric or > 0.75 fails). No stage or data change; recorded as Rule 3 deviation in 11-05-SUMMARY.md.

## 12. Retention status (D-02, post-build)

All 8 artifacts + manifest on disk at `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/`; retention unchanged — keep until the Phase 12 verdict lands, then cleanup. No early deletion.
