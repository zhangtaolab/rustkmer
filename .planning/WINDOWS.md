---
schema_version: 1
open_count: 2
waived_count: 3
fixed_count: 0
total_count: 5
last_updated: 2026-10-07T03:52:57.731Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 03 | stub | tests/dense_merge_integration_tests.rs |  | No open stubs: 3/3 tests GREEN, 0 ignored; verified non-vacuous by 3 mutation runs | waived | Not a defect. Recorded as a status note; tests/dense_merge_integration_tests.rs has 3/3 GREEN tests and 0 #[ignore] attributes. Nothing to block /gsd-ship on. | 2026-10-07T03:08:46.680Z | 2026-10-07T03:09:00.608Z |
| 2 | 03 | deviation | tests/merge_routing_tests.rs |  | Plan 03-04 AC1 literal grep '#[ignore]' matches 3 doc-comment prose lines, not attributes; all 5 phase-3 files have zero #[ignore] attributes | waived | Not an open defect: all 5 phase-3 test files have ZERO #[ignore] attributes (attribute-shaped grep returns no matches; each binary reports 0 ignored). The 3 literal-grep hits are doc-comment prose describing Wave-0 history. Fully documented in .planning/phases/03-memory-safety/deferred-items.md so /gsd-verify-work classifies them as closed. | 2026-10-07T03:08:46.961Z | 2026-10-07T03:09:00.973Z |
| 3 | 03 | deviation | tests/merge_routing_tests.rs |  | probe | waived | Junk entry from a tooling probe; carries no defect. Removed from consideration by waiving rather than leaving it blocking the ship gate. | 2026-10-07T03:08:49.330Z | 2026-10-07T03:09:00.781Z |
| 4 | 03 | unrun-verify | pyo3/pyproject.toml |  | Plan 03-05 verify command 'maturin develop --release' cannot run: python-source='.' with module-name='pyrustkmer' but pyo3/pyrustkmer/ has never existed, so maturin refuses both develop and build (CI's pyo3-build job runs maturin build) | open |  | 2026-10-07T03:52:54.821Z |  |
| 5 | 03 | deviation | pyo3/pyproject.toml |  | pyo3 pytest addopts hard-codes --cov=pyrustkmer --cov-fail-under=80, so every pyo3 pytest run exits 1 even when all tests pass (compiled extension reports 0% coverage); 03-05 ran pytest with -o addopts="". CI has no pyo3 pytest job at all | open |  | 2026-10-07T03:52:57.731Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "03",
    "file": "tests/dense_merge_integration_tests.rs",
    "line": null,
    "description": "No open stubs: 3/3 tests GREEN, 0 ignored; verified non-vacuous by 3 mutation runs",
    "status": "waived",
    "reason": "Not a defect. Recorded as a status note; tests/dense_merge_integration_tests.rs has 3/3 GREEN tests and 0 #[ignore] attributes. Nothing to block /gsd-ship on.",
    "recorded_at": "2026-10-07T03:08:46.680Z",
    "resolved_at": "2026-10-07T03:09:00.608Z",
    "milestone": "v1.0"
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "03",
    "file": "tests/merge_routing_tests.rs",
    "line": null,
    "description": "Plan 03-04 AC1 literal grep '#[ignore]' matches 3 doc-comment prose lines, not attributes; all 5 phase-3 files have zero #[ignore] attributes",
    "status": "waived",
    "reason": "Not an open defect: all 5 phase-3 test files have ZERO #[ignore] attributes (attribute-shaped grep returns no matches; each binary reports 0 ignored). The 3 literal-grep hits are doc-comment prose describing Wave-0 history. Fully documented in .planning/phases/03-memory-safety/deferred-items.md so /gsd-verify-work classifies them as closed.",
    "recorded_at": "2026-10-07T03:08:46.961Z",
    "resolved_at": "2026-10-07T03:09:00.973Z",
    "milestone": "v1.0"
  },
  {
    "id": 3,
    "kind": "deviation",
    "phase": "03",
    "file": "tests/merge_routing_tests.rs",
    "line": null,
    "description": "probe",
    "status": "waived",
    "reason": "Junk entry from a tooling probe; carries no defect. Removed from consideration by waiving rather than leaving it blocking the ship gate.",
    "recorded_at": "2026-10-07T03:08:49.330Z",
    "resolved_at": "2026-10-07T03:09:00.781Z",
    "milestone": "v1.0"
  },
  {
    "id": 4,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "pyo3/pyproject.toml",
    "line": null,
    "description": "Plan 03-05 verify command 'maturin develop --release' cannot run: python-source='.' with module-name='pyrustkmer' but pyo3/pyrustkmer/ has never existed, so maturin refuses both develop and build (CI's pyo3-build job runs maturin build)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-07T03:52:54.821Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 5,
    "kind": "deviation",
    "phase": "03",
    "file": "pyo3/pyproject.toml",
    "line": null,
    "description": "pyo3 pytest addopts hard-codes --cov=pyrustkmer --cov-fail-under=80, so every pyo3 pytest run exits 1 even when all tests pass (compiled extension reports 0% coverage); 03-05 ran pytest with -o addopts=\"\". CI has no pyo3 pytest job at all",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-07T03:52:57.731Z",
    "resolved_at": null,
    "milestone": "v1.0"
  }
]
````
