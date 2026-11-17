# Phase 11 — Hygiene Record (HYG-01 / HYG-04)

**Created:** 2026-11-16 during 11-03 execution
**Scope:** the acknowledged generated-file exception, the renderer-narrative
debt, the D-06 drift-sweep results, and the HYG-04 opportunistic determination.
Plan 11-08 owns the HYG-02 (Nyquist Phases 5–8) and HYG-03 (SECURITY.md
Phases 9/10) milestone-archive records — same wave, disjoint files.

## 1. The superseded banner — single acknowledged exception to the generated-file contract

`docs/benchmark-report.md` is a generated file: its footer states
"Generated file — do not edit by hand. Regenerate with
`python3 scripts/bench/bench.py --render-report --results <jsons> --out
docs/benchmark-report.md`" (evidence JSONs under
`.planning/milestones/v1.0-phases/04-benchmark-validation/`).

The hand-added SUPERSEDED banner at the top of the file (2026-11-16,
HYG-01 / decision D-05) is the **single acknowledged exception** to that
do-not-edit contract. It is a deliberate supersede marker on a v1.0 artifact,
pointing to the authoritative v2.0 Phase-10 evidence at
`.planning/milestones/v2.0-phases/10-benchmark-verdict/`
(k=21 CLI 144.69 s vs jellyfish 194.85 s; k=31 CLI 147.08 s; overall YES).

**Explicit consequence:** a re-render from the v1.0 JSONs reproduces the
original file and **drops this banner**. Until the post-verdict rewrite
replaces the file wholesale, any regeneration must re-add the banner or the
stale report resurfaces unmarked.

The rendered tables, verdict lines, and footer below the banner were not
touched — the report's own historical statements stay historically accurate
(the CRR2044018 provenance block describes the v1.0 run's substitute dataset,
not the current CRR1936095 split directory, so it needed no correction; the
six-part dataset correction belongs to `.planning/PROJECT.md` per D-05).

## 2. Renderer-narrative debt (deliberately NOT fixed this phase)

`scripts/bench/bench.py`'s report renderer still hardcodes the v1.0 narrative:

- the attempt-1 halt note (pre-11-01 anchor `bench.py:1883-1892`; current
  post-11-01 anchor: the `halt_note` literal at `bench.py:1981-1990`,
  emitted under "Recorded methodology finding" at `:2003`), and
- the CRR2044018 dataset-provenance block (pre-11-01 anchor
  `bench.py:1942-1947`; current post-11-01 anchor: `bench.py:2040-2045`).

Any future render therefore still emits v1.0 narrative into the output.

**Disposition (research Open Question 4, resolved as post-verdict debt):**
the renderer narrative is deliberately left unchanged in Phase 11 to protect
byte-identity expectations of old-JSON re-renders
(`render_report` must reproduce committed v1.0-era files byte-for-byte while
those JSONs remain the render inputs). **The post-Phase-12 rewrite of
`docs/benchmark-report.md` owns the renderer-narrative update** — era-scope or
replace these two blocks as part of rewriting the report once, including the
merge verdict (D-05 deferred idea; 11-CONTEXT.md Deferred section).

## 3. D-06 drift sweep — results per file (2026-11-16)

Sweep patterns: `+420`, `CRR2044018` presented as current, `~5.2 GB`,
`5.2 GB`, `split parts` (the broader pattern catches the stale two-parts
phrasing and its variants). Breadth per D-06: `docs/`, `README.md`,
`USER_GUIDE.md`, `PROJECT_SUMMARY.md`, plus the two named artifacts
(`docs/benchmark-report.md`, `.planning/PROJECT.md`). Factual fixes only —
no document rewrites.

| File | Result | Action |
|------|--------|--------|
| `docs/benchmark-report.md` | Sanctioned survivor: rendered rows contain `+420.0%` (k=21 table) and the CRR2044018 provenance block | Kept verbatim under the superseded banner (the acknowledged exception; re-render byte-identity preserved) |
| `.planning/PROJECT.md` | 4 drift sites found | Fixed (see below) |
| `README.md` | 2 drift sites found | Fixed (see below) |
| `USER_GUIDE.md` | Clean — zero matches for any sweep pattern | No action |
| `PROJECT_SUMMARY.md` | Clean — zero matches for any sweep pattern | No action |

