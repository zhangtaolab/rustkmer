---
phase: quick
plan: 261118-fsk
type: execute
wave: 1
depends_on: []
files_modified:
  - pyo3/tests/test_counter.py
  - pyo3/src/counter.rs
  - scripts/bench/n_read_differential.py
  - scripts/bench/tests/test_n_read_differential.py
  - docs/user-guide/n-read-semantics.md
  - scripts/bench/python_bench.py
  - scripts/bench/tests/test_python_bench.py
  - scripts/bench/README.md
  - .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md
autonomous: true
must_haves:
  truths:
    - "IN-01 is recorded as accepted with no code change: the two preservation suites stay as preservation gates and are not cited as proof that the double sort was removed."
    - "The TestPyCounterLocalAccumulationParity docstring names the per-call CountEngine and the checked merge_local_counts bridge, and the stale 'one LocalKmerCounts per file call' wording is gone."
    - "save_database and save_database_on_counter document the lock-free, non-linearizable snapshot and qualify the CLI-identity claim; SaveDatabaseError::Database is documented as a defensive arm; no behavior, signature, or error string changes."
    - "load_previous accepts a prior only when expectation == 'divergence' and totals.python_only_total is a positive integer (bool rejected); the committed pre-D2 artifact still loads unchanged (expectation divergence, python_only_total 33, nine cases)."
    - "The build_cases docstring says record_boundary covers the pre-D2 strip-and-join form and does not prove the absence of cross-record joins; the docs page carries the same qualification; an N-free two-read probe is pinned in the unit suite with per-record 2 distinct/10 total vs concatenated 22 distinct/30 total and 20 chimeric windows."
    - "The live nine-case fixture, the committed pre-D2 artifact, and the delivered Phase 9 evidence artifact are unchanged; the probe is test-local because adding a live case would break --previous's exact case-name check and require regenerating committed artifacts."
    - "test_missing_extension_exits_2 runs n_read_differential.py under an extension-free interpreter (sys.executable -S, PYTHONPATH dropped), exits 2 with the 'cannot import pyrustkmer' message, writes no artifact, and never skips; it passes under both .venv313/bin/python and system python3."
    - "Compare mode rejects --reps < 3 (exit 2) and exits 2 when either measured control arm's cv_warning is set; non-compare modes keep their --reps >= 1 floor and the default --reps 3; README documents both gates; tests pin both."
    - "09-REVIEW.md records IN-01 as Accepted — no code change (quick 261118-fsk), IN-02..IN-08 as Fixed — quick 261118-fsk, and a dated Resolution section states per-finding changes and the observations actually recorded; finding bodies are intact."
    - "One atomic commit contains exactly the nine files above; no dependency, public API, CLI surface (beyond the authorized compare-mode quality guard), .rkdb format, ROADMAP, or STATE.md change is made."
  artifacts:
    - "pyo3/tests/test_counter.py — TestPyCounterLocalAccumulationParity docstring rewritten to the per-call CountEngine + merge_local_counts bridge description."
    - "pyo3/src/counter.rs — save_database/save_database_on_counter non-linearizable-snapshot documentation; SaveDatabaseError::Database defensive-arm documentation."
    - "scripts/bench/n_read_differential.py — expectation/positive-total prior guard; softened record_boundary docstring."
    - "scripts/bench/tests/test_n_read_differential.py — prior-state guard tests, the test-local N-free cross-record probe, and a deterministic extension-free subprocess test."
    - "docs/user-guide/n-read-semantics.md — record-boundary bullet qualified: record_boundary covers only the pre-D2 strip-and-join form."
    - "scripts/bench/python_bench.py — compare-mode --reps >= 3 guard and CV-warning exit-2 gate."
    - "scripts/bench/tests/test_python_bench.py — low-CV fake walls, three-reps guard test, high-CV gate test."
    - "scripts/bench/README.md — compare-mode measurement-quality requirements documented."
    - ".planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md — eight Status cells updated and a dated Resolution section appended."
  key_links:
    - "load_previous <-> the committed pre-D2 artifact at .planning/milestones/v2.0-phases/05-measurement-regression-harness/n_read_differential.json: the hardened guard must still accept it (expectation divergence, python_only_total 33, nine cases), else the documented --previous re-run breaks."
    - "TestCrossRecordJoinProbe <-> build_cases/load_previous exact case-name parity: the probe must stay out of build_cases, because the immutable prior carries exactly nine cases and adding a live case would invalidate --previous and stale the delivered evidence + docs table."
    - "test_missing_extension_exits_2 <-> the lazy 'import pyrustkmer' guard in run_differential: the test must force the import failure itself, not rely on --rustkmer standing in for an interpreter."
    - "compare-mode quality gates <-> compare_to_baseline: the new gates are measurement-validity checks (exit 2, no artifact) layered before the verdict math (exit 0/1); the delivered 3-rep run (1.0%/0.46% CV) remains PASS-capable."
    - "09-REVIEW Resolution section <-> the pinned tests and observed command results: the record states what was actually observed, not what the plan expected."
---

<objective>
Resolve all eight info-only findings from the Phase 09 code review and record their dispositions.

