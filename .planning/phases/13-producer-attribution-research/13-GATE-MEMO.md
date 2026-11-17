# Phase 13 — Producer Attribution Gate Memo (D-02)

> Deterministic render of the Phase-13 evidence document (`phase13-producer-attribution`). Every number below cites a named full-scale run record; the renderer reads no clock and no environment.

## 1. Decision

DECISION: NO-GO

Pre-registered D-05 bar: predicted full-wall improvement >= 10.0% on the CONSERVATIVE (efficiency-derated, E = 0.5) model at 16 extractor threads, applied at BOTH k as a conjunction (exactly the bar at both k is GO; either k below is NO-GO). The idealized E=M bound is reported alongside but is never the bar input.

- k=21: conservative predicted improvement 9.6235%
- k=31: conservative predicted improvement 10.7965%

## 2. Stage attribution (D-09)

The four D-09 stage names plus the control correction. A zero or negative delta-corrected inflate share is recorded exactly as measured — never clamped positive, never rounded away from zero.

### k=21

| Stage | Seconds | Source records |
|---|---|---|
| inflate_s | 26.2500 | A/k21/rep1/part=-/input=gzip; A/k21/rep2/part=-/input=gzip; A/k21/rep3/part=-/input=gzip; B/k21/rep1/part=-/input=plain; B/k21/rep2/part=-/input=plain; B/k21/rep3/part=-/input=plain; control/k21/rep1/part=-/input=gzip; control/k21/rep1/part=-/input=plain; control/k21/rep2/part=-/input=gzip; control/k21/rep2/part=-/input=plain; control/k21/rep3/part=-/input=gzip; control/k21/rep3/part=-/input=plain |
| parse_extract_s | 20.9629 | D/k21/rep1/part=part_001/input=plain; D/k21/rep1/part=part_006/input=plain; D/k21/rep2/part=part_001/input=plain; D/k21/rep2/part=part_006/input=plain; D/k21/rep3/part=part_001/input=plain; D/k21/rep3/part=part_006/input=plain |
| route_send_s | 91.7979 | C/k21/rep1/part=part_001/input=plain; C/k21/rep1/part=part_006/input=plain; C/k21/rep2/part=part_001/input=plain; C/k21/rep2/part=part_006/input=plain; C/k21/rep3/part=part_001/input=plain; C/k21/rep3/part=part_006/input=plain; D/k21/rep1/part=part_001/input=plain; D/k21/rep1/part=part_006/input=plain; D/k21/rep2/part=part_001/input=plain; D/k21/rep2/part=part_006/input=plain; D/k21/rep3/part=part_001/input=plain; D/k21/rep3/part=part_006/input=plain |
| output_stage_s | 22.3887 | A/k21/rep1/part=-/input=gzip; A/k21/rep2/part=-/input=gzip; A/k21/rep3/part=-/input=gzip; C/k21/rep1/part=part_001/input=gzip; C/k21/rep1/part=part_006/input=gzip; C/k21/rep2/part=part_001/input=gzip; C/k21/rep2/part=part_006/input=gzip; C/k21/rep3/part=part_001/input=gzip; C/k21/rep3/part=part_006/input=gzip |
| raw_a_minus_b_s | 25.1200 | A/k21/rep1/part=-/input=gzip; A/k21/rep2/part=-/input=gzip; A/k21/rep3/part=-/input=gzip; B/k21/rep1/part=-/input=plain; B/k21/rep2/part=-/input=plain; B/k21/rep3/part=-/input=plain |
| delta_correction_s | -1.1300 | control/k21/rep1/part=-/input=gzip; control/k21/rep1/part=-/input=plain; control/k21/rep2/part=-/input=gzip; control/k21/rep2/part=-/input=plain; control/k21/rep3/part=-/input=gzip; control/k21/rep3/part=-/input=plain |
| count_phase_wall_probe_s | 135.9013 | C/k21/rep1/part=part_001/input=gzip; C/k21/rep1/part=part_006/input=gzip; C/k21/rep2/part=part_001/input=gzip; C/k21/rep2/part=part_006/input=gzip; C/k21/rep3/part=part_001/input=gzip; C/k21/rep3/part=part_006/input=gzip |
| producer_plain_probe_s | 112.7608 | C/k21/rep1/part=part_001/input=plain; C/k21/rep1/part=part_006/input=plain; C/k21/rep2/part=part_001/input=plain; C/k21/rep2/part=part_006/input=plain; C/k21/rep3/part=part_001/input=plain; C/k21/rep3/part=part_006/input=plain |
| worker_busy_total_s | 411.6186 | C/k21/rep1/part=part_001/input=gzip; C/k21/rep1/part=part_006/input=gzip; C/k21/rep2/part=part_001/input=gzip; C/k21/rep2/part=part_006/input=gzip; C/k21/rep3/part=part_001/input=gzip; C/k21/rep3/part=part_006/input=gzip |

