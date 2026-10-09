---
phase: 04-benchmark-validation
plan: 01
subsystem: testing
tags: [benchmark, python-stdlib, wall-clock, peak-rss, usr-bin-time, regression-harness]

requires:
  - phase: 03-benchmark-validation-prep
    provides: release binary with count/merge/stats CLI and hardened .rkdb v2 readers
provides:
  - scripts/bench/bench.py — measurement core (parse_time_output, measure, count/merge builders, stats, fingerprint, validate_schema, resolve_mode)
  - scripts/bench/gen_synthetic.py — seeded deterministic FASTQ generator CLI
  - scripts/bench/make_slice.sh — deterministic gunzip -c | head slice tool
  - scripts/bench/tests/ — 43 stdlib-unittest tests + dual-platform time fixtures
  - results.json schema version 1 (consumed by 04-03 compare.py and 04-04 report)
affects: [04-02 multi-rep protocol, 04-03 comparator + CI gate, 04-04 milestone run]

actuals:
  tokens: 20900   # chars/4 over the realized diff (83,601 chars) — plan estimated 40,000
  tasks: 3
  commits: 4      # MEASURED: git rev-list --count be0a2da..HEAD

plan_head_before: be0a2da1807ab84dfac2a0deb952b4f88dec05ad
plan_head_after: 395c945

tech-stack:
  added: []   # stdlib-only hard constraint — nothing installed (T-04-SC vacuously clean)
  patterns:
    - "OS rusage accounting via /usr/bin/time -l|-v with a dual-format parser normalized to bytes"
    - "Versioned results.json schema as the single contract shared by harness, comparator, and report"
    - "Pure-function mode resolution (explicit > env > size ladder) with the decision recorded in results.json"

key-files:
  created:
    - scripts/bench/bench.py
    - scripts/bench/gen_synthetic.py
    - scripts/bench/make_slice.sh
    - scripts/bench/tests/test_time_parser.py
    - scripts/bench/tests/test_generator.py
    - scripts/bench/tests/test_schema.py
    - scripts/bench/tests/test_degradation.py
    - scripts/bench/tests/fixtures/time_l_macos.txt
    - scripts/bench/tests/fixtures/time_v_linux.txt
  modified:
    - .gitignore
  deleted:
    - src/cli/commands/benchmark.rs
    - .github/workflows/performance-regression.yml

key-decisions:
  - "Count inputs go through -i (num_args 1..) and FASTQ headers carry '@' — the plan's command-builder sketch failed clap validation and the bio FASTQ reader; two Rule 1 fixes against args.rs ground truth"
  - "Slice extraction in bench.py streams gunzip -c output through pure-subprocess list form (no sh -c) — removes the command-injection surface T-04/V5 flagged instead of validating metacharacters"
  - "Mode precedence is --mode > RUSTKMER_BENCH_MODE > size ladder (default threshold 1 GiB, injectable); a single resolved input is measured twice (honest repetition) rather than fabricating a second input"
  - "Exact-count self-check (reads x (L-k+1)) is scoped to synthetic mode; merge count-conservation and distinct-union assertions run in every mode"
  - "Blanket .gitignore *.txt rule silently excluded the time fixtures; negation entries added (repo has precedent at tests/fixtures/golden_*.rkdb)"

patterns-established:
  - "Every measured run asserts unique_kmers > 0 before its numbers are trusted (silent zero-count trap, Pitfall 1)"
  - "Both per-rep metrics (wall_s AND peak_rss_bytes) mandatory in schema v1 — enforced by validate_schema, the same function 04-03 imports"
  - "Deterministic provisioning: seeded generator (byte-identical output) and first-4N-lines slice (byte-identical everywhere)"

requirements-completed: [BENCH-01, BENCH-03, BENCH-04]

