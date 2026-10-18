<!-- generated-by: gsd-doc-writer -->
# Benchmarking Guide

## Overview

The benchmark harness in `scripts/bench/` measures whole-pipeline invocations of the `rustkmer` **release** binary and turns them into a CI-enforced performance regression gate. It is Python 3.10+ stdlib only — no pip installs — and has three moving parts:

| Component | Role |
|-----------|------|
| `scripts/bench/bench.py` | Measurement core: provision inputs → measure under `/usr/bin/time` → sanity-assert counts → reduce to medians → emit schema-versioned `results.json` |
| `scripts/bench/compare.py` | Gate comparator: baseline vs current `results.json` → exit 0 (within) / 1 (regression) / 2 (invalid input) |
| `scripts/bench/gen_synthetic.py`, `make_slice.sh` | Deterministic input provisioning (seeded synthetic FASTQ; first-N-reads gz slice) |

Every headline number comes from OS rusage accounting (`/usr/bin/time -l` on macOS, `-v` on Linux — never a harness-internal clock) and from a `--release` build (never a debug build). Each run measures three rustkmer arms — `count-A`, `count-B` (two disjoint inputs), and `merge` of the two count databases — and asserts `distinct_kmers > 0` on every arm, so a silent zero-count "success" fails the harness. For the milestone results produced with this harness, see the [benchmark report](../benchmark-report.md); maintainer procedures (baseline bootstrap/regeneration verbatim scripts) live in `scripts/bench/README.md`.

## Prerequisites

- **Rust release binary**: `cargo build --release` — the harness invokes `target/release/rustkmer` by default (override with `--rustkmer`).
- **Python 3.10+** (stdlib only).
- `/usr/bin/time` and `gunzip` on PATH (both are measured-run and slice-extraction dependencies).
- **Jellyfish 2.3.x** on PATH — only needed for the parity gate and the multi-rep comparison protocol. The CI gate and plain single-rep runs never invoke jellyfish; if it is requested but absent, `bench.py` exits 2 with an explicit message.

## Input modes and the degradation ladder

`bench.py` runs in one of three modes, resolved by an explicit ladder (`resolve_mode` in `bench.py`):

```text
--mode  >  RUSTKMER_BENCH_MODE (env)  >  size-based resolution
```

1. An explicit `--mode` always wins (an invalid mode string from the environment raises an error — env is a trust boundary).
2. With no mode given, `--input` (or `RUSTKMER_BENCH_INPUT`) is resolved: a directory is scanned for `*.fq.gz` / `*.fastq.gz` (sorted), a plain file is taken as-is, a glob expands via pathlib.
3. Missing/empty input resolves to `synthetic`; otherwise the total input size decides — at or above 1 GiB → `full`, below → `slice`.

| Mode | What it provisions | Typical use |
|------|--------------------|-------------|
| `synthetic` | Two disjoint seeded FASTQ inputs (150 bp reads, seeds 42 and 1337) generated into the scratch dir next to `--out` | CI gate, quick local runs — no dataset needed |
| `slice` | Deterministic first-N-reads extraction (`--slice-reads`, default 1,000,000) of the first two resolved inputs; a single input is extracted once and measured twice | Merge measurements and parity checks on real data |
| `full` | The resolved inputs themselves (first two; a single input measured twice) | Full-scale counting comparisons — pass `--skip-merge` (merge is measured at slice scale) |

Slice extraction uses `gunzip -c | head`-style truncation with identical bytes for the same input and N on every machine. In slice mode, `--merge-input <r2.fq.gz>` provisions the second slice from a separate gz file (the r1/r2 arrangement) instead of a second resolved input; it is rejected outside slice mode.

`mode=full` additionally guards disk space before any measurement: if free space on the output volume is below `--disk-floor-gb` (default 150 GiB — full-run `.rkdb` artifacts alone can reach 55–60 GB per database), the harness aborts with **exit 3**.

## Running benchmarks

```bash
cargo build --release

# 1. Sanity self-check: exact k-mer counts on synthetic input (~1 min)
python3 scripts/bench/bench.py --mode synthetic --self-check

# 2. Plain synthetic run (the CI gate's measurement step)
python3 scripts/bench/bench.py --mode synthetic --out results.json

# 3. Slice of real data (mode auto-resolves to slice below 1 GiB)
python3 scripts/bench/bench.py --input reads.r2.fq.gz --merge-input reads.r1.fq.gz

# 4. Full-scale counting comparison on the real dataset
python3 scripts/bench/bench.py --mode full --input "data/*.fq.gz" --skip-merge --reps 3
```

