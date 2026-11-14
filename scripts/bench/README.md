# rustkmer benchmark harness

What the harness measures, how to run it, how the CI regression gate works,
and the maintainer procedures for bootstrapping and regenerating baselines.
Python 3.10+ stdlib only — no pip installs anywhere (scripts, CI, or these
procedures).

## What the harness measures

`scripts/bench/bench.py` measures whole-pipeline invocations of the
`rustkmer` **release** binary (`cargo build --release` first — never time a
debug build) under `/usr/bin/time -l` (macOS) / `-v` (Linux):

- **wall-clock** (`wall_s`) and **peak RSS** (`peak_rss_bytes`) per rep,
  from OS rusage accounting — never a harness-internal clock;
- arms: `count-A`, `count-B` (two disjoint seeded synthetic inputs, or the
  resolved real inputs), and `merge` of the two count databases;
- with `--reps >= 2` the interleaved counterbalanced comparison protocol
  engages and adds a `jellyfish-count-A` arm (jellyfish 2.3.x must be on
  PATH; CI never runs this path);
- every run asserts `distinct_kmers > 0` (a silent zero-count "success" is a
  failure), and results land in a schema-versioned `results.json` validated
  by the single shared validator (`validate_schema` in `bench.py`).

The gate comparator `scripts/bench/compare.py` turns a baseline/current
results pair into a verdict with exit codes **0** within, **1** regression
(breach lines name arm, tool, metric, both medians, delta %, threshold),
**2** invalid input (missing/unparseable/schema-violating file, platform
mismatch, one-sided arm). A delta exactly equal to a threshold passes; only
strictly greater deltas breach; wall and RSS are judged independently.

## Quick runs

### v1.0 baseline / synthetic gate

```bash
# sanity self-check (exact k-mer counts on synthetic input; ~1 min)
python3 scripts/bench/bench.py --mode synthetic --self-check

# parity gate vs jellyfish (dev host only — jellyfish must be installed)
python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only

# compare a fresh run against a committed baseline (the CI gate step)
python3 scripts/bench/bench.py --mode synthetic --out results.json
python3 scripts/bench/compare.py \
  --baseline scripts/bench/baselines/bench_baseline.darwin.json \
  --current results.json --wall-threshold 0.25 --rss-threshold 0.15 \
  --wall-advisory
```

### Random-record slicing (PROF-01)

The historical 4M-read head slice is repeat-rich (distinct/instance 2.26 vs
1.76 for a random subslice), so representativeness checks use seeded uniform
random-record slices. `random_slice.py` is single-pass reservoir sampling;
`make_slice.sh`'s first-N behavior is unchanged for the pinned reference.

```bash
python3 scripts/bench/random_slice.py \
  --input /Users/forrest/Data/data/illumina/CRR1936095_r1.part_001.fq.gz \
  --reads 1000000 --seed 20261112 \
  --out slice-random.fq --manifest slice-random.manifest.json
```

The manifest records the source fingerprint, the seed, the requested/actual
record counts, the sorted selected source indices, and the output sha256 —
identical input + seed + record count yields byte-identical FASTQ and JSON.

### Pinned + random parity gates (PROF-01)

`bench.py --slice-selection head|random` provisions the slice; the parity
reference is fingerprint-bound to the full recipe (source sha256 + kind +
reads + k + canonical, plus seed + manifest sha256 for random slices), so a
wrong seed or a changed dataset is exit 2/1, never a convenient pass. Use
`--hash-size 2G` on the real slice: the 1G smoke default silently penalizes
the 229M-distinct input. `--parity-reference` and
`--capture-parity-reference` require `--parity-only` and slice mode.

```bash
SRC=/Users/forrest/Data/data/illumina/CRR1936095_r1.part_001.fq.gz

# pinned head-4M reference (asserts 229,694,874 distinct / 519,271,168 total)
python3 scripts/bench/bench.py --mode slice --input "$SRC" \
  --slice-selection head --slice-reads 4000000 --hash-size 2G --parity-only \
  --parity-reference scripts/bench/baselines/slice_parity.crr1936095.json

# random 1M reference (seed 20261112: 73,578,421 distinct / 129,801,125 total)
python3 scripts/bench/bench.py --mode slice --input "$SRC" \
  --slice-selection random --slice-reads 1000000 --slice-seed 20261112 \
  --hash-size 2G --parity-only \
  --parity-reference scripts/bench/baselines/slice_parity.crr1936095.json

# capture a NEW reference record after a live parity pass (never re-pin the
# pinned head-4M constants; a changed dataset exits 1 instead)
python3 scripts/bench/bench.py --mode slice --input "$SRC" \
  --slice-selection random --slice-reads 1000000 --slice-seed 20261112 \
  --hash-size 2G --parity-only \
  --capture-parity-reference scripts/bench/baselines/slice_parity.crr1936095.json
```