coverage:
  - id: D1
    description: "Harness measures rustkmer count (x2 arms) and merge wall-clock + peak RSS through the release binary with sanity and exact-count self-check assertions"
    requirement: BENCH-01
    verification:
      - kind: integration
        ref: "python3 scripts/bench/bench.py --mode synthetic --reads 50000 --self-check — exits 0, arms count-A/count-B/merge all carry wall_s>0 and peak_rss_bytes>0"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_schema.py#test_real_self_check_results_pass_validation"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dual-platform /usr/bin/time parser: macOS bytes as-is, Linux kbytes x1024, both elapsed shapes, ValueError on malformed/missing lines"
    requirement: BENCH-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_time_parser.py — fixture-driven, Linux peak asserted == 62384*1024 exactly"
        status: pass
    human_judgment: false
  - id: D3
    description: "results.json schema v1 with mandatory per-rep wall_s AND peak_rss_bytes, validated by a shared validate_schema"
    requirement: BENCH-03
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_schema.py — real self-check output passes; missing field/schema_version/empty-arms all raise"
        status: pass
    human_judgment: false
  - id: D4
    description: "Deterministic seeded synthetic FASTQ generator (same seed -> identical sha256; --reads 0 rejected)"
    requirement: BENCH-04
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_generator.py — determinism, seed sensitivity, 2000-line shape, rejection"
        status: pass
    human_judgment: false
  - id: D5
    description: "Degradation ladder: explicit --mode / RUSTKMER_BENCH_MODE overrides, size threshold full/slice boundary, missing -> synthetic, sorted dir/glob scans, no mutation during resolution"
    requirement: BENCH-04
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_degradation.py#TestResolverLadder — 15 resolver rows"
        status: pass
      - kind: integration
        ref: "slice-mode smoke: bench.py --mode slice --input <gz> --slice-reads 1000 --self-check exits 0, 120000/120000/240000 exact, mode+resolved_inputs recorded"
        status: pass
    human_judgment: false
  - id: D6
    description: "Deterministic standalone slice tool make_slice.sh (gunzip -c | head, never zcat)"
    requirement: BENCH-04
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_degradation.py#TestMakeSliceDeterminism — byte-identity across invocations, exact first-4N lines, argument rejection"
        status: pass
    human_judgment: false
  - id: D7
    description: "Dead perf infrastructure deleted (benchmark.rs, performance-regression.yml) with zero dangling references and Rust gates green"
    requirement: BENCH-01
    verification:
      - kind: other
        ref: "test ! -f src/cli/commands/benchmark.rs && test ! -f .github/workflows/performance-regression.yml && cargo clippy --all-targets -- -D warnings && cargo test — all exit 0"
        status: pass
    human_judgment: false

duration: 15 min
completed: 2026-10-09
status: complete
---

# Phase 04 Plan 01: Benchmark Harness Core Summary

**Stdlib-only Python harness measuring rustkmer count+merge wall-clock and peak RSS under /usr/bin/time (dual-platform parser, schema-versioned results.json, deterministic synthetic generator, full/slice/synthetic degradation ladder) with the dead perf infrastructure deleted.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-10-09T14:17:31Z
- **Completed:** 2026-10-09T14:32:55Z
- **Tasks:** 3/3
- **Files modified:** 15 (12 created/modified, 2 deleted, .gitignore)

## Accomplishments

- Measurement core at `scripts/bench/bench.py`: every headline number comes from the release binary under `/usr/bin/time -l|-v` (OS rusage), with `unique_kmers > 0` asserted after every arm (Pitfall 1) and `--self-check` exact-count assertions (6,000,000 = 50,000 x 120 at k=31; merge conserves 12,000,000 = 6M+6M).
- Dual-platform time parser pinned by unit tests on a real captured macOS fixture and the documented GNU `-v` block: bytes as-is vs kbytes x1024 (the 1024x units trap asserted as exact equality `62384 * 1024`); malformed/missing output raises, never best-effort (threat T-04-01).
- results.json schema v1 — every rep carries BOTH `wall_s` and `peak_rss_bytes` (BENCH-03), enforced by `validate_schema` which 04-03's comparator will import as the single source of truth.
- BENCH-04 ladder shipped and tested: explicit `--mode` > `RUSTKMER_BENCH_MODE` > size threshold (1 GiB default, injectable); missing input -> synthetic; directory/glob scans sorted; mode, resolved inputs, and sha256+size fingerprints all recorded in results.json. Slice extraction is `gunzip -c` first-4N-lines — byte-identical everywhere, never macOS zcat.
- Dead perf infrastructure deleted after schema mining: `src/cli/commands/benchmark.rs` (unregistered, cargo-subprocess anti-pattern, `memory_usage_mb: None // TODO`) and `.github/workflows/performance-regression.yml` (branches `main`/`develop` that don't exist, scripts that don't exist). Clippy `-D warnings` and `cargo test` green with zero reference fixes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer — synthetic FASTQ through timed count + merge to results.json** - `7e37c99` (feat)
2. **Task 2: Unit tests — dual-platform time parser fixtures, generator determinism, schema validation** - `8685e9e` (test; amended once to include the two fixture files a blanket `*.txt` gitignore rule had silently dropped)
3. **Task 3: Degradation ladder + deterministic slice script + dead-infrastructure deletion** - `28411ad` (feat)
4. Executable-bit follow-up - `395c945` (chore: gen_synthetic.py mode change)

**Plan metadata:** committed after this SUMMARY (docs)

## Files Created/Modified

