---
schema_version: 1
open_count: 11
waived_count: 3
fixed_count: 5
total_count: 19
last_updated: 2026-10-09T05:23:31.385Z
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
| 6 | 03 | stub | src/database/format.rs |  | No stubs left | fixed | Not a defect — recorded as a status note. Plan 03-07 introduced no stubs: every assertion is wired to live production code, and no #[ignore] attribute was added. | 2026-10-07T12:29:50.679Z | 2026-10-07T12:55:00.000Z |
| 7 | 03 | deviation | src/database/streaming_merge.rs |  | EOF at a run refill is the normal end of a run, not damage; truncation is caught by a len % RECORD_SIZE check in merge_sorted_chunks | fixed | Duplicate of id 10 (two appends raced). Closed in plan 03-07: the EOF-vs-truncation distinction is implemented and covered by chunk_truncated_mid_record_is_reported_not_silently_dropped and chunk_record_count_that_is_a_whole_multiple_of_record_size_still_merges, both green. | 2026-10-07T12:29:50.953Z | 2026-10-07T12:55:00.000Z |
| 8 | 03 | deviation | tests/merge_route_parity_tests.rs |  | Route parity asserted on decoded maps plus an exact count, because 16_777_216 was wrong on BOTH routes and equality alone stayed green | fixed | Closed in plan 03-07: route parity is asserted on decoded (String,u32) maps PLUS an exact expected count, because 16_777_216 was wrong on BOTH routes. Both arms green; both observed RED against the pre-fix reader. | 2026-10-07T12:29:51.192Z | 2026-10-07T12:55:00.000Z |
| 9 | 03 | deviation | .planning/phases/03-memory-safety/03-07-SUMMARY.md |  | Plan criterion grep -c 1_000_000 expecting 2 is unsatisfiable alongside step 10; reported as 3 with a discriminating '> 1_000_000' gate added | fixed | Plan-gate bookkeeping only — the code is as the plan intended. A discriminating gate (grep for the '> 1_000_000' comparison, 1 -> 0) was added and the measurement reported in the SUMMARY. | 2026-10-07T12:29:51.438Z | 2026-10-07T12:55:00.000Z |
| 10 | 03 | deviation | src/database/streaming_merge.rs |  | EOF at a run refill is the normal end of a run, not damage; truncation is caught by a len % RECORD_SIZE check in merge_sorted_chunks | fixed | Closed in plan 03-07: EOF at a run refill is the normal end of a run; mid-record truncation is caught by a len % RECORD_SIZE check in merge_sorted_chunks, with RECORD_SIZE pinned against a real encode. | 2026-10-07T12:29:54.509Z | 2026-10-07T12:55:00.000Z |
| 11 | 03 | unrun-verify | pyo3/tests/test_database_merge.py |  | 03-09's Python half could not be EXECUTED: pyo3/pyproject.toml sets python-source="." with module-name="pyrustkmer" while pyo3/pyrustkmer/ has never existed, so maturin build/develop both refuse; and addopts hard-codes --cov-fail-under=80 against a compiled extension, so every pytest run exits 1. test_python_budget_model_tracks_the_core and the BYTES_PER_KMER_ESTIMATE 24->96 repair are grep-verified and arithmetically verified (extension-free) only. | open |  | 2026-10-07T12:52:42.303Z |  |
| 12 | 03 | deviation | src/database/format.rs |  | 03-09 Deviation: the plan's literal 'grep -c db_refs' gate reads 2, not 0 — both remaining occurrences are a test local for the unrelated validate_compatibility(&[&RKDatabase]) path. Renaming it to satisfy a grep would make the gate green without making the property truer, so the measurement is reported and a discriminating gate (no from_file_path and no Vec<RKDatabase> inside merge_databases_prefix_cache) is used instead. | open |  | 2026-10-07T12:52:47.081Z |  |
| 13 | 03 | deviation | src/database/format.rs |  | 03-09 Deviation: the plan's literal 'grep -c saturating_add(total)' gate is unsatisfiable — the saturating fold is written \|total, count\| total.saturating_add(count), which cannot contain that substring. Reported as 0 with the discriminating evidence being the RED-observed unit test summing_two_near_max_headers_saturates_instead_of_panicking (pre-fix: 'attempt to add with overflow'). | open |  | 2026-10-07T12:52:47.343Z |  |
| 14 | 03 | deviation | src/database/format.rs |  | WR-02 deferred by design: resolve_merge_route's use_prefix_cache arm returns above the D-02 rejection; merge_mode='memory' under --use-prefix-cache warns but is never rejected — needs its own behaviour-change decision | open |  | 2026-10-08T15:02:14.517Z |  |
| 15 | 03 | unrun-verify | pyo3/src/database.rs | 1457 | MERGE-04 residual: PyDatabase::merge no longer emits 'Failed to save merged database to {}' (save folded into merge); no Python-level assertion covers the semantic change because installed pyrustkmer.so is prebuilt | open |  | 2026-10-08T15:02:29.985Z |  |
| 16 | 03 | unrun-verify | pyo3/src/database.rs | 1457 | Plan 03-12: PyDatabase.merge now rejects cross-input k-mer-size/canonical mismatches (CR-03 fix) via inheritance through merge_databases_to_path -> merge_prologue with zero pyo3 edits; the PyRuntimeError manifestation is verified by call-graph inspection and pyo3 clippy compile only, not pytest — the maturin python-source blocker (WINDOWS.md entries 4/5/11) makes every pyo3 pytest run impossible this phase | open |  | 2026-10-08T17:09:14.524Z |  |
| 17 | 03 | unmet-truth | src/database/prefix_cache_merge.rs | 800 | merge_single_prefix_streaming assumes ascending shard runs; post-03-16 a non-canonical input's shard under a mixed-canonical merge can be non-ascending, so mixed-canonical output is only proven correct on the auto/hashmap path (merge_mode=streaming or >threshold buckets still wrong) | open |  | 2026-10-09T05:23:24.392Z |  |
| 18 | 03 | lint-warning | src/cli/commands/count.rs |  | cargo fmt --check fails on 4 phase-03-untouched files (21 hunks: count.rs, merge_bounded_memory_tests.rs, merge_cleanup_tests.rs, parallel_count_tests.rs) - pre-existing rustfmt version drift; all 03-16 touched files fmt-clean | open |  | 2026-10-09T05:23:24.458Z |  |

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
  },
  {
    "id": 6,
    "kind": "stub",
    "phase": "03",
    "file": "src/database/format.rs",
    "line": null,
    "description": "No stubs left",
    "status": "fixed",
    "reason": "Not a defect — recorded as a status note. Plan 03-07 introduced no stubs: every assertion is wired to live production code, and no #[ignore] attribute was added.",
    "recorded_at": "2026-10-07T12:29:50.679Z",
    "resolved_at": "2026-10-07T12:55:00.000Z",
    "milestone": "v1.0"
  },
  {
    "id": 7,
    "kind": "deviation",
    "phase": "03",
    "file": "src/database/streaming_merge.rs",
    "line": null,
    "description": "EOF at a run refill is the normal end of a run, not damage; truncation is caught by a len % RECORD_SIZE check in merge_sorted_chunks",
    "status": "fixed",
    "reason": "Duplicate of id 10 (two appends raced). Closed in plan 03-07: the EOF-vs-truncation distinction is implemented and covered by chunk_truncated_mid_record_is_reported_not_silently_dropped and chunk_record_count_that_is_a_whole_multiple_of_record_size_still_merges, both green.",
    "recorded_at": "2026-10-07T12:29:50.953Z",
    "resolved_at": "2026-10-07T12:55:00.000Z",
    "milestone": "v1.0"
  },
  {
    "id": 8,
    "kind": "deviation",
    "phase": "03",
    "file": "tests/merge_route_parity_tests.rs",
    "line": null,
    "description": "Route parity asserted on decoded maps plus an exact count, because 16_777_216 was wrong on BOTH routes and equality alone stayed green",
    "status": "fixed",
    "reason": "Closed in plan 03-07: route parity is asserted on decoded (String,u32) maps PLUS an exact expected count, because 16_777_216 was wrong on BOTH routes. Both arms green; both observed RED against the pre-fix reader.",
    "recorded_at": "2026-10-07T12:29:51.192Z",
    "resolved_at": "2026-10-07T12:55:00.000Z",
    "milestone": "v1.0"
  },
  {
    "id": 9,
    "kind": "deviation",
    "phase": "03",
    "file": ".planning/phases/03-memory-safety/03-07-SUMMARY.md",
    "line": null,
    "description": "Plan criterion grep -c 1_000_000 expecting 2 is unsatisfiable alongside step 10; reported as 3 with a discriminating '> 1_000_000' gate added",
    "status": "fixed",
    "reason": "Plan-gate bookkeeping only — the code is as the plan intended. A discriminating gate (grep for the '> 1_000_000' comparison, 1 -> 0) was added and the measurement reported in the SUMMARY.",
    "recorded_at": "2026-10-07T12:29:51.438Z",
    "resolved_at": "2026-10-07T12:55:00.000Z",
    "milestone": "v1.0"
  },
  {
    "id": 10,
    "kind": "deviation",
    "phase": "03",
    "file": "src/database/streaming_merge.rs",
    "line": null,
    "description": "EOF at a run refill is the normal end of a run, not damage; truncation is caught by a len % RECORD_SIZE check in merge_sorted_chunks",
    "status": "fixed",
    "reason": "Closed in plan 03-07: EOF at a run refill is the normal end of a run; mid-record truncation is caught by a len % RECORD_SIZE check in merge_sorted_chunks, with RECORD_SIZE pinned against a real encode.",
    "recorded_at": "2026-10-07T12:29:54.509Z",
    "resolved_at": "2026-10-07T12:55:00.000Z",
    "milestone": "v1.0"
  },
  {
    "id": 11,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "pyo3/tests/test_database_merge.py",
    "line": null,
    "description": "03-09's Python half could not be EXECUTED: pyo3/pyproject.toml sets python-source=\".\" with module-name=\"pyrustkmer\" while pyo3/pyrustkmer/ has never existed, so maturin build/develop both refuse; and addopts hard-codes --cov-fail-under=80 against a compiled extension, so every pytest run exits 1. test_python_budget_model_tracks_the_core and the BYTES_PER_KMER_ESTIMATE 24->96 repair are grep-verified and arithmetically verified (extension-free) only.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-07T12:52:42.303Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 12,
    "kind": "deviation",
    "phase": "03",
    "file": "src/database/format.rs",
    "line": null,
    "description": "03-09 Deviation: the plan's literal 'grep -c db_refs' gate reads 2, not 0 — both remaining occurrences are a test local for the unrelated validate_compatibility(&[&RKDatabase]) path. Renaming it to satisfy a grep would make the gate green without making the property truer, so the measurement is reported and a discriminating gate (no from_file_path and no Vec<RKDatabase> inside merge_databases_prefix_cache) is used instead.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-07T12:52:47.081Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 13,
    "kind": "deviation",
    "phase": "03",
    "file": "src/database/format.rs",
    "line": null,
    "description": "03-09 Deviation: the plan's literal 'grep -c saturating_add(total)' gate is unsatisfiable — the saturating fold is written |total, count| total.saturating_add(count), which cannot contain that substring. Reported as 0 with the discriminating evidence being the RED-observed unit test summing_two_near_max_headers_saturates_instead_of_panicking (pre-fix: 'attempt to add with overflow').",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-07T12:52:47.343Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 14,
    "kind": "deviation",
    "phase": "03",
    "file": "src/database/format.rs",
    "line": null,
    "description": "WR-02 deferred by design: resolve_merge_route's use_prefix_cache arm returns above the D-02 rejection; merge_mode='memory' under --use-prefix-cache warns but is never rejected — needs its own behaviour-change decision",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-08T15:02:14.517Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 15,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "pyo3/src/database.rs",
    "line": 1457,
    "description": "MERGE-04 residual: PyDatabase::merge no longer emits 'Failed to save merged database to {}' (save folded into merge); no Python-level assertion covers the semantic change because installed pyrustkmer.so is prebuilt",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-08T15:02:29.985Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 16,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "pyo3/src/database.rs",
    "line": 1457,
    "description": "Plan 03-12: PyDatabase.merge now rejects cross-input k-mer-size/canonical mismatches (CR-03 fix) via inheritance through merge_databases_to_path -> merge_prologue with zero pyo3 edits; the PyRuntimeError manifestation is verified by call-graph inspection and pyo3 clippy compile only, not pytest — the maturin python-source blocker (WINDOWS.md entries 4/5/11) makes every pyo3 pytest run impossible this phase",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-08T17:09:14.524Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 17,
    "kind": "unmet-truth",
    "phase": "03",
    "file": "src/database/prefix_cache_merge.rs",
    "line": 800,
    "description": "merge_single_prefix_streaming assumes ascending shard runs; post-03-16 a non-canonical input's shard under a mixed-canonical merge can be non-ascending, so mixed-canonical output is only proven correct on the auto/hashmap path (merge_mode=streaming or >threshold buckets still wrong)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-09T05:23:24.392Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 18,
    "kind": "lint-warning",
    "phase": "03",
    "file": "src/cli/commands/count.rs",
    "line": null,
    "description": "cargo fmt --check fails on 4 phase-03-untouched files (21 hunks: count.rs, merge_bounded_memory_tests.rs, merge_cleanup_tests.rs, parallel_count_tests.rs) - pre-existing rustfmt version drift; all 03-16 touched files fmt-clean",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-09T05:23:24.458Z",
    "resolved_at": null,
    "milestone": "v1.0"
  }
]
````