Key flags (all defined in `bench.py`'s argparse — no others exist):

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | ladder-resolved | `synthetic`, `slice`, or `full` |
| `--input` | none | Input file, glob, or directory (`.fq.gz` scan) for slice/full |
| `--out` | `scripts/bench/scratch/results.json` | Results JSON output path (scratch dir is created next to it) |
| `--self-check` | off | Assert exact k-mer totals on synthetic input (`reads x (L - k + 1)`) plus merge count-conservation in every mode |
| `--k` | `31` | k-mer size (1–64) |
| `--threads` | `os.cpu_count()` | Thread count passed to rustkmer |
| `--reads` | `200000` | Reads per synthetic input |
| `--slice-reads` | `1000000` | Reads per slice in slice mode |
| `--reps` | `1` | Repetitions per arm; `>= 2` engages the fair-comparison protocol |
| `--hash-size` | `10G` | Jellyfish `-s` initial hash size (generous by default; must match `^\d+[KMG]?$`; recorded in results) |
| `--cooldown-s` | `5` | Cooldown sleep between measured runs (thermal/order-bias defense) |
| `--disk-floor-gb` | `150` | Abort `mode=full` (exit 3) below this free space |
| `--merge-input` | none | Slice mode only: second gz input for the r1/r2 merge arrangement |
| `--skip-merge` | off | Omit the merge arm |
| `--rustkmer` | `target/release/rustkmer` | Path to the release binary |
| `--parity-only` | off | Run only the count-parity gate (see below) |
| `--render-report` + `--results` | none | Render the milestone Markdown report from committed results JSONs |

Exit codes: `0` success; `1` harness failure (failed measured command, parity mismatch, self-check violation — the top-level handler prints `bench.py: <reason>`); `2` jellyfish requested but missing, or an argparse usage error; `3` disk-floor abort in full mode.

## The parity gate

A timing comparison between tools that counted different things is meaningless, so parity is proven before any timing is trusted:

```bash
# dev host only — jellyfish must be installed
python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only
```

`--parity-only` provisions one input via the standard ladder, counts it with both rustkmer and jellyfish (commands derived from one shared `BenchmarkConfig` — matched k, canonical mode, threads), and compares `rustkmer stats -f json` against `jellyfish stats`:

- **Exit 0** — `PARITY OK distinct=... total=...` (Distinct and Total equal, and Distinct > 0).
- **Exit 1** — `PARITY MISMATCH` with both tools' numbers. A mismatch is treated as a methodology finding (e.g. N-containing or lowercase real data), never a silent pass.
- **Exit 2** — jellyfish not on PATH.

The same equality assertion also runs automatically inside every multi-rep comparison run, on the measured input itself.

## Multi-rep fair-comparison protocol

With `--reps >= 2` the harness adds a `jellyfish-count-A` arm and runs the interleaved counterbalanced protocol:

- one warmup run per tool, executed and discarded before round 0;
- tool order alternates each round (rustkmer first in even rounds, jellyfish first in odd rounds — the schedule is recorded verbatim in `params.round_schedule`);
- a cooldown sleep (`--cooldown-s`) separates all runs, and the two tools never run concurrently;
- per-rep results are reduced to **medians** with a wall-clock **CV%**; CV above 10% sets a `cv_warning` flag in results.json without failing the run (a noisy measurement is a warning, not an error);
- count parity between the two tools is asserted on the measured input after the protocol.

Single-rep runs (`--reps 1`, the CI path) measure rustkmer-only arms and need no jellyfish.

## Cold-cache methodology

Before every measured rep the harness attempts a cache purge and **records the honest outcome** per rep (`cache_state`), rather than claiming cold cache by configuration intent:

| Condition | `cache_state` |
|-----------|---------------|
| `GITHUB_ACTIONS` set (fresh CI runner, no purge attempted) | `runner-fresh` |
| macOS, `sudo -n purge` succeeded | `purged` |
| macOS, purge failed (e.g. no passwordless sudo) | `unavailable` |
| Any other platform (no purge attempted) | `unavailable` |

The rendered report census treats `purged` and `runner-fresh` as cold-cache-satisfied and prints an explicit "PARTIALLY SATISFIED" note when any rep recorded otherwise.

## Reading results.json

`bench.py` emits a schema-versioned JSON (currently `schema_version: 1`) validated by the single shared validator (`validate_schema` in `bench.py` — the same function `compare.py` and the report renderer import):

```json
{
  "schema_version": 1,
  "mode": "synthetic",
  "resolved_inputs": [],
  "input_fingerprint": [
    {"path": "inputA.fq", "size_bytes": 62800000, "sha256": "..."}
  ],
  "platform": {"system": "Darwin", "release": "...", "machine": "arm64", "python": "3.x"},
  "created": "2026-10-11T00:24:24+00:00",
  "params": {"k": 31, "canonical": true, "threads": 3, "rustkmer": "target/release/rustkmer"},
  "arms": [
    {
      "name": "count-A",
      "tool": "rustkmer",
      "reps": [{"wall_s": 8.93, "peak_rss_bytes": 2496741376}],
      "distinct_kmers": 24000000,
      "total_kmers": 24000000
    }
  ]
}
```

Per-rep entries carry `wall_s` and `peak_rss_bytes` (mandatory — the schema rejects a rep missing either); multi-rep arms additionally carry `median_wall_s`, `median_peak_rss_bytes`, `cv_wall_pct`, `cv_warning`, and per-rep `cache_state` / `round` / `arm_order`. Inputs are fingerprinted with size + sha256 so any results file is reproducible against its exact input. The console tail prints one summary line per arm plus the results path.

## The regression gate (compare.py)

`compare.py` turns a committed per-platform baseline plus a fresh `results.json` into a gate verdict:

```bash
python3 scripts/bench/compare.py \
  --baseline scripts/bench/baselines/bench_baseline.darwin.json \
  --current results.json \
  --wall-threshold 0.25 --rss-threshold 0.15 --wall-advisory
```

- **Exit 0 — within**: every shared arm's medians sit within both thresholds on both axes. A delta exactly equal to a threshold passes; only strictly greater deltas breach; negative deltas (improvements) always pass.
- **Exit 1 — regression**: at least one arm breached a gating threshold. Each breach line names arm, tool, metric, baseline median, current median, delta %, and threshold.
- **Exit 2 — invalid input**: missing/unparseable/schema-violating file, platform mismatch, or an arm present on only one side (arms match by name **and** tool). A gate over broken inputs fails loudly rather than best-effort.

Wall and RSS are judged **independently** — an RSS breach fails the gate even when wall is comfortably within. Thresholds:

| Axis | Threshold | Gating | Rationale |
|------|-----------|--------|-----------|
| Wall-clock | 25% (`--wall-threshold 0.25`) | **Advisory** (`--wall-advisory`) | Shared CI runners show 2–3x run-to-run wall variance; a tighter timing gate false-positives on zero-change PRs |
| Peak RSS | 15% (`--rss-threshold 0.15`) | **Hard** | RSS is far more stable than timing, so memory regressions get the tighter leash and surface earlier than speed regressions |

Under `--wall-advisory`, wall breaches are still measured, printed, and flagged `ADVISORY wall regression ...`, but only RSS breaches fail the gate. This contingency was activated on 2026-10-17 after three consecutive zero-change pushes went red on darwin wall readings spanning 8.45–15.43 s, while peak RSS held within 2.4% — the wall axis was demoted, the RSS threshold was not widened.

## Baselines

Absolute wall/RSS numbers are not comparable across platforms, so each platform flavor has its own committed baseline: `scripts/bench/baselines/bench_baseline.{darwin,linux}.json`, mirroring the CI matrix. A baseline file is the results schema plus a `platform` flavor string and a `host_note` for provenance — the same `validate_schema` accepts both results and baselines, so there is one schema and one validator. Baselines keep **rustkmer arms only** (`count-A`, `count-B`, `merge`): CI current results carry no jellyfish arm, and one-sided arms exit 2.

**Bootstrapping a new platform** (first run has no baseline — the CI compare step exits 2 while the artifact still uploads, which is intentional fail-loud behavior):

1. Push so `benchmark.yml` runs; expect the gate step to fail exit 2 on the missing baseline while both OS legs upload artifacts.
2. Download the platform's artifact — name contract `bench-results-<runner OS>` (Linux/macOS): `gh run download <run-id> --name bench-results-Linux --dir /tmp/bench-linux`.
3. Convert the downloaded `results.json` into the committed baseline (below), commit, push, and watch the second run go green.

Never fabricate a platform's numbers from a different platform's run.

**Regenerating a baseline** (after an intentional performance change or a toolchain/runner shift) uses the same conversion: from a fresh `results.json`, keep rustkmer arms only, add `platform` flavor + `host_note`, re-validate with `validate_schema`, and write the baseline. The verbatim conversion script and procedure are maintained in `scripts/bench/README.md` ("Baseline regeneration"). Sanity-check any regenerated baseline by self-comparing it — every delta must be exactly 0:

```bash
python3 scripts/bench/compare.py \
  --baseline scripts/bench/baselines/bench_baseline.darwin.json \
  --current scripts/bench/baselines/bench_baseline.darwin.json
```

Baseline changes are ordinary reviewed code diffs — a PR that shaves a baseline to pass a marginal change is conspicuous in review.

## CI benchmark workflow

`.github/workflows/benchmark.yml` (workflow name "Benchmark") is the regression gate. It runs on `pull_request` and `push` to `dev`/`main` on an `ubuntu-latest` + `macos-latest` matrix (flavors `linux` / `darwin`), with a 45-minute timeout, per-ref run cancellation, and read-only contents permission. Steps per leg:

1. Checkout, stable Rust toolchain, benchmark-namespaced Cargo cache, Python 3.11.
2. `cargo build --release`.
3. `python3 scripts/bench/bench.py --mode synthetic --out results.json`.
4. Upload `results.json` as artifact `bench-results-<runner OS>` — **before** the gate step, so a missing-baseline exit 2 still leaves the artifact for bootstrapping.
5. Gate: `compare.py` against `scripts/bench/baselines/bench_baseline.<flavor>.json` with `--wall-threshold 0.25 --rss-threshold 0.15 --wall-advisory`.

Gate semantics live only in `compare.py`'s exit codes — the workflow never softens, skips, or re-derives a decision, and a red gate stays red until a human changes code or baseline.

## Rendering the milestone report

`--render-report` is the only writer of the milestone report's numbers. It reads committed results JSONs (`--results`, one or more) and emits Markdown with zero measurement literals of its own and no clock, so re-rendering reproduces a byte-identical file and any hand-edit is detectable:

```bash
python3 scripts/bench/bench.py --render-report \
  --results <full-k31-results.json> <full-k21-results.json> <slice-results.json> \
  --out docs/benchmark-report.md
```

`mode=full` files render as comparison tables in the order given (first = headline, second = secondary); `mode=slice` files render the slice+merge section. At least one `mode=full` file is required, and only `mode=full`/`mode=slice` files are accepted. The committed report at [docs/benchmark-report.md](../benchmark-report.md) was rendered this way from the committed results JSONs of the milestone runs and carries the k=31/k=21 full-scale Jellyfish2 comparison (k=31: YES / k=21: NO), parity evidence, and the full methodology section (reps, schedule, cache states, CV flags, fingerprints).

## Running the harness tests

The harness ships stdlib-unittest suites in `scripts/bench/tests/` (no pytest). Run them from the repo root:

```bash
python3 -m unittest scripts.bench.tests.test_time_parser   # single suite
python3 -m unittest scripts.bench.tests.test_compare \
                       scripts.bench.tests.test_degradation \
                       scripts.bench.tests.test_schema       # several suites
```

| Suite | Covers |
|-------|--------|
| `test_cmd_matrix.py` | rustkmer/jellyfish command construction (fairness matrix, path screening) |
| `test_compare.py` | gate comparator verdicts, thresholds, exit codes |
| `test_degradation.py` | mode-resolution ladder |
| `test_generator.py` | synthetic generator determinism |
| `test_merge_input.py` | `--merge-input` slice provisioning |
| `test_render_report.py` | report renderer determinism and structure |
| `test_schema.py` | results schema contract (includes one real `--self-check` invocation) |
| `test_time_parser.py` | dual-platform `/usr/bin/time` output parsing |

The dual-platform time-parser tests read committed fixtures `scripts/bench/tests/fixtures/time_l_macos.txt` and `time_v_linux.txt`. Some suites (`test_schema`, `test_cmd_matrix`) invoke the real release binary, so build with `cargo build --release` first.

## Helper tools

```bash
# Deterministic synthetic FASTQ (byte-identical for identical arguments)
python3 scripts/bench/gen_synthetic.py --reads 20000 --length 150 --seed 42 --out inputA.fq

# Deterministic first-N-reads slice of a gz stream (identical bytes everywhere)
./scripts/bench/make_slice.sh INPUT.fq.gz 1000000 slice.fq
```

`gen_synthetic.py` seeds the RNG before any sequence generation (the determinism contract); `--reads` and `--out` are required, `--length` defaults to 150 and `--seed` to 42. `make_slice.sh` takes `INPUT N_READS OUTPUT` and validates its arguments.