### k=31

| Stage | Seconds | Source records |
|---|---|---|
| inflate_s | 21.0200 | A/k31/rep1/part=-/input=gzip; A/k31/rep2/part=-/input=gzip; A/k31/rep3/part=-/input=gzip; B/k31/rep1/part=-/input=plain; B/k31/rep2/part=-/input=plain; B/k31/rep3/part=-/input=plain; control/k31/rep1/part=-/input=gzip; control/k31/rep1/part=-/input=plain; control/k31/rep2/part=-/input=gzip; control/k31/rep2/part=-/input=plain; control/k31/rep3/part=-/input=gzip; control/k31/rep3/part=-/input=plain |
| parse_extract_s | 20.8475 | D/k31/rep1/part=part_001/input=plain; D/k31/rep1/part=part_006/input=plain; D/k31/rep2/part=part_001/input=plain; D/k31/rep2/part=part_006/input=plain; D/k31/rep3/part=part_001/input=plain; D/k31/rep3/part=part_006/input=plain |
| route_send_s | 92.9878 | C/k31/rep1/part=part_001/input=plain; C/k31/rep1/part=part_006/input=plain; C/k31/rep2/part=part_001/input=plain; C/k31/rep2/part=part_006/input=plain; C/k31/rep3/part=part_001/input=plain; C/k31/rep3/part=part_006/input=plain; D/k31/rep1/part=part_001/input=plain; D/k31/rep1/part=part_006/input=plain; D/k31/rep2/part=part_001/input=plain; D/k31/rep2/part=part_006/input=plain; D/k31/rep3/part=part_001/input=plain; D/k31/rep3/part=part_006/input=plain |
| output_stage_s | 41.8384 | A/k31/rep1/part=-/input=gzip; A/k31/rep2/part=-/input=gzip; A/k31/rep3/part=-/input=gzip; C/k31/rep1/part=part_001/input=gzip; C/k31/rep1/part=part_006/input=gzip; C/k31/rep2/part=part_001/input=gzip; C/k31/rep2/part=part_006/input=gzip; C/k31/rep3/part=part_001/input=gzip; C/k31/rep3/part=part_006/input=gzip |
| raw_a_minus_b_s | 19.7300 | A/k31/rep1/part=-/input=gzip; A/k31/rep2/part=-/input=gzip; A/k31/rep3/part=-/input=gzip; B/k31/rep1/part=-/input=plain; B/k31/rep2/part=-/input=plain; B/k31/rep3/part=-/input=plain |
| delta_correction_s | -1.2900 | control/k31/rep1/part=-/input=gzip; control/k31/rep1/part=-/input=plain; control/k31/rep2/part=-/input=gzip; control/k31/rep2/part=-/input=plain; control/k31/rep3/part=-/input=gzip; control/k31/rep3/part=-/input=plain |
| count_phase_wall_probe_s | 135.7916 | C/k31/rep1/part=part_001/input=gzip; C/k31/rep1/part=part_006/input=gzip; C/k31/rep2/part=part_001/input=gzip; C/k31/rep2/part=part_006/input=gzip; C/k31/rep3/part=part_001/input=gzip; C/k31/rep3/part=part_006/input=gzip |
| producer_plain_probe_s | 113.8353 | C/k31/rep1/part=part_001/input=plain; C/k31/rep1/part=part_006/input=plain; C/k31/rep2/part=part_001/input=plain; C/k31/rep2/part=part_006/input=plain; C/k31/rep3/part=part_001/input=plain; C/k31/rep3/part=part_006/input=plain |
| worker_busy_total_s | 396.0691 | C/k31/rep1/part=part_001/input=gzip; C/k31/rep1/part=part_006/input=gzip; C/k31/rep2/part=part_001/input=gzip; C/k31/rep2/part=part_006/input=gzip; C/k31/rep3/part=part_001/input=gzip; C/k31/rep3/part=part_006/input=gzip |

