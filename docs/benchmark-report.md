# rustkmer vs Jellyfish2 — milestone benchmark report

*Mechanically rendered from the committed results JSONs by `scripts/bench/bench.py --render-report`. Every measurement below is read from those JSONs — the renderer contains no measurement literals — and re-rendering reproduces this file byte-for-byte, so a hand-edited number is detectable (BENCH-02/T-04-07).*

## Dataset provenance

**CRR2044018 is the user-approved substitute for CRR1936095** (CRR1936095 was absent from this host's disk; the substitution was approved 2026-10-09). The harness is path-configurable: when CRR1936095 returns, the same protocol re-runs on it via `--input`.

## Headline (primary): k=31 — full-scale counting

| arm | tool | median wall (s) | median peak RSS (GiB) | wall vs jellyfish | RSS vs jellyfish | per-rep wall (s) | per-rep RSS (GiB) | CV wall |
|-----|------|-----------------|----------------------|-------------------|------------------|------------------|-------------------|---------|
| count-A | rustkmer | 494.19 | 55.22 | -41.4% | -34.3% | 494.19 / 494.18 / 499.98 | 55.42 / 55.22 / 54.56 | 0.7% |
| count-B | rustkmer | 485.89 | 55.29 | -42.4% | -34.2% | 484.65 / 492.59 / 485.89 | 56.28 / 55.22 / 55.29 | 0.9% |
| jellyfish-count-A | jellyfish | 843.02 | 84.00 | baseline | baseline | 843.02 / 657.82 / 875.18 | 83.97 / 86.40 / 84.00 | 14.8% **[cv_warning]** |

**Verdict (k=31):** rustkmer matches-or-beats jellyfish on counting speed — **YES** (rule: every rustkmer count-arm median wall <= jellyfish median wall; rustkmer [494.19, 485.89] s vs jellyfish 843.02 s). Peak-memory deltas are in the table above — memory wins/losses are as visible as speed (BENCH-03).

## Secondary: k=21 — full-scale counting

| arm | tool | median wall (s) | median peak RSS (GiB) | wall vs jellyfish | RSS vs jellyfish | per-rep wall (s) | per-rep RSS (GiB) | CV wall |
|-----|------|-----------------|----------------------|-------------------|------------------|------------------|-------------------|---------|
| count-A | rustkmer | 505.77 | 49.27 | +420.0% | +5.2% | 492.89 / 507.78 / 505.77 | 49.27 / 49.23 / 49.73 | 1.6% |
| count-B | rustkmer | 494.14 | 49.73 | +408.1% | +6.2% | 492.42 / 494.14 / 506.47 | 49.73 / 49.60 / 49.73 | 1.5% |
| jellyfish-count-A | jellyfish | 97.26 | 46.84 | baseline | baseline | 92.89 / 97.26 / 102.52 | 46.84 / 46.84 / 46.84 | 4.9% |

**Verdict (k=21):** rustkmer matches-or-beats jellyfish on counting speed — **NO** (rule: every rustkmer count-arm median wall <= jellyfish median wall; rustkmer [505.77, 494.14] s vs jellyfish 97.26 s). Peak-memory deltas are in the table above — memory wins/losses are as visible as speed (BENCH-03).

## BENCH-02 verdict (counting speed, from recorded medians)

**NO** — rustkmer matches-or-beats Jellyfish2 on counting speed across the full-scale tables above (k=31: YES; k=21: NO; rule: every rustkmer count-arm median wall <= jellyfish median wall in every full-scale table). A NO on any k is a valid measured outcome and is reported as-is.

## Count parity evidence (recorded distinct/total equality)

- mode=full k=31: jellyfish-count-A distinct=787,508,352 total=4,448,351,631 vs count-A distinct=787,508,352 total=4,448,351,631 -> EQUAL
- mode=full k=31: count-B distinct=787,508,352 total=4,448,351,631 vs count-A -> EQUAL (same input measured twice)
- mode=full k=21: jellyfish-count-A distinct=663,276,710 total=4,826,823,600 vs count-A distinct=663,276,710 total=4,826,823,600 -> EQUAL
- mode=full k=21: count-B distinct=663,276,710 total=4,826,823,600 vs count-A -> EQUAL (same input measured twice)
- mode=slice k=31: jellyfish-count-A distinct=52,970,251 total=119,972,170 vs count-A distinct=52,970,251 total=119,972,170 -> EQUAL
- mode=slice k=31: count-B distinct=53,827,714 total=119,939,902 — its input differs from input A (see fingerprints; the r2 side of a merge-input run); no jellyfish arm measured it, so this is not a parity claim

## Slice-scale run (k=31) — counting + merge (r1/r2)

| arm | tool | median wall (s) | median peak RSS (GiB) | wall vs jellyfish | RSS vs jellyfish | per-rep wall (s) | per-rep RSS (GiB) | CV wall |
|-----|------|-----------------|----------------------|-------------------|------------------|------------------|-------------------|---------|
| count-A | rustkmer | 16.17 | 5.59 | -29.4% | -93.4% | 16.17 / 16.38 / 16.16 | 5.59 / 5.59 / 5.59 | 0.8% |
| count-B | rustkmer | 16.32 | 5.66 | -28.7% | -93.3% | 16.75 / 16.31 / 16.32 | 5.65 / 5.66 / 5.66 | 1.5% |
| jellyfish-count-A | jellyfish | 22.90 | 84.84 | baseline | baseline | 22.90 / 22.44 / 23.07 | 85.06 / 84.79 / 84.84 | 1.4% |
| merge | rustkmer | 7.55 | 16.94 | n/a | n/a | 7.55 / 7.53 / 7.56 | 16.94 / 16.94 / 16.94 | 0.2% |

- merge total_kmers 239,912,072 == sum of count-arm totals 239,912,072 -> EQUAL (count conservation)
- merge distinct_kmers 77,766,811 >= max input distinct 53,827,714 -> OK (distinct union)

## Methodology

### Run mode=full k=31 (created 2026-10-10T16:36:28.355467+00:00)

- reps: 3 measured per arm (one warmup per tool executed and discarded before round 0); cooldown 5 s between runs; threads 16; canonical (-C on both tools)
- counterbalanced schedule: round 0: rustkmer then jellyfish; round 1: jellyfish then rustkmer; round 2: rustkmer then jellyfish
- jellyfish `-s 10G` (generous initial hash; recorded in results)
- decompression arrangement: rustkmer reads the .gz natively; jellyfish receives `gzcat | jellyfish count ... /dev/stdin` — decompression is inside BOTH tools' measured wall; the residual asymmetry (pipe and context-switch overhead on the jellyfish arm only) remains and is stated here per protocol
- cache_state per arm:
  - count-A (rustkmer): unavailable x3
  - count-B (rustkmer): unavailable x3
  - jellyfish-count-A (jellyfish): unavailable x3

### Run mode=full k=21 (created 2026-10-10T17:47:23.191284+00:00)

- reps: 3 measured per arm (one warmup per tool executed and discarded before round 0); cooldown 5 s between runs; threads 16; canonical (-C on both tools)
- counterbalanced schedule: round 0: rustkmer then jellyfish; round 1: jellyfish then rustkmer; round 2: rustkmer then jellyfish
- jellyfish `-s 10G` (generous initial hash; recorded in results)
- decompression arrangement: rustkmer reads the .gz natively; jellyfish receives `gzcat | jellyfish count ... /dev/stdin` — decompression is inside BOTH tools' measured wall; the residual asymmetry (pipe and context-switch overhead on the jellyfish arm only) remains and is stated here per protocol
- cache_state per arm:
  - count-A (rustkmer): unavailable x3
  - count-B (rustkmer): unavailable x3
  - jellyfish-count-A (jellyfish): unavailable x3

### Run mode=slice k=31 (created 2026-10-10T17:53:06.628925+00:00)

- reps: 3 measured per arm (one warmup per tool executed and discarded before round 0); cooldown 5 s between runs; threads 16; canonical (-C on both tools)
- counterbalanced schedule: round 0: rustkmer then jellyfish; round 1: jellyfish then rustkmer; round 2: rustkmer then jellyfish
- jellyfish `-s 10G` (generous initial hash; recorded in results)
- decompression arrangement: rustkmer reads the .gz natively; jellyfish receives `gzcat | jellyfish count ... /dev/stdin` — decompression is inside BOTH tools' measured wall; the residual asymmetry (pipe and context-switch overhead on the jellyfish arm only) remains and is stated here per protocol
- cache_state per arm:
  - count-A (rustkmer): unavailable x3
  - count-B (rustkmer): unavailable x3
  - jellyfish-count-A (jellyfish): unavailable x3
  - merge (rustkmer): unavailable x3

- **Cold cache: PARTIALLY SATISFIED.** Some measured reps recorded cache_state other than purged/runner-fresh (the between-run purge needs sudo and was not run — user-approved no-sudo execution). The cold-cache wording of the BENCH-02 methodology is therefore only partially satisfied; the criterion's evidence is this recording, not a claim.

- cv_warning flags: mode=full k=31 arm jellyfish-count-A: CV 14.8% (threshold 10%) — treat those medians with care

### Input fingerprints (size + sha256 per file, as recorded)

- mode=full k=31: `/Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz` (2,637,234,342 bytes) sha256 `131ca561b851956077b3f15b95e6afc65e6d4f7ffc986c2d2f1973049a559ce9`
- mode=full k=31: `/Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz` (2,637,234,342 bytes) sha256 `131ca561b851956077b3f15b95e6afc65e6d4f7ffc986c2d2f1973049a559ce9`
- mode=full k=21: `/Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz` (2,637,234,342 bytes) sha256 `131ca561b851956077b3f15b95e6afc65e6d4f7ffc986c2d2f1973049a559ce9`
- mode=full k=21: `/Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz` (2,637,234,342 bytes) sha256 `131ca561b851956077b3f15b95e6afc65e6d4f7ffc986c2d2f1973049a559ce9`
- mode=slice k=31: `scripts/bench/scratch/slice-0.fq` (359,504,511 bytes) sha256 `2dd773f99f0207144d2ed8a3c9564fd5e9ac0c4783873f1b7f88fd3696369520`
- mode=slice k=31: `scripts/bench/scratch/slice-1.fq` (359,504,511 bytes) sha256 `1c0d213e1be5742152e5456d841df8295d29ac291e35f2b0b46f8ed09c3e22b4`

### Harness provenance

- harness: `scripts/bench/bench.py` @ git commit `7eb510dae56194a4059afc65e886ee9d9be34ff2`; results schema_version 1
- platform (as recorded): Darwin 25.6.0 arm64, python 3.12.8
- rustkmer binary path (as recorded): `target/release/rustkmer`

### Recorded methodology finding (attempt 1 of the full run)

- The first full-run attempt (2026-10-10) halted at the harness's count-parity gate: rustkmer's single-member gzip decoder silently read only member 1 of the concatenated-gzip input — a small prefix of the 2,637,234,342-byte input fingerprinted below, whose k-mer count was a tiny fraction of jellyfish's full count. The parity gate caught it before any timing was trusted. Fixed in commit `8102985` (MultiGzDecoder + regression test); the results in this report are from the post-fix attempt 2. This is exactly the pre-timing parity gate the methodology mandates.

---

*Generated file — do not edit by hand. Regenerate with `python3 scripts/bench/bench.py --render-report --results <jsons> --out docs/benchmark-report.md`; the evidence JSONs are committed beside this report under `.planning/phases/04-benchmark-validation/`.
