---
phase: 09-python-parity
plan: "05"
subsystem: measurement-evidence
tags: [differential, skip-n, benchmark, baseline-comparison, phase-gates, evidence, frozen-contract]
requires:
  - phase: 09-python-parity
    provides: "09-01 engine cutover + D2 skip-N; 09-02 single-sort save_database; 09-03 --compare-baseline harness; 09-04 --previous differential mode"
  - phase: 05-measurement-regression-harness
    provides: "committed pre-D2 differential (sha256 6d929a45…) and dev-host Python baseline (sha256 42bb480d…)"
provides:
  - "evidence/n_read_differential_d2.json — --expect-unified PASS, 9/9 cases equal, totals 0/0/0, before block 33 Python-only keys"
  - "evidence/python_bench_after_d2.json — measured comparison PASS: speedup_t1 2.3006x, speedup_default 8.4802x"
  - "evidence/phase9_gates_evidence.json — nine ordered gates with observed exit codes + frozen-contract audit"
affects:
  - "Phase 10 (CI-class baselines, full-human-scale verdict)"
tech-stack:
  added: []
  patterns:
    - "Measured gates run on the final rebuilt tree; each gate's real exit code captured into a TSV log before the evidence JSON is assembled"
    - "Benchmark writes into gitignored scripts/bench/scratch/; only the finished JSON is copied into evidence and cmp-verified"
key-files:
  created:
    - .planning/phases/09-python-parity/evidence/n_read_differential_d2.json
    - .planning/phases/09-python-parity/evidence/python_bench_after_d2.json
    - .planning/phases/09-python-parity/evidence/phase9_gates_evidence.json
  modified: []
key-decisions:
  - "Both measured artifacts were produced on the final tree after an exact .venv313 maturin rebuild and a no-skip __version__ assert"
  - "Benchmark --out pointed at the gitignored scripts/bench/scratch/ tree; only the finished JSON was copied into evidence (byte-identical via cmp)"
  - "Every gate exit code was observed and appended live to the gate log; all nine recorded 0"
  - "The Phase 8 whole-file src/database/format.rs pin is superseded for that file only by 09-02's pure addition (78 insertions, 0 deletions); every other Phase 8 pin remains in force"
  - "The untracked .venv313 symlink was removed before the gates-evidence write, so recorded git_dirty is false for the tracked tree"
requirements-completed: [PY-01, PY-02]
coverage:
  - id: D1
    description: "Unified D2 differential on the final artifact: all nine cases equal, totals 0/0/0, before block carries the committed 33 Python-only chimeric keys"
    requirement: PY-02
    verification:
      - kind: integration
        ref: ".venv313/bin/python scripts/bench/n_read_differential.py --expect-unified --previous .planning/phases/05-measurement-regression-harness/n_read_differential.json --rustkmer target/release/rustkmer --out .planning/phases/09-python-parity/evidence/n_read_differential_d2.json (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Measured Python counting win on the N-free control vs the committed Phase 5 baseline: t1 2.3006x, default 8.4802x, exact counts pinned"
    requirement: PY-02
    verification:
      - kind: integration
        ref: ".venv313/bin/python scripts/bench/python_bench.py --mode slice ... --compare-baseline scripts/bench/baselines/python_bench_baseline.darwin.json (exit 0; comparison.result PASS)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full nine-gate final battery green plus frozen-contract audit: pinned manifest blobs, 12 fixture hashes, format.rs pure-addition proof"
    requirement: PY-01
    verification:
      - kind: other
        ref: "nine-gate battery recorded in .planning/phases/09-python-parity/evidence/phase9_gates_evidence.json (all exit_code 0)"
        status: pass
    human_judgment: false
duration: 9m 20s
completed: 2026-11-13
status: complete
actuals:
  tokens: 2721
  tasks: 2
  commits: 2
  plan_head_before: c571a2dc942e5bed3cb3b1a77ca53016cc8999f6
  plan_head_after: ad4c40f38415fe71f3481ac0fa03331ad77e7871
---

# Phase 9 Plan 05: Final Measured Gates and Frozen-Contract Evidence Summary

**Final-tree evidence proves D2 N-read unification (9/9 cases equal, all 33 Python-only chimeric keys gone) and a measured Python counting win of 2.3006x at `threads=1` / 8.4802x at default threads against the committed Phase 5 baseline, with all nine standing gates green.**

## Performance

- **Duration:** 9m 20s
- **Started:** 2026-11-13T02:00:13Z
- **Completed:** 2026-11-13T02:09:33Z
- **Tasks:** 2
- **Files modified:** 3 committed evidence JSON files (benchmark scratch artifacts stay gitignored)
- **Actuals note:** `tokens: 2721` is chars/4 over the authored evidence (differential 7,543 B + gates 3,341 B). The diff also contains the 33,367,270-byte machine-generated benchmark JSON; including it would put the chars/4 figure at 8,344,538, which measures generated measurement payload rather than execution effort. The benchmark artifact size is stated here rather than hidden.

## Accomplishments

