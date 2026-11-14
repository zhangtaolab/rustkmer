# Phase 10: Benchmark Verdict - Research

**Researched:** 2026-11-13
**Domain:** Full-human-scale cross-tool performance measurement — rustkmer CLI and `pyrustkmer` vs jellyfish 2.3.1 — protocol integrity, memory projection, and mechanical verdict rendering
**Confidence:** HIGH for the tool/harness mechanics (every command was executed locally this session); MEDIUM for full-scale wall/RSS projections (extrapolated from measured sub-samples, explicitly labeled)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Both surfaces are measured at full human scale: the CLI binary and the Python `pyrustkmer` counter.
- Input is the complete CRR1936095 read-1 set — both split parts (`part_001` + `part_006`, ~5.2 GB gzipped). A single part does not satisfy the human-scale requirement.
- Threads are matched across tools at 16 (all cores on the dev host): jellyfish `-t 16`, rustkmer `--threads 16`. A `t1` arm is recorded alongside as scaling evidence.
- Execution is strictly staged: slice gate (the 4M `part_001` slice with pinned parity) must be green first, then CLI full-scale, then Python full-scale. A failing stage stops the sequence — the later stages are not run on a broken foundation.
- KMC3: **Dropped entirely.** No download, no install, no execution, no comparison. BENCH-V2-01 is descoped from v2.0 by user decision, and the verdict artifact must say so explicitly rather than silently omitting the section.
- The harness must not fail or warn-spam because KMC3 is absent; absence is the intended state for this phase.
- 3 reps per arm, counterbalanced (round-robin rotation) across arms, verdict computed from recorded medians — the v1.0 protocol.
- Cache state is recorded honestly per rep. Without sudo there is no cache purge, so reps record `unavailable` rather than claiming a cold cache; the report states this limitation plainly.
- Memory is reported as `max(rss, phys_footprint)` per the project's established convention.
- Dev-host evidence only. CI-class baselines are **not** regenerated from this host; a dev-host number must never be written into a CI baseline slot.
- Both k values are measured: k=21 as the primary acceptance question, k=31 under fair matched-hash comparison to re-verify the v1.0 YES.
- The verdict is a strict comparison of recorded medians: `rustkmer_median <= jellyfish_median` is match-or-beat. No tolerance, no noise band, no re-roll.
- A NO is recorded honestly and stands. The phase never tunes parameters or re-runs until the result turns green.
- After the full-scale numbers land, the D3 decision (whether to build minimizer partitioning / a memory ceiling) is returned to the user as an explicit decision. Phase 11 is not auto-triggered by a threshold.

### Claude's Discretion

- Exact harness entry point and evidence file layout (extend `scripts/bench/` vs a new driver).
- Rep/arm scheduling details beyond counterbalancing.
- How the verdict report is rendered (markdown from recorded medians).
- Whether the Python full-scale arm reuses the Phase 9 `--compare-baseline` machinery or a phase-10-specific path.

### Deferred Ideas (OUT OF SCOPE)

- KMC3 comparison — descoped by user decision, not deferred to a later phase.
- Minimizer partitioning / memory ceiling (Phase 11) — awaits the D3 decision after this phase's numbers.
- CI-class baseline regeneration — no CI-class baseline exists; Phase 10 records dev-host evidence only.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BENCH-V2-02 | A full human-scale jellyfish parity verdict is produced on BOTH surfaces — slice gate at every step, then the full run; medians of counterbalanced reps, honest per-rep cache_state, CI baselines regenerated only from the CI runner class. Acceptance: rustkmer matches or beats jellyfish at k=21 (and k=31 under fair, matched-hash comparison). | Slice gate command verified against the committed fingerprint-bound reference; the comparison protocol exists in `bench.py`; the both-parts input seam, the Python arm seam, the `max(rss, phys_footprint)` seam, the memory preflight model, and the Phase-10 renderer/verdict requirements are specified below with measured constants. |

**BENCH-V2-01 is descoped** (2026-11-13 user decision: "不需要KMC3，本项目与KMC3 无关"). No KMC3 artifact, install, or execution is in scope; the verdict report must state the descope explicitly.
</phase_requirements>

## Summary

Phase 10 is a measurement-and-reporting phase, and most of the instrument already exists. `scripts/bench/bench.py` ships a full-mode comparison protocol (`run_comparison_protocol`) with counterbalanced round-robin rounds, one discarded warmup per tool, honest per-rep `cache_state`, medians/CV reduction, a jellyfish command builder, a strict `jellyfish stats` parser, a pre-timing parity gate, binary provenance, a disk-floor guard, and a byte-deterministic report renderer. `scripts/bench/python_bench.py` ships the Python-surface discipline: one fresh interpreter process per rep under `/usr/bin/time`, module-sha provenance, exact-count identity checks, and an exit contract of 0/1/2. The phase's engineering is therefore extension, not construction — but four concrete seams must be extended: `provision_full`/`run_bench` currently measure `part_001` and `part_006` as **separate** arms rather than counting both parts in one arm; there is **no Python arm** in the comparison protocol; the `/usr/bin/time` parser records only `maximum resident set size`, not `max(rss, phys_footprint)`; and the renderer is v1.0-specific (it hardcodes the CRR2044018 substitute sentence and has no Python surface or KMC3-descope statement).

The full-scale facts were verified locally. Both split parts contain exactly 138,165,280 lines, i.e. 34,541,320 reads each — 69,082,640 reads total — which is 8.98 B k-mer windows at k=21 and 8.29 B at k=31. The complete set is **8.6× the 4M slice per part** (17.3× for both parts); every wall/RSS figure for it in this document is an *estimate* informed by the 20M-read probe (and the Phase 8/9 slice numbers), not a measurement of the full input. A 20M-random-read probe measured 537,770,176 distinct k-mers at k=21 (RSS 35.71 GB, 41.9 s at t16), which revises the full-scale distinct projection down to an estimated **0.94–1.2 B** (the local Heaps exponent falls from 0.82 to 0.74 to 0.53 as n grows). Under a capacity-cliff memory model validated against three measured points, the CLI's both-parts k=21 peak is projected at **~68–80 GB** (fits 128 GiB; the cliff is at D≈1.88 B). The Python surface was measured at **86 B per distinct k-mer** in a single-call counter and calibrated for the two-call (part-by-part) full arm at **~33 B/entry engine tables + ~53.5 B/entry persistent DashMap**, projecting **~80–95 GB** — it fits at the projected distinct count, but the margin is finite and must be re-computed from the *measured* CLI distinct count before the Python arm runs. Jellyfish at `-s 10G` was recorded by v1.0 at 46.84 GiB (k=21) and 84.00 GiB (k=31).

Count parity is proven live on this dataset, at both k values, on 200k real reads: jellyfish and rustkmer both report 16,417,180 distinct / 25,967,840 total at k=21, and 17,362,351 / 23,967,840 at k=31; `PyCounter` reading the same `.gz` matches exactly. The committed slice reference (head-4M, distinct 229,694,874 / total 519,271,168) is fingerprint-bound to part_001's sha256 `dae91042…`, and the full gate command was executed green end-to-end this session, so the slice gate can be re-run mechanically for every stage.

**Primary recommendation:** extend `scripts/bench/bench.py` with a Phase-10 mode that (1) constructs one "both-parts" input list per tool, (2) adds a `pyrustkmer` arm that invokes a fresh `.venv313` worker process, (3) records `max(rss, phys_footprint)` per rep while preserving `peak_rss_bytes` for schema compatibility, and (4) renders a Phase-10 report carrying the Python surface, the KMC3-descope statement, the cold-cache-partial statement, and the dev-host-only statement. Stage strictly: slice gate → CLI part_001 preflight (measures the exact distinct count) → CLI both-parts k=21 → CLI both-parts k=31 → Python both-parts (only after a preflight memory check from the measured distinct count) → report.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Measured invocation (CLI, Python worker, jellyfish pipeline) | Harness subprocess wrapper | OS `/usr/bin/time` | Only a subprocess wrapper with OS rusage accounting sees the whole-pipeline wall and peak; in-process clocks are never headline numbers |
| Full-input provisioning (both split parts as one measured input) | Harness (input construction) | Dataset on disk | The measured unit is the complete r1 set; each arm must count both parts regardless of how many files the tool takes |
| Count-parity gate before timing | Harness verification | `jellyfish stats`, `rustkmer stats -f json`, `PyCounter.get_stats()` | Parity is asserted on the measured input, not inferred from synthetic history; three tools must agree before any median is trusted |
| Arm scheduling / counterbalancing / cache_state | Harness protocol | — | Thermal/order bias is systematic; rotation and a discarded warmup are protocol properties, not tool properties |
| Memory accounting | OS `getrusage` via `/usr/bin/time -l` | Harness parser | Peak is an OS high-water mark; the project convention is `max(rss, phys_footprint)` |
| Verdict computation | Harness (pure function of recorded medians) | — | `rustkmer_median <= jellyfish_median`, no tolerance, no re-roll; computed from the artifact, never asserted in prose |
| Python-surface measurement | Fresh `.venv313` worker process | Shared counting engine | The global rayon pool is first-call-wins, so one process measures one thread configuration; module sha proves which bytes ran |
| Report rendering | Harness renderer | Committed results JSON | Rendered mechanically so a hand-edited number is detectable |
| Provenance | Harness | `git`, `rustc`, `maturin` | Binary/module sha256 + commit + dirty + profile on every artifact |

