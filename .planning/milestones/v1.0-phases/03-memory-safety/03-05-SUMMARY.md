---
phase: 03-memory-safety
plan: 05
subsystem: database
tags: [rust, pyo3, python, merge, memory-budget, admission-control, keyword-args, mutation-testing]

requires:
  - phase: 03-memory-safety
    plan: 01
    provides: "the bounded merge core this plan exposes: RKDatabase::merge_databases with the header-only estimator (D-01), the MERGE-02 hard route, and the D-02 over-budget 'memory' reject"
  - phase: 03-memory-safety
    plan: 04
    provides: "the nonexistent-temp_dir route-observation probe and the documented 'derive the budget, prove the route' discipline this plan's Python tests reuse"
  - phase: 02-parallel-counting
    provides: "PyCounter's threads= kwarg (02-03) — the boundary-validation + keyword-only-signature precedent PyDatabase.merge now mirrors (PCOUNT-03 must not regress)"
provides:
  - "pyrustkmer.PyDatabase.merge(databases, output, *, max_memory=None, merge_mode='auto') — keyword-only budget/strategy control, CLI --max-memory / --merge-mode parity (MERGE-04)"
  - "merge_mode validated against {auto, memory, streaming} at the Python boundary (PyValueError, T-03-15); the core's silent unknown-mode-equals-auto fallback is no longer reachable from Python"
  - "max_memory parsed by the CLI's own parse_memory_size, made pub instead of copied — one grammar, one set of bounds, two surfaces (T-03-16)"
  - "The D-02 over-budget reject bridged to Python as a PyRuntimeError carrying the core's message, byte counts included (T-03-17)"
  - "pyo3/tests/test_database_merge.py — 11 GREEN contract tests, 4 mutation-verified, 0 skipped, including a Python-level route PROOF rather than an assumed route"
  - "2 new entries in deferred-items.md + 2 new open entries in .planning/WINDOWS.md (pyo3 packaging + pytest addopts, both pre-existing)"
affects: [phase-04-benchmark, /gsd-verify-work, /gsd-ship]

actuals:
  tokens: 12400
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Reuse the surface's parser rather than copying it: making the CLI's parse_memory_size pub costs one word and permanently prevents CLI/Python grammar drift, where a local parse_memory_size_py would drift silently"
    - "Route proof lifted to Python: monkeypatch TMPDIR at a nonexistent directory turns MergeConfig::temp_dir (which defaults to std::env::temp_dir(), re-read per call) into a side-effect discriminator — the 03-01 probe needs no new API and no log capture on either surface"
    - "Assert the numbers the core computed, not just that it errored: a D-02 reject that quotes the wrong byte counts would prove the kwargs never reached MergeConfig"

key-files:
  created:
    - pyo3/tests/test_database_merge.py
  modified:
    - pyo3/src/database.rs
    - src/cli/commands/merge.rs
    - .planning/phases/03-memory-safety/deferred-items.md

key-decisions:
  - "parse_memory_size is REUSED from src/cli/commands/merge.rs (made pub) rather than reimplemented in the binding. The plan allowed either; reuse is the one that cannot rot. A duplicated parser would accept different strings on the two surfaces and nothing would notice until a user's budget behaved differently in Python than in the shell — which is the exact failure MERGE-04 exists to prevent."
  - "Both kwargs are keyword-ONLY (`*` in the pyo3 signature), mirroring PyCounter(threads=...) from 02-03. Positional max_memory/merge_mode are now a TypeError. This is a narrowing of the accepted call shapes rather than a break: the pre-MERGE-04 signature took exactly two positional args, so no existing caller can regress."
  - "MergeConfig is assembled with struct-update syntax, not field-by-field assignment. The plan's action text spelled out `let mut config = MergeConfig::default(); config.merge_mode = ...`, which the pyo3 crate's own `-D warnings` gate rejects as clippy::field_reassign_with_default. The plan listed that clippy command as a blocking acceptance criterion, so the assembly form had to give."
  - "max_memory=None resolves to MergeConfig::default().max_memory_usage (50% of system memory) rather than being left to a second default lookup — the value is read once and echoed into the struct, so there is exactly one source for 'unset'."
  - "The pyo3 test suite has NO strategy-returning API and I did not add one. Route selection is observed from Python through its filesystem side effect (TMPDIR), matching 03-01/03-04; a `merge` return value or a `last_strategy_used` field would be new public surface for a test-only need."
  - "The over-budget budget in the tests is 1024 bytes — the smallest value parse_memory_size accepts — and it is only usable because the helper ASSERTS the derived estimate exceeds it first. That assertion is the real content: it converts 'the fixture got smaller' from a silent vacuous test into a loud failure. Same reasoning as 03-04's over_budget_config."
  - "Pre-existing pyo3 breakage (maturin's python-source pairing, and the --cov-fail-under=80 addopts gate) was REPORTED, not fixed. Both are outside MERGE-04: the first is a packaging-config change that would alter the CI artifact, the second changes the quality bar every later contributor runs under. Both are recorded in deferred-items.md and WINDOWS.md with suggested one-line fixes."

