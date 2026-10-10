---
phase: 04-benchmark-validation
reviewed: 2026-10-10T19:04:26Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - .github/workflows/benchmark.yml
  - .gitignore
  - docs/benchmark-report.md
  - scripts/__init__.py
  - scripts/bench/__init__.py
  - scripts/bench/baselines/bench_baseline.darwin.json
  - scripts/bench/baselines/bench_baseline.linux.json
  - scripts/bench/bench.py
  - scripts/bench/compare.py
  - scripts/bench/gen_synthetic.py
  - scripts/bench/make_slice.sh
  - scripts/bench/README.md
  - scripts/bench/tests/__init__.py
  - scripts/bench/tests/fixtures/time_l_macos.txt
  - scripts/bench/tests/fixtures/time_v_linux.txt
  - scripts/bench/tests/test_cmd_matrix.py
  - scripts/bench/tests/test_compare.py
  - scripts/bench/tests/test_degradation.py
  - scripts/bench/tests/test_generator.py
  - scripts/bench/tests/test_render_report.py
  - scripts/bench/tests/test_schema.py
  - scripts/bench/tests/test_time_parser.py
  - src/io/fastq.rs
findings:
  critical: 1
  warning: 7
  info: 7
  total: 15
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-10-10T19:04:26Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Reviewed the phase-04 benchmark harness (bench.py measurement core, compare.py CI gate, gen_synthetic.py, make_slice.sh, baselines, fixtures, 7 test suites), the CI workflow, and the phase's src/io/fastq.rs deviation (GzDecoder→MultiGzDecoder, commit 8102985).

Overall this is an unusually disciplined harness: strict-fail time parsing with pinned units, a single shared schema validator, parity gating before timing is trusted, honest cache_state recording, and an exit-code contract pinned by boundary tests. Verified independently during review: all 124 bench unit tests pass; the committed docs/benchmark-report.md re-renders byte-identically from the committed evidence JSONs; the report's deltas/CVs/medians recompute correctly from the recorded reps; the FASTA route (src/io/fasta.rs) and the count CLI (src/cli/commands/count.rs) both go through the fixed `open_compressed`, so the MultiGzDecoder swap is complete for the reading paths that matter.

The adversarial pass still found one contract violation at the heart of the phase's anti-repudiation deliverable (a hard-coded measurement literal inside the "zero measurement literals" renderer), plus gate-integrity, data-clobber, silent-degradation, and input-tolerance defects detailed below. Note: the phase diff also contains `scripts/bench/tests/test_merge_input.py`, which is not in the provided review scope; its subject functions (`merge_input_for`, `provision_slice`) were nonetheless cross-checked via bench.py and the passing suite.

## Structural Findings (fallow)

None provided — no structural pre-pass was supplied for this review.

## Narrative Findings (AI reviewer)

### Critical Issues

### CR-01: Renderer hard-codes a measurement literal, violating the T-04-07 "zero measurement literals" contract it implements

**File:** `scripts/bench/bench.py:1285-1296` (literal at 1290); carried into `docs/benchmark-report.md:111`
**Issue:** `_methodology_lines` embeds a hand-written measurement figure in the rendered report:

```python
"- The first full-run attempt (2026-10-10) halted at the harness's "
"count-parity gate: rustkmer's single-member gzip decoder silently "
"read only member 1 of the concatenated-gzip input (220,028 k-mers "
"vs jellyfish's full count). ...
```

`220,028 k-mers` is a measured count from the discarded attempt-1 run; it exists in **no committed results JSON**, so it cannot be regenerated from evidence, is invisible to the byte-identity hand-edit detector (it is constant across renders), and is exactly the "manually overridden measurement number" class the renderer exists to make impossible. This directly contradicts:

