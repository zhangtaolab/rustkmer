---
phase: 12-full-scale-merge-verdict
reviewed: 2026-11-17T09:47:19Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - docs/benchmark-report.md
  - scripts/bench/phase11.py
  - scripts/bench/tests/test_phase11_verdict.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
  necessity: 0
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-11-17T09:47:19Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the Phase-12 merge-verdict deliverables at standard depth: the controller (`scripts/bench/phase11.py`), its unit suite (`scripts/bench/tests/test_phase11_verdict.py`), and the hand-shaped benchmark report (`docs/benchmark-report.md`). All five imported harness modules (`bench.py`, `merge_characterize.py`, `prepare_inputs.py`, `phase10.py`, `output_stage.py`) were cross-referenced to verify call signatures and return shapes.

**The published evidence chain verifies end-to-end.** I re-rendered the committed evidence JSONs with `python3 scripts/bench/phase11.py --stage render` and the output is **byte-identical to the committed `12-MERGE-REPORT.md`** (sha256 `9adcc8924eefae5f1f0c7fbb872277ee28cc200facd62bb57db68021b5360cc7`). The report's number contract holds mechanically: all 40 decimal tokens in `docs/benchmark-report.md` are greppable in the mechanical report except exactly the 7 labeled context numbers (2.79, 16.7, 86.74, 144.69, 147.08, 43.97, 68.52 — dataset sizes, cleanup size, v2.0 references, as the contract allows). All output/binary sha256s, provenance tokens (git commit `e9df71af…`, `dirty=True`, `rustc 1.101.0-nightly`), parity lines, and the verdict rule (verbatim modulo line wrap) were confirmed against `12-VERDICT.json` and `12-MERGE-REPORT.md`. The 8-artifact byte total (93,135,484,166) matches `MEASURED_INPUT_ARTIFACTS_BYTES` exactly and equals the claimed ~86.74 GiB. The verdict table (63.34/88.44 at k=21, 82.86/114.7 at k=31, YES/NO-INVEST/exit 0) matches `12-VERDICT.json` and the committed results documents (3 reps per arm per k). All 73 unit tests pass. The cited `tests/thread_pool_size_tests.rs` exists and pins exactly the cited 2-at-N=1 / 2N+1 pool contract.

No Critical findings. The three Warnings are robustness/provenance-binding defects reachable only outside the pinned workflow (a non-default `--rustkmer` flag) or on gate-failure paths; none affect the published verdict. Security posture is clean: list-form subprocess throughout, `validate_path` screening on the harness's only shell string (pre-existing `bench.py`), no secrets, no eval, no network. Necessity review (`$HOME/.claude/gsd-core/references/necessity-review.md`) was read; no necessity findings raised — the controller's guards defend genuine trust boundaries (manifest JSON, external binaries, evidence documents) or plausible maintenance states, not impossible ones.

## Warnings

### WR-01: Timed stage measures `DEFAULT_RUSTKMER` while the doc records `--rustkmer` — provenance mis-attribution

**File:** `scripts/bench/phase11.py:981`
**Issue:** `_timed_rounds` builds the measured argv with `merge_arm_argv(name, k, manifest, scratch)` — no `rustkmer` kwarg — so every measured rep executes `DEFAULT_RUSTKMER` (`"target/release/rustkmer"`, `bench.py:58`) regardless of `--rustkmer`. But `run_timed` records the doc's `command_line` with `merge_arm_argv(..., rustkmer=rustkmer)` (`phase11.py:1111`) and attributes arm provenance via `provenance_fn(rustkmer, "release")` (`phase11.py:1104`) — both from `args.rustkmer`. The binary-identity tripwire (`phase11.py:1072`) pins only `DEFAULT_RUSTKMER`'s sha256 and its return value is never used in `run_timed`. With a non-default `--rustkmer X`, the recorded evidence provably mis-attributes: `command_line` names `X`, `provenance.binary` hashes `X`'s bytes, while the wall times were produced by the default binary — and `X` itself is never hash-pinned. `run_parity` takes the opposite approach (measures `args.rustkmer` at `phase11.py:739` while the tripwire verified the default), so the two stages cannot both be correct when the flag is exercised; parity evidence could then claim "binary_identity: green (pinned ladder sha256 verified)" (`phase11.py:728`) for a binary the tripwire never verified. For a harness whose contract is T-12-06 ("no artifact lands without complete provenance attributing the hashed bytes"), this is a genuine binding defect. Latent in the pinned workflow (the flag was not used), hence Warning, not Critical.
**Fix:** Thread the executable through the stage: add a `rustkmer` parameter to `_timed_rounds` and pass `args.rustkmer` from `run_timed` (mirroring `run_parity`); then bind the tripwire to the actually-measured binary — e.g. replace the unused `identity` in `run_timed`/`run_parity` with `assert_binary_identity(executable=rustkmer, ...)` or raise when `provenance_fn(rustkmer, "release")["binary"]["sha256"] != RUSTKMER_BIN_SHA256`, so a non-pinned binary fails at the gate instead of landing mis-attributed evidence. Extend `TestTimedRounds` to assert the fixture `measure_fn` received argv[0] == the requested binary.

### WR-02: Parity-stage failure paths strand multi-GiB transients on the pinned data volume

