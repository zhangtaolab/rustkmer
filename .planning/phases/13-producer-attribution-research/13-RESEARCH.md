# Phase 13: Producer Attribution Research - Research

**Researched:** 2026-11-17
**Domain:** Full-scale measurement engineering — producer stage attribution (inflate / parse / extract / route-send) on the shipped rustkmer count engine, predicted-win sizing, and the D3 go/no-go gate memo
**Confidence:** HIGH — every load-bearing fact was verified live this session (binary sha256, disk, dataset sizes, profiling build, probe execution) or read verbatim from committed planning artifacts; the measurement design itself is inherited pre-specified from the milestone research (arms A-D, controls, sizing model)

## Summary

Phase 13 is a measurement-only phase that answers one question at full scale on the SHIPPED engine: where does the producer wall actually go, and does parallel extraction's predicted win justify Phase 14? The phase installs **zero new dependencies** and lands **zero Rust changes** — its deliverables are a harness-built driver script (the `merge_characterize.py` pattern), evidence JSONs, and a committed gate memo (`13-GATE-MEMO.md` + `13-ATTRIBUTION.json` pattern per D-02).

The single most consequential planning fact, discovered by live verification this session: **the D-03 fingerprint gate fires the RE-MEASURE branch.** The current release binary's sha256 (`4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b`) differs from v2.0's recorded fingerprint (`8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240d5ec74fc87c3d23`). The delta is real source difference, not a stale rebuild: 9 Rust files changed between the v2.0 fingerprint commit (97b3f01, mid-Phase-10) and HEAD, all fmt/clippy-class from the Phase 10 code-review rounds (48 insertions / 34 deletions, reviewed line-by-line this session — reformatting only). Per D-03's deterministic rule, the driver re-measures the base walls fresh at full scale before any differential math. Practically this costs nothing extra: **arm A (stock gzip, 3 reps × both k) IS the fresh base measurement** — the memo cites arm A's medians as the base and keeps the v2.0 walls as named corroboration source runs, with the fingerprint difference disclosed.

The second load-bearing fact: the stock `rustkmer count` CLI does **not** expose the profiling diagnostics. `--profile` exists only on the `fuzzy`/`prefix` commands; `EngineDiagnostics` (`producer_nanos`, worker `busy_nanos`) is read by exactly one committed artifact — `examples/engine_probe.rs` — which is **hardcoded to k=21**. The probe builds clean (`cargo build --release --locked --features profiling --example engine_probe`, 15.1 s incremental) and runs on both plain and gzip FASTQ, emitting the diagnostics JSON. Consequence: arm C (stage sub-timers) at k=21 uses the stock probe verbatim; arm C at k=31 and arm D (null consumer) require **research-local probe variants** materialized by the driver outside the repo via the established `microbench_Cargo.toml` / `contention_bench.py` precedent (path dependency on rustkmer, `@REPO_ROOT@` substitution, workspace-exempt, never committed). This is D-01-compliant: nothing lands in `src/`; the headline numbers still come from arms A/B + control, with arm C/D as the within-producer decomposition cross-check.

Session budget is modest and matches the CONTEXT estimate: 4 arms × 2 k × 3 reps ≈ 24 heavy runs (~145-180 s each ≈ 1.2-1.6 h) plus cheap shell-level pure-read controls, decompression (~15-30 min), and the memo. Disk is ample: 428 GiB free (verified) against ~60 GB plain inputs + ~23 GB transient output per rep.

