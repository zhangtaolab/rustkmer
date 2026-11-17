# rustkmer vs Jellyfish2 — milestone benchmark report (v2.0 counting + Phase-12 merge verdict)

*Number contract: every measurement number in this document is transcribed from the mechanically rendered
Phase-12 merge-verdict report (`.planning/phases/12-full-scale-merge-verdict/12-MERGE-REPORT.md`), which is
itself rendered from the committed evidence JSONs by `python3 scripts/bench/phase11.py --stage render` — that
renderer holds no measurement literals and consults no clock, so re-rendering reproduces the mechanical report
byte-for-byte (proof recorded in `12-RENDER-PROOF.json`) and a hand-edited number is detectable (T-12-01). This
document is hand-shaped prose bound to that report: its measurement numbers must be greppable in the mechanical
report, and the only decimals outside it are the pinned context numbers (dataset part sizes, cleanup size, v2.0
verdict references), each traceable to committed provenance and labeled as context. The evidence JSONs named in
the footer are the regeneration source.*

## Dataset provenance

**CRR1936095** (GSA-human WGS, NovaSeq 150 bp paired-end) is the benchmark dataset: six single-member gzip
parts of read 1, ~2.79 GB each, ~16.7 GB total, at
`/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/` — outside the repo, not committed. The pinned
benchmark and merge arrangement is the **part_001 + part_006** pair; its source fingerprints as recorded at
build time and committed in `.planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md`
(section 1):

- `CRR1936095_r1.part_001.fq.gz` — 2,785,381,389 bytes, sha256 `dae91042e42c1a05…1b0de`
- `CRR1936095_r1.part_006.fq.gz` — 2,785,388,289 bytes, sha256 `b197f16c31dd3409…7f07e`

(An earlier "two split parts" dataset description that circulated in project docs was inaccurate; it was
corrected to the six-part description above on 2026-11-16.)

