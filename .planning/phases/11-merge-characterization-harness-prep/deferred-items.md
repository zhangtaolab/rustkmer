# Phase 11 — Deferred Items (out-of-scope discoveries)

Recorded during 11-01 execution per the executor scope-boundary rule:
pre-existing failures in files outside the plan's `files_modified` are
logged, never silently fixed or ignored.

| Category | Item | Found during | Detail | Status |
|----------|------|--------------|--------|--------|
| Pre-existing test breakage | `test_phase10_verdict.py` reads the archived Phase-10 path | 11-01 full-suite run | `TestCommittedHistoricalCliEvidence.test_each_historical_pin_matches_its_committed_copy` (k=21, k=31) and `TestCommittedPreflightArtifact.test_committed_preflight_revalidates_for_both_k` fail: they read `.planning/phases/10-benchmark-verdict/*.json`, but commit `97c497c` ("chore: archive v2.0 milestone files and reorganize roadmap", before 11-01) moved those artifacts to `.planning/milestones/v2.0-phases/10-benchmark-verdict/`. 3 tests red on the full `unittest discover` run. The 11-01 diff touches only `scripts/bench/bench.py` + 4 test modules — unrelated. | OPEN — path retarget needed (candidate for Phase 11 hygiene or a quick task) |
| Pre-existing flake | `test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` | 11-01 full-suite run | Reproduced during 11-01 (`requested=4 observed=0`); documented in STATE.md Blockers/Concerns as a ~50% macOS `sample`-race flake; purge stale `target/` artifacts before trusting a red result. Unrelated to the 11-01 diff. | OPEN (already tracked in STATE.md) |
| Docs drift, out of D-06 sweep breadth | `.claude/CLAUDE.md:17` (auto-generated CLAUDE.md) still mirrors the pre-correction PROJECT.md constraint line ("~5.2 GB gzipped r1 across split parts") | 11-03 D-06 sweep | D-06's locked sweep breadth is `docs/`, `README.md`, `USER_GUIDE.md`, `PROJECT_SUMMARY.md` + the two named artifacts (`docs/benchmark-report.md`, `.planning/PROJECT.md`); CLAUDE.md is auto-generated ("Auto-generated from all feature plans") and not in that breadth, so it was not hand-edited. The authoritative line in `.planning/PROJECT.md` (Constraints bullet) was corrected to six single-member parts ~16.7 GB in 11-03. Fix = CLAUDE.md regeneration (the generator that mirrors PROJECT.md), not a manual edit. | OPEN — regenerate CLAUDE.md at the next docs/generation touch |

Impact on the 11-01 CI-gate claim: the full-suite command
`python3 -m unittest discover -s scripts/bench/tests -t .` exits non-zero due
to the 4 pre-existing failures above; every module this plan created or
extended is green (test_merge_arms 11, test_schema 19, test_render_report 24,
test_degradation 70), and the remaining ~464 tests are unaffected.