**Primary recommendation:** Build one stdlib-only driver script (`scripts/bench/phase13.py` naming lineage is the planner's discretion per D-01) that materializes its probe binaries outside the repo, runs the counterbalanced A/B/C/D + control arm matrix at both k with 3 reps, computes the attribution table and the two-ceiling predicted-win model from recorded evidence only, and writes the evidence JSON + memo — with the D3 numeric bar pre-registered BEFORE any measurement runs: D-05 fixes a **predicted full-wall improvement >= 10.0% on the conservative (efficiency-derated, E = 0.5) model at 16 extractor threads, applied at both k** (see Open Questions 1, RESOLVED).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Implementation Decisions (Locked)

- **D-01 (Measurement Vehicle):** Arms A-D are driven by a **harness-built driver script** (the `merge_characterize.py` pattern: stdlib-only, provenance on every run, evidence JSON per arm-k, fail-loud parsing) — not hand-run CLI invocations and not a Rust-side instrumentation addition. The headline numbers come from the plain-vs-gzip differential + pure-read control; `--features profiling` stage sub-timers (arm C) are the cross-check, not the headline source. Both k for every arm. — Reversibility: reversible — a code artifact + evidence JSONs.
- **D-02 (D3 Gate Memo):** The go/no-go decision is recorded as a **committed memo in the phase directory** (evidence-JSON + markdown pattern, e.g. `13-GATE-MEMO.md` + `13-ATTRIBUTION.json`): the memo names both ceilings, cites every input number to a named full-scale source run, and states GO (Phase 14 executes) or NO-GO (PEXT-03/04 remain unexecuted by recorded decision). ROADMAP §Phase 14 carries the conditional annotation pointing at the memo. — Reversibility: costly — the memo is the gate input for Phase 14's existence.
- **D-03 (Full-Scale Input Sources):** **Fingerprint-gated reuse of v2.0 walls:** first compare the current release binary's sha256 against v2.0's recorded fingerprint — if identical, v2.0's measured walls (CLI 144.69 s k=21 / 147.08 s k=31; Python 165.05 s / 178.22 s) are cited directly as the base; if it differs, the driver re-measures the base walls fresh at full scale before any differential math. PEXT-01's fingerprinted-builds requirement applies to every run either way.
- **D-04 (Session Scale & Input Lifecycle):** **Each arm-k runs 3 reps.** The plain (pre-decompressed) FASTQ inputs are **decompressed once into a dedicated directory outside the repo** (data-adjacent, e.g. `/Users/forrest/Data/data/illumina/CRR1936095-plain/`, ~60 GB for six parts), provenance-recorded like every artifact, and **deleted after the memo lands** (the memo cites the recorded evidence, not the bytes). Disk arithmetic is checked before decompression against current free space.

### Carried Constraints (locked, not re-decided)
- No Rust changes land in this phase; measurement-only (binary fingerprint stability).
- Full scale only — no slice-scale number feeds the gate (PEXT-01).
- The six independent gzip parts give a producer-per-file topology ×6 — the sizing model notes this as Phase 14's spread surface if GO.
- Provenance on every run: sha256 of binary + inputs, command line, honest cache_state (established pattern).

### Claude's Discretion
- Driver script CLI shape/name and evidence-JSON schema (follow merge_characterize.py + phase11.py evidence patterns).
- Stage sub-timer invocation details for arm C (profiling feature flags, output capture).
- Null-consumer construction (arm D) — minimal-work consumer that isolates read+inflate cost.
- Exact memo structure (both ceilings, arithmetic, citation table).
- Whether the attribution table records per-part breakdowns as context (the ×6 topology suggests per-part spread is worth recording as context for Phase 14 sizing).

### Deferred Ideas (OUT OF SCOPE)
- zlib-rs feature switch — fires only if arm-C/attribution measured inflate ≥ ~20% of producer wall (separate decision at Phase 14 planning if it ever fires).
- Per-part attribution ×6 as a headline (vs context) — deferred to planning; the D3 gate needs the aggregate stage table first.
- Producer-per-file parallel topology design — Phase 14 territory if GO.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PEXT-01 | Producer stage attribution measured at FULL scale on the shipped engine, both k, fingerprinted builds — stage table (inflate / parse / extract / route-send) via plain-vs-gzip differential plus pure-read control; slice-scale numbers and pre-Phase-7 profiles never feed the gate | Arm matrix A/B/C/D + control fully specified (§Architecture Patterns); probe instrument verified live (builds, runs, emits JSON); stock-CLI limitation discovered (no diagnostics on count; probe is k=21-only) with the research-local materialization path verified as established precedent; fresh-base re-measure branch confirmed FIRING (fingerprint differs) |
| PEXT-02 | Predicted-win model names both ceilings (parallelizable share × worker-side scaling), every input number cited to a named full-scale source run; D3-gate go/no-go recorded as the research deliverable | Model shape with measured inputs documented (§Attribution Arithmetic): parallelizable share from arm D, worker-side ceiling from aggregate `busy_nanos` (engine.rs:1320-1347 wraps the increment loop), composition correction (count-phase vs output-phase) from A − probe wall; every number traceable to an evidence-JSON run record; memo structure per D-02; NOTE: the numeric D3 bar is pre-registered in CONTEXT D-05 (predicted full-wall improvement >= 10.0% on the conservative derated model, E = 0.5, 16 extractor threads, both-k conjunction) — Open Question 1 is resolved before measurement |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Arm A/B stock runs (wall differentials) | Harness driver (Python stdlib) | Stock `rustkmer` release binary | CLI accepts `-i f1 f2` multi-input (args.rs:25); driver only invokes + measures via `/usr/bin/time` |
| Pure-read controls | Harness driver (shell-level) | — | `cat <part> > /dev/null` read-volume calibration; no engine involvement |
| Arm C stage sub-timers | Research-local probe binary (engine_probe at k=21; materialized microbench variant at k=31) | `--features profiling` EngineDiagnostics | Diagnostics exist only in the library API; the stock count CLI never prints them (verified: no diagnostics reference in `src/cli/commands/count.rs`) |
| Arm D null consumer | Research-local probe binary (materialized microbench) | Public `rustkmer::kmer::extract::for_each_window` | Parse+encode-discard is not expressible via the CLI; `for_each_window` is public (doctest-verified signature) so a path-dep microbench can time it |
| Attribution math + predicted-win model | Harness driver (pure functions) | Evidence JSON records | All inputs are recorded run values; model is deterministic arithmetic over them — unit-testable on fixtures |
| D3 gate memo | Committed markdown + evidence JSON (D-02) | — | The memo is the phase deliverable that gates Phase 14's existence |

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3.11+ stdlib | 3.11+ (host venvs) | Driver script — no third-party imports (bench-harness stdlib-only contract) | Established harness rule (merge_characterize.py:48-49) |
| `scripts/bench/bench.py` primitives | in-tree | `fingerprint`, `binary_provenance`, `parse_time_output`, `attempt_cache_purge`, `BenchmarkConfig`, `rustkmer_count_cmd`, `reduce_arm` | 398-test-covered protocol library; every phase since 11 imports from it |
| `/usr/bin/time -l` (darwin) | system | Wall + peak RSS/footprint — the only permitted clock | Harness-internal clocks banned (bench.py measure semantics) |
| `examples/engine_probe.rs` (k=21) | committed, Phase 7 (07-04) | Reads `EngineDiagnostics` — the one committed diagnostics reader | Build command documented in its module docs; verified live this session |
| `--features profiling` build | in-tree feature | Compiles `EngineDiagnostics`/`busy_nanos` into the engine | Default builds untouched; verified 15.1 s incremental build |
| Research-local microbench materialization | `microbench_Cargo.toml` + `contention_bench.py` precedent | k=31 probe + null-consumer probe, built OUTSIDE the repo from a path dep | Phase-5 precedent (`@REPO_ROOT@` substitution, `[workspace]` exemption, microbench-only deps) — lands nothing |
| flate2 gzip backend (in engine) | locked in Cargo.lock | The inflate stage being measured — stock build, no zlib-rs switch | zlib-rs fires only if inflate ≥ ~20% (deferred decision) |

### Supporting
| Component | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `scripts/bench/output_stage.py` `rotation_schedule` | in-tree | Counterbalanced arm-order rotation per rep | Every measured rep (cache-warmth defense, Pitfall 13) |
| `scripts/bench/prepare_inputs.py` patterns | in-tree | Manifest/provenance/`refuse_repo_root`/`run_command` patterns for the plain-inputs decompression stage | D-04 decompression + provenance recording |
| `gunzip -c` / `cat > /dev/null` | system | Decompression; pure-read controls | Arm B inputs + read-volume calibration |
| `pmset -g therm` | system (no sudo needed) | Thermal state per rep | Pitfall 5 confound recording; verified readable this session |
| stdlib `unittest` | 3.11+ | Driver unit tests in `scripts/bench/tests/` | Harness suite pattern (`python3 -m unittest discover -s scripts/bench/tests -t .`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Research-local microbench for k=31 probe | Patching `engine_probe.rs` in-tree to take k from argv | Touches the tree → dirty source → muddies fingerprint discipline; the committed probe's docs pin its shape. Materialized-outside pattern keeps `git status` clean and lands nothing |
| Python surface arm runs (re-measure 165.05/178.22 base) | CLI-only arms + cite Python walls as context | Python shares the same engine (win transfers proportionally); re-measuring needs a profiling-built wheel + maturin session for a context-only number. Planner discretion — see Open Question 3 |
| `samply` profiles (Phase-5 style) | Arms A-D instrument design | Self-time tables confound kernel wait with stage cost (Pitfall 9's exact warning); on-CPU stage timers are the honest instrument |
| Per-part ×6 arms (all six parts) | Pair-only arms (pinned arrangement) | v2.0 walls are pair-based; per-part ×6 is context (Deferred). Disk supports either; planner decides decompression scope — see Open Question 2 |

**Installation:**
```bash
# Nothing to install. Zero new packages, zero dependency changes.
# The only builds are in-tree, from the locked graph:
cargo build --release --locked                        # stock release binary (rebuild clean from HEAD before the fingerprint gate)
cargo build --release --locked --features profiling --example engine_probe   # k=21 probe (verified 15.1 s)
# k=31 / null-consumer probes: materialized by the driver into /tmp scratch — see Architecture Patterns.
```

**Version verification:** No external packages — nothing to verify against a registry. Toolchain verified live: `rustc 1.101.0-nightly (07e526db9 2026-10-19)` — byte-identical to the toolchain recorded in v2.0's provenance block, so the fingerprint delta is source delta, not toolchain delta.

## Package Legitimacy Audit

> This phase installs **no external packages** (D-01 stdlib-only driver; zero dependency changes; all builds from the locked Cargo.lock graph). The legitimacy gate is trivially satisfied: nothing to audit, nothing to remove, nothing to flag.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | No packages installed by this phase |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
                       ┌──────────────────────────────────────────────────────┐
                       │  driver script (stdlib-only, D-01 pattern)           │
                       └──────────────────────────────────────────────────────┘
                          │ prep                │ probe materialization
                          ▼                     ▼
        [gunzip once → plain inputs]   [/tmp scratch: microbench manifest + .rs
        CRR1936095-plain/ (D-04,        variants (k31 probe, null consumer);
        deleted post-memo)              rustkmer path dep via @REPO_ROOT@;
                          │             fingerprinted, never committed]
                          │                     │
                          ▼                     ▼
        ┌──────────────────────── ARM MATRIX (3 reps × both k, counterbalanced) ────────────────────┐
        │                                                                                           │
        │  A stock-gz (CLI)      B plain (CLI)        C sub-timers (probe)     D null consumer      │
        │  rustkmer count -i     rustkmer count -i    engine_probe (k21)       microbench probe     │
        │  gz_p1 gz_p2 -o scr    plain_p1 plain_p2    + k31 variant            parse+encode→discard │
        │  → wall_a (full:       → wall_b (same       → producer_nanos,        → parse+extract time │
        │    count+sort+write)     shape, no inflate)   busy_nanos per worker    (no route/tables)   │
        │                                                                                           │
        │  CONTROL (shell, cheap): cat gz_p1 > /dev/null ; cat plain_p1 > /dev/null                 │
        │  → read_gz, read_plain — the byte-volume correction δ = read_gz − read_plain              │
        └───────────────────────────────────────────────────────────────────────────────────────────┘
                          │ every run: /usr/bin/time -l, cache_state, sha256(binary+inputs),
                          │ command line, thermal — evidence JSON per arm-k (D-01/D-04)
                          ▼
        [13-ATTRIBUTION.json]  ← stage table: inflate = (A−B−δ); parse+extract = D;
                                route-send = producer_plain − (parse+extract);
                                output/sort/write = wall_a − probe count-phase wall
                          ▼
        [predicted-win model: BOTH ceilings]  ──►  [13-GATE-MEMO.md: GO / NO-GO (D-02)]
              parallelizable share (arm D) ×          cites every number to a named run
              min(worker-side scaling ceiling,        fresh base = arm A medians (D-03
              measured producer scaling)              re-measure branch, FIRING)
                          │
                          ▼
              GO → Phase 14 executes  │  NO-GO → PEXT-03/04 unexecuted by recorded decision
```

### The Arm Matrix (the phase's spine)

| Arm | Instrument | Input | Measures | Feeds |
|-----|-----------|-------|----------|-------|
| **A — stock** | `rustkmer count -k {k} -C --threads 16 -o <scratch> -i gz_part1 gz_part2` | pinned pair, gzip | full CLI wall incl. sort+write — **the fresh base wall** (D-03 re-measure) | base wall; inflate differential; full-wall composition |
| **B — pre-decompressed** | same command shape, plain inputs | pinned pair, plain | identical pipeline minus inflate | A−B−δ = inflate share (headline) |
| **CONTROL — pure read** | `cat <input> > /dev/null` (driver-timed, /usr/bin/time) | both input types | raw read volume per input type | δ = read_gz − read_plain byte-volume correction (Pitfall 9's confound) |
| **C — stage sub-timers** | `engine_probe` (k=21, committed) + materialized k=31 variant; per part | each part, gz AND plain | `producer_nanos` vs `wall_nanos`, per-worker `busy_nanos` | producer share of count phase; instrument-level cross-check: producer(gz) − producer(plain) ≈ inflate |
| **D — null consumer** | materialized microbench: bio record loop + `for_each_window(seq, k, canonical, discard)` | each part, plain | parse + extract time with routing/tables/sends removed | parse+extract share (the parallelizable share); route-send = producer_plain − D |

All arms at FULL scale (Pitfall 14: no slice number feeds the gate). A rehearsal at tiny-fixture scale proves the driver end-to-end before round 0 (the 11-06/11-07 dress-rehearsal precedent) — rehearsal numbers never appear in the memo.

### Research-Local Probe Materialization (D-01-compliant arm C/D instrument)

The established pattern (`scripts/bench/contention_bench.py` + `.planning/research/profiling/microbench_Cargo.toml`, Phase 5):

1. Driver writes `Cargo.toml` + probe `.rs` into `/tmp` scratch (outside the repo — `refuse_repo_root` guard applies).
2. Manifest: `rustkmer = { path = "@REPO_ROOT@" }` with the driver substituting the resolved repo root; `[workspace]` empty-table exemption; microbench-only deps already in the production lockfile (serde_json; add nothing else — parse via `bio` is available through rustkmer's re-exports only if public, else hand-roll the 4-line FASTQ record split **only for the null consumer**, never as the parse-stage instrument... actually: the parse-stage instrument should use `bio::io::fastq::Reader` exactly as `count_file_inner` does — add `bio` as a microbench-only direct dep, same class as the precedent's `dashmap`).
3. `cargo build --release --locked --manifest-path <scratch>/Cargo.toml` — fingerprint the resulting binary per run.
4. Nothing lands in the repo: `git status` stays clean, the stock binary's fingerprint stays meaningful, and the phase honors "no Rust changes land".

### Evidence & Memo Structure (D-01/D-02 patterns)

- **Evidence JSON per arm-k** (`13-ATTRIBUTION.json`): follows `merge_characterize.py`'s doc shape — `schema_version`, `kind` (its own kind, never a fork of bench results schema v1), per-run records `{arm, k, rep, wall_s, peak_bytes, cache_state, command_line, binary_sha256, input_sha256s, probe_output_json (arms C/D), thermal, created}`, plus `attribution` (stage table) and `predicted_win` (both ceilings) blocks computed only from recorded values.
- **Memo** (`13-GATE-MEMO.md`): (1) decision + the pre-registered bar; (2) stage-attribution table at both k with per-cell citations to run records; (3) predicted-win model — both ceilings named, arithmetic shown, every input cited; (4) fresh-base statement (arm A medians) + v2.0 corroboration with the fingerprint delta disclosed; (5) D-03 gate provenance (both sha256s); (6) what would need to be true to revisit (on NO-GO); (7) decompression/lifecycle record (D-04) with deletion note.
- **Exit-code contract** (phase10/phase11 precedent): 0 = memo recorded (either outcome is a valid result), 1 = reserved decision code if the planner wants a GO/NO-GO machine-readable split, 2 = infrastructure/invalid (no artifact written).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wall + peak RSS measurement | Python timers, psutil polling | `/usr/bin/time -l` + `bench.parse_time_output` | Harness-internal clocks banned by the README; units-pinned parser already battle-tested |
| Binary/input provenance | ad-hoc shasum calls | `bench.fingerprint` + `bench.binary_provenance` (records git_commit, git_dirty, toolchain, platform) | git_dirty disclosure is exactly what D-03's gate needs |
| Cache-state honesty | assuming cold/warm | `bench.attempt_cache_purge` | sudo purge unavailable on this host → records `unavailable`; rotation+cooldown are the real defense (Pitfall 13) |
| Arm-order counterbalancing | hand-rolled ordering | `output_stage.rotation_schedule` | Pre-built, tested rotation; the thermal-order-bias defense |
| Medians + CV + spread | custom stats | `bench.reduce_arm` | Same reduction as every prior verdict; cv_warning semantics established |
| Path/safety guards | manual checks | `prepare_inputs.refuse_repo_root`, `run_command` (list-form, no shell) | T-04-03 validation class; scratch outside repo is a standing rule |
| Diagnostics JSON parsing | regex on prose | engine_probe already emits one JSON object — `json.loads` it | Probe output is machine-format by design (verified live) |
| Thread-count sanity | trusting flags | record `--threads 16` + the 2N+1 context | Thread-count disclosure per methodology discipline (Pitfall 3 class) |

**Key insight:** every measurement primitive this phase needs already exists in `scripts/bench/` behind tested functions — the driver is glue + attribution math + probe materialization, not a new harness.

## Runtime State Inventory

> Omitted: this is a measurement-only phase — no rename/refactor/migration of stored strings, service config, OS registrations, secrets, or build artifacts. Ephemeral measurement state (plain inputs, scratch outputs, probe binaries) is lifecycle-managed per D-04 and the scratch discipline, and is documented under Environment Availability / disk arithmetic instead.

## Common Pitfalls

### Pitfall 1: Citing v2.0 walls as the base after the fingerprint gate fired (D-03 violation)
**What goes wrong:** The memo computes predicted-win percentages against 144.69/147.08 s even though the current binary's sha256 differs — the gate's re-measure branch exists precisely to prevent this.
**Why it happens:** The v2.0 walls are the most-cited numbers in the planning corpus; the fmt-class source delta looks semantically irrelevant.
**How to avoid:** The driver computes the gate itself (compare sha256s, record both) and REFUSES to emit a memo whose base is not arm A's own medians when the gate fired. The 144.69/147.08 numbers appear only as corroboration, labeled with their (different) fingerprint.
**Warning signs:** Any memo percentage whose denominator is a v2.0 wall while the binary sha256 block shows a mismatch.

### Pitfall 2: Kernel-wait / self-time tables read as stage cost (Pitfall 9's core warning)
**What goes wrong:** A `samply`-style profile says "extraction is hot" and the memo sizes the win on it — but self-time includes wait/spin/syscall time, and pre-Phase-7 profiles describe the old DashMap engine anyway.
**Why it happens:** Profiles are the familiar instrument; on-CPU stage timers feel like new instrumentation.
**How to avoid:** Headline shares come only from wall differentials (A−B−δ) and probe-recorded on-CPU timers (producer_nanos/busy_nanos are Instant-based spans, engine.rs:804-805, 1320-1321 — no sampling, no wait contamination). No profile-derived number enters the memo.
**Warning signs:** Any memo citation to `.planning/research/profiling/` Phase-5 breakdowns or a sampling profile.

### Pitfall 3: Byte-volume confound — plain inputs read ~3× the bytes
**What goes wrong:** A−B is reported as "inflate share" without correcting for the plain arm reading more disk bytes; on a busy volume this inflates the inflate share and could push it toward the ~20% zlib-rs gate spuriously.
**Why it happens:** The differential is the headline; the correction needs its own control arm and it is cheap to skip.
**How to avoid:** Pure-read control at both input types, same rep discipline; δ = read_gz − read_plain subtracted from A−B before the share is computed; δ reported in the memo regardless of size (honesty over rounding).
**Warning signs:** Attribution table has no control row; inflate share quoted with no δ term.

### Pitfall 4: Cache-warmth bias between arms (Pitfall 13)
**What goes wrong:** Decompression warms the page cache for exactly the files arm B then reads; B wins partly on cache and the inflate share is inflated. Repeat reps read warm while first reps don't.
**Why it happens:** The confound is structural (B needs pre-decompressed files), not a mistake.
**How to avoid:** Counterbalanced arm order per rep via `rotation_schedule`; honest `cache_state` per rep (`unavailable` is the accepted answer on this host); cooldown scaled to rep duration (~15-30 s for ~150 s reps); `pmset -g therm` recorded per rep.
**Warning signs:** One arm winning every rep regardless of order; attribution deltas shrinking after counterbalancing is introduced.

### Pitfall 5: Slice-scale contamination of the gate (Pitfall 14)
**What goes wrong:** Rehearsal/slice numbers (driver debugging, probe smoke tests) leak into the memo as sizing inputs.
**Why it happens:** Full-scale arms are ~150 s each; debugging naturally runs small first.
**How to avoid:** Evidence records carry a `scale` field; the memo-derivation function refuses records whose scale is not `full`; rehearsal runs write to a separate rehearsal document (the 11-LADDER/REHEARSAL split precedent).
**Warning signs:** A memo input number whose source run record lacks the full-scale input paths.

### Pitfall 6: Arm C/D probes are different binaries — fingerprint discipline
**What goes wrong:** Probe-derived shares get attributed to "the shipped engine" while the probe binary was never fingerprinted, or worse: a probe experiment leaves the repo dirty and invalidates the stock binary's fingerprint comparison.
**Why it happens:** Three distinct binaries exist in this phase (stock CLI, stock probe, research-local probes).
**How to avoid:** Every run record carries its own `binary_sha256`; probe materialization lives in /tmp scratch (never in-tree); the D-03 gate compares only the stock release binary rebuilt clean from HEAD (`binary_provenance.git_dirty` must be false).
**Warning signs:** A run record without binary_sha256; `git status` dirty after probe builds; probe shares labeled "shipped engine" without naming the probe binary.

### Pitfall 7: Composition confusion — probe wall ≠ CLI wall
**What goes wrong:** The memo treats the probe's wall_nanos (count phase only: open→parse→extract→route→flush, no sort/write — engine.rs:803-871 + probe never writes .rkdb) as comparable to the CLI's 144.69 s wall (count + sort + write), inflating or deflating the predicted full-wall win.
**Why it happens:** Both are "the count run".
**How to avoid:** The model splits composition explicitly: output/sort/write share = wall_a − probe count-phase wall (both measured at full scale); predicted full-wall win applies the parallelizable share only to the count-phase term. The probe counts one file per invocation (fresh engine) while the CLI counts the pair in one engine — record this topology difference in the methodology.
**Warning signs:** A predicted win computed as a fraction of 144.69 s with no composition term; probe walls summed with CLI walls.

### Pitfall 8: engine_probe is k=21-hardcoded — k=31 arm C silently runs k=21
**What goes wrong:** Someone runs the committed probe for the k=31 arm and records k=21 diagnostics as k=31 attribution (probe's `EngineConfig::new(21, true, threads, 1_000_000)` — verified, engine argument parsing has no k parameter).
**Why it happens:** The probe exists and runs; its k is invisible in the output JSON.
**How to avoid:** The k=31 probe is a materialized variant that takes k from argv and asserts the value in its output JSON; the driver cross-checks `probe_output.k == arm.k` fail-loud. Same for canonical: the probe hardcodes `canonical=true`, matching the arms' `-C` — keep it that way and record it.
**Warning signs:** Identical producer shares at both k; probe JSON without a k field.

### Pitfall 9: Plain-input lifecycle — decompressed files outliving the memo
**What goes wrong:** ~19.5-60 GB of plain FASTQ quietly persists after the phase, or gets deleted BEFORE the evidence JSON records their provenance (making the recorded runs unreproducible-in-principle).
**Why it happens:** D-04's deletion is manual wrap-up work; provenance feels already-done once the runs finish.
**How to avoid:** The driver records plain-input sha256s + sizes at decompression time; deletion is an explicit plan task AFTER the memo commit (D-02 order: evidence commits → memo → cleanup, the 12-03 precedent); deletion recorded in the wrap-up.
**Warning signs:** `CRR1936095-plain/` present after phase close; evidence JSON missing plain-input fingerprints.

## Code Examples

### Verified probe build + run (live-verified this session)
```bash
# Build (15.1 s incremental, exit 0):
cargo build --release --locked --features profiling --example engine_probe

# Run on plain and gzip FASTQ (one file per invocation; k=21 canonical hardcoded):
target/release/examples/engine_probe tiny.fq fastq 2
# {"input":"tiny.fq","producer_nanos":93750,"threads":2,"wall_nanos":133459,
#  "workers":[{"batches":3,"busy_nanos":16416},{"batches":5,"busy_nanos":16042}]}
target/release/examples/engine_probe tiny.fq.gz fastq 2
# {"input":"tiny.fq.gz","producer_nanos":88666,"threads":2,"wall_nanos":120334, ...}
```
Source: `examples/engine_probe.rs:1-97` (module docs pin the build command; `EngineConfig::new(21, true, threads, 1_000_000)` at :45 — k hardcoded).

### Producer bundle stages (what the attribution table decomposes)
```text
count_file_inner (src/count/engine.rs:803-871):
  1. DefaultCompressedFileReader::open_compressed(path)   # read + inflate  (:806-812)
  2. bio::io::fastq::Reader record loop                   # parse           (:835-842)
  3. count_sequence(record.seq())                         # extract + route (:1001-1040)
       for_each_window(seq, k, canonical, |value| {
           state.route_key(value, layout, keys_per_batch) # route+send INSIDE the emit closure
       })
  producer_nanos span ends BEFORE flush (:857-864) — flush wait is not producer time.
Worker busy_nanos wraps owned_table + increment loop per batch (:1320-1332, 1341-1347).
```

### Attribution arithmetic (all inputs from recorded runs)
```python
# per k, from evidence records (illustrative shape — exact schema is planner discretion):
inflate_s   = (median_A - median_B) - (median_read_gz - median_read_plain)   # δ-corrected headline
parse_extract_s = median_D_plain                                             # null-consumer probe
route_send_s    = producer_plain_probe_s - parse_extract_s                   # within-producer residual
output_stage_s  = median_A - count_phase_wall_probe_s                        # composition split
# predicted win (both ceilings, PEXT-02):
parallelizable_share = parse_extract_s / count_phase_wall_probe_s
serial_floor         = (inflate_s + route_send_s) / count_phase_wall_probe_s
# new_wall >= max(serial_terms + parallelizable/E, worker_busy_total/S)  — E = extraction
# scaling efficiency at M extractors, S = worker-side scaling ceiling; worker_busy_total
# is measured (aggregate busy_nanos), S is bounded by the MEM-safe worker count and stated
# as the ceiling the memo must not assume beyond.
```

### Driver skeleton (pattern inheritance from merge_characterize.py)
```python
# measured_run: /usr/bin/time + parse_time_output, fail-loud (merge_characterize.py:146-167)
# rotation:     output_stage.rotation_schedule(arm_names, reps)
# cache_state:  bench.attempt_cache_purge() -> honest label per rep# guards:       prepare_inputs.refuse_repo_root(scratch); ensure_free_space before decompress
# evidence:     write_doc(indent=2, sort_keys=True) + upsert-per-arm-k + kind/schema validation
# exit codes:   0 recorded / 2 infrastructure (phase10/phase11 contract)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase-5 sampling profiles (samply, self-time tables) | `--features profiling` on-CPU stage spans (`producer_nanos`, `busy_nanos`) | v2.0 Phase 7 | Wait-free attribution instrument; sampling profiles are stale evidence for the current engine |
| Slice-scale wall composition (4M records: sort/write dominated) | Full-scale attribution arms | this phase | Slice numbers cannot feed the gate (Pitfall 14); full-scale composition measured fresh |
| v2.0 walls as "the" baseline | Fresh arm-A base (fingerprint-gated, D-03) | this session's verification (gate FIRES) | Memo cites fresh medians; v2.0 walls become disclosed-fingerprint corroboration |
| Estimated inflate ~13% (~19 s of 144.69 s, research ballpark) | Measured δ-corrected differential | this phase | The ~19 s figure is a research estimate, NOT a citable source run — the memo must use the measured value |

**Deprecated/outdated:**
- `docs/benchmark-report.md` v1.0 +420% headline: superseded (banner landed Phase 11); never cite.
- The "~16 GiB vs ~5.2 GB" byte-volume sentence in PITFALLS.md Pitfall 9: written when the dataset description said two parts ~5.2 GB; the pinned pair is ~5.57 GB gz (sizes verified this session). Same confound, update the arithmetic, keep the control.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Plain-FASTQ size ≈ 3.1-3.5× gzip (pair ≈ 17-19.5 GB; six parts ≈ 52-60 GB); exact bytes recorded at decompression | Environment Availability / disk arithmetic | Low — disk check re-runs against measured size before decompression (D-04); 428 GiB makes any plausible error harmless |
| A2 | The fmt/clippy-class binary delta measures within noise of v2.0 walls (fresh base ≈ 144.69/147.08) | Summary / D-03 consequence | Low — the hypothesis is TESTED by the fresh base measurement itself; a material deviation is a recorded finding that changes the base, not the gate logic |
| A3 | Probe count-phase wall (one file, fresh engine) is a valid instrument for the CLI pair-run's count phase, modulo a recorded topology note | Architecture Patterns / Pitfall 7 | Medium — if probe-vs-CLI count-phase ratio looks anomalous, the memo must report bounds rather than point shares (the A−B headline differential is CLI-only and unaffected) |
| A4 | Aggregate worker `busy_nanos` is a usable worker-side ceiling numerator (increment work currently done off the critical path) | Attribution arithmetic | Medium — if worker-side saturation dynamics at 16 threads prove unmodellable from busy_nanos alone, the memo states the worker ceiling as a bound + "what would need to be true", not a point prediction |
| A5 | `cat > /dev/null` read rates approximate the engine's read cost per byte (NVMe sequential) | Attribution arithmetic | Low — δ is a correction term, not a decision axis; if δ is material the memo reports attribution bounds (Pitfall 13 discipline) |

## Open Questions (RESOLVED)

> All four questions were resolved in the 2026-11-17 `--auto` discuss pass and are locked in
> `13-CONTEXT.md` as D-05..D-10; Plans 13-01..13-03 implement the resolutions verbatim. No open
> question remains before measurement.

1. **The D3 numeric bar was not pre-registered anywhere at research time.** — **RESOLVED by D-05.**
   - What we knew: ROADMAP/CONTEXT say the memo records whether the predicted win "clears the D3 bar", but no threshold was written down.
   - Resolution: D-05 pre-registers a predicted full-wall improvement **>= 10.0%** on the **conservative (efficiency-derated, E = 0.5) model** at **16 extractor threads**, applied at **both k** as a conjunction (exactly 10.0% is GO; either k below is NO-GO). The idealized E=M bound is reported alongside but never used for the bar test. The constants are asserted in unit tests before any measurement runs (pre-registration discipline).
2. **Decompression scope: pinned pair only (~17-19.5 GB) vs all six parts (~52-60 GB)?** — **RESOLVED by D-07 (with D-04's lifecycle).**
   - What we knew: the gate needs the pair for v2.0-arrangement comparability; the per-part ×6 spread was explicitly left to planning; disk supported either (428 GiB).
   - Resolution: D-07 decompresses **all six** parts — the pinned pair (`part_001` + `part_006`) feeds the gate arms, and the four non-pinned parts feed an arm-C per-part context matrix marked `context=true` / `excluded=true` (structurally invisible to `build_attribution` / `derive_gate_decision`). D-04 deletes the whole plain directory after the memo commit, with provenance recorded before deletion.
3. **Does the memo re-measure the Python-surface base walls (165.05/178.22 s) or cite them as context?** — **RESOLVED by D-06.**
   - What we knew: D-03's gate compares the release binary (CLI); a fresh Python base needs a profiling-independent wheel rebuild plus a `python_bench` session for a context-only number.
   - Resolution: the predicted-win model and the gate decision are scoped to the **CLI count wall only**. The Python walls are cited as **context only**, with the v2.0-recorded module fingerprint (`6d526431…f5558ae3`) and the binary-fingerprint caveat stated; no Python wall is a denominator or a headline.
4. **Should arm A/B runs write outputs to scratch (v2.0-comparable walls including sort+write) or run output-less?** — **RESOLVED by D-08.**
   - What we knew: v2.0's 144.69 s includes sort+write (`-o` was passed); an output-less run is possible but NOT comparable.
   - Resolution: arms A/B **write a `.rkdb` output to scratch via `-o` on every rep**, deleted immediately after that rep's stats are recorded, so the fresh base measures the same sort+write-inclusive workload as the walls it corroborates.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Release binary rebuilt clean from HEAD | D-03 fingerprint gate | ✓ (exists; REBUILD before gate — provenance `git_dirty` must be false) | rustkmer 0.5.0, rustc 1.101.0-nightly (07e526db9 2026-10-19) — matches v2.0's recorded toolchain | — |
| `--features profiling` example build | arm C (k=21) | ✓ verified live (15.1 s, exit 0) | — | — |
| Dataset six gzip parts | all arms | ✓ all six present | part_001 = 2,785,381,389 B, part_006 = 2,785,388,289 B — sizes exactly match 11-PREPARE-RECORD §1 and v2.0 input fingerprints | slices/synthetic per harness degradation (never for the gate) |
| Disk free | plain inputs + scratch outputs | ✓ 428 GiB on /System/Volumes/Data (single volume backing repo + data) | vs ~19.5-60 GB plain + ~23 GB transient | — |
| `gunzip` | arm B decompression | ✓ (system) | — | `gzip -cd` equivalent |
| `/usr/bin/time -l` | every measured run | ✓ (harness standard) | — | — |
| `pmset -g therm` | per-rep thermal recording | ✓ verified readable, no sudo | — | omit with honest `unavailable` |
| `sudo -n purge` | cache purge attempt | ✗ (expected — host precedent: `cache_state: unavailable` ×30 in v2.0) | — | honest cache_state + counterbalancing + cooldown (the established answer) |
| `/tmp` scratch volume | probe materialization, arm outputs | ✓ (same volume; `refuse_repo_root` guard) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `sudo -n purge` (fallback is the established honest-cache_state protocol — not a blocker).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python stdlib `unittest` (harness suite; no pytest/conftest by contract) |
| Config file | none — discover-based (`python3 -m unittest discover -s scripts/bench/tests -t .`) |
| Quick run command | `python3 -m unittest scripts.bench.tests.test_phase13_driver -v` (new module) |
| Full suite command | `python3 -m unittest discover -s scripts/bench/tests -t .` (~398 tests, plus `cargo test` unaffected — no Rust changes) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PEXT-01 | Fingerprint gate branches: match → cite, mismatch → refuse non-fresh base | unit (fixture sha256s) | `python3 -m unittest scripts.bench.tests.test_phase13_driver -v` | ❌ Wave 0 |
| PEXT-01 | Attribution arithmetic (δ correction, stage residuals, composition split) on fixture numbers | unit (pure functions) | same | ❌ Wave 0 |
| PEXT-01 | Evidence record schema: full-scale-only enforcement (memo derivation refuses non-full records), provenance completeness (binary/input sha256, command, cache_state) | unit | same | ❌ Wave 0 |
| PEXT-01 | Fail-loud parsing: probe JSON missing k / malformed → loud abort (merge_characterize `_guard_zero` class) | unit | same | ❌ Wave 0 |
| PEXT-02 | Predicted-win model: both ceilings present, every input resolved to a named run record or loud failure | unit | same | ❌ Wave 0 |
| PEXT-01/02 | End-to-end driver rehearsal on tiny fixtures (arms A-D + control complete, gates green) at fixture scale | integration (driver --rehearsal mode) | driver invocation in plan verify | ❌ Wave 0 (driver itself is Wave 1+) |
| PEXT-01 | Full-scale measurement session + gates | measurement (the phase deliverable itself) | driver --run (plan task; ~1.5-2 h) | ❌ in-phase |

### Sampling Rate
- **Per task commit:** new-driver unit module (fast, fixture-only)
- **Per wave merge:** full harness unittest suite
- **Phase gate:** full-scale session green (all gates fail-loud passed) + memo committed; rehearsal at fixture scale green BEFORE the full-scale session (11-06/11-07 dress-rehearsal precedent; rehearsal numbers never feed the gate)

### Wave 0 Gaps
- [ ] `scripts/bench/tests/test_phase13_driver.py` — fingerprint gate, attribution math, schema/full-scale guards, fail-loud parsing, model completeness (covers PEXT-01/02 unit layer)
- [ ] Driver `--rehearsal` fixture-scale mode (tiny.fq-class inputs; proves materialization → run → evidence → memo-derivation chain end-to-end without full-scale cost)

## Security Domain

> Required: `security_enforcement: true` (config), ASVS level 1. This is a local measurement phase: no authentication, session, cryptography, or network surface. The applicable categories are input validation and safe subprocess/temp handling in the driver script — the same classes the harness has enforced since T-04-03.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | N/A — local CLI measurement, no identity surface |
| V3 Session Management | no | N/A — no sessions |
| V4 Access Control | no | N/A — single-user dev host; artifacts under user-owned paths |
| V5 Input Validation | **yes** | List-form subprocess only (no shell); fail-loud parsing of every tool output (`_run_fail_loud`/`measured_run` pattern); `refuse_repo_root` path guard; probe JSON parsed with `json.loads` + schema assertions, never regex-on-prose |
| V6 Cryptography | no | N/A — sha256 for provenance only (integrity, not secrecy) |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tool output mis-parsed into a "successful" measurement | Tampering | Fail-loud rc checks + zero-entry guards (`_guard_zero` semantics) + evidence schema validation before memo derivation |
| Temp/scratch sprawl (plain inputs, probe trees, per-rep outputs) | Denial of Service (disk) | Pre-flight disk arithmetic (D-04), per-rep output deletion, explicit post-memo deletion task, `scratch_cleaned` recording (the 12-03 lifecycle precedent) |
| Repo-tree contamination by probe builds (dirty source invalidating fingerprints) | Tampering (provenance) | Materialize probes outside the repo; `binary_provenance.git_dirty` recorded and asserted false for the gate run |
| Silent partial-session acceptance (crashed arm reported as complete) | Repudiation | Exit-code contract (0/2); evidence written incrementally per arm-k; memo derivation refuses incomplete matrices |

## Sources

### Primary (HIGH confidence — live-verified this session)
- Live sha256 + size of `target/release/rustkmer` (`4539b893…d6d023b`, 2,966,832 B) vs v2.0 recorded fingerprint (`8f38d20c…c87c3d23` from `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k21.json` provenance block, git_commit 97b3f01, toolchain string byte-identical to current `rustc 1.101.0-nightly (07e526db9 2026-10-19)`) — D-03 gate FIRES
- `git diff 97b3f01..HEAD -- src/ pyo3/src/`: 9 files, 48+/34−, inspected line-by-line — fmt/clippy-class only
- Live `cargo build --release --locked --features profiling --example engine_probe` (exit 0, 15.1 s) + probe execution on plain and gzip FASTQ (JSON output captured verbatim in Code Examples)
- Live `df` (428 GiB free), live `ls` of the six dataset parts (sizes exact-match 11-PREPARE-RECORD §1), live `pmset -g therm`
- `examples/engine_probe.rs:1-97` — the only committed diagnostics reader; k=21/canonical hardcoded at :45
- `src/count/engine.rs:803-871` (producer bundle), `:1001-1040` (extract+route in one emit closure), `:857-864` (producer span ends before flush), `:1313-1348` (busy_nanos wraps increment loop)
- `src/kmer/extract.rs:90-96` — `for_each_window` public signature with doctest
- `src/cli/args.rs:25` (`-i` num_args=1..), `:47-49` (`-o` optional); absence of any diagnostics reference in `src/cli/commands/count.rs` (grep-verified); `--profile` exists only on fuzzy/prefix (`args.rs:187,388`)
- `scripts/bench/bench.py:1300-1312` (`attempt_cache_purge` darwin `sudo -n purge` → `unavailable`)
- `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k21.json` + `10-results-full-k31.json` — arms' `inputs` field = pinned pair; `medians.wall_s` 144.69/147.08; `cache_state: unavailable`; peak RSS 47.2 GB (43.97 GiB) k=21
- `scripts/bench/merge_characterize.py` (driver pattern, verbatim sections referenced), `scripts/bench/phase11.py` (staged-controller/exit-code pattern), `scripts/bench/prepare_inputs.py` (stage/manifest/provenance patterns), `.planning/research/profiling/microbench_Cargo.toml` + `contention_bench.py` (research-local materialization precedent)
- `scripts/bench/README.md:302` — unittest discover command

### Secondary (CITED — committed planning artifacts)
- `.planning/PROJECT.md` — v2.0 walls + MEM references (43.97/68.52 GiB), D3 history, dataset description
- `.planning/research/PITFALLS.md` Pitfalls 5/7/8/9/10/13/14 — attribution design, confounds, full-scale-only discipline, stale-baseline contamination
- `.planning/research/ARCHITECTURE.md` §1.1/§3.3 — engine integration surfaces; "research-phase-local patch" anticipation for sub-timers
- `.planning/research/SUMMARY.md` — inflate ~13% / ~19 s estimate (research ballpark, explicitly NOT a citable source run), zero-deps recommendation
- `.planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md` §1/§8 — source fingerprints, command-line provenance shape
- `.planning/phases/13-producer-attribution-research/13-CONTEXT.md` — all locked decisions (copied verbatim in User Constraints)

### Tertiary (LOW confidence)
- None — this phase required no external/web sources: zero new packages, no library-API questions beyond the in-tree code, all unknowns resolved by local verification.

## Metadata

**Confidence breakdown:**
- Standard stack / instruments: HIGH — every instrument verified live (build, run, JSON) or read from source with file:line anchors
- Architecture (arm design, materialization pattern): HIGH — inherited pre-specified from milestone research + established repo precedents (microbench, driver, evidence lifecycle)
- Pitfalls: HIGH — code-anchored + direct live verification of the two new planning-critical facts (gate fires; CLI diagnostics gap)
- Session arithmetic / disk: HIGH — measured free space, measured part sizes; plain-size band is the only estimate (A1, harmless at 428 GiB)

**Research date:** 2026-11-17
**Valid until:** 2026-12-17 (stable — local facts; re-verify the binary fingerprint if any Rust-source commit lands before execution)
