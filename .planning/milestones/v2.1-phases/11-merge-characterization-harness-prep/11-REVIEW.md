---
phase: 11-merge-characterization-harness-prep
reviewed: 2026-11-16T17:36:03Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - README.md
  - docs/benchmark-report.md
  - scripts/bench/README.md
  - scripts/bench/bench.py
  - scripts/bench/merge_characterize.py
  - scripts/bench/prepare_inputs.py
  - scripts/bench/tests/test_degradation.py
  - scripts/bench/tests/test_disk_floor.py
  - scripts/bench/tests/test_merge_arms.py
  - scripts/bench/tests/test_prepare_inputs.py
  - scripts/bench/tests/test_render_report.py
  - scripts/bench/tests/test_schema.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
  necessity: 0
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-11-16T17:36:03Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the Phase-11 merge-characterization harness prep: the two new dev-host
stages (`prepare_inputs.py`, `merge_characterize.py`), the `bench.py` disk-floor
mechanics (D-10/D-11/D-12) and seven-arm comparison protocol they build on, the
six committed unit suites, and the three documentation surfaces. No structural
findings block was provided, and no external-reviewer evidence was provided, so
this report contains only narrative findings.

The code is unusually defense-heavy and most of it held up under adversarial
reading: the D-10 floor arithmetic was recomputed independently
(93,135,484,166 + 22,927,072,000) × 1.25 / 2³⁰ = 135.11 → ceil 136, matching the
import-time tripwire, the committed constants, and `11-FLOOR-DERIVATION.md`;
every number in `docs/benchmark-report.md` was recomputed from its own per-rep
columns (medians, CV%, deltas, conservation) and all check out; the
`reservoir_slice` manifest contract consumed by the ladder's honest-reuse logic
matches `random_slice.py` exactly; and the binary-light unit suites pass as
committed (39 tests green). The D-12 per-rep disk re-check, the anchor
reconciliation, and the fail-loud parsers are all correctly wired.

Four warnings were found, all with concrete reproducible impact: a latent
out-of-memory trap in the full-scale comparison path that can destroy an
entire multi-hour measurement session after the fact; a `--render-report`
default that silently overwrites a results artifact with a wrong-kind file; a
silently ignored `--merge-input` in one mode that violates the harness's own
never-silent contract; and a README rehearsal recipe that provably cannot
reproduce the recorded dress rehearsal (the committed evidence file shows the
real commands differed in exactly the missing flags). Five info items cover
test-fidelity and robustness gaps.

Necessity was assessed at standard depth against
`~/.claude/gsd-core/references/necessity-review.md` (read successfully): zero
necessity findings. Nearly every guard in these scripts sits on a trust
boundary (env vars, CLI args, files, subprocess output, deserialized JSON),
which the rubric explicitly excludes from impossible-state classification; the
remaining defensive patterns carry stated rationales or real failure modes.

## Warnings

### WR-01: Full-scale comparison path runs the in-memory dump-vs-dump gate — OOM after hours of measurement, results lost

**File:** `scripts/bench/bench.py:1857-1859` (gate invocation), `scripts/bench/bench.py:1614-1635` (in-process compare)
**Category:** correctness/robustness
**Issue:** `run_bench`'s comparison path (`--reps >= 2`, merge arms enabled) ends with
`dump_vs_dump_equal(db_merged, jf_merged, ...)`, which `read_text()`s both full
dumps and builds normalized + sorted lists in the Python heap. The repo itself
proves this form cannot run at scale: `merge_characterize.py:181-191` states
the in-process variant "requires ~120-150 GB of Python heap and cannot run on
this host" at merely the 10% ladder rung (~356M lines per side) — which is why
the streaming gate was written. A full-scale run (`--mode full --reps 2`
without `--skip-merge`) produces billions of entries; the gate executes only
AFTER every rep of a multi-hour session, and `run_bench` writes `results.json`
only after the gates (bench.py:1950). So the session dies in `MemoryError` (or
swap death) with nothing written and exit 1 — the entire measurement is lost.
Nothing in `bench.py` warns, blocks, or scales the gate by mode.
**Fix:** Route the deep leg through the streaming comparator at scale (lift
`dump_vs_dump_equal_streaming` from `merge_characterize.py` into `bench.py` and
use it whenever the merged outputs exceed an in-memory-safe line/byte bound, or
unconditionally for `mode == "full"`), or hard-fail early (before any
measurement) when `mode == "full"` and merge arms are enabled without an
explicit opt-in, pointing the user at the streaming form.

