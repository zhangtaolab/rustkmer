---
phase: "08"
slug: "output-pipeline-rkdb-v2-parity"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-16"
validated: "2026-11-16"
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Reconstructed post-execution** (validate-phase State B, 2026-11-16): the phase executed 2026-11-12 without a seeded VALIDATION.md; this record was audited from the archived artifacts (4 PLANs, 4 SUMMARYs, `08-VERIFICATION.md` initial verification 2026-11-12 at 16/16 passed) and the test files on disk. It closes the v2.0 milestone-audit Nyquist coverage gap (HYG-02).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test` (integration + `proptest` 1.5) + Python stdlib `unittest` (`scripts/bench/tests/`) |
| **Config file** | `Cargo.toml` (root) |
| **Quick run command** | `cargo test --locked --test output_pipeline_tests --test output_differential_matrix_tests --test rkdb_v2_byte_identity_tests` |
| **Full suite command** | `cargo test --locked` + `python3 -m unittest discover -s scripts/bench/tests -t .` |
| **Harness gates** | `scripts/bench/output_stage.py` (pre/post output-stage compare vs the immutable captured baseline; verdict GREEN/RED, exit 0/1); `scripts/bench/mutation_red.py run` (injects ordering/duplication/overflow defects, expects gates RED, restores, re-verifies blobs) |
| **Estimated runtime** | quick suites ~2-4 min; output-stage compare minutes (slice-scale); full suite ~5-8 min |

---

## Sampling Rate

- **After every task commit:** the touched Rust suite (`output_pipeline_tests` / `output_differential_matrix_tests` / `rkdb_v2_byte_identity_tests`) + `unittest ... -k test_output_stage` / `-k test_mutation_red` when harness files changed
- **After every plan wave:** full locked suite + harness unittest discovery + golden fixture rehash check
- **Before `/gsd-verify-work`:** full suite green; mutation-verdict GREEN (all defects RED then restored); output-stage compare GREEN vs baseline
- **Max feedback latency:** ~8 minutes

---

## Per-Task Verification Map

Reconstructed 2026-11-16 from plan frontmatter declarations and `08-VERIFICATION.md` (verified 2026-11-12, 16/16 truths, digest `ba3a2f99…`; several gates re-executed during verification).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-* | 01 | 1 | OUT-02 | — | Pre-change output-stage baseline captured from the untouched tree (provenance, pinned fingerprint, counts, sha256) | integration (dev host) | `scripts/bench/output_stage.py capture` | ✅ `tests/test_output_stage.py` | ✅ green (`pre/phase8_output_stage_pre.json`: binary `d107d17e…`, HEAD `4d53102`, counts 229,694,874/519,271,168, sha `0976f29c…`) |
| 08-01-* | 01 | 1 | OUT-01, OUT-02, OUT-03 | — | Sorted output = rayon in-place parallel unstable sort + streaming frozen writer; no `get_all_counts` materialization; numeric key order == decoded order for k 1..=64 | unit/integration | `cargo test --locked --test output_pipeline_tests` | ✅ | ✅ green (truths 1-2) |
| 08-02-* | 02 | 1 | OUT-01, OUT-02, OUT-03 | — | 12-cell old-vs-new matrix (k×canonical×t{1,4}) in text and binary; old frozen-writer bytes equal new bytes per cell; t1==t4 | differential | `cargo test --locked --test output_differential_matrix_tests` | ✅ | ✅ green (truths 5, 6, 11: six sorted cells reproduce committed goldens + hand-built byte reference; unsorted cells carry same record multiset) |
| 08-02-* | 02 | 1 | OUT-03 | — | `DatabaseQuery` binary search (disk + preload) answers oracle keys; unsorted disk refused; prefix query returns exact oracle subset with contiguous block bounds | integration | `cargo test --locked --test output_pipeline_tests` (query/prefix cases) | ✅ | ✅ green (truths 7-8: named "Cannot query unsorted database…" error path exercised) |
| 08-02-* | 02 | 1 | OUT-03 | — | 42-byte header literals frozen byte-by-byte; IN-03 meanings preserved (header `total_kmers` = record count ≠ sum of counts) | unit | `cargo test --locked --test rkdb_v2_byte_identity_tests` (`header_bytes_match_the_frozen_v2_literals`) | ✅ | ✅ green (truth 9: 20 records vs 279 sum on the golden cell) |
| 08-03-* | 03 | 1 | OUT-01 | — | Post-change output stage GREEN vs immutable baseline (strictly lower sorted wall, delta ≤ 0.5×, same sha, RSS not regressed) | e2e (slice scale) | `python3 scripts/bench/output_stage.py compare` | ✅ | ✅ green (re-executed at verification: sorted 10.37 s vs 18.73 s, delta 1.60 ≤ 0.5×8.91, sha match 3/3 reps, verdict GREEN exit 0 — truth 4) |
| 08-03-* | 03 | 1 | OUT-01 | — | Slice t1/t4/t16 below Phase 7 values with pinned counts; all three slice `.rkdb` hash to `0976f29c…` | e2e (slice scale) | `python3 scripts/bench/thread_scaling.py --measure-only` | ✅ | ✅ green (re-executed: 31.83/10.27/9.12 s vs Phase 7 36.92/17.76/23.83 s; three DBs hash-identical — truth 14) |
| 08-04-* | 04 | 1 | OUT-02, OUT-03 | — | Mutation gate: injected ordering/duplication/overflow defects observed RED, then restored and re-greened with blob verification | negative-control | `python3 scripts/bench/mutation_red.py run` | ✅ `tests/test_mutation_red.py` | ✅ green (re-executed at verification: 3/3 + 2/2 + 1/1 gates RED, every `expect_substring_seen=true`, `restored_blob_matches=true`, `MUTATION VERDICT result=GREEN`, `git status` clean — truth 13) |
| 08-04-* | 04 | 1 | OUT-02 | — | Disjointness + conservation at the output boundary (visit-once, pair count == unique, sum == total, strict ascending, run-to-run identity) | property | `cargo test --locked --test output_differential_matrix_tests` (`proptest_output_boundary_disjointness_and_conservation`) | ✅ | ✅ green (truth 12: 12 cases pass; `count_engine_tests` 20/20) |
| — | — | — | OUT-01..03 (standing) | — | Single frozen `format.rs` writer (blob unchanged from phase base); no gate softened; fixtures/baselines/evidence untouched | gate | `git hash-object src/database/format.rs`; grep workflows for softeners | ✅ | ✅ green (truths 10, 15, 16: blob `eb0d5bf2…`; zero silencers; MSRV clippy + full suites green) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/output_pipeline_tests.rs` — sort ordering, streaming writers, query/prefix oracle cases, header literals
- [x] `tests/output_differential_matrix_tests.rs` — 12-cell old-vs-new matrix, unsorted multiset, boundary conservation proptest
- [x] `tests/rkdb_v2_byte_identity_tests.rs` — 8 byte-identity tests incl. hand-built byte-reference arm
- [x] `scripts/bench/output_stage.py` + `tests/test_output_stage.py` — capture/compare stage with immutable baseline
- [x] `scripts/bench/mutation_red.py` + `tests/test_mutation_red.py` — negative-control mutation harness
- [x] Evidence/fixtures beside archived artifacts: `phase8_gates_evidence.json`, `phase8_mutation_red.json`, `08-mutation-spec.json`, `pre/` + `post/` stage baselines, 12 golden fixtures (unmodified, manifest `f010e42a…`)
- [x] No framework install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Outcome |
|----------|-------------|------------|-------------------|---------|
| Slice-scale output-stage capture/compare and thread-scaling measurement | OUT-01 | Requires the local CRR1936095 slice (~4M reads) and release binary; CI runs synthetic-only gates | `output_stage.py capture` / `compare`; `thread_scaling.py --measure-only` | **DONE 2026-11-12** (capture) and **re-executed 2026-11-12 at verification** (compare GREEN, measure-only GREEN — truths 4, 14) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none remained at phase close)
- [x] No watch-mode flags
- [x] Feedback latency < 8 min
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-16 — reconstructed from archived artifacts; grounding: `08-VERIFICATION.md` initial verification 2026-11-12 (16/16 truths, 0 behavior-unverified, digest `ba3a2f99…`, three slice-scale gates re-executed during verification), test files verified present at HEAD, per-plan requirement frontmatter greps consistent with the report.

## Validation Audit 2026-11-16

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
