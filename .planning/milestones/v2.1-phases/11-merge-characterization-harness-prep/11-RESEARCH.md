# Phase 11: Merge Characterization & Harness Prep - Research

**Researched:** 2026-11-16
**Domain:** Measurement-engineering prep on a stdlib-only Python benchmark harness (`scripts/bench/`) — jellyfish-merge arm extension, three-way parity gate, prepare-inputs stage, characterization ladder, dress rehearsal, evidence-hygiene workflows
**Confidence:** HIGH — every harness integration point below was re-read from the current tree this session with file:line anchors and verbatim quotes; environment (binaries, dataset, disk) probed directly; jellyfish 2.3.1 semantics are pinned by milestone research and are cited, not re-derived

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Input Artifacts (full-scale merge inputs)**
- **D-01:** All 8 full-scale merge input artifacts (part_001/part_006 × `.rkdb`/`.jf` × k=21/31, ~70 GiB total) are **pre-built in Phase 11**, not at Phase 12 round 0. Rationale: the dress rehearsal and characterization then validate the real fingerprint/Total-revalidation path, and Phase 12 starts clean with zero setup risk. Verified 2026-11-16: no v2.0-era `.rkdb`/`.jf` artifacts survive on disk — regeneration is the only option. — **Reversibility:** reversible — artifacts are rebuildable from source data by re-running the prepare stage (~30–90 min).
- **D-02:** Retention: keep all artifacts on disk **until the Phase 12 verdict lands**, then clean up. Do NOT delete `.jf` early (parity-green deletes cost more than ~22 GiB of disk: `.jf` regeneration forces re-running jellyfish merge arms).
- **D-03:** Artifacts live in a **dedicated directory next to the source data, outside the repo** — e.g. `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` (exact name planner's choice). Never inside the repo tree (mis-commit risk).
- **D-04:** Artifacts are built by a **harness built-in stage** (prepare-inputs subcommand or equivalent in `scripts/bench/`) that records sha256 + Total + command-line provenance automatically. No manual fingerprint transcription. Phase 12 round-0 revalidation consumes the same recorded provenance. — **Reversibility:** costly — provenance records feed the Phase 12 round-0 gate and the verdict's methodology block; changing the record format after the fact means re-rendering/re-validating everything downstream of it.

**Stale Report Resolution (HYG-01)**
- **D-05:** `docs/benchmark-report.md` gets a **superseded banner now** (pointing to v2.0 milestone evidence in `.planning/milestones/`) + the dataset-description correction (six single-member gzip parts ~16.7 GB, not "two parts ~5.2 GB"); the **full v2.0-based rewrite is deferred until after the Phase 12 merge verdict** so the doc is rewritten once, including merge results (see Deferred).
- **D-06:** Drift sweep breadth: the two named artifacts (`docs/benchmark-report.md`, PROJECT.md dataset description) **plus a grep sweep** of `docs/`, `README.md`, `USER_GUIDE.md`, `PROJECT_SUMMARY.md` for same-class drift (stale dataset description, stale "+420%" cites). Factual fixes only — no document rewrites (a full docs audit is /gsd-docs-update territory, out of scope).

**Characterization Ladder (intermediate-scale)**
- **D-07:** **Two-point ladder** (e.g. ~10% and ~40% of part scale) — slope + coarse linearity check is sufficient for Phase 12 scheduling and the disk-floor derivation. The MBENCH-04 predicted-vs-measured check at full scale is the backstop against residual non-linearity.
- **D-08:** Ladder inputs are **real-data slice pairs** via the existing `random_slice.py`/`make_slice.sh` mechanism, each side running the complete prepare→count→merge chain. This also exercises the prepare-inputs stage (D-04) on real data before it matters.
- **D-09:** **Both tools are characterized** on the same slice pairs — `jellyfish merge` AND `rustkmer merge`. This gives MBENCH-04's cost-model check a fitted curve instead of an assumed slope and surfaces rustkmer-side scaling behavior (route switches, spill) before full scale.

**Disk Pre-flight**
- **D-10:** The raised disk floor is a **derived formula**: input artifacts + largest single-arm transient (extrapolated from the D-07/D-09 ladder) + safety margin — derived in Phase 11 from measured sizes and written into the bench default (replacing the 150 GiB default sized for count artifacts). Re-derive if inputs change. — **Reversibility:** costly — the floor guards the Phase 12 full-scale session; a mis-derived floor discovered mid-session wastes hours, so the derivation and its inputs are recorded evidence.
- **D-11:** Below the floor → **hard block with the shortfall stated** + an explicit override flag (e.g. `--disk-floor-override`) for deliberate runs. No silent continue.
- **D-12:** Check timing: **full-budget check before round 0** (all arms + transients) + **lightweight re-check before each rep** (catches other processes filling the disk during multi-hour sessions).

### Claude's Discretion
- Dress rehearsal breadth: full protocol at slice scale (all arms, both k) — success criterion 2 already says "full-protocol"; both k is cheap at slice scale.
- Parity-gate written spec: exact document location and format (phase-dir doc vs docs/) — planner picks; the content requirements are fixed by MBENCH-02 (three legs, per-k-mer exact, `total_kmers` definition named per check).
- Characterization results format/location: follow existing evidence-JSON patterns.
- prepare-inputs stage CLI shape and naming.
- Whether a `phase11.py` staged controller is created in this phase or deferred to Phase 12 (ROADMAP marks the controller optional for the Phase 12 session).
- HYG-02/HYG-03 run through the named workflows (`/gsd-validate-phase`, `/gsd-secure-phase`) as their requirements state; HYG-04 stays opportunistic per the backlog rule (fix in the same touch when milestone work touches 999.1–999.3 files).

### Deferred Ideas (OUT OF SCOPE)
- **Full v2.0-based rewrite of `docs/benchmark-report.md`** including merge-verdict sections — after the Phase 12 verdict lands, so the doc is rewritten once with complete current data (D-05). Needs a home at v2.1 close (candidate: Phase 12 wrap-up task or a post-verdict quick task).
- (Carried from milestone scope, unchanged: MBF-01 flag sweep, MBF-02 N-way/r1+r2, PEXT-05 — post-verdict v2.2+ items, not this phase.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MBENCH-01 | Harness gains jellyfish merge arms — two same-`-m/-s/-C` jellyfish per-part count artifacts plus a `jellyfish merge` command arm wired into bench.py's counterbalanced protocol, with input fingerprints, provenance, honest per-rep `cache_state` | Extension points verified at `bench.py:1420-1432` (arm_specs), `bench.py:252-280` (`jellyfish_count_cmd`), `bench.py:283-286` (`build_merge_cmd` — no `--num-threads` yet), `bench.py:1401-1404` (only ONE `.jf` artifact exists today); prepare-inputs stage design (Pattern 1); per-part `-s` sizing arithmetic (Pitfall 3); `-s` merge-equality constraint cited from milestone FEATURES.md Part 1 |
| MBENCH-02 | Three-way parity gate defined in writing and executed BEFORE timing; slice-scale dump-vs-dump deep gate; `total_kmers` definition named per check | Gate spec content checklist (Pattern 2); union parity anchors verified in committed Phase-10 JSONs (897,266,581 / 8,967,099,203 k=21; 1,146,353,600 / 8,275,694,030 k=31); `rustkmer dump` empirically verified at k=21 this session; `stats` JSON keys `unique_kmers`/`total_kmers` verified (`bench.py:289-301`) |
| MBENCH-05 | CI degradation rung for merge arm on the existing synthetic two-part arm; no second results schema | Single-rep CI path verified at `bench.py:1450-1464` (rustkmer-only, merge arm present, no jellyfish); SCHEMA_VERSION stays 1 (`bench.py:44`, `validate_schema` :422-452 tolerates new arm names); CI workflow reads `.github/workflows/benchmark.yml` (synthetic bench + `unittest discover scripts/bench/tests`) |
| HYG-01 | `docs/benchmark-report.md` drift resolved before the Phase 12 verdict; dataset description corrected in PROJECT.md/docs | Stale headline verified (`docs/benchmark-report.md` k=21 "+420.0%" on deleted CRR2044018); **renderer hardcodes the v1.0 narrative** (`bench.py:1883-1892`, `bench.py:1942-1947`) — banner strategy must account for the generated-file contract; stale PROJECT.md lines verified (:88, :96); six-part directory verified on disk with exact byte sizes |
| HYG-02 | Nyquist validation records for Phases 5–8 (per `/gsd-validate-phase`) | Gap inventory verified: v2.0 archive has `07-VALIDATION.md` (draft) and `09/10-VALIDATION.md`; **05, 06, 08 have NO `*VALIDATION.md`** (they do have `VERIFICATION.md`); records belong in `.planning/milestones/v2.0-phases/<dir>/` |
| HYG-03 | SECURITY.md threat-model verification for Phases 9–10 (per `/gsd-secure-phase`) | No SECURITY.md exists anywhere (repo root, `.planning/`, v2.0 archive — verified); v1.0 precedent format read (`04-SECURITY.md` frontmatter: `phase/slug/status/threats_open/asvs_level/created`); targets: `09-python-parity/09-SECURITY.md`, `10-benchmark-verdict/10-SECURITY.md` |
| HYG-04 | Backlog 999.1–999.3 resolved opportunistically when milestone work touches their files | Item-to-file mapping verified (v1.0-MILESTONE-AUDIT.md:65-67): 999.1 → `pyo3/build.rs`, 999.2 → venv site-packages shadowing, 999.3 → `v1.0-phases/03-memory-safety/deferred-items.md` chunk-sweep claim; plus WARNING-2 (`scripts/bench/README.md:321` stale pool-size formula) which Phase 11 DOES trigger by touching `scripts/bench/` |
</phase_requirements>

## Summary

Phase 11 is measurement engineering on an already-shipped harness: no Rust changes, no new Python packages (`bench.py` is stdlib-only by contract), no new external tools. The milestone research (`.planning/research/{SUMMARY,FEATURES,ARCHITECTURE,PITFALLS,STACK}.md`, 2026-11-16) pinned jellyfish 2.3.1 merge semantics and the build order; this phase-level research re-verified every integration point against the current tree, probed the environment (jellyfish 2.3.1 present, six dataset parts byte-identical to Phase 10's committed fingerprints, 323 GiB free), and resolved the details the milestone research left open at phase granularity: where each arm/gate/renderer change lands in `bench.py`, what the parity-gate spec must contain, how the prepare-inputs stage records provenance so Phase 12 round-0 can revalidate from records alone, and how the hygiene items execute through their named workflows.

Five phase-level findings materially shape planning and are **not** in the milestone research: (1) the report renderer hardcodes the v1.0-era narrative — the CRR2044018 substitute-dataset provenance block (`bench.py:1942-1947`) and the attempt-1 halt note (`bench.py:1883-1892`) — so a hand-added superseded banner on the generated doc must be planned knowing any future re-render drops it, and the post-Phase-12 rewrite will be produced by a renderer that still carries that narrative unless this phase adjusts it; (2) bench.py's full-mode provisioning cannot express the pinned part_001+part_006 pair — `gather_inputs` on a directory returns the six parts sorted and `provision_full` takes the first two (`bench.py:667-674` → 001+002), and `--merge-input` is slice-mode-only (`bench.py:529-547`), so the merge arrangement needs explicit part-pair resolution (phase10.py's token-based pattern is the in-repo precedent); (3) the per-part jellyfish `-s` cannot reuse `DEFAULT_HASH_SIZE = "10G"` — that value was sized for union counts (v2.0 union `.jf` RSS anchors: 46.84 GiB at k=21 / 88.00 GiB at k=31), and four per-part `-s 10G` artifacts would occupy hundreds of GiB, contradicting D-01's ~70 GiB budget; the `-s` must be derived from measured per-part distinct counts (which do not exist yet — they are new data this phase produces); (4) the parity pre-gate anchors are the committed Phase-10 **union** values — per-part artifacts sum to them (Total is additive over disjoint read sets; merged Distinct must equal the union Distinct exactly), while per-part Distinct/Total values themselves are first-time measurements the prepare stage must record; (5) `rustkmer dump` was empirically verified at k=21 this session (65,000/65,000 entries; 20 B/entry confirmed on disk; EOF-terminated loop) — the deep dump-vs-dump gate's rustkmer side works, and a stale 12-byte entry-size heuristic in `dump.rs` is inert dead code on the v2 path.

**Primary recommendation:** extend `scripts/bench/` additively in the milestone research's shape (new command builders, arm specs, merge parity gates, prepare-inputs stage, dump-vs-dump comparator, ordering assertion, disk-floor derivation + override + per-rep recheck, unit tests in `scripts/bench/tests/`), write the parity-gate spec as a phase-dir document before any timed run, drive the characterization ladder and dress rehearsal through a phase10-style staged flow, and close HYG-01/02/03 through banner+sweep, `/gsd-validate-phase` (phases 5, 6, 8; confirm 7), and `/gsd-secure-phase` (phases 9, 10) — fixing WARNING-2 (`README.md:321`) in the same touch as any `scripts/bench/README.md` edit.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| prepare-inputs stage (build 8 artifacts, record provenance, revalidate) | Python harness (`scripts/bench/`) | External CLI binaries (`rustkmer`, `jellyfish`) as measured subprocesses | Pure orchestration + record-keeping; the Rust side is explicitly frozen this phase (CONTEXT: "No Rust code changes") |
| Extended merge arms + counterbalanced protocol wiring | Python harness (`bench.py`) | — | All protocol machinery lives in bench.py; arms are data (spec dicts) |
| Three-way parity gate (spec + implementation + slice-scale proof) | Python harness + phase-dir spec doc | `rustkmer dump` / `jellyfish dump -c` subprocesses | Spec is a document (planner picks location, CONTEXT discretion); implementation mirrors the existing count-parity gate |
| Characterization ladder (2-point, both tools) | Python harness + slice mechanism (`random_slice.py`/`make_slice.sh`) | CLI binaries | Reuses D-08's named slice mechanism; results as evidence JSONs |
| Dress rehearsal (full protocol at slice scale) | Python harness (phase10-style staged flow) | — | phase10.py is the in-repo controller precedent |
| CI degradation rung (MBENCH-05) | Python harness + GitHub Actions (`benchmark.yml`) | — | Extends the existing synthetic single-rep path; no schema fork |
| Disk pre-flight (derive floor, hard block, override, per-rep recheck) | Python harness (`bench.py`) | — | `check_disk_floor` exists; extension is additive |
| HYG-01 stale-report banner + dataset correction + drift sweep | Docs/planning artifacts | Python renderer (narrative decision) | D-05/D-06 fixed breadth |
| HYG-02 / HYG-03 evidence-debt workflows | GSD workflows (`/gsd-validate-phase`, `/gsd-secure-phase`) | Archive dirs under `.planning/milestones/v2.0-phases/` | Named-workflow requirement (CONTEXT discretion item); not hand-rolled |
| HYG-04 opportunistic backlog | In-touch edits | — | Same-touch rule only; remaining items stay tracked |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.11+ floor (host: 3.13.11) | All harness work; `bench.py` bans third-party imports by docstring contract | `bench.py:25-26`: "Python 3.10+ stdlib only — no third-party imports, no pip installs" [VERIFIED: scripts/bench/bench.py:25-26] |
| jellyfish (pinned comparator) | 2.3.1 at `/opt/homebrew/bin/jellyfish` | per-part count artifacts + `jellyfish merge` arms + `dump -c` for the deep gate | The milestone's pinned comparator; present and version-verified this session [VERIFIED: `jellyfish --version` probe, 2026-11-16] |
| rustkmer release binary | 0.5.0 (`target/release/rustkmer`, built 2026-11-16) | count/merge/dump/stats subprocesses; never a debug build | Harness convention (`bench.py:57` `DEFAULT_RUSTKMER`); measured this session [VERIFIED: binary probe] |
| `/usr/bin/time` | OS-provided | wall + `max(rss, phys_footprint)` per rep; harness-internal clocks banned | `measure` at `bench.py:173-186`; README bans internal clocks [VERIFIED: scripts/bench/bench.py:173-186] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `scripts/bench/output_stage.py` rotation_schedule | in-repo | Per-arm counterbalanced rotation for the extended arm set | Dress rehearsal / any new controller (phase10.py already imports it, `phase10.py:95`) |
| `scripts/bench/random_slice.py` + `make_slice.sh` | in-repo | Seeded random-record slice pairs for the D-08 ladder | Ladder provisioning |
| `scripts/bench/gen_synthetic.py` | in-repo | Synthetic two-part inputs for the CI rung (MBENCH-05) | Synthetic mode + tests |
| `python3 -m unittest discover -s scripts/bench/tests -t .` | stdlib | Harness regression net (existing suite; CI runs it in `benchmark.yml`) | Every harness change |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| bench.py `round_schedule` (per-tool alternation, `bench.py:1196-1205`) | `output_stage.rotation_schedule` (per-arm rotation, `output_stage.py:121-137`) | `round_schedule` alternates only TOOL order; arm order within a tool is fixed across rounds. For 6 arms, per-arm rotation counterbalances thermal/order bias better and is the phase10 precedent. Either works; per-arm rotation is the stronger default for the new arms |
| phase11.py controller now | defer to Phase 12 | CONTEXT leaves this open; the dress rehearsal can be driven as staged bench.py invocations. A controller adds resumability + session provenance; defer is cheaper |
| Hand-written parity spec in `docs/` | phase-dir doc (`.planning/phases/11-.../PARITY-GATE.md`) | Phase-dir doc travels with the phase evidence and does not imply user-facing docs status; planner's call per CONTEXT |

**Installation:**
```bash
# Nothing to install. All tooling is present and pinned:
#   python3 3.13.11 (floor 3.11 per pyproject), jellyfish 2.3.1, target/release/rustkmer 0.5.0
# The harness is stdlib-only by contract — any pip install in scripts/bench would violate it.
```

**Version verification:** performed this session — `jellyfish --version` → 2.3.1; `python3 --version` → 3.13.11; `target/release/rustkmer --version` → rustkmer 0.5.0. No registry packages involved.

## Package Legitimacy Audit

**N/A — this phase installs zero external packages.** `scripts/bench/` is stdlib-only by documented contract (`bench.py:25-26`), the Rust side is frozen (CONTEXT domain statement), and the only external executables (jellyfish 2.3.1, rustkmer 0.5.0) are already-pinned local binaries, not packages fetched from any registry. No `checkpoint:human-verify` install gates are needed.

## Architecture Patterns

### System Architecture Diagram

```text
                            PHASE 11 DATA FLOW
╔═══════════════════════════════════════════════════════════════════════╗
║  SOURCE DATA (outside repo, verified on disk)                         ║
║  /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/         ║
║  six single-member gzip parts; pinned pair = part_001 + part_006      ║
╚──────────────┬────────────────────────────────────────────────────────╝
               │  (D-08) seeded random-record slice pairs via
               │  random_slice.reservoir_slice / make_slice.sh
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PREPARE-INPUTS STAGE (new, scripts/bench/)         [D-01/D-03/D-04] │
│  prepare  ──► per-part count:  rustkmer count  ×2 parts ×2 k → .rkdb │
│                jellyfish count ×2 parts ×2 k → .jf  (same -m/-s/-C)  │
│  order: .rkdb first → read measured per-part Distinct                │
│         → derive/validate shared -s  → build .jf  → jellyfish info   │
│  records: manifest JSON {path,size,sha256,cmdline,Distinct,Total,    │
│           k,canonical,-s,source fingerprints,provenance,created}     │
│  revalidate ──► re-hash + re-stats, compare against manifest only    │
└──────┬──────────────────────────────────────────────┬────────────────┘
       │ artifacts (outside repo: CRR1936095-merge-inputs/)        │
       ▼                                             ▼
┌──────────────────────────────┐   ┌───────────────────────────────────┐
│ CHARACTERIZATION LADDER      │   │ DRESS REHEARSAL (slice scale,     │
│ (D-07/D-09) 2 slice pairs    │   │ full protocol, both k)            │
│ ~10% and ~40% of part scale  │   │ all arms incl. jellyfish-count-B, │
│ each side: prepare→count→    │   │ jellyfish-merge, merge, merge-t1  │
│ merge; jellyfish AND         │   │ 3-way parity gate FIRST           │
│ rustkmer merge characterized │   │ (dump-vs-dump deep gate at slice) │
│ → wall/output-size slope     │   │ → green before any timed round    │
└──────┬───────────────────────┘   └──────┬────────────────────────────┘
       │ slope + sizes                    │ gates + evidence JSONs
       ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ DISK PRE-FLIGHT (D-10/11/12): floor = inputs + largest transient     │
│ (ladder-extrapolated) + margin → replaces DEFAULT_DISK_FLOOR_GB=150; │
│ full-budget check before round 0 + lightweight per-rep re-check;     │
│ hard block exit 3 + --disk-floor-override                            │
└──────────────────────────────────────────────────────────────────────┘
       │
       ▼  Phase 12 consumes: extended harness + written PARITY-GATE spec
          + prebuilt artifacts + recorded provenance (round-0 revalidation)

  PARALLEL HYGIENE TRACK (no measurement coupling):
  HYG-01 banner+dataset fix+grep sweep → HYG-02 /gsd-validate-phase (5,6,8;
  confirm 7) → HYG-03 /gsd-secure-phase (9,10) → HYG-04 same-touch items
```

Primary use case traceable: source parts → prepare (fingerprinted artifacts) → ladder (slope + disk numbers) → dress rehearsal (gates green at slice scale) → everything Phase 12 needs exists and is recorded.

### Recommended Project Structure

```text
scripts/bench/
├── bench.py                  # MODIFIED: jellyfish_merge_cmd, merge cmd builders
│                             #   (+ --num-threads), arm specs, merge parity gates,
│                             #   dump-vs-dump comparator, ordering assertion,
│                             #   disk-floor derivation/override/per-rep recheck
├── prepare_inputs.py         # NEW: build/revalidate/manifest stage (D-04)
├── merge_characterize.py     # NEW or folded into controller: 2-point ladder
├── phase11.py                # OPTIONAL (CONTEXT discretion): staged rehearsal
│                             #   controller modeled on phase10.py
├── README.md                 # MODIFIED: new stage docs + WARNING-2 fix (:321, same touch)
├── tests/
│   ├── test_prepare_inputs.py    # NEW
│   ├── test_merge_arms.py        # NEW (cmd shapes, ordering assertion, gates GREEN/RED)
│   ├── test_disk_floor.py        # NEW (derive/block/override/per-rep)
│   └── (existing: test_schema.py, test_cmd_matrix.py, test_merge_input.py,
│        test_render_report.py, test_degradation.py, ... extended)
└── baselines/                # parity reference records (existing pattern)
docs/benchmark-report.md      # HYG-01 banner + dataset fix
.planning/phases/11-merge-characterization-harness-prep/
└── PARITY-GATE.md            # RECOMMENDED home for the written gate spec (planner ratifies)
.planning/milestones/v2.0-phases/
├── 05-measurement-regression-harness/05-VALIDATION.md   # HYG-02 (new)
├── 06-parallelism-correctness-hot-path/06-VALIDATION.md # HYG-02 (new)
├── 07-shared-counting-engine/07-VALIDATION.md           # HYG-02 (exists, draft — confirm/complete)
├── 08-output-pipeline-rkdb-v2-parity/08-VALIDATION.md   # HYG-02 (new)
├── 09-python-parity/09-SECURITY.md                      # HYG-03 (new)
└── 10-benchmark-verdict/10-SECURITY.md                  # HYG-03 (new)
```

### Pattern 1: prepare-inputs stage (D-01/D-03/D-04)

**What:** a `scripts/bench/prepare_inputs.py` stage (name per planner discretion) with three verbs: `build` (run the 8 per-part counts + record a manifest), `revalidate` (re-hash + re-stats, compare against the manifest), and `manifest` (print/emit the record). Artifacts go to the data-adjacent dir outside the repo (D-03); nothing lands under `scripts/bench/scratch/` (that default is inside the repo — `bench.py:49` `DEFAULT_SCRATCH = HERE / "scratch"`).

**Build order inside the stage (matters for the `-s` decision):**
1. Build the 4 per-part `.rkdb` first (rustkmer count per part per k) — these produce the **first-ever per-part Distinct measurements**.
2. Read measured per-part Distinct per k; derive or validate the shared jellyfish `-s` (occupancy assertion: `max_per_part_distinct ≤ ~0.75 × slots` keeps jellyfish's load headroom; jellyfish auto-grows when over — correct but slow, and auto-grow mid-artifact-build would change provenance).
3. Build the 4 per-part `.jf` with the identical `-m <k> -s <s> -C` per k-pair (merge refuses differing hash sizes — milestone FEATURES.md Part 1, pinned).
4. Record `jellyfish info` output (actual slots, occupancy) per artifact — the hash-size fairness discipline ("state occupancy") from milestone FEATURES.md.
5. Write the manifest: per artifact `{path, size_bytes, sha256, command_line, k, canonical, hash_size, distinct, total, source_fingerprints[{path,size_bytes,sha256}], provenance (reuse `binary_provenance` shape), created}`. Reuse `fingerprint()` (`bench.py:304-312`) and the `PROVENANCE_KEYS` provenance shape (`bench.py:322-323`) so Phase 12 round-0 revalidation consumes records, not memory (D-04).

**Pre-gate anchors (verified this session from the committed Phase-10 JSONs):** the union values are what per-part artifacts must reconcile to, not match individually:
- k=21: union Distinct **897,266,581**, union Total **8,967,099,203** [VERIFIED: `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k21.json` — arms carry keys `total_kmers`/`unique_kmers`; total=8967099203 read verbatim]
- k=31: union Distinct **1,146,353,600**, union Total **8,275,694,030** [VERIFIED: `10-results-full-k31.json`, same keys]
- Invariants for the prepare pre-gate: `p1.Total + p2.Total == union Total` (Total is additive over disjoint read sets; jellyfish merge sums counts by default — milestone FEATURES.md Part 1) and `merged.Distinct == union Distinct` (disjoint key-spaces). Per-part Distinct values are NEW records with no prior committed value.
- Source-part fingerprints already committed and still valid on disk: part_001 = 2,785,381,389 bytes sha256 `dae91042e42c1a05…`; part_006 = 2,785,388,289 bytes sha256 `b197f16c31dd3409…` [VERIFIED: 10-results-full-k21.json input_fingerprint + on-disk `ls` byte sizes match exactly]

### Pattern 2: parity-gate written spec (MBENCH-02)

**Content checklist (fixed by MBENCH-02; format/location are planner discretion):**
1. **Pre-gate (fast, before any timing):** input Totals reconcile (per-part sums == committed Phase-10 union Totals, named as **sum-of-counts** from `rustkmer stats -f json` keys `unique_kmers`/`total_kmers` — never the header field); Distinct ≥ max input Distinct; source fingerprints match the manifest.
2. **Ground-truth leg (once per k):** independent recount of the union — note the phase-11 simplification: a union count over both parts IS what the existing count-A arm produces when fed the part pair as one input list, so the recount leg can consume the union `.rkdb` the count arms already produce; per-k-mer diff against the merged DB.
3. **Cross-tool leg (the verdict gate):** `rustkmer dump` of merged `.rkdb` vs `jellyfish dump -c` of merged `.jf` → strip `#` lines → normalize to `(canonical k-mer, count)` pairs → `LC_ALL=C sort` both → `cmp` — exact equality (slice scale). At full scale the deep dump-vs-dump leg is user-selected per MBENCH-02/03 split and runs inside Phase 12.
4. **Definition naming:** every check states which `total_kmers` it uses — header field = record count vs stats = sum-of-counts (the IN-03 collision; milestone PITFALLS.md Pitfall 2 governs; verified reader-side at `bench.py:289-301` which intentionally reads the snake_case stats JSON).
5. **Canonicality assertion:** all inputs canonical (one `BenchmarkConfig` drives both command lines — `bench.py:203-219, 1409-1412`); jellyfish merge silently accepts canonicality-mixed inputs (milestone Pitfall 1) so the per-key gate is the structural defense.

### Pattern 3: extending the arm set (MBENCH-01)

**New command builders (all list-form; extend `BenchmarkConfig` single-source pattern):**
- `jellyfish_merge_cmd(out, input_jfs)` — `["jellyfish", "merge", "-o", out, in1, in2]`; inputs are `.jf` files, never `.gz`, so no shell pipe is needed; still run `validate_path` for consistency (T-04-03 stance, `bench.py:190-195`).
- Extend `build_merge_cmd` (`bench.py:283-286`) or add a parameter for `--num-threads 1` — the flag exists on the CLI [VERIFIED: `src/cli/args.rs` `Merge` variant, `num_threads: usize` default `"0"` ("0 = use all cores") and `merge_mode` default `"auto"`].
- New arm specs appended to the `bench.py:1420-1432` block: `jellyfish-count-B` (second `.jf` — today only `jf_a` exists at `bench.py:1404`), `jellyfish-merge`, and `merge-t1` (like-for-like `rustkmer merge --num-threads 1`).
- **Ordering assertion:** within each tool's spec order, count arms precede merge arms. Two load-bearing ordering facts verified: `run_comparison_protocol`'s warmup executes the FIRST spec of each tool (`bench.py:1309-1312`, `next(s for s in arm_specs if s["tool"] == tool)`), and same-tool arms run in spec order inside a round (`bench.py:1316-1317`). Today the dependency is implicit; make it an explicit assertion + unit test before adding arms.
- Extend the count-parity gate (`bench.py:1438-1449`) with the merge parity block after the protocol: merged Total == Σ input Totals; `jellyfish-merge` Total == same sum; merged Distinct == `jellyfish-merge` Distinct (union semantics); merged Distinct ≥ max input Distinct (already in self-check, `bench.py:1489-1496`).
- The self-check synthetic-total formula is synthetic-mode-only (`bench.py:1466-1478`); merge conservation checks apply whenever a merge arm exists (`bench.py:1479-1496`).
- MBENCH-05: the single-rep CI path (`bench.py:1450-1464`) already runs count-A/count-B/merge without jellyfish — extending it means the synthetic merge arm keeps working unchanged; `SCHEMA_VERSION` stays 1 (`bench.py:44`; `validate_schema` :422-452 tolerates new arm names; renderer merge handling `_arm_row` :1626-1629 stays load-bearing for old results — extend it only when a `jellyfish-merge` arm exists in the same results file).

### Pattern 4: characterization ladder mechanics (D-07/D-08/D-09)

1. Two slice pairs at ~10% and ~40% of part scale. Part scale anchor: each pinned part is ~2.79 GB gz; union Total 8,967,099,203 at k=21 over 2 parts ⇒ ~34.5M reads/part (arithmetic: 8,967,099,203 ÷ 2 ÷ (150−21+1)) [ASSUMED — uniform 150 bp read length]. So ~10% ≈ 3–4M reads, ~40% ≈ 13–14M reads per slice; planner pins exact numbers.
2. Provision via `random_slice.reservoir_slice` (seeded, manifest per slice — `random_slice.py:24-60`, `provision_random_slice` at `bench.py:615-664`) — one slice from part_001, one from part_006, same N and seed discipline.
3. Each side runs the complete chain: prepare (same stage code as full scale — deliberately exercising D-04) → per-part counts → both merges.
4. Record per rung: wall (merge arms), output sizes (`.rkdb` bytes and `.jf` bytes), entry counts, `cache_state`, tool + flags + provenance. Evidence-JSON pattern per CONTEXT discretion.
5. Fit slope (wall per entry) per tool; coarse linearity check (two points give a line; MBENCH-04's full-scale predicted-vs-measured is the backstop). jellyfish merge expected linear-in-entries single-threaded (milestone FEATURES.md Part 1 cost model); rustkmer side may switch admission routes between rungs — record the route per rung (milestone ARCHITECTURE.md §7: route attribution).
6. Outputs feed: (a) the disk-floor derivation (D-10), (b) Phase 12 round scheduling (expected wall per arm), (c) MBENCH-04's fitted curve.

### Pattern 5: dress-rehearsal orchestration

- Model on `phase10.py`: staged flow with exit-code contract 0/1/2 (`phase10.py:97-99` verbatim: `EXIT_OK = 0`, `EXIT_NO = 1`, `EXIT_INVALID = 2`) and per-stage documents. Whether that means a `phase11.py` file or staged bench.py invocations is CONTEXT discretion.
- Stages (suggested): `synthetic` (tracer through all new arms + gates) → `parity-gate` (slice-scale three-way + dump-vs-dump, both k) → `ladder` (2 rungs) → `rehearsal` (full protocol at slice scale: all arms, counterbalanced, `cache_state`, medians + CV) → `preflight` (disk-floor derivation recorded).
- Exit criteria (from milestone PITFALLS.md Pitfall 4 + success criterion 2): every gate green, every artifact fingerprinted, protocol timings recorded, evidence JSONs committed.
- Reuse `rotation_schedule` per-arm for the 6-arm set; one discarded warmup per tool (keep the phase10 shape — `run_rounds` at `phase10.py:346-455` is the reference implementation with injectable seams for tests).

### Pattern 6: disk pre-flight (D-10/D-11/D-12)

- Floor formula: `floor = input artifacts (measured post-prepare) + largest single-arm transient (ladder-extrapolated) + safety margin`. Enumerate components (all on one volume — verified 323 GiB free on `/System/Volumes/Data`, which backs both the repo and `/Users/forrest/Data`): 8 per-part artifacts (~70 GiB per D-01), union count-arm outputs (`.rkdb` ≈ union Distinct × 20 B: ~17.1 GB k=21 / ~22.9 GB k=31 [VERIFIED entry size: `src/database/format.rs:950` "42-byte header, 20-byte entries" and `:954` `const RECORD_SIZE: u64 = 20`; `KmerEntry::write_to` writes u128+u32, `format.rs:307-310`]), the union jellyfish count artifact at `DEFAULT_HASH_SIZE 10G` (tens of GB; v2.0 RSS anchors 46.84/88.00 GiB [VERIFIED: 10-03-SUMMARY.md:156,159]), merge outputs (merged `.rkdb` ≈ union size; merged `.jf` capacity-derived ≈ input-0 `.jf` size — milestone FEATURES.md), rustkmer streaming-merge temp chunks.
- **The floor is a function of the per-part `-s` decision** — the 150–400 GiB phase-description estimate assumed `-s 10G`-scale artifacts; the derived floor must be recomputed after Pattern 1's `-s` derivation, and the derivation + inputs recorded as evidence (D-10).
- Mechanics: keep `check_disk_floor` (`bench.py:1263-1277`, `os.statvfs`, exit `DISK_FLOOR_EXIT = 3` at `bench.py:64`) as the full-budget gate; add the override flag (D-11, stated shortfall + explicit opt-in) and a lightweight per-rep re-check hook (D-12) callable from the protocol loop or controller.
- Note: the current guard fires only in `mode == "full"` (`bench.py:1381-1382`); decide whether the derived floor also applies to the rehearsal's slice runs at a scaled value or stays full-mode-only.

### Anti-Patterns to Avoid

- **Hand-editing rendered docs without acknowledging the generator.** `docs/benchmark-report.md` footer says "Generated file — do not edit by hand. Regenerate with … --render-report … --out docs/benchmark-report.md" [VERIFIED: docs/benchmark-report.md footer]. The banner (D-05) is a deliberate supersede marker on a v1.0 artifact; expect and accept that a re-render from the v1.0 JSONs would drop it — and note the renderer itself still emits the v1.0 narrative (`bench.py:1942-1947` CRR2044018 block; `:1883-1892` halt note) into any report it renders, so the post-Phase-12 rewrite needs a renderer-narrative decision too (this phase should record that debt, and may fix the narrative if the planner scopes it).
- **Reusing `DEFAULT_HASH_SIZE = "10G"` for per-part jellyfish count artifacts.** It was sized for union counts; four per-part 10G artifacts would occupy on the order of hundreds of GiB (v2.0 union anchors: 46.84 GiB / 88.00 GiB RSS at `-s 10G`), contradicting D-01's ~70 GiB and the 323 GiB free. Derive `-s` from measured per-part Distinct (Pattern 1 step 2).
- **Expressing the part pair through `--input` on a directory.** `gather_inputs` sorts the six-part dir and `provision_full` takes the first two → part_001 + part_002, not the pinned pair. phase10.py's token-pair resolution (`_SPLIT_PART_TOKENS = (".part_001", ".part_006")`, `phase10.py:2000`; enforced in its input validation ~:2018-2035) is the precedent to reuse. Also: `--merge-input` is slice-mode-only and raises otherwise (`bench.py:540-543`).
- **Creating a second results schema.** SCHEMA_VERSION stays 1; new arm names ride the existing arms list (MBENCH-05).
- **Copying flag strings between jellyfish subcommands.** In `count`, `-m` is mer length; in `merge`, `-m` is MIN mode (milestone FEATURES.md Part 1). Build each command from its own literal set.
- **Relying on `sudo purge` for cold caches.** `attempt_cache_purge` records honest states (`bench.py:1220-1236`); the rehearsal inherits "PARTIALLY satisfied" honesty, never claims cold.
- **Writing HYG-02/03 records into `.planning/phases/`.** v2.0's phases live only under `.planning/milestones/v2.0-phases/` (verified: `.planning/phases/` contains only phase 11). Records go beside the archived phase artifacts.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Counterbalanced scheduling | a new rotation scheme | `output_stage.rotation_schedule` (`output_stage.py:121-137`) or extend `run_comparison_protocol` | Unit-tested, persisted in results, thermal-bias semantics already reasoned through |
| Cache honesty | purge heuristics | `attempt_cache_purge` / `cache_state_from` (`bench.py:1208-1236`) | Honest-label contract (T-04-04); CI/platform branches handled |
| Medians + CV% | manual stats | `reduce_arm` (`bench.py:1239-1260`) | cv_warning threshold convention (10%) |
| Fingerprints / provenance | ad-hoc hashing | `fingerprint` (`bench.py:304-312`), `binary_provenance` (`bench.py:345-375`), `validate_provenance` (:378-419) | The manifest (D-04) should reuse these verbatim so Phase 12 tooling reads one shape |
| Results contract | new schema | `validate_schema` + `SCHEMA_VERSION = 1` | Committed baselines stay loadable; MBENCH-05 forbids a fork |
| Disk guard | new free-space check | `check_disk_floor` (`bench.py:1263-1277`) + derive/override/recheck per D-10/11/12 | Exit-code contract (3) already documented |
| Nyquist backfill | hand-written VALIDATION docs | `/gsd-validate-phase` | Named-workflow requirement (CONTEXT); v1.0/v2.0 `NN-VALIDATION.md` format precedent exists |
| Threat-model verification | hand-written SECURITY.md | `/gsd-secure-phase` | Named-workflow requirement; v1.0 `04-SECURITY.md` shows the produced format |
| Slice provisioning | new sampler | `random_slice.reservoir_slice` / `make_slice.sh` | Deterministic + manifest-bound (D-08 names them) |
| Report numbers | hand-typed values | `--render-report` discipline | Byte-identical re-render; no measurement literals (T-04-07) |

**Key insight:** the harness already paid for every protocol primitive this phase needs; the phase's engineering risk is mis-wiring (orderings, `-s` sizing, schema drift), not missing capability.

## Common Pitfalls

### Pitfall 1: Renderer-narrative contamination (HYG-01)
**What goes wrong:** the banner lands on the doc, but `render_report` still carries the v1.0 dataset-provenance block and halt note as hardcoded strings (`bench.py:1942-1947`, `:1883-1892`) — any future render resurrects stale claims, and the post-Phase-12 rewrite inherits them silently.
**Why it happens:** those lines were correct v1.0 renderer content; nothing marks them era-scoped.
**How to avoid:** implement D-05 as (a) banner + dataset fix on the doc now, (b) an explicit decision recorded in the phase: the post-verdict rewrite owns a renderer-narrative update (or this phase scopes the minimal narrative adjustment — planner's call), (c) the drift sweep (D-06) greps for `+420%`, `CRR2044018`, `5.2 GB`, "two split parts" across `docs/`, `README.md`, `USER_GUIDE.md`, `PROJECT_SUMMARY.md` and fixes factual drift only.
**Warning signs:** a planning doc citing "+420%" or "505 s" without "superseded"; PROJECT.md still saying "~5.2 GB" after the phase [VERIFIED stale at `.planning/PROJECT.md:88` "currently two split parts of read 1 (`part_001`, `part_006`, ~5.2 GB gzipped total; valid standard gzip)" and :96 "~5.2 GB gzipped r1 across split parts"].

### Pitfall 2: Full-mode provisioning cannot express the pinned pair
**What goes wrong:** a full-mode run with `--input <split-dir>` silently measures part_001+part_002; the merge arrangement never matches Phase 10's committed fingerprints.
**Why it happens:** `gather_inputs` sorts the dir (`bench.py:481-497`); `provision_full` takes `resolved_inputs[:2]` (`bench.py:667-674`); `--merge-input` raises outside slice mode (`bench.py:540-543`).
**How to avoid:** add explicit part-pair resolution to the harness (phase10 token pattern) or have arms consume prebuilt artifacts via the manifest; assert input fingerprints against Phase 10's committed values before round 0.
**Warning signs:** results JSON fingerprints listing part_002; pre-gate Total mismatch of exactly one part's worth.

### Pitfall 3: Per-part `-s` sizing
**What goes wrong:** with `-s 10G` per part, four `.jf` artifacts dominate the disk (hundreds of GiB) and jellyfish count RSS balloons; with `-s` too small, jellyfish auto-grows mid-build (slow, provenance ambiguity) or the merge-geometry assumption changes.
**Why it happens:** `DEFAULT_HASH_SIZE = "10G"` (`bench.py:58`) was chosen for union counts (v2.0 jf-t16 RSS 46.84/88.00 GiB at that size [VERIFIED: 10-03-SUMMARY.md:156,159]); merge enforces hash-size **equality**, not any particular value (milestone FEATURES.md Part 1 constraint table).
**How to avoid:** build `.rkdb` first, measure per-part Distinct, derive `-s` with an occupancy assertion (≤ ~75% load), record `jellyfish info`; keep one `-s` per k-pair; state occupancy in the manifest.
**Warning signs:** artifact dir >> 70 GiB after prepare; `jellyfish info` occupancy > 0.8; auto-generate intermediate files appearing during count.

### Pitfall 4: Disk floor derived before its inputs exist
**What goes wrong:** the raised floor is committed from estimates, then the real `-s` or merge transients differ, and Phase 12 discovers it mid-session (D-10 calls this costly-to-reverse).
**How to avoid:** sequence the phase so the floor derivation consumes (a) measured artifact sizes post-prepare and (b) ladder-extrapolated transients; record the formula + inputs; only then change the default (`DEFAULT_DISK_FLOOR_GB = 150` at `bench.py:61-63`, verbatim comment: "Pitfall 8: full-run .rkdb artifacts alone can / reach 55-60 GB per database + merge scratch").
**Warning signs:** a plan task that edits the floor default before the prepare/ladder tasks run.

### Pitfall 5: `total_kmers` definition mixing
**What goes wrong:** conservation checks that compare a header field against a stats sum fail mysteriously or pass vacuously (milestone Pitfall 2 / IN-03).
**How to avoid:** the spec names the definition per check; harness reads the stats JSON keys `unique_kmers`/`total_kmers` (`bench.py:289-301` docstring: "Reads the snake_case serde keys … — never the text-format prose labels"); conservation sums stream entries, never trust the header.
**Warning signs:** an 897M-vs-8.97B "harness bug" report; checks citing `DatabaseHeader::total_kmers`.

### Pitfall 6: Warmup/arm-order coupling when inserting arms
**What goes wrong:** the protocol's per-tool warmup runs the FIRST spec of each tool (`bench.py:1309-1312`); inserting a merge arm ahead of count arms breaks warmup semantics and input dependencies mid-round.
**How to avoid:** explicit ordering assertion + unit test (count arms before merge arms within a tool; jellyfish-count-B after jellyfish-count-A, before jellyfish-merge).
**Warning signs:** a warmup that overwrites an artifact a later arm in the same round consumes; rounds where a merge arm runs before its inputs exist.

### Pitfall 7: Archive-path confusion for HYG-02/03
**What goes wrong:** validation/security records created under a fresh `.planning/phases/05-…` dir fragment the evidence trail (v2.0 phases are archived).
**How to avoid:** write `05-VALIDATION.md`, `06-VALIDATION.md`, `08-VALIDATION.md`, `09-SECURITY.md`, `10-SECURITY.md` beside the archived phase artifacts under `.planning/milestones/v2.0-phases/…` (verified inventory in Sources); confirm the `07-VALIDATION.md` draft (frontmatter `status: draft`, `wave_0_complete: false` [VERIFIED: file head]) is completed or re-issued by `/gsd-validate-phase`.
**Warning signs:** a new phases/NN dir for an archived phase; SECURITY.md at repo root when the milestone convention is per-phase records.

### Pitfall 8: Known harness flake treated as a regression
**What goes wrong:** `test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` flakes ~50% on macOS (`sample` race), and a shared `target/` can bake stale paths into test binaries — a red result gets "investigated" for hours.
**How to avoid:** STATE.md-documented handling: purge stale `target/` artifacts before trusting a red; treat that single test's red as suspected-flake first [VERIFIED: `.planning/STATE.md:74`].
**Warning signs:** intermittent red only in that test; recent worktree/target/ shuffling.

### Pitfall 9: Artifacts or rehearsal scratch landing inside the repo
**What goes wrong:** `bench.py`'s default scratch is `scripts/bench/scratch` (`bench.py:49`) — inside the repo tree; D-03 forbids artifacts there (mis-commit risk), and slice rehearsal scratch can be GiB-scale.
**How to avoid:** prepare stage defaults to the data-adjacent dir; rehearsal scratch follows the phase10 precedent (`/tmp/rustkmer-phase10/scratch` [VERIFIED: `10-results-full-k21.json` `scratch` field]) or another explicit out-of-repo path; add a guard that refuses an artifact root inside `REPO_ROOT`.
**Warning signs:** `git status` showing new `.rkdb`/`.jf`/slice files under `scripts/bench/scratch/`.

## Code Examples

### jellyfish merge command builder
```python
# Source: scripts/bench/bench.py:252-280 (jellyfish_count_cmd shape) +
# milestone FEATURES.md Part 1 (pinned CLI surface: merge -o out in1 in2;
# default = SUM; no -t, no -s on merge)
def jellyfish_merge_cmd(out_jf, input_jfs):
    """jellyfish merge argv (list form, no shell).

    Inputs are .jf databases (never .gz), so no decompressor pipe is needed.
    validate_path stays applied for T-04-03 consistency. Defaults only:
    SUM semantics; -m/-M/-j are different operations (flag collision with
    count's -m is why literals are not shared between subcommands).
    """
    return ["jellyfish", "merge", "-o", validate_path(out_jf),
            *[validate_path(p) for p in input_jfs]]
```

### Like-for-like merge arm (rustkmer --num-threads 1)
```python
# Source: src/cli/args.rs Merge variant (--num-threads default "0"; "0 = use
# all cores") + bench.py:283-286 (build_merge_cmd today — no threads param yet)
def rustkmer_merge_cmd(rustkmer, out_db, input_dbs, num_threads=None):
    argv = [str(rustkmer), "merge", "-i", *[str(p) for p in input_dbs],
            "-o", str(out_db)]
    if num_threads is not None:
        argv += ["--num-threads", str(num_threads)]
    return argv
# "merge" arm: defaults (num_threads=None → CLI default 0/all-cores)
# "merge-t1" arm: num_threads=1 — the like-for-like single-thread row
```

### Merge parity gate (mirrors the count-parity block)
```python
# Source: bench.py:1438-1449 (existing count-parity gate shape) +
# bench.py:1479-1496 (self-check conservation shape)
by_name = {a["name"]: a for a in arms}
sum_totals = (by_name["count-A"]["total_kmers"]
              + by_name["count-B"]["total_kmers"])
# Total here is the SUM-OF-COUNTS definition (stats JSON), named in the spec.
if by_name["merge"]["total_kmers"] != sum_totals:
    raise RuntimeError("merge parity: rustkmer merged total != sum of inputs")
if by_name["jellyfish-merge"]["total_kmers"] != sum_totals:
    raise RuntimeError("merge parity: jellyfish merged total != sum of inputs")
if by_name["merge"]["distinct_kmers"] != by_name["jellyfish-merge"]["distinct_kmers"]:
    raise RuntimeError("merge parity: union Distinct differs across tools")
if by_name["merge"]["distinct_kmers"] < max(
        by_name["count-A"]["distinct_kmers"],
        by_name["count-B"]["distinct_kmers"]):
    raise RuntimeError("merge parity: merged Distinct < max input Distinct")
```

### Deep dump-vs-dump comparator (slice scale)
```python
# Source: src/cli/commands/dump.rs:124-131,163 (verified output: '#'-comment
# header then "<sequence>\t<count>" lines; empirically verified at k=21 this
# session: 65,000/65,000 entries, EOF-terminated) + milestone PITFALLS.md
# Integration Gotchas (jellyfish dump -c, LC_ALL=C sort, keys unique → cmp safe)
#   rustkmer dump merged.rkdb -o rk.txt
#   jellyfish dump -c merged.jf > jf.txt
#   grep -v '^#' rk.txt | LC_ALL=C sort > rk.sorted
#   LC_ALL=C sort jf.txt        > jf.sorted
#   cmp rk.sorted jf.sorted     # byte equality == per-k-mer count equality
```

### prepare-inputs manifest record (consumed by Phase 12 round 0)
```json
{
  "schema_version": 1,
  "kind": "merge-input-manifest",
  "artifacts": [
    {"path": "/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/part_001.k21.rkdb",
     "size_bytes": 0, "sha256": "<64-hex>", "k": 21, "canonical": true,
     "tool": "rustkmer", "command_line": ["rustkmer", "count", "-k", "21", "-C", "..."],
     "distinct": 0, "total": 0}
  ],
  "jellyfish_inputs": [
    {"path": "...part_001.k21.jf", "size_bytes": 0, "sha256": "<64-hex>",
     "k": 21, "hash_size": "1G", "jellyfish_info": {"...": "occupancy etc."}}
  ],
  "source_fingerprints": [
    {"path": "...part_001.fq.gz", "size_bytes": 2785381389,
     "sha256": "dae91042e42c1a05..."},
    {"path": "...part_006.fq.gz", "size_bytes": 2785388289,
     "sha256": "b197f16c31dd3409..."}
  ],
  "provenance": {"binary": {"path": "...", "size_bytes": 0, "sha256": "..."},
                 "git_commit": "<40-hex>", "git_dirty": false,
                 "build_profile": "release", "rust_toolchain": "...",
                 "platform": "...", "created": "..."},
  "created": "2026-11-..."
}
```
Field shapes deliberately mirror `fingerprint()` and `PROVENANCE_KEYS` so `validate_provenance` and Phase 12 tooling read them unchanged [VERIFIED shapes: bench.py:304-312, 322-323].

### Per-rep disk re-check hook (D-12)
```python
# Source: bench.py:1263-1277 (check_disk_floor: os.statvfs, f_bavail*f_frsize,
# exit 3) — the lightweight re-check reuses the same primitive with the derived
# floor; the full-budget check runs once before round 0 with all-arms budget.
def ensure_disk_headroom(out_dir, floor_gb, phase="rep"):
    free = free_bytes(out_dir)                    # os.statvfs, as check_disk_floor
    if free < int(floor_gb * (1 << 30)):
        print(f"disk guardrail ({phase}): {free} bytes free < floor "
              f"{floor_gb} GiB — abort (exit 3); use --disk-floor-override "
              f"to run deliberately", file=sys.stderr)
        sys.exit(DISK_FLOOR_EXIT)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v1.0 count-only full-scale runs on substitute dataset CRR2044018 | v2.0 protocol on CRR1936095 (parity-gated, counterbalanced, 144.69/147.08 s verdicts) | 2026-11-14 | All new evidence cites v2.0 measured values; the stale v1.0 doc gets the banner (HYG-01) |
| Merge measured only at slice scale with `n/a` deltas (`_arm_row` :1626-1629) | True counterpart arm (`jellyfish-merge`) + like-for-like `merge-t1` | This phase | Renderer merge special case becomes conditional; old results files still render |
| Inputs provisioned per-run (count arms) | Prebuilt per-part artifacts + manifest revalidation (D-01/D-04) | This phase | Phase 12 starts with zero setup risk; sha256+Total revalidation replaces regeneration |
| 150 GiB disk floor sized for count artifacts | Derived floor (inputs + ladder-extrapolated transient + margin) | This phase (D-10) | Floor value becomes recorded evidence |

**Deprecated/outdated:** none new this phase — jellyfish 2.3.1 semantics (merge single-threaded streaming, SUM default, hash-size equality, canonicality silence) are pinned in milestone FEATURES.md Part 1 and remain authoritative.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | jellyfish `.jf` file size ≈ hash slots × compressed per-slot bytes (~5–9 B/slot at k=21/31 for `-s` in the 1G–10G range), inferred from jellyfish's compressed-key storage and the v2.0 RSS anchors (46.84/88.00 GiB at `-s 10G`) | Pattern 6 / Pitfall 3 | Floor derivation off by up to ~2×; mitigated — prepare stage measures actual sizes and `jellyfish info` before the floor is committed (D-10 sequencing) |
| A2 | Per-part Distinct ≈ 450–920M (union 897M/1,146M minus cross-part overlap) — per-part values are new measurements | Pitfall 3 / Pattern 1 | `-s` sizing miss → jellyfish auto-grows (slow, not wrong) or oversized artifacts; occupancy assertion + measured Distinct before `.jf` build closes this |
| A3 | ~34.5M reads per pinned part (8,967,099,203 ÷ 2 ÷ 130) | Pattern 4 | Ladder rung percentages shift; harmless — read counts are pinned explicitly when the ladder is built |
| A4 | D-01's "~70 GiB total" implies per-part `-s` ≈ 1G–2G rather than 10G | Pitfall 3 | If the user intends `-s 10G` per part despite the budget, disk planning changes materially — worth a checkpoint confirm when the planner fixes `-s` |
| A5 | Merge-rep cooldown should scale to rep duration (milestone PITFALLS.md Pitfall 5, MEDIUM-confidence methodology) | Pattern 5 | Under-cooled merge reps inflate CV; visible as cv_warning, not silent |
| A6 | `rustkmer merge --num-threads 1` maps to a meaningfully single-threaded path worth recording (milestone Pitfall 3: "record what 1 thread actually changes in the route") | Pattern 3 | The t1 row could be mis-read as strictly like-for-like; the methodology line must state what the flag controls |
| A7 | `/tmp` scratch (phase10 precedent) is acceptable for rehearsal scratch — same single volume as the data dir on this host | Pattern 6 / Pitfall 9 | Only relevant if the user prefers another scratch root; trivial to re-point |

## Open Questions (RESOLVED at planning, 2026-11-16)

1. **Exact per-part jellyfish `-s` value (and whether one `-s` serves both k-pairs).**
   - What we know: merge requires equality within a k-pair; D-01's ~70 GiB budget implies well below 10G; occupancy assertion needs measured per-part Distinct which only exists after the first `.rkdb` builds.
   - What's unclear: the user's intent on the ~70 GiB figure vs a "-s 10G everywhere" fairness reading (A4).
   - Recommendation: planner sequences `.rkdb`-first, derives `-s` with the occupancy assertion, and puts a `checkpoint:human-verify` on the chosen `-s` + resulting disk budget before the full-scale builds run.
   - RESOLVED: Plan 11-02 Task 1 derives `-s` per k-pair with the occupancy assertion (`derive_hash_size`; one shared `-s` per k-pair, not one for both k-pairs); Plan 11-05 Task 2 is the blocking checkpoint that approves the derived `-s` + disk budget before any `.jf` build (also closes A4 explicitly).
2. **Ladder rung read-counts.** CONTEXT says "e.g. ~10% and ~40%" — planner pins exact N (A3 gives the scale anchors). Recommendation: pick round read counts that keep each rung's jellyfish count + merge under ~15 min combined.
   - RESOLVED: Plan 11-06 pins RUNGS at N=3,500,000 and N=14,000,000 reads per slice (seed 4242), at both k.
3. **phase11.py now or Phase 12.** CONTEXT discretion. Recommendation: if the rehearsal wants resumable stages + session provenance, create it now as a thin phase10 clone; otherwise drive staged bench.py/prepare invocations and defer the controller.
   - RESOLVED: deferred — no `phase11.py` is created this phase; Plans 11-05/11-06/11-07 drive staged bench.py / prepare_inputs invocations directly; the optional controller remains a Phase 12 decision (ROADMAP marks it optional for the Phase 12 session).
4. **Renderer narrative scope.** Fix the hardcoded v1.0 narrative lines this phase (small, but touches the byte-identity expectations for old JSON re-renders) or record as post-verdict debt. Recommendation: record as debt in the phase summary + make the post-verdict rewrite own it; do not re-render old JSONs after any narrative change without noting the intentional diff.
   - RESOLVED: recorded as post-verdict debt — Plan 11-03 Task 2 records the renderer-narrative debt (bench.py:1883-1892, :1942-1947) in 11-HYGIENE-RECORD.md; the post-Phase-12 rewrite owns the renderer-narrative update.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| jellyfish | per-part `.jf` artifacts, jellyfish merge arms, deep gate | ✓ | 2.3.1 (`/opt/homebrew/bin/jellyfish`) | none needed (pinned comparator; `require_jellyfish` exits 2 if absent, `bench.py:698-709`) |
| rustkmer release binary | count/merge/dump/stats subprocesses | ✓ | 0.5.0 (`target/release/rustkmer`, built 2026-11-16) | rebuild via `cargo build --release` |
| python3 | all harness work | ✓ | 3.13.11 (floor 3.11) | — |
| `/usr/bin/time` | wall/RSS measurement | ✓ (darwin `-l`) | OS-provided | — |
| Dataset parts part_001/part_006 | artifacts + ladder + rehearsal | ✓ | 2,785,381,389 / 2,785,388,289 bytes — byte-sizes match Phase 10's committed fingerprints | none (regeneration impossible without data) |
| Disk free (data volume) | artifacts + transients | ✓ | 323 GiB free on `/System/Volumes/Data` (single volume backing repo + `/Users/forrest/Data`) | watch during sessions (D-12 per-rep re-check exists for this) |
| `CRR1936095-merge-inputs/` dir | artifact root | ✗ (does not exist yet — verified) | — | created by the prepare stage (D-01/D-03) |
| `sudo -n purge` | cold-cache attempts | unverified this session (v2.0 recorded `unavailable` x30) | — | honest `cache_state` recording (established protocol) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** artifact root dir (created by the stage); `sudo purge` (honest-cache protocol).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python stdlib `unittest` (`scripts/bench/tests/`, existing suite run by CI) + `cargo test` untouched (no Rust changes) |
| Config file | none for unittest (discover-based); CI: `.github/workflows/benchmark.yml` runs `python3 -m unittest discover -s scripts/bench/tests -t .` |
| Quick run command | `python3 -m unittest discover -s scripts/bench/tests -t . -k <module>` (per-module) |
| Full suite command | `python3 -m unittest discover -s scripts/bench/tests -t .` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MBENCH-01 | `jellyfish_merge_cmd` shape (list-form, no shell, `-o` + inputs) | unit | `python3 -m unittest discover -s scripts/bench/tests -t . -k test_merge_arms` | ❌ Wave 0 (`tests/test_merge_arms.py`) |
| MBENCH-01 | arm ordering assertion (count arms precede merge arms per tool) | unit | same, `-k ordering` | ❌ Wave 0 |
| MBENCH-01 | merge cmd builders carry `--num-threads 1` for the t1 arm | unit | same, `-k threads` | ❌ Wave 0 |
| MBENCH-02 | merge parity gate GREEN on conserved fixture / RED on each violated invariant | unit (GREEN+RED) | same, `-k parity` | ❌ Wave 0 |
| MBENCH-02 | dump comparator: normalize+sort equality on a tiny fixture pair | integration (tiny synthetic) | same, `-k dump` | ❌ Wave 0 |
| MBENCH-02 (D-04) | prepare manifest round-trip: build (synthetic scale) → revalidate passes; tampered byte → revalidate fails | unit + integration | `tests/test_prepare_inputs.py` | ❌ Wave 0 |
| MBENCH-05 | synthetic run with merge arm validates under `validate_schema` v1; new arm names tolerated; renderer handles `jellyfish-merge`-bearing files while old files render byte-compatibly | unit + regression | `python3 -m unittest discover -s scripts/bench/tests -t . -k test_schema` + `-k test_render_report` + `-k test_degradation` | ✅ (extend existing files) |
| D-10/11/12 | floor derivation function; hard block exit 3 with shortfall; override flag; per-rep recheck | unit | `tests/test_disk_floor.py` | ❌ Wave 0 |
| HYG-01 | (docs change — verified by review, not unit tests) | manual-only | grep sweep command recorded in plan: `grep -rn "420%\|CRR2044018\|5.2 GB" docs/ README.md USER_GUIDE.md PROJECT_SUMMARY.md .planning/PROJECT.md` | n/a |
| HYG-02/03 | (workflow outputs — `/gsd-validate-phase`, `/gsd-secure-phase` own their verification) | manual-only | workflow-driven | n/a |

### Sampling Rate
- **Per task commit:** the touched test module + `python3 -m unittest discover -s scripts/bench/tests -t . -k <changed-area>`; a real-data slice smoke (`bench.py --mode slice --slice-reads 100000 --reps 2`) after arm-wiring tasks.
- **Per wave merge:** full harness suite; the synthetic tracer through all new arms/gates.
- **Phase gate:** full harness suite green + dress rehearsal green (all gates, both k) + ladder evidence + floor derivation recorded before phase close.

### Wave 0 Gaps
- [ ] `scripts/bench/tests/test_merge_arms.py` — cmd shapes, ordering assertion, parity gates (MBENCH-01/02)
- [ ] `scripts/bench/tests/test_prepare_inputs.py` — manifest build/revalidate/tamper (D-04)
- [ ] `scripts/bench/tests/test_disk_floor.py` — derive/block/override/recheck (D-10/11/12)
- [ ] Extensions to `tests/test_render_report.py` (merge-verdict rows) and `tests/test_schema.py` (new arm names) — files exist, cases new

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1` (`.planning/config.json`). The phase touches only the Python harness and docs; ASVS L1 applicability assessed below.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | no auth surface (local CLI harness) |
| V3 Session Management | no | no sessions |
| V4 Access Control | no | local files; artifact dir outside repo by design (D-03 also reduces mis-commit risk) |
| V5 Input Validation | yes | `validate_path` allowlist (`bench.py:222-234`) applied to every path entering any shell string; new command builders keep list-form subprocess (no shell); `HASH_SIZE_RE`/`DECOMPRESSOR_RE` for the two non-path knobs (`bench.py:194-195`) |
| V6 Cryptography | yes (integrity only) | sha256 via `fingerprint`/`hashlib` for artifact identity + tamper detection (manifest revalidation); never hand-rolled crypto |
| V7 Errors/Logging | yes | fail-loud subprocess stance (`measure`, `stats`, `jellyfish_stats` raise on non-zero); no error swallowing in new gates |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path injection into the single `sh -c` pipeline (jellyfish gz arm) | Tampering/Elevation | keep `validate_path` screening; new `.jf`-based arms need no shell at all (list form) |
| Artifact tampering between build and use (silently changed merge inputs) | Tampering | manifest sha256 + `revalidate` verb; round-0 gate consumes records only (D-04) |
| Provenance spoofing (who/what built an artifact) | Repudiation | reuse `binary_provenance` (hashes actual executable bytes, `bench.py:345-375`) in the manifest |
| Env-var trust boundary (`RUSTKMER_BENCH_MODE/INPUT`) | Tampering | existing `resolve_mode` validation (`bench.py:500-526`); do not add new env knobs without the same validation |
| Tool-output parsing drift (jellyfish/rustkmer text formats) | DoS (gate corruption) | fail-loud parsers (`parse_jellyfish_stats` raises on missing lines, `bench.py:712-735`); same stance for any new `jellyfish info`/dump parsing |
| Mass-of-stale-data confusion (v1.0 evidence cited current) | Repudiation | HYG-01 banner + sweep; "superseded" labeling rule from milestone Pitfall 7 |

## Sources

### Primary (HIGH confidence — read directly this session)
- `scripts/bench/bench.py` (full read, 2135 lines) — every anchor cited above with verbatim quotes for discrete values (`SCHEMA_VERSION`, `DEFAULT_DISK_FLOOR_GB = 150`, `DEFAULT_HASH_SIZE = "10G"`, `DISK_FLOOR_EXIT = 3`, `VALID_MODES`, exit codes, `PROVENANCE_KEYS`, `build_merge_cmd` body, arm_specs block, parity gates, renderer narrative blocks)
- `scripts/bench/phase10.py` (structure + `run_rounds` + `build_arm_specs` + constants incl. `_SPLIT_PART_TOKENS`, exit codes, `DEFAULT_DATA_DIR`)
- `scripts/bench/output_stage.py` (`rotation_schedule` :121-137, defaults), `scripts/bench/random_slice.py` (head), `scripts/bench/make_slice.sh`, `scripts/bench/gen_synthetic.py` (full)
- `src/cli/args.rs` (`Merge` variant verbatim: `-i` num_args=2.., `--num-threads` default "0", `--merge-mode` auto/memory/streaming), `src/cli/commands/dump.rs` (output format :124-131, :163), `src/database/format.rs` (entry size :307-310, :950, :954)
- `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k21.json` + `10-results-full-k31.json` (union Distinct/Total values, part fingerprints, arm key names, scratch path) + `10-03-SUMMARY.md` (measured wall/RSS table :154-159, distinct supersession note :50, scratch-deletion :115)
- `.planning/milestones/v2.0-MILESTONE-AUDIT.md` (WARNING-1/2 verbatim :18-19, :93-94), `.planning/milestones/v1.0-MILESTONE-AUDIT.md` (999.1-999.3 verbatim :65-67), `milestones/v2.0-phases/` inventory (VALIDATION/SECURITY file presence per phase dir), `milestones/v1.0-phases/04-benchmark-validation/04-SECURITY.md` (format precedent), `milestones/v2.0-phases/07-shared-counting-engine/07-VALIDATION.md` (draft frontmatter), `milestones/v1.0-phases/03-memory-safety/deferred-items.md` (999.3 location)
- `docs/benchmark-report.md` (full read — stale headline, footer contract), `.planning/PROJECT.md` (:88, :96 stale dataset lines verbatim), `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/ROADMAP.md` (§Phase 11), `.planning/config.json`, `.github/workflows/benchmark.yml`
- Empirical probes (2026-11-16, this host): `jellyfish --version` → 2.3.1; six-part `ls` byte sizes; `df -h` → 323 GiB free; `python3 --version` → 3.13.11; `rustkmer --version` → 0.5.0; synthetic k=21 count+dump round-trip (65,000/65,000 entries; file 1,300,042 B = 42 + 65000×20; EOF-terminated dump loop → the 12-byte entry-size heuristic in `dump.rs` is inert on the v2 path)

### Secondary (HIGH confidence — milestone research, cited not re-derived)
- `.planning/research/SUMMARY.md`, `FEATURES.md` (jellyfish merge CLI surface, input-constraint table, canonical-flag loss, cost model), `ARCHITECTURE.md` (harness integration design §2), `PITFALLS.md` (pitfalls 1-8 phase mapping, integration gotchas), `STACK.md` (dataset six-part fact, inflate share — PEXT-side, not load-bearing here)

### Tertiary (none)
- No web fetches were performed this session: every research question was codebase- or environment-local, and the pinned jellyfish semantics were explicitly out of scope for re-research (phase instructions). All web-sourced claims inherited from milestone research carry that research's own confidence labels.

## Metadata

**Confidence breakdown:**
- Harness integration points: HIGH — full `bench.py` read + verbatim quotes this session
- Parity-gate anchors and disk arithmetic inputs: HIGH — committed Phase-10 JSONs read verbatim; entry-size constant read from `format.rs`; empirical dump probe run
- Hygiene targets (HYG-01/02/03/04): HIGH — every stale line and missing record located by direct read
- `-s` sizing arithmetic: MEDIUM — direction and anchors verified, exact per-slot formula and per-part Distinct are measured-in-phase (A1/A2)
- Ladder/dress-rehearsal mechanics: HIGH on mechanism (phase10 precedent), MEDIUM on exact rung parameters (planner pins)

**Research date:** 2026-11-16
**Valid until:** 2026-12-16 (stable — harness code changes would invalidate line anchors; re-verify anchors if `scripts/bench/` is edited before planning lands)

---
*Research for: rustkmer v2.1 Phase 11 — Merge Characterization & Harness Prep*