### Thread-scaling gate (PROF-02)

`thread_scaling.py` measures `count` at `--threads 1/4/16` on one input in
counterbalanced rounds and gates on **material** scaling: both
`speedup_t4 = median_wall(t1)/median_wall(t4)` and `speedup_t16` must reach
`--min-speedup` (default 1.3). Exit codes: **0** GREEN, **1** measured
no-op/regression (RED), **2** invalid (missing arm, cross-arm count
mismatch, zero counts, bad provenance, unsupported platform).

```bash
# run mode — measure + verdict (exit 0 when --threads sizes the pool; exit 1
# is a measured no-op/regression)
python3 scripts/bench/thread_scaling.py --mode synthetic --reads 200000 \
  --reps 2 --out thread_scaling.json

# measure only — writes the doc and exits 0 (the CI upload step)
python3 scripts/bench/thread_scaling.py --mode synthetic --reads 200000 \
  --reps 2 --measure-only --out thread_scaling.json

# verdict only — no measurement, reads an existing results doc (CI gate step)
python3 scripts/bench/thread_scaling.py --current thread_scaling.json

# real slice (head selection for comparability with the research matrix)
python3 scripts/bench/thread_scaling.py --mode slice \
  --input /Users/forrest/Data/data/illumina/CRR1936095_r1.part_001.fq.gz \
  --slice-reads 4000000 --reps 3 --out thread_scaling_baseline.json
```

### Live pool-size observation (PROF-02)

`verify_threads.py` observes the ACTUAL rayon pool of a live `count` child
(one independent process per requested N — rayon initializes its global pool
once per process). macOS uses `sample`, Linux `/proc/<pid>/task`; unsupported
platforms exit 2 rather than reporting a false PASS.

```bash
python3 .planning/research/profiling/verify_threads.py \
  --binary target/release/rustkmer --input <large.fastq> \
  --threads 1 4 16 --json thread_observations.json
```

### Contention microbench (PROF-03)

`contention_bench.py` drives the standalone microbench's four
mechanism-isolating arms (shared-counter, shared-dashmap, atomic-only,
thread-local) and persists attribution evidence. Real reads are required for
evidence — `--synthetic` is smoke-only. Exit **0** valid, **1** conservation
failure, **2** invalid.

```bash
python3 scripts/bench/contention_bench.py \
  --input /Users/forrest/Data/data/illumina/CRR1936095_r1.part_001.fq.gz \
  --reads 200000 --seed 20261112 --threads 1 4 16 --reps 3 \
  --out .planning/phases/05-measurement-regression-harness/contention_evidence.json
```

### Python-surface benchmark (PROF-04)

The installed `pyrustkmer` `.so` is prebuilt — rebuild from source before any
Python-surface run (benchmark, differential, or pytest), with `CONDA_PREFIX`
unset and the interpreter's virtualenv pinned to `.venv313`:

```bash
env -u CONDA_PREFIX VIRTUAL_ENV="$PWD/.venv313" PATH="$PWD/.venv313/bin:$PATH" \
  .venv313/bin/maturin develop --release -m pyo3/Cargo.toml
.venv313/bin/python -c "import pyrustkmer; print(pyrustkmer.__version__, pyrustkmer.__file__)"
```

Every Python command in this README uses `.venv313/bin/python`: the system
interpreter has no `pyrustkmer` installed.

Each measured rep is a FRESH worker process under `/usr/bin/time` (no
in-process clock), and each worker takes its own `--threads` value
(`default|N`) — the global rayon pool is first-call-wins, so the threads=1
configuration and the default (all-cores) configuration must never share a
process. Slice mode proves CLI-vs-Python parity on an N-free control BEFORE
timing and commits the dev-host baseline from that control. The real-N arm
is separately labeled `timing-only-real-N-post-D2`: its counts are post-D2
skip-N values and are not comparable to the pre-D2 committed baseline — it
is timing-only evidence, and the N-free control is the only comparison
basis.

