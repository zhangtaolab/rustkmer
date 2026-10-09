---
phase: 04-benchmark-validation
plan: 02
subsystem: testing
tags: [benchmark, jellyfish, parity-gate, fairness-matrix, command-injection, cold-cache, protocol, python-stdlib]

requires:
  - phase: 04-benchmark-validation
    provides: bench.py measurement core (measure, stats, provisioning ladder, validate_schema) from 04-01
provides:
  - bench.py BENCH-02 surface — BenchmarkConfig, rustkmer_count_cmd/jellyfish_count_cmd (golden-tested matched argv), validate_path (T-04-03), parse_jellyfish_stats, run_parity/--parity-only gate, run_comparison_protocol (warmup + counterbalanced rounds + cooldown + honest cache_state + median/CV), check_disk_floor (exit 3)
  - scripts/bench/tests/test_cmd_matrix.py — 26 unit tests (golden argv pairs, hostile-path rejection, protocol primitives)
  - results.json comparison-mode shape — per-rep cache_state/round/arm_order, arm median_wall_s/median_peak_rss_bytes/cv_wall_pct/cv_warning, params hash_size/decompressor/reps/cooldown_s/round_schedule
affects: [04-03 comparator + CI gate (schema unchanged, v1), 04-04 milestone run (consumes the protocol + parity gate)]

actuals:
  tokens: 11121   # chars/4 over the realized diff (44,484 chars) — plan estimated 30,000
  tasks: 2
  commits: 4      # MEASURED: git rev-list --count 4b18be4..HEAD

plan_head_before: 4b18be45d4f6de82f7c3e624cbbe1d835a515be6
plan_head_after: 001b95ad72da70ec2e24f6e8b8f704c16ca78d33

tech-stack:
  added: []   # stdlib-only hard constraint maintained (T-04-SC vacuously clean)
  patterns:
    - "Fairness matrix as code: one frozen BenchmarkConfig dataclass derives both tools' argv so settings cannot drift between arms"
    - "Shell-string containment: exactly one sh -c site in the harness, fed only by validate_path-screened paths and regex-validated harness constants"
    - "Honest measurement labels: cache_state derived from the actual purge-subprocess outcome / CI marker, never from configuration intent"
    - "Counterbalanced interleaving with per-rep round + arm_order labels so order is data, not narrative"

key-files:
  created:
    - scripts/bench/tests/test_cmd_matrix.py
  modified:
    - scripts/bench/bench.py

key-decisions:
  - "Comparison protocol engages at --reps >= 2 (jellyfish arms join the run and require_jellyfish exits 2 when absent); the CI reps=1 synthetic path never needs jellyfish — satisfying the must_have by construction rather than by a separate flag"
  - "The plan's builder sketch omitted -i; kept -i per src/cli/args.rs ground truth (repeat of 04-01's Rule 1 finding) — the golden argv encode the clap-valid form"
  - "hash_size and decompressor join paths in the T-04-03 screen (only ^\\d+[KMG]?$ and a conservative decompressor allowlist pass): both cross into the sh -c string from CLI args, so screening paths alone would leave the pipe open"
  - "Every comparison run asserts count parity on the measured input itself (stats are already computed; a timing comparison between tools that counted different things is meaningless)"
  - "run_parity refactored onto the shared BenchmarkConfig builders and build_count_cmd deleted — one source of truth for both the gate and the protocol"

patterns-established:
  - "Golden-argv tests pin cross-tool flag mirroring (-k == -m, -C mirrored, identical thread literals) instead of trusting two builders to stay in sync"
  - "Hostile-filename unit suites (spaces, $(), backticks, ;|&, quotes, glob, newline) prove the injection rejection before any shell string exists"
  - "Exit-code vocabulary of the harness: 0 ok, 1 parity mismatch/methodology finding, 2 jellyfish required but absent, 3 disk guardrail"

requirements-completed: []   # BENCH-02 is declared by 04-02 AND 04-04; the shared-ID gate holds it incomplete until 04-04's SUMMARY exists (requirements.ready-ids returned 0/1 ready)