patterns-established:
  - "Mutation-test a binding task: four defects injected into the PyO3 layer (drop each MergeConfig assignment, remove the mode validation, swallow the parse error), each caught by a specific named test. For a plan whose deliverable is 'a kwarg reaches the core', the mutation IS the proof — a GREEN test that cannot fail would report MERGE-04 verified while proving nothing."
  - "Header total_kmers counts RECORDS, not the sum of counts — RKDatabase::from_kmer_pairs writes entries.len() into both total_kmers and unique_kmers. Count conservation must therefore be asserted on the exported map, not on the header. The first draft of the smoke test asserted header total_kmers == 150 against a 110-k-mer merge and failed immediately; the correct split is header == records AND sum(counts) == 150."

requirements-completed: [MERGE-04]

coverage:
  - id: D1
    description: "PyDatabase.merge exposes keyword-only max_memory and merge_mode kwargs and threads them into MergeConfig, so Python reaches the same RKDatabase::merge_databases core the CLI uses"
    requirement: MERGE-04
    verification:
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_merge_signature_exposes_the_cli_kwargs (both kwargs present in the public __doc__ and __text_signature__)"
        status: pass
      - kind: integration
        ref: "mutation: delete `config.merge_mode = merge_mode` -> test_streaming_route_is_proven_by_its_chunk_files[streaming] FAILS"
        status: pass
      - kind: other
        ref: "grep -nE 'pyo3\\(signature' pyo3/src/database.rs | grep -E 'max_memory|merge_mode' -> line 1367, both kwargs; PyDatabase.merge.__text_signature__ == '(databases, output, *, max_memory=None, merge_mode=...)'"
        status: pass
    human_judgment: false
  - id: D2
    description: "max_memory is parsed by the CLI's own grammar, so a Python budget and a shell budget cannot mean different byte counts"
    requirement: MERGE-04
    verification:
      - kind: integration
        ref: "src/cli/commands/merge.rs::parse_memory_size is now `pub` and is the only parser; pyo3/src/database.rs calls rustkmer::cli::commands::merge::parse_memory_size (single definition, grep-verified)"
        status: pass
      - kind: integration
        ref: "mutation: replace the parse with .unwrap_or(usize::MAX) -> test_merge_rejects_bad_max_memory FAILS"
        status: pass
      - kind: other
        ref: "cargo test -> root suite green (221 lib + 34 golden + 26 merge_cleanup + 26 merge_routing + ... , 0 failures), so the CLI's own --max-memory behaviour is unchanged"
        status: pass
    human_judgment: false
  - id: D3
    description: "Invalid merge_mode is rejected at the Python boundary with a matchable PyValueError instead of silently behaving as 'auto'"
    requirement: MERGE-04
    verification:
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_merge_rejects_bad_merge_mode (pytest.raises(ValueError, match='merge_mode'))"
        status: pass
      - kind: integration
        ref: "mutation: `if false && !VALID_MERGE_MODES.contains(...)` -> test_merge_rejects_bad_merge_mode FAILS with 'DID NOT RAISE ValueError'"
        status: pass
    human_judgment: false
  - id: D4
    description: "A malformed max_memory string is rejected with PyValueError carrying the parser's own reason"
    requirement: MERGE-04
    verification:
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_merge_rejects_bad_max_memory (pytest.raises(ValueError, match='max_memory'))"
        status: pass
    human_judgment: false
  - id: D5
    description: "The D-02 over-budget reject reaches Python: merge_mode='memory' with a budget below the real estimate raises PyRuntimeError whose message names the streaming alternative and the byte counts the core computed"
    requirement: MERGE-04
    verification:
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_over_budget_memory_mode_is_rejected (asserts 'rejected', 'streaming', f'{estimate} bytes', f'{budget} bytes')"
        status: pass
      - kind: integration
        ref: "mutation: drop the max_memory_usage MergeConfig assignment -> this test FAILS (and so does the auto hard-route proof)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The selected merge route is PROVEN at the Python boundary, not assumed: with TMPDIR pointed at a nonexistent directory the streaming route fails on its chunk file while the in-memory route succeeds on the same fixture"
    requirement: MERGE-04
    verification:
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_streaming_route_is_proven_by_its_chunk_files[streaming] and [auto] (assert the error names the bogus dir and 'Failed to create temp file')"
        status: pass
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_inmemory_route_never_touches_temp_dir[auto] and [memory] (the control: same fixture, same bogus TMPDIR, exact union returned)"
        status: pass
    human_judgment: false
  - id: D7
    description: "MERGE-02's hard route and MERGE-01's data correctness hold when reached from Python: over-budget 'auto' completes with the exact union, and the streaming and in-memory routes return identical data"
    requirement: MERGE-04
    verification:
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_over_budget_auto_hard_route_completes"
        status: pass
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_streaming_and_inmemory_routes_produce_identical_data (full exported count map equality + header accounting + count conservation on both routes)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Backward compatibility: the pre-MERGE-04 two-positional-arg call still merges correctly under the bounded dispatcher"
    requirement: MERGE-04
    verification:
      - kind: integration
        ref: "pyo3/tests/test_database_merge.py#test_merge_default_no_kwargs_works (exact 110-kmer union, summed shared counts, header accounting)"
        status: pass
    human_judgment: false
  - id: D9
    description: "No regression on either crate: root suite green, .rkdb v2 byte-identical, clippy -D warnings clean on BOTH crates, release build clean, Phase 2 PyCounter tests unaffected"
    requirement: MERGE-04
    verification:
      - kind: other
        ref: "cargo test -> exit 0 (221 lib + 34 golden + 26 merge_cleanup + 26 merge_routing + 23 round_trip + 20 mod + 8 property + 6 dense_differential + 5 cjk + 4 parallel_count + 3 dense_merge_integration + 3 dense_proptest + 3 legacy + 2 golden_sha256 + 2 consistency, 0 failures)"
        status: pass
      - kind: other
        ref: "cargo clippy --all-targets -- -D warnings (root) -> exit 0"
        status: pass
      - kind: other
        ref: "(cd pyo3 && cargo clippy --all-targets -- -D warnings) -> exit 0"
        status: pass
      - kind: other
        ref: "cargo build --release -> exit 0; Cargo.toml untouched, [profile.release] panic = \"abort\" intact"
        status: pass
      - kind: other
        ref: "pytest tests/test_counter.py -> 85 passed (PCOUNT-03 not regressed); whole pyo3 suite 124 passed / 63 pre-existing skips"
        status: pass
      - kind: other
        ref: "rustfmt --check clean on both touched Rust files; `cargo fmt --all --check` drift confined to the two documented pre-existing files"
        status: pass
    human_judgment: false
  - id: D10
    description: "A Python merge's PEAK MEMORY at human-genome scale stays inside its declared max_memory budget"
    verification: []
    human_judgment: true
    rationale: "Not measurable here: this machine and CI have no human-scale dataset, and the estimator's 24-bytes-per-kmer figure is a MODEL (the same caveat 03-03 logged for KmerCounter::memory_usage). What is machine-proven is the routing LOGIC — the budget reaches MergeConfig, the over-budget 'memory' request is refused, and the over-budget 'auto' request takes the streaming path — which is exactly 03-01's 'bounding proof over scale proof' approach. The physical ceiling is Phase 4's benchmark against CRR1936095, and the same open item has been carried by 03-01 D7, 03-03 D8 and 03-04 D8 without being closed by any of them."