```bash
.venv313/bin/python scripts/bench/python_bench.py \
  --python .venv313/bin/python --mode slice \
  --input /Users/forrest/Data/data/illumina/CRR1936095_r1.part_001.fq.gz \
  --slice-reads 1000000 --slice-seed 20261112 --reps 3 \
  --out scripts/bench/scratch/python_bench.json \
  --emit-baseline scripts/bench/baselines/python_bench_baseline.darwin.json
```

`--emit-baseline` is slice-mode only, requires `--threads 1`, and its
filename must match the host flavor (`python_bench_baseline.darwin.json` /
`.linux.json`). The control arm's name is derived from the configuration
actually measured, and comparison selects the baseline arm by identity — the
single arm named `*-n-free-control-t1` whose recorded `threads` is `1` —
never by list position. A synthetic, default-threads, or mislabeled baseline
therefore cannot be committed or consumed as a real one. The committed
baseline file is immutable history — never re-pin it to turn a comparison
green.

#### Baseline comparison mode (Phase 9, dev-host only)

`--compare-baseline` re-proves the N-free control BEFORE any timing: CLI-vs-
Python parity on the same bytes, the committed baseline's exact counts, and
the regenerated control's sha256. It then measures BOTH the `threads=1`
engine-isolation arm and the default-threads user arm as fresh worker
processes, and computes the verdict only from the recorded medians with
locked inclusive thresholds:

- `speedup_t1` = baseline t1 median / new t1 median, must be `>= 1.0x`
  (non-regressive against the committed sequential baseline);
- `speedup_default` = baseline t1 median / new default median, must be
  `>= 1.2x` (the measured win).

There is no noise band. Both arms are always reported. Compare mode
measures both arms itself, so `--threads` must stay at its default `1`;
any other value exits 2 instead of being silently ignored. Every worker
reports the binding's own resolved rayon count (`get_stats().threads`, the
`threads_resolved` field in the arm), and the arm is invalid unless that
observed count matches the configuration the arm requested — a `PyCounter`
that ignores its `threads` argument can never produce a PASS.

```bash
.venv313/bin/python scripts/bench/python_bench.py --mode slice \
  --input /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz \
  --slice-reads 1000000 --slice-seed 20261112 --reps 3 \
  --python .venv313/bin/python --rustkmer target/release/rustkmer \
  --compare-baseline scripts/bench/baselines/python_bench_baseline.darwin.json \
  --out scripts/bench/scratch/python_bench_compare.json
```

Exit contract: `0 = PASS, 1 = valid FAIL (artifact kept), 2 = invalid (no artifact)`.
A valid measurement is written on PASS and on a genuine FAIL; every
invalid path exits 2 with no artifact. The identity guards that exit 2 are:
a platform-flavor mismatch, a `provenance.platform` mismatch, a k/canonical
mismatch, a baseline without exactly one unambiguous threads=1 control arm,
a baseline without a control fingerprint or positive exact counts,
a pre-timing exact-count mismatch, a regenerated-control fingerprint
mismatch, and a worker whose resolved thread count disagrees with its arm's
requested configuration. The artifact carries both measured arms, the
`comparison` and `verdict` blocks, the baseline record (path, sha256,
control median, exact counts), and full provenance.

This is dev-host evidence only: it adds no CI comparison gate, because no
CI-class baseline exists. Phase 10 records dev-host evidence only and
deliberately regenerates no CI-class baseline (see "Phase-10 verdict stages"
below).

### N-read differential (PROF-05)

`n_read_differential.py` records the CLI-vs-Python differential on
N-containing reads. Phase 9's D2 unification landed the CLI's skip-N
semantics on the Python surface too: after D2 both surfaces skip every
length-k window containing a non-ACGT byte, so no chimeric flank-joined
k-mers survive. The no-N control must be exactly equal. Exit **0** measured
verdict, **1** unexpected result, **2** invalid input. The historical
pre-D2 capture below is kept as provenance for the committed Phase 5
artifact; that artifact
(`.planning/phases/05-measurement-regression-harness/n_read_differential.json`,
sha256 `6d929a45…`) is immutable and must never be overwritten by a re-run.