coverage:
  - id: D1
    description: "Parity gate: both tools count the same input end-to-end; Distinct==unique_kmers AND Total==total_kmers AND Distinct>0 exits 0 with PARITY OK; mismatch exits 1 as a methodology finding; jellyfish absent exits 2"
    requirement: BENCH-02
    verification:
      - kind: integration
        ref: "python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only — exit 0, 'PARITY OK distinct=2400000 total=2400000' (2.4M = 20000 x (150-31+1))"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_cmd_matrix.py#TestParseJellyfishStats — extraction + missing-Distinct/Total/empty rejection"
        status: pass
      - kind: other
        ref: "env -i PATH= <python3> bench.py --parity-only — exit 2 with explicit message, no traceback"
        status: pass
    human_judgment: false
  - id: D2
    description: "Matched BenchmarkConfig command matrix: one config derives both tools' argv with k/-C/threads mirrored, gz reaching jellyfish only via the decompressor pipe with /dev/stdin, plain inputs as direct path arguments; validate_path rejects hostile filenames before any shell string is assembled (T-04-03)"
    requirement: BENCH-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_cmd_matrix.py#TestGoldenArgvPairs + #TestValidatePath — 26 tests, golden argv pairs, mirror flags, 16 hostile paths, hostile hash_size/output refusal, builder determinism"
        status: pass
    human_judgment: false
  - id: D3
    description: "Interleaved counterbalanced protocol: warmup-per-tool discarded, rustkmer-first-even/jellyfish-first-odd rounds, cooldown gaps, per-rep cache_state from the actual purge outcome, round+arm_order labels, median/CV reduction with cv_warning, parity asserted on the measured input"
    requirement: BENCH-02
    verification:
      - kind: integration
        ref: "bench.py --mode synthetic --reads 20000 --reps 2 — PROTO-OK: both tools' arms, 2 reps each with cache_state='unavailable' (sudo -n purge failed honestly), round/arm_order labels showing jellyfish at order 3 in round 0 and order 0 in round 1, medians + CV in every arm"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_cmd_matrix.py#TestProtocolPrimitives — round_schedule, cache_state truth table, reduce_arm median/CV/warning/single-rep-null"
        status: pass
    human_judgment: false
  - id: D4
    description: "Disk guardrail: mode=full aborts with exit 3 before any measurement when free space on the output volume is below --disk-floor-gb (default 150), naming free and required bytes"
    requirement: BENCH-02
    verification:
      - kind: other
        ref: "bench.py --mode full --disk-floor-gb 9999999 — exit 3, message names 1,610,547,990,528 bytes free vs 10,737,417,166,258,176 required"
        status: pass
    human_judgment: false

duration: 16 min
completed: 2026-10-09
status: complete
---

# Phase 04 Plan 02: Fair-Comparison Methodology Summary

**Parity gate + matched BenchmarkConfig command matrix (golden-tested, injection-screened) + interleaved counterbalanced cold-cache protocol with honest cache_state recording and a disk guardrail, all against Jellyfish2 2.3.1.**

## Performance

- **Duration:** 16 min (14:43:30Z → 14:59:13Z)
- **Started:** 2026-10-09T14:43:30Z
- **Completed:** 2026-10-09T14:59:13Z
- **Tasks:** 2/2 (tracer + TDD task)
- **Files modified:** 2 (bench.py, test_cmd_matrix.py)

## Accomplishments

