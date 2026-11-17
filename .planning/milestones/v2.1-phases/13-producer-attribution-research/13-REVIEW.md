---
phase: 13-producer-attribution-research
reviewed: 2026-11-17T14:57:47Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - scripts/bench/phase13.py
  - scripts/bench/tests/test_phase13_driver.py
  - scripts/bench/fixtures/phase13_probe_k31.Cargo.lock
  - scripts/bench/fixtures/phase13_null_consumer.Cargo.lock
findings:
  critical: 2
  warning: 9
  info: 4
  total: 15
  necessity: 1
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-11-17T14:57:47Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Scope: the Phase-13 producer-attribution driver (`scripts/bench/phase13.py`, 2539 lines), its
unit suite (`scripts/bench/tests/test_phase13_driver.py`, 1350 lines), and the two committed
lockfile fixtures. No `<structural_findings>` block was supplied, so the fallow section is
omitted.

What was checked: every reviewed file was read in full; the imports were traced into
`bench.py`, `merge_characterize.py`, `output_stage.py`, `phase10.py` and `prepare_inputs.py`
to confirm each call actually does what the driver assumes (`_guard_zero` arity,
`ensure_free_space` units, `rotation_schedule` round order, `publish_atomic` contract,
`validate_provenance` strictness, `reduce_arm` keys); the embedded Rust probe templates were
checked against the live `src/count/engine.rs` and `src/kmer/extract.rs` API
(`EngineConfig::new`, `CountResult::diagnostics`, `WorkerDiagnostics`, `for_each_window` /
`WindowSummary::emitted`) — they match, and gzip inputs are handled by
`DefaultCompressedFileReader::open_compressed`, so the arm-C gzip path is viable. The unit
suite was executed: **80 tests, OK**. The committed `13-GATE-MEMO.md` was re-rendered twice
from `13-ATTRIBUTION.json`: byte-identical to the committed memo and to itself. The lockfile
fixtures contain only `crates.io` registry sources; the two local path packages (`rustkmer`
0.5.0, `phase13-*` 0.1.0) carry no `source` field and the pinned versions match the embedded
manifests (`bio 2.3.0`, `serde_json 1.0.145`) — **no fixture anomalies**.