- the renderer's own contract comment (bench.py:966-971: "every MEASUREMENT number in the rendered report is read from the results JSONs — the code below carries no measurement literals");
- plan 04-04 Task 3 ("writes a Markdown report containing ONLY numbers mechanically read from the JSONs — the renderer contains no numeric literals of its own"; deliverable: "report renderer (no numeric literals of its own)");
- the threat T-04-07 mitigation claim (high-rated Repudiation threat);
- 04-04-SUMMARY.md's own verification claim ("zero measurement literals", stated three times).

The commit hash `8102985` and the dates are provenance, not measurements, and are acceptable; the k-mer count is not. The unit tests for the renderer do not catch this because they only check byte-identity and JSON-sensitivity — a constant literal passes both.
**Fix:** Either de-numeralize the hard-coded sentence (e.g. "…read only member 1 of the concatenated-gzip input — a small fraction of jellyfish's count…"), or commit the attempt-1 parity evidence as a JSON sidecar and render the number from it like every other figure:

```python
# Option A (minimal): drop the figures from the hard-coded narrative
"- The first full-run attempt (2026-10-10) halted at the harness's "
"count-parity gate: rustkmer's single-member gzip decoder silently "
"read only member 1 of the concatenated-gzip input (a fraction of "
"jellyfish's count). The parity gate caught it before any "
```

Then re-render `docs/benchmark-report.md` and amend the byte-identity check to also `grep` the renderer source for digit-group literals in emitted strings if you want the contract mechanically enforced.

## Warnings

### WR-01: make_slice.sh swallows gunzip failure — corrupt input yields exit 0 and a partial slice

**File:** `scripts/bench/make_slice.sh:35`
**Issue:** `gunzip -c "$INPUT" | head -n $((4 * N_READS)) > "$OUTPUT"` under `set -e` without `pipefail`: the pipeline's exit status is `head`'s (0), so a corrupt or truncated gz that errors mid-stream produces a silently truncated slice and exit 0 — the exact Pitfall-1 class (plausible output from broken input) the phase guards against everywhere else. The Python twin `extract_slice` (bench.py:407-439) explicitly checks gunzip's return code; the shell tool does not. Note the fix is not plain `set -o pipefail`: `head` closing the pipe early gives gunzip SIGPIPE (exit 141) on every normal run, which would false-fail the tool.
**Fix:**

```bash
gunzip -c "$INPUT" | head -n $((4 * N_READS)) > "$OUTPUT"
gz_rc=${PIPESTATUS[0]}
# 141 = SIGPIPE from head's early exit — the normal truncation path
if [ "$gz_rc" -ne 0 ] && [ "$gz_rc" -ne 141 ]; then
    echo "error: gunzip failed rc=$gz_rc on '$INPUT' (corrupt input?)" >&2
    rm -f "$OUTPUT"
    exit 1
fi
```

### WR-02: `--render-report` without `--out` clobbers the default measurement results file

**File:** `scripts/bench/bench.py:1400` (`--out` default `scripts/bench/scratch/results.json`), `bench.py:1382-1386`, `bench.py:1471-1475`
**Issue:** `--out` defaults to the *measurement* output path. `bench.py --render-report --results X.json` without `--out` writes the Markdown report over `scripts/bench/scratch/results.json` — the exact file a previous default-configuration measurement wrote. The scratch directory is gitignored (`.gitignore:241`), so the overwritten measurement data is unrecoverable. The README always shows `--out docs/benchmark-report.md`, but the footgun is one forgotten flag away and destroys the phase's core artifact.
**Fix:** In `main()`, when `args.render_report` is set, either require an explicit `--out` or change the effective default:

```python
if args.render_report:
    if not args.results:
        parser.error("--render-report requires --results ...")
    out = args.out if is_explicit_out else "docs/benchmark-report.md"
```

(Simplest: make `--out` default `None` and resolve per-mode: `DEFAULT_SCRATCH / "results.json"` for measurement, `docs/benchmark-report.md` for rendering; error if `None` reaches a writer.)

### WR-03: A typo'd or missing explicit `--input` silently degrades to a synthetic run

