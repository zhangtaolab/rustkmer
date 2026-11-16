---
phase: quick
plan: 261116-mjo
subsystem: docs
tags: [pyo3, python-bindings, false-positive, docs-verification, canonical]

# Dependency graph
requires:
  - phase: none
    provides: standalone verification-only quick task; consumes the 2026-11-16 docs-update flag and existing PyCounter/PyCounterStats bindings
provides:
  - Durable proof that docs/getting-started/first-steps.md:56 (`counter.canonical`) is correct as written — runtime probe, end-to-end doc sample, count gates, CI citations
  - Permanent two-getter map for future docs passes: PyCounter.canonical (bool) vs PyCounterStats.canonical_mode (bool)
affects: [docs-update passes touching first-steps.md, any rename review of pyo3/src/counter.rs getters]

# Actuals (#2632)
actuals:
  tokens: 2407        # chars/4 over .planning artifacts actually written (SUMMARY 8954 B + STATE.md diff ~675 B); no repo file changed
  tasks: 2
  commits: 0          # verification-only resolution — executor commits nothing; orchestrator owns the docs commit

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Verification-first quick task: probe runtime truth before applying a docs flag; an inverted premise voids the fix action"

key-files:
  created:
    - .planning/quick/261116-mjo-fix-docs-getting-started-first-steps-md-/261116-mjo-SUMMARY.md
  modified:
    - .planning/STATE.md  # Last activity line + Quick Tasks Completed row only

key-decisions:
  - "Flag on first-steps.md:56 resolved as FALSE POSITIVE — the flagged rename would inject AttributeError into a correct, CI-pinned doc line"
  - "No repo source/doc/test file modified; both .planning artifacts left uncommitted for the orchestrator (lhq precedent)"

patterns-established:
  - "Two-getter map: `PyCounter.canonical` (#[getter] fn canonical, pyo3/src/counter.rs:549-551) vs `PyCounterStats.canonical_mode` (#[getter] fn canonical_mode, pyo3/src/counter.rs:55-58, field at line 26) — get_stats() objects carry canonical_mode, PyCounter does not"

requirements-completed: []

# Metrics
duration: 3min
completed: 2026-11-16
status: complete
---

# Quick Task 261116-mjo: first-steps.md:56 canonical flag Summary

**Flag resolved as FALSE POSITIVE with recorded proof — `docs/getting-started/first-steps.md:56` keeps its correct, CI-pinned `counter.canonical` expression; the flagged `canonical_mode` rename exists only on `PyCounterStats` and raises AttributeError on `PyCounter`. No repo file changed.**

## Resolution Verdict

The 2026-11-16 docs-update flag claimed: *"code sample calls `counter.canonical` but PyCounter exposes `canonical_mode`"*. The premise is inverted:

- `counter` on line 54 is `PyCounter(21, canonical=True)` — a `PyCounter`.
- `PyCounter` exposes **`canonical`** (bool) via `#[getter] fn canonical(&self)` at `pyo3/src/counter.rs:549-551`.
- `PyCounter` does **NOT** expose `canonical_mode`: `hasattr(c, "canonical_mode")` is False and direct access raises `'builtins.PyCounter' object has no attribute 'canonical_mode'`.
- `canonical_mode` belongs to **`PyCounterStats`** — `#[getter] fn canonical_mode(&self)` at `pyo3/src/counter.rs:55-58`, backed by the `canonical_mode: bool` field at `pyo3/src/counter.rs:26` — reachable only through `counter.get_stats().canonical_mode`.
- Applying the requested rename would have injected the exact AttributeError the flag fears into a correct line and broken the CI-pinned tests listed below.

Applying the flagged fix was therefore prohibited (plan Task 1 HARD PROHIBITION); the honest deliverable is this recorded proof.

## Verification Evidence

All probes ran at HEAD `c55482daa24dfc97e52701695f3d59b03f4ba32a` on branch `dev`, working tree clean except the untracked quick-task planning directory.

### Probe 1 — Attribute truth (`.venv313/bin/python -I`, inline script)

```python
import pyrustkmer
c = pyrustkmer.PyCounter(21, canonical=True)
assert c.canonical is True                    # passed
assert not hasattr(c, 'canonical_mode')       # passed
assert c.get_stats().canonical_mode is True   # passed
```

Output (extended probe run for the record):

```text
module resolved: /Users/forrest/GitHub/rustkmer/.venv313/lib/python3.13/site-packages/pyrustkmer/__init__.py
AttributeError as expected: 'builtins.PyCounter' object has no attribute 'canonical_mode'
MJO-ATTR-TRUTH-OK
```

### Probe 2 — End-to-end doc sample (lines 50-69 behavior vs the doc's own sample.fa, lines 37-44)

Ran the doc's exact snippet in a `mktemp -d` scratch dir against the doc's two-record sample.fa; scratch dir removed after the run.

