---
phase: "11"
slug: "merge-characterization-harness-prep"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-16"
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest discover (stdlib runner; harness tests in `scripts/bench/tests/`, unittest-style) + `cargo test` (Rust gates, untouched by this phase) |
| **Config file** | none — existing `scripts/bench/tests/` suite + harness self-checks |
| **Quick run command** | `python3 -m unittest discover -s scripts/bench/tests -t .` |
| **Full suite command** | `python3 -m unittest discover -s scripts/bench/tests -t .` && slice-scale dress rehearsal (`bench.py` slice protocol) |
| **Estimated runtime** | ~60 seconds (unit) / ~10–20 min (slice rehearsal) |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest discover -s scripts/bench/tests -t .`
- **After every plan wave:** Run full harness test suite + the phase's own protocol checks (schema validation, gate unit checks, renderer render test)
- **Before `/gsd-verify-work`:** Full suite must be green; dress rehearsal evidence present
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-02 T1+T2 | 11-02 | 1 | MBENCH-01 | T-11-03 | provenance integrity (sha256 + Total recorded per artifact) | unit | `python3 -m unittest discover -s scripts/bench/tests -t . -k test_prepare_inputs` | ❌ W0 | ⬜ pending |
| 11-04 T2 | 11-04 | 2 | MBENCH-02 | — | parity gate rejects conservation-only passes | unit | `python3 -m unittest discover -s scripts/bench/tests -t . -k test_merge_arms` | ❌ W0 | ⬜ pending |
| 11-01 T2+T3 | 11-01 | 1 | MBENCH-05 | — | no second results schema (schema_version unchanged) | unit | `python3 -m unittest discover -s scripts/bench/tests -t . -k test_schema` | ✅ | ⬜ pending |
| 11-03 T1+T2 | 11-03 | 1 | HYG-01 | T-11-07 | stale verdict no longer presented as current | source assertion | `grep` banner in `docs/benchmark-report.md` + drift grep script | ✅ (file exists) | ⬜ pending |
| 11-08 T1+T2 | 11-08 | 1 | HYG-02/03 | T-11-19 | validation records + SECURITY.md exist | source assertion | `ls` milestone archive targets | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/bench/tests/test_merge_arms.py` (or equivalent) — stubs for MBENCH-01/02 gate units
- [ ] Known-flake note: `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` is a pre-existing ~50% macOS `sample`-race flake (STATE.md) — not gate-blocking for this phase; purge stale `target/` artifacts before trusting a red result

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-protocol slice-scale dress rehearsal passes three-way parity gate | MBENCH-02 | Requires built binaries + jellyfish + slice data at runtime (minutes-scale live run) | Run the harness slice protocol; verify parity gate green + dump-vs-dump deep gate green before any timed round |
| Intermediate-scale characterization ladder (2 rungs, both tools) | (phase deliverable) | Live measurement runs on real data slices | Run ladder via harness; verify wall/output-size recorded per rung with provenance |
| Derived disk floor sanity | (D-10) | Arithmetic over measured artifact sizes + ladder extrapolation | Review derived floor vs measured sizes; `checkpoint:human-verify` on the value before full-scale builds |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