```bash
# Historical pre-D2 provenance re-record (scratch only — never the committed
# Phase 5 artifact):
.venv313/bin/python scripts/bench/n_read_differential.py \
  --out scripts/bench/scratch/n_read_differential_pre_d2_record.json

# Phase 9 re-run AFTER the D2 skip-N unification: every case must be equal
# (exit 0 required). The output is NEW Phase 9 evidence; it never lands on
# the committed Phase 5 artifact.
.venv313/bin/python scripts/bench/n_read_differential.py --expect-unified --previous .planning/phases/05-measurement-regression-harness/n_read_differential.json --rustkmer target/release/rustkmer --out .planning/phases/09-python-parity/evidence/n_read_differential_d2.json
```

`--expect-unified` is the Phase 9 mode: every divergent cell must become
zero, and the before/after block built from `--previous` supplies the
pre-D2 counts.

### Golden capture (Phase 8 input)

`capture_goldens.py` rehashes the 12 committed golden `.rkdb` fixtures and
asserts manifest equality. It never regenerates fixtures and never runs the
ignored generator; a tampered fixture is a blocking finding, not a recapture.

```bash
python3 scripts/bench/capture_goldens.py \
  --out .planning/phases/05-measurement-regression-harness/golden_capture.json
```

## Standing harness gates in CI

`.github/workflows/benchmark.yml` runs, in order: release build → harness
unit suite (`python3 -m unittest discover -s scripts/bench/tests -t .`) →
synthetic BENCH-01 measure/upload/gate → maturin wheel build + install →
`python_bench.py --mode synthetic` + artifact upload → thread-scaling
`--measure-only` + artifact upload → the PROF-02 `--current` verdict (last).
Every measurement and gate step trusts the script exit code directly.

There is deliberately **no Python compare gate** in CI yet: no CI-class
baseline exists, and comparing a CI run against the committed dev-host
baseline would violate the per-runner-class rule. No CI-class baseline is
produced by Phase 10 either — that phase records dev-host evidence only.

## Standing thread gates (PROF-02)

Both PROF-02 gates are **standing** and must remain green. They were RED in
Phase 5 while `--threads` was a silent no-op (Phase 6 PAR-01 fixed the
resolver); they now pin the fixed behavior:

- **Thread-scaling gate** (`scripts/bench/thread_scaling.py`): exits **0**
  only when both `speedup_t4` and `speedup_t16` reach `--min-speedup`. A
  measured no-op or regression is exit **1** — never converted to a pass.
- **Rust standing gate** `pool_size_matches_requested_threads`
  (`tests/thread_pool_size_tests.rs`) runs in the default `cargo test`
  suite: a fresh CLI child per requested N in {1, 4, 16} must observe exactly
  requested + 1 OS threads (rayon workers + main).
- **Characterization test** `pool_size_characterization_records_requested_pool`
  pins the same contract for a single `--threads 1` child in the default
  suite. Single-core hosts skip the comparison because the fixed one-worker
  pool and the old all-cores default coincide there.

### Maintaining the gates

Do not lower the scaling threshold, weaken the pool-size contract, or
recapture the Phase 5 RED baseline to get green. Prohibited constructs, all
of which would launder the gate: GitHub Actions `continue-on-error`, shell
fallbacks such as `|| true` (or `; true`), any conditional on a
measurement/gate step (`if: success() && false`, etc.), and "baseline
recapture" that repins the scaling numbers to make a no-op pass. An
`if: always()` ARTIFACT UPLOAD is not an exception to this rule — see
"CI evidence retention" below.

## Phase-10 verdict stages

`phase10.py` is the Phase-10 verdict controller (BENCH-V2-02). It measures
ONE arm per tool over BOTH split parts of the CRR1936095 read-1 set and is
strictly staged:

| Stage | What it does |
|---|---|
| `synthetic` | four-arm spine proof over two seeded synthetic parts (`mode: synthetic`) |
| `slice-gate` | provisions the head-4M slice from `part_001` once, gates k=21 against the committed pinned reference (its sha256 is re-checked before consumption), and records k=31 as live-parity-only because no pinned k=31 slice reference exists |
| `cli` | full-scale CLI session: `rk-t16`, `rk-t1` (scaling evidence only) and `jf-t16` over both parts |
| `python` | full-scale Python session: `jf-t16` and `py-t16`; consumes the slice-gate artifact, the Python preflight record, and the matching CLI document, validating each one's provenance and input identity, re-deriving the preflight gate against the pinned budget and its measured source distinct/sha256, and pinning each consumed artifact's sha256 in the artifact |
| `preflight-python` | projects the Python peak from the MEASURED CLI distinct count and writes a PROCEED/BLOCKED record |
| `render` | mechanically renders the verdict document and the Markdown report from the committed result documents |

