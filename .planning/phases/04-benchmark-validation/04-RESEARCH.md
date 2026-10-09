# Phase 4: Benchmark & Validation - Research

**Researched:** 2026-10-09
**Domain:** Performance benchmarking harness design (Rust CLI subprocess measurement, cross-platform peak-RSS capture, CI regression gating) + fair-comparison methodology vs Jellyfish2 on human-scale FASTQ
**Confidence:** HIGH

## Summary

Phase 4 is a measurement-and-validation phase, not an optimization phase: it builds a reproducible harness that measures `rustkmer count` and `rustkmer merge` wall-clock + peak RSS, runs a fair head-to-head against Jellyfish2 on human-scale Illumina data, and wires the harness into CI as a regression gate. The good news: every hard external dependency was verified live on the dev host this session — jellyfish 2.3.1 is installed (`/opt/homebrew/bin/jellyfish`), `/usr/bin/time -l` captures peak RSS in bytes on macOS, rustkmer's release binary counts `.fq.gz` natively, and **count parity between the two tools is already proven** on a synthetic 2000-read input (jellyfish `Distinct: 260000` == rustkmer `Unique k-mers: 260000` at k=21 canonical, via both pipe mechanisms).

Three findings reshape the plan. **First, the CRR1936095 dataset is GONE from disk** — the documented path `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/` does not exist; `/Users/forrest/Data/` contains only Docker/labagents/NGS/Pre_train/Ref/Review. The nearest human WGS substitute on disk is `/Users/forrest/Downloads/CRR2044018/` (`CRR2044018_r1.fq.gz` + `r2.fq.gz`, 2.5 GB each, NovaSeq 150 bp — verified: first header `@LH00380:80:223F2MLT4:7:1101:43767:1014`, read length 150). Re-downloading CRR1936095 vs substituting CRR2044018 is a **user decision that blocks plan 04-04** (Open Question 1). **Second, jellyfish2 cannot read `.gz` files as path arguments** — reproduced locally (`std::runtime_error: Unsupported format`, abort, on both `.fasta.gz` and `.fq.gz` at 2.3.1) and corroborated by Biostars/Debian-changelog sources. Fair "decompression counted" methodology must therefore pipe decompressed bytes into jellyfish (`gzcat X | jellyfish count ... /dev/stdin`, process substitution, or the `-g` generator) while rustkmer reads the `.gz` natively — both verified working this session. **Third, the existing perf infrastructure is dead weight**: `src/cli/commands/benchmark.rs` is an unregistered prototype (not in `args.rs`, not dispatched; `memory_usage_mb: None, // TODO: Add memory profiling` at line 312), and `.github/workflows/performance-regression.yml` triggers on branches `main`/`develop` that do not exist (repo uses `dev`) and calls `scripts/check_performance_regression.py`, which does not exist. The harness must be built fresh; nothing existing can be turned on as-is.

Measurement mechanics are settled: macOS `/usr/bin/time -l` reports peak RSS in **bytes**, Linux GNU `/usr/bin/time -v` reports it in **kbytes** — the parser must branch or be 1024× wrong. Best practice gathered from cold-cache and Apple-Silicon benchmarking literature: ≥3 repetitions with tool order interleaved/counterbalanced across rounds (thermal drift is *systematic*, up to 54% skew on sequential sweeps — averaging repeats does not fix it), median as headline with CV% reported, `sudo purge` (macOS) / `sudo sysctl vm.drop_caches=3` (Linux) before every cold run, and a sanity assertion that each run actually counted k-mers (jellyfish exits 0 with an empty database on empty stdin — a silent-false-success trap verified this session).

**Primary recommendation:** Build a Python 3 stdlib-only harness at `scripts/bench/` (runner + baseline comparator + synthetic generator + stdlib-unittest tests), measuring whole-pipeline invocations under `/usr/bin/time -l|-v`, emitting a versioned JSON results file, gated in CI by a new dedicated workflow (ubuntu + macOS matrix, synthetic input, committed baseline JSON, generous wall threshold ~25% + tight RSS threshold ~15%); run the full-dataset Jellyfish2 milestone comparison only on the dev host, after a slice-level count-parity gate passes.

## User Constraints (no CONTEXT.md — locked decisions from PROJECT.md / REQUIREMENTS.md)

No CONTEXT.md exists for this phase (no discuss-phase session). The following are locked at the project level and constrain this phase the same way:

### Locked Decisions (from PROJECT.md Key Decisions + Out of Scope)

- **Reference comparator is Jellyfish2 for v1** — KMC3 comparison is explicitly Out of Scope this milestone (BENCH-V2-01, v2). Research covers Jellyfish2 only.
- **Benchmark dataset: real human-scale Illumina WGS data (CRR1936095, 150 bp PE, ~5.2 GB gzipped r1 across split parts)** is the primary target; the harness must be reproducible, run in CI as a regression gate, and degrade to slices/synthetic inputs where the full dataset is absent. *(Note: the dataset is currently missing from disk — see Open Question 1.)*
- **Preserve `.rkdb` v2 format and public CLI/Python APIs** — the benchmark phase must not change product behavior; it observes it.
- **No new user-facing features** — the harness and report are engineering artifacts, not product surface.
- **Tech stack: work within the established stack** (Rust 1.80+ stable, existing dependency set) rather than introducing new engines. Python 3.10+ is already a first-class project surface.

### Claude's Discretion (research recommends; planner decides)

- Harness implementation language and location (recommendation: Python 3 stdlib at `scripts/bench/`; cargo-native alternative documented below).
- k value(s) for the headline comparison (recommendation: k=31 canonical headline, k=21 secondary).
- CI gate mechanics (recommendation: committed-baseline JSON + threshold check in a new workflow).
- Report format and location.

### Deferred Ideas (OUT OF SCOPE)

- KMC3 as comparator (v2, BENCH-V2-01).
- Query/fuzzy/prefix micro-optimization benchmarks (query path untouched per Out of Scope).
- Minimizer-partitioned counting benchmarks (v2 MINIM-*).

## Phase Requirements

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BENCH-01 | A reproducible benchmark harness measures counting and merge wall-clock time and peak memory, runnable in CI as a regression gate | Measurement loop verified end-to-end this session (`/usr/bin/time -l` around both tools, stderr parse, count sanity); CI gate patterns surveyed (committed-baseline + threshold is the consensus); harness design in Architecture Patterns |
| BENCH-02 | rustkmer matches or beats Jellyfish2 on counting speed on the CRR1936095 human-scale dataset, under fair methodology (cold cache, decompression counted, matched k/canonicalization/input settings) | jellyfish 2.3.1 flags captured verbatim from installed binary; gz-input landmine + three working pipe mechanisms verified; matched-settings matrix + cold-cache protocol + interleaved-reps protocol documented; count parity already proven on synthetic input; **dataset missing from disk — user decision required** |
| BENCH-03 | The benchmark reports peak memory alongside wall-clock, so memory wins (not just speed) are visible and validated | Peak-RSS capture verified on macOS (`-l`, bytes); Linux format documented (`-v`, kbytes); JSON schema puts `peak_rss_bytes` and `wall_s` on equal footing; RSS is more stable than timing → tighter CI threshold |
| BENCH-04 | The harness degrades gracefully to a slice or synthetic input on machines without the full CRR1936095 dataset, so CI can still run | Deterministic slice recipe (`gzcat | head -n`), seeded synthetic generator design, env-var dataset path (`RUSTKMER_BENCH_INPUT`), mode-escalation ladder (full → slice → synthetic) documented |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

