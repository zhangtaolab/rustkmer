---
phase: quick
plan: 261118-pja
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/bench/phase10.py
  - scripts/bench/tests/test_python_full_arm.py
  - scripts/bench/README.md
  - .planning/ROADMAP.md
autonomous: true
must_haves:
  truths:
    - "A `--stage cli` invocation without `--pre-gate` exits 2 with no artifact and stderr naming the requirement."
    - "A CLI session whose gate fails provenance, session-k, same-input, or slice-source validation exits 2 BEFORE any measured work (`run_rounds` is never called) and writes no artifact."
    - "A valid CLI session records a `pre_gate` block carrying the gate path and the sha256 of the bytes validated before measurement."
    - "The two committed v2.0 CLI documents (which have no `pre_gate` block) remain readable: `--stage render` over all four committed documents and `--stage preflight-python` over the two committed CLI documents both exit 0."
    - "The python stage's behaviour is unchanged: `scripts/bench/tests/test_python_full_arm.py` is green, including its existing pre-gate and k=31 gate tests."
    - "ROADMAP's v2.0 carry-forward bullet marks the WARNING-1 half RESOLVED with the mechanism and evidence, marks WARNING-2 RESOLVED at commit 7e837f1, and no other carry-forward bullet changes."
  artifacts:
    - "scripts/bench/phase10.py — `run_cli_session` requires `--pre-gate`, validates it with `_load_slice_gate_doc` plus same-input and slice-source checks, and pins path+sha256 in the CLI document; `build_parser` help updated."
    - "scripts/bench/tests/test_python_full_arm.py — shared gate fixture, four new CLI-stage tests, and the recorded-block assertions."
    - "scripts/bench/README.md — the `cli` stage row states that it consumes the slice-gate artifact."
    - ".planning/ROADMAP.md — the v2.0 carry-forward WARNING-1/WARNING-2 bullet is resolved and dated."
  key_links:
    - "run_cli_session's gate check <-> _load_slice_gate_doc: the CLI stage must consume exactly the validator the python stage uses, so both stages share one definition of a valid gate (provenance, session-k, k=21 pins, k=31 same-slice)."
    - "CLI gate same-input check <-> python stage lines 2463-2469: the same `input_fingerprint == [fingerprint(p) for p in inputs]` equality is the model, so a gate measured on other bytes can never authorize a CLI run."
    - "CLI slice-source check <-> _resolve_two_parts: `slice_recipe.source_sha256` must equal `fingerprint(inputs[0])['sha256']`, tying the gate's slice provenance to the pinned part_001 bytes the session measures."
    - "Historical CLI documents <-> render/preflight-python: both stages consume recorded JSON only; neither reads the gate path, so documents without `pre_gate` stay readable and no render-time ordering assertion is added."
---

<objective>
Close benchmark-harness WARNING-1 (BENCH-V2-02): make the full-scale CLI
stage structurally consume the slice-gate artifact instead of relying on
process discipline.

Purpose: `.planning/milestones/v2.0-MILESTONE-AUDIT.md` WARNING-1 records
that `--stage cli` never reads the slice gate: the gate-before-CLI ordering
was satisfied by an operator re-run plus committed timestamps, but a future
CLI run could omit the gate without the harness noticing. The python stage
already requires and validates `--pre-gate`; this change mirrors that model
for the CLI stage and records the consumed artifact.

Output: one code commit (controller enforcement + unittest coverage + README
stage row) and one record commit (ROADMAP carry-forward resolution).

Scope decision (explicit): the smallest safe structural fix is the required
`--pre-gate` plus recorded `pre_gate` block. A render-time ordering assertion
is NOT added: the two committed CLI documents carry no `pre_gate` block, so
such an assertion could only run conditionally; and a gate-path read at
render time would depend on the recorded path still resolving (the plan-10-03
k=31 pre-gate was written to a `/tmp` scratch path). Requiring the flag
subsumes the ordering concern: a future CLI document can no longer exist
without the gate it consumed, while the two committed v2.0 CLI documents keep
their present shape and remain readable.

