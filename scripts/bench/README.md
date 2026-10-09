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

```bash
# sanity self-check (exact k-mer counts on synthetic input; ~1 min)
python3 scripts/bench/bench.py --mode synthetic --self-check

# parity gate vs jellyfish (dev host only — jellyfish must be installed)
python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only

# compare a fresh run against a committed baseline (the CI gate step)
python3 scripts/bench/bench.py --mode synthetic --out results.json
python3 scripts/bench/compare.py \
  --baseline scripts/bench/baselines/bench_baseline.darwin.json \
  --current results.json --wall-threshold 0.25 --rss-threshold 0.15
```

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
├── bench.py          # measurement core: provision → measure → sanity → reduce
├── compare.py        # gate comparator (exit 0/1/2) — CI invokes this
├── gen_synthetic.py  # seeded deterministic FASTQ generator
├── make_slice.sh     # deterministic gunzip -c | head slice tool
├── baselines/        # committed per-platform baselines (darwin, linux)
└── tests/            # stdlib-unittest suites + dual-platform time fixtures
```
