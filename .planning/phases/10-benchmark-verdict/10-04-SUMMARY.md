---
phase: 10-benchmark-verdict
plan: 04
subsystem: benchmark-verdict
tags:
  - benchmark-verdict
  - python-full-scale
  - memory-preflight
  - cross-session-parity
  - mechanical-report
  - checkpoint

requires:
  - phase: 10-benchmark-verdict
    provides: "10-03: measured CLI sessions (rk-t16, rk-t1, jf-t16) at k=21 and k=31 over both split parts; Checkpoint-1 selection `proceed`"
  - phase: 10-benchmark-verdict
    provides: "10-01/10-02: phase10.py `preflight-python`/`python`/`render` stages, the two-input fresh-process py-t16 worker, the 86 B/distinct memory model (later re-derived at 86.5 B; see the revision note), and the byte-deterministic renderer"
provides:
  - "10-python-preflight.json: 86.5 B x measured rk-t16 distinct = 72.28 GiB (k=21) / 92.35 GiB (k=31) vs the 110 GiB budget; PROCEED at both k (re-derived 2026-11-14; the run-time 86 B record was 71.87 / 91.82 GiB, superseded and preserved in the session documents)"
  - "10-results-python-k21.json: Python session (`jf-t16`, `py-t16`), both parts, 3 counterbalanced reps, exact parity"
  - "10-results-python-k31.json: the same shape at k=31"
  - "10-verdict.json: per-k per-surface YES/NO computed from same-session recorded medians, with input shas, descope, dev-host statement"
  - "10-BENCHMARK-REPORT.md: mechanically rendered report, byte-identical on re-render"
  - "Checkpoint 2: overall YES at both k on both surfaces; D3/Phase 11 left to the user, not auto-triggered"
affects:
  - 11

actuals:
  tokens: 7267
  tasks: 3
  commits: 3
  plan_head_before: 295c7b6044f1c20e01eb1bacd636282c83856289
  plan_head_after: 10075cecd4b18c12d4b1b495e3ba70086c4bc531

tech-stack:
  added: []
  patterns:
    - "Preflight from measurement, not estimate: the Python projection is re-derived inside the stage from each CLI document's `rk-t16.unique_kmers`, and the decision is computed by `memory_gate` (equality passes); the record is written on both PROCEED and BLOCKED paths as decision evidence"
    - "Same-session reference: each surface's verdict compares against the jellyfish median recorded in its OWN counterbalanced session; the Python session re-measures jellyfish so the comparison never borrows the other session's number"
    - "Cross-session byte identity: the Python session must reproduce the CLI session's jellyfish counts, arm inputs, and both-part input fingerprints before an artifact is written"
    - "Provenance records the worktree-built CLI binary and the installed native module sha256; the k=31 document truthfully reports `git_dirty: true` while an uncommitted k=21 evidence file existed"

key-files:
  created:
    - .planning/phases/10-benchmark-verdict/10-python-preflight.json
    - .planning/phases/10-benchmark-verdict/10-results-python-k21.json
    - .planning/phases/10-benchmark-verdict/10-results-python-k31.json
    - .planning/phases/10-benchmark-verdict/10-verdict.json
    - .planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md
  modified: []