## 3. Predicted-win model (PEXT-02, both ceilings)

Composition rule (D-09): predicted_full_wall = max(parallelizable floor, worker floor) + output_stage_s.

probe-vs-CLI topology: arm C/D probes count ONE file per invocation with a fresh engine, while CLI arms A/B count the pinned pair in ONE engine (RESEARCH Pitfall 7).

### k=21

- PARALLELIZABLE CEILING (derated E=0.5, extractors=8.0): 120.6683 s [D/k21/rep1/part=part_001/input=plain; D/k21/rep1/part=part_006/input=plain; D/k21/rep2/part=part_001/input=plain; D/k21/rep2/part=part_006/input=plain; D/k21/rep3/part=part_001/input=plain; D/k21/rep3/part=part_006/input=plain]
- PARALLELIZABLE CEILING (idealized E=M, extractors=16): 119.3581 s
- WORKER-SIDE CEILING (worker_busy_total_s / WORKER_SCALING_CEILING=16): 25.7262 s [C/k21/rep1/part=part_001/input=gzip; C/k21/rep1/part=part_006/input=gzip; C/k21/rep2/part=part_001/input=gzip; C/k21/rep2/part=part_006/input=gzip; C/k21/rep3/part=part_001/input=gzip; C/k21/rep3/part=part_006/input=gzip]
- serial terms (inflate + route_send): 118.0479 s [C/k21/rep1/part=part_001/input=plain; C/k21/rep1/part=part_006/input=plain; C/k21/rep2/part=part_001/input=plain; C/k21/rep2/part=part_006/input=plain; C/k21/rep3/part=part_001/input=plain; C/k21/rep3/part=part_006/input=plain; D/k21/rep1/part=part_001/input=plain; D/k21/rep1/part=part_006/input=plain; D/k21/rep2/part=part_001/input=plain; D/k21/rep2/part=part_006/input=plain; D/k21/rep3/part=part_001/input=plain; D/k21/rep3/part=part_006/input=plain]
- output stage (sort + write): 22.3887 s [A/k21/rep1/part=-/input=gzip; A/k21/rep2/part=-/input=gzip; A/k21/rep3/part=-/input=gzip; C/k21/rep1/part=part_001/input=gzip; C/k21/rep1/part=part_006/input=gzip; C/k21/rep2/part=part_001/input=gzip; C/k21/rep2/part=part_006/input=gzip; C/k21/rep3/part=part_001/input=gzip; C/k21/rep3/part=part_006/input=gzip]
- anomaly criteria: probe_vs_cli_ratio=0.8586 (band [0.25, 1.0]), worker_busy_ratio=0.1893 (max 1.0), mode=point
- predicted_full_wall = max(120.6683, 25.7262) + output stage = 143.0570 s
- predicted improvement vs fresh arm-A median (158.2900 s): 9.6235% (conservative/derated); idealized E=M bound: 10.4512%
- arm-A citations: A/k21/rep1/part=-/input=gzip; A/k21/rep2/part=-/input=gzip; A/k21/rep3/part=-/input=gzip

### k=31

