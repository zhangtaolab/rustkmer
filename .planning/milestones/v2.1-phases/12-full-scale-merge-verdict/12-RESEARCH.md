# Phase 12: Full-Scale Merge Verdict - Research

**Researched:** 2026-11-17
**Domain:** Full-scale benchmark session execution — staged controller (`phase11.py`) driving a pre-registered merge-verdict protocol over Phase 11's prepared artifacts
**Confidence:** HIGH — every load-bearing number and mechanism is anchored to Phase 11 evidence files or code read directly this session; the ROADMAP research flag is "none — execution of a pre-registered protocol; no unknowns beyond Phase 11's characterization output"

## Summary

Phase 12 RUNS what Phases 10-11 built; it adds no measurement capability and changes no Rust code. The session's shape is fixed by locked decisions: a staged controller `phase11.py` (D-01, modeled on `phase10.py`) pins the order revalidate → parity → timed rounds → verdict → render; one session covers both k (D-02) with exactly 3 counterbalanced reps per arm; the three-way parity gate (PARITY-GATE.md) executes green BEFORE any timed round, with the full-scale deep per-k-mer leg running ONLY the streaming form (`merge_characterize.dump_vs_dump_equal_streaming`) — never bench.py's in-process comparator (WR-01, the one live hazard: it loads both dumps into a Python heap and would need far more than the host's RAM at 897M-1.15B lines per side). The timed arms are the three merge arms — `rustkmer merge` (defaults), `rustkmer merge --num-threads 1` (like-for-like), `jellyfish merge` (defaults; single-threaded by design) — run over the 8 fingerprinted artifacts already on disk and revalidated at round 0.

Everything the plan needs is already measured: union anchors (k=21 Total 8,967,099,203 / k=31 Total 8,275,694,030; merged Distinct 897,266,581 / 1,146,353,600), ladder slopes and full-scale wall predictions (rustkmer 53.8/73.4 s, jellyfish 77.3/105.5 s — MBENCH-04's predicted-vs-measured inputs), byte rates (`.rkdb` 20.0 B/entry, `.jf` 10.0/12.0 B/entry), the derived 136 GiB disk floor with its tripwire, and the streaming comparator proven green at 318.5M/373.0M lines per side. The release binary's sha256 (`4539b893e8ec…d023b`) was re-verified this session and matches the ladder's recorded provenance exactly — predictions and measurements stay attribution-clean.

Genuine Phase 12 implementation work (small, additive): (1) the controller itself; (2) **the Leg-2 independent-recount leg has no harness implementation yet** — PARITY-GATE.md §8's mapping table covers only Legs 1 and 3, and no code in `scripts/bench/` counts the two parts as one input list and diffs it per-k-mer against the merged database (ROADMAP success criterion 1 requires it: "the independent recount leg is cheap enough that skipping saves nothing"); (3) merge-verdict renderer sections with entry-rate/byte-rate metrics and the byte-identical re-render proof; (4) wrap-up tasks locked inside this phase — artifact cleanup after verdict evidence commits (D-03) and the one-time v2.0+verdict rewrite of `docs/benchmark-report.md` (D-04). Note the controller's file name is `phase11.py` per D-01 verbatim, despite executing in roadmap Phase 12 — do not "fix" the name.

**Primary recommendation:** Build `scripts/bench/phase11.py` as a five-stage controller (`revalidate`, `parity`, `timed`, `verdict`, `render`) that imports every primitive from `bench.py`, `merge_characterize.py`, `prepare_inputs.py`, and `output_stage.py`; implement the Leg-2 recount diff by reusing the streaming dump→normalize→LC_ALL=C-sort→compare pipeline with two `.rkdb` dump sides; never invoke `bench.py run_bench` for the full-scale session.

## Project Constraints (from CLAUDE.md)

- **GSD workflow enforcement:** all repo edits go through GSD commands; this phase's plans are executed via `/gsd-execute-phase`. The D-05 pre-planning fix (3 red tests) is explicitly routed through `/gsd-quick` BEFORE Phase 12 planning.
- **Tech stack:** work within the established dependency set; no new persistence engine. This phase adds zero Rust changes and zero new packages (harness stdlib-only contract, `bench.py:25-26`: "Python 3.10+ stdlib only — no third-party imports, no pip installs" — Phase 11 scripts require 3.11+ per IN-04).
- **Compatibility:** preserve `.rkdb` v2 format and public CLI/Python APIs — untouched by this phase (measurement only).
- **Dual surface:** N/A this phase (no engine changes); Phase 13 may overlap this phase's window precisely because it also lands no changes.
- **Version policy:** Python floor 3.11+ (`pyo3/pyproject.toml`); Rust MSRV 1.82 — both untouched; the pinned comparator is jellyfish 2.3.1 (Homebrew, sha256-fingerprinted per run).
- **Commands:** `cargo test` / `cargo clippy` are the Rust gates — no Rust changes this phase, so the Python harness suite is the relevant gate (see Validation Architecture).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 12 creates a **staged controller (`phase11.py`)** modeled on the `phase10.py` precedent — stage isolation, the 0/1/2 exit-code contract as the verdict carrier, and per-stage resume. The controller mechanically pins the stage order (revalidate → parity → timed rounds → verdict → render) so the WR-01 constraint (deep leg via the streaming form, never bench.py's in-process comparator at full scale) is enforced by construction, not by operator memory. — **Reversibility:** reversible — a code artifact; the session can be re-driven.
- **D-02:** A **single staged session covers both k** — one round-0 gate block (artifact fingerprint + Total revalidation from 11-PREPARE-RECORD.md records, full disk-budget check against the 136 GiB derived floor), then parity execution, then exactly **3 counterbalanced reps per arm at each k** (the protocol minimum; the ladder showed linear scaling with tight ratios, so extra reps buy little). The D-12 per-rep light disk re-check runs before every measured rep. — **Reversibility:** reversible — the schedule is replannable until round 0 commits; after that the session's own resume contract carries it.
- **D-03:** **Artifact cleanup is a Phase 12 wrap-up task**, executed only after the verdict evidence (report + results JSON + exit-code record) is committed: delete the 8 artifacts under `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` (~86.74 GiB) per D-02 of Phase 11's lifecycle ("keep until the Phase 12 verdict lands, then clean up"). Rebuild remains possible via the 11-02 stage (~30-90 min), so nothing one-way is destroyed.
- **D-04:** The **full v2.0+verdict-based rewrite of `docs/benchmark-report.md` is a Phase 12 wrap-up task** (closes the D-05 deferred item from Phase 11) — the verdict data is fresh in-phase, so the doc is rewritten exactly once, including the merge-verdict sections, the superseded-banner removal, and current dataset/verdict numbers.
- **D-05:** The **3 pre-existing test reds** (`scripts/bench/tests/test_phase10_verdict.py` archived-path failures, caused by commit 97c497c moving Phase-10 artifacts to `.planning/milestones/v2.0-phases/`) are fixed by a **`/gsd-quick` task BEFORE Phase 12 planning** — not inside Phase 12 plans. The same quick task may fold the WR-04 README rehearsal-command fix (missing `--input`/`--k` brace/`--disk-floor-gb 2`) as an adjacent doc correction.

### Carried Constraints from Phase 11 (locked, not re-decided)

- Parity-before-timing: the three-way gate (`rustkmer merge == independent recount of union == jellyfish merge`, exact per k-mer, `total_kmers` definition named per check) executes green before any timed round (MBENCH-03 success criterion 1).
- The full-scale deep leg runs the **streaming form** (PARITY-GATE.md §4 / `merge_characterize` streaming comparator) — bench.py's in-process dump-vs-dump is unit-level only (WR-01: it needs ~120-150 GB heap at the 10% rung).
- Input equivalence: both tools merge their own representation of identical, parity-validated source data (fingerprints + Totals revalidated from 11-PREPARE-RECORD.md before round 0 — Phase 11 D-04).
- Defaults-only flags during measurement; wall time is the primary decision axis; `max(rss, phys_footprint)` and disk recorded as context; BOTH verdict outcomes are valid results.
- Disk floor 136 GiB (derived, tripwire-pinned) guards the session; `--disk-floor-override` only for deliberate runs.
- Like-for-like `rustkmer merge --num-threads 1` arm is mandatory in the methodology block; t1 = 2-OS-thread pool contract (research A6).

### Claude's Discretion

- Controller stage granularity (how many stages, their names, resume-point placement) — phase10.py precedent governs.
- Parity execution mechanics at full scale (recount leg sizing, streaming deep-leg invocation, runtime) per PARITY-GATE.md.
- Report rendering details — extend the existing renderer patterns; entry-rate/byte-rate metric formulas per MBENCH-04.
- Counterbalanced arm ordering within the 6-arm merge round schedule (bench.py `round_schedule` machinery already generalizes).
- Predicted-vs-measured check inputs (ladder slopes from 11-LADDER-RESULTS.json; backstop caveat per milestone Pitfall 14).
- WR-02 (render-report default-out clobbering) may be fixed opportunistically in the same touch if the renderer is extended (HYG-04-style same-touch rule).

### Deferred Ideas (OUT OF SCOPE)

- **MBF-01 flag/config sweep** — post-verdict v2.2+ work, only if the verdict is INVEST (ROADMAP Note).
- **KMC3 arm** — descoped 2026-11-16 (memory bar = below jellyfish; see memory notes).
- **Mixed-canonicality / mixed-k arms** — not a comparison axis (documented jellyfish bug).
- **Phase 13 overlap** — Producer Attribution Research is independent and may run in parallel with this phase's window (measurement-only, no code changes), per ROADMAP execution order.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MBENCH-03 | Full-scale merge verdict measured and recorded at BOTH k=21 and k=31 — counterbalanced ≥3 reps, wall (primary decision axis), `max(rss, phys_footprint)` (context), disk (recorded); invest/no-invest verdict via the 0/1/2 exit-code contract; methodology block captures threads/flags/merge-route/sha256 per arm including the like-for-like `rustkmer merge --num-threads 1` arm | Parity gate machinery exists and is unit-proven (`assert_merge_parity`, `normalize_dump_lines`, `dump_vs_dump_equal`); the full-scale deep leg route exists (`dump_vs_dump_equal_streaming`, green at 373M lines/side); round-0 revalidation is one `prepare_inputs.py revalidate` call over 8 manifest records; anchors and merged-Distinct targets are pinned constants; merge command builders enforce defaults-only and hash-size equality by construction; the only new build is the controller + Leg-2 recount leg + verdict stage |
| MBENCH-04 | Mechanical merge-verdict report — byte-identical re-render proof, entry-rate / byte-rate metrics, single-threaded-comparator asymmetry disclosed, predicted-vs-measured cost-model check (linear-in-entries, single-threaded) | Renderer contract and patterns exist in two proven implementations (`bench.py render_report` with no measurement literals + `phase10.py render_report_text` with `publish_atomic` and `_validate_render_document`); ladder constants feed the predicted-vs-measured check (`11-LADDER-RESULTS.json` summary.slopes / extrapolated_full_scale); byte-rate asymmetry is measured (`.jf` 10/12 vs `.rkdb` 20 B/entry); asymmetry sentence text is pre-agreed in milestone Pitfall 3 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Round-0 artifact revalidation + anchor equality | Harness (Python `scripts/bench/`) | Filesystem artifacts | `prepare_inputs.py revalidate_stage` already re-hashes + re-stats and rejects unrecorded artifacts; the controller only invokes and records it |
| Three-way parity execution (Legs 1-3) | Harness (Python) | Tools under test (rustkmer/jellyfish binaries) | Gate logic is harness code; the legs invoke the pinned binaries as subprocesses; per-k-mer identity is decided by harness streaming comparison |
| Timed merge measurement | Harness (Python) via `/usr/bin/time` | Tools under test | OS rusage is the only clock (harness-internal clocks banned); arms are list-form argv built by `build_merge_cmd`/`jellyfish_merge_cmd` |
| Verdict computation + exit-code contract | Harness (controller `phase11.py`) | — | Pure comparison of recorded medians — never re-measured, never hand-entered (phase10 `verdict_block` pattern) |
| Mechanical report + re-render proof | Harness (renderer) | Committed evidence JSONs | Renderer reads recorded JSONs only, no clock, no literals (T-04-07 contract) |
| Evidence persistence | `.planning/phases/12-full-scale-merge-verdict/` (committed) | Data-volume artifacts (transient) | Session results/evidence are committed documents; merge outputs and dumps are volume transients, deleted or left per plan |
| Input artifacts (read-only this phase) | Data volume `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` | — | Built by Phase 11; consumed verbatim after revalidation; deleted only in the D-03 wrap-up after evidence commits |
| Rust engine | — | — | NO changes this phase (provenance stability: binary sha256 must equal the ladder's `4539b893…` so predictions stay attributable) |

## Standard Stack

### Core

No new packages. The phase installs nothing; the harness is stdlib-only Python over two pinned binaries.

| Component | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib harness | 3.11+ (host: 3.13.11 via `.venv313`) | Controller, parity gates, protocol, renderer | `bench.py`/`phase10.py`/`merge_characterize.py`/`prepare_inputs.py` are all stdlib-only, unit-proven, and importable (`scripts.bench.*`) [VERIFIED: scripts/bench/bench.py:25-26, scripts/bench/merge_characterize.py:48-49] |
| `rustkmer` release binary | 0.5.0, sha256 `4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b` | Tool under test (merge, merge-t1, recount leg, stats, dump) | Re-verified this session — byte-identical to the ladder's recorded provenance, so ladder predictions attribute to the same bytes [VERIFIED: shasum this session == 11-LADDER-RESULTS.json provenance.binary.sha256] |
| jellyfish | 2.3.1 pinned (`/opt/homebrew/bin/jellyfish`, sha256 `e99c676b…91ee`) | Comparator (merge arm + dump -c) | Pinned-comparator semantics locked in Phase 11 (single-threaded streaming merge, no `-t`/`-s` accepted on merge, silent canonicality acceptance is a known bug) [VERIFIED: `jellyfish --version` this session; 11-LADDER-RESULTS.json provenance] |
| `/usr/bin/time -l` (macOS) / `-v` (Linux) | OS | Only clock; wall + max(rss, phys_footprint) via `parse_time_output` | Units-pinned dual-platform parser already unit-proven [VERIFIED: scripts/bench/bench.py:121-140] |
| `sort` (LC_ALL=C), `awk`, `wc` | macOS system | Streaming deep-leg pipeline (normalize → external sort → line count) | Proven at 318.5M/373.0M lines per side in Phase 11 [VERIFIED: scripts/bench/merge_characterize.py:193-322 + 11-LADDER-RESULTS.json gates] |

### Supporting

| Component | Purpose | When to Use |
|---------|---------|-------------|
| `scripts.bench.bench` primitives | `build_merge_cmd`, `jellyfish_merge_cmd`, `measure`/`parse_time_output`, `attempt_cache_purge`, `check_disk_floor`/`ensure_disk_headroom`, `stats`, `jellyfish_stats`, `fingerprint`, `binary_provenance`, `validate_schema`, `validate_provenance`, `assert_merge_parity`, `BenchmarkConfig`, `DEFAULT_DISK_FLOOR_GB` | Every stage of the controller imports these — zero reimplementation |
| `scripts.bench.merge_characterize` | `measured_run` (keeps stderr for route attribution), `route_from_stderr`, `dump_vs_dump_equal_streaming`, `_normalized_sorted_dump`, `_AWK_NORMALIZE` | Parity + timed stages; the only full-scale deep-leg route (WR-01) |
| `scripts.bench.prepare_inputs` | `revalidate_stage` (+ CLI verb `revalidate`), `DEFAULT_ARTIFACTS_DIR` | Round-0 gate |
| `scripts.bench.output_stage.rotation_schedule` | Generic counterbalanced round-robin (N arms × R reps, pure) | Timed-stage arm ordering ( CONTEXT discretion: "round_schedule machinery already generalizes") |
| `phase10.py` patterns | `EXIT_OK/EXIT_NO/EXIT_INVALID`, per-stage dispatch, `assemble_doc`/`write_doc`, `verdict_line`, `publish_atomic`, `_validate_render_document` | The controller template (D-01) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `phase11.py` controller driving merge-only arms over prepared artifacts | `bench.py --mode full --reps 3` | bench.py re-counts fresh inputs (invalidating the "parity-validated prepared inputs" premise) AND hardwires the in-process `dump_vs_dump_equal` after all reps — the WR-01 OOM path. Rejected by locked constraints. [VERIFIED: scripts/bench/bench.py:1857-1859] |
| Extending `bench.py` with a merge-only mode | New controller file per D-01 | D-01 locks the controller decision; bench.py stays untouched except opportunistic WR-02 if the renderer is extended |
| In-process sort of dump lines (bench.py form) | Streaming external `sort` (merge_characterize form) | In-process needs a Python heap proportional to dump size (~120-150 GB at the 10% rung) — cannot run at full scale; streaming is proven |

**Installation:** Nothing to install. Harness runs as `python3 scripts/bench/phase11.py --stage …` (script-execution path fixup already handled by the `sys.path.insert` pattern all bench scripts carry).

**Version verification:** No packages to verify on any registry — the stdlib-only contract bans pip installs. The two binaries were fingerprinted this session (sha256 above); jellyfish 2.3.1 is the Phase-11-pinned comparator and must not be upgraded mid-milestone.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | This phase installs no external packages |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

The harness stdlib-only contract (`bench.py:25-26`, `merge_characterize.py:48-49`) and the milestone constraint "work within the established stack" (`.claude/CLAUDE.md`) forbid new dependencies. `jellyfish` is a pre-existing pinned system binary (Homebrew Cellar), not installed by this phase; its sha256 is recorded per-run via `binary_provenance` (build_profile `pinned-comparator-2.3.1`).

## Architecture Patterns

### System Architecture Diagram

```text
            ┌──────────────────────────────────────────────────────────────┐
            │  Data volume: CRR1936095-merge-inputs/ (8 artifacts + manifest)│
            │  part_001/006 × {k21,k31} × {.rkdb,.jf}  — 86.74 GiB, frozen  │
            └──────────────┬───────────────────────────────────────────────┘
                           │ (read-only until D-03 cleanup)
                           ▼
              ┌────────────────────────┐
              │ STAGE revalidate       │  prepare_inputs revalidate (re-hash +
              │ (round-0 gate)         │  re-stats ×8, reject unrecorded),
              │                        │  manifest Totals == union anchors
              │                        │  (8,967,099,203 / 8,275,694,030),
              │                        │  binary fingerprints, FULL disk budget
              │                        │  (computed, passed explicitly — D-12)
              └──────────┬─────────────┘
                         │ evidence JSON
                         ▼
              ┌────────────────────────┐   rustkmer merge (defaults)
              │ STAGE parity (per k)   │   rustkmer merge -t1          → merged
              │  merge once per tool   │   jellyfish merge (defaults)  → outputs
              │  + Leg-2 recount       │
              │  + Legs 1-3 gates      │   Leg 1: aggregates vs manifest+anchors
              │  GREEN BEFORE TIMING   │   Leg 2: recount(both parts as ONE   streaming
              │                        │          input list) vs rk merge  → dumps
              │                        │   Leg 3: rk merged vs jf merged      (WR-01:
              │                        │          per-k-mer exact            never
              └──────────┬─────────────┘                                     in-process)
                         │ parity evidence JSON (per k)
                         ▼
              ┌────────────────────────┐   3 arms × 3 reps, counterbalanced
              │ STAGE timed (per k)    │   (rotation_schedule), 1 discarded
              │                        │   warmup per tool, per-rep D-12 disk
              │                        │   re-check + honest cache_state,
              │                        │   route attribution from stderr
              └──────────┬─────────────┘
                         │ results JSON per k (schema v1)
                         ▼
              ┌────────────────────────┐   invest/no-invest from recorded
              │ STAGE verdict          │   medians (wall primary); greppable
              │  exit 0/1/2 contract   │   verdict line; both outcomes valid
              └──────────┬─────────────┘
                         │ verdict JSON + exit code
                         ▼
              ┌────────────────────────┐   rendered from recorded JSONs only;
              │ STAGE render           │   render → sha256 → re-render → sha256
              │                        │   byte-identical proof; publish_atomic
              └──────────┬─────────────┘
                         ▼
              ┌────────────────────────┐   D-03: delete 8 artifacts AFTER
              │ WRAP-UP (in-phase)     │   verdict evidence commits (~86.74 GiB)
              │  cleanup + docs (D-03/ │   D-04: rewrite docs/benchmark-report.md
              │  D-04)                 │   once (verdict + banner removal)
              └────────────────────────┘
```

### Recommended Project Structure

```text
scripts/bench/
├── phase11.py                      # NEW: staged controller (D-01) — revalidate/
│                                   #   parity/timed/verdict/render stages
├── tests/test_phase11_verdict.py   # NEW: controller contract tests (Wave 0)
├── bench.py                        # UNTOUCHED (except optional WR-02 same-touch)
├── merge_characterize.py           # UNTOUCHED (streaming deep-leg source; recount
│                                   #   leg may reuse its pipeline helpers)
└── prepare_inputs.py               # UNTOUCHED (revalidate verb invoked as-is)

.planning/phases/12-full-scale-merge-verdict/
├── 12-RESEARCH.md                  # this file
├── 12-PARITY-K21.json / 12-PARITY-K31.json   # parity evidence (suggested names)
├── 12-RESULTS-FULL-K21.json / 12-RESULTS-FULL-K31.json  # timed results (suggested)
├── 12-VERDICT.json                 # verdict document + re-render proof inputs
├── 12-MERGE-REPORT.md              # mechanical merge-verdict report
└── 12-RENDER-PROOF.json            # byte-identical re-render record (suggested)
```

### Pattern 1: Staged controller with the 0/1/2 exit-code contract (D-01)

**What:** `--stage` dispatch over a pinned stage tuple; per-stage functions return contract codes; a top-level exception handler maps ANY infrastructure failure to exit 2, never to a verdict code.
**When to use:** every stage of the session.
**Example (verified mechanics from the precedent):**

```python
# Source: scripts/bench/phase10.py:97-99, 2539-2622
EXIT_OK = 0        # valid result (the verdict stage's measured YES)
EXIT_NO = 1        # a genuine measured NO (artifact kept)
EXIT_INVALID = 2   # invalid/inapplicable (no artifact written)

STAGES = ("synthetic", "slice-gate", "cli", "python", "render", "preflight-python")

if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — fail loudly, no traceback noise
        # Infrastructure failures are INVALID (exit 2), never a measured NO
        # (exit 1): the verdict code is reserved for a recorded observation.
        print(f"phase10.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)
```

Resume contract: each stage takes its predecessors' artifacts by path (`--docs`, `--cli-doc` style args) and re-runs idempotently from recorded JSON — no hidden internal state (phase10 precedent: `run_render` consumes only recorded documents).

### Pattern 2: Parity before timing, deep legs streamed (WR-01 / PARITY-GATE.md)

**What:** the parity stage runs the three legs and only a green gate admits the timed stage. At full scale, Leg 3 (and Leg 2's diff) run `dump_vs_dump_equal_streaming`-style pipelines: dump → awk fail-loud normalize → `sort` with `LC_ALL=C` and `-T workdir` → streaming line compare.
**When to use:** parity stage, both k, before any timed round.
**Example (the only sanctioned full-scale deep-leg route):**

```python
# Source: scripts/bench/merge_characterize.py:278-298 (signature + sides)
def dump_vs_dump_equal_streaming(rkdb_path, jf_path, rustkmer, workdir):
    # rustkmer side: [rustkmer, "dump", rkdb, "-o", raw]   (via -o file)
    # jellyfish side: ["jellyfish", "dump", "-c", jf]      (via stdout)
    # both: awk normalize (exit 2 on malformed/empty) -> LC_ALL=C sort -T workdir
    #       -> wc -l guard -> streaming zip compare, first difference named
    ...
```

Transient facts the plan must budget: raw+norm coexist during awk (peak ≈ 2× dump text per side), `raw`/`norm` are unlinked in a `finally` per side, sorted files persist until compared then unlinked; `sort -T workdir` writes temp in the workdir's volume — same APFS volume as everything else on this host. [VERIFIED: merge_characterize.py:231-322]

### Pattern 3: Merge-only counterbalanced protocol over prepared artifacts

**What:** 3 arms — `merge` (rustkmer defaults), `merge-t1` (`--num-threads 1`), `jellyfish-merge` (defaults) — 3 reps, rounds visit every arm once with rotated start. Count arms do NOT re-run: the prepared artifacts ARE the validated count outputs; re-counting would break the "parity-validated inputs before round 0" premise.
**When to use:** timed stage.
**Example (arm builders + scheduler):**

```python
# Source: scripts/bench/bench.py:338-366 (defaults-only by construction)
def build_merge_cmd(rustkmer, out_db, input_dbs, num_threads=None):
    argv = [str(rustkmer), "merge", "-i", *[str(p) for p in input_dbs],
            "-o", str(out_db)]
    if num_threads is not None:
        argv += ["--num-threads", str(num_threads)]
    return argv

def jellyfish_merge_cmd(out_jf, input_jfs):
    # Defaults only — SUM semantics; -m/-M/-j/-t/-s are NOT passed because in
    # merge -m is MIN mode ... flag strings are never copied between subcommands.
    out_v = validate_path(out_jf)
    inputs = [validate_path(p) for p in input_jfs]
    return ["jellyfish", "merge", "-o", out_v, *inputs]

# Source: scripts/bench/output_stage.py:121-140 — generic counterbalanced rounds
def rotation_schedule(arm_names, reps):
    # Round r starts at arm index r mod len(arm_names); every round contains
    # every arm exactly once.
    ...
```

Per-rep mechanics (reuse, do not re-hand-roll): `attempt_cache_purge()` → honest `cache_state`; `measured_run(argv)` from merge_characterize (keeps stderr so `route_from_stderr` can attribute "prefix-cache" vs "not-reported" — no invention, T-11-15); `ensure_disk_headroom(dir, floor_gb, phase=…, override=…)` before EVERY measured rep (D-12); medians via `reduce_arm` (CV% warning, not failure).

### Pattern 4: Mechanical renderer + byte-identical re-render proof

**What:** the report's every measurement number is read from recorded JSONs; the renderer carries no measurement literals and consults no clock; the proof is render → hash → re-render → hash → byte equality.
**When to use:** render stage; the D-04 docs rewrite consumes the rendered report as its source of numbers.
**Example (the load-bearing precedent pieces):**

```python
# Source: scripts/bench/bench.py:1971-1979 (contract statement)
# Contract (threat T-04-07): every MEASUREMENT number in the rendered report
# is read from the results JSONs — the code below carries no measurement
# literals and consults no clock, so a re-render is byte-identical and a
# hand-edited number is detectable.

# Source: scripts/bench/phase10.py:1677-1739 — publish semantics:
#   in-memory build -> publish_atomic([(verdict_path, …), (out_path, report)])
#   -> failure restores/never destroys pre-existing artifacts
#   -> print(verdict_line(block)) machine-greppable line
#   -> return EXIT_OK if overall == "YES" else EXIT_NO
```

Merge-verdict sections to add (MBENCH-04): per-arm methodology rows (threads/flags/merge-route/sha256), the asymmetry sentence ("each tool merges its own representation of identical, parity-validated input data" — milestone Pitfall 3's exact pre-agreed wording), entry-rate (entries/s) and byte-rate (output bytes/s or B/entry) per arm making the `.jf` 10/12 vs `.rkdb` 20 B/entry asymmetry visible, predicted-vs-measured table with the backstop caveat verbatim from `11-LADDER-RESULTS.json summary.extrapolated_full_scale.caveat`, and the RSS-is-context-not-a-decision-axis framing (Pitfall 6 — no memory-win claims over a streaming comparator). The `_arm_row` merge `n/a` special case in bench.py stays byte-compatible for committed pre-Phase-11 files — extend, don't repurpose. [VERIFIED: bench.py:2037-2069]

### Anti-Patterns to Avoid

- **Running `bench.py --mode full` for the session:** it re-counts fresh inputs AND executes the in-process `dump_vs_dump_equal` (bench.py:1857-1859) only AFTER all reps — the WR-01 OOM path: hours of measurement lost. The controller enforces streaming-by-construction (D-01's whole point).
- **In-process dump normalization at full scale:** `normalize_dump_lines` + `sorted()` loads ~30 GB text per side into Python objects — unit-level only. [VERIFIED: merge_characterize.py:181-191 states ~120-150 GB heap need at merely the 10% rung]
- **Aggregate-only parity:** Total/Distinct conservation passes even under jellyfish's silent canonicality mixing — per-k-mer dump identity is the verdict gate. [VERIFIED: PARITY-GATE.md §6; milestone Pitfall 1, demonstrated on the pinned binary]
- **Reading `DatabaseHeader.total_kmers` for any conservation check:** that field is the record count, not the sum of counts (IN-03 collision). Only `rustkmer stats -f json` `unique_kmers`/`total_kmers` and `jellyfish stats` Distinct/Total. [VERIFIED: PARITY-GATE.md §5]
- **Memory-win framing:** jellyfish merge is streaming (~6.8 MB RSS measured) — RSS is context, never a decision axis, for merge. [VERIFIED: milestone Pitfall 6; REQUIREMENTS.md Out-of-scope table]
- **Hand-written numbers in the report or hand-transcribed fingerprints:** every number comes from recorded JSON; every fingerprint from `fingerprint()`/`revalidate_stage`.
- **Trust a red harness test during this phase while the D-05 reds persist** — they should be gone before planning (D-05 quick task); the known `test_verify_threads.py` ~50% macOS `sample`-race flake additionally requires purging stale `target/` before believing a red. [VERIFIED: STATE.md Blockers; 11-VERIFICATION.md warning 1]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wall/RSS measurement | A Python timer around subprocess | `merge_characterize.measured_run` / `bench.measure` (`/usr/bin/time` + units-pinned `parse_time_output`) | Harness-internal clocks are banned; dual-platform unit parsing is proven and unit-tested |
| Cache honesty | Assuming cold cache | `attempt_cache_purge()` honest labels (`purged`/`unavailable`/`runner-fresh`) | `sudo purge` cannot evict active pages on macOS; honesty discipline is locked (Pitfall 5) |
| Disk guards | ad-hoc df checks | `check_disk_floor` (exit-3 pre-flight) + `ensure_disk_headroom` (per-rep, D-12) | Stated-shortfall messages, override semantics, and exit-3 contract are unit-proven |
| Counterbalancing | Hand-rolled ordering | `output_stage.rotation_schedule(arm_names, reps)` | Pure, wraps rotation, unit-testable |
| Merge parity legs | New comparison code | `assert_merge_parity` (Leg 1) + `dump_vs_dump_equal_streaming` machinery (Legs 2-3) | GREEN/RED unit-proven; fail-loud semantics (T-11-09) are the defense against vacuous gates |
| Artifact revalidation | Manual sha256 transcription | `prepare_inputs.revalidate_stage` | Re-hashes, re-stats, rejects unrecorded artifacts; stage-computed provenance is D-04's locked decision |
| Provenance blocks | Hand-built dicts | `binary_provenance` + `validate_provenance` | Strict gate; path-without-hash is not provenance (T-05-02) |
| Results documents | New schema | `phase10.assemble_doc` + `validate_schema` (schema v1 tolerates extra keys) | MBENCH-05 boundary: never fork a second results schema |
| Atomic evidence publish | Direct writes | `phase10.publish_atomic` + `write_doc`/`write_evidence_doc` (validate-then-write) | Failed publishes never destroy prior artifacts |
| Counterbalanced schedule proof | Manual reasoning | existing unit tests + one new schedule-shape test | Schedule shape is a pure function — cheapest possible test |

**Key insight:** Every risky primitive already exists, is unit-proven GREEN/RED, and was exercised live at scale in Phase 11 (ladder + dress rehearsal). Phase 12's new code is almost entirely *orchestration*; the only genuinely new measurement logic is the Leg-2 recount diff, which reuses the streaming dump pipeline with two `.rkdb` sides.

## Runtime State Inventory

> Not a rename/refactor/migration phase — the per-category audit is out of template scope. The measurement-relevant runtime state is fully covered by Environment Availability (artifacts on disk, free space, binary hashes) and the wrap-up tasks (D-03 artifact deletion, D-04 docs rewrite). One deliberate note: the 8 artifacts + manifest on the data volume ARE runtime state consumed by this phase — they are verified present with sizes matching 11-PREPARE-RECORD.md §11 exactly (e.g. `part_001.k21.rkdb` = 13,292,834,822 bytes, `manifest.json` present). [VERIFIED: ls this session]

## Common Pitfalls

### Pitfall 1: WR-01 — the in-process deep gate at full scale (the one live hazard)
**What goes wrong:** `bench.py`'s comparison path calls `dump_vs_dump_equal(db_merged, jf_merged, …)` after ALL reps complete (bench.py:1857-1859). At full scale each dump is ~897M (k21) / ~1.15B (k31) lines of ~28-34 GB text; in-process normalization would need a heap far beyond the 128 GB host — OOM after hours of reps, nothing saved.
**Why it happens:** the gate was wired for slice-scale runs; the ladder proved the in-process form cannot even run at the 10% rung (~120-150 GB heap need, documented in merge_characterize.py:181-191).
**How to avoid:** D-01's structural fix — the controller never invokes bench.py's comparison path at full scale; parity legs use `dump_vs_dump_equal_streaming` / the shared `_normalized_sorted_dump` pipeline; stage order (parity before timed) plus per-stage evidence persistence means a failure loses at most the current stage.
**Warning signs:** any plan task that shells out to `bench.py --mode full`; any new code importing `normalize_dump_lines` for a full-scale path.

### Pitfall 2: Canonicality silent mixing (milestone Pitfall 1)
**What goes wrong:** `jellyfish merge` exits 0 on canonicality-mixed inputs with conserved totals and a meaningless key space — demonstrated on the pinned 2.3.1 binary.
**Why it happens:** canonicality is baked at count time; merge validates only key length.
**How to avoid:** already pinned structurally — the prepared `.jf` inputs were built by the Phase 11 stage under one BenchmarkConfig (canonical=True) and are frozen behind sha256 revalidation; the per-k-mer dump gate structurally cannot pass a mixed key space. Do not regenerate or "refresh" any input this phase.
**Warning signs:** any task touching input creation; jellyfish Distinct ≈ sum of input Distincts.

### Pitfall 3: The `total_kmers` definition collision (IN-03)
**What goes wrong:** `DatabaseHeader.total_kmers` is the record count; `rustkmer stats`' `total_kmers` is the sum of counts. Mixing them fails mysteriously (897M vs 9B "mismatch") or passes vacuously.
**How to avoid:** every check names its definition; conservation reads only the stats readers; the manifest Totals compared at round 0 are sum-of-counts (verified: 4,483,548,820 + 4,483,550,383 = 8,967,099,203 EXACT).
**Warning signs:** a check reading `format.rs` header fields; a mismatch whose ratio ≈ average count.

### Pitfall 4: jellyfish hash-size equality precondition
**What goes wrong:** jellyfish merge requires equal `-s` capacity across inputs (output slots derive from the FIRST input). A regenerated input with a different `-s` changes output capacity and invalidates comparability.
**How to avoid:** inputs are frozen and revalidated (k-pair equality `{21: ['1G'], 31: ['2G']}` asserted by revalidate); merged-output occupancy consequences are pre-computed (k21 0.836 — above the 0.75 count-time target, expected and gated by Leg 1 + the deep leg; k31 0.534 comfortable). [VERIFIED: 11-PREPARE-RECORD.md §7, §11]

### Pitfall 5: Disk exhaustion / APFS accounting lag
**What goes wrong:** the session writes ~20+ GiB outputs per arm-rep and ~60-100 GB of deep-gate dump transients; a near-full APFS volume silently distorts write-heavy arms; ENOSPC mid-rep kills a round. Also: an intermediate df sample right after heavy writes can read near-zero free space that recovers within minutes (observed live in Phase 11: 0.35 GiB → 359.42 GiB, no snapshots, no other writer). [VERIFIED: 11-PREPARE-RECORD.md §6]
**How to avoid:** the controller computes the session's full budget (inputs + parity transients + timed transients) and passes it explicitly (D-12); `ensure_disk_headroom` before every measured rep; budget reviews re-sample df after writes settle; sequence deletions (recount db after its dump exists; k21 parity before k31) to cut the peak; free space this session: 365 GiB ≥ floor 136 with the computed full budget fitting (~270-285 GiB peak requirement by our estimate — see Assumptions A3). [ASSUMED for the estimate; floor constants VERIFIED]
**Warning signs:** free-space dropping hundreds of GiB mid-run; df readings that recover after minutes (lag, not exhaustion).

### Pitfall 6: Measurement confounds — thermal, cooldown, write-back, page cache
**What goes wrong:** merge reps are 10× the bytes of count reps; the v2.0 5 s cooldown was tuned for 2.5-min count runs; write-back from rep N lands in rep N+1's window; page cache cannot be fully purged on this host.
**How to avoid:** keep rounds truly interleaved (rotation schedule); cooldown ≥ the protocol default with discretion to raise it for merge-scale reps (CONTEXT discretion; the ladder used the default and stayed linear, supporting the default); record honest per-rep `cache_state`; one discarded warmup per tool; CV% > 10% sets `cv_warning` (a recorded finding, not a failure). [VERIFIED: bench.py:61-62 CV_WARNING_THRESHOLD_PCT=10.0, reduce_arm semantics]
**Warning signs:** later rounds systematically faster within an arm; cv_warning on merge arms.

### Pitfall 7: Route attribution honesty
**What goes wrong:** a route change between reps silently compares different algorithms (milestone Pitfall 3/6). rustkmer merge's route is admission-controlled (`--max-memory` defaults to 50% of system memory; `--merge-mode auto`).
**How to avoid:** keep stderr (`measured_run`), record `route_from_stderr` verbatim — "prefix-cache" only on the tool's own marker, else "not-reported". The ladder's full-scale-relevant runs all recorded "not-reported"; do not infer the route from flags. [VERIFIED: merge_characterize.py:135, 170-178; ladder merges[].route]
**Warning signs:** anyone writing "route=in-memory" without a tool-stated marker.

### Pitfall 8: merge-t1 interpretation (the 2-thread pool contract)
**What goes wrong:** reading `merge-t1` as "one OS thread" — the CLI child's pool is exactly 2 threads at N=1 and 2N+1 at N>1 (`tests/thread_pool_size_tests.rs` cited in the 11-07 record).
**How to avoid:** the methodology block states t1 = like-for-like single-worker scheduling point with the pool contract disclosed (README already carries this wording from the HYG-04 WARNING-2 fix); t1 never enters the verdict computation (phase10 precedent). [VERIFIED: scripts/bench/README.md:466-471; STATE.md 11-07]
**Warning signs:** a report row labeling t1 "1 OS thread"; t1 medians inside a YES/NO computation.

### Pitfall 9: Misreading predicted-vs-measured (milestone Pitfall 14 backstop)
**What goes wrong:** treating a deviation from the ladder predictions (rustkmer 53.8/73.4 s; jellyfish 77.3/105.5 s) as a harness failure — or silently smoothing a large deviation.
**How to avoid:** the predictions are scheduling inputs with a recorded caveat; the measured medians are the deliverable; large deviations are FINDINGS to record and reconcile against the linearity caveat (all four ladder arms were linear, ratios 1.06-1.37 < 2.0 threshold). [VERIFIED: 11-LADDER-RESULTS.json summary.linearity + extrapolated_full_scale.caveat]
**Warning signs:** re-running reps "until the prediction lands"; deleting the caveat line.

### Pitfall 10: Exit-code contract erosion
**What goes wrong:** mapping infrastructure failures to exit 1 (a "measured NO") — corrupting the verdict carrier; or treating exit 1 as a crash to retry.
**How to avoid:** phase10's mapping verbatim: 0/1 are reserved for recorded verdict observations; any raise → exit 2 with no artifact written; exit 3 stays the disk-floor block (bench.py DISK_FLOOR_EXIT). Both verdict outcomes are valid results — exit 1 publishes its artifacts.
**Warning signs:** a `retry` branch around a verdict exit; exit 1 without a written artifact.

### Pitfall 11: Wrap-up ordering (D-03/D-04)
**What goes wrong:** deleting the 86.74 GiB of input artifacts before the verdict evidence is committed — or rewriting `docs/benchmark-report.md` from anything other than the rendered report, reintroducing hand-written numbers.
**How to avoid:** cleanup strictly after report + results JSON + exit-code record are committed; the docs rewrite transcribes the mechanical report's numbers (rendered from committed JSONs), removes the superseded banner, and updates the dataset description; rebuild escape hatch exists (prepare build ~30-90 min).
**Warning signs:** an rm task ordered before the commit task; prose numbers in the doc that the renderer can't reproduce.

## Code Examples

Verified patterns from repo code read this session (paths + line anchors in comments):

### Round-0 gate: revalidate + anchor equality
```python
# Source: scripts/bench/prepare_inputs.py:616-645 (raises on any drift;
# rejects unrecorded .rkdb/.jf; returns verified manifest)
from scripts.bench.prepare_inputs import revalidate_stage, DEFAULT_ARTIFACTS_DIR
manifest = revalidate_stage(DEFAULT_ARTIFACTS_DIR)   # 8 artifacts + 4 jf-input records
# CLI equivalent: python3 scripts/bench/prepare_inputs.py revalidate   (exit 2 on drift)
# Anchor equality (sum-of-counts Totals from the manifest records):
#   k=21: 4,483,548,820 + 4,483,550,383 == 8,967,099,203  (EXACT)
#   k=31: 4,137,846,285 + 4,137,847,745 == 8,275,694,030  (EXACT)
```

### Timed arm execution (per rep)
```python
# Source: scripts/bench/merge_characterize.py:146-178 + bench.py:1371-1382
cache_state = attempt_cache_purge()                      # honest label
ensure_disk_headroom(disk_dir, floor_gb, phase=f"rep round {rnd}",
                     override=disk_override)             # D-12, exit 3 on breach
rep, stderr = measured_run(argv)                         # /usr/bin/time; keeps stderr
route = route_from_stderr(stderr)                        # "prefix-cache"|"not-reported"
```

### Leg-2 recount leg (new, minimal shape reusing proven machinery)
```python
# Count both parts as ONE input list (the independent recount), then
# streaming per-k-mer diff vs the rustkmer merged output:
#   rustkmer count -k K -C --threads 16 -o recount.rkdb -i part_001 part_006
#     (bench.rustkmer_count_cmd with BenchmarkConfig(inputs=[p1, p2]))
#   dump recount.rkdb -> normalize -> LC_ALL=C sort   (_normalized_sorted_dump, via_stdout=False)
#   dump merged.rkdb  -> normalize -> LC_ALL=C sort   (same helper)
#   streaming zip-compare, first difference named     (dump_vs_dump_equal_streaming compare loop)
# No harness code does this today — PARITY-GATE.md §8 maps only Legs 1 and 3.
```

### Verdict stage shape (precedent)
```python
# Source: scripts/bench/phase10.py:771-832 — pure comparison of recorded medians,
# machine-greppable line, both outcomes valid:
#   verdict = f(result per k) with the rule stated verbatim in the verdict doc;
#   print(verdict_line(...))  -> "PHASE11 VERDICT k=… result=… rustkmer_wall_s=…"
#   return EXIT_OK if overall == "YES" else EXIT_NO
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stale 150 GiB disk floor (count-era `-s 10G` regime) | Derived floor **136 GiB** = ceil((93,135,484,166 + 22,927,072,000) × 1.25 / 2^30), import-time tripwire | Phase 11 (11-07, D-10) | Session guard uses measured constants; controller passes the full session budget explicitly (D-12) |
| In-process dump-vs-dump deep gate | Streaming external-sort form (`dump_vs_dump_equal_streaming`) | Phase 11 (11-06) | Only full-scale deep-leg route (WR-01); proven at 318.5M/373.0M lines/side |
| No intermediate-scale merge numbers | Two-point ladder with slopes + linearity verdicts | Phase 11 (11-06, D-07/08/09) | MBENCH-04's predicted-vs-measured inputs; disk-floor transient term |
| `-s 10G` fairness guess | Derived per-part `-s` (1G@k21, 2G@k31, occupancy ≤ 0.75) + recorded occupancy | Phase 11 (11-05, A4 closed) | Hash-size equality precondition holds by construction; merged-output occupancy consequences pre-computed |
| Stale `docs/benchmark-report.md` (v1.0 +420% headline, banner) | Banner landed (HYG-01); full rewrite lands HERE with verdict numbers | Phase 11 → Phase 12 (D-04) | Doc rewritten exactly once, mechanically sourced |

**Deprecated/outdated for this phase:** bench.py's in-process deep gate at scale; `--disk-floor-gb 150` muscle memory; any v2.0 count-era `-s 10G` flag copying into merge arms (merge takes NO `-s`; jellyfish merge `-m` is MIN mode — flag strings never copied between subcommands).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exit-code polarity: recommend exit 0 = rustkmer merge matches-or-beats at both k (NO-INVEST), exit 1 = loses at either k (INVEST), carrying phase10's "0 = measured YES" shape; verdict JSON + greppable line are the primary carriers regardless | Open Questions / Pitfall 10 | Cosmetic-to-moderate: a flipped mapping mislabels CI/consumer semantics; trivially corrected before round 0 — confirm in plan review |
| A2 | Verdict rule: match-or-beat per k (median wall `<=`), NO-INVEST only if rustkmer wins/matches at BOTH k; merge-t1 excluded from the decision (scaling evidence) | Open Questions | The verdict text/exit code changes; the measurements don't — confirm wording at plan time |
| A3 | Deep-gate workdir transient estimate (~60-100 GB peak per k: raw+norm coexist ≈ 2× dump text; dump text ~28-34 GB/side at k31 assuming ~30 B/line) and total session peak ~270-285 GiB vs 365 GiB free | Pitfall 5 | Underestimate → mid-parity exit-3 block (safe, recoverable after cleanup) — the guard fails loud, so wrongness costs time, not corruption |
| A4 | Streaming deep gate at 897M-1.15B lines/side completes in tens of minutes (mechanism proven at 373M lines/side; ~2.4-3× scale-up, same bounded-memory pipeline) | Summary / Architecture | Underestimate → schedule slack; overestimate → wasted buffer; correctness unaffected |
| A5 | Parity-stage merges can double as the protocol's discarded per-tool warmups (recorded as warmup, gate-green before round 1) | Architecture Patterns | If planner prefers separate warmups, session grows ~3-6 min — no validity impact |
| A6 | Timed-stage results docs reuse schema v1 via `phase10.assemble_doc`/`validate_schema` (schema tolerates extra keys; merge arms carry the required name/reps/wall_s/peak_rss_bytes) | Don't Hand-Roll | If a required phase10 field doesn't fit (e.g. per-arm `threads` semantics for jellyfish), fall back to a dedicated evidence `kind` like the ladder's — still not a results-schema fork |
| A7 | rustkmer merge default route at full scale is whatever admission picks (likely in-memory given 50%-of-RAM default vs ~23 GB output) — recorded honestly as "not-reported" unless the tool states a marker | Pitfall 7 | None: the report records the honest label either way; only prose expectations would shift |

## Open Questions (RESOLVED)

All four questions were resolved at plan time; each resolution is encoded in the adopting plan artifact. No open questions remain.

1. **Exit-code polarity and verdict rule wording (A1/A2)** — RESOLVED
   - What we know: D-01 locks "0/1/2 exit-code contract as the verdict carrier"; phase10's contract maps 0 = measured YES / 1 = measured NO / 2 = invalid; wall is the primary axis; both outcomes valid; merge-t1 never enters YES/NO.
   - What's unclear: which polarity INVEST gets, and whether NO-INVEST requires winning at BOTH k or is per-k.
   - Resolution: exit 0 = NO-INVEST (rustkmer matches-or-beats at both k — the phase10 "good-for-rustkmer" shape), exit 1 = INVEST (loses at either k); exact median-wall equality is match-or-beat, no tolerance band; the rule is stated verbatim in the verdict doc. Encoded in 12-01-PLAN.md Task 1 (behavior + action) and must_haves [adjacency]; consumed by 12-02-PLAN.md's exit-code gates.
   - Recommendation: exit 0 = NO-INVEST (rustkmer matches-or-beats at both k — the phase10 "good-for-rustkmer" shape), exit 1 = INVEST (loses at either k); state the rule verbatim in the verdict doc. Confirm at plan review; the JSON + greppable line make the choice auditable either way.

2. **Parity-stage warmup reuse (A5)** — RESOLVED
   - What we know: the protocol includes one discarded warmup per tool; parity requires one merge per tool before timing.
   - What's unclear: whether the parity merges should be recorded AS the warmups (they are untimed-for-verdict either way).
   - Resolution: yes — the parity merges are recorded as warmup-marked records in the parity doc, and the timed stage cites them via warmup_provenance with no additional warmups. Encoded in 12-04-PLAN.md Task 1 (warmup records per A5) and Task 2 (warmup_provenance consumption).
   - Recommendation: yes — record them as warmups in the parity evidence; keeps the timed stage's warmup slot explicit-free and the arm count clean.

3. **Evidence artifact naming/location** — RESOLVED
   - What we know: pattern is committed evidence JSONs in the phase dir (ladder/prepare/rehearsal precedents); exact names are planner discretion.
   - Resolution: the names suggested in Recommended Project Structure are pinned verbatim as files_modified in 12-02-PLAN.md frontmatter (12-REVALIDATE.json, 12-PARITY-K21/K31.json, 12-RESULTS-FULL-K21/K31.json, 12-VERDICT.json, 12-MERGE-REPORT.md, 12-RENDER-PROOF.json), all in the phase dir.
   - Recommendation: the names suggested in Recommended Project Structure; keep the `12-` prefix and one file per stage per k for the resume contract.

4. **WR-02 opportunistic fix scope** — RESOLVED
   - What we know: `--render-report` without `--out` clobbers the default results.json (open warning finding); CONTEXT allows a same-touch fix if the renderer is extended.
   - Resolution: the same-touch trigger does NOT fire — the merge-verdict renderer extension lives entirely in phase11.py, so bench.py's render-report path is not extended and WR-02 stays an open tracked finding (11-REVIEW-DISPOSITION.md). Encoded in 12-01-PLAN.md success criteria.
   - Recommendation: fold it into the renderer-extension task (require explicit `--out`), keeping bench.py's diff minimal and test-covered.

## Environment Availability

| Dependency | Required By | Available | Version / Evidence | Fallback |
|------------|------------|-----------|--------------------|----------|
| 8 input artifacts + manifest | Parity + timed arms | ✓ | Verified on disk this session; sizes match 11-PREPARE-RECORD.md §11 exactly; 86.74 GiB | Rebuild via `prepare_inputs.py build` (~30-90 min) — only if revalidation fails |
| Free disk ≥ floor (136 GiB) + session transients | Round-0 gate + per-rep checks | ✓ | 365 GiB free on /System/Volumes/Data this session | Free more space (human) — floor fails loud with stated shortfall (exit 3) |
| `rustkmer` release binary | All rustkmer arms + recount + stats + dump | ✓ | sha256 `4539b893…d023b` == ladder provenance [VERIFIED this session] | Rebuild `cargo build --release` would CHANGE the hash and break prediction attribution — escalate, don't silently rebuild |
| jellyfish | jellyfish-merge arm + dump -c | ✓ | 2.3.1 pinned at /opt/homebrew/bin/jellyfish [VERIFIED this session] | None — pinned comparator; do not upgrade |
| Python 3.11+ + pytest | Controller + tests | ✓ | 3.13.11 system; `.venv313` has pytest (644 bench tests collected via `.venv313/bin/python -m pytest`) [VERIFIED this session] | — |
| `/usr/bin/time`, `sort`, `awk`, `wc` | Measurement + streaming gates | ✓ | All present [VERIFIED this session] | — |
| `sudo -n purge` (cache purge) | Honest cache labels only | ✓/✗ (attempt-dependent) | Attempted per rep; failure records `unavailable` honestly — never blocks | None needed (labels are the honesty mechanism) |
| Graph/knowledge-graph context | Research cross-refs | ✗ (disabled) | `gsd-tools graphify status` → disabled | Not needed — all context is in-repo |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none blocking; the sudo-purge availability only shapes `cache_state` labels by design.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (host `.venv313`; Python 3.13.11) over `scripts/bench/tests/` — 644 tests collected [VERIFIED this session] |
| Config file | none needed for bench tests (pytest defaults; `pyo3/pyproject.toml` pytest config does not govern `scripts/bench`) |
| Quick run command | `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py scripts/bench/tests/test_merge_arms.py -q` |
| Full suite command | `.venv313/bin/python -m pytest scripts/bench/tests/ -q` (CI equivalent: `python3 -m unittest discover -s scripts/bench/tests -t .` — exits non-zero until the D-05 path retarget lands) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MBENCH-03 | Controller stage isolation + exit-code contract (0/1/2; infra → 2) | unit | `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` | ❌ Wave 0 |
| MBENCH-03 | Round-0 gate: revalidate drift → loud failure; anchor equality asserted from manifest records | unit (fixtures) + session evidence | `... test_phase11_verdict.py -q` + the `revalidate` verb run in-stage | verb ✅ (test_prepare_inputs.py); controller gate ❌ Wave 0 |
| MBENCH-03 | Counterbalanced schedule shape (3 arms × 3 reps, rotated starts) | unit | schedule-shape test over `rotation_schedule` | ❌ Wave 0 (function ✅ output_stage.py) |
| MBENCH-03 | Parity legs green before results acceptance; Leg-2 recount diff raises on first mismatch | unit (fixture dumps) + live session evidence | `... test_phase11_verdict.py -q` (streaming pipeline fixtures) | ❌ Wave 0 (Leg-2 leg is new code) |
| MBENCH-03 | Full-scale session itself | session evidence (not unit-testable) | the staged runs; verified by gates green + schema-valid results + recorded exit code | n/a — the deliverable |
| MBENCH-04 | Renderer: no measurement literals; entry-rate/byte-rate formulas; asymmetry sentence present; predicted-vs-measured section carries the caveat | unit | `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` (renderer tests) | ❌ Wave 0 |
| MBENCH-04 | Byte-identical re-render proof | unit (render twice on fixture JSONs, byte-compare) + live proof recorded in-stage | renderer test + the render stage's recorded proof | ❌ Wave 0 (pattern ✅ phase10/bench) |

### Sampling Rate

- **Per task commit:** quick run command (new controller/renderer tests + `test_merge_arms.py`).
- **Per wave merge:** full suite command.
- **Phase gate:** full suite green (modulo the known `test_verify_threads.py` ~50% macOS `sample`-race flake — purge stale `target/` before trusting a red [VERIFIED: STATE.md blockers]) + the session's own gates green + exit-code record + re-render proof before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `scripts/bench/tests/test_phase11_verdict.py` — controller contract (stages, exit codes, schedule shape, Leg-2 recount fixtures, renderer byte-identity + metric formulas). Covers MBENCH-03/04 unit surface.
- [ ] Recount-leg fixture pair (small synthetic .rkdb dumps) driving the streaming diff GREEN/RED.
- [ ] Renderer fixture JSONs (two arms, one k) exercising entry-rate/byte-rate/asymmetry/predicted-vs-measured sections.
- [ ] NOTE (pre-phase, not Wave 0): the D-05 `/gsd-quick` task fixes the 3 `test_phase10_verdict.py` archived-path reds BEFORE planning — verified live this session (3 failed: FileNotFoundError on `.planning/phases/10-benchmark-verdict/...`; correct location is `.planning/milestones/v2.0-phases/10-benchmark-verdict/`). 98 tests in that file pass.

## Security Domain

`security_enforcement: true`, ASVS level 1 (config). This is a local, offline measurement phase: no network I/O, no secrets, no auth/session surface, no new untrusted input classes beyond file bytes already gated.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local harness |
| V3 Session Management | no | N/A — no sessions |
| V4 Access Control | no | N/A — single-user dev host; artifacts dir outside repo (D-03 heritage) |
| V5 Input Validation | yes | Fail-loud parsing (`normalize_dump_lines`/awk exit-2 on malformed lines, T-11-09); `validate_path` on every argv path; `revalidate_stage` rejects unrecorded artifacts; `validate_schema`/`validate_provenance` before any document lands |
| V6 Cryptography | no (no crypto feature) | sha256 used for integrity fingerprints only (stdlib `hashlib`) — never hand-rolled primitives |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Results/report tampering (a hand-edited number shipping as a verdict) | Tampering | Mechanical renderer + byte-identical re-render proof (T-04-07); provenance blocks on every artifact; `publish_atomic` never destroys prior evidence |
| Silent input swap between rounds | Tampering | Round-0 revalidation (re-hash ×8) + per-stage fingerprint records; unrecorded artifacts rejected loud (Pitfall 8) |
| Command injection via paths | Tampering | List-form subprocess argv everywhere (no `shell=True` in the merge paths); `validate_path` [VERIFIED: bench.py:353-366] |
| Disk exhaustion degrading measurements (local DoS) | Denial of Service | Derived floor + exit-3 hard block with stated shortfall + explicit override semantics (D-11/D-12) |
| Vacuous gate (checks that cannot fail) | Tampering | GREEN/RED unit proofs for every gate; empty-dump/malformed-line loud errors (MBENCH-02/empty probes) |

## Sources

### Primary (HIGH confidence — read directly this session)

- `scripts/bench/bench.py` — schema/parity/floor/protocol/renderer primitives (lines cited inline: 45-119 floor+tripwire, 338-366 merge cmds, 502-532 schema, 1276-1382 schedule+disk guards, 1420-1635 parity gates, 1638-1719 protocol, 1743-1968 run_bench incl. WR-01 wiring at 1857-1859, 2037-2078 `_arm_row`)
- `scripts/bench/merge_characterize.py` — streaming deep gate + measured_run + route (48-49 stdlib contract, 135 route regex, 146-178 measured_run/route, 181-322 streaming pipeline, 448-657 run_rung)
- `scripts/bench/phase10.py` — controller precedent (1-125 contract+constants, 771-832 verdict, 1677-1739 render/publish, 2539-2622 stage dispatch + exit mapping)
- `scripts/bench/prepare_inputs.py` — revalidate verb (613-662, 668-721 CLI)
- `scripts/bench/output_stage.py` — `rotation_schedule` (121-140)
- `.planning/phases/11-merge-characterization-harness-prep/PARITY-GATE.md` — the gate definition of record (§2-§8)
- `.planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md` — artifact inventory, -s derivation, occupancy, retention (§2, §4, §7, §10, §11)
- `.planning/phases/11-merge-characterization-harness-prep/11-LADDER-RESULTS.json` — slopes, linearity, byte rates, full-scale predictions, binary provenance
- `.planning/phases/11-merge-characterization-harness-prep/11-FLOOR-DERIVATION.md` — 136 GiB derivation (§1-§5)
- `.planning/phases/11-merge-characterization-harness-prep/11-REVIEW-DISPOSITION.md` — WR-01..04 + IN-01..05 open findings
- `.planning/phases/11-merge-characterization-harness-prep/11-VERIFICATION.md` — verifier warnings consumed by this phase (WR-01 mitigation, D-05 reds, stale CLAUDE.md mirror)
- `.planning/phases/12-full-scale-merge-verdict/12-CONTEXT.md` — D-01..D-05 + carried constraints (verbatim source for User Constraints)
- `.planning/REQUIREMENTS.md` — MBENCH-03/04 definitions, out-of-scope table, traceability
- `.planning/ROADMAP.md` §Phase 12 — success criteria 1-4, Note, research flag "none"
- `.planning/PROJECT.md` — v2.0 verdict reference numbers (144.69/147.08 s walls; 43.97/68.52 GiB)
- `.planning/research/PITFALLS.md` — binding pitfalls 1, 2, 3, 5, 6, 7, 8, 14
- `.planning/research/SUMMARY.md` — merge decision axes, table stakes, asymmetry sentence
- `scripts/bench/README.md` — rehearsal docs (WR-04 defect at 463-464), t1 pool-contract wording (466-471)
- `docs/benchmark-report.md` — current superseded-banner state (rewrite target, D-04)
- Live probes this session: artifact `ls` + sizes; `df` 365 GiB free; binary sha256 (`shasum -a 256`); `jellyfish --version`; `rustkmer merge --help` flag surface; pytest collection (644 tests); D-05 red reproduction (3 failed / 98 passed); `.planning/config.json` flags

### Secondary (MEDIUM confidence)

- None needed — the ROADMAP research flag is "none"; no external/web sources were consumed. All search-provider flags in `.planning/config.json` are false and every load-bearing fact is repo-anchored.

### Tertiary (LOW confidence)

- Assumption-tagged estimates A2-A4 (deep-gate runtime and transient-size extrapolations beyond the proven 373M-line rung) — guarded by loud disk guards and recorded findings, never by silence.

## Metadata

**Confidence breakdown:**
- Session mechanics / standard stack: HIGH — every primitive read in source this session; controller precedent proven in v2.0.
- Numbers (anchors, slopes, predictions, floor, byte rates): HIGH — all read from committed Phase 11 evidence files quoted verbatim above.
- Architecture (stage structure, Leg-2 shape, renderer extension): HIGH on constraints, MEDIUM on the discretionary details (A1/A2/A5/A6 flagged for plan review).
- Pitfalls: HIGH — WR-01 verified in code at bench.py:1857-1859; others carried from GREEN/RED-proven milestone research and live Phase 11 records.

**Research date:** 2026-11-17
**Valid until:** 2026-12-17 (stable — measurement phase over a frozen artifact set; re-verify only the binary hash and free disk if planning slips past ~30 days)