key-decisions:
  - "The Python memory gate is PROCEED from the MEASURED distinct counts under the corrected 86.5 B/distinct model (re-derived 2026-11-14): k=21 77,613,559,257 B (72.28 GiB, 37.72 GiB headroom) and k=31 99,159,586,400 B (92.35 GiB, 17.65 GiB headroom) against 110 GiB. The run-time 86 B projections (77,164,925,966 / 98,586,409,600 B) are superseded, preserved in the session documents as historical values. No number was copied; each record pins its CLI source sha256."
  - "Python full-scale measured both parts in one fresh process per rep at 16 threads: py-t16 165.05 s vs same-session jf-t16 197.95 s at k=21; py-t16 178.22 s vs jf-t16 187.14 s at k=31. Both are match-or-beat (YES)."
  - "Observed Python peaks (46.47 GB at k=21, 73.85 GB at k=31) were well below the conservative 86.5 B/distinct projections (77.61 / 99.16 GB; the historical run-time 86 B projections were 77.16 / 98.59 GB); the projection is an upper bound, never a measurement."
  - "Verdict is YES at both k on BOTH surfaces, computed only from recorded t16 medians with equality counting as match-or-beat: k=21 rustkmer 144.69 <= 194.85 and python 165.05 <= 197.95; k=31 rustkmer 147.08 <= 1380.92 and python 178.22 <= 187.14. Overall YES."
  - "The k=31 jellyfish median differed sharply between sessions (CLI 1380.92 s vs Python 187.14 s) with identical counts, identical two-part input, and an identical ~94.5 GB peak. Each surface uses its own session's reference, so both results are unaffected; the numbers are reported as measured and no run was re-rolled."
  - "A NO would have stood; there is no tolerance band, no re-roll, and the t1 arm never enters the verdict. Phase 11/D3 remains the user's decision and was not triggered."

requirements-completed: [BENCH-V2-02]

coverage:
  - id: D1
    description: "Python memory preflight derived from the measured CLI distinct counts: 86.5 x distinct vs 110 GiB, both k PROCEED, each record pinned to its source artifact sha256 (re-derived 2026-11-14; the run-time 86 B record is superseded but preserved)"
    requirement: BENCH-V2-02
    verification:
      - kind: other
        ref: "python3 assertion on 10-python-preflight.json (plan 10-04 task 1 <automated>; values re-derived under the 86.5 B model) -> 'preflight OK {21: (897266581, 77613559257, 'PROCEED'), 31: (1146353600, 99159586400, 'PROCEED')}' (run-time 86 B output, superseded: 77164925966 / 98586409600)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Python full-scale sessions at k=21 and k=31: jf-t16 and py-t16 over both split parts, one fresh .venv313 process per rep, 16 resolved threads, exact parity within and across sessions"
    requirement: BENCH-V2-02
    verification:
      - kind: other
        ref: "python3 assertion on both Python artifacts (plan 10-04 task 2 <automated>) -> 'python sessions OK [(21, {897266581}), (31, {1146353600})]'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Verdict and report: per-k per-surface YES/NO recomputed from recorded medians, four input shas pinned, KMC3 descope and dev-host/cold-cache statements rendered, report byte-identical on re-render, frozen contracts clean"
    requirement: BENCH-V2-02
    verification:
      - kind: other
        ref: "render stage + adapted plan verify -> 'verdict OK {21: ('YES','YES','YES'), 31: ('YES','YES','YES')} overall YES'; 'REPORT BYTE-IDENTICAL'; baselines/src/manifests diff empty"
        status: pass
    human_judgment: false
  - id: D4
    description: "Checkpoint 2: the user has seen the per-k per-surface verdict, medians, peak memory, parity evidence and KMC3 descope, and knows a NO stands and the D3/Phase-11 decision is theirs"
    requirement: BENCH-V2-02
    verification: []
    human_judgment: true
    rationale: "A blocking-human checkpoint: the milestone acceptance answer and the D3 decision (whether Phase 11 is worth building) cannot be auto-approved."

duration: 1h3m
completed: 2026-11-14
status: complete
---

# Phase 10 Plan 04: Python full-scale sessions, verdict, and mechanical report

**The Python surface matches or beats jellyfish at full human scale on both surfaces and both k values — py-t16 165.05 s vs jf-t16 197.95 s at k=21 and 178.22 s vs 187.14 s at k=31 — so the phase's overall verdict is YES, delivered as Checkpoint 2.**