- PARALLELIZABLE CEILING (derated E=0.5, extractors=8.0): 116.6138 s [D/k31/rep1/part=part_001/input=plain; D/k31/rep1/part=part_006/input=plain; D/k31/rep2/part=part_001/input=plain; D/k31/rep2/part=part_006/input=plain; D/k31/rep3/part=part_001/input=plain; D/k31/rep3/part=part_006/input=plain]
- PARALLELIZABLE CEILING (idealized E=M, extractors=16): 115.3108 s
- WORKER-SIDE CEILING (worker_busy_total_s / WORKER_SCALING_CEILING=16): 24.7543 s [C/k31/rep1/part=part_001/input=gzip; C/k31/rep1/part=part_006/input=gzip; C/k31/rep2/part=part_001/input=gzip; C/k31/rep2/part=part_006/input=gzip; C/k31/rep3/part=part_001/input=gzip; C/k31/rep3/part=part_006/input=gzip]
- serial terms (inflate + route_send): 114.0078 s [C/k31/rep1/part=part_001/input=plain; C/k31/rep1/part=part_006/input=plain; C/k31/rep2/part=part_001/input=plain; C/k31/rep2/part=part_006/input=plain; C/k31/rep3/part=part_001/input=plain; C/k31/rep3/part=part_006/input=plain; D/k31/rep1/part=part_001/input=plain; D/k31/rep1/part=part_006/input=plain; D/k31/rep2/part=part_001/input=plain; D/k31/rep2/part=part_006/input=plain; D/k31/rep3/part=part_001/input=plain; D/k31/rep3/part=part_006/input=plain]
- output stage (sort + write): 41.8384 s [A/k31/rep1/part=-/input=gzip; A/k31/rep2/part=-/input=gzip; A/k31/rep3/part=-/input=gzip; C/k31/rep1/part=part_001/input=gzip; C/k31/rep1/part=part_006/input=gzip; C/k31/rep2/part=part_001/input=gzip; C/k31/rep2/part=part_006/input=gzip; C/k31/rep3/part=part_001/input=gzip; C/k31/rep3/part=part_006/input=gzip]
- anomaly criteria: probe_vs_cli_ratio=0.7645 (band [0.25, 1.0]), worker_busy_ratio=0.1823 (max 1.0), mode=point
- predicted_full_wall = max(116.6138, 24.7543) + output stage = 158.4521 s
- predicted improvement vs fresh arm-A median (177.6300 s): 10.7965% (conservative/derated); idealized E=M bound: 11.5300%
- arm-A citations: A/k31/rep1/part=-/input=gzip; A/k31/rep2/part=-/input=gzip; A/k31/rep3/part=-/input=gzip

## 4. Fresh base and v2.0 corroboration (D-03/D-10)

Fingerprint gate: current release binary sha256 `4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b` vs v2.0's recorded fingerprint `8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240d5ec74fc87c3d23` -> branch `re-measure`.

Because the gate fired `re-measure`, arm A's own fresh medians are the ONLY decision denominator. The v2.0 CLI walls (144.69 s k=21 / 147.08 s k=31) are disclosed-fingerprint corroboration only; no memo percentage uses a v2.0 wall as its denominator while the fingerprint mismatch stands.

### D-03/D-10 gate provenance

- current_sha256: `4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b`
- v2_0_sha256: `8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240d5ec74fc87c3d23`
- branch: `re-measure`
- git_commit: `78fc4f4e0594a3400389b636f6977a00e6300dc5`; git_dirty: `False`; build_profile: `release`; platform: `darwin-arm64`; rust_toolchain: `rustc 1.101.0-nightly (07e526db9 2026-10-19)`

## 5. Python-surface context (D-06)

The decision surface is the CLI count wall only. The Python-surface walls (k=21 165.05 s, k=31 178.22 s) are context only, recorded against the v2.0 module fingerprint `6d5264316e5c3e0587430cd87b49694e408871ddd780619950550cd7f5558ae3`. The binary-fingerprint caveat applies: those Python walls were measured on a different binary fingerprint than the current release build, so they are neither a denominator nor a headline — context only.

## 6. Revisit conditions (NO-GO)

PEXT-03/04 remain unexecuted BY RECORDED DECISION. Revisit only if one of the following changes and is re-pre-registered before any measurement:

- the conservative predicted improvement at either k rises to >= 10.0% on a fresh full-scale session (bar unchanged);
- the inflate share measures >= ~20% of producer wall, firing the separate zlib-rs decision;
- the arm-C/D topology confound is removed by a paired instrument, turning the bounds interval into point shares.

## 7. Lifecycle / deletion record (D-04)

Plain inputs were decompressed once into `/Users/forrest/Data/data/illumina/CRR1936095-plain` (the `CRR1936095-plain` path token) and are regenerable per part:

    gunzip -c <DATASET_DIR>/<part>.fq.gz > /Users/forrest/Data/data/illumina/CRR1936095-plain/<part>.fq

Their provenance (part, path, size_bytes, sha256, decompression_command) is recorded in the evidence document's prep block BEFORE any deletion; deletion happens only after this memo is committed.