Exit contract (shared with the rest of `scripts/bench/`): **0** valid result
or measured YES, **1** a genuine measured NO (artifacts kept), **2** invalid
or inapplicable (no artifact written). The disk-floor guard keeps its own
exit **3**. The `render` stage publishes the verdict and the report
atomically: on exit 2 neither destination exists.

`render` and `preflight-python` consume recorded JSON only. Their
`provenance` block is the MEASURED CLI provenance carried by the source
documents, so neither stage needs a local release binary or Rust toolchain —
a clean checkout can mechanically re-render the committed verdict.

The Phase-10 verdict artifacts are **dev-host evidence only**: no CI-class
baseline is regenerated, written, or modified, and a dev-host number must
never be copied into a CI baseline slot. Every file under
`scripts/bench/baselines/` is a read-only input whose sha256 is pinned.

## Provenance fields

Every new results/evidence artifact carries a `provenance` block; a path
string without a hash is not provenance. The shared builder is
`binary_provenance` in `scripts/bench/bench.py`:

| Field | Meaning |
|---|---|
| `binary` / `module` | resolved absolute path, size, and sha256 of the ACTUAL executable or native `.so` bytes |
| `git_commit` | repo `HEAD` at measurement (not the last commit touching the script) |
| `git_dirty` | whether the working tree was dirty |
| `build_profile` | `release` (or `release+debug-assertions` where applicable) |
| `rust_toolchain` | `rustc --version` output |
| `platform` | `sys.platform` + machine (e.g. `darwin-arm64`) |
| `python_executable` / `python_version` / `maturin_version` | Python artifacts only: the measured interpreter, its version, and the wheel build tool |

Artifacts also carry `input_fingerprint` (path/size/sha256 of each measured
input), the selection manifest for random slices, and per-arm raw reps with
medians. Python artifacts fingerprint the inner native module, because
maturin 1.11's editable develop wraps the `.so` in a generated shim package.

## Python baseline classes and the CI bootstrap

A baseline's numbers only make sense against the runner class that produced
them. Two classes exist:

- **dev-host class** — the committed
  `scripts/bench/baselines/python_bench_baseline.darwin.json`
  (`baseline_scope: dev-host-local-comparison`). It exists for Phase 9's
  same-host before/after comparison. It must **never** gate CI.
- **CI class** — produced from CI runner artifacts only. No CI-class
  baseline exists today; Phase 10 records **dev-host evidence only** and
  regenerates no baseline. Do not compare across classes.

Bootstrap a CI-class Python baseline the same way the bench baseline is
bootstrapped:

```bash
# 1. Push so benchmark.yml runs; the python bench step uploads its artifact.
gh run list --workflow=benchmark.yml --branch dev --limit 1
gh run watch

# 2. Download the artifact for the runner class you are baselining.
gh run download <run-id> --name python-bench-results-Linux --dir /tmp/py-bench-linux
#   (macOS artifact is python-bench-results-macOS)

# 3. Commit the downloaded result as a CI-class baseline for that platform
#    only (a later phase owns the comparison gate and thresholds). Never copy
#    CI numbers into the dev-host baseline, or dev-host numbers into a CI file.
```

Artifact name contracts: `bench-results-<runner OS>`,
`python-bench-results-<runner OS>`, `thread-scaling-<runner OS>`.

## CI evidence retention

Artifact-upload steps run with `if: always()` (plus `if-no-files-found:
warn`) so a FAILED measurement step still leaves its evidence on the run — a
python_bench exit 2 or a scaling `--measure-only` exit 2 must not lose the
artifact that explains it. Measurement and gate steps never carry a
condition. An `if: always()` upload is **not** error softening: it runs no
gate, and the failed measurement/gate step still fails the job verdict.

## The committed-baseline CI gate