**File:** `scripts/bench/bench.py:357-383` (`resolve_mode`), with `gather_inputs` at 338-354
**Issue:** `resolve_mode(None, "/typo/path.fq.gz", env)` → `gather_inputs` returns `[]` → `return "synthetic", []` — a user who asked for real-data measurement gets a fast 200k-read synthetic run with only `results.json`'s `mode`/`resolved_inputs` fields betraying the substitution. The degradation ladder is the right design for *absent* input (env-driven, CI), but degrading an *explicitly provided* CLI path is the classic silent-fallback failure: an operator skimming stdout ("PARITY OK", arm lines, "results written to …") can easily mistake the synthetic run for the intended one. The docstring's "never guesses silently" is not true for this case.
**Fix:** Fail loudly when the CLI flag explicitly named an input that resolves to nothing; keep ladder degradation only for the absent/env-provided cases:

```python
def resolve_mode(explicit_mode, input_arg, env, size_threshold_bytes=..., strict_input=False):
    ...
    inputs = gather_inputs(spec) if spec else []
    if strict_input and input_arg is not None and not inputs:
        raise ValueError(
            f"--input {input_arg!r} resolved to no input files — refusing to "
            f"silently degrade to synthetic mode")
```

and pass `strict_input=True` from `main()`/`run_bench`/`run_parity_cli` where the argument came from the CLI.

### WR-04: `total_sequence_length` and `average_quality` bypass the compressed opener — `.fq.gz` parsed as raw deflate bytes

**File:** `src/io/fastq.rs:424-442` and `src/io/fastq.rs:451-486`
**Issue:** Both functions open `io::BufReader::new(std::fs::File::open(path))` directly instead of `DefaultCompressedFileReader::open_compressed`, so a `.fq.gz` path is parsed as compressed bytes — wrong values or hard parse errors. This is the identical bug class that was fixed in the FASTA twins (`src/io/fasta.rs` "WR-03 regression" test at fasta.rs:338-361 pins the fixed behavior there), and it is inconsistent with every other reader in the same file (`count_sequences`, `validate_fastq_file`, `process_file*` all route through `open_compressed`). Neither function currently has callers in the repo (verified by grep), which makes them dead public API carrying a latent gzip bug — whichever of "fix" or "delete" is chosen, leaving them half-migrated is the defect.
**Fix:** Route through the same opener (mirroring fasta.rs):

```rust
pub fn total_sequence_length<P: AsRef<Path>>(file_path: P) -> ProcessingResult<usize> {
    let path = file_path.as_ref();
    let (reader, _) = DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
        ProcessingError::with_context(
            format!("Failed to open FASTQ file: {:?} ({})", path,
                    CompressionType::from_path(path).name()), e)
    })?;
    let reader = Reader::new(reader);
    ...
```

(and likewise for `average_quality`), or remove both functions if the API is intentionally dead.

### WR-05: benchmark.yml cache key hashes a file that does not exist in CI (Cargo.lock is gitignored)

**File:** `.github/workflows/benchmark.yml:50-57`
**Issue:** `key: bench-${{ runner.os }}-cargo-${{ hashFiles('Cargo.lock') }}` — but `Cargo.lock` is untracked (verified: `git ls-files` has no entry; `.gitignore:7`/`.gitignore:117` ignore it), so after checkout `hashFiles('Cargo.lock')` evaluates to `''`. The key degenerates to the constant `bench-<os>-cargo-`: the first run saves under that exact key and every later run exact-hits it, so the cache is frozen forever — dependencies added afterwards are downloaded every run and never saved, and the comment's stated invariant ("runner OS + Cargo.lock hash", CR-04) is inoperative. (The same pattern pre-exists in ci.yml — newly replicated here.) Second-order concern for a *measurement* gate: with no committed lockfile, dependency resolution drifts over time, letting third-party crate updates shift wall/RSS past the 25%/15% thresholds with zero code change in this repo.
**Fix:** Commit `Cargo.lock` (best practice for a binary crate and a prerequisite for the key to function — it also pins the measurement environment), or if the lockfile must stay untracked, key on `hashFiles('**/Cargo.toml')`.