# Measured at SUMMARY-write time from the ledger at `.git/gsd-plan-head-before-03-05`
# (written before the first commit). `commits: 2` is the two TASK commits. This
# SUMMARY's own commit plus the STATE/ROADMAP/REQUIREMENTS close-out commit
# follow and cannot appear in this field without changing the value being
# measured, so `git rev-list --count d99bbc1..HEAD` = 4 once both land.
# (03-01/03-02 record `commits: 4` and 03-04 records `commits: 1` for the same
# documented reason.)
commits: 2
plan_head_before: d99bbc1e785b533ba21a5f185864173ca32aa7a0
plan_head_after: c2cd8ab

duration: 35min
completed: 2026-10-07
status: complete
---

# Phase 3 Plan 5: Python-side Bounded Merge Control (MERGE-04) Summary

**`pyrustkmer.PyDatabase.merge` now takes the same memory budget and merge-strategy controls the CLI has always had — `max_memory=` and `merge_mode=`, keyword-only, validated at the Python boundary, parsed by the CLI's own parser — so a Python user's merge inherits the bounded dispatcher by construction instead of by promise.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-10-07T03:46:20Z
- **Completed:** 2026-10-07T04:21:00Z
- **Tasks:** 2
- **Files modified:** 5 (2 source, 1 new test file, 1 planning ledger, plus the WINDOWS ledger)

## Accomplishments