`.github/workflows/benchmark.yml` (the BENCH-01 regression gate) runs on
pull_request and push to `dev`/`main` on an `ubuntu-latest` + `macos-latest`
matrix: `cargo build --release` → `bench.py --mode synthetic` → upload the
runner's `results.json` as artifact `bench-results-<runner OS>` → gate via
`compare.py` against the committed baseline for that platform. The gate
needs neither jellyfish nor the human dataset (BENCH-04): it is
rustkmer-vs-baseline on seeded synthetic input, so it runs on any machine.

**Why baselines are per-platform files.** Absolute wall/RSS numbers are not
comparable across platforms (different cores, memory layout, `/usr/bin/time`
provenance), so each platform flavor has its own committed baseline —
`scripts/bench/baselines/bench_baseline.<flavor>.json` where flavor is
`darwin` or `linux`, mirroring the workflow matrix. The baseline carries a
`platform` field; `compare.py` exits 2 on any platform mismatch rather than
silently comparing a Linux run against macOS numbers. The baseline keeps the
**rustkmer arms only** (`count-A`, `count-B`, `merge`): the CI current
results are produced without jellyfish, and `compare.py` exits 2 on arms
present on only one side, so a jellyfish arm in a baseline would brick the
gate. A dev-host multi-rep run (which does measure a jellyfish arm) is
converted by dropping that arm — the conversion below does exactly this.

A baseline file is the results schema plus the `platform` flavor string (and
a `host_note` for provenance), so the SAME `validate_schema` accepts both
results and baselines — one schema, one validator, no drift.

## Bootstrapping a new platform's baseline

The first run on a platform has no baseline to compare against — the
workflow's compare step exits 2 (missing file) while `bench.py` still
uploads its artifact. That red is correct fail-loud behavior: a gate with
no baseline is not yet a gate. Bootstrap it from the workflow's own
artifacts:

```bash
# 1. Push the branch so benchmark.yml runs on dev.
git push origin dev

# 2. Watch the first run — expect the compare step to fail exit 2 on the
#    missing baseline while both OS legs still upload their artifacts.
gh run list --workflow=benchmark.yml --branch dev --limit 1
gh run watch

# 3. Download the platform's artifact (name contract: bench-results-<runner OS>).
gh run download <run-id> --name bench-results-Linux --dir /tmp/bench-linux
#   (macOS artifact is bench-results-macOS)

# 4. Convert the downloaded results.json into the committed baseline
#    (see "Baseline regeneration" below for the exact command).

# 5. Commit the baseline, push again, and watch the second run go green
#    on both matrix legs.
```

Never fabricate a platform's numbers from a different platform's run — the
baseline must come from that platform's own runner artifact.

## Baseline regeneration (maintainer)

Regenerate after an intentional performance change (or a toolchain/runner
update that shifts the numbers), using the same conversion the bootstrap
uses. From a fresh `results.json` (either a local run or a downloaded CI
artifact):

```bash
python3 - scripts/bench/scratch/results.json \
         scripts/bench/baselines/bench_baseline.darwin.json \
         darwin \
         "regenerated <date> from <host or runner note>" <<'PYEOF'
import json, sys
from datetime import datetime, timezone
sys.path.insert(0, ".")
from scripts.bench.bench import validate_schema

src, dst, flavor, note = sys.argv[1:5]
with open(src) as fh:
    results = json.load(fh)
baseline = {
    "schema_version": results["schema_version"],
    "platform": flavor,
    "mode": results.get("mode"),
    "created": results.get("created"),
    "generated": datetime.now(timezone.utc).isoformat(),
    "input_fingerprint": results.get("input_fingerprint"),
    "params": results.get("params"),
    "host_note": note,
    # rustkmer arms only: CI's current results carry no jellyfish arm, and
    # one-sided arms exit 2 (see README section above).
    "arms": [a for a in results["arms"] if a.get("tool") == "rustkmer"],
}
validate_schema(baseline)  # same validator compare.py uses
with open(dst, "w") as fh:
    json.dump(baseline, fh, indent=2)
    fh.write("\n")
print(f"wrote {dst}: platform={flavor} arms={len(baseline['arms'])}")
PYEOF

# sanity: the baseline must self-compare green (every delta exactly 0)
python3 scripts/bench/compare.py \
  --baseline scripts/bench/baselines/bench_baseline.darwin.json \
  --current scripts/bench/baselines/bench_baseline.darwin.json
```

Baseline changes are ordinary reviewed code diffs (threat T-04-05): a PR
that shaves a baseline to pass a marginal change is conspicuous in review.