> **Revision note (2026-11-14):** the delivered `10-python-preflight.json`
> was re-derived from the corrected **86.5 B**/distinct model (WR-02/CR-01).
> It now records 77,613,559,257 B (k=21) and 99,159,586,400 B (k=31), both
> PROCEED against the 118,111,600,640 B (110 GiB) budget. The frontmatter,
> `key-decisions`, `coverage` and `Accomplishments` below state those
> delivered values; the original run-time **86 B** values remain visible
> beside them, marked superseded, and survive verbatim in the Python session
> documents' historical `memory_preflight` blocks. No measurement was re-run
> and the PROCEED decision is unchanged.

## Performance

- **Duration:** ~1 h 3 min (started 2026-11-14T01:18:31Z, last artifact 02:21:09Z)
- **Tasks:** 3 of 3 executed; task 3 carries the Checkpoint-2 human-check
- **Files created:** 5 evidence/verdict artifacts; no production source, fixture, harness, baseline, or manifest changed

## Accomplishments

- **Preflight (gate, not estimate):** `10-python-preflight.json` re-derives the projection inside the `preflight-python` stage from each CLI document's measured `rk-t16.unique_kmers` under the corrected 86.5 B/distinct model (re-derived 2026-11-14): k=21 897,266,581 → 77,613,559,257 B (72.28 GiB); k=31 1,146,353,600 → 99,159,586,400 B (92.35 GiB); budget 118,111,600,640 B (110 GiB). Both PROCEED (headroom 37.72 / 17.65 GiB), overall PROCEED, exit 0. Each record names its CLI source path and live sha256. The run-time 86 B projections (77,164,925,966 / 98,586,409,600 B; 71.87 / 91.82 GiB; headroom 38.13 / 18.18 GiB) are superseded — no measurement was re-run and the decision is unchanged.
- **k=21 Python session** (after a green slice-gate pre-run: k=21 pinned 229,694,874 / 519,271,168, k=31 live parity 261,863,892 / 479,271,168): `jf-t16` medians 200.03 / 197.95 / 196.13 s → **197.95 s**, peak 50,297,651,200 B (46.84 GiB); `py-t16` 167.83 / 165.05 / 164.31 s → **165.05 s**, peak 46,470,447,104 B (43.28 GiB). Exact parity at 897,266,581 distinct / 8,967,099,203 total.
- **k=31 Python session** (pre-gate re-run green): `jf-t16` 186.51 / 187.14 / 195.22 s → **187.14 s**, peak 94,505,009,152 B (88.01 GiB); `py-t16` 178.22 / 178.43 / 176.85 s → **178.22 s**, peak 73,847,406,592 B (68.78 GiB). Exact parity at 1,146,353,600 distinct / 8,275,694,030 total.
- **Every py rep validated:** `threads_resolved == 16`, native module under the interpreter's site-packages (`pyrustkmer.cpython-313-darwin.so`, sha256 `6d526431…558ae3`), two ordered `--inputs`, `peak_bytes == max(peak_rss_bytes, peak_footprint_bytes)`, positive counts.
- **Cross-session identity:** the Python sessions' jellyfish counts, arm `inputs` lists, and both-part `input_fingerprint` blocks equal the matching CLI sessions' — all four arms provably counted the same bytes.
- **Verdict:** `10-verdict.json` — k=21 YES (rustkmer 144.69 ≤ 194.85; python 165.05 ≤ 197.95), k=31 YES (rustkmer 147.08 ≤ 1380.92; python 178.22 ≤ 187.14), overall YES. Every result is recomputable from the four recorded medians; equality would count as YES; `rk-t1` is scaling evidence only.
- **Report:** `10-BENCHMARK-REPORT.md` is the renderer's output over the four documents; re-render to scratch is byte-identical (`cmp` clean). It carries both parts' fingerprints, per-rep walls beside medians, both sessions at both k, the descope, the cache census (`unavailable x30`) and the dev-host statement.
- **Frozen contracts:** `scripts/bench/baselines/` byte-unchanged; `git diff --name-only -- src pyo3/src tests/fixtures Cargo.toml Cargo.lock pyo3/Cargo.toml pyo3/Cargo.lock` empty; `--emit-baseline` never passed.
- **Full suite (after all measured sessions):** `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` exit 0; `cargo test --locked` exit 0; `python3 -m unittest discover -s scripts/bench/tests -t .` → `Ran 510 tests … OK (skipped=1)`; `.venv313/bin/python -m pytest pyo3/tests -q` → `179 passed, 63 skipped`. The permitted flake did not occur.