Assessment: the arithmetic, the pre-registered constants, the probe k-contract enforcement and
the render determinism are genuinely well built. The weakness is on the integrity boundary the
plan itself names ("evidence doc -> memo renderer: a hand-typed or stale number here corrupts
the D3 decision downstream", `13-03-PLAN.md:256`): the memo renderer trusts the stored
attribution/predicted-win/decision without ever re-deriving them from the run records it
cites, and the evidence doc is written non-atomically 77 times per session. Both were
reproduced live against the committed evidence doc (see CR-01/CR-02). The suite is green, but
two tests encode the unsound behaviour rather than catch it.

No source files were modified.

## Critical Issues

### CR-01: Memo renders stored attribution/decision without re-deriving it from the cited run records

**File:** `scripts/bench/phase13.py:2412-2469` (run_memo), `:2379-2406` (run_measure incremental writes), `:859-865` (write_doc)

**Issue:** `run_memo` validates provenance and gate-matrix completeness, then renders
`doc["attribution"]`, `doc["predicted_win"]` and `doc["predicted_win"]["decision"]` exactly as
stored. It never calls `compute_gate_blocks` / `build_attribution` / `derive_gate_decision`
again, and it never checks that a citation key resolves to a record or that a cited record's
numbers reproduce the printed value. Two reproduced failures:

1. Copy of `13-ATTRIBUTION.json` with all three arm-A k=21 `wall_s` rewritten to `200.0`
   (stored attribution untouched): `--stage memo` exits 0 and section 3 still prints
   `predicted improvement vs fresh arm-A median (158.2900 s): 9.6235%`, while the three cited
   arm-A records now reduce to `200.0` (`bench.reduce_arm(...)["median_wall_s"] == 200.0`).
   The memo's own claim ("Every number below cites a named full-scale run record") is false,
   and the render proof still says `byte_identical`.
2. Same doc with `decision = "GO"` and `per_k_improvement_pct = {21: 99.0, 31: 99.0}` while
   the per-k blocks still carry 9.62 % / 10.80 %: the memo publishes `DECISION: GO` and
   `k=21: conservative predicted improvement 99.0000%` alongside
   `predicted improvement ... 9.6235%` — a self-contradictory gate artifact, exit 0.

This is not only a hand-edit scenario. `run_measure` loads the previous document, rewrites
records incrementally (one `write_doc` per record, 76 writes) and recomputes the gate blocks
only after the last record (`:2399`). A crash / Ctrl-C / ENOSPC in the middle of a re-run
leaves freshly measured records next to the *previous* session's attribution and decision;
`run_memo`'s only guards (provenance shape, three distinct reps per arm×k) cannot detect that.
The suite encodes the unguarded behaviour: `test_no_go_fixture_also_exits_zero`
(`test_phase13_driver.py:923-937`) flips only `decision`, leaving the per-k improvements at
49.83 %, and asserts exit 0.

**Fix:** Re-derive and cross-check inside `run_memo` (the functions are pure and already use
the records):

```python
# after validate_memo_inputs(doc)
recomputed = copy.deepcopy(doc)
compute_gate_blocks(recomputed)          # build_attribution + build_predicted_win + decision
for key in ("attribution", "predicted_win"):
    if recomputed[key] != doc[key]:
        raise ValueError(
            f"memo: stored {key} disagrees with a re-derivation from the recorded runs "
            "— refusing to render stale or hand-edited math (T-13-09)")
```

Belt-and-braces: have `run_measure` reset `doc["attribution"] = {"per_k": {}}` and
`doc["predicted_win"] = {"per_k": {}}` before the first record, so an interrupted session can
never carry stale math. Add an arm×k×rep multiplicity check to `validate_memo_inputs`
(A/B: 1, control: 2, C: 4, D: 2 per rep) and require `probe_output_json` on C/D records, since
a re-derivation would otherwise raise `KeyError` on a thinned matrix. `test_no_go_fixture_also_exits_zero`
will need to rewrite the per-k blocks consistently.

### CR-02: Evidence-document writes are non-atomic — a crash during any of the 77 writes destroys the whole session record

**File:** `scripts/bench/phase13.py:859-865`, called at `:2386`, `:2396`, `:2401`, `:2283`

**Issue:** `write_doc` opens the destination with mode `"w"` (truncate first) and then streams
the JSON. A `KeyboardInterrupt` (the realistic abort during a multi-hour session — note
`main` at `:2533` does not catch it), a power loss, or an ENOSPC between the truncate and the
end of the write leaves a partial JSON document. `load_doc` then raises `JSONDecodeError` and
the entire session's measurements are unrecoverable — there is no backup and no sibling temp.
`run_measure`'s docstring at `:2359` claims "crash-safe incremental writes"; the increments are
crash-safe against losing individual records, the write itself is not. The same applies to the
single `run_prep` write at `:2283` (the decompression/probe provenance block).

**Fix:** Publish via sibling temp + `os.replace` (the pattern already used by
`phase10.publish_atomic`), with `fsync` for the abort case:

```python
import tempfile

def write_doc(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp",
                               dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        _unlink_quiet(tmp)
        raise
```

## Warnings

### WR-01: `--scratch` is parsed but never used; every scratch path is hardcoded

**File:** `scripts/bench/phase13.py:2497-2499`; hardcoded at `:2048`, `:2252`, `:2351`

**Issue:** The CLI advertises `--scratch` ("probe scratch root (must be outside the repo)"),
but no code reads `args.scratch` — `run_rehearsal` uses `PROBE_SCRATCH_ROOT/"rehearsal"`,
`run_prep` uses `PROBE_SCRATCH_ROOT/"session-probes"`, `_full_scale_ctx` uses
`PROBE_SCRATCH_ROOT/"session-out"`, and `--generate-lock-fixtures` ignores it too. An operator
who re-points scratch at a volume with space (the harness writes several GB of probe builds and
per-rep `.rkdb` outputs) is silently overridden, and the help text is misleading.

**Fix:** Thread the resolved root through `run_rehearsal` / `run_prep` / `_full_scale_ctx` /
`generate_lock_fixtures` (`refuse_repo_root(Path(args.scratch))`), or remove the option.

### WR-02: Bounds mode still issues a GO/NO-GO from inputs the code declares invalid; a negative `output_stage_s` is accepted unflagged

**File:** `scripts/bench/phase13.py:1080`, `:1191-1199`, `:1206-1223`, `:1301-1332`

**Issue:** `output_stage_s = median_a - count_phase_wall_probe_s` (`:1080`) is a physically
non-negative quantity (sort + write). When A3 trips (`probe_vs_cli_ratio > 1.0`, `:1208`), the
probe wall exceeds the CLI wall and the residual goes negative; the "conservative" derated wall
then falls *below* its own serial terms and the reported improvement can approach or exceed
100 %. The repository's own fixture demonstrates it: `_attribution_runs(arm_c_gzip=100.0)`
yields `mode == "bounds"` and a "conservative" predicted wall of `55.25 - 50 = 5.25 s`, i.e.
~96.5 % improvement → GO, while the memo simultaneously prints the A3 anomaly and withholds
point shares. `derive_gate_decision` consumes the contaminated number regardless of `mode`.

**Fix:** Add an anomaly criterion and let it withhold a definitive decision:

```python
if output_stage_s < 0:
    anomalies.append(
        "output_stage_s={:.6f} is negative — the sort+write residual cannot be negative; "
        "the arm-C probe wall exceeds the CLI wall (A3)".format(output_stage_s))
```

and either mark the decision provisional (`decision_valid: bool`) or refuse a GO when
`mode == "bounds"`. D-05 fixes the bar, not the validity of the instrument feeding it.

### WR-03: Memo renders an inverted wall interval in bounds mode

**File:** `scripts/bench/phase13.py:1277-1287` (construction), `:1568-1573` (render)

**Issue:** `bounds.predicted_full_wall_s` maps `lower_s` to the **derated** wall and `upper_s`
to the **idealized** wall, but the derated wall is always ≥ the idealized wall
(`parse_extract_s > 0` is enforced). The renderer then prints `predicted_full_wall in
[{lower_s}, {upper_s}] s`. Reproduced against the committed doc (worker busy zeroed to force
bounds mode):

```
- BOUNDS MODE: point shares withheld. predicted_full_wall in [143.0570, 141.7468] s;
  improvement in [28.4715, 29.1266] %
```

The wall range descends while the improvement range ascends. The unit test
`test_zero_busy_total_bounds_with_interval_and_assumptions`
(`test_phase13_driver.py:1165-1180`) asserts `walls["upper_s"] <= walls["lower_s"]`, encoding
the inversion. Also note the `.get(..., 0.0)` defaults at `:1570-1573` silently print zeros if
a bounds block is malformed, contradicting the renderer's "never a silent default" stance.

**Fix:** Render `predicted_full_wall in [{upper_s}, {lower_s}] s` (or rename the keys
`conservative_s` / `optimistic_s` and render in that order), and drop the `0.0` defaults in
favour of a loud refusal when a key is absent.

### WR-04: Memo lifecycle/deletion record hardcodes `PLAIN_INPUTS_DIR` / `DATASET_DIR` instead of the recorded paths

**File:** `scripts/bench/phase13.py:1686-1692`

**Issue:** Section 7 (D-04 lifecycle) renders the module constants, not what the session
actually used. Every other path is honouring `--plain-dir` (`:2207`, `:2300`), so a run with
`--plain-dir /Volumes/scratch/plain` produces a deletion record naming
`/Users/forrest/Data/data/illumina/CRR1936095-plain`, and a regeneration recipe with a
placeholder source. The prep block stores only per-part `path` values, so the renderer cannot
recover the directory today.

**Fix:** Record `"plain_dir": str(plain_dir)` and `"data_dir": str(data_dir)` in
`doc["prep"]` at `:2271`, and render them from `doc["prep"]` (falling back only when absent).

### WR-05: Measure re-verifies the plain inputs against prep but never the gzip sources — `prep["gzip_inputs"]` is dead provenance

**File:** `scripts/bench/phase13.py:2305-2323`

**Issue:** `_full_scale_ctx` refuses when a plain part's sha256 no longer matches the recorded
one, but performs no equivalent check on the gzip parts it is about to measure in arm A. The
like-for-like premise of the A/B delta is `plain == gunzip(gzip)`; if a gzip part changes
between prep and measure (re-split, re-download, in-place edit), arm A reads new bytes while
arm B reads the prep-time plain file, `inflate_s`/`delta_correction_s` silently mix two
datasets, and the recorded `gzip_inputs` block is never consulted.

**Fix:** Mirror the plain check:

```python
recorded_gzip = {e.get("part"): e for e in prep.get("gzip_inputs") or []}
prefix = recorded_gzip.get(part) or {}
if prefix.get("sha256") and prefix["sha256"] != fingerprints[part]["gzip"]["sha256"]:
    raise ValueError(f"gzip input {part} sha256 changed since prep — refusing to measure")
```

### WR-06: Probe binaries are hashed at prep and never re-verified at measure

**File:** `scripts/bench/phase13.py:2325-2343`

**Issue:** The stock binary's sha256 is re-checked against prep (`:2325-2331`), but each probe
binary path is taken straight from `entry["provenance"]["binary"]["path"]` (`:2342-2343`) with
no re-fingerprint. If `target/release/examples/engine_probe` is rebuilt (for example by a
plain `cargo build --release --examples` after the profiling build) or a scratch probe is
relinked, the harness executes the new bytes while every arm-C/D record cites the prep-time
`binary_sha256`. The arm-C/D provenance claim would then be false, which is exactly what the
phase's threat model forbids ("a path string without a hash is not provenance").

**Fix:** At ctx build, `fingerprint(Path(entry["provenance"]["binary"]["path"]))` and compare
to `entry["provenance"]["binary"]["sha256"]`; refuse on mismatch, as for the stock binary.

### WR-07: Disk guard checks the source volume, not the volume that receives the plain files

**File:** `scripts/bench/phase13.py:2210-2215` (guard) vs `:2207`, `:2226`, `:2236` (writes)

**Issue:** `free_before = free_bytes_fn(data_dir)` and
`ensure_free_fn(data_dir, required_free_bytes / (1 << 30))` probe `--data-dir`'s filesystem,
but the ~76 GB of plain FASTQ is written to `--plain-dir`, which is independently overridable
and may live on another mount. The guard can pass while the destination volume fills, leaving
a truncated part; recovery exists (sha mismatch triggers re-decompression) but only after an
ENOSPC abort mid-session is discovered.

**Fix:** Run the guard on `plain_dir` (create it first, or use its nearest existing ancestor —
`free_bytes` already walks up), and keep recording the free bytes for the actual write volume.

### WR-08: `main()` maps only OSError/RuntimeError/ValueError to exit 2; several malformed-evidence paths raise KeyError/AttributeError as tracebacks with exit 1

**File:** `scripts/bench/phase13.py:2533-2534`

**Issue:** The documented contract is "2 = infrastructure/invalid input". Concrete
uncaught paths: `render_memo_text` does `block[name]` for nine stage keys (`:1510-1513`) →
`KeyError` on a doc that is schema 1 but missing a term; `assert_clean_tree` interpolates
`provenance.get(...)` in its own error message (`:907`) → `AttributeError` when
`provenance` is `None`; `_full_scale_ctx` indexes
`entry["provenance"]["binary"]["path"]` (`:2342-2343`) → `KeyError` on a malformed prep entry.
Each surfaces as a Python traceback and exit 1 instead of a clean exit 2.

**Fix:** Add `KeyError, TypeError, AttributeError` to the except tuple at `:2533`, or convert
those three sites to explicit `ValueError`/`RuntimeError` raises with named fields.

### WR-09: Predictable world-writable scratch root reused without an ownership/permission check

**File:** `scripts/bench/phase13.py:173`, `:598-651`, `:2048`, `:2347-2354`

**Issue:** `PROBE_SCRATCH_ROOT = /tmp/phase13-probe-scratch` is a fixed name under a
world-writable `/tmp`. `refuse_repo_root` only rejects in-repo paths; a directory pre-created
by another local user is accepted (`mkdir(parents=True, exist_ok=True)` at `:613` and `:2049`)
and the harness writes `Cargo.toml` and `src/main.rs` into it (`:633-638`) before compiling
and executing the result. A permissive pre-created tree lets another local user swap
`src/main.rs` between the write and `cargo build` (TOCTOU) — arbitrary code execution as the
invoking user. The committed threat model (13-SECURITY.md T-13-03) covers repo contamination,
not this. Precondition: a hostile local user or shared runner host.

**Fix:** Create the root with mode `0700` and refuse a pre-existing root whose `st_uid` is not
`os.getuid()` or whose mode is group/other-writable; or use `tempfile.mkdtemp()` per session
and record the path in the evidence document.

## Info

### IN-01: `scratch_cleaned` is a dead field

**File:** `scripts/bench/phase13.py:811`

**Issue:** `new_doc()` seeds `"scratch_cleaned": False`; nothing in `phase13.py` ever writes or
reads it (the committed evidence doc's `true` was set out of band per `.planning/STATE.md:131`,
and the ladder's writer lives in `merge_characterize.py:957`). The test at
`test_phase13_driver.py:132` only asserts its presence.
**Fix:** Drop the field, or add the cleanup verb that records it after the D-04 deletion.

### IN-02: Null-consumer `windows` is not validated

**File:** `scripts/bench/phase13.py:786-792`

**Issue:** The guard-zero class requires `records > 0`, but not `windows > 0`. A run whose
reads are shorter than `k` parses records and emits zero windows; such a record would still be
reduced into `parse_extract_s` as if extraction had run. For the current 150 bp / k ≤ 31 data
this cannot happen, but the guard is the stated invariant of the instrument.
**Fix:** Require `windows > 0` (same message shape as the `records` guard).

### IN-03: Machine-specific absolute paths as committed defaults

**File:** `scripts/bench/phase13.py:162-167`

**Issue:** `DATASET_DIR` and `PLAIN_INPUTS_DIR` default to `/Users/forrest/Data/...`. The
driver fails cleanly on any other machine (`discover_gzip_parts`), but the project constraint
asks the harness to "degrade to slices/synthetic inputs where the full dataset is absent" —
there is no such path here. Acceptable for a one-time local measurement phase, but the
defaults should not silently point at one developer's home.
**Fix:** Make `--data-dir` / `--plain-dir` required for `--stage prep|measure`, or read them
from `RUSTKMER_PHASE13_DATA_DIR` / `RUSTKMER_PHASE13_PLAIN_DIR`.

### IN-04: (necessity) Duplicate `validate_provenance(doc)` with no mutation in between

**File:** `scripts/bench/phase13.py:2431`, `:2460`
**Category:** necessity

**Issue:** `run_memo` validates the same in-memory dict twice; the intervening statements are
`render_memo_text` (pure), two digests, and the construction of `proof_doc`, none of which
mutate `doc`. The second call therefore cannot catch anything the first did not — the guarded
state ("provenance became invalid during the render") cannot occur in this code. Classified
Info rather than Warning because a deliberate second layer around a publish is a defensible
judgment call (necessity-review negative space: defense in depth).
**Fix:** Keep one call (preferably immediately before `publish_atomic`) and drop the other, or
leave both with a comment saying it is deliberate.

---

_Reviewed: 2026-11-17T14:57:47Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