Purpose: this is the last carried review-findings block. Seven findings are documentation or harness-honesty gaps with concrete, small fixes; IN-01 explicitly requires no code change and asks only for an accepted-rationale record. Together they make the PyO3 counting docs honest about the retired LocalKmerCounts path and the non-linearizable save snapshot, harden the N-read differential's prior-state and cross-record-join evidence, make the extension-absent test deterministic, and stop the Python comparison harness from PASSing on a single noisy sample.

Output: one atomic commit touching exactly nine files — the PyO3 docstrings/doc comments, the N-read differential + its unit suite + the semantics page, the comparison-harness quality gates + their tests + the README, and the 09-REVIEW.md resolution record.

Planning shape note: no tracer task. Every change is a documentation, test, or existing-harness guard edit; there is no new end-to-end layer, format, or runtime path to prove (the --no-tracer condition). The only behavior change is the authorized compare-mode exit-2 quality guard in IN-08.

Commit contract (quick executor): implement all three tasks, run every gate, then land ONE atomic commit staging exactly the nine files by explicit path (`git add -- <paths>`; never `git add -A`). Do NOT touch STATE.md, ROADMAP.md, Cargo manifests, dependencies, or any other phase artifact. STATE.md's carried-items rows are orchestrator-owned; the orchestrator updates and commits the PLAN/SUMMARY/STATE artifacts afterwards. Never stage `.claude/CLAUDE.md` (gitignored) and never use `git add -f`.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md
@pyo3/tests/test_counter.py
@pyo3/src/counter.rs
@scripts/bench/n_read_differential.py
@scripts/bench/tests/test_n_read_differential.py
@docs/user-guide/n-read-semantics.md
@scripts/bench/python_bench.py
@scripts/bench/tests/test_python_bench.py
@scripts/bench/README.md

## Planning-time live observations (2026-11-18, HEAD 7ba2223, clean tree)

Line numbers are guidance only; content-based gates are authoritative (mutable-scope authority).