History-preservation note: `.planning/milestones/v2.0-phases/10-benchmark-verdict/`
is a frozen milestone archive. The committed CLI documents (`10-results-full-k21.json`,
`10-results-full-k31.json` — note: the dispatch brief's `10-results-cli-*`
names do not exist) and `10-slice-gate.json` MUST NOT be edited, and the
render/preflight compatibility gates in Task 1 prove they stay readable.

Commit contract (quick executor): land Task 1 as one atomic code commit and
Task 2 as one atomic record commit, staging only the named files by explicit
path (`git add -- <paths>`; never `git add -A`). The orchestrator records the
STATE.md quick-task row and commits the PLAN/SUMMARY/STATE artifacts
afterwards. Do NOT touch STATE.md, BATCH.json, any milestone archive, or any
historical phase artifact.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@scripts/bench/phase10.py
@scripts/bench/tests/test_python_full_arm.py
@scripts/bench/README.md
@.planning/ROADMAP.md

## Planning-time live observations (2026-11-18, HEAD 7947043, tracked tree clean)

- WARNING-1 is quoted in `.planning/milestones/v2.0-MILESTONE-AUDIT.md:93`;
  ROADMAP line 127 still lists WARNING-1 and WARNING-2 together as
  "opportunistic when `scripts/bench/` is touched". WARNING-2 was actually
  fixed in `scripts/bench/README.md` by commit `7e837f1` (2026-11-17,
  "docs(11-07): README stage docs + WARNING-2 same-touch fix") with no
  ROADMAP edit — the bullet is stale on both halves.
- `scripts/bench/phase10.py` (2622 lines) facts verified live:
  `STAGES = ("synthetic", "slice-gate", "cli", "python", "render",
  "preflight-python")` at 2539; `run_cli_session(args)` at 2210 resolves the
  two parts, checks the disk floor, projects the research-upper preflight,
  builds `rk-t16`/`rk-t1`/`jf-t16`, runs rounds, asserts parity, and writes
  the doc with `preflight` + `schedule` extras — it consumes NO gate.
  `_load_slice_gate_doc(path, k)` at 2264 validates provenance, kind,
  duplicate/per-k gates, positive counts, `slice_recipe.source_sha256`, the
  k=21 pinned counts (`PINNED_HEAD4M`) and reference sha (`REFERENCE_SHA256`),
  and k=31 same-slice source. `run_python_session` at 2438 requires
  `--pre-gate` via `invalid(...)`, calls the loader at 2463, compares
  `gate_doc["input_fingerprint"]` to `[fingerprint(p) for p in inputs]` at
  2465, and records `pre_gate` {path, sha256} at 2494. `invalid()` at 178
  prints to stderr and raises SystemExit(2). `file_sha256` at 184.
  `fingerprint` is imported from `scripts.bench.bench` (line 79).
- `build_parser()` `--pre-gate` help at 2573 currently reads "python stage:
  the slice-gate artifact (10-slice-gate.json)".
- `assemble_doc` (837) rejects `extra` keys colliding with pinned keys, so
  adding `pre_gate` and `preflight` together is safe. `validate_schema`
  (bench.py:511) tolerates extra keys (its own comment at bench.py:407 says
  so); `validate_provenance` is the strict gate and is unaffected.
- Tests verified live: `scripts/bench/tests/test_python_full_arm.py` has 42
  tests, all green; `test_phase10_verdict.py` + `test_render_report.py` have
  127, all green. `CliStageFixture` (382) has no gate; `cli_argv` (412) does
  not pass `--pre-gate`. `PythonStageFixture` (480) owns `write_pre_gate`
  (494), which writes a k=21 gate whose `slice_recipe.source_sha256` is
  `"f" * 64`, a value the loader accepts because it only cross-checks k=31.
  `_add_k31_gate` (732) hardcodes the same `"f" * 64` default.
  `TestCliStageDocument` (419) is the CLI-stage suite.