- `scripts/bench/bench.py` - harness core: parser, measure, builders, stats, fingerprint, validate_schema, resolve_mode, extract_slice, CLI (--mode/--input/--out/--self-check/--k/--threads/--reads/--reps/--rustkmer/--slice-reads)
- `scripts/bench/gen_synthetic.py` - seeded deterministic FASTQ generator (--reads/--length/--seed/--out)
- `scripts/bench/make_slice.sh` - standalone deterministic slice tool (INPUT N_READS OUTPUT)
- `scripts/bench/tests/test_time_parser.py` - dual-platform parser fixtures + rejection cases
- `scripts/bench/tests/test_generator.py` - determinism, seed sensitivity, record shape, rejection
- `scripts/bench/tests/test_schema.py` - real self-check output + negative schema cases
- `scripts/bench/tests/test_degradation.py` - 15-row resolver table + make_slice determinism
- `scripts/bench/tests/fixtures/time_l_macos.txt` - real `/usr/bin/time -l` capture (sleep 0.1 workload)
- `scripts/bench/tests/fixtures/time_v_linux.txt` - documented GNU `time -v` block
- `scripts/{,bench/,bench/tests/}__init__.py` - packages so `python3 -m unittest scripts.bench.tests.<mod>` resolves
- `.gitignore` - `scripts/bench/scratch/` + fixture negations
- DELETED `src/cli/commands/benchmark.rs`, `.github/workflows/performance-regression.yml`

## Decisions Made

See key-decisions in frontmatter. Notably: the plan's count-builder sketch (inputs positional) and the FASTQ header spec (no '@') were both corrected against `src/cli/args.rs` and the bio reader ground truth before commit; bench.py avoids `sh -c` entirely for slice extraction so env-provided paths have no injection surface.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Count command builder omitted the `-i` flag**
- **Found during:** Task 1 (first self-check run)
- **Issue:** Plan/research sketch built `count -k .. -C --threads .. -o .. *inputs` (positional); clap rejects it — `input` is `-i` with `num_args = 1..` (args.rs:25-26). rc=2 usage error.
- **Fix:** `build_count_cmd` now passes `-i` before the input list.
- **Files modified:** scripts/bench/bench.py
- **Verification:** self-check green end-to-end (6M distinct/total per input)
- **Committed in:** 7e37c99

**2. [Rule 1 - Bug] Synthetic FASTQ headers lacked the '@' prefix**
- **Found during:** Task 1 (second self-check run)
- **Issue:** Plan said "sequential headers (R0000001...)" without '@'; rustkmer's FASTQ reader rejects: `expected '@' at record start`.
- **Fix:** Generator writes `@R0000001`.
- **Files modified:** scripts/bench/gen_synthetic.py
- **Verification:** self-check green; Task 2 header-shape tests pass
- **Committed in:** 7e37c99

**3. [Rule 1 - Bug] Test sliced the wrong line for the plus-line assertion**
- **Found during:** Task 2 (first test run — the tdd task's genuine RED)
- **Issue:** `lines[1::4]` is the sequence line, not the plus line (record lines are 0=header, 1=seq, 2=+, 3=quality).
- **Fix:** `lines[2::4]`.
- **Files modified:** scripts/bench/tests/test_generator.py
- **Verification:** all 24 tests OK
- **Committed in:** 8685e9e

**4. [Rule 3 - Blocker] Blanket `.gitignore` `*.txt` rule silently dropped the test fixtures from the Task 2 commit**
- **Found during:** Task 2 commit
- **Issue:** `git add` warned "paths ignored"; the commit landed without the fixtures the tests depend on — a fresh clone could not run the suite.
- **Fix:** Added `!scripts/bench/tests/fixtures/time_l_macos.txt` / `time_v_linux.txt` negations (existing repo precedent: golden `*.rkdb` negations), staged the fixtures, amended the Task 2 commit.
- **Files modified:** .gitignore
- **Verification:** amended commit shows all 7 files; `git check-ignore` no longer matches
- **Committed in:** 8685e9e (amended)

---

**Total deviations:** 4 auto-fixed (3 x Rule 1, 1 x Rule 3)
**Impact on plan:** All fixes were forced by ground truth (clap args, FASTQ format, gitignore) and landed inside the tasks' own commits. No scope creep; the schema contract (the plan's costly-reversibility surface) shipped exactly as specified.

## Issues Encountered

None beyond the deviations above. The tracer feedback gate re-ran the full verify end-to-end post-commit and passed (auto mode).

## User Setup Required

None - no external service configuration required. (Dev-host prerequisites for later plans: jellyfish 2.3.1 already verified installed; the CRR2044018 substitute dataset decision applies to 04-04 only.)

## Next Phase Readiness

- Ready for 04-02 (multi-rep protocol/interleaving), which refactors the command builders into a shared BenchmarkConfig as planned.
- `validate_schema`, `parse_time_output`, `resolve_mode`, and `fingerprint` are importable and unit-pinned for 04-03's compare.py and the CI gate.
- 43 harness tests + full Rust suite green; `scripts/bench/scratch/` is gitignored.
- Known flagged assumption carried forward (plan-level): synthetic-mode CI representativeness — full-dataset evidence arrives with 04-04.

## Self-Check: PASSED

All key-files created exist on disk; all 4 task commits are ancestors of HEAD; ledger-measured commit count is 4 (base be0a2da -> HEAD 395c945).

---
*Phase: 04-benchmark-validation*
*Completed: 2026-10-09*
