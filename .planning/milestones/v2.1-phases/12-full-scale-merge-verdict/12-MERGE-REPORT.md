# rustkmer vs Jellyfish2 — Phase 12 full-scale merge verdict report

*Mechanically rendered from the committed evidence documents by `python3 scripts/bench/phase11.py --stage render`. Every number below is read from those documents — the renderer holds no measurement literals and consults no clock — so re-rendering reproduces this file byte-for-byte and a hand-edited number is detectable (T-12-01/T-04-07 contract). The report carries no per-artifact clock fields by construction.*

## Verdict

| k | verdict | rustkmer merge median wall (s) | jellyfish merge median wall (s) |
|---|---|---|---|
| 21 | YES | 63.34 | 88.44 |
| 31 | YES | 82.86 | 114.7 |

Overall: **YES** — decision **NO-INVEST** (exit code 0). Both outcomes are valid recorded results.

Rule: acceptance compares merge-arm wall medians only; rustkmer merge is YES at a k when its median wall <= the jellyfish-merge median wall at that k (equality is match-or-beat; no tolerance band); overall YES requires YES at both k=21 and k=31; merge-t1 is scaling evidence and never enters the verdict

## Comparator-shape asymmetry

each tool merges its own representation of identical, parity-validated input data. Threads/flags/merge-route/sha256 are recorded per arm below; defaults-only flags during measurement (no flag sweep — MBF-01 is post-verdict v2.2+ work, only on INVEST).

### Per-arm methodology (k=21)

| arm | tool | threads | argv | route | output sha256 | binary sha256 |
|---|---|---|---|---|---|---|
| merge | rustkmer | defaults | `target/release/rustkmer merge -i /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.rkdb /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k21.rkdb -o /Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch/merged.k21.rkdb` | not-reported | `75ddd231b674a6ec8e48b6eaa1346209de2e5a81b261963f93979d4bbdb0b73c` | `4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b` |
| merge-t1 | rustkmer | 1 | `target/release/rustkmer merge -i /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.rkdb /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k21.rkdb -o /Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch/merged.k21.rkdb --num-threads 1` | not-reported | `75ddd231b674a6ec8e48b6eaa1346209de2e5a81b261963f93979d4bbdb0b73c` | `4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b` |
| jellyfish-merge | jellyfish | defaults | `jellyfish merge -o /Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch/merged.k21.jf /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.jf /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k21.jf` | not-reported | `8de0aeee50ca4595b532ad70a838d7db58c3e87ccb9c1b41fac633f6488146fe` | `e99c676bbead8f5f520b84359088740aa853b0a0b3b122a21373fe93ae8091ee` |

#### Rates (k=21) — computed only from recorded values

| arm | entry rate (distinct/s) | byte rate (output B/s) | output B/entry |
|---|---|---|---|
| merge | 14165875.92358699 | 283317519.1348279 | 20.000000046808832 |
| merge-t1 | 14437113.129525343 | 288742263.26629126 | 20.000000046808832 |
| jellyfish-merge | 10145483.729081864 | 101454855.1108096 | 10.000001756445668 |


### Per-arm methodology (k=31)

| arm | tool | threads | argv | route | output sha256 | binary sha256 |
|---|---|---|---|---|---|---|
| merge | rustkmer | defaults | `target/release/rustkmer merge -i /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k31.rkdb /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k31.rkdb -o /Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch/merged.k31.rkdb` | not-reported | `c2b974d905b9877589c99ea19964b5cd0b8d85f5e62ef1a8add26318949b1362` | `4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b` |
| merge-t1 | rustkmer | 1 | `target/release/rustkmer merge -i /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k31.rkdb /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k31.rkdb -o /Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch/merged.k31.rkdb --num-threads 1` | not-reported | `c2b974d905b9877589c99ea19964b5cd0b8d85f5e62ef1a8add26318949b1362` | `4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b` |
| jellyfish-merge | jellyfish | defaults | `jellyfish merge -o /Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch/merged.k31.jf /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k31.jf /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k31.jf` | not-reported | `3843f69f014cd4fa7e4495291dc3296c7ed2d1e698a799ad3aac29a7f5af5ad6` | `e99c676bbead8f5f520b84359088740aa853b0a0b3b122a21373fe93ae8091ee` |

#### Rates (k=31) — computed only from recorded values

| arm | entry rate (distinct/s) | byte rate (output B/s) | output B/entry |
|---|---|---|---|
| merge | 13834825.006034276 | 276696500.62756455 | 20.00000003663791 |
| merge-t1 | 13746895.311188392 | 274937906.72742534 | 20.00000003663791 |
| jellyfish-merge | 9994364.428945074 | 119932388.91020052 | 12.00000157717479 |


