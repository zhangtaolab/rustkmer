# 04-04 Pilot: Real-Slice Parity Gate + Timing Calibration + Disk Check

**Date:** 2026-10-09
**Host:** Darwin 25.6.0, arm64 (M4 Max, 16 cores, 128 GB RAM), python 3.12.8, jellyfish 2.3.1, rustkmer 0.5.0 (target/release)
**Dataset:** CRR2044018 (user-approved substitute for CRR1936095 — orchestrator decision 2026-10-09, option (c))

## 1. Parity gate on the REAL slice (Pitfall 10 — precondition for full-scale trust)

Command (exactly as planned):

```
python3 scripts/bench/bench.py --mode slice \
  --input /Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz \
  --slice-reads 400000 --parity-only
```

Output line (exit 0):

```
PARITY OK distinct=23241904 total=47989599
```

Interpretation: jellyfish `Distinct` == rustkmer `unique_kmers` = 23,241,904 and
`Total` == `total_kmers` = 47,989,599 on real NovaSeq 150 bp data at k=31
canonical. The 10,401 k-mers missing from the theoretical 48,000,000
(400,000 reads x (150-31+1)) are N-containing windows — both tools skip them
identically. Real-data parity (the thing synthetic parity cannot prove) HOLDS.
No methodology finding; the gate to Task 2 is green.

## 2. Slice provisioning + fingerprint

- Slice: first 400,000 reads of `CRR2044018_r1.fq.gz` (deterministic
  first-4N-lines extraction) = 143,793,955 bytes.
- Slice fingerprint (recorded in `scripts/bench/scratch/calib_k31.json`):
  sha256 `5dcf6920f54ada26...` (full value in the JSON), 143,793,955 bytes.
- Calibration run command (see Deviations for `--reps 2`):

```
python3 scripts/bench/bench.py --mode slice \
  --input /Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz \
  --slice-reads 400000 --reps 2 --out scripts/bench/scratch/calib_k31.json
```

Params: k=31, canonical, threads=16, hash_size=10G (milestone default),
decompressor=gzcat, cooldown 5 s, counterbalanced schedule
(round 0: rustkmer-first, round 1: jellyfish-first), 1 warmup per tool
discarded. Parity was re-asserted by the protocol on the measured input
itself (all arms distinct/total equal above).

## 3. Per-arm slice timings (medians of 2 reps; per-rep values in the JSON)

| Arm | Tool | median wall (s) | median peak RSS | distinct | total | CV% |
|-----|------|-----------------|-----------------|----------|-------|-----|
| count-A | rustkmer | 6.440 | 2,804,375,552 B (2.61 GiB) | 23,241,904 | 47,989,599 | 4.4 |
| count-B | rustkmer | 6.465 | 2,797,551,616 B (2.60 GiB) | 23,241,904 | 47,989,599 | 5.6 |
| jellyfish-count-A | jellyfish | 16.630 | 90,109,960,192 B (83.95 GiB) | 23,241,904 | 47,989,599 | 0.9 |
| merge | rustkmer | 2.390 | 5,193,129,984 B (4.84 GiB) | 23,241,904 | 95,979,198 | 0.6 |

All cache_state labels honestly `unavailable` (`sudo -n purge` cannot succeed
non-interactively; Task 2 is where the cold-cache decision is made).

Notes:
- jellyfish's slice wall is dominated by the fixed `-s 10G` initial-hash
  touch: 04-02 measured ~10.7 s for -s 10G on a 20k-read smoke input, so the
  data-dependent part here is ~5.9 s. Its RSS (~84 GiB) is likewise a
  property of -s 10G, not of the data size.
- rustkmer's slice RSS is table + end-of-run sort/write working set, not a
  per-k-mer linear quantity (20.0 B/k-mer applies to the on-disk `.rkdb`,
  measured below — not to RSS).

## 4. Output sizes (measured)

| Artifact | Bytes | Per-k-mer (distinct=23,241,904) |
|----------|-------|--------------------------------|
| db_count-A.rkdb | 464,838,122 | 20.0 B (format spec confirmed) |
| db_count-B.rkdb | 464,838,122 | 20.0 B |
| db_jellyfish-A.jf | 278,904,624 | 12.0 B |
| db_merged.rkdb | 464,838,122 | 20.0 B (same input twice -> union == input) |

## 5. Full-input measurement (one gunzip pass; makes the extrapolation denominator measured, not assumed)

- `CRR2044018_r1.fq.gz`: 2,637,234,342 bytes gz; sha256
  `131ca561b851956077b3f15b95e6afc65e6d4f7ffc986c2d2f1973049a559ce9`.
