---
phase: quick
plan: 261118-c2r
subsystem: build-configuration
tags: [pyo3, build-rs, link-args, macos, dynamic-lookup, cargo-lock, documentation]
requires:
  - pyo3-build-config 0.27.2 (already resolved in pyo3/Cargo.lock as pyo3's own build-dependency)
provides:
  - pyo3/build.rs emits the macOS extension-module link args via pyo3_build_config::add_extension_module_link_args()
  - pyo3/Cargo.toml [build-dependencies] pyo3-build-config = "0.27.2" (no new package in the graph)
  - pyo3/Cargo.lock gains exactly one dependency reference
  - The three documented locations no longer present the RUSTFLAGS export as required
affects: [backlog 999.1, Phase 03 UAT Test 22, pyo3 build recipe, CI pyo3 clippy job]
key-files:
  created: []
  modified:
    - pyo3/build.rs
    - pyo3/Cargo.toml
    - pyo3/Cargo.lock
    - docs/guides/pyo3-binding-readme.md
    - docs/getting-started/installation-advanced.md
    - pyo3/build_with_python.sh
decisions:
  - "Call add_extension_module_link_args() unconditionally, not behind the extension-module cargo feature: rustc-cdylib-link-arg only affects this crate's cdylib link step, and the documented manual build does not enable the feature, so gating would leave the targeted path unfixed"
  - "Declare the already-resolved pyo3-build-config 0.27.2 (not the removed 0.22 series) so the lockfile change is exactly one dependency reference with no package or version change"
  - "Keep the manual RUSTFLAGS value documented only as an explicitly-labelled fallback for older code trees lacking the build.rs call"
metrics:
  duration: 3min
  completed: 2026-11-18
status: complete
actuals:
  tokens: 924       # chars/4 over the realized diff (git diff HEAD~2 = 3,696 chars)
  tasks: 2
  commits: 2        # MEASURED: git rev-list --count 137461c..HEAD
plan_head_before: 137461c9920dd1ebbe73b117d39a5868637e6ab6
plan_head_after: 78b8542e5579fe87134833d97906231622dc902c
---

# Quick Task 261118-c2r: Emit the pyo3 extension-module link args from build.rs Summary

**`pyo3/build.rs` now calls `pyo3_build_config::add_extension_module_link_args()`, so a macOS extension-module build succeeds with `RUSTFLAGS` and `CARGO_ENCODED_RUSTFLAGS` unset — proving the `-undefined dynamic_lookup` cdylib link args are emitted automatically — and the three documented locations no longer present the manual export as required. 2 atomic commits over exactly the 6 planned files.**

## Performance

- **Duration:** 3 min (2026-11-18T00:47:45Z → 00:50:22Z)
- **Tasks:** 2/2
- **Files modified:** 6 (3 build/manifest, 3 documentation)
- **Commits:** 2 (one per task, explicit-path staging)

## Task Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Wire the link-arg emission and prove it end-to-end | `aaacda3` (fix) | pyo3/build.rs, pyo3/Cargo.toml, pyo3/Cargo.lock |
| 2 | Stop presenting the manual linker-flag export as required | `78b8542` (docs) | docs/guides/pyo3-binding-readme.md, docs/getting-started/installation-advanced.md, pyo3/build_with_python.sh |

## Verification Evidence

### Red baseline (reproduced at HEAD 137461c before any change)

Command (as planned, run with the dependency graph already compiled):

```
env -u RUSTFLAGS -u CARGO_ENCODED_RUSTFLAGS -u CONDA_PREFIX \
  PYO3_PYTHON="$(command -v python3)" \
  cargo build --manifest-path pyo3/Cargo.toml --features extension-module -vv
```

Measured: **exit 101**; `error: linking with 'cc' failed`; `Undefined symbols for architecture arm64:` beginning with `_PyBaseObject_Type` (also `_PyBool_Type`, `_Py_TYPE`, ...); **0** occurrences of `-C link-arg=-undefined`; **0** occurrences of `-C link-arg=dynamic_lookup`; `pyo3/target/debug/libpyrustkmer.dylib` absent.

### Green proof (Task 1 gate, exactly as written)

```
touch pyo3/build.rs pyo3/src/lib.rs && LOG=$(mktemp) && \
  env -u RUSTFLAGS -u CARGO_ENCODED_RUSTFLAGS -u CONDA_PREFIX \
  PYO3_PYTHON="$(command -v python3)" \
  cargo build --manifest-path pyo3/Cargo.toml --features extension-module --locked -vv > "$LOG" 2>&1 \
  && test "$(grep -cF -- '-C link-arg=-undefined' "$LOG")" -ge 1 \
  && test "$(grep -cF -- '-C link-arg=dynamic_lookup' "$LOG")" -ge 1
```

Measured: **rc=0**. The rustc invocation with `crate-name pyrustkmer`, `crate-type cdylib` carries both `link-arg=-undefined` and `link-arg=dynamic_lookup` (1 occurrence of each; the build script's own stdout line is `cargo:rustc-cdylib-link-arg=-undefined`, so only the intended cdylib link step is affected). `pyo3/target/debug/libpyrustkmer.dylib` (8,837,888 bytes) is produced.

### Task 1 gates (HEAD baselines beside them)

| Gate | Baseline (HEAD) | Measured after |
|------|-----------------|----------------|
| `grep -c 'add_extension_module_link_args' pyo3/build.rs` | 0 | **1** |
| `grep -c 'pyo3-build-config' pyo3/Cargo.toml` | 0 | **1** |
| `"pyo3-build-config"` refs in the rustkmer-pyo3 lock block | 0 | **1** |
| Link-arg occurrences in a `--locked` `-vv` build | 0 (exit 101 before link) | **1 + 1** (rc=0) |

### Exact pyo3/Cargo.lock delta

Exactly one added line, no removals, no package entry or version change:

```diff
@@ -1299,6 +1299,7 @@ dependencies = [
   "memmap2",
   "parking_lot",
   "pyo3",
+  "pyo3-build-config",
   "rayon",
   "rustkmer",
```

`git diff --numstat` for the lockfile: `1 0 pyo3/Cargo.lock`.

### pyo3/Cargo.toml delta (additions only)

```diff
+[build-dependencies]
+# Emits the macOS extension-module link args from build.rs (already in the lockfile via pyo3).
+pyo3-build-config = "0.27.2"
```

`git diff --numstat`: `4 0 pyo3/Cargo.toml`. The `pyo3 = { version = "0.27.2" }` dependency, the `extension-module = ["pyo3/extension-module"]` feature mapping, the `[package.metadata.maturin]` block, and the `[profile.release]` / `[profile.dev]` blocks are byte-identical to HEAD (the single hunk contains only added lines).

### Task 2 gates (HEAD baselines beside them)

| Gate | Baseline (HEAD) | Measured after |
|------|-----------------|----------------|
| `add_extension_module_link_args` in docs/guides/pyo3-binding-readme.md | 0 | **1** |
| `add_extension_module_link_args` in docs/getting-started/installation-advanced.md | 0 | **1** |
| `export RUSTFLAGS` across docs/ + pyo3/build_with_python.sh | 3 | **0** (`grep` rc=1, empty output) |

Both docs now name the automatic mechanism and keep the manual `-C link-arg=-undefined -C link-arg=dynamic_lookup` values only as an explicitly-labelled fallback for older trees; the legacy script carries the one-line automatic-emission comment and is otherwise unchanged.

### Plan-level verification

- **CI parity:** `env -u CONDA_PREFIX PYO3_PYTHON="$(command -v python3)" cargo clippy --manifest-path pyo3/Cargo.toml --locked --all-targets -- -D warnings` → **exit 0** (`Finished dev profile`).
- **Diff review:** `git diff HEAD~2 --stat` → exactly the 6 planned files, 18 insertions / 4 deletions; deleted lines exist only in the three documentation locations (the removed export plus the removed "设置正确的链接标志" comment).
- **Commit hygiene:** two atomic commits, each staging exactly its task's file set by explicit path; `git status --porcelain` shows only `?? .planning/quick/261118-c2r-.../` (orchestrator-owned docs artifacts, intentionally uncommitted); STATE.md / ROADMAP.md / BATCH.json untouched; `.claude/CLAUDE.md` never staged; no `git add -f`.
- **Changed-file scan:** no stubs, placeholders, or TODOs introduced; no security-relevant surface added (the build script only calls the documented API).

## Backlog Resolution

**Backlog 999.1 (Phase 03 UAT Test 22) is resolved.** The documented manual-build recipe is no longer broken as written: at HEAD the extension-module build failed (exit 101, undefined `_Py*` symbols), and after this change the same `--locked` build succeeds with `RUSTFLAGS` and `CARGO_ENCODED_RUSTFLAGS` unset while both link-arg flags appear on the rustkmer-pyo3 cdylib invocation. The orchestrator can close the ROADMAP entry.

## Decisions Made

- **Unconditional call.** `add_extension_module_link_args()` is called unconditionally rather than behind `CARGO_FEATURE_EXTENSION_MODULE`: the function does not consult the feature (it emits the Darwin flags unconditionally and is a no-op elsewhere), `rustc-cdylib-link-arg` applies only to this crate's cdylib link step, and the documented manual build (`cargo build` with no feature flag) is exactly the path the backlog targets. `use_pyo3_cfgs()` was deliberately not added (no `cfg(Py_*)` usage in `pyo3/src`).
- **Same-version build-dependency.** `pyo3-build-config = "0.27.2"` reuses the single copy already in `pyo3/Cargo.lock` (checksum `b4559331...`), so no package enters the graph and the lockfile delta stays at one line.
- **Docs as record-only correction.** The export line is removed from the recipe and the automatic mechanism is named; the manual values survive only as a labelled fallback for trees lacking the build.rs call.

## Deviations from Plan

None - plan executed exactly as written. All four Task 1 gates and all three Task 2 gates passed with the planned baseline-to-result transition; no auto-fixes were required.

## Known Stubs

None. The change is a build-script wiring addition plus documentation corrections; no placeholder or unwired data path was introduced.

## Threat Flags

None. No new runtime surface (no endpoints, auth paths, file access changes, or schema changes). The new build-dependency is the already-resolved `pyo3-build-config` 0.27.2, and all post-change cargo commands ran with `--locked`.

## Self-Check: PASSED

- All 6 changed files plus this SUMMARY are present on disk.
- Both task commits (`aaacda3`, `78b8542`) are ancestors of HEAD; measured `commits=2` between `plan_head_before=137461c` and `plan_head_after=78b8542`.
- Stub scan over the touched files: none.

---
*Quick task: 261118-c2r*
*Completed: 2026-11-18*