## Task Commits

Each task was committed atomically:

1. **Task 1: Python memory preflight** — `efee253` (feat)
2. **Task 2: Python full-scale sessions k=21 + k=31** — `10f0591` (feat)
3. **Task 3: Verdict + mechanical report** — `10075ce` (feat)

## Files Created

- `.planning/phases/10-benchmark-verdict/10-python-preflight.json` — both k projections, budget, headroom, source paths + shas, overall PROCEED.
- `.planning/phases/10-benchmark-verdict/10-results-python-k21.json` — `mode=full`, `session=python`, k=21, arms `jf-t16`/`py-t16`, 3 reps each, pre-gate sha, memory preflight vs observed peak, cross-session block, provenance.
- `.planning/phases/10-benchmark-verdict/10-results-python-k31.json` — the same shape at k=31.
- `.planning/phases/10-benchmark-verdict/10-verdict.json` — `kind=phase10-verdict`, per-k `verdicts` with both surfaces' medians/results, overall YES, four input shas, descope, `dev_host_only`, `kmc3_executed: false`, `ci_baseline_written: false`, provenance.
- `.planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md` — mechanically rendered final report.

## Checkpoint 2 — the measured answer (from the committed artifacts)

### Per-k per-surface verdict (same-session t16 medians)

| k | surface | tool median | same-session jellyfish median | result |
|---|---------|-------------|-------------------------------|--------|
| 21 | CLI `rk-t16` | **144.69 s** | 194.85 s | **YES** |
| 21 | Python `py-t16` | **165.05 s** | 197.95 s | **YES** |
| 31 | CLI `rk-t16` | **147.08 s** | 1380.92 s | **YES** |
| 31 | Python `py-t16` | **178.22 s** | 187.14 s | **YES** |

**Overall: YES.** k=21 is the primary acceptance question; k=31 re-verifies the v1.0 matched-hash comparison.

### Raw per-rep walls and peak memory

| k | session | arm | per-rep wall (s) | median (s) | median peak (GiB) |
|---|---------|-----|------------------|------------|-------------------|
| 21 | CLI | rk-t16 | 145.76 / 143.91 / 144.69 | 144.69 | 43.97 |
| 21 | CLI | rk-t1 (scaling only) | 496.75 / 493.86 / 468.38 | 493.86 | 43.96 |
| 21 | CLI | jf-t16 | 193.81 / 205.60 / 194.85 | 194.85 | 46.84 |
| 21 | Python | jf-t16 | 200.03 / 197.95 / 196.13 | 197.95 | 46.84 |
| 21 | Python | py-t16 | 167.83 / 165.05 / 164.31 | 165.05 | 43.28 |
| 31 | CLI | rk-t16 | 148.63 / 147.08 / 146.74 | 147.08 | 68.52 |
| 31 | CLI | rk-t1 (scaling only) | 472.57 / 476.29 / 474.31 | 474.31 | 68.51 |
| 31 | CLI | jf-t16 | 1377.62 / 1380.92 / 1450.67 | 1380.92 | 88.00 |
| 31 | Python | jf-t16 | 186.51 / 187.14 / 195.22 | 187.14 | 88.01 |
| 31 | Python | py-t16 | 178.22 / 178.43 / 176.85 | 178.22 | 68.78 |

### Parity evidence

- k=21: distinct=897,266,581 total=8,967,099,203 — EQUAL across `rk-t16` (cli), `rk-t1` (cli), `jf-t16` (cli), `jf-t16` (python), `py-t16` (python) on the same two-part input.
- k=31: distinct=1,146,353,600 total=8,275,694,030 — EQUAL across the same five arm records.
- Both parts fingerprinted identically in all four documents: part_001 `dae91042…`, part_006 `b197f16c…`.