- Compatibility commands verified live at HEAD (exit 0 each):
  `--stage render` over the four committed v2.0 documents, and
  `--stage preflight-python` over the two committed CLI documents. Neither
  reads the gate path.
- The committed `10-slice-gate.json` has both k gates with
  `slice_recipe.source_sha256 = dae91042...` equal to part_001's fingerprint —
  the new slice-source check holds on real evidence.
- Ruff baseline (no repo ruff config; CI does not run ruff on these files):
  `ruff check scripts/bench/phase10.py scripts/bench/tests/test_python_full_arm.py`
  reports exactly 4 pre-existing F541 findings in `phase10.py`
  (lines 1200-1203, unrelated). The delta gate below pins that count.
- Gate baselines measured at HEAD:
  phase10.py: `the cli stage requires --pre-gate` = 0; `cli and python
  stages: the slice-gate artifact` = 0; `"pre_gate": {` = 1;
  `the gate must have been measured on the pinned slice source` = 0.
  test file: `include_pre_gate` = 0; each of the four new test names = 0.
  README: `consumes the slice-gate artifact` = 1 (python row only).
  ROADMAP: `WARNING-1` = 1; `WARNING-2` = 1; `opportunistic when
  `scripts/bench/` is touched` = 1; `261118-pja` = 0; `7e837f1` = 0;
  `status updated 2026-11-16` = 1.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Require and validate `--pre-gate` for the cli stage, record it, and pin it with tests</name>
  <files>scripts/bench/phase10.py, scripts/bench/tests/test_python_full_arm.py, scripts/bench/README.md</files>
  <behavior>
    - Missing `--pre-gate` on `--stage cli` -> exit 2, stderr names the requirement, no artifact.
    - Gate from other input bytes -> exit 2, no artifact, `run_rounds` never called.
    - Gate whose k=21 `slice_recipe.source_sha256` differs from part_001's sha256 -> exit 2, no artifact.
    - Gate without the session's k (k=31 run, k=21-only gate) -> exit 2, no artifact.
    - Valid gate -> exit 0 and `doc["pre_gate"]` carries the gate path and the sha256 of its pre-run bytes.
    - The python stage's existing gate behavior and all its tests remain green.
  </behavior>
  <action>
    1. In `scripts/bench/phase10.py`, edit `run_cli_session` (currently
       line 2210). Immediately before `out_path, scratch = _stage_paths(args)`,
       add the required-argument check, mirroring the python stage's `invalid`
       usage: when `args.pre_gate` is falsy, call
       `invalid("the cli stage requires --pre-gate <10-slice-gate.json>")`.
       This must stay outside the `try` so SystemExit(2) is not swallowed.
    2. Inside the existing `try`, immediately AFTER
       `inputs = _resolve_two_parts(args.data_dir)` and BEFORE
       `check_disk_floor(...)`, insert the gate validation, in this order:
       (a) `gate_doc = _load_slice_gate_doc(args.pre_gate, args.k)` — reuse
       the python stage's validator unchanged; do not modify
       `_load_slice_gate_doc`.
       (b) `current_fingerprints = [fingerprint(path) for path in inputs]`
       and raise ValueError when `gate_doc.get("input_fingerprint")` differs,
       with a message that names `--pre-gate`, says "was measured on different
       input bytes", and includes both fingerprint values — mirror the python
       stage's wording at lines 2467-2468 so one phrasing describes both
       sessions.
       (c) Select the gate for the session's k from `gate_doc["gates"]`
       (a dict whose `get("k") == args.k`; the loader has already proven
       exactly one exists). Compare its `slice_recipe["source_sha256"]` to
       `current_fingerprints[0]["sha256"]` (part_001) and raise ValueError on
       mismatch. The message must name `--pre-gate`, the k value, both sha256
       values, and the literal sentence "the gate must have been measured on
       the pinned slice source".
       (d) `pre_gate_sha256 = file_sha256(args.pre_gate)` — computed here,
       BEFORE the disk floor, preflight, specs, or rounds, so the recorded
       digest describes the bytes validated before any measured work and a
       mid-run edit cannot repin the document.
       These checks must precede `check_disk_floor`, `_cli_preflight`,
       `build_arm_specs`, and `run_rounds`: a failed gate exits 2 with no
       artifact and no measurement.
    3. Add `"pre_gate": {"path": str(args.pre_gate), "sha256":
       pre_gate_sha256}` to the `assemble_doc` `extra` dict (alongside
       `preflight` and `schedule`). Key order in the dict literal is
       preflight, pre_gate, schedule; `assemble_doc` rejects collisions with
       pinned keys, so this placement is safe.
    4. Update the `run_cli_session` docstring: it consumes the slice-gate
       artifact, the gate is validated (provenance, session-k, same inputs,
       slice source) before any measured work, and a failed gate exits 2 with
       no artifact. Do not reword any existing error string outside the new
       checks.
    5. Update the `--pre-gate` help in `build_parser` (line 2573) from
       "python stage: ..." to "cli and python stages: the slice-gate artifact
       (10-slice-gate.json)" keeping the existing string-concatenation wrap
       style.
    6. In `scripts/bench/tests/test_python_full_arm.py`, move
       `write_pre_gate` from `PythonStageFixture` into `FullArmFixture` so
       the CLI fixture can use it: base `setUp` gains
       `self.pre_gate = self.tmp / "10-slice-gate.json"` followed by
       `self.write_pre_gate()` (after the parts and pin patch exist);
       `PythonStageFixture.setUp` keeps only `self.distinct` and its existing
       cli-doc/preflight setup. In the moved helper, change the k=21 gate's
       `slice_recipe.source_sha256` from `"f" * 64` to
       `p10.fingerprint(self.part1)["sha256"]` so the new slice-source check
       sees the fixture's real part_001 bytes; keep the `distinct`/`total`/
       `sha` override parameters and all other content unchanged. Change
       `_add_k31_gate` to `def _add_k31_gate(self, source_sha=None)` and
       default `source_sha` to the k=21 gate's own
       `slice_recipe["source_sha256"]` (the explicit `"0" * 64` mismatch
       caller is unchanged), so the existing k=31 tests stay green.
    7. Change `CliStageFixture.cli_argv` to
       `def cli_argv(self, k=21, include_pre_gate=True)`; use `str(k)` for
       `--k` and append `--pre-gate`, `str(self.pre_gate)` only when
       `include_pre_gate` is true. Existing callers stay valid.
    8. In `TestCliStageDocument.test_stage_writes_the_pinned_sub_shapes`, add
       assertions that `doc["pre_gate"]["path"] == str(self.pre_gate)` and
       that `doc["pre_gate"]["sha256"]` equals
       `hashlib.sha256(self.pre_gate.read_bytes()).hexdigest()`.
    9. Add four tests to `TestCliStageDocument`:
       `test_missing_pre_gate_exits_2_with_no_artifact` — run
       `cli_argv(include_pre_gate=False)` and assert EXIT_INVALID, that
       stderr contains "the cli stage requires --pre-gate", and that
       `self.out` does not exist.
       `test_gate_for_different_inputs_exits_2_before_any_measurement` —
       mutate the gate JSON's `input_fingerprint[0]["sha256"]` to `"0" * 64`;
       create `run_rounds = mock.Mock()` and pass
       `self.stage_patches() + [mock.patch.object(p10, "run_rounds",
       run_rounds)]` to `run_main`; assert EXIT_INVALID, no artifact, stderr
       contains "different input bytes", and `run_rounds.call_count == 0`
       (the explicit `new=` object is what makes the call count observable
       after the ExitStack unwinds).
       `test_gate_from_a_different_slice_exits_2` — mutate only the k=21
       gate's `slice_recipe.source_sha256` to `"0" * 64` (leave
       `input_fingerprint` intact, which proves this check is distinct from
       the input check), then assert EXIT_INVALID, no artifact, and stderr
       contains "pinned slice source".
       `test_gate_missing_the_session_k_exits_2` — run `cli_argv(k=31)`
       against the k=21-only fixture gate and assert EXIT_INVALID, no
       artifact, and stderr contains "no gate for the session's k=31".
    10. In `scripts/bench/README.md`, replace the `cli` row of the
        "Phase-10 verdict stages" table so it reads: full-scale CLI session:
        `rk-t16`, `rk-t1` (scaling evidence only) and `jf-t16` over both
        parts; consumes the slice-gate artifact (`--pre-gate`: provenance,
        the session's k gate, same input fingerprints, and the gate's slice
        source sha256 against part_001, all before any measurement) and pins
        its path+sha256 in the artifact. Do not change the `python` row or
        the exit-contract prose.
    11. Run every gate in the Verify block. Then commit exactly the three
        files as one atomic commit:
        "fix(quick-261118-pja): require and validate --pre-gate for the cli stage".
  </action>
  <verify>
    <automated>python3 -m unittest scripts.bench.tests.test_python_full_arm # [HEAD=0 EXPECT==0 GUARD MUTATION: the 42 pre-existing tests must stay green after the shared-fixture change and the controller change]</automated>
    <automated>python3 -m unittest scripts.bench.tests.test_python_full_arm.TestCliStageDocument.test_missing_pre_gate_exits_2_with_no_artifact scripts.bench.tests.test_python_full_arm.TestCliStageDocument.test_gate_for_different_inputs_exits_2_before_any_measurement scripts.bench.tests.test_python_full_arm.TestCliStageDocument.test_gate_from_a_different_slice_exits_2 scripts.bench.tests.test_python_full_arm.TestCliStageDocument.test_gate_missing_the_session_k_exits_2 # [HEAD=error:1 EXPECT==0]</automated>
    <automated>python3 -m unittest scripts.bench.tests.test_phase10_verdict scripts.bench.tests.test_render_report # [HEAD=0 EXPECT==0 GUARD MUTATION: the render/verdict consumers must not regress on the added extra key]</automated>
    <automated>ruff check scripts/bench/phase10.py scripts/bench/tests/test_python_full_arm.py --ignore F541 # [HEAD=0 EXPECT==0 GUARD MUTATION: a new non-F541 finding fails; F541 is the recorded pre-existing baseline]</automated>
    <automated>test "$(ruff check scripts/bench/phase10.py scripts/bench/tests/test_python_full_arm.py --select F541 --output-format=concise 2>/dev/null | grep -c '^scripts/')" -le 4 # [HEAD=4 EXPECT<=4 GUARD MUTATION: introducing a new F541 pushes the count past the recorded baseline]</automated>
    <automated>grep -qF 'the cli stage requires --pre-gate' scripts/bench/phase10.py # [HEAD=absent EXPECT==present]</automated>
    <automated>grep -qF 'cli and python stages: the slice-gate artifact' scripts/bench/phase10.py # [HEAD=absent EXPECT==present]</automated>
    <automated>grep -qF 'pre_gate_sha256' scripts/bench/phase10.py # [HEAD=absent EXPECT==present]</automated>
    <automated>grep -qF 'the gate must have been measured on the pinned slice source' scripts/bench/phase10.py # [HEAD=absent EXPECT==present]</automated>
    <automated>grep -qF 'include_pre_gate' scripts/bench/tests/test_python_full_arm.py # [HEAD=absent EXPECT==present]</automated>
    <automated>test "$(grep -cF 'consumes the slice-gate artifact' scripts/bench/README.md)" -ge 2 # [HEAD=1 EXPECT>=2]</automated>
    <automated>TMP=$(mktemp -d) && python3 scripts/bench/phase10.py --stage render --docs .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k21.json .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k31.json .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k21.json .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k31.json --out "$TMP/report.md" --verdict-out "$TMP/verdict.json" && rm -rf "$TMP" # [HEAD=0 EXPECT==0 GUARD MUTATION: a render-time gate read or a required pre_gate would make the two historical CLI documents unrenderable]</automated>
    <automated>TMP=$(mktemp -d) && python3 scripts/bench/phase10.py --stage preflight-python --cli-docs .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k21.json .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k31.json --out "$TMP/preflight.json" && rm -rf "$TMP" # [HEAD=0 EXPECT==0 GUARD MUTATION: preflight-python must keep reading the historical CLI documents]</automated>
    <automated>test -z "$(git status --porcelain -- .planning/STATE.md .planning/milestones .claude/CLAUDE.md)" # [HEAD=absent EXPECT==absent GUARD MUTATION: any archive edit or stray artifact makes this non-empty]</automated>
    <automated>FILES=$(git show --pretty=format: --name-only HEAD) && printf '%s\n' "$FILES" | grep -qxF 'scripts/bench/phase10.py' && printf '%s\n' "$FILES" | grep -qxF 'scripts/bench/tests/test_python_full_arm.py' && printf '%s\n' "$FILES" | grep -qxF 'scripts/bench/README.md' && test -z "$(printf '%s\n' "$FILES" | grep -vF -e 'scripts/bench/phase10.py' -e 'scripts/bench/tests/test_python_full_arm.py' -e 'scripts/bench/README.md')" # [HEAD=absent EXPECT==present]</automated>
    HEAD baselines are recorded beside each gate. All test/grep/ruff gates run before the commit; the two compatibility runs write only into a fresh temp dir removed in the same command; the diff-shape gate runs after the commit.
  </verify>
  <done>The cli stage refuses to run without `--pre-gate`, validates provenance, the session's k, same input fingerprints, and the gate's slice source sha256 against part_001 before the disk floor/preflight/rounds, and records `pre_gate` {path, sha256} in the document; the four new tests pass and the existing 42-test module, the 127 adjacent tests, the ruff delta gate, and both historical-document compatibility commands are green; the parser help and README stage row describe `--pre-gate` as a cli+python requirement; one atomic commit touches exactly the three files.</done>