### WR-02: `--render-report` without `--out` writes the Markdown report over the default results.json

**File:** `scripts/bench/bench.py:2529-2531, 2556-2561`
**Category:** correctness (data-clobbering default)
**Issue:** `main()` unconditionally defaults `--out` to
`scripts/bench/scratch/results.json` (verified:
`DEFAULT_SCRATCH / "results.json"`) before the mode branches. Under
`--render-report` that same path is then used as the REPORT destination, so
`python3 scripts/bench/bench.py --render-report --results a.json b.json`
silently overwrites whatever results artifact a previous default-path run left
at that exact location — replacing a measurement JSON with a Markdown report of
a different kind. This contradicts the harness's own artifact-identity
discipline (the Phase-10 render stage is explicitly designed so "a failed
re-render never destroys the previously published verdict/report", per
`scripts/bench/README.md:371-373`). The documented regeneration command always
passes `--out`, so the bug fires only on the omitted-`--out` invocation — but
that is the same invocation form documented for the parity/measure paths, making
the clobber easy to trigger.
**Fix:** Make `--render-report` require an explicit `--out`
(`parser.error("--render-report requires --out")`), or give the render
destination its own default (e.g. `scratch/benchmark-report.md`) so it can never
collide with the results.json slot.

### WR-03: `--merge-input` is silently ignored in synthetic mode, violating the helper's never-silent contract

**File:** `scripts/bench/bench.py:1759-1760` (synthetic branch), contract at `scripts/bench/bench.py:609-627`
**Category:** bug (fail-silent invalid combination)
**Issue:** `merge_input_for`'s documented contract is "Raises ValueError for a
non-slice mode or a missing file — never a silent ignore" (bench.py:613-627).
`run_parity_cli` honors it unconditionally for every mode (bench.py:1162), but
`run_bench` only calls it in the slice branch and the full branch; the
synthetic branch (`bench.py:1759-1760`) never sees `args.merge_input`. So
`bench.py --mode synthetic --merge-input <r2.gz>` runs the plain A/B synthetic
arrangement with no error, no warning, and no record — the user believes they
measured the r1/r2 merge arrangement while the harness measured something else.
For a harness whose entire ethos is "fail loud on invalid combinations" this is
a real gap, and the correctness of the emitted results doc is affected (the
run is labeled as if the requested arrangement never mattered).
**Fix:** Validate before the mode branches, mirroring `run_parity_cli`:
`merge_input_for(mode, args.merge_input)` for every resolved mode (the helper
already raises for non-slice modes), or add `if args.merge_input is not None: merge_input_for(mode, args.merge_input)` at the top of `run_bench`.

### WR-04: README rehearsal Stage A/B commands are not runnable as documented and cannot reproduce the recorded rehearsal

**File:** `scripts/bench/README.md:459-464` (rehearsal table), vs. the disk-floor discipline at `scripts/bench/README.md:445-454`
**Category:** documentation defect with reproducibility impact
**Issue:** The dress-rehearsal table documents:
Stage A `bench.py --mode slice --slice-reads 50000 --reps 2 --self-check` and
Stage B `bench.py --mode slice --slice-reads 200000 --k {21,31} --reps 3
--self-check`. All three fail as written:

1. Both omit `--input`; explicit `--mode slice` with no resolved input exits 1
   immediately (`bench.py:665-674`, "slice mode requires a resolved input").
2. `--k {21,31}` expands (bash brace expansion) to `--k 21 --k 31`, and
   argparse keeps only the last occurrence — verified empirically: parsed
   `k == 31`. The claimed outcome "all seven arms at both k" is impossible from
   that command line; k=21 never runs.