**File:** `scripts/bench/phase11.py:787-823`
**Issue:** `run_parity`'s deletions exist only on the success path: `recount.k{k}.rkdb` (created at `:792`, ~23 GB at k=31) is unlinked at `:810` only after `recount_vs_merged_equal` returns; `merged.k{k}.rkdb` (~23 GB) and `merged.k{k}.jf` (~9 GB) are unlinked at `:818-820` only after Leg 3 passes. Any gate failure — Leg-1 `assert_merge_parity`, the recount Total anchor check (`:799`), the Leg-2 diff, or Leg 3 — raises to exit 2 and strands 30–55 GB in scratch on the data volume. A retry session's computed `session_budget_gb` floor (282 GiB, enforced by `check_disk_floor`/`ensure_disk_headroom`) assumes a clean scratch, so accumulated failures can push a legitimate session into the exit-3 disk block or an ENOSPC mid-rep. The success path is explicitly meticulous about deletion sequencing ("research Pitfall 5", `:807-809`); the failure path is not. No correctness impact (failures are loud, no doc lands), hence Warning.
**Fix:** Wrap the leg sequence in `try/finally` that unlinks `recount_rkdb`, `merged_rkdb`, and `merged_jf` when the gate raises (recording the emergency deletions in the raised message or stderr), e.g. collect `pending = [recount_rkdb, merged_rkdb, merged_jf]` and in the `finally` on failure path `for p in pending: p.unlink(missing_ok=True)`; keep the success-path ordered deletion as-is.

### WR-03: Vacuous t1-exclusion test — the load-bearing A2 rule is never exercised with a differing t1 wall

**File:** `scripts/bench/tests/test_phase11_verdict.py:418-428`
**Issue:** `test_merge_t1_excluded_from_verdict_but_recorded_as_scaling` builds `baseline` and `with_slow_t1` from two identical `make_results_doc(k=21)` calls, so the headline assertion `baseline["result"] == with_slow_t1["result"]` compares `f(x)` to `f(x)` — it cannot fail under any verdict rule, including one that wrongly folds `merge-t1` into YES/NO (e.g. requiring the t1 arm to also match-or-beat). The test name promises the A2 rule ("merge-t1 … never enters the YES/NO verdict") but pins only the `scaling` extraction. A regression in `verdict_block`'s result computation would pass this suite.
**Fix:** Build a case where the merge arm wins but the t1 arm loses, e.g. `make_results_doc(merge_wall=50.0, t1_wall=100.0, k=21)` against the default `jf_wall=63.5`: the pinned rule must yield YES (50.0 <= 63.5) while any rule incorporating t1 yields NO. Assert `p11.verdict_block(21, doc)["result"] == "YES"` for that input (and keep a slower-t1 case for the `scaling` extraction).

## Info

### IN-01: Arm-level `route` cell renders only reps[0]'s route

**File:** `scripts/bench/phase11.py:934`
**Issue:** `_timed_arm` sets `"route": reps[0]["route"]`, and `_methodology_lines` renders that single value as the arm's route. Per-rep routes are recorded honestly in the evidence JSON, but the rendered methodology row would present one rep's attribution as the arm's if reps disagree. Latent today — all committed routes are `not-reported` and attribution is deterministic per tool — but the test fixture itself constructs diverging routes (`prefix-cache` + two `not-reported`, `test_phase11_verdict.py:1409`), showing the shape permits silent masking.
**Fix:** Render the arm route as the per-rep set when they disagree (e.g. `mixed(prefix-cache,not-reported)`), or add a render-time check that all reps of an arm share one route and fail loudly otherwise.

### IN-02: Duplicate arm names pass results-document validation; verdict scaling silently picks the first

**File:** `scripts/bench/phase11.py:1253-1272`
**Issue:** `_validate_results_document` checks each arm's name is one of `MERGE_ARMS` but never that names are unique. `_required_arm` enforces exactly-one only for `merge`/`jellyfish-merge` (verdict) and all three names (render), so a hand-built or drifted results doc with two `merge-t1` arms passes verdict-stage validation and `verdict_block`'s scaling loop (`:1194-1203`) silently takes the first duplicate with a numeric wall. The render stage would reject it later, but the verdict doc can publish first.
**Fix:** In `_validate_results_document`, collect `names = [arm["name"] for arm in doc.get("arms", [])]` and raise when `sorted(names) != sorted(MERGE_ARMS)` (exactly one of each), or at minimum raise on `len(set(names)) != len(names)`.

### IN-03: `--help` under-describes stage requirements for `--round0` and `--parity-doc`

**File:** `scripts/bench/phase11.py:1879-1884`
**Issue:** `--round0`'s help reads "timed stage: the round-0 revalidation evidence document", but `run_parity` also hard-requires it (`:711-714`, exit 2 without it). `--parity-doc`'s help reads "render stage: the two parity evidence documents", but the timed stage requires exactly one (`:1057-1064`, exit 2). An operator wiring the staged session from `--help` alone would mis-invoke the parity/timed stages and get exit-2 refusals.
**Fix:** Update both help strings, e.g. `--round0`: "parity/timed stage: the round-0 revalidation evidence document"; `--parity-doc`: "timed stage: this k's parity document; render stage: the two parity documents (k=21 and k=31)".

---

_Reviewed: 2026-11-17T09:47:19Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