</task>

<task type="auto">
  <name>Task 2: Close the ROADMAP v2.0 carry-forward WARNING-1 record</name>
  <files>.planning/ROADMAP.md</files>
  <action>
    1. Edit `.planning/ROADMAP.md` only within the "### v2.0 carry-forward"
       block (currently lines 122-129). Change the heading's trailing
       "status updated 2026-11-16" to "status updated 2026-11-18".
    2. Replace the single bullet that currently reads "Benchmark harness
       WARNING-1 (CLI stage does not structurally consume the slice gate) and
       WARNING-2 (README pool-size formula drift) → opportunistic when
       `scripts/bench/` is touched (Phase 11 does touch it)" with two bullets:
       (a) "- Benchmark harness WARNING-1 (CLI stage did not structurally
       consume the slice gate) → **RESOLVED** (quick 261118-pja, 2026-11-18):
       `--stage cli` now requires `--pre-gate` and validates it with
       `_load_slice_gate_doc` (complete provenance, a gate for the session's
       k, the pinned k=21 counts/reference), asserts the gate's
       `input_fingerprint` equals the current two parts AND its
       `slice_recipe.source_sha256` equals part_001's sha256, all before the
       disk floor, preflight, or any measured round; a failed gate exits 2
       with no artifact. The CLI document pins the gate's path+sha256 in a
       `pre_gate` block, pinned by four new unittest cases in
       `scripts/bench/tests/test_python_full_arm.py`. Historical note: the
       two committed v2.0 CLI documents predate the block and remain
       readable — the schema tolerates the extra key and neither `render`
       nor `preflight-python` reads the gate path (both re-run green on
       2026-11-18)."
       (b) "- Benchmark harness WARNING-2 (README pool-size formula drift) →
       **RESOLVED** (commit `7e837f1`, 2026-11-17): the stale Phase-5
       'requested + 1' sentence now states the pinned contract (exactly 2
       threads at N=1, 2N+1 at N>1)."
       Wrap to the file's existing prose width (about 78 columns) with the
       bullet continuation indent. Keep every other bullet in the block
       (Phase 5/6/7/8 Nyquist, SECURITY.md, cargo fmt, MINIM-01..03)
       byte-identical, and do not touch the "### Deferred to v2.2+" block.
    3. Run the Verify gates, then commit exactly `.planning/ROADMAP.md` as
       one atomic commit: "docs(quick-261118-pja): close ROADMAP benchmark
       harness WARNING-1 carry-forward".
  </action>
  <verify>
    <automated>grep -qF 'quick 261118-pja' .planning/ROADMAP.md # [HEAD=absent EXPECT==present]</automated>
    <automated>grep -qF 'Benchmark harness WARNING-1' .planning/ROADMAP.md # [HEAD=present EXPECT==present GUARD MUTATION: the bullet is replaced in place; deleting it fails this gate]</automated>
    <automated>grep -qF 'Benchmark harness WARNING-2' .planning/ROADMAP.md # [HEAD=absent EXPECT==present]</automated>
    <automated>test -z "$(grep -F 'opportunistic when `scripts/bench/` is touched' .planning/ROADMAP.md)" # [HEAD=present EXPECT==absent]</automated>
    <automated>grep -qF '7e837f1' .planning/ROADMAP.md # [HEAD=absent EXPECT==present]</automated>
    <automated>grep -qF 'status updated 2026-11-18' .planning/ROADMAP.md # [HEAD=absent EXPECT==present]</automated>
    <automated>test -z "$(grep -F 'status updated 2026-11-16' .planning/ROADMAP.md)" # [HEAD=present EXPECT==absent]</automated>
    <automated>grep -qF 'PROMOTED** to v2.1 requirement HYG-02' .planning/ROADMAP.md # [HEAD=present EXPECT==present GUARD MUTATION: collateral edit to the neighbouring bullet fails this gate]</automated>
    <automated>grep -qF 'PROMOTED** to v2.1 requirement HYG-03' .planning/ROADMAP.md # [HEAD=present EXPECT==present GUARD MUTATION: collateral edit to the neighbouring bullet fails this gate]</automated>
    <automated>grep -qF 'MINIM-01..03 (minimizer partitioning / memory ceiling)' .planning/ROADMAP.md # [HEAD=present EXPECT==present GUARD MUTATION: collateral edit to the neighbouring bullet fails this gate]</automated>
    <automated>test -z "$(git status --porcelain -- .planning/STATE.md .planning/milestones scripts/bench)" # [HEAD=absent EXPECT==absent GUARD MUTATION: any extra changed file makes this non-empty]</automated>
    <automated>FILES=$(git show --pretty=format: --name-only HEAD) && printf '%s\n' "$FILES" | grep -qxF '.planning/ROADMAP.md' && test -z "$(printf '%s\n' "$FILES" | grep -vxF '.planning/ROADMAP.md')" # [HEAD=absent EXPECT==present]</automated>
    HEAD baselines are recorded beside each gate. The record gates and the clean-status gate run before the commit; the diff-shape gate runs after it. The three neighbour-presence gates guard against collateral edits: each bullet must still be present exactly as it was.
  </verify>
  <done>ROADMAP's v2.0 carry-forward block marks WARNING-1 RESOLVED with the enforced mechanism, its test coverage, and the historical-document compatibility note; WARNING-2 is marked RESOLVED at commit 7e837f1; the heading reads "status updated 2026-11-18"; every other bullet in the block is byte-identical; one atomic commit touches only ROADMAP.md.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| slice-gate artifact -> CLI session | The gate file is untrusted input whose claims authorize a multi-hour measured run; a forged or stale gate must never authorize it. |
