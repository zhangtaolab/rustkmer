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

PENDING — filled after the Task 2 decision.

## 8. Provenance (stage-recorded, D-04 — zero manual transcription)

- `command_line` per artifact (sample, part_001.k21): `/Users/forrest/GitHub/rustkmer/target/release/rustkmer count -k 21 -C --threads 16 -o /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.rkdb -i /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz` (16 = all cores)
- `binary_provenance`: release profile, git_commit, rust_toolchain, platform — recorded verbatim by `binary_provenance`; manifest `created` 2026-11-16T14:34:12.648643+00:00, `stage: rkdb`
- `source_fingerprints`: recorded by the stage at build time (§1)

## 9. Retention (D-02)

All artifacts stay on disk until the Phase 12 verdict lands, then cleanup. No early `.jf` deletion — regeneration costs more than ~22 GiB of disk and forces re-running the jellyfish merge arms.