### Statements the checkpoint must carry

- **KMC3 / BENCH-V2-01:** descoped by user decision on 2026-11-13; no KMC3 binary was downloaded, installed, or executed, and its absence is intentional.
- **Cold cache:** only partially satisfied — no sudo purge was run, so all 30 measured reps recorded `cache_state: "unavailable"`; no rep claims a cold cache.
- **Dev-host only:** these are dev-host numbers; no CI-class baseline was regenerated, written, or modified, and they must never be copied into a CI baseline slot.
- **Rule:** `tool_median <= same-session jellyfish_median` at 16 threads; equality is match-or-beat; no tolerance band; no re-roll; the `t1` arm never enters a YES/NO.
- **A NO stands.** This phase measured YES, but if it had measured NO the verdict would have been recorded and kept unchanged. The **D3 decision** — including whether Phase 11 (minimizer partitioning / memory ceiling) is worth building — belongs to the user and was **not** auto-triggered.

## Deviations from Plan

### Environment / process

**1. [Worktree base] Fast-forwarded the stale worktree before any edit**
- **Found during:** start-up worktree check
- **Issue:** HEAD was `2fc58cb`, a strict ancestor of the expected base `295c7b6`, clean tree, zero own commits.
- **Fix:** `git merge --ff-only 295c7b6044f1c20e01eb1bacd636282c83856289` before any edit, per dispatch.
- **Files modified:** none by the merge.

**2. [Runtime] Built `target/release/rustkmer` in THIS worktree**
- **Found during:** pre-execution probing (no `target/` in a fresh worktree)
- **Fix:** `cargo build --release --locked`, 38.7 s, exit 0; binary sha256 `8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240d5ec74fc87c3d23`, 2,966,832 B — byte-identical to the binary that produced the CLI session artifacts. `target/` is gitignored.
- **Files modified:** none.

**3. [Runtime] Used the shared venv's absolute interpreter path**
- **Found during:** `.venv313` does not exist inside the worktree
- **Fix:** passed `--python /Users/forrest/GitHub/rustkmer/.venv313/bin/python`; no worktree-local symlink was created (none remains).

**4. [Interface drift] The render stage and verdict schema in the plan text are stale**
- **Found during:** Task 3 pre-run inspection
- **Issue:** the plan's command uses `--cli-docs/--python-docs`, but the committed `--stage render` (pinned by `test_phase10_verdict.TestRenderStage`) accepts `--docs <four docs>`; the plan's expected `results`/`{cli,python}.tool_median_s` schema is not what the renderer writes — it writes `verdicts` with flat `rustkmer_wall_s`/`python_wall_s`/`jellyfish_cli_wall_s`/`jellyfish_python_wall_s`. Plan 10-02's SUMMARY documents the implemented contract.
- **Fix:** executed the actual harness interface (`--docs`) and verified equivalent semantics against the actual schema: every result recomputed from its recorded medians, four input shas, descope/dev-host/CI flags, four mandatory literals, byte-identical re-render. No harness edit; no number edited.
- **Files modified:** none.

**5. [Interface] The `python` stage requires `--preflight`, omitted from the plan's listed command**
- **Found during:** Task 2 pre-run
- **Fix:** passed `--preflight .planning/phases/10-benchmark-verdict/10-python-preflight.json` explicitly; the stage re-derives the decision and refuses a BLOCKED record.

**6. [Provenance] The k=31 Python artifact records `git_dirty: true`**
- **Found during:** Task 2 commit
- **Issue:** when the k=31 session started, the k=21 evidence document was still untracked, so `git status --porcelain` was non-empty; `binary_provenance` recorded that truthfully.
- **Fix:** none — the flag is honest (no source file was dirty; binary/module shas are intact). The document was not regenerated, since re-running a measured session to change metadata would be a re-measure.