**Merge-input lifecycle (Phase 11 build → Phase 12 wrap-up deletion).** The 8 full-scale merge-input artifacts
(4 `.rkdb` + 4 `.jf`, ~86.74 GiB total) were pre-built from the pinned pair by
`scripts/bench/prepare_inputs.py` (rkdb stage then jf stage, 2026-11-16; per-artifact sha256 and sizes in the
input-fingerprints section below and in `11-PREPARE-RECORD.md`), parity-validated, and retained on disk until
the Phase-12 verdict landed (Phase-11 retention decision D-02). In the Phase-12 wrap-up (decision D-03, plan
12-03) the 8 artifacts were deleted — strictly after every verdict-evidence commit (round-0 record + parity
JSONs + timed results JSONs + verdict + mechanical report + render proof, plus this document's rewrite commit)
had landed in git. `manifest.json` is retained beside them at
`/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/manifest.json` and records every artifact's sha256
and size, so nothing one-way was destroyed: the artifact set is rebuildable with
`python3 scripts/bench/prepare_inputs.py build` (roughly 30–90 minutes).

## Headline: full-scale merge verdict (Phase 12 session, 2026-11-17)

Both tools merged their own representation of the identical, parity-validated input pair at full scale;
exactly 3 counterbalanced reps per arm per k; verdict medians read from the recorded walls:

| k | verdict | rustkmer merge median wall (s) | jellyfish merge median wall (s) |
|---|---|---|---|
| 21 | YES | 63.34 | 88.44 |
| 31 | YES | 82.86 | 114.7 |

**Overall: YES — decision NO-INVEST (exit code 0).** Both outcomes are valid recorded results.

Rule (verbatim from `12-VERDICT.json`): acceptance compares merge-arm wall medians only; rustkmer merge is YES
at a k when its median wall <= the jellyfish-merge median wall at that k (equality is match-or-beat; no
tolerance band); overall YES requires YES at both k=21 and k=31; merge-t1 is scaling evidence and never enters
the verdict

## Comparator-shape asymmetry

each tool merges its own representation of identical, parity-validated input data. Threads/flags/merge-route/
sha256 are recorded per arm below; defaults-only flags during measurement (no flag sweep — MBF-01 is
post-verdict v2.2+ work, only on INVEST).

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

The like-for-like arm: merge-t1 (`--num-threads 1`) reads as a like-for-like single-worker scheduling point:
the CLI child pool contract is exactly 2 OS threads at N=1 (2N+1 at N>1, tests/thread_pool_size_tests.rs), not
a one-OS-thread measurement; merge-t1 is scaling evidence and never enters the YES/NO verdict. The rate rows
above also make the output-format asymmetry visible — rustkmer's `.rkdb` entries cost 20 bytes each while
jellyfish's `.jf` records cost 10 bytes at k=21 and 12 bytes at k=31 — so byte-rate comparisons across tools
reflect format, not effort.

## Parity evidence (three-way gate green BEFORE any timed round)

- k=21: legs [leg1-aggregate-conservation, leg2-recount-vs-merged, leg3-dump-vs-dump]; anchors exact=True
  expected=8967099203 actual=8967099203; merges recorded=2
- k=31: legs [leg1-aggregate-conservation, leg2-recount-vs-merged, leg3-dump-vs-dump]; anchors exact=True
  expected=8275694030 actual=8275694030; merges recorded=2

Leg 2 recounts the pinned pair as ONE input list and asserts the sum-of-counts Total exactly against the union
anchor before the per-k-mer diff; leg 3 is the streaming per-k-mer dump-vs-dump deep leg — the only full-scale
deep-leg route (the in-process comparator form is unit-level only). No timed rep ran before these gates were
green at both k.

## Predicted vs measured (ladder extrapolation)

| k | arm | predicted wall (s) | measured median wall (s) | delta (s) |
|---|---|---|---|---|
| 21 | merge | 53.84865958547661 | 63.34 | 9.491340414523393 |
| 21 | jellyfish-merge | 77.26391787523114 | 88.44 | 11.176082124768854 |
| 31 | merge | 73.36277547930045 | 82.86 | 9.497224520699547 |
| 31 | jellyfish-merge | 105.52449658729188 | 114.7 | 9.175503412708125 |

Caveat (verbatim from the recorded ladder doc): slice-scale extrapolation under a two-point linear model —
MBENCH-04's predicted-vs-measured check at full scale is the backstop (D-07); no slice-scale number is
presented as a full-scale prediction without this caveat and the backstop named (milestone Pitfall 14)

The predicted walls were scheduling inputs; the measured medians are the deliverable, and the deltas are
recorded as findings in the mechanical report — never smoothed or re-run.

## Memory is context, not a decision axis

Peak RSS and physical footprint are recorded per rep as context only — the merge verdict compares recorded
wall medians only. No memory-superiority claim over the streaming jellyfish merge comparator is made or
implied (milestone Pitfall 6).

## Input fingerprints (the 8 merge-input artifacts, as recorded)

- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.rkdb` —
  sha256=`409b76362e37f3794de9e8c2d1c12edb9b6157a59d7bcd51a5d51faa25383c63` size_bytes=13292834822
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k21.rkdb` —
  sha256=`9748ef7798b54bbac3db0928df3830f383e5f0e62f8c767149a03b03ffcc409d` size_bytes=13294483202
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.jf` —
  sha256=`5f14f78eaee40591d4fec4c2e8089c4300d8832674438a153359584f00bc309e` size_bytes=6646418886
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k21.jf` —
  sha256=`136803aca29972cc6a6d11a2ca60c191cf542d5f2450f4b7cb6dee24943e6729` size_bytes=6647243076
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k31.rkdb` —
  sha256=`c2c7ebdf6bb15f967c794c423cd69e303aa22ff66b7a48a889c5842fd5c07f23` size_bytes=16641359442
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k31.rkdb` —
  sha256=`9ab882e29c5a35acfb418784c6b14183aa5c3070c0b63808e6281f77a3eb4f7d` size_bytes=16642703542
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k31.jf` —
  sha256=`a6a40944ba783fcb4107014ffb6cd4d14f0325b393622f9365c5e65823c8c369` size_bytes=9984817368
- `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_006.k31.jf` —
  sha256=`41647a68e729eeba24d7c6daa78f6a2333218d8142de24246d4524504c812c61` size_bytes=9985623828

All 8 artifacts were deleted at the Phase-12 wrap-up (D-03) after the evidence commits landed; the retained
`manifest.json` preserves these exact records for revalidation and rebuild.

## Harness provenance

- rustkmer binary: `/Users/forrest/GitHub/rustkmer/target/release/rustkmer` — size_bytes=2966832
  sha256=`4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b`
- jellyfish binary: `/opt/homebrew/Cellar/jellyfish/2.3.1/bin/jellyfish` — size_bytes=374544
  sha256=`e99c676bbead8f5f520b84359088740aa853b0a0b3b122a21373fe93ae8091ee` (build profile
  pinned-comparator-2.3.1)
- results build: git commit `e9df71af0ba086ed4d50e0bcc7901ab7766c2e5b`, dirty=True, profile release, rustc
  1.101.0-nightly (07e526db9 2026-10-19)
- Renderer source commit (last commit touching the renderer): `68e2f3e5e753ac65c113aba9561bfbc1eaead2b5`
- Controller: `scripts/bench/phase11.py` staged session (revalidate → parity → timed → verdict → render),
  results schema_version 1, honest per-rep `cache_state` and route labels; evidence documents committed in
  `.planning/phases/12-full-scale-merge-verdict/`

## Historical context: the v2.0 counting verdicts (not part of the merge verdict)

The Phase-10 full-scale counting verdict — overall YES at both k on both surfaces — is committed under
`.planning/milestones/v2.0-phases/10-benchmark-verdict/`. Its rustkmer headline walls (CLI 144.69 s at k=21,
147.08 s at k=31) and rustkmer peak-memory references (43.97 GiB at k=21, 68.52 GiB at k=31 — below the
jellyfish comparators recorded there) are historical context for this milestone only and never mix into the
merge-verdict tables above.

---

*Generated-file contract — do not hand-edit numbers in this file. Regeneration source: the Phase-12 evidence
JSONs `.planning/phases/12-full-scale-merge-verdict/12-RESULTS-FULL-K21.json`,
`12-RESULTS-FULL-K31.json`, `12-PARITY-K21.json`, `12-PARITY-K31.json`, `12-VERDICT.json`, mechanically
rendered by `python3 scripts/bench/phase11.py --stage render` into `12-MERGE-REPORT.md` (byte-identical
re-render proof in `12-RENDER-PROOF.json`); phase directory `.planning/phases/12-full-scale-merge-verdict/`.*
