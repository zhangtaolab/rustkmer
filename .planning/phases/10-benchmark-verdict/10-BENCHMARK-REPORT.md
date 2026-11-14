# rustkmer vs Jellyfish2 — Phase 10 benchmark report

*Mechanically rendered from the committed result documents by `python3 scripts/bench/phase10.py --stage render`. Every number below is read from those documents — the renderer holds no measurement literals and consults no clock — so re-rendering reproduces this file byte-for-byte and a hand-edited number is detectable (BENCH-V2-02/T-10-05).*

## Dataset provenance

- `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz` — size_bytes=2,785,381,389 sha256=`dae91042e42c1a0562a2bda66b7a3409665cddc87e702d99b922e44160c1b0de`
- `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_006.fq.gz` — size_bytes=2,785,388,289 sha256=`b197f16c31dd34094858adcb25f811194f532ed3ce95523df6ae709f2a37f07e`

- Both split parts of the CRR1936095 read-1 set form ONE measured input per arm; no arm measures a single part.
- The fingerprints above are read from the committed result documents, not re-read at render time.

## k=21

### CLI session

| arm | threads | per-rep wall (s) | median wall (s) | median peak (GiB) | distinct | total | notes |
|-----|---------|------------------|-----------------|------------------|----------|-------|-------|
| rk-t16 | 16 | 145.76 / 143.91 / 144.69 | 144.69 | 43.97 | 897,266,581 | 8,967,099,203 | |
| rk-t1 | 1 | 496.75 / 493.86 / 468.38 | 493.86 | 43.96 | 897,266,581 | 8,967,099,203 | |
| jf-t16 | 16 | 193.81 / 205.6 / 194.85 | 194.85 | 46.84 | 897,266,581 | 8,967,099,203 | |
Scaling evidence (excluded from the verdict): `rk-t1` at 1 thread(s), median 493.86 s.

### Python session

| arm | threads | per-rep wall (s) | median wall (s) | median peak (GiB) | distinct | total | notes |
|-----|---------|------------------|-----------------|------------------|----------|-------|-------|
| jf-t16 | 16 | 200.03 / 197.95 / 196.13 | 197.95 | 46.84 | 897,266,581 | 8,967,099,203 | |
| py-t16 | 16 | 167.83 / 165.05 / 164.31 | 165.05 | 43.28 | 897,266,581 | 8,967,099,203 | |

## k=31

### CLI session

| arm | threads | per-rep wall (s) | median wall (s) | median peak (GiB) | distinct | total | notes |
|-----|---------|------------------|-----------------|------------------|----------|-------|-------|
| rk-t16 | 16 | 148.63 / 147.08 / 146.74 | 147.08 | 68.52 | 1,146,353,600 | 8,275,694,030 | |
| rk-t1 | 1 | 472.57 / 476.29 / 474.31 | 474.31 | 68.51 | 1,146,353,600 | 8,275,694,030 | |
| jf-t16 | 16 | 1377.62 / 1380.92 / 1450.67 | 1380.92 | 88.00 | 1,146,353,600 | 8,275,694,030 | |
Scaling evidence (excluded from the verdict): `rk-t1` at 1 thread(s), median 474.31 s.

### Python session

| arm | threads | per-rep wall (s) | median wall (s) | median peak (GiB) | distinct | total | notes |
|-----|---------|------------------|-----------------|------------------|----------|-------|-------|
| jf-t16 | 16 | 186.51 / 187.14 / 195.22 | 187.14 | 88.01 | 1,146,353,600 | 8,275,694,030 | |
| py-t16 | 16 | 178.22 / 178.43 / 176.85 | 178.22 | 68.78 | 1,146,353,600 | 8,275,694,030 | |

## Verdict

- k=21 (primary acceptance question): **YES** — rustkmer YES (median 144.69 s vs jellyfish 194.85 s), python YES (median 165.05 s vs jellyfish 197.95 s).
- k=21 cross-session jellyfish reference: CLI session median 194.85 s vs Python session median 197.95 s (ratio 1.02x). Both sessions' reference medians are within the documented 2.0x comparability factor.
- k=31 (matched-hash re-verification): **YES** — rustkmer YES (median 147.08 s vs jellyfish 1380.92 s), python YES (median 178.22 s vs jellyfish 187.14 s).
- k=31 cross-session jellyfish reference: CLI session median 1380.92 s vs Python session median 187.14 s (ratio 7.38x). The identical `jf-t16` command counted the same bytes in both sessions, so each surface is judged only against its own session's jellyfish median; no cross-session timing claim is made.
- Overall: **YES** — k=21 is the primary acceptance question; k=31 re-verifies the v1.0 matched-hash comparison.