```text
kmer_length: 21
canonical: True
total_kmers: 106
unique_kmers: 24
MJO-SNIPPET-GREEN
```

Exit 0. Exact asserted counts: `kmer_length == 21`, `canonical is True`, `total_kmers == 106`, `unique_kmers == 24`.

### Probe 3 — Static count gates vs recorded HEAD baselines

| Gate | Expected [HEAD] | Observed | Result |
|------|-----------------|----------|--------|
| `grep -c 'counter\.canonical}' docs/getting-started/first-steps.md` | 1 | 1 | PASS |
| `grep -c 'fn canonical(&self)' pyo3/src/counter.rs` | 1 | 1 | PASS |
| `grep -c 'fn canonical_mode(&self)' pyo3/src/counter.rs` | 1 | 1 | PASS |
| `git status --porcelain` over doc + counter.rs + pyo3/tests | empty | empty | PASS |

Formal Task 1 verify block printed `MJO-T1-VERIFIED`.

### Probe 4 — CI citations pinning `counter.canonical` (read the cited lines live)

- `pyo3/tests/test_counter.py:51` — `assert counter.canonical == False`
- `pyo3/tests/test_counter.py:58` — `assert counter.canonical == True`
- `pyo3/tests/test_counter.py:65` — `assert counter.canonical == True`
- `pyo3/tests/test_counter.py:951-952` — `assert counter_true.canonical == True` / `assert counter_false.canonical == False`
- `pyo3/tests/test_counter_simple.py:20,25` — `assert counter.canonical == True` / `assert counter.canonical == False`
- `pyo3/tests/test_counter_simple.py:91-92` — `assert counter_true.canonical == True` / `assert counter_false.canonical == False`
- `pyo3/tests/test_public_api.py:48` — `assert pyrustkmer.PyCounter(21, canonical=True).canonical is True`

## Source-Truth Citations (the two-getter map)

| Object | Attribute | Source |
|--------|-----------|--------|
| `PyCounter` | `canonical: bool` | `#[getter] fn canonical(&self)` — `pyo3/src/counter.rs:549-551` |
| `PyCounterStats` (from `get_stats()`) | `canonical_mode: bool` | `#[getter] fn canonical_mode(&self)` — `pyo3/src/counter.rs:55-58`; field `pub canonical_mode: bool` at `pyo3/src/counter.rs:26` |

The likely origin of the recurring confusion: `get_stats()` objects DO carry `canonical_mode`, so a docs pass skimming getter names can mis-attribute it to `PyCounter`.

## Warning for Future Docs Passes

**The stats-only attribute name raises AttributeError on `PyCounter`.** `c.canonical_mode` on a `PyCounter` raises `'builtins.PyCounter' object has no attribute 'canonical_mode'`. A doc line printing the canonical flag off a `PyCounter` variable must use **`counter.canonical`** or **`counter.get_stats().canonical_mode`** — never bare `counter.canonical_mode`. Renaming the correct `.canonical` expression in `docs/getting-started/first-steps.md:56` would break the sample at runtime and the CI tests listed above.

## Accomplishments

- Flag closed as FALSE POSITIVE with runtime, end-to-end, static, and CI evidence — no repo change required or made.
- Permanent two-getter map recorded in this SUMMARY so the PyCounter/PyCounterStats confusion cannot recur.
- STATE.md updated: refreshed Last activity line + Quick Tasks Completed row (Commit cell is a literal em dash — no code commit exists for a verification-only resolution).

## Files Changed

| File | Change |
|------|--------|
| `.planning/quick/261116-mjo-fix-docs-getting-started-first-steps-md-/261116-mjo-SUMMARY.md` | Created (this file) |
| `.planning/STATE.md` | Last activity line replaced; quick-task row appended — nothing else touched |

**Repository source/doc/test files touched by the executor: NONE.** `docs/getting-started/first-steps.md`, `pyo3/src/counter.rs`, and `pyo3/tests` remain porcelain-clean; the flagged expression count stays at 1.

## Deviations from Plan

None - plan executed exactly as written.

## Commits

None by the executor, per plan contract: this is a verification-only resolution, and the plan (lhq precedent) leaves `261116-mjo-SUMMARY.md`, `261116-mjo-PLAN.md`, and `.planning/STATE.md` UNCOMMITTED for the orchestrator's docs commit.

## Self-Check: PASSED

- Probe markers: MJO-ATTR-TRUTH-OK and MJO-SNIPPET-GREEN both printed (captured above).
- Count gates 1 / 1 / 1 at HEAD baselines; doc + source + tests porcelain-clean.
- `261116-mjo-SUMMARY.md` exists in the quick directory with `status: complete` frontmatter.
- `.planning/STATE.md` carries the 261116-mjo quick-task row and the refreshed Last activity line.
- No repo file modified; no commit created by the executor (verified via `git status --porcelain` before handoff).