- **`PyDatabase.merge(databases, output, *, max_memory=None, merge_mode="auto")`.** Both kwargs thread into a `MergeConfig` handed to the *same* `RKDatabase::merge_databases` the CLI calls, so the 03-01 header-only estimator, the MERGE-02 hard route to streaming, and the D-02 over-budget reject all apply to Python by inheritance — no dispatch logic was duplicated, and none could drift.
- **Boundary validation that closes a real hole (T-03-15).** `merge_databases` treats an unrecognised `merge_mode` as `"auto"`, so before this plan `merge_mode="streming"` would have silently produced an auto-routed merge. It now raises `ValueError: Invalid merge_mode: streming. Must be one of: auto, memory, streaming` — the same shape as `PyCounter(threads=0)` from 02-03, and the Python analog of clap's `value_parser`.
- **One parser, two surfaces (T-03-16).** `src/cli/commands/merge.rs::parse_memory_size` is now `pub` and is the only definition; the binding calls it. A budget string means the same byte count in the shell and in Python, including the 1KB floor and 1TB ceiling.
- **The D-02 reject, bridged.** `merge_mode="memory"` over budget raises `RuntimeError: Merge operation failed: merge_mode='memory' rejected: estimated memory (2880 bytes for 120 k-mers) exceeds max_memory (1024 bytes); use merge_mode='streaming' (or 'auto') to merge within the memory budget` — the core's own wording, byte counts included.
- **The route is PROVEN from Python, not asserted by label.** `test_streaming_route_is_proven_by_its_chunk_files` points `TMPDIR` at a directory that does not exist: the streaming path cannot create its first `rustkmer_sort_*.chunk` and fails by name, while `test_inmemory_route_never_touches_temp_dir` returns the exact union on the *same* fixture with the *same* bogus `TMPDIR`. The 03-01 probe needed no new API and no log capture to travel to the Python surface — it only needed `MergeConfig::temp_dir`'s existing default of `std::env::temp_dir()`.
- **11 GREEN tests, 4 mutations, 0 skips.** Every mutation of the new wiring is caught by a specific named test (table in Self-Check). The full pyo3 suite is 124 passed / 63 pre-existing skips; `test_counter.py` is 85 passed, so PCOUNT-03 is intact.
- **Full Wave-2 gate still green.** Root `cargo test` exit 0 (golden_tests 34/34 → `.rkdb` v2 byte-identical), `cargo clippy -D warnings` exit 0 on **both** crates, `cargo build --release` exit 0 with `panic = "abort"` untouched, rustfmt clean on both touched files.

## Task Commits

1. **Task 1: Wave-0 scaffold `pyo3/tests/test_database_merge.py`** — `58c51a2` (test)
2. **Task 2: kwargs + MergeConfig threading (GREEN)** — `c2cd8ab` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `pyo3/src/database.rs` (modified) — `#[pyo3(signature = (databases, output, *, max_memory=None, merge_mode="auto".to_string()))]`; `merge_mode` validated against `{auto, memory, streaming}`; `max_memory` parsed via the CLI parser; `MergeConfig` assembled by struct update; docstring extended with the new args, the Raises, and a kwargs example. The empty-list `PyValueError`, the `PyFileNotFoundError` per input, and the two `PyRuntimeError` bridges are unchanged, and the kwargs validate *after* them exactly as the plan specified.
- `pyo3/tests/test_database_merge.py` (new, 11 tests) — MERGE-04 contract: backward-compat smoke, both validation rejects, the D-02 reject with byte-count assertions, the two route-proof tests (parametrized, 4 cases), the over-budget `auto` hard route, cross-route data equality, and a scripted form of the plan's manual `help(...)` signature check.
- `src/cli/commands/merge.rs` (modified) — `parse_memory_size` visibility `fn` → `pub fn` plus a doc comment explaining why the binding reuses it. **No behavioural change to the CLI.**
- `.planning/phases/03-memory-safety/deferred-items.md` (modified) — 2 new entries (below).
- `.planning/WINDOWS.md` (modified) — 2 new open entries, `open_count: 2`.

## Decisions Made