Fixes applied:

1. `.planning/PROJECT.md:88` (Task 1): "currently two split parts of read 1
   (`part_001`, `part_006`, ~5.2 GB gzipped total)" → "six single-member gzip
   parts of read 1 (~2.79 GB each, ~16.7 GB total; valid standard gzip); the
   pinned benchmark arrangement is still part_001 + part_006".
2. `.planning/PROJECT.md:96` (Task 1): constraint bullet "~5.2 GB gzipped r1
   across split parts" → "~16.7 GB gzipped r1 across six single-member split
   parts".
3. `.planning/PROJECT.md:18` (Task 2): the HYG target bullet no longer says
   the report "still shows" the v1.0 k=21 +420% verdict — it now records the
   resolution (superseded banner added 2026-11-16; the verdict there is
   historical).
4. `.planning/PROJECT.md:74` (Task 2): v2.0 milestone paragraph "both split
   parts" → "the pinned part_001 + part_006 pair" (the split directory holds
   six parts; the measurement used the pinned two).
5. `README.md:353` (Task 1): the stale "+420.0%" table row kept, labeled
   superseded in place, citing the v2.0 k=21 verdict (144.69 s); no table
   restructure.
6. `README.md:356` (Task 2): the v1.0 conclusion sentence labeled as v1.0 /
   CRR2044018 / superseded, with a pointer to the v2.0 re-measurement
   (144.69 s / 147.08 s, faster at both k).

Historical CRR2044018 mentions that were checked and deliberately left
(they do not present the substitute as current): `.planning/PROJECT.md:33`
(v1.0 Phase-4 deliverable record), `:72` (v1.0 verdict in the "Current state"
history paragraph, explicitly era-labeled), `:109` (Key Decisions table row,
decision record).

Out-of-breadth discovery (logged, not fixed): `.claude/CLAUDE.md:17` — the
auto-generated CLAUDE.md still mirrors the pre-correction constraint line;
fix is regeneration, recorded in `deferred-items.md`.

Gate: zero unlabeled `+420` cites and zero `5.2 GB` / `two split parts`
phrasings remain anywhere in the sweep breadth outside the banner-marked
report (verified in the 11-03 Task 2 verify).

## 4. HYG-04 determination (opportunistic backlog)

**WARNING-2** (`scripts/bench/README.md:318-321` stale "requested + 1"
pool-size formula): **assigned to the Plan 11-07 same-touch** — 11-07 is the
only Phase 11 plan that edits `scripts/bench/README.md` (new stage docs +
harness doc updates), so WARNING-2 is fixed in that same touch per the
opportunistic rule. Not a separate task; tracked here so 11-07 cannot miss it.

**Backlog 999.1 / 999.2 / 999.3: not triggered** by Phase 11:

- **999.1** (`pyo3/build.rs` link args): not triggered — Phase 11 makes no
  Rust or build-script changes (CONTEXT domain: "No Rust code changes in this
  phase"); no plan in this phase touches `pyo3/build.rs`.
- **999.2** (venv site-packages shadowing): not triggered — no venv
  construction or site-packages work occurs anywhere in the phase; the
  memory note "rebuild pyrustkmer with .venv313" remains routine user
  workflow, not a milestone change.
- **999.3** (`v1.0-phases/03-memory-safety/deferred-items.md` stale
  chunk-sweep claim): not triggered — no Phase 11 edit reaches that archived
  file (11-03's own `deferred-items.md` is the phase-dir record, a different
  file).

Per the HYG-04 opportunistic rule and D-06's factual-fixes-only breadth, all
three stay tracked in the ROADMAP backlog and are **not gate-blocking** for
Phase 11 or the Phase 12 verdict.

---
*Record: 11-03 (HYG-01 banner/sweep + HYG-04 determination).*
*Plan 11-08 adds the HYG-02/HYG-03 records beside the archived phase artifacts under `.planning/milestones/v2.0-phases/`.*