`/Users/forrest/GitHub/rustkmer/CLAUDE.md` (auto-generated from feature plans) lists:

- **Active technologies**: Rust 1.80+ stable, clap 4.x, serde, thiserror, anyhow, rayon, bio, memmap2, PyO3 0.27.2, binary `.rkdb` format — benchmark work must not change these.
- **Commands**: `cargo test`, `cargo clippy` are the named verification commands — Rust-side test additions should stay runnable under these; new warnings must not appear (`cargo clippy --all-targets -- -D warnings` is a CI merge gate per FOUND-01).
- **Project structure**: `src/` + `tests/` — a Python harness belongs in `scripts/` (established precedent: `scripts/*.sh`, `scripts/*.py`, `test_data/generate_test_data.py`).
- **Code style**: standard Rust conventions.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wall-clock + peak-RSS measurement of tool invocations | Harness script (subprocess wrapper) | OS `/usr/bin/time` | The measured artifact is a whole process (CLI binary, or decompress-pipe + tool); only a subprocess wrapper with OS rusage accounting sees the true whole-pipeline peak |
| Comparison-vs-Jellyfish2 fairness rules | Harness script (methodology config) | Human-run protocol (dev host) | Fairness is encoded in how the harness constructs matched command lines and interleaves runs, not in either tool |
| CI regression gate | CI workflow (GitHub Actions) | Harness comparator mode | Gate decision (threshold vs baseline) is CI policy; the harness only measures and compares |
| Count-parity verification | Harness verification step | `rustkmer stats -f json` / `jellyfish stats` | Both tools expose machine-readable distinct/total counts; parity is asserted before timing runs are trusted |
| Input provisioning (full/slice/synthetic) | Harness provisioning module | `test_data/` generator precedent | Dataset lives outside the repo; the ladder from full → slice → synthetic is a harness concern |
| Report generation | Harness report mode | Committed JSON + rendered Markdown | The milestone report derives from measured JSON, never hand-edited (report truthfulness threat) |
| rustkmer/merge behavior under measurement | Existing CLI (unchanged) | — | Phase 4 observes; it does not modify `src/` hot paths |

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3 (stdlib only: `subprocess`, `json`, `argparse`, `random`, `unittest`, `statistics`, `hashlib`, `platform`) | 3.10+ (3.12.8 on dev host — verified) | Harness runner, comparator, synthetic generator, tests | Zero new dependencies; subprocess + JSON + deterministic RNG are all stdlib; CI images ship Python 3 by default; the repo already uses Python in `scripts/` and `test_data/` |
| `/usr/bin/time` (macOS BSD time / Linux GNU time) | OS-provided | Wall-clock + peak RSS capture around each measured invocation | OS rusage accounting for arbitrary subprocess trees, including decompress-pipes (verified locally: wrapping `sh -c 'gzcat \| jellyfish'` reports jellyfish's 525 MB peak) |
| jellyfish (comparator binary) | 2.3.1 via Homebrew — verified installed `/opt/homebrew/bin/jellyfish` | The pinned reference comparator | PROJECT.md locks Jellyfish2 for v1; 2.3.1 is current homebrew-core, bottled, source repo github.com/gmarcais/Jellyfish |
| `rustkmer` release binary | `cargo build --release` from this repo | The measured subject | Release profile has `lto = true, codegen-units = 1, panic = "abort"` [VERIFIED: Cargo.toml:116-119] — debug builds are not representative; the gate must build release |

### Supporting

| Tool | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `gzcat` (macOS) / `gunzip -c`, `zcat` (Linux) | OS-provided | Feed decompressed FASTQ into jellyfish (which cannot read `.gz` paths) | Every jellyfish timing run under the "decompression counted" protocol |
| `jellyfish stats` / `jellyfish dump -c` | 2.3.1 | Parity verification (Distinct/Total; per-k-mer two-column dump) | Before trusting any timing comparison; on the actual slice |
| `rustkmer stats -f json` | current | Machine-readable distinct/total from `.rkdb` | Parity gate + sanity assertions |
| `sudo purge` (macOS) / `sudo sysctl vm.drop_caches=3` (Linux) | OS-provided | Cold-cache protocol between runs | Dev-host milestone runs; optional in CI |
| serde / serde_json | 1.0.228 / 1.0.145 (already deps) | JSON handling if any Rust-side test parses results | Only if Rust integration tests consume harness JSON |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python stdlib harness | Cargo-native integration test (`tests/bench_harness.rs`) using `env!("CARGO_BIN_EXE_rustkmer")` + `/usr/bin/time` parse | Keeps everything under `cargo test`/clippy/fmt gates and the repo's Rust discipline; costs: release-binary path is awkward (`cargo test` runs the debug binary unless `--release`), subprocess-orchestration + JSON plumbing is clumsier in Rust, and the abandoned `benchmark.rs` shows the in-Rust path already rotting once. Recommended as the home for *assertions* (parser fixtures, degradation logic) if any are Rust-side — not for the orchestration |
| Python stdlib harness | hyperfine (`--export-json`, `--prepare` cache-drop hook) | Excellent CLI measurement tool, but: not installed on dev host or CI (new external dep), does not capture peak RSS, and cannot express the parity gate or mode ladder. Not suitable as the spine; could be an optional dev-host convenience later |
| `/usr/bin/time` parsing | Rust-internal `getrusage(RUSAGE_CHILDREN)` via `libc` | Avoids output parsing but hits the same units trap (bytes on Darwin, KB on Linux) and adds a `libc` dependency just to avoid parsing two stable output formats. Parsing time output keeps the harness dependency-free |
| Committed-baseline CI gate | Same-job base-ref build + compare (mdt pattern) | More rigorous (same runner, same conditions) but doubles build time per PR. Recommended as a v2 upgrade if the committed-baseline gate proves flaky |

**Installation:**
```bash
# No new packages. Phase installs nothing.
# Dev-host prerequisites (all verified present this session):
cargo build --release                 # measured subject
jellyfish --version                   # 2.3.1 (brew install jellyfish if absent)
python3 --version                     # 3.12.8
/usr/bin/time -l true                 # prints "... maximum resident set size"
```

**Version verification (performed this session):** jellyfish `2.3.1` [VERIFIED: local `jellyfish --version`]; python3 `3.12.8` [VERIFIED: local]; `/usr/bin/time -l` functional [VERIFIED: local run prints `maximum resident set size`]; hyperfine absent; gtime absent; kmc absent (expected — v2).

## Package Legitimacy Audit

> This phase installs **no external packages** — the harness is Python 3 stdlib only, the comparator is an already-installed system binary, and no new crates are added. There is nothing to audit; the gate is vacuously satisfied. (If the planner adds any crate or pip package anyway, re-run `gsd-tools query package-legitimacy check` before install.)

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| *(none — stdlib only)* | — | — | — | — | — | Approved (N/A) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                       ┌────────────────────────────────────────────────────────┐
                       │                  bench harness (python3)                │
                       │  scripts/bench/bench.py                                 │
                       │  ┌──────────┐  ┌────────────┐  ┌────────────────────┐   │
                       │  │ config:  │  │ provision: │  │ measure loop:      │   │
  env vars             │  │ k, reps, │→ │ full/slice │→ │ for round in N:    │   │
  RUSTKMER_BENCH_INPUT─┼─▶│ threads, │  │ /synthetic │  │  purge (cold opt)  │   │
  RUSTKMER_BENCH_MODE  │  │ cold,    │  │ ladder     │  │  run A, run B      │   │
  RUSTKMER_BENCH_JF    │  │ protocol │  │ (BENCH-04) │  │  (interleaved)     │   │
                       │  └──────────┘  └────────────┘  └─────────┬──────────┘   │
                       │                                        │              │
                       │  ┌───────────────┐  ┌───────────────┐  │              │
                       │  │ verify:       │  │ reduce:       │  │              │
                       │  │ parity gate   │←─│ median/CV,    │←─┘              │
                       │  │ (jf Distinct  │  │ peak RSS,     │                 │
                       │  │ == rk Unique) │  │ sanity>0      │                 │
                       │  └───────────────┘  └──────┬────────┘                 │
                       │                            │                          │
                       │  ┌──────────────────┐  ┌───▼──────────┐               │
                       │  │ compare mode:    │  │ report mode: │               │
                       │  │ vs baseline.json │  │ results.json │               │
                       │  │ exit 1 on breach │  │ + Markdown   │               │
                       │  └──────────────────┘  └──────────────┘               │
                       └──────┬──────────────────────┬─────────────────────────┘
                              │ subprocess           │ subprocess
              ┌───────────────▼───────┐   ┌──────────▼───────────┐
              │ measured run A:       │   │ measured run B:      │
              │ /usr/bin/time -l/-v   │   │ /usr/bin/time -l/-v  │
              │   rustkmer count ...  │   │   sh -c 'gzcat F.fq.gz │ jellyfish
              │   -i part.fq.gz (gz   │   │        count ... /dev/stdin'
              │   native)             │   │  (gz piped: jf can't read .gz)     │
              └───────────────────────┘   └──────────────────────┘
                        │                            │
                        ▼                            ▼
              .rkdb (20 B/k-mer)            .jf (+ jellyfish stats)
                        │                            │
                        └──────────┬─────────────────┘
                                   ▼
                       parity gate (BENCH-02 fairness)
                       rustkmer stats -f json  ↔  jellyfish stats

  CI (regression gate, BENCH-01/04):  synthetic input only, rustkmer-only arms,
  committed baseline JSON, threshold check → pass/fail the workflow
  Dev host (milestone, BENCH-02/03):  full dataset, both tools, interleaved
  rounds, cold-cache protocol → committed results.json + report
```

A reader can trace the milestone use case: env-configured harness provisions input (full → slice → synthetic), runs interleaved measured rounds of both tools under `/usr/bin/time`, verifies count parity, reduces to medians, and emits results; the same harness in compare mode consumes a committed baseline for the CI gate.

### Recommended Project Structure

```
scripts/
├── bench/
│   ├── bench.py              # orchestration: provision → measure → verify → reduce → report
│   ├── compare.py            # baseline comparator (exit 1 on threshold breach) — CI gate step
│   ├── gen_synthetic.py      # seeded synthetic FASTQ generator (BENCH-04)
│   ├── make_slice.sh         # deterministic slice: gzcat | head -n 4*N_READS > slice.fq
│   ├── baselines/
│   │   └── bench_baseline.json   # committed CI baseline (schema-versioned)
│   └── tests/
│       ├── test_time_parser.py   # parses BOTH fixture formats (macOS -l bytes, Linux -v KB)
│       ├── test_degradation.py   # mode ladder: missing path → slice → synthetic
│       └── fixtures/
│           ├── time_l_macos.txt  # captured real output
│           └── time_v_linux.txt  # captured real output
.github/workflows/
└── benchmark.yml             # new: ubuntu + macOS, release build, synthetic gate
docs/ (or .planning/phases/04-*/)
└── benchmark-report.md       # milestone report artifact (from results.json)
```

### Pattern 1: Whole-pipeline measurement under `/usr/bin/time` (BENCH-01/02/03)

**What:** Every timed number comes from one measurement primitive: `/usr/bin/time -l` (macOS) or `/usr/bin/time -v` (Linux) wrapped around the *entire* command the user would really run — including the decompression pipe for jellyfish.

**When to use:** Every wall-clock and peak-RSS datapoint. Harness-internal clocks are only for sanity/reporting, never headline numbers.

**Why:** Both wall-clock and peak RSS come from the same OS accounting (rusage); wrapping the shell pipeline attributes the decompressor's and the tool's peaks to one measured invocation — verified locally: `/usr/bin/time -l sh -c 'zcat|jellyfish -s 100M ...'` reported jellyfish's 525,582,336-byte peak, not the shell's.

```bash
# macOS (bytes):
/usr/bin/time -l /path/rustkmer count -k 31 -C --threads 16 -o out.rkdb in.fq.gz
# stderr line to parse: "60391424  maximum resident set size"
#   [VERIFIED: local run this session — 60391424 bytes for a 260k-k-mer count]

# Linux (kbytes):
/usr/bin/time -v /path/rustkmer count -k 31 -C --threads 16 -o out.rkdb in.fq.gz
# stderr line to parse: "Maximum resident set size (kbytes): 62384"

# jellyfish arm (macOS, "decompression counted" protocol):
/usr/bin/time -l sh -c 'gzcat in.fq.gz | jellyfish count -m 31 -s 10G -t 16 -C -o out.jf /dev/stdin'
```

### Pattern 2: Fair-comparison methodology matrix (BENCH-02)

**What:** One config object pins every knob for both tools; the harness derives both command lines from it so they cannot drift.

| Dimension | rustkmer | jellyfish 2.3.1 | Notes |
|-----------|----------|-----------------|-------|
| k | `-k 31` | `-m 31` | matched [VERIFIED: rustkmer `-k` in args.rs:21-22; jellyfish `-m, --mer-len=uint32 *Length of mer` from `count --help`] |
| canonical | `-C` | `-C` | **Both opt-in, same letter** [VERIFIED: args.rs:49-50 `#[arg(short = 'C', long)] canonical: bool`; jellyfish help: `-C, --canonical  Count both strand, canonical representation (false)`] |
| threads | `--threads 16` | `-t 16` | same explicit count on both |
| input | `-i part001.fq.gz part006.fq.gz` (multi-file) | `gzcat p1 p6 \| ... /dev/stdin` (concatenated) | rustkmer takes `num_args = 1..` [VERIFIED: args.rs:25-26]; same byte stream for both |
| decompression | native (inline flate2, single-threaded per D-02) | `gzcat` child in the measured pipeline | decompression inside the measured wall-clock for BOTH; residual asymmetry noted honestly in report |
| count bounds | `-L/-U` | `-L/-U` | both support lower/upper; keep unset for headline [VERIFIED: args.rs:93-104 `min_count`/`max_count` with `alias = "lower-count"`/`"upper-count"`; jellyfish `-L, --lower-count=uint64`, `-U, --upper-count=uint64`] |
| hash sizing | n/a (DashMap auto-grows) | `-s 10G` initial hash | jellyfish `-s` documented as *Initial hash size* with auto-doubling; size generously and record the value in the report — undersizing silently slows jellyfish (fairness knob) |
| output | `.rkdb` | `.jf` | both write their native format |

**Protocol (per round):** warmup run (discarded) → `sudo purge` (if available; record whether it ran) → run A → `purge` → run B; **interleave/counterbalance** (A,B then B,A across rounds); ≥3 rounds; headline = median, report all raw reps + CV%. Rationale: thermal drift on Apple Silicon is *systematic* — sequential A-then-B sweeps bias the later tool by up to 54% on fanless machines and averaging repeats of a biased order does not fix it [CITED: y42u.net case study; asiai best practices; USENIX Sec23]. Dev host is an actively-cooled M4 Max (16 cores, 128 GB RAM — verified) where 2-5% variance is the normal band.

### Pattern 3: Parity gate before timing (BENCH-02 correctness leg)

**What:** Before any timing comparison is trusted, assert the two tools counted the *same thing* on the actual input slice.

```bash
jellyfish stats out.jf          # Distinct / Total / Max_count  [VERIFIED: 2.3.1 --help + local run]
rustkmer stats -f json out.rkdb # {"Total k-mers": N, "Unique k-mers": M, ...}
# assert jellyfish Distinct == rustkmer Unique k-mers, and Total == Total
```

Verified working end-state on synthetic data this session: jellyfish `Distinct: 260000` / `Total: 260000` == rustkmer `Unique k-mers: 260000` / `Total k-mers: 260000` (k=21, canonical). For per-k-mer spot checks: `jellyfish dump -c out.jf` (two-column k-mer/count) vs `rustkmer dump`/`query`. **Real-data caveat (N handling, lowercase bases)**: parity proven on uppercase ACGT synthetic input; the real slice contains Ns — the gate must run on the real slice *before* the full milestone run, and any mismatch becomes a methodology finding, not a silent pass.

### Pattern 4: Graceful-degradation ladder (BENCH-04)

**What:** One env-configured input resolver that escalates deterministically:

```
RUSTKMER_BENCH_INPUT=/path/to/dir (or file list)
  └─ exists and total gz size > threshold?  → mode=full (dev host only)
  └─ exists but small / slice requested?    → mode=slice:
        gzcat part.fq.gz | head -n $((4 * N_READS)) > slice.fq   # deterministic
  └─ missing?                               → mode=synthetic:
        python3 scripts/bench/gen_synthetic.py --reads N --length 150 --seed 42
```

**Rules:** the chosen mode, the seed, and the input fingerprint (size + sha256 of a full slice, or full hash when time permits) are written into results.json; CI *always* runs mode=synthetic (never claims BENCH-02); the milestone criterion is only ever claimed from a mode=full run on the dev host. Synthetic generator follows the `test_data/generate_test_data.py` precedent but targets FASTQ with fixed `random.seed(...)` and a `--reads` count sized so the measured op runs ≥5 s (timer-display granularity pitfall).

### Pattern 5: CI regression gate (BENCH-01)

**What:** New workflow `.github/workflows/benchmark.yml` — `pull_request`/`push` to `dev` (matching ci.yml's branch set; **not** the dead `main`/`develop` set), ubuntu + macOS matrix, steps: checkout → rust toolchain → `cargo build --release` → `python3 scripts/bench/bench.py --mode synthetic --out results.json` → `python3 scripts/bench/compare.py --baseline scripts/bench/baselines/bench_baseline.json --current results.json --wall-threshold 0.25 --rss-threshold 0.15`. Comparator exits 1 on breach. Baseline is regenerated by a documented maintainer command after intentional perf changes.

**Why these thresholds:** shared GitHub runners show 2-3× run-to-run wall variance (projects either use 15-25% thresholds or give up on timing gates); peak RSS is far more stable, so memory regressions get the tighter leash — which also serves BENCH-03 (memory regressions are caught *earlier* than speed ones).

### Anti-Patterns to Avoid

- **Do NOT revive `src/cli/commands/benchmark.rs`.** It is unregistered dead code (absent from `args.rs` Commands enum and `main.rs` dispatch — verified), shells out to `cargo` instead of the built binary, and its memory field is `memory_usage_mb: None, // TODO: Add memory profiling` [VERIFIED: benchmark.rs:312]. Mine its JSON schema ideas at most.
- **Do NOT trust `zcat` on macOS.** macOS `zcat` is the compress(1) `.Z` variant: it fails on `.gz` with `can't stat: file (file.Z)` — and because it sits in a pipe, **the downstream tool still exits 0 with a valid empty database**. Verified this session (three zero-count "successful" runs before the cause was isolated). Use `gzcat`/`gunzip -c` on macOS; assert `distinct > 0` after every run.
- **Do NOT let jellyfish read `.gz` paths** — it aborts (`Unsupported format`), verified locally and corroborated by Biostars/Debian-changelog.
- **Do NOT time with the debug binary.** `cargo test` builds debug; the gate workflow must `cargo build --release` and measure `target/release/rustkmer`.
- **Do NOT run both tools concurrently** to save wall time — they contend for the unified memory pool and cores; sequential interleaved rounds only.
- **Do NOT hand-edit the milestone report numbers** — render from results.json (report-truthfulness threat).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|------|
| Process time + peak-RSS accounting | Custom sampler polling `ps`/`/proc` in a loop | `/usr/bin/time -l` / `-v` around the invocation | rusage high-water mark is exact and free; polling misses the peak between samples and adds observer load |
| Statistical reduction of noisy timings | Ad-hoc "best of N" or single-run numbers | ≥3 interleaved reps, median + CV (`statistics.median`/`stdev`) | Single runs on shared runners / thermally drifting SoCs are 2-54% off; median-of-interleaved-rounds is the documented defense |
| FASTQ decompression for jellyfish | Anything other than `gzcat`/`gunzip -c` in the measured pipeline | OS gzip tools | zlib performance is not the thing under test; keep it identical across arms |
| Synthetic FASTQ generation | Complex genome simulator | ~20-line seeded `random.choice('ACGT')` writer (stdlib) | The benchmark needs reproducible volume, not biological realism; complexity only adds drift risk |
| JSON schema for results | Per-run ad-hoc formats | One versioned schema (`schema_version`, `mode`, `input_fingerprint`, per-arm reps with `wall_s` + `peak_rss_bytes`, medians) | The comparator, CI, and the report all consume it; version it once |
| CI threshold logic | Inline workflow YAML arithmetic | Small `compare.py` (stdlib) | Testable with unit tests; YAML-embedded logic rots invisibly |

**Key insight:** everything measurement-critical is either OS-provided (`time`, `gzcat`, `purge`) or stdlib — the phase's actual engineering is protocol correctness (matching, interleaving, verifying) and honest reporting, not measurement infrastructure.

## Common Pitfalls

### Pitfall 1: macOS `zcat` silently produces empty input
**What goes wrong:** `zcat file.fq.gz | jellyfish ...` — macOS zcat expects `.Z`, fails with `can't stat`, the pipe delivers EOF, and jellyfish **exits 0 with a valid, empty database**. A timing run "succeeds" while measuring nothing.
**Why it happens:** macOS ships compress(1)-family `zcat`; Linux ships gzip's. Same name, different format.
**How to avoid:** `gzcat` / `gunzip -c` on macOS; post-run sanity assertion `distinct_kmers > 0` for every arm (this session lost three runs to exactly this before isolation — treat the assertion as non-negotiable).
**Warning signs:** 0.0x-second "human-scale" runs; `Distinct: 0` in jellyfish stats.

### Pitfall 2: Peak-RSS units differ 1024× across platforms
**What goes wrong:** One parser for both platforms reports macOS memory 1024× too high or Linux 1024× too low.
**Why:** macOS `/usr/bin/time -l` prints bytes (`1261568  maximum resident set size` — verified locally); Linux GNU `/usr/bin/time -v` prints kbytes (`Maximum resident set size (kbytes): N`). Same underlying rusage field, different units — Darwin getrusage is bytes, Linux is KB.
**How to avoid:** Parser branches on output format (distinct line shapes), normalizes to bytes; unit tests parse both fixture files.
**Warning signs:** two platforms disagreeing by exactly 3 orders of magnitude.

### Pitfall 3: jellyfish cannot read `.gz` paths (aborts)
**What goes wrong:** `jellyfish count ... file.fq.gz` → `libc++abi: terminating due to uncaught exception of type std::runtime_error: Unsupported format`, exit 134.
**Why:** jellyfish2 reads uncompressed FASTA/FASTQ from paths; compression support is via pipes/generators.
**How to avoid:** Always pipe (`gzcat X | jellyfish count ... /dev/stdin`), process substitution (`<(gzcat X)`), or `-g` generator file — all three verified working this session on 2.3.1.
**Warning signs:** exit code 134 in harness logs.

### Pitfall 4: jellyfish `-s` undersizing silently penalizes the comparator
**What goes wrong:** Default/small `-s` forces repeated hash doubling — jellyfish looks slower than it is, and the "win" is an artifact.
**Why:** `-s` is the *initial* hash size; jellyfish doubles with reprobes when full.
**How to avoid:** Size for the expected distinct count (human-scale: `-s 10G` ballpark) and record the value in results.json; report methodology includes it.
**Warning signs:** run time dominated by growth phases; memory climbing stepwise in pilot runs.

### Pitfall 5: Thermal/order bias on Apple Silicon masquerades as a result
**What goes wrong:** Running all rustkmer reps then all jellyfish reps gives rustkmer the cool chip every time — up to 54% skew documented on sequential sweeps; averaging repeats of the same biased order does not help.
**Why:** Systematic DVFS/thermal drift, not random noise; M4 Max is actively cooled but not immune.
**How to avoid:** Interleave/counterbalance order across rounds (A,B / B,A), cooldown gap between runs, median + CV; CV > ~5% means the measurement is dirty — rerun.
**Warning signs:** monotonic slowdown across reps of the same tool.

### Pitfall 6: CI timing gates false-positive on shared runners
**What goes wrong:** Tight threshold (5%) on wall-clock fails spuriously; developers start ignoring/skipping the gate.
**Why:** Documented 2-3× run-to-run variance on GitHub shared runners; multiple major Rust projects dropped timing gates for this reason.
**How to avoid:** 25% wall threshold + 15% RSS threshold on synthetic input; keep the gate rustkmer-only (no jellyfish install in CI); if still flaky, demote wall to warn-only and keep RSS hard (RSS is stable).
**Warning signs:** gate red on zero-change PRs.

### Pitfall 7: `/usr/bin/time` display granularity on short runs
**What goes wrong:** macOS `time -l` prints centisecond-resolution real time (`0.05 real`) — sub-second micro-runs carry huge relative error.
**How to avoid:** Size slice/synthetic inputs so every measured op runs ≥5 s (the smoke test: 2000 reads = 0.05 s → scale to ≥200k reads for 5 s-class runs, calibrate empirically).
**Warning signs:** two-decimal wall times in results.

### Pitfall 8: Disk exhaustion from human-scale outputs
**What goes wrong:** `.rkdb` is 20 B/k-mer: a full-human count (~2.6-2.9 B distinct 31-mers from r1 parts) is ~55-60 GB *per database*; merge benchmarks need two input DBs + output + streaming temp (32 B/k-mer) — peak scratch can exceed 200 GB.
**Why:** Format density, plus jellyfish's own `.jf` outputs alongside.
**How to avoid:** Harness checks `df` before each mode=full run and aborts with a clear message below a configured floor; iterate the harness itself on slices; delete inter-run artifacts (keep final ones for the report).
**Warning signs:** `No space left on device` mid-milestone-run. (1.5 TB free on dev host — verified — so this is a guardrail, not a blocker.)

### Pitfall 9: Cold-cache claim without evidence
**What goes wrong:** Report says "cold cache" but `purge` wasn't run (needs sudo) or failed silently.
**How to avoid:** Harness records `cache_state: "purged" | "unavailable" | "runner-fresh"` per run in results.json; only "purged"/"runner-fresh" runs count toward the cold-cache criterion.
**Warning signs:** sudo prompt failures in logs; identical first/second rep times.

### Pitfall 10: Real-data parity assumed from synthetic parity
**What goes wrong:** N-containing / lowercase / adapter-content reads break the Distinct == Unique equality on real data after the harness was validated on clean synthetic input.
**How to avoid:** Parity gate runs on the actual slice before the full run (Pattern 3); a mismatch halts the milestone run and surfaces as a methodology finding.
**Warning signs:** distinct counts differing by a small fraction (Ns) rather than wildly.

### Pitfall 11: Dead perf workflow breeds false confidence
**What goes wrong:** `performance-regression.yml` exists, so the project "has" a perf gate — but it triggers on `main`/`develop` (neither exists; repo uses `dev`) and every real step no-ops with a warning because `scripts/check_performance_regression.py` doesn't exist.
**How to avoid:** The new benchmark.yml is the real gate; delete or fix the old workflow in this phase (one-line decision for the planner), don't leave two gates where one is dead.

## Code Examples

### Measured invocation + dual-format time parser (harness core)

```python
# Source: pattern verified by direct local execution this session (macOS arm64)
import re, subprocess, sys

MAC_RSS = re.compile(r"^\s*(\d+)\s+maximum resident set size\s*$")   # bytes
LIN_RSS = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")  # kbytes

def measure(argv: list[str]) -> dict:
    """Run argv under /usr/bin/time; return {'wall_s': float, 'peak_rss_bytes': int}."""
    time_flag = "-l" if sys.platform == "darwin" else "-v"
    proc = subprocess.run(["/usr/bin/time", time_flag, *argv],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{argv[0]} failed rc={proc.returncode}: {proc.stderr[-500:]}")
    peak = None
    for line in proc.stderr.splitlines():
        if m := MAC_RSS.match(line):
            peak = int(m.group(1))                      # already bytes on macOS
        elif m := LIN_RSS.match(line):
            peak = int(m.group(1)) * 1024               # kbytes -> bytes
    # NOTE: real-time line parsing omitted for brevity; sanity assertions mandatory:
    assert peak is not None, "no RSS line parsed — format drift?"
    return {"peak_rss_bytes": peak}
```

### Matched command construction (BENCH-02 fairness encoded, not hand-copied)

```python
# Derived from flags verified this session:
#   rustkmer:  args.rs:21-50,84-104  |  jellyfish: 2.3.1 `count --help`
def rustkmer_cmd(k, threads, inputs, out):
    return ["target/release/rustkmer", "count", "-k", str(k), "-C",
            "--threads", str(threads), "-o", out, *inputs]

def jellyfish_cmd(k, threads, gz_inputs, out, hash_size="10G", decompressor="gzcat"):
    inner = (f"{decompressor} {' '.join(gz_inputs)} | "
             f"jellyfish count -m {k} -s {hash_size} -t {threads} -C -o {out} /dev/stdin")
    return ["sh", "-c", inner]   # measured as one pipeline; RSS attributes to children
```

### Parity gate (BENCH-02 correctness leg)

```bash
# Verified end-to-end this session (k=21, synthetic 2000x150bp):
jellyfish stats out.jf | awk '/^Distinct:/{d=$2} /^Total:/{t=$2} END{print d, t}'
# -> "260000 260000"
rustkmer stats -f json out.rkdb      # machine-readable; assert Unique k-mers == 260000
```

### CI gate step (benchmark.yml core)

```yaml
# Source: consensus pattern from surveyed Rust-project gates (endless/Resilient/mdt)
- run: cargo build --release
- run: python3 scripts/bench/bench.py --mode synthetic --out results.json
- run: python3 scripts/bench/compare.py
        --baseline scripts/bench/baselines/bench_baseline.json
        --current results.json
        --wall-threshold 0.25 --rss-threshold 0.15
```

### Deterministic slice (BENCH-04)

```bash
# gz stream -> first N reads (4 lines each); identical bytes on every machine
gzcat CRR*_r1.fq.gz.part001 | head -n 4000000 > slice_1m_reads.fq   # 1,000,000 reads
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| In-repo `benchmark.rs` CLI subcommand (cargo-subprocess prototype) | External stdlib harness measuring release binaries under OS rusage | This repo's prototype predates Phase 1 (Jan 2026) and was never registered | Harness lives outside `src/`, cannot rot silently, measures the real binary |
| criterion as CI gate | Committed-baseline + generous-threshold gates; deterministic instruction counting (CodSpeed/iai-callgrind) for the strict case | 2023-2025 (ripgrep/starship/fd/bat opting out of timing gates) | Subprocess-level CLI benchmarks (our case) belong to the baseline+threshold family; criterion stays for in-process microbenches only |
| Single-run benchmark claims | Interleaved multi-round, median + CV, counterbalanced order | Established practice (SPEC-style; re-popularized by Apple Silicon thermal studies 2023+) | BENCH-02's "fair methodology" explicitly means this |
| `performance-regression.yml` aspirational workflow | Dedicated benchmark.yml with real scripts, correct branches, no-op-free steps | This phase | The gate becomes real and enforced |

**Deprecated/outdated:**
- macOS `zcat` for gzip (use `gzcat`/`gunzip -c`) — behavior confirmed this session.
- GNU time 1.7 maxrss (4× pages bug) — irrelevant on modern runners (fixed in 1.7-24), but a footnote if anyone pins ancient images.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | k=31 canonical is the headline comparison (PROJECT.md does not pin k) | Patterns 2/3 | User may prefer k=21 or both; plan should parameterize and confirm — LOW risk (harness is k-agnostic) |
| A2 | CRR2044018 (on disk, verified) is an acceptable stand-in for the missing CRR1936095, OR the user re-downloads CRR1936095 | Environment / Open Q1 | **HIGH** — BENCH-02 names CRR1936095 explicitly; substituting without user sign-off undermines the milestone claim; re-download path (source, auth, ~5.2 GB) unverified |
| A3 | Linux `/usr/bin/time -v` output format as documented (Debian GNU time 1.9; ubuntu-latest ships GNU time) | Pitfall 2 / Pattern 1 | Parser fixture covers it; if a CI image lacks GNU time the gate fails loudly (fixture-based unit test catches drift before CI) |
| A4 | GitHub-hosted runners have passwordless sudo and fresh (cold) caches per job | Pattern 5 | If sudo is unavailable, drop_caches/purge steps degrade to `cache_state: "runner-fresh"` — gate unaffected (synthetic input is small) |
| A5 | jellyfish default `-c 7`-bit counters suffice for this dataset's depth (r1-half of ~30x PE → typical max counts well under 127; satellite-repeat outliers handled by jellyfish's overflow storage) | Pattern 2 | If wrong, parity gate catches a count discrepancy on the slice before any headline number is produced |
| A6 | rustkmer `Unique k-mers` (stats) ≡ jellyfish `Distinct` (stats) semantically on real data | Pattern 3 | The parity gate exists precisely to falsify this on the real slice before the milestone run |
| A7 | `sudo purge` will be permitted/runnable on the dev host when the user executes the milestone run | Pattern 2 / Pitfall 9 | Cold-cache criterion records `cache_state` honestly; if purge never runs, BENCH-02's "cold cache" wording is only partially satisfied — surface to user |
| A8 | The parity-check pipe (`/dev/stdin`) and generator mechanisms behave identically at full-dataset scale as at smoke scale | Patterns 1/3 | First full run should begin with a slice-scale pilot anyway; abort-on-discrepancy protects the milestone |

## Open Questions

1. **The CRR1936095 dataset is missing — what is the milestone input?**
   - What we know: documented path absent; verified missing via directory listing + bounded `find` + `mdfind`. Nearest substitute `CRR2044018` (2.5 GB r1 + 2.5 GB r2, NovaSeq 150 bp) verified present in `~/Downloads`. Disk has 1.5 TB free, so a re-download fits.
   - What's unclear: whether the user can/will re-fetch CRR1936095 (source + auth for GSA data unverified), and whether BENCH-02's explicit "CRR1936095" wording may be amended to CRR2044018.
   - Recommendation: ask the user before planning 04-04. Options: (a) re-download CRR1936095 (keeps requirement text literal), (b) substitute CRR2044018 r1 (update requirement wording), (c) benchmark on CRR2044018 now and re-run the report on CRR1936095 when re-fetched. The harness is path-agnostic either way — only the report's input fingerprint changes.
2. **Headline k value** — recommend k=31 canonical (exercises the Phase-3 dense u64 path, standard for human genomics) + k=21 as a secondary datapoint; confirm in planning (A1).
3. **What to do with `performance-regression.yml`** — recommend deletion (superseded by benchmark.yml); alternative is fixing its branches/scripts. Planner decision, one task.
4. **Gate strictness** — committed-baseline with 25%/15% thresholds recommended; if the user wants stricter, the same-job base-ref build comparison (mdt pattern) is the rigorous upgrade at ~2× CI build cost.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| jellyfish (comparator) | BENCH-02 | ✓ (dev host) | 2.3.1 `/opt/homebrew/bin/jellyfish` | build v2.3.1 from GitHub source tarball (releases ship source only) |
| CRR1936095 dataset (~5.2 GB gz) | BENCH-02 milestone run | **✗ MISSING** (documented path absent) | — | CRR2044018 r1 (verified on disk) or re-download — **user decision (Open Q1)** |
| CRR2044018 r1+r2 (2.5+2.5 GB gz) | Substitute candidate | ✓ (dev host, `~/Downloads/CRR2044018`) | NovaSeq 150 bp, verified | — |
| `/usr/bin/time -l` (peak RSS, macOS) | BENCH-01/02/03 | ✓ (verified: prints `maximum resident set size` in bytes) | macOS BSD time | none needed |
| `/usr/bin/time -v` (peak RSS, Linux CI) | CI gate | not run locally (macOS host); format documented from GNU time 1.9 docs | GNU time | parser fixture + unit test guard |
| `gzcat` / `gunzip -c` | jellyfish arms | ✓ (verified) | macOS | `gunzip -c` (portable) |
| python3 | harness | ✓ | 3.12.8 (miniconda) | any 3.10+ (stdlib-only harness) |
| `sudo purge` (cold cache, macOS) | BENCH-02 protocol | untested (needs interactive sudo) | — | record `cache_state: "unavailable"`; criterion claims rest on recorded state |
| Rust toolchain + release build | measured subject | ✓ | stable, target/release/rustkmer builds and runs (verified) | — |
| hyperfine | (optional convenience) | ✗ not installed | — | not used by the design |
| kmc | v2 comparator | ✗ not installed | — | out of scope (locked) |
| Disk space (dev host) | full-mode artifacts (~200+ GB peak) | ✓ 1.5 TB free | — | harness `df` guardrail |
| RAM / cores (dev host) | full-mode runs | ✓ 128 GB / 16 cores (M4 Max) | — | — |
| GitHub Actions ubuntu+macOS runners | CI gate | ✓ (existing ci.yml matrix proves both) | — | — |

**Missing dependencies with no fallback:**
- None that block harness construction (04-01..04-03 proceed on synthetic/slice data regardless).

**Missing dependencies with fallback:**
- CRR1936095 (fallback: CRR2044018 substitute or re-download — user decision, blocks only 04-04's headline run).
- `sudo purge` on demand (fallback: honest `cache_state` recording).

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required. `security_enforcement: true` at ASVS L1 — Security Domain section included below.

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Rust) | `cargo test` (built-in; proptest 1.5, criterion 0.5 as dev-deps) [VERIFIED: Cargo.toml:99-113; TESTING.md] |
| Framework (harness) | Python 3 stdlib `unittest` (zero-install: `python3 -m unittest discover scripts/bench/tests`) — deliberately NOT pytest, to dodge the repo's known pyo3 pytest/addopts breakage recorded in STATE.md blockers |
| Config file | none needed for stdlib unittest (Rust: default cargo config; existing suites unaffected) |
| Quick run command | `python3 -m unittest discover -s scripts/bench/tests && cargo test` |
| Full suite command | `cargo test && cargo clippy --all-targets -- -D warnings && python3 -m unittest discover -s scripts/bench/tests` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BENCH-01 | Harness measures count+merge wall-clock and peak RSS on a real invocation | integration (smoke: synthetic ≥100k reads through release binary; assert `wall_s > 0`, `peak_rss_bytes > 0`, distinct == generator's expectation) | `python3 scripts/bench/bench.py --mode synthetic --self-check` (wired into CI gate step) | ❌ Wave 0 |
| BENCH-01 | Time-output parser handles BOTH platform formats, rejects garbage | unit (fixture-driven: macOS `-l` bytes sample, Linux `-v` kbytes sample, malformed input) | `python3 -m unittest scripts.bench.tests.test_time_parser` | ❌ Wave 0 |
| BENCH-01 | Comparator flags regression beyond threshold, passes within | unit (baseline/current JSON pairs around the boundary; RSS + wall axes) | `python3 -m unittest scripts.bench.tests.test_compare` | ❌ Wave 0 |
| BENCH-02 | Matched-settings command construction (k/canonical/threads mirrored; gz piped for jf only) | unit (golden argv pairs for both tools from one config) | `python3 -m unittest scripts.bench.tests.test_cmd_matrix` | ❌ Wave 0 |
| BENCH-02 | Count parity on real slice before timing (jf Distinct == rk Unique; Total == Total) | integration, dev-host (slice-scale; jellyfish present) | `python3 scripts/bench/bench.py --mode slice --parity-only` | ❌ Wave 0 (manual-only in CI: CI has no jellyfish — justification: gate is rustkmer-vs-baseline by design) |
| BENCH-02 | Milestone verdict on full dataset | manual-only (dev host; ~1-2 h wall including reps; produces committed results.json + report) | `python3 scripts/bench/bench.py --mode full --out results.json` then report render | ❌ by design (documented as milestone evidence artifact) |
| BENCH-03 | results.json carries `peak_rss_bytes` alongside `wall_s` for every arm and median | unit (schema validation incl. schema_version, per-rep list) | `python3 -m unittest scripts.bench.tests.test_schema` | ❌ Wave 0 |
| BENCH-04 | Mode ladder: missing path → synthetic; present path → slice; explicit override honored | unit (resolver table over existing/missing tmp paths) | `python3 -m unittest scripts.bench.tests.test_degradation` | ❌ Wave 0 |
| BENCH-04 | Synthetic generator deterministic given seed | unit (same seed → identical bytes; distinct read count) | `python3 -m unittest scripts.bench.tests.test_generator` | ❌ Wave 0 |
| BENCH-01/04 | CI gate workflow green on synthetic input | e2e (workflow run on PR to dev) | push a PR; `benchmark.yml` must pass | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m unittest discover -s scripts/bench/tests && cargo test` (seconds; parser/generator/schema/degradation units + existing Rust suites)
- **Per wave merge:** full suite command above + one local `bench.py --mode synthetic --self-check` run
- **Phase gate:** full suite green; CI `benchmark.yml` green on a PR; slice-scale parity gate green on dev host; milestone results.json + rendered report committed (mode=full)

### Wave 0 Gaps

- [ ] `scripts/bench/tests/test_time_parser.py` (+ `fixtures/time_l_macos.txt`, `fixtures/time_v_linux.txt`) — covers BENCH-01
- [ ] `scripts/bench/tests/test_degradation.py` — covers BENCH-04
- [ ] `scripts/bench/tests/test_compare.py`, `test_schema.py`, `test_cmd_matrix.py`, `test_generator.py` — covers BENCH-01/02/03/04
- [ ] `scripts/bench/baselines/bench_baseline.json` — committed after first green synthetic run (documented regen command)
- [ ] `.github/workflows/benchmark.yml` — CI gate job
- [ ] Rust test suites: no new gaps — existing `cargo test` infrastructure covers any Rust-side additions; framework install not needed

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: "high"` — L1 grep-depth threat surface for a benchmark phase is **measurement integrity**, not classic webapp ASVS. Categories below assessed accordingly.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface (local tooling + CI) |
| V3 Session Management | no | None |
| V4 Access Control | partial (CI) | Gate workflow uses `pull_request` (NOT `pull_request_target`) with `contents: read` — same least-privilege pattern as ci.yml's documented T-01-SC control; fork PR code never touches base secrets |
| V5 Input Validation | yes | Harness validates env-var paths (exists, is file/dir, size sanity) before use; comparator validates results/baseline JSON against the versioned schema before trusting numbers; malformed input → hard error, never best-effort parse |
| V6 Cryptography | no | sha256 input fingerprinting uses stdlib `hashlib` (integrity labeling, not security crypto) |
| V8 Data Protection | partial | Dataset paths/fingerprints in committed results.json — verify no user-identifying paths beyond the dev host's absolute paths (acceptable: repo is private-tooling, but planner should keep results.json paths relative-or-scoped) |

### Known Threat Patterns for benchmark/measurement tooling (STRIDE, L1)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Dataset substitution/tampering between runs (untrusted-input boundary: env-var-provided paths) | Tampering | Input fingerprint (size + sha256 of slice/full input) recorded in results.json; report binds numbers to fingerprint; parity gate would also catch semantic swaps |
| Report truthfulness (hand-edited "wins") | Repudiation | Report rendered mechanically from results.json; comparator is the only threshold authority; raw per-rep numbers committed alongside medians |
| PR self-baseline manipulation (a PR edits its own baseline to pass the gate) | Elevation of privilege | Baseline changes reviewed like code (committed file, visible diff); optional hardening: gate workflow checks out baseline from base ref rather than PR head (mdt dual-checkout pattern) — planner choice, note in workflow comments |
| Command injection via dataset paths/filenames into `sh -c` jellyfish pipeline | Tampering/EoP | Harness constructs `sh -c` strings only from harness-controlled constants + validated absolute paths (no user-controlled free text); reject paths containing shell metacharacters at the V5 validation step; unit test with a hostile filename |
| Timer/measurement integrity (cache state misreported) | Spoofing | `cache_state` recorded per run from actual purge attempt outcome, not config intent (Pitfall 9) |
| Malicious synthetic FASTQ / crafted .rkdb read by stats during parity | Tampering | Inputs are harness-generated (seeded) or the user's own dataset; no untrusted third-party inputs enter the pipeline; existing Phase-3 hardened readers already reject corrupt `.rkdb` headers |

## Sources

### Primary (HIGH confidence — tool-verified this session)

- Local: `jellyfish count/stats/dump/merge --help` output from installed jellyfish 2.3.1 (`/opt/homebrew/bin/jellyfish`) — flag semantics verbatim
- Local: gz-input abort reproduced (`Unsupported format`, exit 134) on `.fasta.gz` and `.fq.gz`; three working feed mechanisms verified (`gzcat | /dev/stdin`, `<(gzcat …)`, `-g` generator)
- Local: count-parity demonstration — jellyfish `Distinct: 260000` == rustkmer `Unique k-mers: 260000` (k=21, `-C`, synthetic 2000×150 bp)
- Local: `/usr/bin/time -l` RSS capture incl. child attribution through `sh -c` pipes (60,391,424 B rustkmer / 525,582,336 B jellyfish `-s 100M` on smoke input)
- Local: macOS `zcat` `.Z`-only behavior → silent zero-count false successes (root-caused)
- Local: dataset absence (documented CRR1936095 path) + CRR2044018 presence/specs (150 bp NovaSeq headers)
- Repo (Read this session): `src/cli/args.rs` (Count 17-105, Merge 247-315), `src/cli/commands/count.rs` (290-334), `src/cli/commands/stats.rs` (210-229), `src/cli/commands/benchmark.rs` (300-319), `Cargo.toml`, `.github/workflows/ci.yml`, `.github/workflows/performance-regression.yml`, `.planning/{REQUIREMENTS,STATE,PROJECT,ROADMAP}.md`, `tests/common/performance.rs`

### Secondary (MEDIUM confidence — official docs / cross-checked web)

- [Biostars p/263464](https://www.biostars.org/p/263464/) — jellyfish zipped-input limitation + pipe workarounds (matches local repro)
- [Debian jellyfish 2.2.6 CHANGES](https://sources.debian.org/src/jellyfish/2.2.6-1~bpo8%2B1/CHANGES/) — pipe input, fasta/fastq-only support
- [Debian GNU time 1.9 texinfo](https://sources.debian.org/src/time/1.9-0.2/doc/time.texi/) + [LKML maxrss thread](https://lkml.org/lkml/2012/10/6/264) + [Debian #649402](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=649402) — GNU time `-v` kbytes, kernel ru_maxrss KB since 2.6.32, 1.7 4× bug history
- [Python issue 30513](https://bugs.python.org/issue30513), [nix-rust #2331](https://github.com/nix-rust/nix/issues/2331), [LLVM source comment](https://llvm.googlesource.com/llvm/+/03e6cc7c7…) — ru_maxrss bytes on Darwin vs KB on Linux
- [purge(8) man page](https://www.unix.com/man_page/osx/8/purge), [PostgresAI flush-caches guide](https://v2.postgres.ai/docs/postgres-howtos/monitoring-troubleshooting/troubleshooting/how-to-flush-caches), [ax-engine cold-start methodology](https://github.com/defai-digital/ax-engine/blob/…/EMBEDDING_COLDSTART.md), [cqlite cold-cache A/B](https://raw.githubusercontent.com/pmcfadin/cqlite/…/issue-2210-madv-random-point-read-mmap-ab.md), [shenwei356/drop_file_cache](https://github.com/shenwei356/drop_file_cache) — cold-cache protocols and their limits
- [Fanless Mac 54% skew case study](https://uvp.y42u.net/en/blog/uwview-pro-thermal-throttling-benchmark-en/), [asiai benchmark best practices](https://asiai.dev/benchmark-best-practices/), [gpu_benchmarking_osx METHODOLOGY](https://github.com/Novotarskyi/gpu_benchmarking_osx/blob/main/METHODOLOGY.md), [apple-silicon-bench FAQ](https://github.com/carlosacchi/apple-silicon-bench/wiki/FAQ), [USENIX Sec23](https://www.usenix.org/system/files/usenixsecurity23-taneja.pdf) — Apple Silicon variance + interleaving/median practice
- [abix-/endless bench guardrails](https://github.com/abix-/endless/blob/dev/docs/bench-guardrails.md), [Resilient RES-202 hyperfine gate](https://github.com/EricSpencer00/Resilient/commit/3545268bd…), [ifiokjr/mdt regression docs](https://ifiokjr.github.io/mdt/book/advanced/benchmarking-and-regressions.html), [RuView ADR-174](https://raw.githubusercontent.com/ruvnet/RuView/…/ADR-174-ci-bench-regression-compile-verify-gate.md), [linesmith perf-benchmarking survey](https://raw.githubusercontent.com/oakoss/linesmith/…/perf-benchmarking-survey.md) — CI gate patterns and shared-runner variance
- [Jellyfish releases (source-only)](https://github.com/gmarcais/Jellyfish/releases/) via [ILRI](https://hpc.ilri.cgiar.org/jellyfish-software…) / [FreeBSD ports commit](https://codeberg.org/FreeBSD/freebsd-ports/commit/c001466376…) / [EESSI](https://www.eessi.io/docs/available_software/detail/Jellyfish/) — no prebuilt binaries; pinning practice

### Tertiary (LOW confidence — single-source / unverified)

- GSA-human download path/auth for re-fetching CRR1936095 — not investigated (user decision first)
- Exact distinct-k-mer count and `.jf`/`.rkdb` sizes at full scale — estimates only until the pilot run measures them

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every measurement primitive and both tool binaries executed live this session; no new packages to vet
- Architecture: HIGH — harness design derived from verified primitives + surveyed gate patterns; the one open architectural choice (harness language) carries a documented steel-manned alternative
- Pitfalls: HIGH — five of eleven pitfalls reproduced or root-caused locally this session (zcat, gz-abort, units, empty-success, granularity); the rest are multi-source documented
- Methodology/fairness: MEDIUM-HIGH — parity and pipe mechanics verified at smoke scale; full-scale and real-data parity remain to be proven by the phase's own gates (A5-A8)

**Research date:** 2026-10-09
**Valid until:** 2026-11-08 (stable tooling; re-verify jellyfish version if brew-upgraded, and re-check dataset presence before 04-04)