- `evidence/n_read_differential_d2.json`: `--expect-unified` exits 0; `verdict == {result: PASS, expect: unified, exit_code: 0}`; `expected_semantics == {cli: skip-N-windows, python: skip-N-windows}`; `divergent_cases == []`; `python_only_total == cli_only_total == count_delta_total == 0`; all nine cases equal on `{distinct, total}`; the embedded `before` block is the committed Phase 5 artifact (sha256 `6d929a45…`) with `python_only_total == 33` and `cases == 9`.
- `evidence/python_bench_after_d2.json`: `comparison.result == PASS`, `verdict.exit_code == 0`, `speedup_t1 = 2.3006x >= 1.0`, `speedup_default = 8.4802x >= 1.2`; N-free control exact counts `129,579,577 / 73,476,107` and fingerprint `5cc93333…`; committed baseline sha256 `42bb480d…`; `params.threads_default == "default"`; exactly two arms (`py21-n-free-control-t1`, `py21-n-free-control-tdefault`); both artifacts pass `validate_schema` + `validate_provenance`.
- `evidence/phase9_gates_evidence.json`: `created` ISO-8601 UTC, `git_commit` `0271d8a`, `git_dirty: false`, an ordered nine-entry `{command, exit_code, summary}` gate list (all observed `0`), the four pinned manifest/lockfile blobs, `format.rs` pre/post blobs with `{insertions: 78, deletions: 0}`, the manifest sha256 `f010e42a…` with 12/12 fixtures verified, both measured-artifact sha256 values, the pre-D2 RED artifact sha256, and the scoped Phase 8 pin disposition.
- Bench hygiene: the benchmark ran with `--out` under `scripts/bench/scratch/` (gitignored at `.gitignore:244`); only the finished JSON was copied to evidence, `cmp -s` confirmed byte identity, and `git status --porcelain` is empty for both the scratch tree and non-evidence paths under `evidence/`.

## Gate Results (observed exit codes)