- IN-02: `pyo3/tests/test_counter.py:1116-1126` is `class TestPyCounterLocalAccumulationParity`; the stale sentence is at 1121-1122 (it describes a single per-file `LocalKmerCounts` accumulation merged once at the end). HEAD count for that stale sentence = 1.
- IN-03: `pyo3/src/counter.rs:458-485` is the `save_database` docstring; the identity claim is at 471-472 (unconditional byte identity with the CLI `count` output for the same input, described as thread-count independent); `save_database_on_counter` doc is at 719-728. The snapshot is `counter.get_all_counts()` at 740, no lock.
- IN-07: `pyo3/src/counter.rs:696-706` declares `SaveDatabaseError`; the `Database(String)` variant doc is at 700-701; its `map_err` is at 749-754. `RKDatabase::from_sorted_kmer_pairs` currently cannot fail (the arm is unreachable).
- IN-04: `scripts/bench/n_read_differential.py:144-194` is `load_previous`; it validates k, canonical, exact case-name set and per-case count shape, but copies `expectation`/`totals` through unvalidated. `run_differential` calls it at 327.
- IN-05: `scripts/bench/n_read_differential.py:93-116` is `build_cases`; the false claim is the docstring phrase `equality here proves there` (HEAD = 1, split across lines). `record_boundary` is the two 25 bp reads with N at read1[24] and read2[0]. The docs claim is `docs/user-guide/n-read-semantics.md:15-17`.
- IN-05 artifact coupling: the committed pre-D2 artifact lives at `.planning/milestones/v2.0-phases/05-measurement-regression-harness/n_read_differential.json` (the README's pre-archive path `.planning/phases/...` is stale but out of scope). Its fields: `expectation = "divergence"`, `totals.python_only_total = 33`, exactly nine case names. `load_previous` requires exact case-name-set equality with `build_cases()`, so adding a live case would invalidate --previous and require regenerating the delivered Phase 9 evidence doc and the docs table. Therefore IN-05 is scoped to the unit suite + docstring + docs, per the locked instruction.
- IN-06: `scripts/bench/tests/test_n_read_differential.py:259-269` passes `--rustkmer sys.executable` but the import guard executes in the test process; it fails when the suite runs under `.venv313/bin/python`. Verified live: `python3 -S scripts/bench/n_read_differential.py --rustkmer <path> --out /tmp/x.json` and `.venv313/bin/python -S ...` both print `n_read_differential.py: cannot import pyrustkmer: No module named 'pyrustkmer' ...`, exit 2, and write no artifact. The script is stdlib-only plus its own package and runs fine under `-S`.
- IN-08: `scripts/bench/python_bench.py:870-871` is the only reps check (`>= 1`); compare guards are at 857-885; the two compare arms are measured at 1000-1021; arms' `medians.cv_warning` is set from `reduce_arm` (`scripts/bench/bench.py:1328-1349`, threshold `CV_WARNING_THRESHOLD_PCT = 10.0` at bench.py:62). The verdict math is `compare_to_baseline` at python_bench.py:447-485. `scripts/bench/bench.py`'s separate comparison protocol enters only at `args.reps >= 2` (bench.py:1800) and emits measurements, not a PASS/FAIL verdict — it is inspected and left unchanged. The opt-in `TestRealWorkerIntegration` uses `--reps 1` in synthetic NON-compare mode and stays valid.
- Test harness baselines: `python3 -m unittest scripts.bench.tests.test_n_read_differential` → 33 tests OK; `python3 -m unittest scripts.bench.tests.test_python_bench` → 93 tests OK (1 skipped); combined → 126 tests OK (1 skipped), ~0.3 s. Do NOT run `test_verify_threads.py` (known macOS flake).
- Compile/format baselines: `cargo check --manifest-path pyo3/Cargo.toml` → exit 0, `Finished dev profile`; `cargo fmt --manifest-path pyo3/Cargo.toml --check` → exit 0; `cargo fmt --all --check` → exit 0. The pyo3 crate is NOT a root workspace member, so `-p rustkmer-pyo3` will not resolve; use `--manifest-path`.
- Review record: `09-REVIEW.md` table rows 51-64; Info section 120-184; closing `---`/`_Reviewed:_` at 186-190. HEAD counts: `| Open — out of fix scope |` = 8; `Fixed — quick 261118-fsk` = 0; `Accepted — no code change (quick 261118-fsk)` = 0; `## Resolution 2026-11-18 (quick-261118-fsk)` = 0. Frontmatter (`status: issues_found`, counts) is historical and is NOT edited.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Correct the PyO3 counting docs — IN-02, IN-03, IN-07</name>
  <files>pyo3/tests/test_counter.py, pyo3/src/counter.rs</files>
  <action>
    Documentation and doc-comment edits only. Change no code path, signature, error string, or assertion.

    IN-02 — `pyo3/tests/test_counter.py`, the `TestPyCounterLocalAccumulationParity` class docstring (HEAD 1121-1125). Replace the stale paragraph that describes a single per-file `LocalKmerCounts` accumulation merged once at the end — and that therefore says a parity failure is either a local-accumulation bug or a reduction bug — with wording that says: the file helpers count through a per-call `CountEngine` and merge its partition tables via the checked `merge_local_counts` bridge, so a parity failure here is either a local-accumulation bug or a reduction bug; `add_sequence` deliberately stays on the shared increment path, and comparing both methods against the same reference pins that both surfaces agree. Keep the class's PAR-02 opening sentence and every test body unchanged. Do not reintroduce the stale `LocalKmerCounts` accumulation claim.

    IN-03 — `pyo3/src/counter.rs`, `save_database` docstring Notes (HEAD 463-473). Add one bullet: the counter is snapshotted without locking, so a concurrent `add_*` or `reset` from another Python thread may or may not be reflected in the emitted file, and the emitted file is always internally consistent. Reword the existing identity bullet (which claims unconditional byte identity with the CLI `count` output for the same input, thread-count independent) into a qualified form: absent concurrent mutation, emitted bytes match the CLI `count` output for the same input and are thread-count independent. Keep the sort-once, GIL-release, and load-usage bullets unchanged. Also add one sentence to the `save_database_on_counter` doc (HEAD 719-728): the snapshot is lock-free — `get_all_counts` may observe a concurrent `add_*`/`reset` partially or not at all; the writer always emits an internally consistent database, but it is not promised to be any point-in-time state. The private error enum and the four user-visible messages must stay byte-identical.

    IN-07 — same file, the `SaveDatabaseError::Database` variant doc (HEAD 700-701). Replace "Building the `RKDatabase` from the sorted snapshot failed." with a defensive-arm note: `RKDatabase::from_sorted_kmer_pairs` currently cannot fail; this arm exists only because that constructor returns `ProcessingResult` and would surface a future validation error instead of discarding it. Optionally add a one-line comment at the `.map_err` site (HEAD 749-754) pointing at the same defensive rationale. Do not remove the arm, do not change the constructor call, and do not change the Display text ("Failed to create database: ...").

    Keep doc-comment line widths in the file's existing style. Run `cargo fmt --manifest-path pyo3/Cargo.toml --check` after the edit; comments are not reformatted by default, so it only guards accidental code movement.
  </action>
  <verify>
    <automated>test "$(grep -v '^[[:space:]]*#' pyo3/tests/test_counter.py | grep -cF 'one `LocalKmerCounts` per file call')" -eq 0 # [HEAD=1 EXPECT==0]</automated>
    <automated>test "$(grep -cF 'per-call `CountEngine`' pyo3/tests/test_counter.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'checked `merge_local_counts` bridge' pyo3/tests/test_counter.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'taken without locking' pyo3/src/counter.rs)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'always internally consistent' pyo3/src/counter.rs)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'With no concurrent mutation' pyo3/src/counter.rs)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'currently cannot fail' pyo3/src/counter.rs)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'Failed to create database: ' pyo3/src/counter.rs)" -ge 1 # [HEAD=1 EXPECT>=1 GUARD MUTATION: changing the preserved Display text drops this to 0]</automated>
    <automated>test "$(grep -cF 'The emitted bytes are identical to the CLI `count` output for the' pyo3/src/counter.rs)" -eq 0 # [HEAD=1 EXPECT==0]</automated>
    <automated>python3 -c "import ast, pathlib; ast.parse(pathlib.Path('pyo3/tests/test_counter.py').read_text())" # [HEAD=0 EXPECT==0 GUARD MUTATION: a syntax error introduced by the docstring edit makes ast.parse exit non-zero]</automated>
    <automated>cargo check --manifest-path pyo3/Cargo.toml # [HEAD=0 EXPECT==0 GUARD MUTATION: a type or syntax error introduced by the doc edit makes cargo check exit non-zero]</automated>
    <automated>cargo fmt --manifest-path pyo3/Cargo.toml --check # [HEAD=0 EXPECT==0 GUARD MUTATION: accidental code reformatting makes cargo fmt --check exit non-zero]</automated>
    HEAD baselines are recorded beside each gate. Prose summary: the stale LocalKmerCounts sentence is present once at HEAD and must be gone; the new doc phrases are absent at HEAD and must appear; the four-message contract's Database text stays; the unqualified identity claim is replaced; the test file must still parse; the pyo3 crate must compile and stay rustfmt-clean.
  </verify>
  <done>The IN-02 docstring names the per-call CountEngine and merge_local_counts bridge with no LocalKmerCounts claim; save_database and save_database_on_counter document the lock-free non-linearizable snapshot and qualify the CLI-identity claim; SaveDatabaseError::Database is documented as defensive; all behavior, signatures, and error strings are unchanged; the pyo3 crate compiles and is rustfmt-clean.</done>
</task>

<task type="auto">
  <name>Task 2: Harden the N-read differential — IN-04, IN-05, IN-06</name>
  <files>scripts/bench/n_read_differential.py, scripts/bench/tests/test_n_read_differential.py, docs/user-guide/n-read-semantics.md</files>
  <action>
    A. IN-04 — `scripts/bench/n_read_differential.py` `load_previous` (HEAD 144-194).
    1. After the canonical check and BEFORE the cases validation, read `expectation = data.get("expectation")`; if it is not exactly `"divergence"`, raise `ValueError` whose message starts `prior artifact expectation=` and states clearly that only a pre-D2 divergence record can be a before state, naming the path (inline literal `is not 'divergence'`).
    2. Read `totals = data.get("totals")`; if it is not a dict, raise `ValueError` naming the missing totals block and the path. Read `python_only_total = totals.get("python_only_total")`; if it is not an `int` (bool must be rejected explicitly) or is `<= 0`, raise `ValueError` whose message contains `totals.python_only_total=` and the literal `is not a positive integer`, stating that a prior with no recorded divergence cannot be a before state, naming the path.
    3. Return the validated `expectation` and `totals` values instead of re-reading them with `data.get(...)`.
    4. Update the docstring: a prior must itself record the pre-D2 divergence (`expectation == "divergence"` and a positive integer `totals.python_only_total`) in addition to the existing k/canonical/case-set/shape checks. Do not change the k, canonical, case-set, or per-case count validations, and do not pin a committed sha256.

    B. IN-04 tests — `scripts/bench/tests/test_n_read_differential.py`, `TestPreviousLoading`. The shared `valid_prior()` already has `expectation: "divergence"` and `totals.python_only_total: 33`; keep it passing. Add:
    1. `test_non_divergence_expectation_raises`: for `"unified"` and for a popped `expectation`, `assert_invalid` raises.
    2. `test_missing_or_malformed_totals_raise`: over mutations that pop `totals`, set `totals` to None, pop `python_only_total`, and set `python_only_total` to 0, -3, `"33"`, `33.0`, and `True`, each raises ValueError. The bool and float cases pin the explicit `isinstance(..., int) and not isinstance(..., bool)` rule.

    C. IN-05 — `scripts/bench/n_read_differential.py` `build_cases` docstring (HEAD 93-116). Replace the claim that `record_boundary` equality proves there are no cross-record joins with: `record_boundary` predates D2 — its terminal Ns sit in the boundary windows, so under skip-N it only covers the pre-D2 strip-and-join form (joining the N-free flanks) and does NOT prove the absence of cross-record joins; the N-free two-read probe in the unit suite (`TestCrossRecordJoinProbe`) is the shape that would expose a join-based implementation; it stays out of this fixture because adding a live case would break `--previous`'s exact case-name check against the immutable pre-D2 artifact and require regenerating the committed evidence. Keep the window_end/window_start/short_read explanations and the nine returned cases byte-identical.

    D. IN-05 docs — `docs/user-guide/n-read-semantics.md:15-17`. Keep the true statement that windows never span record boundaries and that each record is counted on its own (enforced by per-record window extraction), and add the qualification that the differential's `record_boundary` case only covers the pre-D2 strip-and-join form — its terminal Ns suppress the boundary-spanning windows under skip-N, so it is not the post-D2 proof. Do not change the measured-evidence table or any count.

    E. IN-05 test-suite probe — same test file. Add `class TestCrossRecordJoinProbe(ImplementedGate)`:
    1. Class-level `READS = ("A" * 25, "C" * 25)` with a docstring explaining that the live `record_boundary` case cannot detect a join (terminal Ns are skipped) and that this probe is test-local because the committed pre-D2 artifact has exactly the nine legacy cases and `load_previous` requires an exact case-name set — adding a live case would invalidate the immutable before state and require regenerating the delivered Phase 9 evidence and the docs table.
    2. `test_probe_case_is_two_n_free_reads_longer_than_k`: assert two reads, no `N`/`n`, each length > `nrd.K`, and that `nrd.fastq_bytes({"name": "records_no_n_boundary", "reads": list(self.READS)})` has the four-line shape (8 lines; quality length equals sequence length).
    3. `test_concatenation_creates_chimeric_windows_not_produced_per_record`: compute per-record length-K windows and concatenated length-K windows with plain Python; pin distinct/total = 2/10 for per-record and 22/30 for concatenated, 20 chimeric keys, `"A" * 20 + "C"` and `"A" + "C" * 20` both present, and an empty intersection between chimeric and per-record keys. This is the fixture shape that a cross-record-join implementation would fail.

    F. IN-06 — `scripts/bench/tests/test_n_read_differential.py`, `test_missing_extension_exits_2` (HEAD 259-269). Replace the in-process `run_main` invocation with a subprocess run of the real script under an extension-free interpreter:
    1. Add `import os` and `import subprocess` to the module imports (stdlib only; keep the existing guarded `nrd` import).
    2. Build a child env from `os.environ` with `PYTHONPATH` removed, so neither site-packages nor a PYTHONPATH entry can re-expose the extension.
    3. Run `subprocess.run([sys.executable, "-S", str(Path(nrd.__file__)), "--rustkmer", sys.executable, "--out", str(out)], capture_output=True, text=True, env=env)` in a `tempfile.TemporaryDirectory`.
    4. Assert `proc.returncode == 2` (pass `proc.stderr` as the failure message), `"cannot import pyrustkmer" in proc.stderr`, and that `out` does not exist. Do not add a skip, do not weaken the rc/message assertions, and keep the test name (09-REVIEW.md references it).
    Live confirmation: this exact shape prints `n_read_differential.py: cannot import pyrustkmer: No module named 'pyrustkmer' ...`, exits 2, and writes no artifact under both system `python3` and `.venv313/bin/python`.
  </action>
  <verify>
    <automated>test "$(grep -cF 'prior artifact expectation=' scripts/bench/n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF "is not 'divergence'" scripts/bench/n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'is not a positive integer' scripts/bench/n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -v '^[[:space:]]*#' scripts/bench/n_read_differential.py | grep -cF 'equality here proves there')" -eq 0 # [HEAD=1 EXPECT==0]</automated>
    <automated>test "$(grep -cF 'pre-D2 strip-and-join form' scripts/bench/n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'def test_non_divergence_expectation_raises' scripts/bench/tests/test_n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'def test_missing_or_malformed_totals_raise' scripts/bench/tests/test_n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'class TestCrossRecordJoinProbe' scripts/bench/tests/test_n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'def test_concatenation_creates_chimeric_windows_not_produced_per_record' scripts/bench/tests/test_n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF '"-S"' scripts/bench/tests/test_n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'cannot import pyrustkmer' scripts/bench/tests/test_n_read_differential.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'covers the pre-D2 strip-and-join form' docs/user-guide/n-read-semantics.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>python3 -c "from scripts.bench import n_read_differential as n; p = n.load_previous('.planning/milestones/v2.0-phases/05-measurement-regression-harness/n_read_differential.json'); assert p['expectation'] == 'divergence'; assert p['totals']['python_only_total'] == 33; assert len(p['cases']) == 9" # [HEAD=0 EXPECT==0 GUARD MUTATION: an over-strict guard rejects the committed prior and this command exits non-zero]</automated>
    <automated>python3 -m unittest scripts.bench.tests.test_n_read_differential # [HEAD=0 EXPECT==0 GUARD MUTATION: a broken guard or new test makes unittest exit non-zero]</automated>
    HEAD baselines are recorded beside each gate. Prose summary: the new guard messages and softened docstring are absent at HEAD; the false proof claim is present once at HEAD and must be gone; the probe class/test and the `-S` subprocess marker are absent at HEAD; the docs qualification is absent at HEAD; the committed pre-D2 artifact must still load with its 33-divergence totals and nine cases; the unit module is green at HEAD (33 tests) and must stay green with the new tests.
  </verify>
  <done>load_previous rejects a non-divergence or zero-divergence prior with a specific ValueError while still accepting the committed pre-D2 artifact (33 python-only keys, nine cases); the build_cases docstring and the semantics page say record_boundary covers only the pre-D2 strip-and-join form; an N-free two-read probe pins per-record 2/10 vs concatenated 22/30 with 20 chimeras in the unit suite, and the live fixture plus committed artifacts are untouched; test_missing_extension_exits_2 runs the script under `-S` in a subprocess, asserts rc 2 and the specific import message, writes no artifact, and never skips.</done>
</task>

<task type="auto">
  <name>Task 3: Gate compare-mode measurement quality (IN-08), record the resolutions, commit atomically</name>
  <files>scripts/bench/python_bench.py, scripts/bench/tests/test_python_bench.py, scripts/bench/README.md, .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md</files>
  <action>
    A. IN-08 — `scripts/bench/python_bench.py`.
    1. Add `CV_WARNING_THRESHOLD_PCT` to the existing `from scripts.bench.bench import (...)` list.
    2. In `run_controller`, keep the generic `--reps must be >= 1` check for all modes, then add a compare-only guard: when `args.compare_baseline is not None` and `args.reps < 3`, raise `ValueError` whose message contains `--compare-baseline requires --reps >= 3` and states that a comparison verdict must rest on at least three measured samples per arm (naming the received value). This raises before any measurement and exits 2 with no artifact.
    3. In the `if compare:` block, immediately after the default-threads control arm is measured (after its `evidence_class` assignment and before `control_block` is built), collect `noisy = [arm["name"] for arm in (control_arm, default_arm) if arm["medians"].get("cv_warning")]`; if non-empty, raise `ValueError` containing `quality-controlled measurements` and `cv_warning`, naming the flagged arms and the `CV_WARNING_THRESHOLD_PCT` threshold, and stating that no verdict is computed from noisy arms. This is an invalid-measurement exit 2 (no artifact), not a FAIL verdict (exit 1).
    4. Do NOT change the argparse default `--reps 3`, the generic `>= 1` floor for non-compare modes, `compare_to_baseline`'s math, or any existing error string.

    B. IN-08 tests — `scripts/bench/tests/test_python_bench.py`.
    1. Extend `make_fake_measure` with an optional `walls=None` sequence: when provided and the call index is in range, return `walls[i]` as `wall_s`; otherwise keep `1.0 + i`. Do not change its stats payload or threads behavior.
    2. Add `LOW_CV_COMPARE_WALLS = (0.5, 0.5, 3.9, 4.0, 4.1, 0.5, 7.9, 8.0, 8.1)` and a `make_low_cv_measure(module_path)` helper. The call order in compare mode is control parity warmup (0), t1 warmup (1) + measured reps (2-4), default warmup (5) + measured reps (6-8), so the t1 median stays 4.0 and the default median stays 8.0 while each arm's CV is 2.5% (below the 10% threshold).
    3. Extend `TestCompareController.run_compare` with `measure=None`, defaulting to `make_low_cv_measure(self.module)`. The existing PASS/FAIL tests keep their asserted speedups (3.0/1.5 and 2.0/1.0) unchanged and now pass the CV gate.
    4. Add `test_compare_requires_three_reps`: loop `reps` in ("1", "2"), replace the `--reps` value in `compare_argv`, expect exit 2, `"--reps >= 3"` in stderr, and no output artifact.
    5. Add `test_compare_high_cv_exits_2`: call `run_compare(baseline, measure=make_fake_measure(self.module))` (the default monotone walls give 25% CV on each arm), expect exit 2, `cv_warning` in stderr, and no artifact.
    6. Leave `TestRealWorkerIntegration`'s `--reps 1` synthetic non-compare invocation untouched.

    C. IN-08 docs — `scripts/bench/README.md`, baseline-comparison section near "There is no noise band" (HEAD ~212-231). Add: a comparison verdict requires `--reps >= 3` (fewer measured samples per arm exits 2), and each measured control arm's wall-time CV is a gate — if either arm's `cv_warning` is set (CV above the 10% warning threshold), the run exits 2 as an invalid measurement and no verdict is computed. Keep the existing "no noise band", threads, and baseline-identity text unchanged.

    D. Record — `.planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md`. Use `Edit` for scoped replacements; never rewrite the whole file.
    1. Findings Overview table (HEAD 51-64): change only the eight Status cells. IN-01 becomes `Accepted — no code change (quick 261118-fsk)`; IN-02 through IN-08 become `Fixed — quick 261118-fsk`. Leave IDs, severities, file lists, finding text, and row order intact. Leave the frontmatter and the four Warning rows untouched.
    2. Append `## Resolution 2026-11-18 (quick-261118-fsk)` after the Info section (after the IN-08 body, before the closing `---`/`_Reviewed:_` lines). State that all eight Info findings are closed, that the finding bodies/frontmatter above are the historical review record and unchanged, and give one bullet per finding:
       - IN-01: accepted, no code change — the two suites remain preservation gates and also pass on the parent implementation, so they are not cited as proof the double sort was removed; that property remains proven by code inspection and the 09-02 static greps.
       - IN-02: docstring now names the per-call CountEngine and checked merge_local_counts bridge; add_sequence stays on the shared increment path; old wording gone.
       - IN-03: save_database/save_database_on_counter document the lock-free non-linearizable snapshot and qualify the CLI-identity claim; behavior unchanged.
       - IN-04: load_previous now requires expectation == "divergence" and a positive integer totals.python_only_total; the committed pre-D2 artifact still loads (33, nine cases); tests added.
       - IN-05: build_cases docstring and the semantics page now scope record_boundary to the pre-D2 strip-and-join form; the N-free two-read probe is pinned in the unit suite (per-record 2/10 vs concatenated 22/30, 20 chimeras). Record the reason it is test-local: the immutable pre-D2 artifact carries exactly nine cases, load_previous requires exact case-name parity, and a live case would require regenerating the delivered Phase 9 evidence artifact and the docs table.
       - IN-06: the test now runs the script under `sys.executable -S` with PYTHONPATH dropped, asserts rc 2 and `cannot import pyrustkmer`, writes no artifact, and has no skip; deterministic under both interpreters.
       - IN-07: SaveDatabaseError::Database kept and documented as defensive; no signature or behavior change.
       - IN-08: compare mode now requires --reps >= 3 and exits 2 when either control arm's cv_warning is set; README and tests updated; the delivered 3-rep run (1.0%/0.46% CV) remains valid. Note that bench.py's separate `--reps >= 2` comparison protocol was inspected and left unchanged because a single rep cannot enter it and it emits measurements, not a PASS/FAIL verdict.
       Record the ACTUAL observed results for the targeted commands (test counts/exit codes and the cargo check result), not the plan's expectations. Do not rewrite the original finding text, the Triage-style order, or the frontmatter.

    E. Run every gate in the Verify block except the final commit-shape gates. Confirm `git diff --name-only` lists exactly the nine files named in the frontmatter, stage exactly those nine by explicit path (`git add -- <paths>`; never `git add -A`), and create ONE atomic commit with message: `fix(quick-261118-fsk): resolve the eight Phase-09 info-only review findings`. After the commit, run the two commit-shape gates.
  </action>
  <verify>
    <automated>test "$(grep -cF -- '--compare-baseline requires --reps >= 3' scripts/bench/python_bench.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'quality-controlled measurements' scripts/bench/python_bench.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'CV_WARNING_THRESHOLD_PCT' scripts/bench/python_bench.py)" -ge 2 # [HEAD=0 EXPECT>=2]</automated>
    <automated>test "$(grep -cF -- '--reps must be >= 1' scripts/bench/python_bench.py)" -ge 1 # [HEAD=1 EXPECT>=1 GUARD MUTATION: removing the non-compare floor drops this to 0]</automated>
    <automated>test "$(grep -cF 'def test_compare_requires_three_reps' scripts/bench/tests/test_python_bench.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'def test_compare_high_cv_exits_2' scripts/bench/tests/test_python_bench.py)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'LOW_CV_COMPARE_WALLS' scripts/bench/tests/test_python_bench.py)" -ge 2 # [HEAD=0 EXPECT>=2]</automated>
    <automated>test "$(grep -cF -- '--reps >= 3' scripts/bench/README.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'There is no noise band' scripts/bench/README.md)" -ge 1 # [HEAD=1 EXPECT>=1 GUARD MUTATION: deleting the existing no-noise-band statement drops this to 0]</automated>
    <automated>python3 -m unittest scripts.bench.tests.test_python_bench # [HEAD=0 EXPECT==0 GUARD MUTATION: a broken compare guard or test makes unittest exit non-zero]</automated>
    <automated>python3 -m unittest scripts.bench.tests.test_n_read_differential scripts.bench.tests.test_python_bench # [HEAD=0 EXPECT==0 GUARD MUTATION: a cross-module regression makes the combined run exit non-zero]</automated>
    <automated>test "$(grep -cF '| Fixed — quick 261118-fsk |' .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md)" -ge 7 # [HEAD=0 EXPECT>=7]</automated>
    <automated>test "$(grep -cF '| Accepted — no code change (quick 261118-fsk) |' .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF '| Open — out of fix scope |' .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md)" -eq 0 # [HEAD=8 EXPECT==0]</automated>
    <automated>test "$(grep -cF '## Resolution 2026-11-18 (quick-261118-fsk)' .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF '### IN-01: Preservation gates also pass on the parent implementation' .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md)" -ge 1 # [HEAD=1 EXPECT>=1 GUARD MUTATION: rewriting finding bodies drops this to 0]</automated>
    <automated>test "$(grep -cF 'quick-261118-fsk' .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md)" -ge 9 # [HEAD=0 EXPECT>=9]</automated>
    <automated>git diff --name-only HEAD > /tmp/fsk_changed.txt && test "$(LC_ALL=C sort /tmp/fsk_changed.txt | tr '\n' ' ')" = ".planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md docs/user-guide/n-read-semantics.md pyo3/src/counter.rs pyo3/tests/test_counter.py scripts/bench/README.md scripts/bench/n_read_differential.py scripts/bench/python_bench.py scripts/bench/tests/test_n_read_differential.py scripts/bench/tests/test_python_bench.py " # pre-commit scope check [HEAD=absent EXPECT==present]</automated>
    <automated>git show --pretty=format: --name-only HEAD > /tmp/fsk_commit_files.txt && test "$(LC_ALL=C sort /tmp/fsk_commit_files.txt | tr '\n' ' ')" = ".planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md docs/user-guide/n-read-semantics.md pyo3/src/counter.rs pyo3/tests/test_counter.py scripts/bench/README.md scripts/bench/n_read_differential.py scripts/bench/python_bench.py scripts/bench/tests/test_n_read_differential.py scripts/bench/tests/test_python_bench.py " # post-commit shape [HEAD=absent EXPECT==present]</automated>
    HEAD baselines are recorded beside each gate; the two commit-shape gates run after the commit. Prose summary: the new guards/tests/README text are absent at HEAD; the non-compare reps floor and the no-noise-band statement must remain; both Python modules are green at HEAD (93 + 33) and must stay green; all eight Open cells become seven Fixed plus one Accepted and zero Open; the Resolution heading and the IN-01 body are pinned; the quick id appears at least nine times; the working-tree diff and the landed commit each contain exactly the nine intended files.
  </verify>
  <done>Compare mode rejects --reps < 3 and CV-warning arms with exit 2 and no artifact, while non-compare modes are unchanged; the README documents both gates; the tests pin the reps guard, the CV guard, and the low-CV PASS/FAIL math; 09-REVIEW.md shows seven Fixed and one Accepted status with a dated Resolution section and untouched finding bodies; exactly the nine intended files are one atomic commit.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| prior artifact file -> embedded `before` block | An attacker or a stale post-D2 rerun could be embedded as pre-D2 history if the prior is not required to record divergence. |
| measurement samples -> comparison PASS verdict | A single or high-variance sample can clear the locked speedup thresholds by noise. |
| review record -> planning truth | A record that still says Open after the fixes causes re-triage or silent loss of the resolution evidence. |
| test fixture -> committed differential evidence | Changing the live case set would silently invalidate the immutable pre-D2 artifact and the delivered Phase 9 evidence. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-fsk-01 | Repudiation | scripts/bench/n_read_differential.py load_previous | medium | mitigate | Require `expectation == "divergence"` and a positive integer `totals.python_only_total`; reject bool/float/zero/absent; pin with two TestPreviousLoading tests and verify the committed prior still loads. |
| T-quick-fsk-02 | Repudiation | scripts/bench/python_bench.py compare verdict | medium | mitigate | Require `--reps >= 3` and exit 2 when either control arm's `cv_warning` is set; pin with two TestCompareController tests and a low-CV fake measure preserving the existing verdict math assertions. |
| T-quick-fsk-03 | Repudiation | .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md | low | mitigate | Flip exactly the eight Status cells, preserve finding bodies and frontmatter, and append a dated Resolution that records the observed commands/results rather than expectations. |
| T-quick-fsk-04 | Tampering | scripts/bench/n_read_differential.py build_cases vs committed artifacts | medium | mitigate | Keep the live nine-case fixture unchanged; pin the N-free cross-record probe test-locally and record why regeneration would be required; gate that the live case set and committed prior still load. |
| T-quick-fsk-SC | Tampering | npm/pip/cargo installs | high | mitigate | No dependency is added or installed; the only cargo commands are `cargo check`/`cargo fmt` on existing manifests, and all Python tests are stdlib unittest. |
</threat_model>

<verification>
1. Task 1: stale LocalKmerCounts wording absent; new doc phrases present; unqualified CLI-identity claim replaced; preserved Database error text present; `ast.parse` passes; `cargo check --manifest-path pyo3/Cargo.toml` and `cargo fmt --manifest-path pyo3/Cargo.toml --check` both exit 0 (baseline: both pass at HEAD).
2. Task 2: the prior-state guard and its tests exist; the false cross-record-join proof claim is gone from code and qualified in docs; the test-local probe pins 2/10 vs 22/30 with 20 chimeras; the committed pre-D2 artifact still loads (33, nine cases); the `-S` subprocess test is deterministic and asserts rc 2 plus the specific message; the module is green (33 at HEAD, expected to grow).
3. Task 3: compare-mode reps and CV guards exist and are pinned; non-compare floor and default reps untouched; both Python modules green; review table reads 7 Fixed + 1 Accepted + 0 Open and the Resolution section exists with bodies intact; exactly nine files in the working-tree diff and the landed commit.
4. Scope: no dependency, public API, .rkdb format, ROADMAP, STATE.md, or non-compare CLI behavior change; the only behavior change is the authorized compare-mode exit-2 quality guard.
</verification>

<success_criteria>
- IN-01: accepted with no code change, with the preservation-gate rationale recorded in 09-REVIEW.md.
- IN-02: docstring describes the per-call CountEngine and checked merge_local_counts bridge; LocalKmerCounts claim gone.
- IN-03: both save docs state the lock-free, non-linearizable snapshot and qualify the CLI-identity claim; behavior unchanged.
- IN-04: prior must record divergence (expectation + positive integer total); committed artifact still accepted; pinned by tests.
- IN-05: build_cases docstring and docs page scope record_boundary to the pre-D2 strip-and-join form; the N-free two-read probe is pinned in the unit suite; live fixture and committed artifacts unchanged; the non-regeneration reason is recorded.
- IN-06: extension-absent test is deterministic under both interpreters, never skips, and asserts rc 2 + the specific message.
- IN-07: SaveDatabaseError::Database documented as defensive; signature and behavior unchanged.
- IN-08: compare mode requires `--reps >= 3` and exits 2 on any arm's cv_warning; README and tests updated; non-compare modes untouched.
- 09-REVIEW.md: seven Fixed / one Accepted / zero Open; dated Resolution with observed evidence; finding bodies intact.
- One atomic commit, exactly nine files, no unrelated change.
</success_criteria>

<output>
Create `.planning/quick/261118-fsk-resolve-the-8-phase-09-info-only-review-/261118-fsk-SUMMARY.md` when done.
</output>