- **Reuse the parser, do not copy it.** The plan offered "reuse `parse_memory_size`, or write `parse_memory_size_py`". Reuse costs one word and permanently prevents the two surfaces from disagreeing about what `"4GB"` means; a copy would drift silently and the drift would surface as a user's budget behaving differently in Python than in the shell — the precise failure MERGE-04 exists to eliminate. The same argument 03-02 used for `MERGE_TEMP_PREFIX`.
- **Both kwargs are keyword-only.** `*` in the pyo3 signature mirrors `PyCounter(threads=...)` from 02-03 and makes the arguments self-documenting at the call site. This narrows accepted call shapes (positional use is now a `TypeError`), but the pre-MERGE-04 signature accepted only two positional args, so no existing caller can regress.
- **Struct-update syntax over field assignment.** The plan's action text spelled out `let mut config = MergeConfig::default(); config.merge_mode = ...`, which the pyo3 crate's own `-D warnings` gate rejects as `clippy::field_reassign_with_default` — and that clippy command is one of the plan's blocking acceptance criteria. The wiring is identical; only the assembly form differs.
- **No new public API for route observation.** `merge` still returns `None`. A `last_strategy_used` field or a strategy-returning variant would be new surface on the public Python class for a test-only need; the `TMPDIR` side-effect discriminator does the job with zero API.
- **The over-budget budget is 1024 *because* it is the parser floor, and the helper asserts the estimate exceeds it.** That assertion is the substance of the test: it turns "someone shrank the fixture" from a silently vacuous routing test into a loud failure. Directly inherited from 03-04's finding that a hard-coded "tiny" budget exceeded its fixture's 960-byte estimate and made the whole composition claim vacuous.
- **Pre-existing pyo3 breakage reported, not fixed** (see Deviations 4 and 5).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's own `MergeConfig` assembly form fails the plan's own clippy gate**
- **Found during:** Task 2, `cargo clippy --all-targets -- -D warnings` on the pyo3 crate.
- **Issue:** `<action>` specifies `let mut config = MergeConfig::default(); config.merge_mode = merge_mode;` and a conditional `config.max_memory_usage = ...`. `clippy::field_reassign_with_default` fires on exactly that shape, and the pyo3 crate denies warnings — so following the plan literally produced `error: field_reassign_with_default` and a red gate.
- **Fix:** Built the config with struct-update syntax: `MergeConfig { max_memory_usage: parsed.unwrap_or(defaults.max_memory_usage), merge_mode, ..defaults }`. Same values, one `MergeConfig::default()` evaluation (which reads `/proc/meminfo`).
- **Files modified:** `pyo3/src/database.rs`
- **Verification:** `(cd pyo3 && cargo clippy --all-targets -- -D warnings)` exit 0.
- **Committed in:** `c2cd8ab`

**2. [Rule 3 - Blocking] `maturin develop --release` — the plan's verify command — cannot run in this repository**
- **Found during:** Task 1, first attempt to build the extension for the RED stubs.
- **Issue:** `pyo3/pyproject.toml` sets `python-source = "."` with `module-name = "pyrustkmer"`, but the mixed-layout package directory `pyo3/pyrustkmer/` has never existed in git history. maturin validates the pairing before building anything: *"python-source is set to `.../pyo3`, but the python module at `.../pyo3/pyrustkmer` does not exist."* Both `maturin develop` and `maturin build` exit 1 — including the `maturin build` step of the CI `pyo3-build` merge gate.
- **Fix (workaround, not a repo change):** built the cdylib directly and installed it by hand — `PYO3_PYTHON=<venv>/bin/python cargo build --release --features extension-module` in `pyo3/`, then `cp target/release/libpyrustkmer.so <venv>/lib/python3.11/site-packages/pyrustkmer.so`. `PYO3_PYTHON` is load-bearing: without it pyo3-build-config binds to the ambient interpreter (3.14 here) and the `.so` fails to import with `undefined symbol: PyUnicode_EqualToUTF8AndSize`.
- **Files modified:** none in the repo (the packaging config is untouched — see below).
- **Verification:** `import pyrustkmer` succeeds under the venv; all 11 tests + 85 counter tests run against the hand-installed extension.
- **Committed in:** n/a (environment workaround)
- **Reported, not fixed:** the underlying packaging-config defect is a pre-existing one-line config change outside MERGE-04, so it is logged in `deferred-items.md` and `.planning/WINDOWS.md` with a suggested fix rather than silently applied.