- Uncompressed: 13,388,496,200 bytes; 148,961,332 lines = 37,240,333 reads
  (359.5 B/read, matching the slice's per-read size exactly).
- **Scale factor slice -> full r1: 93.11x bytes (93.10x reads).**

## 6. Full-run extrapolation (from the measured numbers above)

| Quantity | Projection | Basis |
|----------|------------|-------|
| distinct 31-mers in full r1 | ~2.16 B (linear upper bound) | 23,241,904 x 93.11; saturation at ~1.8x haploid coverage means the true value is likely somewhat below linear — treat as an upper bound |
| .rkdb per full count | ~43.3 GB (upper bound) | 20.0 B/k-mer measured, x 2.16 B |
| jellyfish .jf per full count | ~26 GB | 12.0 B/k-mer measured |
| Peak disk per full run (db_a + db_b + .jf) | ~112 GB | two rustkmer arms each write a full .rkdb (single input measured twice by design) + one .jf |
| rustkmer full count wall/rep | ~10.0 min | 6.44 s x 93.11 (linear; gz read is native and included) |
| jellyfish full count wall/rep | ~9.4 min (fixed-cost-corrected: 10.7 s + 5.93 s x 93.11) to ~25.8 min (naive linear 16.63 x 93.11) | the honest band; the 10G touch amortizes at full scale, so the corrected figure is the better estimate |
| rustkmer full count peak RSS | ~60-95 GB (wide band) | table (2.16 B x ~16-20 B) + sort/write working set; NOT linearly extrapolable from the 2.6 GiB slice RSS. Fits 128 GB, but this is the widest uncertainty in the projection |
| jellyfish full count peak RSS | ~86-90 GiB | measured at slice; -s 10G pre-sizes the hash (~21% occupancy at 2.16 B distinct -> no doubling expected) |
| k=21 vs k=31 | ~+8% k-mers per read (130 vs 120 windows) | wall within the same band |

Projected total run time for the three milestone commands (with
`--skip-merge` on the full runs — see Deviations):

- One full run (1 warmup/tool + 3 reps x 3 arms + cooldowns):
  ~1.8 h (corrected jellyfish estimate) to ~2.6 h (naive-linear bound).
- Both k values: **~3.6-5.2 h**. Slice+merge run: ~5-10 min.
- **Honest total: ~3.7-5.3 h** — the plan's "~1-2 h" estimate was optimistic;
  the checkpoint presents this corrected number.

## 7. Disk guardrail (live, measured)

- Free on the scratch volume (`scripts/bench/scratch` → system volume):
  **1,600,721,240,064 bytes = 1492 GiB**, far above the harness floor of
  150 GiB (`--disk-floor-gb` default). Projected peak use ~112 GB per full
  run + ~5 GB slice scratch → guardrail green.

## 8. Milestone commands (Task 2 — exactly as calibrated, no ad-hoc invocations)

```
# (a) cold-cache variant — run `sudo -v` first so between-run purges succeed:
python3 scripts/bench/bench.py --mode full \
  --input /Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz \
  --k 31 --reps 3 --skip-merge --out scripts/bench/scratch/full_k31.json
python3 scripts/bench/bench.py --mode full \
  --input /Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz \
  --k 21 --reps 3 --skip-merge --out scripts/bench/scratch/full_k21.json
python3 scripts/bench/bench.py --mode slice \
  --input /Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz \
  --slice-reads 1000000 \
  --merge-input /Users/forrest/Downloads/CRR2044018/CRR2044018_r2.fq.gz \
  --reps 3 --out scripts/bench/scratch/slice_merge.json
# (b) is the same three commands without sudo (cache_state records
# "unavailable" per rep; the report then states the cold-cache criterion is
# only partially satisfied).
```

## 9. Deviations from the plan text (Rule 3 — recorded, minimal)

1. **Calibration ran `--reps 2`, not `--reps 1`.** The plan asks for "one
   timed slice comparison (--mode slice, --reps 1, both tools, k=31)" — but
   the 04-02 harness design engages jellyfish arms / the comparison protocol
   only at `--reps >= 2` (a locked 04-02 decision: CI's reps=1 path stays
   rustkmer-only). `--reps 1` cannot measure "both tools". Two reps is the
   smallest run that satisfies the plan's own "both tools" requirement under
   the real protocol (warmup + counterbalanced rounds + medians included).
2. **`--skip-merge` added to the two full-run commands.** The plan's must_have
   states merge wall/RSS is *reported from the slice-scale run* "keeping the
   full run to the counting comparison the milestone criterion names" — but
   the Task 2 commands as written (reps 3) would engage the merge arm at full
   scale: 4 merges of two ~43 GB databases per k value (hundreds of GB of
   extra I/O, hours of extra wall, ~200+ GB scratch) and a total run far
   outside any 1-2 h budget. The flag (default off; no existing behavior
   changed — CI baselines unaffected) implements the must_have. The
   slice+merge command keeps its merge arm.
3. **Full-input size measured by one `gunzip | wc` pass** rather than
   assuming a compression ratio — the 93.11x scale factor (and every
   projection built on it) is measured.

## 10. Gate decision

Parity on real data at slice scale: **PASS**. Disk above floor: **PASS**
(1492 GiB vs 150 GiB). Full-run cost projected and bounded. The milestone
run (Task 2) may proceed — it needs the user's cold-cache decision
(sudo-terminal vs executor-background) per the blocking-human checkpoint.