- **Parity gate before timing (BENCH-02 correctness leg):** `--parity-only` provisions one input via the BENCH-04 ladder, counts it with both tools, and asserts jellyfish Distinct == rustkmer unique_kmers AND Total == total_kmers AND Distinct > 0. Verified end-to-end at smoke scale (2,400,000/2,400,000 at k=31 canonical). A mismatch exits 1 naming both tools' numbers plus the Pitfall-10 N-handling caveat — a methodology finding, never a silent pass. `parse_jellyfish_stats` is a pure function pinned to the verbatim 2.3.1 output shape; text missing either line raises.
- **Fairness encoded in one config (BENCH-02):** a frozen `BenchmarkConfig` dataclass (k, canonical, threads, hash_size=10G generous default, inputs, decompressor) derives both command lines, so the two arms cannot drift. Golden-argv unit tests pin k mirroring `-k`/`-m`, `-C` in both, identical thread literals, gz input reaching jellyfish ONLY through the `gzcat|jellyfish … /dev/stdin` pipe (decompression inside jellyfish's measured wall-clock, mirroring rustkmer's native gz reading), and plain inputs as direct path arguments.
- **T-04-03 injection rejection:** the jellyfish gz arm is the single `sh -c` site in the harness; `validate_path` (letters/digits/dot/slash/underscore/hyphen allowlist) screens every path before the string is assembled, and `hash_size`/`decompressor` are regex-screened too (both cross into the string from CLI args). Unit-proven with 16 hostile filenames plus hostile hash sizes and output paths.
- **Interleaved protocol (BENCH-02):** `--reps >= 2` runs one discarded warmup per tool, counterbalanced rounds (rustkmer first in even rounds, jellyfish first in odd), `--cooldown-s` (default 5) gaps, never both tools concurrent, per-rep `cache_state` recorded from the actual `sudo -n purge` outcome (`purged`/`unavailable`) or the `GITHUB_ACTIONS` marker (`runner-fresh`) — T-04-04's "never configuration intent" is the tested truth table. Medians + CV% via `statistics.median`/`stdev`; CV > 10 sets `cv_warning` without failing. The 2-rep smoke run recorded jellyfish at arm_order 3 in round 0 and 0 in round 1 — counterbalancing visible in the data.
- **Disk guardrail (Pitfall 8):** `os.statvfs` on the output directory before any mode=full measurement; free bytes below `--disk-floor-gb` (default 150) aborts with exit 3 naming both byte counts. Spot-checked with an absurd floor (exit 3 observed).

## Task Commits

Each task was committed atomically (Task 2 followed the full TDD cycle):

1. **Task 1 (tracer): Parity gate end-to-end** - `fd38b9e` (feat)
2. **Task 2 RED: failing test_cmd_matrix** - `22b62a3` (test; 26 tests, 22 assertion failures, 0 errors — classifier verdict `RED_EVIDENCE_OK`, record at scripts/bench/scratch/tdd-red-04-02.json)
3. **Task 2 GREEN: BenchmarkConfig matrix + protocol + guardrail** - `af61657` (feat)
4. **Task 2 REFACTOR: module docstring names the BENCH-02 surface** - `001b95a` (refactor, docs-only)

**Plan metadata:** committed after this SUMMARY (docs)

## Files Created/Modified

- `scripts/bench/bench.py` — added: BenchmarkConfig, default_decompressor, validate_path, rustkmer_count_cmd, jellyfish_count_cmd, parse_jellyfish_stats, require_jellyfish, jellyfish_stats, run_parity/run_parity_cli, round_schedule, cache_state_from/attempt_cache_purge, reduce_arm, check_disk_floor, run_comparison_protocol; CLI --parity-only/--hash-size/--cooldown-s/--disk-floor-gb; build_count_cmd deleted; run_parity refactored onto the shared builders; self-check now resolves arms by name and comparison runs assert parity on the measured input
- `scripts/bench/tests/test_cmd_matrix.py` — 26 stdlib-unittest tests: golden argv pairs (gz pipe + plain direct-args), mirror-flag assertions, 16 hostile-path rejections, hostile hash_size/output refusal, builder determinism, parse_jellyfish_stats extraction/rejection, round_schedule/cache_state truth table/reduce_arm

## Decisions Made