**3. [Rule 3 - Blocking] No Python interpreter or test runner existed in the environment**
- **Found during:** Task 1, before the first test run.
- **Issue:** `pyrustkmer` was not installed for any interpreter, `maturin` and `ruff` were absent, and the only `pytest` on `PATH` belongs to an unrelated project's venv (`~/Github/HelixIdentify/.venv`). The plan's suite could not run at all.
- **Fix:** created a dedicated venv at `~/.cache/rustkmer-venv` (CPython 3.11, matching CI's `actions/setup-python`) with `uv`, installed `pytest`, `pytest-cov`, `numpy`, `maturin`, `ruff`, and hand-installed the built `.so` (see Deviation 2). Nothing outside `~/.cache` was touched; no repo file or other project's venv was modified.
- **Files modified:** none in the repo.
- **Committed in:** n/a (environment setup)

**4. [Rule 3 - Blocking] The plan's `pytest` acceptance criteria are unsatisfiable as written: `addopts` forces a coverage failure**
- **Found during:** Task 1 baseline run.
- **Issue:** `pyo3/pyproject.toml`'s `addopts` includes `--cov=pyrustkmer ... --cov-fail-under=80`. `pyrustkmer` is a *compiled* extension, so coverage is structurally 0.00% and the gate always trips. Confirmed pre-existing on an untouched file: `pytest tests/test_counter.py` prints "85 passed" and then "FAIL Required test coverage of 80% not reached", exit 1. The same is true of every file in the crate, so the criterion "`pytest tests/test_database_merge.py` exits 0" cannot be met by any implementation.
- **Fix:** ran the suite with `-o addopts=""` (which neutralises the coverage flags and nothing else) and reported the substitution here.
- **Files modified:** none in the repo.
- **Verification:** 11 passed / 124 passed across the suite, exit 0, under `-o addopts=""`.
- **Committed in:** n/a (environment workaround)
- **Reported, not fixed:** changing the crate's pytest configuration would alter the quality bar every later contributor runs under, and is outside MERGE-04. Logged in `deferred-items.md` and `WINDOWS.md` with a suggested fix.

**5. [Rule 1 - Bug] The RED stub's smoke test asserted the wrong header semantics**
- **Found during:** Task 1, first run of the (unskipped) smoke test.
- **Issue:** the stub asserted `stats.total_kmers == 150` (the sum of the fixtures' counts) against a merged database whose header reports 110. `RKDatabase::from_kmer_pairs` writes `total_kmers: entries.len()` — the header counts **records**, not counts. A test that encoded the wrong invariant would have "passed" only if a merge ever stopped summing counts, and it mislabels the real invariant.
- **Fix:** the smoke test now asserts `stats.total_kmers == stats.unique_kmers == 110` (header accounting) **and** `sum(counts.values()) == 150` (count conservation) as two separate invariants, with a comment recording the header semantics so the next reader does not re-derive it.
- **Files modified:** `pyo3/tests/test_database_merge.py`
- **Verification:** `test_merge_default_no_kwargs_works` GREEN; the same two-invariant split is applied to every route arm.
- **Committed in:** `58c51a2` (found and fixed within Task 1) and carried into `c2cd8ab`

**6. [Rule 2 - Missing Critical] Route-observing tests added beyond the plan's five**
- **Found during:** Task 2, while turning the RED stubs GREEN.
- **Issue:** the plan's five tests would all pass while every one of them ran the in-memory path — precisely the vacuity 03-04 shipped and had to retract. `merge_mode='streaming'` succeeding and `max_memory` being honoured are both consistent with the kwargs being ignored *when the estimate happens to fall on the other side of the budget*. Nothing in the plan's set observes which branch ran.
- **Fix:** added 6 tests / 4 parametrized cases that observe the route directly (`test_streaming_route_is_proven_by_its_chunk_files[streaming|auto]` against a nonexistent `TMPDIR`, its control `test_inmemory_route_never_touches_temp_dir[auto|memory]`, `test_over_budget_auto_hard_route_completes`, and `test_merge_signature_exposes_the_cli_kwargs`). No new public API — the observation is a filesystem side effect, and the control arm is what makes the raise attributable to the route rather than to the fixture.
- **Files modified:** `pyo3/tests/test_database_merge.py`
- **Verification:** all 11 GREEN; 2 of the 4 mutations are caught *only* by these added tests (`merge_mode` not threaded → `[streaming]` arm fails; `max_memory` not threaded → `[auto]` arm fails).
- **Committed in:** `c2cd8ab`

---

**Total deviations:** 6 auto-fixed (2 Rule 1 bugs, 3 Rule 3 blocking, 1 Rule 2 missing critical)
**Impact on plan:** Deviation 1 was forced by the plan's own clippy criterion. Deviations 2–4 are environment and pre-existing-repo-configuration problems that blocked the plan's stated verification commands; none was fixed in-repo because each is a config change outside MERGE-04, and all three are now visible in `deferred-items.md` + `WINDOWS.md` with suggested fixes. Deviation 5 corrected a wrong invariant in the plan's own test scaffold. Deviation 6 is the one that matters for trust: without it, this plan could have reported MERGE-04 verified while proving nothing about which merge route Python actually took. No production behaviour was changed beyond the two lines the plan asked for, and no CLI behaviour changed at all.

## Issues Encountered

- **The plan's paths are macOS, this executor is Linux** (`/Users/forrest/GitHub/rustkmer` vs `/home/forrest/Github/rustkmer`). All commands run with the path adapted; no behavioural difference. Same as 03-01 through 03-04.
- **The documented build path for the pyo3 extension is broken** (Deviations 2 and 4). Two independent pre-existing defects had to be worked around to run *any* Python test here: maturin's `python-source` pairing, and the `addopts` coverage gate. Neither is Phase 3's, and neither is caused by Phase 3, but together they mean the Python surface — now carrying 11 contract tests — has no working documented build-and-test path and no CI job. That is worth a small dedicated plan.
- **The 63 skips in the pyo3 suite are pre-existing** and come from other test files (feature-gated and fixture-dependent), not from this plan's file: `test_database_merge.py` reports 11 passed and 0 skipped.
- **Deferred items (a) and (b) from 03-02 were not exercised.** `use_prefix_cache` defaults to `false` and no test here enables it, so the prefix-cache path (`merge_prefix_buckets` silent partial merge, `external_sort_merge_output.tmp` leak) was never entered — both remain open and are still not this plan's to fix. The kwargs do not expose a prefix-cache switch, so MERGE-04 gives Python no way to reach that path at all.
- **Deferred item (c) also not exercised**: no streaming chunk file survived a successful merge in any of the 11 tests, consistent with 03-04's finding that `TempFileManager`'s `Drop` is correct on the normal path. The abort/SIGKILL sweep-coverage gap is unchanged.
- **In-memory merge of two k=21 DBs still gets no dense-width win** — confirmed again here and deliberately not touched: `merge_databases_inmemory`'s accumulator is still `HashMapBrown<u128, u32>`, which is 03-03's logged follow-up, not this plan's scope.
- **`PyDatabase.merge` still holds the GIL.** Pre-existing (the method never released it) and outside this plan's scope — the plan is param-threading, not concurrency. But a Python user merging two large databases blocks every other thread in the process for the duration, where `PyCounter.add_from_fastq` correctly uses `py.detach`. Worth a follow-up, and it is a behavioural change to a public method, so it should not ride along here.

## Known Stubs

None. All 11 tests in `pyo3/tests/test_database_merge.py` are GREEN, 0 skipped, 0 `TODO`/`FIXME`, no placeholder text, no unwired data source. The two `#[ignore]`d tests in the Rust suite are the Phase 1/2 run-once fixture generators, pre-existing and out of scope.

**Open defects recorded in `.planning/WINDOWS.md` (`open_count: 2`)** — both pre-existing, both outside Phase 3, both carried deliberately rather than waived so a human decides at ship time:
1. `maturin build` / `maturin develop` cannot run (`python-source` pairing with a package dir that never existed) — the CI `pyo3-build` job's final step.
2. `pyo3` pytest `addopts` forces a coverage failure on every run, and CI has no pyo3 pytest job.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Phase 03 is complete.** MERGE-01/02/03/04 and DENSE-01/02/03 are all delivered: the bounded merge core (03-01), temp lifecycle (03-02), the dense counter (03-03), the composition gate (03-04), and now CLI-parity control from Python (03-05). `RKDatabase::merge_databases` is still the single admission-control point, and both surfaces reach it.
- **Phase 4's benchmark is the remaining human-judgment item** (coverage D10, carried by 03-01 D7, 03-03 D8, 03-04 D8): the physical memory ceiling at human scale, plus `memory_usage()` being a model rather than a measurement. Nothing in CI can substitute, and this plan's tests prove the *routing*, not the *ceiling*.
- **For downstream planners:** the pyo3 extension must be built with `PYO3_PYTHON` set (Deviation 2) and the test suite run with `-o addopts=""` (Deviation 4). Both are pre-existing and both are one-line config fixes that a dedicated plan should land before the next phase adds Python-side tests.
- **Open defects carried forward unchanged:** `merge_prefix_buckets` silent partial merge; `external_sort_merge_output.tmp` outside the subdir and never deleted; loose `rustkmer_sort_*.chunk` files not covered by the orphan sweep; dense `u64` not applied to the in-memory merge accumulator or the `RKDatabase` read path; `memory_usage()` modelled not measured; `cargo fmt --all --check` drift in `src/cli/commands/count.rs` + `tests/parallel_count_tests.rs`; `maturin` packaging; pyo3 pytest `addopts`; no pyo3 CI job. Plus one new observation from this plan: `PyDatabase.merge` holds the GIL.
- **Note on `merge_mode` reach:** the kwargs expose `{auto, memory, streaming}`, matching the CLI's `value_parser` exactly. The prefix-cache strategy (`--use-prefix-cache`) has no Python equivalent and still cannot be reached from Python.

---

## Self-Check: PASSED

- **Files verified on disk:** `pyo3/tests/test_database_merge.py`, `pyo3/src/database.rs`, `src/cli/commands/merge.rs`, `deferred-items.md`, `.planning/WINDOWS.md`, this SUMMARY ✓
- **Commits verified present in history:** `58c51a2` (task 1), `c2cd8ab` (task 2) ✓
- **`commits: 2` is MEASURED** via `git rev-list --count d99bbc1..HEAD` (ledger at `.git/gsd-plan-head-before-03-05`, written before the first commit) = **2** at SUMMARY-write time: the two task commits. This SUMMARY's commit and the STATE/ROADMAP close-out follow and cannot appear without changing the measured value — matching the convention documented in 03-01/03-02/03-04.
- **Task 1 acceptance criteria re-run:**

  | Criterion | Result |
  |---|---|
  | `pyo3/tests/test_database_merge.py` exists, `python -m py_compile` exit 0 | PASS |
  | `pytest --collect-only` collects >= 5 tests (1 smoke + 4 skipped RED) | PASS — exactly 5 collected at commit time |
  | Import guard (`try: import pyrustkmer` / `pytest.skip(..., allow_module_level=True)`) present | PASS |
  | >= 4 tests carry `@pytest.mark.skip(reason="TODO(03-05 Task 2)...")` | PASS — 4 |
  | `test_merge_default_no_kwargs_works` NOT skipped | PASS — GREEN in Task 1 |
  | Validation tests use `pytest.raises(ValueError, match=...)` | PASS |
  | Configured linter clean | PASS — `ruff check tests/test_database_merge.py` → "All checks passed!" (the repo's own pre-commit Python hooks are scoped to `python/`, not `pyo3/`) |

- **Task 2 acceptance criteria re-run:**

  | Criterion | Result |
  |---|---|
  | `pyo3(signature)` line contains both `max_memory` and `merge_mode` | PASS — `database.rs:1367` |
  | `Invalid merge_mode` literal present | PASS — `database.rs:1401` |
  | Wheel builds with the new signature | **PASS with a substituted command** — `maturin develop --release` cannot run (Deviation 2, pre-existing packaging config). `PYO3_PYTHON=... cargo build --release --features extension-module` exit 0 and the module imports. |
  | `pytest tests/test_database_merge.py` exit 0, all tests GREEN, none skipped | PASS with a substituted invocation (`-o addopts=""`, Deviation 4) — **11 passed, 0 skipped** (9 functions, 2 parametrized × 2) |
  | `pytest tests/test_counter.py` exit 0 (PCOUNT-03 not regressed) | PASS — 85 passed |
  | `cargo clippy --all-targets -- -D warnings` on pyo3 | PASS — exit 0 (after Deviation 1) |
  | `help(pyrustkmer.PyDatabase.merge)` shows both kwargs | PASS — scripted: `__text_signature__ == '(databases, output, *, max_memory=None, merge_mode=...)'` |
  | D-02 reject observable from Python with "memory" in the message | PASS — `test_over_budget_memory_mode_is_rejected` asserts `rejected`, `streaming`, `2880 bytes`, `1024 bytes` |

- **Non-vacuity verified by 4 mutations, all reverted** (`git diff` against the pre-mutation backup confirmed byte-identical restore before the commit):

  | Injected defect | Caught by |
  |---|---|
  | `config.max_memory_usage` assignment deleted | `test_over_budget_memory_mode_is_rejected` + `test_streaming_route_is_proven_by_its_chunk_files[auto]` |
  | `config.merge_mode` assignment deleted | `test_over_budget_memory_mode_is_rejected` + `test_streaming_route_is_proven_by_its_chunk_files[streaming]` |
  | `merge_mode` validation neutered | `test_merge_rejects_bad_merge_mode` ("DID NOT RAISE ValueError") |
  | `max_memory` parse error swallowed (`unwrap_or`) | `test_merge_rejects_bad_max_memory` |

- **Full Wave-2 gate:** `cargo test` exit 0 — 221 lib + 34 golden + 26 merge_cleanup + 26 merge_routing + 23 round_trip + 20 mod + 8 property + 6 dense_differential + 5 cjk + 4 parallel_count + 3 dense_merge_integration + 3 dense_proptest + 3 legacy + 2 golden_sha256 + 2 consistency, **0 failures** ✓ · `cargo clippy -D warnings` (root) exit 0 ✓ · `cargo clippy -D warnings` (pyo3) exit 0 ✓ · `cargo build --release` exit 0, `Cargo.toml` untouched, `panic = "abort"` intact ✓
- **`.rkdb` v2 byte-identity preserved:** `golden_tests` 34/34 and `golden_sha256_tests` 2/2 over all 12 fixtures, unchanged by this plan (it writes no `.rkdb` layout and the merge output path is unchanged) ✓
- **rustfmt:** both touched Rust files clean under `rustfmt --edition 2021 --check`; `cargo fmt --all --check` drift is confined to the two documented pre-existing files (`src/cli/commands/count.rs`, `tests/parallel_count_tests.rs`) ✓
- **Ship gate surfaced, not hidden:** `.planning/WINDOWS.md` `open_count: 2`, both pre-existing pyo3 config defects, recorded with suggested fixes rather than waived by the executor ✓

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*