3. Both omit the scaled `--disk-floor-gb` budget that the same README's
   disk-floor section mandates for rehearsal runs ("Slice/rehearsal runs pass
   their computed scaled budget explicitly (e.g. `--disk-floor-gb 2` at
   200k-read scale)"). Without it, the D-12 per-rep re-check
   (`run_comparison_protocol` is passed `args.disk_floor_gb`, whose default is
   the 136 GiB derived floor, and is "active in comparison runs regardless of
   mode", bench.py:1684-1689) hard-exits 3 on any host with < 136 GiB free.

The committed evidence proves the real commands differed in exactly these
flags: every run in `.planning/phases/11-merge-characterization-harness-prep/11-REHEARSAL-RESULTS.json`
carries `--input <split dir> --disk-floor-gb 2 --out <stage dir>/results.json`
and one `--k` value per invocation. A maintainer copying the README table gets
exit 1 (Stage A) or a k=31-only, floor-blocked run (Stage B) — not the proof
the table describes.
**Fix:** Replace the table's command column with the recorded per-k invocations
(e.g. `bench.py --mode slice --input "$SRC_DIR" --slice-reads 200000 --k 21
--reps 3 --self-check --disk-floor-gb 2 --out .../results.json`, repeated for
k=31), or annotate the table with the flags it currently omits.

## Info

### IN-01: Real-run tests in test_schema.py lack the release-binary skip guard

**File:** `scripts/bench/tests/test_schema.py:32-53, 178-198`
**Issue:** `TestRealSelfCheckOutput` and `TestRealRunProvenance` invoke
`bench.py` against `target/release/rustkmer` with no
`@unittest.skipUnless(HAS_RELEASE, ...)`, unlike the equivalent real-binary
classes in `test_prepare_inputs.py:254-256, 333-335`. On any checkout without
a built release binary (the documented local first-run state), these tests
fail instead of skipping, making the committed unit suite environment-dependent.
**Fix:** Add the same `HAS_RELEASE = Path(DEFAULT_RUSTKMER).is_file()` guard and
`skipUnless` decorators used in `test_prepare_inputs.py`.

### IN-02: Non-dict JSON evidence/manifest files crash with AttributeError instead of the exit-2 contract

**File:** `scripts/bench/merge_characterize.py:816-822`, `scripts/bench/prepare_inputs.py:372-377`
**Issue:** `load_doc` and `load_manifest` call `.get()` directly on
`json.loads` output. A file containing valid-but-non-dict JSON (a list or
scalar) raises `AttributeError`, which is outside both `main()` handlers'
`except (OSError, RuntimeError, ValueError)` tuples — the CLI dies with a raw
traceback and exit 1 instead of the contracted "invalid inputs exit 2" with a
named message. (`JSONDecodeError` for unparseable files is caught, so only the
wrong-shape case slips through.)
**Fix:** After `json.loads`, check `isinstance(doc, dict)` and raise
`ValueError(f"... is not a JSON object ...")` before any `.get()`.

### IN-03: Disk-floor protocol test mocks attempt_cache_purge with the wrong return shape

**File:** `scripts/bench/tests/test_disk_floor.py:186-190`
**Issue:** `TestPerRepRecheck._protocol` patches `attempt_cache_purge` with
`return_value={"purged": False, "ci": False}` (a dict), but production returns
a string label (`"purged"` / `"runner-fresh"` / `"unavailable"`,
`bench.py:1288-1316`). The reps in that test therefore record a dict as
`cache_state`. The test's assertions never touch it, so it passes, but the mock
diverges from the real contract and will mislead anyone who later asserts on
`cache_state` in this fixture.
**Fix:** `return_value="unavailable"` (the honest no-purge label the mocked
context would produce).

### IN-04: Contradictory Python floor claims — README says 3.10+, Phase-11 scripts require 3.11+

**File:** `scripts/bench/README.md:5` vs. `scripts/bench/merge_characterize.py:48-49`, `scripts/bench/prepare_inputs.py:27-28`
**Issue:** The harness README declares "Python 3.10+ stdlib only — no pip
installs anywhere", while both new Phase-11 scripts state "Python 3.11+ stdlib
only" and the project's normalized floor is 3.11 (`.claude/CLAUDE.md`).
A 3.10 host following the README header passes its stated requirement and then
fails on the new stages.
**Fix:** State the floor per component in `scripts/bench/README.md:5` (core
harness 3.10-compatible, Phase-11 stages 3.11+), or raise the header to 3.11+.

### IN-05: `cleanup_scratch` rmtree's the entire `--scratch` root with no ownership guard

**File:** `scripts/bench/merge_characterize.py:850-860` (cleanup), `scripts/bench/prepare_inputs.py:234-251` (the only guard)
**Issue:** At the end of a successful `--run`, `cleanup_scratch(args.scratch)`
`shutil.rmtree`s the whole scratch root. The only protection is
`refuse_repo_root`, which excludes the repo tree but nothing else — pointing
`--scratch` at any existing out-of-repo directory containing unrelated data
deletes all of that data at end of run. The ladder creates its own
`n<N>/...` subdirectories beneath the root, so it could confine removal to what
it created.
**Fix:** Remove only ladder-created subdirectories (`n3500000`, `n14000000`),
or refuse to clean a root that contains entries the ladder did not create
(e.g. require an empty-or-ladder-only root, recorded via a marker file).

---

_Reviewed: 2026-11-16T17:36:03Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