## Project Constraints (from CLAUDE.md)

- **Tech stack is fixed:** Rust 1.82+ stable, PyO3 0.27.2, existing dependency set. Phase 10 adds no Rust dependency and no Python package; the harness is Python stdlib only.
- **Dual surface:** changes must benefit (or at least not regress) both the CLI and `pyrustkmer`; the shared core is the delivery vehicle. This phase observes both surfaces; it must not change counting behavior.
- **Compatibility:** preserve `.rkdb` v2 and the public CLI/Python APIs. The phase must not alter the writer, the counter semantics, or the 12-name frozen `PyCounter` surface.
- **Memory:** human-genome-scale count/merge must fit within practical RAM; the measured ceiling is set by this phase's numbers and feeds the D3 decision.
- **Benchmark honesty:** parity before timing; true per-rep `cache_state`; medians of counterbalanced reps; CI baselines only from the CI runner class; binary/module provenance (sha256 + commit + build profile) on every artifact.
- **Commands:** `cargo test`, `cargo clippy` are the named verification commands. The Python harness must stay stdlib-only (no `pytest` dependency for `scripts/bench/`).
- **Python floor:** 3.11+ per `pyo3/pyproject.toml`; use `.venv313` (Python 3.13.11) for the Python surface.
- **Rebuild discipline:** `maturin develop --release` with `CONDA_PREFIX` unset before any Python-surface run; assert `pyrustkmer.__version__` and the module sha before measuring.

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Python 3 stdlib harness (`subprocess`, `json`, `statistics`, `hashlib`, `platform`, `argparse`, `unittest`) | 3.13.11 on the dev host (`python3` on PATH) | Driver, scheduling, reduction, renderer, tests | Zero new dependencies; the project already uses this shape across `scripts/bench/`; the 415-test stdlib suite is the regression net |
| `scripts/bench/bench.py` | committed at HEAD | Measurement primitive (`/usr/bin/time`), `BenchmarkConfig`, rustkmer/jellyfish command builders, `jellyfish stats` parser, comparison protocol, parity gate, provenance, disk guard, renderer | The v1.0/v2.0 protocol is already encoded here; extending it preserves the invariants instead of re-deriving them |
| `scripts/bench/python_bench.py` | committed at HEAD | Python-surface discipline: fresh worker per rep, module sha, exact-count identity, exit contract | Phase 9's hardened Python measurement; the full arm should reuse its worker/provenance pattern |
| jellyfish | 2.3.1 at `/opt/homebrew/bin/jellyfish` [VERIFIED: local `--version`] | The pinned reference comparator | Locked by PROJECT.md; the only comparator in scope (KMC3 descoped) |
| `/usr/bin/time -l` (macOS) | OS-provided | Wall-clock + peak RSS + peak footprint around each measured invocation | rusage high-water mark; aggregates the waited-for child pipeline (verified: `sh -c 'gzcat | jellyfish'` reports the jellyfish peak, not the shell's) |
| `gzcat` | `/usr/bin/gzcat` (macOS) | Feed decompressed bytes to jellyfish | jellyfish 2.3.1 aborts on `.gz` path arguments (`Unsupported format`); the pipe keeps decompression inside the measured wall for both tools |
| `target/release/rustkmer` | 0.5.0, sha256 `f6ace9f7…c1eae9` (current build) | The measured CLI subject | Release profile (`lto`, `codegen-units=1`, `panic=abort`) is the representative binary |
| `.venv313` + `pyrustkmer` | Python 3.13.11, module `pyrustkmer.cpython-313-darwin.so` sha256 `6d526431…558ae3`, version `0.5.0` [VERIFIED: local import + shasum] | The measured Python subject | Phase 9's rebuilt extension; the module sha must match the tree at measurement time |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `jellyfish stats` | 2.3.1 | Distinct/Total/Max_count for parity and recording | One call per arm after the reps (not per rep) |
| `jellyfish info -j` | 2.3.1 | Confirms the `.jf` is `binary/sorted` and records the command line | Diagnostic only |
| `rustkmer stats -f json` | 0.5.0 | Exact `unique_kmers`/`total_kmers` for parity | One call per rustkmer arm after the reps; slow on multi-GB DBs |
| `pyrustkmer.PyCounter.get_stats()` | 0.5.0 | Exact `unique_kmers`/`total_kmers` + observed threads | Inside the Python worker; no separate stats pass |
| `scripts/bench/random_slice.py` | committed | Deterministic random-record sub-slices with selection manifests | Preflight probes and any random-slice evidence |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending `bench.py` | A new Phase-10 driver | A new driver would duplicate the schedule, reduction, parity, provenance, and disk guard; the existing renderer tests pin behavior that a rewrite would silently diverge from. Extend instead |
| Reusing `--compare-baseline` for the Python full arm | A Phase-10 Python full-arm path | `--compare-baseline` is slice-mode-only and t1-only by construction (`python_bench.py:785`, `:1069`); the full arm needs a new mode that measures both parts in one process at t16 and reports medians for the verdict |
| `-s 10G` for jellyfish | `-s 2G` / `-s 4G` | 10G is the v1.0 recipe and far exceeds the projected distinct count; the memory cost is 40–90 GB. A smaller size is defensible only if recorded and applied identically at k=21 and k=31 — do not silently change it between tables |
| `--size` matching `-s` on rustkmer | Leave `--size` at its default | See Pitfall 2: `--size` is a *total* capacity hint divided across 64 partitions; matching 10G would pre-reserve ~160 GB and abort instantly |

**Installation:** none. This phase installs no packages: the harness is Python stdlib, jellyfish 2.3.1 is already present, and no crate or pip package is added. `cargo build --release --locked` is the only build step (it already succeeds on this tree).

## Package Legitimacy Audit

> This phase installs **no external packages**. The comparator is an already-installed system binary; the harness is stdlib-only; no crate or pip package is added. The gate is therefore vacuously satisfied. If the planner adds any package anyway, re-run `gsd-tools query package-legitimacy check` before install.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| *(none — stdlib + preinstalled binary)* | — | — | — | — | — | Approved (N/A) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                         ┌──────────────────────────────────────────────────────────┐
                         │        Phase-10 driver (scripts/bench/bench.py ext.)     │
                         │                                                          │
  CONTEXT decisions ────▶│  1. slice gate: provision head-4M from part_001          │
  (k=21/31, t16+t1,      │     → rustkmer + jellyfish count the SAME slice          │
   both parts, 3 reps)   │     → assert pinned 229,694,874 / 519,271,168            │
                         │     → provenance-bound gate record                       │
                         │                                                          │
                         │  2. CLI preflight: part_001 alone (1 rep, k=21)          │
                         │     → exact distinct D1, wall, RSS                       │
                         │     → memory model predicts both-parts peak (go/no-go)   │
                         │                                                          │
                         │  3. per-k full protocol (k=21 then k=31):                │
                         │     arms = [rk-t16, rk-t1, jf-t16, py-t16]               │
                         │     schedule = round-robin rotation, 3 reps,             │
                         │     warmup per tool discarded, cache_state per rep       │
                         └───────────────┬──────────────────────────────────────────┘
                                         │
        ┌────────────────────────────────┼──────────────────────────────────┐
        ▼                                ▼                                  ▼
┌───────────────────────┐   ┌───────────────────────────┐   ┌──────────────────────────────┐
│ rustkmer CLI arm      │   │ jellyfish arm             │   │ pyrustkmer arm               │
│ /usr/bin/time -l      │   │ /usr/bin/time -l          │   │ /usr/bin/time -l             │
│  rustkmer count -k K  │   │  sh -c 'gzcat p1 p2 |     │   │  .venv313/bin/python worker  │
│   -C --threads {16,1} │   │   jellyfish count -m K    │   │   PyCounter(k,canonical,     │
│   -i p1 p2 -o out.rkdb│   │   -s 10G -t 16 -C         │   │   threads=16)                │
│ (reads .gz natively)  │   │   -o out.jf /dev/stdin'   │   │   add_from_fastq(p1); (p2);  │
│                       │   │                           │   │   get_stats() → stats.json   │
└──────────┬────────────┘   └────────────┬──────────────┘   └──────────────┬───────────────┘
           │                             │                                 │
           ▼                             ▼                                 ▼
    rustkmer stats -f json        jellyfish stats               exact counts in stats.json
           └──────────────┬──────────────┴─────────────────┬───────────────┘
                          ▼                                ▼
              parity: all three distinct/total must agree, > 0
                          ▼
              medians + CV per arm (from recorded reps only)
                          ▼
              verdict: rk-t16 median <= jf-t16 median
                    AND py-t16 median <= jf-t16 median
                    (per k; t1 arms are scaling evidence, excluded by rule)
                          ▼
              Phase-10 report (mechanical): tables, verdicts, parity,
              provenance, cache census, KMC3 descope, dev-host statement
```

A reader can trace the acceptance question from the CONTEXT decisions through the staged gates to the rendered verdict: slice parity is proven first, the CLI preflight measures the true distinct count, the per-k protocol records three counterbalanced medians per arm, and the verdict is a pure comparison of those recorded medians.

### Recommended Project Structure (additions only)

```
scripts/bench/
├── bench.py                    # extend: both-parts arm construction, Python arm,
│                               #   max(rss, footprint) parser fields, Phase-10 renderer
├── python_bench.py             # extend or import: full-input worker (two add_from_fastq calls)
├── baselines/
│   └── slice_parity.crr1936095.json   # READ-ONLY: fingerprint-bound slice reference
└── tests/
    ├── test_phase10_verdict.py # new: verdict pairing, t1 exclusion, both-parts construction
    ├── test_time_parser.py     # extend: peak-footprint line + max() semantics
    └── test_python_full_arm.py # new: worker stats validation, two-input accumulation
.planning/phases/10-benchmark-verdict/
├── 10-RESEARCH.md              # this file
├── 10-results-full-k21.json    # mode=full artifact (all arms, all reps)
├── 10-results-full-k31.json    # mode=full artifact
├── 10-slice-gate.json          # provenance-bound slice gate record
├── 10-BENCHMARK-REPORT.md      # mechanically rendered report
└── evidence/                   # optional: gate logs, sha256 census
```

No file under `scripts/bench/baselines/` may be modified or added by this phase (dev-host evidence only).

### The v1.0 invocation recipe (committed precedent — reusable)

v1.0's committed artifacts do record a complete, reusable recipe. From `docs/benchmark-report.md` (methodology block):

> `- jellyfish \`-s 10G\` (generous initial hash; recorded in results)`
>
> `- decompression arrangement: rustkmer reads the .gz natively; jellyfish receives \`gzcat | jellyfish count ... /dev/stdin\` — decompression is inside BOTH tools' measured wall; the residual asymmetry (pipe and context-switch overhead on the jellyfish arm only) remains and is stated here per protocol`

From `04-results-full-k21.json` (`params`): `"k": 21`, `"canonical": true`, `"threads": 16`, `"hash_size": "10G"`, `"decompressor": "gzcat"`, `"reps": 3`, `"cooldown_s": 5`, round schedule round 0 = `["rustkmer", "jellyfish"]`, round 1 reversed, round 2 = round 0. Commands derived from that config [VERIFIED: scripts/bench/bench.py:201-245]: `rustkmer count -k 21 -C --threads 16 -o out.rkdb -i <inputs>` and `sh -c 'gzcat <inputs...> | jellyfish count -m 21 -s 10G -t 16 -C -o out.jf /dev/stdin'`. Phase 10 reuses this recipe with the k=21/k=31 inputs being both parts and the input set being the complete r1 file list.

### Harness seams and blockers (extend `bench.py`)

| Seam | Current state (verified) | Phase-10 change | Blocker if unchanged |
|------|--------------------------|-----------------|----------------------|
| Arm scheduling | `run_comparison_protocol` (bench.py:1244) rotates tools; each tool's warmup is discarded | Add a `pyrustkmer` tool class; rotate four arms; keep the rotator | No Python surface in the verdict |
| Input construction | `provision_full` (bench.py:631) returns the first two inputs; `run_bench` builds `cfg_a=inputs[0]`, `cfg_b=inputs[1]` | One arm over the full two-part list | Measures half the dataset |
| `cache_state` | `attempt_cache_purge` + per-rep label already correct | None (reuse) | — |
| Provenance | `binary_provenance` + `fingerprint`; `validate_provenance` tolerates extra keys | Add `provenance.python_module`, interpreter, maturin version | Python artifact lacks module identity |
| Memory accounting | `parse_time_output` records only `maximum resident set size` | Parse `peak memory footprint`, record `max(rss, footprint)` | Violates the locked memory convention |
| Verdict rendering | v1.0 renderer hardcodes the CRR2044018 substitute sentence; `_count_verdict` includes every rustkmer count arm; no Python arm; no KMC3 statement | Phase-10 render function: Python surface, t16-only rule, descope/cold-cache/dev-host statements | Wrong dataset text; t1 arm manufactures a NO; missing success criterion 4 |
| Python full run | `python_bench.py --mode` choices are `("synthetic", "slice")`; `--compare-baseline` is slice/t1-only | New full-input worker mode (two `add_from_fastq` calls) | No full Python measurement path |
| Post-arm stats | `rustkmer stats` scans the DB (minutes at full scale); `jellyfish stats` reads the `.jf` | Keep one call per arm after its reps | Budget overrun |

### Pattern 1: Both-parts single arm (the input seam)
**What:** Each tool's arm must count the complete r1 set in one measured invocation. rustkmer takes `-i part_001 part_006` (one engine, cumulative tables); jellyfish takes `gzcat part_001 part_006 | jellyfish ... /dev/stdin`; Python calls `add_from_fastq(part_001)` then `add_from_fastq(part_006)` in one fresh process (Phase 9 proves successive calls accumulate exactly).

**When to use:** Every full-scale arm. The current `run_bench` violates this: `provision_full` returns the first two inputs [VERIFIED: scripts/bench/bench.py:631-639 — `"""Measure the resolved inputs directly (first two; a single input is measured twice — an honest repeated measurement, not a fabrication)."""`] and `run_bench` builds `cfg_a` with `inputs=[inputs[0]]` and `cfg_b` with `inputs=[inputs[1]]`, i.e. two separate single-part arms. A Phase-10 mode must build one arm whose `inputs` list is the full two-part list.

**Why:** Counting each part separately measures a different workload (half the reads, a truncated distinct set) and cannot answer the acceptance question; the locked decision names both parts as the measured input.

```python
# Shape of the required arm construction (derived from bench.py's existing builders)
cfg_full = BenchmarkConfig(k=k, canonical=True, threads=16,
                           hash_size="10G", inputs=[part_001, part_006],
                           decompressor=default_decompressor())
rk_cmd = rustkmer_count_cmd(cfg_full, db_out, rustkmer)   # -i p1 p2
jf_cmd = jellyfish_count_cmd(cfg_full, jf_out)            # gzcat p1 p2 | jellyfish ...
```

### Pattern 2: Three-tool counterbalanced protocol

**What:** Extend `run_comparison_protocol` (bench.py:1244) from a two-tool to a four-arm protocol: `rk-t16`, `rk-t1`, `jf-t16`, `py-t16`, one discarded warmup per *tool*, then `--reps` rounds; each round visits every arm exactly once in rotated order; every rep records `round`, `arm_order`, and the honest `cache_state`.

**When to use:** The full-scale measurement per k.

**Why:** The existing protocol already implements the v1.0/v2.0 discipline; adding a Python arm is a tool-class branch (counts from the worker's `--stats-out` file instead of `rustkmer stats`), not a protocol rewrite. The rotation prevents thermal/order bias from accumulating inside one arm's block.

**Critical rule:** the verdict must compare only matched-thread arms. The v1.0 `_count_verdict` requires *every* rustkmer count arm to beat jellyfish; with a t1 arm in the same document that rule would compare a t1 run against a t16 jellyfish run and manufacture a NO. Phase 10 must filter to `threads == 16` arms for the acceptance verdict and report t1 arms separately as scaling evidence.

### Pattern 3: Memory preflight from the measured distinct count

**What:** Before the both-parts CLI run and again before the Python arm, compute the projected peak from the *measured* distinct count and the model below; abort with exit 2 (invalid, no artifact) or surface a user checkpoint if the projection exceeds a declared budget (recommend 110 GiB of the 128 GiB host, leaving ~18 GiB for OS/page cache).

**Model (validated at three measured points):** with P=64 partitions, hashbrown capacity is the next power of two ≥ D/(P·0.875); each slot is 16 B (`Dense(hashbrown::HashMap<u64, u32>)` — 8-byte key + 4-byte count padded to 16 B [VERIFIED: src/hash/local.rs:103]); the pair buffer is 32 B/entry (u128 + u32 padded). Peak ≈ 16·cap·P + 32·D + base. Validation: Phase 8 head-4M (D=229,694,874) predicts tables 4.29 GB + pairs 7.35 GB + ~0.4 GB base ≈ 12.0 GB, observed 12.04 GB; 5M random (D=256,606,202) predicts 17.5 GB, observed 17.52 GB; 20M random (D=537,770,176) predicts 35.7 GB, observed 35.71 GB.

**Python model:** measured single-call coefficient is 86 B/distinct (20M distinct → 1.707 GB; 40M → 3.438 GB). The full arm makes two calls, so peak ≈ 33 B/entry × D_part + 53.5 B/entry × D_union (calibrated from a two-call probe: 2×20M distinct calls with a 40M union → 2.949 GB vs 3.438 GB for a single 40M call).

### Pattern 4: Mechanical Phase-10 report

**What:** Render the report from the committed JSONs with no measurement literals and no render-time clock; re-rendering must be byte-identical. The v1.0 renderer cannot be reused as-is: it hardcodes the CRR2044018 substitute sentence and the v1.0 attempt-1 halt note, and it has no Python surface or KMC3-descope statement. Add a Phase-10 renderer section (or a new renderer) with mandatory lines:

- dataset provenance: CRR1936095, both parts, fingerprints, `dae91042…` for part_001;
- KMC3 descope: "BENCH-V2-01 was descoped on 2026-11-13 by user decision; no KMC3 binary was downloaded, installed, or executed" — this is success criterion 4, not optional prose;
- cold-cache partial: every rep's `cache_state` census plus the plain statement that the cold-cache criterion is only partially satisfied because no sudo purge was run;
- dev-host only: no CI-class baseline was regenerated or written;
- per-arm threads and the verdict rule (t16 arms only; t1 excluded as scaling evidence);
- provenance: CLI binary sha256 + git commit/dirty + build profile + Python module sha256 + interpreter + maturin version.

### Anti-Patterns to Avoid

- **Do NOT "match" rustkmer `--size` to jellyfish `-s 10G`.** `--size` is a total capacity hint divided across partitions [VERIFIED: src/count/engine.rs:604 — `let per_partition_capacity = (config.initial_capacity / layout.partitions()).max(1);`] and the default is 1,000,000 [VERIFIED: src/cli/args.rs:53-54 — `#[arg(long, default_value = "1000000")]` / `size: usize,`]. Passing 10,000,000,000 would pre-reserve ~160 GB (64 partitions × 156M entries × 16 B) and abort before reading a read.
- **Do NOT use `--compare-baseline` for the full Python arm.** It is slice-mode and t1-only by construction [VERIFIED: scripts/bench/python_bench.py:785 — `"--compare-baseline requires --mode slice — the N-free "`; `--mode` choices are `("synthetic", "slice")` at :1069]. Its baseline is a 1M-read sequential reference, not a full-scale comparator.
- **Do NOT edit or regenerate any committed baseline.** `slice_parity.crr1936095.json` and `python_bench_baseline.darwin.json` are immutable history; the verdict artifact asserts their shas.
- **Do NOT run the two tools concurrently.** They contend for the unified memory pool and cores; sequential interleaved rounds only.
- **Do NOT report a partial run as full-scale.** A killed/OOM/failed run must produce no artifact (exit 2); only a `mode=full` document with all arms and all reps may feed the verdict.
- **Do NOT claim a cold cache.** Every rep records `unavailable` without sudo; the report says "partially satisfied".
- **Do NOT hand-edit report numbers.** Render mechanically from the JSONs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Counterbalanced arm scheduling | Ad-hoc `for arm in arms` loops | `run_comparison_protocol` / `rotation_schedule` (bench.py:1244, :1160) | Round-robin rotation, discarded warmup, per-rep round/order, honest cache_state — already tested |
| jellyfish command construction | Hand-written shell strings | `jellyfish_count_cmd` (bench.py:216) | It owns the gz-pipe branch and the path/hash-size/decompressor allowlists (T-04-03); a second implementation is an injection surface |
| `jellyfish stats` parsing | `awk`/split on whitespace | `parse_jellyfish_stats` (bench.py:676) | Strict line-anchored regexes; a missing `Distinct:` raises instead of yielding a zero/None that could pass |
| Binary/module provenance | Timestamps or path strings | `binary_provenance` + `fingerprint` (bench.py:309, :268); python_bench `build_provenance` | Actual-bytes sha256 + git commit/dirty + profile; path strings are not provenance |
| Peak-memory accounting | `ps` polling | `/usr/bin/time -l` rusage | Exact high-water mark, no observer overhead, aggregates the waited-for child pipeline |
| Input slicing | `head -n` on gz by hand | `provision_slice` / `random_slice.py` | Deterministic, fingerprintable, manifest-backed; head-4M is fingerprint-bound to the committed reference |
| Verdict math | Asserting "we win" in prose | A pure function of recorded medians | The report is rendered from JSON; a hand-edited number must be detectable |
| Python-surface process protocol | In-process timing | `python_bench.py`'s fresh-worker pattern | The global rayon pool is first-call-wins; one process = one thread config; module sha proves the measured bytes |

**Key insight:** every measurement-critical primitive already exists and is regression-tested (415 stdlib tests). The phase's engineering risk is in the seams (both-parts arms, Python arm, footprint parsing, Phase-10 renderer), not in measurement infrastructure.

## Common Pitfalls

### Pitfall 1: "Full mode" currently measures one part per arm
**What goes wrong:** Running `bench.py --mode full --input <dir>` today builds `count-A` over `inputs[0]` and `count-B` over `inputs[1]`. The resulting artifact claims `mode=full` but never counts the complete r1 set in one arm; a verdict rendered from it answers a half-size question.
**Why it happens:** v1.0's full run used two inputs to measure the same file twice (or r1/r2 at slice scale); `provision_full` intentionally returns the first two paths [VERIFIED: scripts/bench/bench.py:631-639].
**How to avoid:** Add a Phase-10 arms mode that passes the full two-part list to ONE arm per tool, and assert in the artifact that `inputs == [part_001, part_006]` and that the arm's `input_fingerprint` covers both files.
**Warning signs:** an artifact where `count-A` and `count-B` have different fingerprints in a full-mode run, or a `distinct_kmers` total near half the expected union.

### Pitfall 2: Matching rustkmer `--size` to jellyfish `-s` reserves ~160 GB
**What goes wrong:** A well-meaning "matched-hash" change passes `--size 10000000000`. The engine divides the hint across 64 partitions and preallocates each table [VERIFIED: src/count/engine.rs:604], instantly reserving ~160 GB and failing before the first read.
**How to avoid:** Leave `--size` at its default (1,000,000) and record it; document that rustkmer auto-grows, while jellyfish receives a generous `-s`. "Matched-hash" means both were sized to avoid growth penalties — not that the numbers are equal.
**Warning signs:** near-instant OOM/allocation failure at process start, or RSS jumping to >150 GB before input is read.

### Pitfall 3: jellyfish cannot read `.gz` paths; the pipe is mandatory
**What goes wrong:** `jellyfish count ... part_001.fq.gz` aborts (`Unsupported format`). Piping through the wrong decompressor (macOS `zcat` expects `.Z`) can deliver EOF while jellyfish still exits 0 with an empty database.
**How to avoid:** Use `default_decompressor()` (gzcat on darwin, gunzip -c otherwise); assert `distinct > 0` after every arm (the protocol already raises on zero counts). The parity gate against rustkmer catches a truncated stream.
**Warning signs:** exit 134, or `Distinct: 0`; v1.0 lost three runs to the zcat variant.

### Pitfall 4: Multi-member gzip truncation is caught only by parity
**What goes wrong:** A single-member gzip decoder reads only the first member of a concatenated `.gz`, producing a small fraction of the true count with exit 0. v1.0 hit exactly this (fix `8102985`, MultiGzDecoder).
**How to avoid:** rustkmer's reader uses `flate2::read::MultiGzDecoder` [VERIFIED: src/io/fastq.rs:78]; keep the pre-timing parity gate against jellyfish (which decompresses via `gzcat`) on the actual measured input. Do not "prove" multi-member handling only on the head-4M plain `.fq` slice — the slice gate does not exercise the gz reader.
**Warning signs:** rustkmer distinct a tiny fraction of jellyfish's on the same input.

### Pitfall 5: `peak memory footprint` on a pipeline is the shell's footprint
**What goes wrong:** `/usr/bin/time -l sh -c 'gzcat | jellyfish'` prints `maximum resident set size` (the pipeline's peak, e.g. 526,532,608 B) and `peak memory footprint` (the *direct child shell's* footprint, e.g. 1,294,648 B). Taking the footprint line as the tool's memory would under-report by 400×; taking only RSS would miss compressed-memory cases for direct children.
**How to avoid:** Parse both lines and record `max(rss, footprint)` per rep, while keeping `peak_rss_bytes` (the schema-required field) and adding the raw footprint. For pipeline arms the max is the RSS; for direct children the two are close (1,194,852,352 vs 1,192,199,608 B for rustkmer).
**Warning signs:** a jellyfish arm reporting ~1 MB peak.

### Pitfall 6: `rustkmer stats` is slow on multi-GB databases
**What goes wrong:** The post-arm exact-count read scans the whole `.rkdb`. Measured this session: 28.6 s for a 2.6 GB DB (2M reads), 55.5 s for 5.4 GB (5M reads), 123.7 s for 10.75 GB (20M reads). At full scale a 21–24 GB DB may take 4–8 minutes per call.
**How to avoid:** Call `stats` once per arm after its reps (not per rep), and budget it in the wall-clock estimate. Do not replace it with stderr progress parsing (fragile).
**Warning signs:** the measurement "finishing" long after the last timed rep.

### Pitfall 7: Partial or failed full runs must not become results
**What goes wrong:** A killed process, OOM, or Ctrl-C mid-round leaves scratch files; copying them into the phase directory as "results" would report a partial run as full-scale.
**How to avoid:** The artifact is written only after all arms complete and validate; any failure exits 2 with no artifact at the destination. The verdict renderer requires `mode=full` and all arms; a missing arm is an error, not a table row.
**Warning signs:** an artifact with fewer reps than requested, or `mode=full` with a fingerprint that covers only one part.

### Pitfall 8: The Python arm can OOM if the measured distinct count is high
**What goes wrong:** `PyCounter` merges the engine's partition tables into a persistent `DashMap`; `merge_into` merges all tables in parallel [VERIFIED: src/count/engine.rs:505-512 — `self.tables.par_iter().try_for_each(|table| counter.merge_local_counts(table))`], so all partition tables stay alive during the merge. The measured single-call cost is 86 B/distinct; a two-call full arm is ~33 B/entry on the per-part tables plus ~53.5 B/entry on the union DashMap.
**Why it happens:** Unlike the CLI's consuming drain [VERIFIED: src/count/engine.rs:413-421 — `for table in self.tables { table.into_pairs_into(&mut pairs); }`], the Python path retains both structures at peak.
**How to avoid:** Run the CLI both-parts arm first; take its exact distinct count; compute the projection; if it exceeds the budget, surface a user checkpoint instead of attempting the run. The projection is a gate, not an estimate to "try anyway".
**Warning signs:** RSS climbing past ~100 GB, macOS memory-pressure warnings, or the worker dying with no stats file.

### Pitfall 9: The environment's `python3` matters
**What goes wrong:** `/usr/bin/python3` is macOS system Python **3.9.6**; the stdlib harness uses `Path.write_text(newline=...)` (3.10+) and fails with 47 errors. The phase's documented harness command must use `python3` on PATH (3.13.11) or `.venv313/bin/python`.
**How to avoid:** Use `python3 -m unittest discover -s scripts/bench/tests -t .` (415 tests, OK, 1 skip) and `.venv313/bin/python` for the binding tests.
**Warning signs:** dozens of `TypeError: write_text() got an unexpected keyword argument 'newline'` errors.

### Pitfall 10: The v1.0 jellyfish k=31 slowdown may not reproduce — and that is fine
**What goes wrong:** v1.0 recorded jellyfish k=31 at 843.02 s vs 97.26 s at k=21 on a different dataset; budgeting 26 min/rep could over-allocate hours. A 5M-read slice of CRR1936095 measured this session shows jellyfish k=31 and k=21 at 16.87 s vs 16.80 s (6.46 GB vs 3.72 GB RSS at `-s 1G`) — the anomaly did not reproduce.
**How to avoid:** Budget from the phase's own warmup/early reps, keep the CV warning machinery, and treat the v1.0 number as dataset-specific history, not a forecast.
**Warning signs:** a schedule that assumes a 9× k=31 penalty before any local measurement.

### Pitfall 11: Disk is finite (242 GiB free, not the v1.0 host's 1.5 TB)
**What goes wrong:** Full artifacts at D≈1.05–1.2 B are ~21–24 GB per `.rkdb` (20 B/distinct), ~10–14 GB per `.jf` (10 B/distinct at k=21, 12 B at k=31, verified from the gate run's 2.30 GB `.jf` for 229.7M distinct), plus the 1.47 GB slice and probes. Two k values retained together ≈ 70 GB; add the Python arm (no DB written) and scratch, comfortably under 242 GiB but not under a 150 GiB floor plus leftovers.
**How to avoid:** Keep the existing disk-floor guard, delete per-k `.rkdb`/`.jf` after their stats and shas are recorded (or keep one representative pair), and never let scratch probes accumulate.
**Warning signs:** `No space left on device` mid-round.

### Pitfall 12: A dev-host number must never enter a CI baseline slot
**What goes wrong:** `--emit-baseline` in `python_bench.py` writes an immutable comparison basis; using it (or hand-copying a dev number into `scripts/bench/baselines/`) would violate the locked decision and poison the CI gate.
**How to avoid:** Never pass `--emit-baseline`; verify `git status` shows no changes under `scripts/bench/baselines/`; the report states "dev-host evidence only; no CI-class baseline was regenerated".
**Warning signs:** a modified baseline file in the phase diff.

## Code Examples

### Slice gate — the exact command that was verified end-to-end this session

```bash
# Verified 2026-11-13: exit 0, PARITY OK + PARITY REFERENCE OK.
# --hash-size 2G is ample for 229.7M distinct and keeps jellyfish at ~10 GB;
# the committed reference carries no hash-size field, so the gate's counts are
# invariant. Pass the FILE (not the directory) so the source fingerprint is
# part_001's dae91042…
python3 scripts/bench/bench.py --parity-only --mode slice \
  --slice-selection head --slice-reads 4000000 --k 21 --threads 16 \
  --hash-size 2G \
  --input /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz \
  --parity-reference scripts/bench/baselines/slice_parity.crr1936095.json \
  --out <scratch>/parity_gate.json
# stdout:
#   PARITY OK distinct=229694874 total=519271168
#   PARITY REFERENCE OK distinct=229694874 total=519271168 (bound to source dae91042e42c… kind=head-4M-profiling-reference)
# The emitted record carries binary sha256 f6ace9f7…, git commit 967b3bc,
# build_profile release, and the slice recipe (head-4M, k=21, canonical, t16).
```

Run this gate before EACH stage (CLI k=21, CLI k=31, Python k=21, Python k=31) or at minimum before each surface/k pair; "slice gate green at every step" is a locked decision.

### Full CLI arm — both parts in one invocation

```bash
/usr/bin/time -l target/release/rustkmer count -k 21 -C --threads 16 \
  -o <scratch>/rk_k21.rkdb \
  -i /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz \
     /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_006.fq.gz
# Two files -> one engine, cumulative tables, one union .rkdb.
# Do NOT add --size 10000000000 (Pitfall 2). Leave the 1,000,000 default.
```

### Full jellyfish arm — both parts through one pipe

```bash
# The harness builds this as ONE string (no line breaks inside the quotes).
/usr/bin/time -l sh -c 'gzcat /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_006.fq.gz | jellyfish count -m 21 -s 10G -t 16 -C -o <scratch>/jf_k21.jf /dev/stdin'
# Then: jellyfish stats <scratch>/jf_k21.jf
# -s 10G is the v1.0 recipe; memory at k=21 ~46.84 GiB, at k=31 ~84.00 GiB
# (v1.0 recorded values; ~50/90 GB decimal). The .jf is proportional to
# DISTINCT, not -s:
# 229.7M distinct produced a 2,296,950,252-byte .jf (10.0 B/k-mer) in the
# verified gate run; k=31 is ~12 B/k-mer.
```

### Full Python arm — two calls in one fresh process

```python
# python_bench.py --worker extension (phase-10 worker mode)
import pyrustkmer
counter = pyrustkmer.PyCounter(k, canonical=True, threads=16)
counter.add_from_fastq(part_001)      # accumulates exactly (Phase 9 adjacency proof)
counter.add_from_fastq(part_006)
st = counter.get_stats()
payload = {"total_kmers": int(st.total_kmers),
           "unique_kmers": int(st.unique_kmers),
           "threads_resolved": int(st.threads),
           "module_path": ..., "module_sha256": ...}
# The process is wrapped by /usr/bin/time -l; one process = one thread config.
# Verified on 200k real reads: gz input matches CLI/jellyfish exactly
# (25,967,840 total / 16,417,180 unique at k=21).
```

### Memory preflight (run after the CLI both-parts arm; before the Python arm)

```python
import math

def cli_peak_bytes(distinct, partitions=64):
    """Validated against three measured points (12.04/17.52/35.71 GB)."""
    cap = 1 << math.ceil(math.log2(distinct / partitions / 0.875))  # u64,u32 slot = 16 B
    tables = 16 * cap * partitions
    pairs = 32 * distinct          # Vec<(u128,u32)> buffer
    return tables + pairs

def python_peak_bytes(d_part, d_union):
    """Calibrated from single-call 20M/40M probes and a two-call 2x20M probe:
    33 B/entry per-part engine tables + 53.5 B/entry union DashMap."""
    return 33 * d_part + 53.5 * d_union

BUDGET = 110 * (1 << 30)          # leave ~18 GiB of the 128 GiB host
# CLI k=21: D~1.05B -> ~68 GB (fits); capacity cliff at D~1.88B (~129 GB).
# Python:   D_part~0.74B, D_union~1.05B -> ~80 GB (fits);
#           OOM cliff around D_union~1.4-1.6B.
```

### `max(rss, phys_footprint)` parsing

```python
# macOS `time -l` emits both lines; only the RSS line aggregates a pipeline.
MAC_RSS = re.compile(r"^\s*(\d+)\s+maximum resident set size\s*$")   # bytes
MAC_FOOTPRINT = re.compile(r"^\s*(\d+)\s+peak memory footprint\s*$")  # bytes
# Record per rep: peak_rss_bytes (unchanged schema field),
#                 peak_footprint_bytes (new), peak_bytes = max(rss, footprint).
# Verified: pipeline arm -> (526,532,608, 1,294,648); direct rustkmer -> (1,194,852,352, 1,192,199,608).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v1.0 headline = k=31 on the CRR2044018 substitute | v2.0 acceptance = k=21 primary on the real CRR1936095 r1 set (both parts), k=31 as re-verification | v2.0 roadmap / Phase 10 CONTEXT | The milestone question is answered on the intended dataset and k |
| v1.0 compared two rustkmer arms on one input | Phase 10 compares matched-thread arms of three tools (`rk-t16`, `jf-t16`, `py-t16`) plus a CLI t1 scaling arm | This phase | The Python surface enters the acceptance verdict for the first time |
| KMC3 as a second comparator (BENCH-V2-01) | Descoped by user decision (2026-11-13) | REQUIREMENTS.md update | No third-party binary; the report states the descope explicitly |
| Peak memory reported as maxRSS only | `max(rss, phys_footprint)` per the project's pre-registered convention | CONTEXT locked decision | Honest memory accounting on macOS |
| Naive Heaps extrapolation from 1M–5M reads (1.7–2.4 B distinct) | 20M-read probe + falling local exponent → 0.94–1.2 B distinct | This research | The full run is projected to fit; earlier OOM fear was an artifact of the short baseline |

**Deprecated/outdated:**
- v1.0's "substitute dataset" sentence in the renderer — Phase 10 runs the real dataset and must render its own provenance.
- The assumption that `python_bench.py --compare-baseline` can serve full-scale Python evidence — it is slice-mode/t1-only by construction.
- Budgeting jellyfish k=31 at ~26 min/rep from v1.0's 843 s — not reproduced at 5M-read scale.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Full both-parts distinct is ~0.94–1.2 B at k=21 (`[ASSUMED]` extrapolation from the measured 20M-read point 537,770,176 with a falling local Heaps exponent 0.53–0.62) | Summary / Pattern 3 | **HIGH** — a value ≥1.4–1.6 B pushes the Python arm toward OOM and ≥1.88 B pushes the CLI over the capacity cliff; the phase's preflight from the measured CLI count is the mitigation, not the estimate |
| A2 | The Python two-call peak splits as 33 B/entry (part tables) + 53.5 B/entry (union DashMap) — `[ASSUMED]` calibration on synthetic disjoint inputs, not real full data | Pattern 3 / Pitfall 8 | HIGH — a different split changes the projected peak by ±15 GB; the preflight must be re-anchored on the actual `D_part`/`D_union` before the run |
| A3 | Per-rep wall: CLI ~145–180 s, Python ~260–320 s, jellyfish ~166–233 s (extrapolated from 20M-read, 1M-read, and 5M-read measurements) | Summary / Open Q3 | MEDIUM — the protocol can overrun by hours; stage per k and write artifacts per stage |
| A4 | The t1 arm is CLI-only scaling evidence; the Python and jellyfish verdict arms are t16 | Open Q2 | MEDIUM — if the user intended Python t1 too, add ~60–65 min per k |
| A5 | The two split parts are disjoint read sets of one library, so the union distinct is below the sum of parts | Summary / A1 | LOW–MEDIUM — if they overlap heavily, D_union is lower (safer); if they are different libraries, D_union is higher |
| A6 | The host is otherwise idle during the measurement window | Protocol | MEDIUM — other memory pressure invalidates the peak projections and can turn a fit into an OOM |
| A7 | jellyfish k=31 at full scale behaves like k=21 (no 9× penalty) | Pitfall 10 | MEDIUM — if the v1.0 anomaly recurs, the k=31 jellyfish arm alone could take 1–2 h; the schedule must be resumable per arm |

## Open Questions

1. **What happens if the preflight projects the Python arm over budget?** (RESOLVED — CONTEXT post-research decision "Python OOM is a hard gate with a user stop"; the three options are carried verbatim in Plan 10-04 task 1 and are the user's to choose)
   - What we know: the single-call coefficient is 86 B/distinct; the two-call model projects ~80–95 GB at D_union 1.05–1.2 B, with an OOM cliff near D_union ≈ 1.4–1.6 B. The CLI both-parts run measures D_union exactly before the Python arm starts.
   - What's unclear: whether the user would accept a scoped memory change or a non-full Python measurement if the projection exceeds the budget.
   - Recommendation: make the preflight a hard gate. If over budget, STOP and return an explicit user decision with three options: (a) record the Python full-scale verdict as BLOCKED by RAM (honest, no artifact claiming full scale); (b) authorize a scoped `CountResult::merge_into` drain change (drops the peak toward ~T(D_part)+DashMap(D), but does not eliminate the DashMap cost); (c) accept a single-part Python measurement explicitly labeled NOT full-scale. Do not silently choose any of these.

2. **Is the t1 arm CLI-only, and how many reps?** (RESOLVED — CONTEXT post-research decision "The `t1` arm is CLI-only"; the locked 3-rep protocol applies to it, Plans 10-01/10-03 run it, and the verdict filter `threads == 16` excludes it)
   - What we know: CONTEXT says "jellyfish `-t 16`, rustkmer `--threads 16`. A `t1` arm is recorded alongside as scaling evidence." The 3-rep protocol is locked; t1 arms are excluded from the acceptance rule (otherwise a t1 run is compared against a t16 jellyfish run).
   - What's unclear: whether Python t1 is required (cost ~63 min/k at 3 reps) and whether t1 arms need all 3 reps.
   - Recommendation: CLI t1 only, 3 reps if the ~6 h total is acceptable; otherwise declare t1 evidence-grade with 1 measured rep in the plan (a surfaced decision, not a silent reduction). The verdict must filter `threads == 16`.

3. **Extend `bench.py` or add a Phase-10 driver?** (RESOLVED — Claude's Discretion plus Plan 10-01/10-02: a new `scripts/bench/phase10.py` controller; `bench.py` receives only the `parse_time_output` extension, and its v1.0 renderer/tests stay byte-identical)
   - What we know: `bench.py` already has the protocol, parity, provenance, disk guard, and renderer; its renderer is v1.0-specific and its v1.0 tests pin byte-identical output.
   - Recommendation: extend `bench.py` with new arm construction and a separate Phase-10 render function, leaving the v1.0 renderer and its tests untouched. Add `scripts/bench/tests/test_phase10_verdict.py` (Wave 0).

4. **Which artifacts should be retained?** (RESOLVED — Plans 10-02/10-03: record each `.rkdb`/`.jf` sha256 in the evidence, then delete the scratch databases after stats and shas are captured; nothing under `/tmp` is committed and the verdict never depends on the DBs)
   - What we know: `.rkdb` ≈ 20 B/distinct, `.jf` ≈ 10–12 B/distinct; both k values retained ≈ 70 GB; 242 GiB free.
   - Recommendation: record sha256 of each DB in the evidence, keep the k=21 pair (or neither) and delete the rest; never let scratch grow unbounded. The verdict artifact must not depend on the DBs after stats are captured.

5. **Does the Phase-10 report replace `docs/benchmark-report.md`?** (RESOLVED — Plan 10-02 prohibitions and Plan 10-04: the phase renders a phase-local `10-BENCHMARK-REPORT.md`; `docs/benchmark-report.md` and the v1.0 renderer are never touched)
   - What we know: that file is the v1.0 milestone report (CRR2044018 substitute, k=31 headline) and its renderer is byte-identity-tested.
   - Recommendation: write a phase-local `10-BENCHMARK-REPORT.md`; do not overwrite the v1.0 report. If the project wants a v2 report in `docs/`, render it separately and state the provenance.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| jellyfish | BENCH-V2-02 comparator | ✓ | 2.3.1 at `/opt/homebrew/bin/jellyfish`, on PATH [VERIFIED: local] | Build 2.3.1 from source (source-only releases) |
| `gzcat` | jellyfish gz pipeline | ✓ | `/usr/bin/gzcat` [VERIFIED: local] | `gunzip -c` (portable) |
| `python3` (PATH) | Harness driver + tests | ✓ | 3.13.11 [VERIFIED: `python3 --version`] | `.venv313/bin/python` (3.13.11) |
| `/usr/bin/python3` | — | ✗ as a harness interpreter | 3.9.6 | Do not use: 47 harness-test errors (Pitfall 9) |
| `.venv313` + `pyrustkmer` | Python surface | ✓ | 0.5.0; module sha256 `6d526431…558ae3` [VERIFIED: import + shasum] | Rebuild: `env -u CONDA_PREFIX VIRTUAL_ENV="$PWD/.venv313" PATH="$PWD/.venv313/bin:$PATH" .venv313/bin/maturin develop --release -m pyo3/Cargo.toml` |
| `target/release/rustkmer` | CLI surface | ✓ | 0.5.0; sha256 `f6ace9f7…c1eae9` [VERIFIED: shasum] | `cargo build --release --locked` |
| CRR1936095 r1 part_001 | Both surfaces | ✓ | 2,785,381,389 B; 34,541,320 reads; sha256 `dae91042…` [VERIFIED: local line count + committed fingerprint] | Re-download (not needed) |
| CRR1936095 r1 part_006 | Both surfaces | ✓ | 2,785,388,289 B; 34,541,320 reads [VERIFIED: local line count] | Re-download (not needed) |
| `/usr/bin/time -l` | Wall + peak accounting | ✓ | macOS BSD time [VERIFIED: local runs] | none needed |
| Disk space | Full artifacts + scratch | ✓ | 242 GiB free on the data volume [VERIFIED: `df`] | Delete per-k artifacts after stats |
| RAM / cores | Full runs | ✓ | 128 GiB, 16 cores; 93% free at research time [VERIFIED: sysctl/memory_pressure] | Stage by k and arm; no concurrent tools |
| `sudo -n purge` | Cold-cache protocol | ✗ (no sudo) | — | Record `cache_state: "unavailable"` per rep (locked decision) |
| CI-class baseline runner | CI baseline regeneration | ✗ by design | — | Not regenerated; dev-host evidence only |
| KMC3 | BENCH-V2-01 | ✗ (absent) | — | **Intended** — descoped; the harness must not warn or fail |

**Missing dependencies with no fallback:** none that block the phase. The only true blocker would be a Python-arm projection above the memory budget (Open Question 1), which is a decision, not a missing tool.

**Missing dependencies with fallback:** sudo purge (honest label); CI-class baselines (explicitly out of scope); KMC3 (descoped).

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json`, and `security_enforcement: true` at ASVS L1. This section names how each success criterion is verified with commands that were executed or are directly runnable in this repo.

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Rust) | `cargo test` (built-in) + proptest/criterion dev-deps |
| Framework (harness) | Python 3 stdlib `unittest`; **415 tests, OK (1 skip)** via `python3 -m unittest discover -s scripts/bench/tests -t .` [VERIFIED: run this session] |
| Framework (Python bindings) | `pytest` in `.venv313` (`pyo3/tests/`; 179 passed / 63 skipped at Phase 9 close) |
| Config file | none needed for the stdlib harness; `pyo3/pyproject.toml` for pytest |
| Quick run command | `python3 -m unittest discover -s scripts/bench/tests -t . && cargo test --locked` |
| Full suite command | `cargo clippy --all-targets -- -D warnings && cargo test --locked && python3 -m unittest discover -s scripts/bench/tests -t . && .venv313/bin/python -m pytest pyo3/tests -q` |

**Known environment note:** `/usr/bin/python3` is 3.9.6 and fails 47 harness tests; `python3` on PATH is 3.13.11 and passes. The one `.venv313`-specific harness failure (`test_n_read_differential.TestInvalidArtifacts.test_missing_extension_exits_2`) is a documented Phase 9 IN-06 fragility, not a phase gate; run the harness suite with `python3`.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BENCH-V2-02 | Slice gate green, fingerprint-bound to part_001 | integration (dev host, jellyfish present) | `python3 scripts/bench/bench.py --parity-only --mode slice --slice-selection head --slice-reads 4000000 --k 21 --threads 16 --hash-size 2G --input <part_001> --parity-reference scripts/bench/baselines/slice_parity.crr1936095.json --out <scratch>/gate.json` → expect `PARITY OK` + `PARITY REFERENCE OK`, exit 0 [VERIFIED this session] | ✅ existing |
| BENCH-V2-02 | Both-parts arm construction (one arm, two inputs) | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestArmConstruction` | ❌ Wave 0 |
| BENCH-V2-02 | Three-tool rotation + t1 exclusion from the verdict | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestVerdict` | ❌ Wave 0 |
| BENCH-V2-02 | Python full worker: two `add_from_fastq` calls accumulate exactly; stats validated; zero counts rejected | unit + integration | `python3 -m unittest scripts.bench.tests.test_python_full_arm` | ❌ Wave 0 |
| BENCH-V2-02 | `max(rss, phys_footprint)` parsing (both lines; pipeline vs direct child) | unit (fixtures) | `python3 -m unittest scripts.bench.tests.test_time_parser` | ✅ extend existing |
| BENCH-V2-02 | Report carries provenance, cache census, KMC3 descope, dev-host statement; re-render byte-identical | unit | `python3 -m unittest scripts.bench.tests.test_phase10_verdict.TestReport` | ❌ Wave 0 |
| BENCH-V2-02 | Full k=21/k=31 verdict from recorded medians | manual-only (dev host; ~4–6 h) — the artifact IS the evidence | `python3 scripts/bench/phase10.py --stage cli --k 21 ...` and `--stage python --k 21 ...`, then the same at `--k 31`, then `--stage render ...` | ❌ by design (milestone artifact) |
| BENCH-V2-02 | No CI baseline modified | repository check | `git status --porcelain scripts/bench/baselines/` → empty; `git diff --name-only -- scripts/bench/baselines/` → empty | ✅ existing |
| BENCH-V2-02 | Provenance on every artifact | unit + artifact check | `validate_provenance` runs before write (`bench.py` `run_bench` pre-write validation; `python_bench.py` `write_json` at :756-765); the Phase-10 doc adds `provenance.python_module` | ✅ extend |
| BENCH-V2-02 | KMC3 descoped, not silently omitted | unit (report text) + REQUIREMENTS.md | assert the rendered report contains the descope sentence; `grep -c "DESCOPED" .planning/REQUIREMENTS.md` = 1 | ✅ requirement text, ❌ report test (Wave 0) |

### Sampling Rate

- **Per task commit:** `python3 -m unittest discover -s scripts/bench/tests -t .` (~10 s) + `cargo test --locked` if Rust changed (this phase should not change Rust).
- **Per wave merge:** the full suite command above; one slice-gate run on the dev host.
- **Phase gate:** full suite green; slice gate green; both `mode=full` artifacts committed with provenance; the report renders byte-identically on re-render; no baseline files touched.

### Wave 0 Gaps

- [ ] `scripts/bench/tests/test_phase10_verdict.py` — both-parts arm construction, three-tool rotation, t1 exclusion, verdict truth table (equality = match), descope/cold-cache/dev-host statements, byte-identical re-render.
- [ ] `scripts/bench/tests/test_python_full_arm.py` — worker stats schema/validation, two-input accumulation exactness (small synthetic fixtures), zero-count rejection, module-sha requirement.
- [ ] Extend `scripts/bench/tests/test_time_parser.py` — `peak memory footprint` fixture (pipeline values 526,532,608 / 1,294,648; direct-child values 1,194,852,352 / 1,192,199,608) and the `max()` rule.
- [ ] Phase-10 arm builder + renderer code in `scripts/bench/bench.py` (or a `phase10` module imported by it) with the tests above.
- [ ] No Rust test gaps: the phase must not change `src/`, `pyo3/src/`, or the fixtures. If it does, the existing `cargo test`/clippy/golden suites are the gate.

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: "high"`. For a benchmark phase the threat surface is **measurement integrity and report truthfulness**, not classic webapp ASVS.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface (local tooling) |
| V3 Session Management | no | None |
| V4 Access Control | no (CI untouched) | The phase regates no CI workflow and writes no baseline |
| V5 Input Validation | yes | `validate_path` screens every path entering the one `sh -c` jellyfish pipeline (`SAFE_PATH_RE = ^[A-Za-z0-9./_-]+$`); `HASH_SIZE_RE`/`DECOMPRESSOR_RE` screen the flags; JSON artifacts are schema- and provenance-validated before write; a malformed `jellyfish stats` raises rather than yielding zero |
| V6 Cryptography | partial | sha256 via stdlib `hashlib` is integrity labeling (input fingerprints, binary/module provenance), not security crypto |
| V8 Data Protection | partial | Artifacts record absolute dataset paths and fingerprints; no credentials or secrets are involved; keep the artifacts repo-local |

### Known Threat Patterns for benchmark/measurement tooling (STRIDE, L1)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Dataset substitution/tampering between runs | Tampering | Input fingerprints (size + sha256 of each part) recorded in every artifact; the slice reference is fingerprint-bound to `dae91042…`; parity is asserted on the measured input |
| Report truthfulness (hand-edited "wins") | Repudiation | Report rendered mechanically from JSON; no measurement literals; byte-identical re-render is the tamper detector; raw per-rep values shown beside medians |
| Comparing non-matched configurations (t1 vs t16, different k/hash size) | Spoofing | One `BenchmarkConfig` derives every command; the verdict filters matched-thread arms; params recorded in the artifact |
| Silent zero-count / empty-database "success" | Tampering | Every arm asserts `distinct > 0`; the jellyfish pipeline uses the correct decompressor; parity gate before timing |
| Command injection via dataset paths into `sh -c` | Elevation of privilege | Only validated absolute paths and harness constants enter the jellyfish pipeline; all other invocations are list-form |
| Cache-state misreporting | Spoofing | `cache_state` derives from the actual purge attempt outcome, never from configuration intent |
| Dev-host number entering a CI baseline | Elevation of privilege | No baseline writes; `git status`/`git diff` checks; the report states dev-host-only |

## Sources

### Primary (HIGH confidence — executed locally this session)

- `jellyfish --version` / `count --help` / `stats --help` / `histo --help` / `dump --help` / `info -j` from the installed **jellyfish 2.3.1** at `/opt/homebrew/bin/jellyfish`.
- Live parity on real CRR1936095 data (200k head reads of part_001): jellyfish vs rustkmer at k=21 = 16,417,180 distinct / 25,967,840 total; k=31 = 17,362,351 / 23,967,840; `PyCounter` over the same `.gz` matched exactly.
- CLI scaling/memory probes: 2M random reads → 130,282,421 distinct, 8.88 GB RSS, 6.57 s; 5M → 256,606,202 distinct, 17.52 GB, 12.94 s; 20M → 537,770,176 distinct, 35.71 GB, 41.90 s (all k=21, t16, canonical).
- Python memory probes: 20M distinct → 1.707 GB; 40M → 3.438 GB; two 20M-distinct calls (40M union) → 2.949 GB.
- `/usr/bin/time -l` behavior: pipeline `maximum resident set size` 526,532,608 B vs `peak memory footprint` 1,294,648 B; direct rustkmer 1,194,852,352 vs 1,192,199,608 B.
- Slice gate run: `PARITY OK distinct=229694874 total=519271168` + `PARITY REFERENCE OK … bound to source dae91042e42c…`, exit 0; emitted `.jf` = 2,296,950,252 B for 229,694,874 distinct.
- Dataset: both parts 138,165,280 lines each (34,541,320 reads each); part_001 sha256 `dae91042…` (committed reference); part_006 2,785,388,289 B.
- Harness suite: `python3 -m unittest discover -s scripts/bench/tests -t .` → 415 tests OK (1 skip); `.venv313` suite has the known IN-06 failure; `/usr/bin/python3` (3.9.6) fails 47 tests.
- Repo reads: `scripts/bench/bench.py` (protocol 1244, jellyfish 216/676, provision 631, pinned 653, renderer 1875), `scripts/bench/python_bench.py` (785, 1069), `src/count/engine.rs` (413, 505, 604), `src/hash/table.rs` (19, 22, 43, 45, 775), `src/hash/local.rs` (103, 105), `src/cli/args.rs` (53–54), `src/io/fastq.rs` (78), `src/cli/commands/count.rs` (180–270), `.planning/config.json`.

### Secondary (MEDIUM confidence — committed project artifacts)

- `.planning/milestones/v1.0-phases/04-benchmark-validation/04-RESEARCH.md` — v1.0 invocation recipe (`-s 10G`, gzcat pipe, 3 counterbalanced reps, parity gate).
- `04-results-full-k21.json` / `04-results-full-k31.json` — v1.0 medians: k=21 rustkmer 505.77/494.14 s vs jellyfish 97.26 s (46.84 GiB); k=31 rustkmer 494.19/485.89 s vs jellyfish 843.02 s (84.00 GiB).
- `docs/benchmark-report.md` — v1.0 methodology block (cache census, `-s 10G`, decompression asymmetry, harness commit).
- `.planning/phases/09-python-parity/09-VERIFICATION.md` and `evidence/python_bench_after_d2.json` — Phase 9 Python measurement discipline and the 1M-read control (73,476,107 distinct, 6.36–6.47 GB RSS).
- `.planning/phases/05-measurement-regression-harness` / `08-output-pipeline-rkdb-v2-parity` evidence — pinned head-4M counts and the validated RSS model points (12.04 / 17.97 GB).

### Tertiary (LOW confidence — not relied on)

- Web search on macOS `/usr/bin/time -l` rusage semantics returned no authoritative source; the local measurements above are the evidence.
- Any full-scale wall/RSS number in this document not marked "measured" is an explicit extrapolation (Assumptions Log A1–A3).

## Metadata

**Confidence breakdown:**
- Standard stack / tool mechanics: **HIGH** — every command, flag, parser, and memory measurement was executed locally this session; the slice gate ran green end-to-end.
- Architecture/seams: **HIGH** — the exact code locations that must change were read and cited; the v1.0 protocol is committed and tested.
- Full-scale projections: **MEDIUM** — the distinct count and memory models are extrapolations from measured sub-samples (20M reads max); the phase's own CLI preflight converts them into measurements before the Python arm.
- Pitfalls: **HIGH** — most were reproduced or root-caused locally (multi-member gzip history, zcat variant, footprint semantics, `--size` arithmetic, Python per-distinct cost, slow stats).

**Research date:** 2026-11-13
**Valid until:** 2026-12-13 for the tool/protocol facts (stable); re-verify the binary/module shas and `df` before the measurement week. Re-check the memory projection after the CLI preflight — it supersedes this document's estimate.

