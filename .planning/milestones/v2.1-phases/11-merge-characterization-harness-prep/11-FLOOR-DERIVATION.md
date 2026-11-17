# Phase 11: Derived Disk Floor — Recorded Derivation (11-07, D-10)

**Plan:** 11-07 (wave 3, depends on 11-04/11-05/11-06)
**Decision:** D-10 — the raised disk floor is a **derived formula**: input artifacts + largest single-arm transient (ladder-extrapolated) + safety margin. The derivation consumes measurements, never estimates (research Pitfall 4); this document is the recorded evidence. Re-derive if the inputs change.
**Result: `DEFAULT_DISK_FLOOR_GB = 136`** (replaces the stale 150), enforced in `scripts/bench/bench.py` by the import-time tripwire that re-runs `derive_disk_floor(MEASURED_INPUT_ARTIFACTS_BYTES, LARGEST_SINGLE_ARM_TRANSIENT_BYTES)` against the literal.

---

## 1. Formula (D-10, verbatim)

```
floor_gb = ceil((input_artifacts_bytes + largest_single_arm_transient_bytes) * SAFETY_MARGIN / 2^30)
SAFETY_MARGIN = 1.25   (documented constant, D-10)
```

Implemented as the pure function `derive_disk_floor(inputs_bytes, transient_bytes, margin=SAFETY_MARGIN)` in `scripts/bench/bench.py`; unit-proven in `scripts/bench/tests/test_disk_floor.py::TestDeriveDiskFloor`.

## 2. Term 1 — input artifacts (measured, 11-PREPARE-RECORD.md §11)

| Component | Bytes | Source |
|---|---|---|
| `.rkdb` × 4 (part_001/part_006 × k=21/31) | 59,871,381,008 | 11-PREPARE-RECORD.md §2 (stage-measured, sha256-fingerprinted) |
| `.jf` × 4 (same parts × same k, `-s 1G`/`2G`) | 33,264,103,158 | 11-PREPARE-RECORD.md §10 (stage-measured, sha256-fingerprinted) |
| **Term 1 total** | **93,135,484,166 B (86.74 GiB)** | §11 final inventory |

`MEASURED_INPUT_ARTIFACTS_BYTES = 93_135_484_166` in bench.py cites this section.

## 3. Term 2 — largest single-arm transient (ladder-extrapolated)

Fitted per-entry rates (measured constants, 11-LADDER-RESULTS.json `summary.bytes_per_entry`; both rungs agree to <1e-5 and both tools' linearity verdicts are `linear`, ratio_40_over_10 < 1.4 at threshold 2.0):

| Output class | Rate | Source |
|---|---|---|
| rustkmer `.rkdb` (count and merged) | 20.0 B/entry (both k) | ladder summary; format.rs 20-byte records |
| jellyfish `.jf` (count and merged) | 10.0 B/entry (k=21), 12.0 B/entry (k=31) | ladder summary |

Full-scale union Distinct anchors (committed Phase-10 results, carried in 11-LADDER-RESULTS.json `summary.extrapolated_full_scale.full_scale_entries`): k=21 → 897,266,581; k=31 → 1,146,353,600.

Enumeration of every arm output at its maximum scale (union scale for merge arms, part scale for count arms — the largest is what the formula takes):

| Candidate | Scale | Entries × rate | Bytes | GiB |
|---|---|---|---|---|
| merged `.rkdb` k=31 (rustkmer merge / merge-t1) | union | 1,146,353,600 × 20.0 | **22,927,072,000** | **21.36** ← **largest** |
| merged `.rkdb` k=21 | union | 897,266,581 × 20.0 | 17,945,331,620 | 16.71 |
| merged `.jf` k=31 | union | 1,146,353,600 × 12.0 | 13,756,243,200 | 12.81 |
| merged `.jf` k=21 | union | 897,266,581 × 10.0 | 8,972,665,810 | 8.36 |
| count arm `.rkdb` k=31 (largest count arm, part scale, measured) | part | measured, 11-PREPARE-RECORD.md §2 | 16,642,703,542 | 15.50 |
| count arm `.jf` k=31 (largest jellyfish count arm, measured) | part | measured, §10 | 9,985,623,828 | 9.30 |

`LARGEST_SINGLE_ARM_TRANSIENT_BYTES = 22_927_072_000` — the k=31 rustkmer merged output.

**Temp footprint:** no disk-spill temp was observed at either ladder rung — the merge is the in-memory streaming external-sort merge (peak RSS 1.6–2.3 GiB across rungs/tools, ladder `merges[].peak_rss_bytes`; route not-reported, no scratch files left and `scratch_cleaned: true`). Residual temp/fragmentation variance at full scale is covered by the 1.25 margin applied to the whole sum, not by an invented temp term.

## 4. Arithmetic (stage-checked, unit-proven)

```
inputs      = 93,135,484,166 B   (§2, 86.744 GiB)
transient   = 22,927,072,000 B   (§3, 21.356 GiB)
sum         = 116,062,556,166 B  (108.100 GiB)
sum × 1.25  = 145,078,195,207.5 B
/ 2^30      = 135.1146 GiB
ceil        = 136 GiB
```

`derive_disk_floor(93_135_484_166, 22_927_072_000) == 136` asserted in `test_disk_floor.py::TestDeriveDiskFloor::test_recorded_inputs_yield_the_derived_default`, and bench.py's import-time tripwire fails the module if the literal ever drifts from the formula on the recorded inputs.

## 5. Comparison against the old default (150 GiB)

The derived floor is **lower** than the stale 150. That is the expected outcome, not a weakening: the 150 default was sized for the count-era `-s 10G` artifact regime ("full-run .rkdb artifacts alone can reach 55-60 GB per database + merge scratch", old comment) — under per-part `-s 10G` the four `.jf` artifacts alone would occupy hundreds of GiB (RESEARCH Pitfall 3). The measured regime is per-part `-s 1G`/`2G` (11-05 Task 2 checkpoint, occupancy-derived), and its recorded evidence yields 136 GiB. D-10 explicitly replaces the 150 default with the derivation.

**Scope note (D-12):** the derived default is the bench-level guardrail — the exit-3 pre-flight on `mode=full` runs and the per-rep re-check budget for comparison protocols. The session-level full-budget check (all arms + transients, which exceeds the single-arm term by construction) remains D-12's full-budget pre-flight: Phase 12's controller passes the session's computed full budget explicitly via `--disk-floor-gb`. Slice/rehearsal runs likewise pass their scaled budget explicitly rather than inheriting the full-scale default. Under-floor paths: exit 3 with the stated shortfall, or the explicit `--disk-floor-override` printing the shortfall and continuing — no silent continue (D-11).

---

*Phase: 11-merge-characterization-harness-prep — D-10 recorded evidence (Plan 11-07 Task 1)*