## Predicted vs measured (ladder extrapolation)

| k | arm | predicted wall (s) | measured median wall (s) | delta (s) |
|---|---|---|---|---|
| 21 | merge | 53.84865958547661 | 63.34 | 9.491340414523393 |
| 21 | jellyfish-merge | 77.26391787523114 | 88.44 | 11.176082124768854 |
| 31 | merge | 73.36277547930045 | 82.86 | 9.497224520699547 |
| 31 | jellyfish-merge | 105.52449658729188 | 114.7 | 9.175503412708125 |

Caveat: slice-scale extrapolation under a two-point linear model — MBENCH-04's predicted-vs-measured check at full scale is the backstop (D-07); no slice-scale number is presented as a full-scale prediction without this caveat and the backstop named (milestone Pitfall 14)

## Parity evidence

- k=21: legs [leg1-aggregate-conservation, leg2-recount-vs-merged, leg3-dump-vs-dump]; anchors exact=True expected=8967099203 actual=8967099203; merges recorded=2
- k=31: legs [leg1-aggregate-conservation, leg2-recount-vs-merged, leg3-dump-vs-dump]; anchors exact=True expected=8275694030 actual=8275694030; merges recorded=2

## Memory is context, not a decision axis

Peak RSS and physical footprint are recorded per rep as context only — the merge verdict compares recorded wall medians only. No memory-superiority claim over the streaming jellyfish merge comparator is made or implied (milestone Pitfall 6).

merge-t1 (--num-threads 1) reads as a like-for-like single-worker scheduling point: the CLI child pool contract is exactly 2 OS threads at N=1 (2N+1 at N>1, tests/thread_pool_size_tests.rs), not a one-OS-thread measurement; merge-t1 is scaling evidence and never enters the YES/NO verdict

## Input fingerprints

- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.rkdb` — sha256=`409b76362e37f3794de9e8c2d1c12edb9b6157a59d7bcd51a5d51faa25383c63` size_bytes=13292834822
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k21.rkdb` — sha256=`9748ef7798b54bbac3db0928df3830f383e5f0e62f8c767149a03b03ffcc409d` size_bytes=13294483202
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.jf` — sha256=`5f14f78eaee40591d4fec4c2e8089c4300d8832674438a153359584f00bc309e` size_bytes=6646418886
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k21.jf` — sha256=`136803aca29972cc6a6d11a2ca60c191cf542d5f2450f4b7cb6dee24943e6729` size_bytes=6647243076
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k31.rkdb` — sha256=`c2c7ebdf6bb15f967c794c423cd69e303aa22ff66b7a48a889c5842fd5c07f23` size_bytes=16641359442
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k31.rkdb` — sha256=`9ab882e29c5a35acfb418784c6b14183aa5c3070c0b63808e6281f77a3eb4f7d` size_bytes=16642703542
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k31.jf` — sha256=`a6a40944ba783fcb4107014ffb6cd4d14f0325b393622f9365c5e65823c8c369` size_bytes=9984817368
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k31.jf` — sha256=`41647a68e729eeba24d7c6daa78f6a2333218d8142de24246d4524504c812c61` size_bytes=9985623828

## Provenance

- rustkmer binary: `/Users/forrest/GitHub/rustkmer/target/release/rustkmer` — size_bytes=2966832 sha256=`4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b`
- jellyfish binary: `/opt/homebrew/Cellar/jellyfish/2.3.1/bin/jellyfish` — size_bytes=374544 sha256=`e99c676bbead8f5f520b84359088740aa853b0a0b3b122a21373fe93ae8091ee` (build profile pinned-comparator-2.3.1)
- results build: git commit `e9df71af0ba086ed4d50e0bcc7901ab7766c2e5b`, dirty=True, profile release, rustc 1.101.0-nightly (07e526db9 2026-10-19)
- Renderer source commit (last commit touching this renderer): `68e2f3e5e753ac65c113aba9561bfbc1eaead2b5`

---

*Generated file — do not edit by hand. Regenerate with `python3 scripts/bench/phase11.py --stage render --results <k21 results> <k31 results> --parity-doc <k21 parity> <k31 parity> --verdict-doc 12-VERDICT.json --ladder-doc 11-LADDER-RESULTS.json --out 12-MERGE-REPORT.md --proof-out 12-RENDER-PROOF.json`; phase directory `.planning/phases/12-full-scale-merge-verdict/`.*