## Threshold rationale

- **Wall 25%** (`--wall-threshold 0.25`): GitHub shared runners show 2-3x
  run-to-run wall variance; tighter timing gates false-positive on zero-change
  PRs until developers stop trusting the gate.
- **RSS 15%** (`--rss-threshold 0.15`): peak RSS is far more stable than
  timing, so memory regressions get the tighter leash and surface EARLIER
  than speed regressions (BENCH-03's visibility requirement — memory losses
  must not be gated more loosely than speed).

Both thresholds are the locked orchestrator decision of 2026-10-09. If the
wall axis proves flaky on real zero-change PRs, demote wall to advisory and
keep RSS hard — do not widen RSS.

**Wall advisory activated 2026-10-17.** The contingency's condition was
met: three consecutive zero-change pushes went red (38047563014, 38098134712,
38098497116 — docs-only commits and the baseline regen between them). On
identical code, darwin wall readings spanned 8.45–15.43 s across four runs
(count-A delta −42%…+51% against whichever baseline was committed), so no
single committed baseline survives both runner classes at any sane
threshold; peak RSS meanwhile held within 2.4% of the committed
high-runner-class values on every run. Per the locked decision, the CI gate
now passes `--wall-advisory`: wall deltas are still measured, printed, and
flagged (`ADVISORY wall regression …`) on every run, but only RSS breaches
fail the gate — the RSS threshold did not move. The same-job base-ref
upgrade below remains the path to re-hardening the wall axis.

## Upgrade path: same-job base-ref comparison

The committed-baseline model compares today's run against numbers committed
on another day, so runner-generation drift lands inside the thresholds. The
rigorous upgrade (adopt only if this gate proves flaky) is a same-job
base-ref build: the workflow checks out both the PR merge and the base ref,
builds and measures each in the same job, and compares the two fresh runs —
eliminating committed baselines entirely at roughly double the CI build
cost. Until then, the committed baseline plus the generous wall threshold is
the deliberate tradeoff.

## Layout

```
scripts/bench/
├── bench.py                 # measurement core: provision → measure → sanity → reduce
│                            #   (+ random-record subslicing, parity references)
├── compare.py               # gate comparator (exit 0/1/2) — CI invokes this
├── gen_synthetic.py         # seeded deterministic FASTQ generator
├── make_slice.sh            # deterministic first-N slice tool (unchanged)
├── random_slice.py          # seeded Algorithm R random-record slicer + manifest
├── thread_scaling.py        # PROF-02 t1/t4/t16 scaling gate (exit 0/1/2)
├── python_bench.py          # PROF-04 fresh-worker PyO3 counting benchmark
├── phase10.py               # Phase-10 verdict controller: four arms over both
│                            #   split parts, slice gate, mechanical report (0/1/2)
├── n_read_differential.py   # PROF-05 CLI-vs-Python N-read differential (D2 evidence)
├── contention_bench.py      # PROF-03 four-arm contention microbench controller
├── capture_goldens.py       # read-only golden .rkdb hash capture (Phase 8 input)
├── baselines/
│   ├── bench_baseline.darwin.json          # BENCH-01 per-platform baselines
│   ├── bench_baseline.linux.json
│   ├── python_bench_baseline.darwin.json   # dev-host-class PROF-04 baseline
│   └── slice_parity.crr1936095.json        # pinned head-4M + random parity references
├── tests/                   # stdlib-unittest suites + dual-platform time fixtures
└── scratch/                 # gitignored runtime outputs (slices, dbs, docs)

.planning/research/profiling/
├── verify_threads.py        # live rayon pool-size observer (PROF-02)
├── microbench_main.rs       # four mechanism-isolating contention arms (PROF-03)
├── microbench_Cargo.toml
└── microbench_Cargo.lock    # committed audited lock for the measured closure

.planning/phases/05-measurement-regression-harness/
├── golden_capture.json          # immutable pre-refactor golden capture
├── thread_reality_evidence.json # Phase 5 observed pool sizes (pre-fix RED, historical)
├── slice_parity_evidence.json   # head + random parity pass evidence
├── thread_scaling_baseline.json # real-slice RED scaling baseline (Phase 6 target)
├── contention_evidence.json     # attribution-v1 evidence (Phase 7 input)
└── n_read_differential.json     # D2 divergence evidence
```