### WR-06: MultiGzDecoder hard-fails on trailing bytes after the last member — stricter than GzDecoder and than gzip itself

**File:** `src/io/fastq.rs:67-75` (change at 73)
**Issue:** The fix for concatenated members is correct and complete for its target (all read paths route through `open_compressed`; regression test is sound). But flate2's multi-member loop (verified in flate2-1.1.10 `src/gz/bufread.rs`, `GzState::Finished` + `self.multi` branch) does: after each member's CRC check, if `fill_buf()` is non-empty it parses another header, and any bytes that don't start `1f 8b` return `Err("invalid gzip header")`. Consequences: (a) files with trailing zero-padding — real for block-aligned archives and some transfer tools — previously read fine under `GzDecoder` (which stops at member end and ignores the rest) and now error the whole count; (b) GNU/BSD gzip themselves tolerate this ("decompression OK, trailing garbage ignored"). The prior behavior silently truncated member 2+; the new behavior hard-errors on trailing garbage — swapping under-count for spurious failure on a class of malformed-but-previously-working inputs. At minimum this asymmetry vs. the gzcat comparator arm deserves a decision; a parity run on such a file will fail loudly at the gate (RuntimeError, not a wrong number), which is the right failure mode but still a regression for previously-working inputs.
**Fix:** Decide and document the tolerance policy, e.g. wrap the decoder so that a bad-header error *after at least one successfully decoded member* is treated as EOF (mirroring gzip's trailing-garbage behavior), keeping the hard error for a bad *first* member. If strictness is intended, add a test pinning it and note it in the CLI error message so users with padded files get an actionable message.

### WR-07: NaN/Infinity medians pass the gate as "ok" — comparator fails open on non-finite data

**File:** `scripts/bench/compare.py:123-135` (`arm_median`), `compare.py:168-176` (breach decision); enabler `bench.py:279-309` (`validate_schema`)
**Issue:** `json.load` accepts `NaN`/`Infinity` literals by default, and `validate_schema` only checks key presence. For a NaN median: `base_v <= 0` is False (skips the non-positive guard at compare.py:170-173), `delta` is NaN, and `delta > threshold` is False — so the arm prints `delta nan% ok` and the gate **passes**. This violates the comparator's own stated contract ("a verdict on malformed data would be a fabricated verdict"; "fails loudly, never best-effort") — a corrupted or hand-mangled results file with a NaN wall/RSS sails through green instead of exiting 2.
**Fix:** Add a finiteness guard where the values enter the comparison:

```python
import math
...
    base_v = arm_median(base_arms[key], arm_field, rep_field)
    cur_v = arm_median(cur_arms[key], arm_field, rep_field)
    if not (math.isfinite(base_v) and math.isfinite(cur_v)):
        invalid(f"arm {name!r}: {arm_field} is non-finite "
                f"(baseline={base_v!r}, current={cur_v!r}) — not a gate verdict")
```

(and optionally reject non-finite values in `validate_schema`, protecting the renderer too).

## Info

### IN-01: Dead validation branch in gen_synthetic.py

**File:** `scripts/bench/gen_synthetic.py:47-50`
**Issue:** `if args.length < 1` is immediately subsumed by `if args.length < 2` (`--length` is `type=int`, so only integers arrive). The first check can never fire independently.
**Fix:** Delete the `< 1` check (or merge into one message: `--length must be >= 2 to contain at least one k-mer`).

### IN-02: bench.py exit-code contract is ambiguous at the edges

**File:** `scripts/bench/bench.py:1390-1390` (argparse), `bench.py:1486-1490` (catch-all)
**Issue:** (a) argparse usage errors exit 2, colliding with the documented `2 = jellyfish required but absent` contract (bench.py:484-486) — a wrapper distinguishing them cannot. (b) The `__main__` catch-all exits 1 for *any* runtime failure, the same code as `PARITY_MISMATCH_EXIT` — a parity mismatch and a harness crash are indistinguishable to callers. (c) `--render-report --parity-only` together silently does render-only (main's precedence at 1471-1479) with no mutual-exclusion error.
**Fix:** Distinct exit code for unexpected failures (e.g. 4) in the catch-all; note the argparse-2 collision in the docstring; `parser.error` when both mode flags are given.

### IN-03: Methodology schedule sorts round keys lexicographically

**File:** `scripts/bench/bench.py:1217-1219`
**Issue:** `sorted(sched.items())` orders the string keys "0","1","10","11","2"… — for any `--reps >= 10` the rendered counterbalance schedule lists rounds out of order (still deterministic, so byte-identity holds, but misleading to read).
**Fix:** `sorted(sched.items(), key=lambda kv: int(kv[0]))`.

### IN-04: Duplicate or tool-less arms collapse silently in compare.py's dict build

**File:** `scripts/bench/compare.py:147-148`; root cause `bench.py:279-309`
**Issue:** `validate_schema` does not require a `tool` field, and `arm_key` defaults it to `""`. Two arms with the same name (both lacking `tool`) silently overwrite each other in `{arm_key(a): a for a in baseline["arms"]}` — the gate then compares one of them instead of exiting 2, contrary to the one-sided-arm strictness elsewhere. (A tool-less arm vs a tooled arm does exit 2 loudly; only the silent-collapse path is the gap.)
**Fix:** In `compare_results`, detect duplicate keys while building the dicts and `invalid()` on them; optionally require `tool` in `validate_schema` (schema bump needed — coordinate with committed baselines).

### IN-05: test_schema.py's real-run test fails confusingly on a fresh clone

**File:** `scripts/bench/tests/test_schema.py:19,29-34`
**Issue:** `TestRealSelfCheckOutput` shells out to `target/release/rustkmer`; without a prior `cargo build --release` the test fails with a buried RuntimeError from bench.py instead of a skip, and the whole suite goes red for an environment reason.
**Fix:** `@unittest.skipUnless(RUSTKMER.exists(), "release binary not built — run cargo build --release")`.

### IN-06: No timeout on measured subprocesses

**File:** `scripts/bench/bench.py:144-150` (`measure`), likewise `stats`/`jellyfish_stats`
**Issue:** A hung rustkmer/jellyfish run hangs the harness forever; in CI the 45-minute job timeout eventually catches it, but a local full-scale run (hours by design) has no guard, and a hang mid-protocol loses all reps taken so far (nothing is written until the end).
**Fix:** Not urgent — optionally `subprocess.run(..., timeout=...)` derived from a generous multiple of the first rep, or at least write partial results after each round.

### IN-07: Leading-hyphen paths pass validate_path and reach argv positions where tools parse options

**File:** `scripts/bench/bench.py:157,186-198` (`SAFE_PATH_RE`, `validate_path`), consumed at 244 (list form) and 241-243 (sh -c)
**Issue:** The T-04-03 allowlist blocks shell metacharacters but permits a path starting with `-` (e.g. a dataset file literally named `-C.fq.gz`). In the plain-input branch it becomes a `jellyfish count` argument position; in the pipe branch a `gzcat`/`gunzip` argument position — option injection into the tool (loud failure in practice; no escalation path identified since the decompressor constant always forces `-c`/stdout). Defense-in-depth only.
**Fix:** Reject or neutralize leading-hyphen paths in `validate_path`: `if text.startswith("-"): raise ValueError(...)` (or prefix `./` for relative paths), mirroring the `--` convention.

---

_No structural findings block was provided by the orchestrator; no external reviewer evidence was supplied._

_Reviewed: 2026-10-10T19:04:26Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