### Measurement reality (nothing tuned)

**7. [Measurement reality] The k=31 jellyfish median did not reproduce across sessions**
- **Found during:** Task 3
- **Issue:** the CLI session recorded `jf-t16` 1377.62 / 1380.92 / 1450.67 s (median 1380.92 s), while the Python session recorded 186.51 / 187.14 / 195.22 s (median 187.14 s) over the same input, same command, identical counts, and an identical ~94.5 GB peak. Both sessions are internally consistent and cross-session parity passed.
- **Fix:** none — each surface's verdict uses its own session's jellyfish (the locked rule), so both YES results stand; no run was re-rolled, no arm dropped, no number adjusted. The report renders both medians side by side.

**8. [Host state] Other host activity was not controlled**
- **Found during:** both measured sessions
- **Issue:** the dev host is a shared workstation; no agent-run build/test/measurement ran concurrently with a measured session (only light file reads), but external applications were not monitored or killed.
- **Fix:** none possible; the counterbalanced rotation applies the same background conditions to every arm within a session. Recorded here.

---

**Total deviations:** 8 documented (5 environment/interface, 2 measurement reality, 1 host state). No production source, fixture, baseline, manifest, or harness measurement primitive was modified; no gate was edited.

## Issues Encountered

- Scratch `.jf` files were deleted by the stage after their stats and sha256 were recorded; the data volume remained at 232+ GiB free (floor 150 GiB). No session's scratch artifacts were committed.
- The pre-gate artifacts (`pre_gate_k21.json`, `pre_gate_k31.json`) live under `/tmp/rustkmer-phase10/scratch/`; their sha256 values are recorded in the corresponding Python artifacts. The committed `10-slice-gate.json` was not rewritten.
- The harness suite grew from the 415-test baseline to 510 tests with the Phase-10 stages; all pass (1 skip).

## Verification

- Task 1 automated verify — passed: `preflight OK {21: (897266581, 77613559257, 'PROCEED'), 31: (1146353600, 99159586400, 'PROCEED')}` (re-derived 2026-11-14 under the 86.5 B model; the original run-time verify printed `preflight OK {21: (897266581, 77164925966, 'PROCEED'), 31: (1146353600, 98586409600, 'PROCEED')}`, superseded but kept here as history).
- Task 2 automated verify — passed: `python sessions OK [(21, {897266581}), (31, {1146353600})]`.
- Task 3 render + adapted verify — passed: `verdict OK {21: ('YES','YES','YES'), 31: ('YES','YES','YES')} overall YES`; `REPORT BYTE-IDENTICAL`; baselines/source/manifest diff empty.
- Full suite — green as listed above; exit codes captured raw (no masked pipelines).

## Known Stubs

None. No stubbed code or placeholder value was written by this plan.

## User Setup Required

None.

## Next Phase Readiness

- **Checkpoint 2 is delivered.** The measured answer is YES at both k on both surfaces. The D3 decision — whether to invest in a memory ceiling/minimizer partitioning (Phase 11) — is the user's; Phase 11 was not auto-triggered.
- The phase's five evidence artifacts are committed; the report is byte-deterministic and regenerable with the documented command.
- The worktree is clean; `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/state.json` were intentionally left untouched for the orchestrator.

---
*Phase: 10-benchmark-verdict*
*Completed: 2026-11-14*

## Self-Check: PASSED

- FOUND: .planning/phases/10-benchmark-verdict/10-python-preflight.json
- FOUND: .planning/phases/10-benchmark-verdict/10-results-python-k21.json
- FOUND: .planning/phases/10-benchmark-verdict/10-results-python-k31.json
- FOUND: .planning/phases/10-benchmark-verdict/10-verdict.json
- FOUND: .planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md
- FOUND: efee253 (task 1 preflight)
- FOUND: 10f0591 (task 2 Python sessions)
- FOUND: 10075ce (task 3 verdict + report)