| # | Gate | Exit | Detail |
|---|------|------|--------|
| — | Pre-D2 RED (cited, from 09-01) | 1 | 4 divergent cases, `python_only_total = 33`, 9 cases |
| 1 | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` | 0 | root crate |
| 2 | `cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings` | 0 | pyo3 crate |
| 3 | `cargo build --release --locked` | 0 | release binary 2,966,832 B |
| 4 | `cargo test --locked` | 0 | 508 passed, 0 failed across 32 suites |
| 5 | `python3 -m unittest discover -s scripts/bench/tests -t .` | 0 | Ran 398 tests, OK (skipped=1) |
| 6 | `.venv313` maturin rebuild | 0 | Installed `pyrustkmer-0.5.0` |
| 7 | `pyrustkmer.__version__` assert | 0 | 0.5.0 == `pyproject.toml` |
| 8 | `.venv313/bin/python -m pytest pyo3/tests -q` | 0 | 177 passed, 63 skipped |
| 9 | five frozen-output/constructor binaries | 0 | golden_sha256 5, golden 34, rkdb_v2 8, output_pipeline 9, sorted_pairs 5 |
| — | Measured differential (Task 1) | 0 | 9/9 equal, totals 0/0/0 |
| — | Measured benchmark comparison (Task 1) | 0 | t1 2.3006x, default 8.4802x |

Frozen contract: `Cargo.toml` `fb5c8395…`, `Cargo.lock` `7f24f3f3…`, `pyo3/Cargo.toml` `5b01979c…`, `pyo3/Cargo.lock` `6da3805f…`, `tests/fixtures/golden_manifest.sha256` `f010e42a…`, `src/database/format.rs` post `dedfd95a…` (pre `eb0d5bf2…`), `tests/fixtures/` porcelain empty.

## Task Commits

Each task was committed atomically:

1. **Task 1: Run the final measured gates: unified D2 differential and the baseline comparison** - `0271d8a` (feat)
2. **Task 2: Run the full final battery and write the consolidated phase-gates evidence** - `ad4c40f` (feat)

**Plan metadata:** SUMMARY commit (docs: complete plan) — no STATE.md or ROADMAP.md changes (orchestrator-owned).

## Files Created/Modified

- `.planning/phases/09-python-parity/evidence/n_read_differential_d2.json` — post-D2 unified differential with validated `before` block (7,543 B).
- `.planning/phases/09-python-parity/evidence/python_bench_after_d2.json` — measured comparison verdict + provenance (33,367,270 B; embeds the 1M-index selection manifests, matching the committed baseline's artifact shape).
- `.planning/phases/09-python-parity/evidence/phase9_gates_evidence.json` — nine-gate battery, pinned blobs, fixture re-hash, measured-artifact hashes, Phase 8 pin disposition (3,341 B).
- `scripts/bench/scratch/python_bench_after_d2.json` — gitignored working artifact; not committed (only the finished JSON was copied into evidence).

## Decisions Made

- Ran the measured gates after an exact `.venv313` rebuild and a no-skip version assert, so the recorded module sha256 (`a8ef5772…`) and binary sha256 (`8f38d20c…`) provably cover the code under test.
- Kept the benchmark's generated FASTQs, manifests, `.rkdb`, and per-arm stats in the gitignored scratch tree; only the finished JSON entered evidence.
- Recorded each gate's real exit code in a TSV while the battery ran; the evidence generator refuses to write on a missing gate, a non-zero exit, or an extra key.
- Removed the untracked `.venv313` symlink after the battery and before the evidence write, so `git_dirty: false` reflects a clean tracked tree at evidence time (the benchmark/differential provenance recorded `git_dirty: true` earlier because that untracked symlink existed then).
- Recorded `actuals.tokens` over authored evidence only; the generated 33.4 MB benchmark JSON is disclosed in the Performance note rather than silently folded into or excluded from the estimate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree was created from the stale base `2fc58cb`**
- **Found during:** Startup worktree branch check
- **Issue:** HEAD was `2fc58cb` while the declared expected base was `c571a2dc…`; the phase 9 plan files were absent from the worktree.
- **Fix:** The tree was clean and HEAD was a strict ancestor with zero own commits, so `git merge --ff-only c571a2dc942e5bed3cb3b1a77ca53016cc8999f6` fast-forwarded the agent branch before any edit. No merge commit, no history rewrite.
- **Files modified:** none
- **Committed in:** N/A (no commit)

**2. [Rule 3 - Blocking] `.venv313` is untracked and absent from the worktree**
- **Found during:** Task 1 setup
- **Issue:** The mandated rebuild/pytest commands use `$PWD/.venv313`, which worktrees do not receive.
- **Fix:** Created a worktree-local symlink to `/Users/forrest/GitHub/rustkmer/.venv313`, ran every mandated command verbatim, then removed it before the gates-evidence write and before returning.
- **Files modified:** `.venv313` (untracked symlink only; never committed)

**3. [Rule 3 - Tooling] Plan commit ledger written through the worktree's own git metadata dir**
- **Found during:** Summary preparation
- **Issue:** The standard ledger write uses a `$(git rev-parse --git-dir)` compound command, which worktree-isolated agents have previously had refused (09-02 deviation 4).
- **Fix:** Wrote the verified base `c571a2dc942e5bed3cb3b1a77ca53016cc8999f6` with a plain `printf` redirect into the worktree's git metadata dir. `commits: 2` in this summary is measured from that base with `git rev-list --count`.
- **Files modified:** none

**4. [Rule 3 - Tooling] Full battery run through a background script**
- **Found during:** Task 2
- **Issue:** The nine-gate battery exceeds the foreground command window; the harness moved the first long command (the benchmark) to the background automatically.
- **Fix:** Ran the plan's `run_gate` battery as a single background script that appends each observed `{rc, command, summary}` to `$TMPDIR/phase9_gates.tsv`, then generated the evidence with the plan's validating `python3` script reading that log. The command strings, order, and assertions are unchanged.
- **Files modified:** none

---

**Total deviations:** 4 auto-fixed (4 blocking/environment)
**Impact on plan:** No scope change and no assertion weakened; all deviations were worktree/environment mechanics required to execute the plan's commands in this isolated copy.

## Issues Encountered

- The gates evidence embeds a 33.4 MB benchmark document because the harness records both 1M-entry selection manifests (top-level and N-free-control). This matches the committed baseline's artifact shape (17.7 MB with one manifest); the size is disclosed in the Performance note.
- The default toolchain in this environment is nightly `rustc 1.101.0-nightly`, which emits one pre-existing `Atomic::fetch_update` deprecation warning during `cargo test`; the MSRV clippy gates explicitly use `+1.82.0` and are warning-free. No source was changed.
- No `cargo fmt --all --check` was gated, per the phase invariant; the file-scoped `rustfmt --check pyo3/src/counter.rs` gate was already green in 09-01/09-02 and this plan changes no Rust source.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. Every evidence field is populated from an executed command or a re-hashed committed artifact; no placeholder or synthetic value is recorded.

## Threat Flags

None. The evidence strengthens the plan's mitigations: provenance covers the measured `.so`/binary (T-9-13), fixtures are re-hashed against the committed manifest with an empty porcelain (T-9-14), and both clippy gates ran `--locked` with all four manifest/lockfile blobs pinned (T-9-SC).

## Threat Surface

The trust boundaries in this plan are all verified rather than newly created: final tree -> measured artifacts (rebuilt + version-asserted + hashed), committed goldens -> gate result (re-hashed, never regenerated), Phase 8 record -> Phase 9 change (scoped supersession with pure-addition proof), evidence JSON -> downstream phase (validated by a refusing-to-write generator).

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | `0271d8a` | feat(09-05): record unified D2 differential and measured baseline comparison |
| 2 | `ad4c40f` | feat(09-05): record full final gate battery and frozen-contract audit |

---

*Phase: 09-python-parity*
*Completed: 2026-11-13*

## Self-Check

- Created files verified present: `evidence/n_read_differential_d2.json`, `evidence/python_bench_after_d2.json`, `evidence/phase9_gates_evidence.json`.
- Commits verified ancestors of HEAD: `0271d8a`, `ad4c40f`.
- Untracked `.venv313` symlink removed; `scripts/bench/scratch/` reports no tracked artifacts.

## Self-Check: PASSED