| historical milestone archive -> live render/preflight | Committed v2.0 documents are evidence; a new required field or a render-time file read could make that evidence unreadable. |
| controller source -> recorded result document | The document's `pre_gate` block is the proof of what was consumed; it must name bytes validated before measurement. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-pja-01 | Tampering | scripts/bench/phase10.py `run_cli_session` | high | mitigate | Require `--pre-gate`; validate with the python stage's `_load_slice_gate_doc` (provenance, kind, session-k, k=21 pins, k=31 same-slice), then assert same input fingerprints and the gate's slice source sha256 against part_001, all before any measured work; failed gate exits 2 with no artifact and `run_rounds` uncalled (pinned by test). |
| T-quick-pja-02 | Tampering / Repudiation | recorded CLI document | medium | mitigate | Pin `pre_gate` {path, sha256} using a digest computed immediately after validation and before measurement; the new test asserts the recorded sha equals the gate bytes. |
| T-quick-pja-03 | Repudiation | .planning/milestones/v2.0-phases/10-benchmark-verdict/ | medium | mitigate | No archive edit; no render-time gate read; the render and preflight-python compatibility runs over the committed documents are verify gates, and a clean-status gate rejects archive collateral. |
| T-quick-pja-SC | Tampering | package installs | high | mitigate | No package or dependency is added or installed; only stdlib unittest, the existing controller, and ruff run. |
</threat_model>