See key-decisions in frontmatter. The load-bearing ones: comparison == `--reps >= 2` (CI's reps=1 path never needs jellyfish); `-i` retained against args.rs ground truth where the plan sketch omitted it; hash_size/decompressor added to the injection screen; parity asserted on every measured comparison run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's rustkmer_count_cmd sketch omitted the -i flag**
- **Found during:** Task 2 design (before writing the golden tests)
- **Issue:** Plan action specifies `[rustkmer, count, -k, str(k), -C, --threads, str(t), -o, out, *inputs]` — positional inputs. clap rejects this: `input` is `-i` with `num_args = 1..` (args.rs:25-26). Identical to 04-01's Task 1 finding.
- **Fix:** Builder emits `…, "-o", out, "-i", *inputs`; the golden argv encode the clap-valid form.
- **Files modified:** scripts/bench/bench.py
- **Verification:** real comparison run (PROTO) invoked the built command 6 times without a usage error; golden tests pin the shape.
- **Committed in:** af61657

**2. [Rule 2 - Missing critical functionality] hash_size and decompressor were unscreened inputs to the sh -c string**
- **Found during:** Task 2 design
- **Issue:** The plan screens paths (T-04-03) but `--hash-size` arrives from the CLI and lands verbatim inside the single sh -c pipeline (`-s {hash_size}`) — `--hash-size '10G; touch /tmp/pwned'` would execute. The threat register's own mitigation says the string is "built solely from validated absolute paths and harness constants"; a CLI-sourced value is not a harness constant until validated.
- **Fix:** `HASH_SIZE_RE = ^\d+[KMG]?$` and a conservative decompressor allowlist gate jellyfish_count_cmd; violations raise ValueError naming the value. Unit-proven with 5 hostile hash sizes; argparse also validates --hash-size early.
- **Files modified:** scripts/bench/bench.py, scripts/bench/tests/test_cmd_matrix.py
- **Verification:** test_jellyfish_cmd_refuses_hostile_hash_size passes.
- **Committed in:** af61657

**3. [Rule 1 - Bug] Two RED test fixtures were wrong, not the implementation**
- **Found during:** Task 2 GREEN (first run after implementation)
- **Issue:** (a) `test_reduce_arm_medians_and_cv` used walls [1.0, 2.0, 3.0] — 50% CV — while asserting `cv_warning` false; the spec says warn above 10, so the fixture contradicted itself. (b) `test_rejects_hostile_filenames` required the newline-bearing hostile path to appear literally in the message, but the message carries the repr (the safe rendering for hostile input).
- **Fix:** (a) walls [1.0, 1.02, 0.98] (2% CV) with expected_cv still computed from `statistics`; (b) accept raw-or-repr naming, documented in the test docstring.
- **Files modified:** scripts/bench/tests/test_cmd_matrix.py
- **Verification:** 26/26 module tests, 69/69 full suite.
- **Committed in:** af61657

---

**Total deviations:** 3 auto-fixed (2 x Rule 1, 1 x Rule 2)
**Impact on plan:** All three were forced by ground truth (clap args, the threat model's own containment rule, arithmetic). No scope creep; the schema contract and protocol shape shipped exactly as specified.

## Issues Encountered

None beyond the deviations. Observation worth carrying to 04-04: with the mandated generous default `-s 10G`, jellyfish commits ~85 GiB RSS even on a 20k-read smoke input (it touches the whole initial hash) and takes ~10.7 s vs rustkmer's 0.45 s — smoke-scale comparisons should pass `--hash-size 1G` (as `--parity-only` does); full-scale milestone runs keep the 10G fairness default. Both numbers came from the same PROTO run that verified the protocol.

## User Setup Required

None - no external service configuration required. (Dev-host prerequisite jellyfish 2.3.1 verified on PATH before Task 1; the CRR2044018 substitute-dataset decision still belongs to 04-04.)

## Next Phase Readiness

- Ready for 04-03 (comparator + CI gate): schema_version stays 1, `validate_schema` unchanged and still the single source of truth; CI's reps=1 synthetic path is untouched rustkmer-only and never needs jellyfish.
- Ready for 04-04 (milestone run): the protocol, parity gate, and disk guardrail it consumes are in place; run the slice-scale parity gate on the real data before the full run (Pitfall 10), keep `--hash-size 10G` for the headline, and expect cache_state='unavailable' unless sudo -n purge succeeds.
- Flagged-assumption status (plan frontmatter): both prohibitions verified mechanically — (1) -s 10G generous default recorded in results.json params and decompression inside jellyfish's measured pipeline (golden-tested); (2) cold-cache claims have a recorded basis only (cache_state per rep from actual outcomes; the harness emits no cold-cache claim of its own).
- 69 harness tests + the Rust suite untouched (no src/ changes this plan).

## Self-Check: PASSED

All key-files exist on disk (bench.py, test_cmd_matrix.py, this SUMMARY); all 4 task commits (fd38b9e, 22b62a3, af61657, 001b95a) are ancestors of HEAD; ledger-measured commit count is 4 (base 4b18be4 -> HEAD 001b95a); full suite 69/69 green on the final tree; all six acceptance criteria re-run and passing on the final tree (parity exit 0 / parse rejection / PATH-cleared exit 2 / test module OK / PROTO-OK protocol shape / disk floor exit 3).

---
*Phase: 04-benchmark-validation*
*Completed: 2026-10-09*