- Rule: the comparison is `rustkmer_median <= jellyfish_median` per surface in the SAME session; equality counts as match-or-beat, with no tolerance band and no re-roll.
- Only arms recorded at `threads == 16` enter the verdict.
- The t1 arm is scaling evidence only and never enters a YES/NO computation.
- A NO is a recorded outcome, not a failure to explain away; the phase never re-runs until a result turns green.

- BENCH-V2-01 (KMC3 comparison) is descoped: by user decision on 2026-11-13 the KMC3 comparison was removed from this phase's scope. No KMC3 binary was downloaded, installed, or executed, and its absence from this report is intentional.
- the cold-cache criterion is only partially satisfied: no sudo purge was run on this host, so no rep claims a cold cache. Per-rep cache_state census: unavailable x30.
- Dev-host evidence only. No CI-class baseline was regenerated, written, or modified by this phase, and these numbers must never be copied into a CI baseline slot.

## Parity evidence

- k=21: distinct=897,266,581 total=8,967,099,203 — EQUAL across rk-t16 (cli), rk-t1 (cli), jf-t16 (cli), jf-t16 (python), py-t16 (python) on the same two-part input.
- k=31: distinct=1,146,353,600 total=8,275,694,030 — EQUAL across rk-t16 (cli), rk-t1 (cli), jf-t16 (cli), jf-t16 (python), py-t16 (python) on the same two-part input.

## Methodology

- reps: 3 measured per arm; cooldown 5 s between measured runs.
- rotation: round-robin rotation — every round visits every arm once, and round r starts at arm r mod N, so order bias cannot accumulate inside one arm's block.
- one discarded warmup per TOOL before round 0.
- schedule policy: round-robin-rotation; warmup order: rustkmer, jellyfish.
- recorded rotation: round 0: rk-t16 then rk-t1 then jf-t16; round 1: rk-t1 then jf-t16 then rk-t16; round 2: jf-t16 then rk-t16 then rk-t1.
- jellyfish `-s 10G` (generous initial hash).
- rustkmer `--size` stayed at its default and is NOT matched to jellyfish `-s`: rustkmer auto-grows while jellyfish receives a generous `-s`; matching the numbers would pre-reserve roughly 160 GB.
- decompression asymmetry: rustkmer reads the `.gz` natively; jellyfish receives `gzcat <part_001> <part_006> | jellyfish count ... /dev/stdin`, so decompression is inside BOTH measured walls (the residual pipe overhead remains and is stated here per protocol).
- exact counts are re-read from every measured run's OWN output immediately after that run, outside the timed wall, so a rep that silently counts nothing invalidates its arm before any median exists; `rustkmer stats` scans the whole database per read, so these per-rep parity reads are not part of any recorded wall time.
- every number in this report is read from the committed result documents; the renderer holds no measurement literals and consults no clock.

## Provenance

- CLI binary: `/Users/forrest/GitHub/rustkmer/.claude/worktrees/agent-a24abbc9a0da37b75/target/release/rustkmer` — size_bytes=2966832 sha256=`8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240d5ec74fc87c3d23`
- CLI build: git commit `97b3f01c273c11e8780e3af2de5a69016c6cdbe4`, dirty=False, profile release, rustc 1.101.0-nightly (07e526db9 2026-10-19)
- Python module: `/Users/forrest/GitHub/rustkmer/.venv313/lib/python3.13/site-packages/pyrustkmer/pyrustkmer.cpython-313-darwin.so` — size_bytes=1597920 sha256=`6d5264316e5c3e0587430cd87b49694e408871ddd780619950550cd7f5558ae3`
- Python interpreter: /Users/forrest/GitHub/rustkmer/.venv313/bin/python (3.13.11); maturin maturin 1.11.5
- Python session CLI parity reference: `/Users/forrest/GitHub/rustkmer/.claude/worktrees/agent-a5eb35be1e40e77fd/target/release/rustkmer` — size_bytes=2966832 sha256=`8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240d5ec74fc87c3d23`
- Harness source commit (last commit touching this renderer): `d6a5857c250defa509dffc8b9fbdd1947462867f`

---

*Generated file — do not edit by hand. Regenerate with `python3 scripts/bench/phase10.py --stage render --docs <cli-k21.json> <cli-k31.json> <python-k21.json> <python-k31.json> --verdict-out .planning/phases/10-benchmark-verdict/10-verdict.json --out .planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md`; phase directory `.planning/phases/10-benchmark-verdict/`.*