<verification>
1. Every Verify-block gate passes with the HEAD baselines recorded beside it;
   the four new CLI-stage tests pass individually and as part of the full
   module (baseline 42 tests, now 46).
2. The python stage is unchanged behaviourally: its existing pre-gate,
   k=31-gate, and preflight tests pass with only the shared fixture's gate
   source sha and the k=31 helper default adjusted.
3. Historical evidence stays readable: the render over the four committed
   v2.0 documents and preflight-python over the two committed CLI documents
   both exit 0 after the change.
4. Commit hygiene: Task 1 commits exactly scripts/bench/phase10.py,
   scripts/bench/tests/test_python_full_arm.py, scripts/bench/README.md;
   Task 2 commits exactly .planning/ROADMAP.md; both staged by explicit
   path, `git status --porcelain` clean afterwards, STATE.md, milestone
   archives, and .claude/CLAUDE.md untouched, no `git add -f`.
5. The SUMMARY records that WARNING-1 is resolved (and WARNING-2's stale
   half is now marked resolved at 7e837f1) so the orchestrator can add the
   STATE.md quick-task row and commit the artifacts.
</verification>

<success_criteria>
- `--stage cli` without `--pre-gate` exits 2 with no artifact.
- A gate that is forged, from other bytes, from another slice, or missing
  the session's k exits 2 before any measured round.
- A valid CLI session records `pre_gate` path+sha256 in its document.
- The two committed v2.0 CLI documents remain render/preflight-readable.
- Four new unittest cases pin the enforcement; the full module and the 127
  adjacent tests are green; ruff shows no new findings.
- ROADMAP closes the WARNING-1 half with evidence and marks WARNING-2
  resolved at 7e837f1, touching nothing else.
</success_criteria>

<output>
Create `.planning/quick/261118-pja-resolve-benchmark-harness-warning-1-the-/261118-pja-SUMMARY.md` when done. Record in it: the exact `run_cli_session` checks and their order (gate before disk floor/preflight/rounds), the `pre_gate` block shape, the four new test names and results, the compatibility command results on the committed documents, the ruff delta result, the two commit hashes and their exact staged paths, and that ROADMAP WARNING-1 is resolved (with WARNING-2 marked resolved at 7e837f1) so the orchestrator can add the STATE.md quick-task row and commit the artifacts.
</output>
