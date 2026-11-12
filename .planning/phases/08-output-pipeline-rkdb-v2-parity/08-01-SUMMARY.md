---
phase: 08-output-pipeline-rkdb-v2-parity
plan: 01
subsystem: output-pipeline
tags: [rust, k-mer-counting, parallel-sort, streaming-write, byte-identity, output-stage-measurement, out-01]

requires:
  - phase: 07-shared-counting-engine
    provides: "CountEngine/CountResult disjoint partition tables, producer-bound count phase (~6.4 s at t4), pinned slice counts 229,694,874/519,271,168, and the sorted .rkdb sha256 0976f29c…"

provides:
  - "Consuming pair collection: LocalKmerCounts::into_pairs_into and CountResult::into_filtered_pairs; each partition table released as it drains, one sort buffer, no second full copy"
  - "In-place rayon par_sort_unstable_by (pdqsort) shared by the .rkdb and text writers; sorted output streamed one record at a time through the frozen format.rs header/entry writers"
  - "Numeric-key text output with a deterministic k 1..=64 order-equivalence proof and an inverted-order control"
  - "scripts/bench/output_stage.py capture/compare gate + 29 stdlib unit tests + the immutable pre-change baseline pre/phase8_output_stage_pre.json"
  - "Measured post-change stage: sorted 18.73 s -> 10.43 s, sort delta 8.91 s -> 1.71 s, sorted .rkdb sha256 unchanged, sorted RSS 17.97 GB -> 12.04 GB, verdict GREEN"

affects: [08-02, 08-03, 08-04, 10]

actuals:
  tokens: 21053
  tasks: 3
  commits: 3
  plan_head_before: 4d53102a66befe15317b538b9bc66a3a8da22dae
  plan_head_after: b6109a8461b7d90fe93297f6b8297f89d4f36a28

tech-stack:
  added: []
  patterns:
    - "Consuming collection releases each partition table as it drains — the pair buffer is the ONE sort buffer"
    - "rayon par_sort_unstable_by (pdqsort, in place) instead of the merge-sort family, whose slice-sized temporary buffer would raise peak RSS"
    - "Streaming the sorted slice through the frozen DatabaseHeader/KmerEntry writers with an explicit flush mapped to FileWriteError"
    - "Output-stage gate: parity before timing, counterbalanced rotation, per-rep cache_state/round/arm_order, raw unclamped delta, byte identity + pinned counts + pinned slice sha"

key-files:
  created:
    - scripts/bench/output_stage.py
    - scripts/bench/tests/test_output_stage.py
    - tests/output_pipeline_tests.rs
    - .planning/phases/08-output-pipeline-rkdb-v2-parity/pre/phase8_output_stage_pre.json
  modified:
    - src/hash/local.rs
    - src/count/engine.rs
    - src/cli/commands/count.rs

key-decisions:
  - "The pre-change baseline was captured from the untouched tree (binary sha d107d17e…, HEAD 4d53102) before any src edit; git_dirty is true only because the new harness files were untracked at capture time — the binary sha and HEAD pin the measured artifact"
  - "The sorted arm's baseline CV is 11.66% (third rep 22.42 s); the median is kept and cv_warning is recorded rather than discarding a rep or softening the number"
  - "The pair buffer is the single sort buffer and each table dies as it drains, so peak RSS cannot exceed the pre-change peak; measured post sorted RSS is 12.04 GB vs 17.97 GB pre"
  - "Text output sorts by numeric encoded key; decoded-string order is the same permutation because A<C<G<T maps to 0<1<2<3 by significance — proven for every k in 1..=64"
  - "The post-change compare ran to /tmp (08-04 owns post/phase8_output_stage_post.json): GREEN with delta 1.71 s = 0.192x the 8.91 s pre delta, well inside the inclusive 0.5x boundary"
  - "The frozen writer and the 12 committed fixtures stayed untouched: git blob eb0d5bf2… and an empty tests/fixtures/ status"

requirements-completed: [OUT-01]

coverage:
  - id: D1
    description: "Pre-change output-stage baseline captured from the untouched tree with provenance, pinned slice fingerprint/counts/.rkdb sha256 and a persisted counterbalanced schedule"
    requirement: OUT-01
    verification:
      - kind: e2e
        ref: "scripts/bench/output_stage.py capture --threads 4 --reps 3 --slice-reads 4000000 -> sorted 18.730 s / unsorted 9.820 s / delta 8.91 s; fingerprint 71c6264b…, counts 229,694,874/519,271,168, sha 0976f29c… identical across 3 reps"
        status: pass
      - kind: unit
        ref: "python3 -m unittest discover -s scripts/bench/tests -t . -p test_output_stage.py: 29 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "Consuming pair collection + in-place parallel unstable sort streams the sorted .rkdb through the frozen writer and reproduces the committed k21/canon/sorted golden byte for byte"
    requirement: OUT-01
    verification:
      - kind: integration
        ref: "tests/output_pipeline_tests.rs#sorted_rkdb_output_reproduces_the_committed_k21_canon_golden (sha256 a5da813e…)"
        status: pass
      - kind: integration
        ref: "tests/output_pipeline_tests.rs#{sorted_rkdb_records_are_strictly_ascending,header_record_count_equals_the_number_of_records_on_disk,sorted_output_is_byte_identical_across_thread_counts}"
        status: pass
      - kind: other
        ref: "cargo test --test golden_sha256_tests (5 passed) + golden_tests (34 passed); git hash-object src/database/format.rs = eb0d5bf2…; tests/fixtures untouched"
        status: pass
    human_judgment: false
  - id: D3
    description: "Text output ordered by the numeric encoded key, proven equal to the historical decoded order for every supported k"
    requirement: OUT-01
    verification:
      - kind: integration
        ref: "tests/output_pipeline_tests.rs#{text_output_is_sorted_by_numeric_key,text_output_is_byte_identical_across_thread_counts,text_and_binary_maps_agree,numeric_order_equals_decoded_order_for_every_k,inverted_order_control_fails}"
        status: pass
      - kind: unit
        ref: "src/cli/commands/count.rs#sort_pairs_ascending_orders_numeric_keys_and_is_deterministic (cargo test --lib: 260 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Post-change output-stage gate GREEN: one .rkdb sha256 at slice scale, sorted wall strictly below baseline, sort delta at most half the baseline delta, peak RSS not regressed"
    requirement: OUT-01
    verification:
      - kind: e2e
        ref: "scripts/bench/output_stage.py compare --threads 4 --reps 3 -> OUTPUT STAGE VERDICT result=GREEN sorted_wall_s=10.43 sort_delta_s=1.709999999999999 sha256_match=True score=ok"
        status: pass
    human_judgment: false

duration: 27min
completed: 2026-11-13
status: complete
---

# Phase 8 Plan 01: Output Pipeline Tracer Summary

**The CLI's counting-output stage now collects each partition table once, sorts in place with rayon's pdqsort, and streams through the frozen `.rkdb` writer: the measured t4 sort delta fell from 8.91 s to 1.71 s (0.192x) while the sorted output stayed byte-identical, and text output is numerically ordered with a k 1..=64 equivalence proof.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-11-12T16:56:00Z
- **Completed:** 2026-11-12T17:23:00Z
- **Tasks:** 3
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments

- Captured the immutable PRE-change baseline from the untouched tree before any source edit: t4 sorted median 18.730 s, unsorted 9.820 s, raw sort delta 8.910 s (> the 3.0 s instrument precondition), peak RSS 17,967,087,616 B, pinned counts 229,694,874 unique / 519,271,168 total, slice fingerprint `71c6264b…`, and one sorted `.rkdb` sha256 `0976f29c…` across all three reps.
- Built the standing `scripts/bench/output_stage.py` gate (`capture` / `compare`) on the existing harness helpers: exactly one provisioned slice, parity before timing, one discarded warmup per arm, a persisted counterbalanced rotation, per-rep `cache_state`/`round`/`arm_order`, a raw never-clamped `sort_delta_s`, schema+provenance validation before every write, and the 0/1/2 exit contract with no verdict line on exit 2. Its 29 unit tests pass with no sleeps and no real `sudo purge`.
- Landed the consuming output path: `LocalKmerCounts::into_pairs_into` drains an owning table into the pair buffer; `CountResult::into_filtered_pairs` pre-allocates the exact key capacity and moves each table out so it is dropped as it drains; `sort_pairs_ascending` is a single `par_sort_unstable_by` (pdqsort, in place) call; the sorted slice streams one record at a time through the unchanged `DatabaseHeader::write_to` / `KmerEntry::write_to` codec with an explicit flush.
- Proved byte identity: the real CLI on the golden input emits the committed `a5da813e…` fixture byte for byte; all 12 fixtures and the manifest are untouched (`tests/fixtures/` clean); `src/database/format.rs` is still git blob `eb0d5bf2…`. Records are strictly ascending, the header record count equals the on-disk records, and the sum of counts equals the reported total. t1 and t4 outputs are byte-identical.
- Replaced the text comparator (two decoded `String`s per comparison) with the shared numeric-key sort, and proved the numeric order equals the decoded lexicographic order for every k in 1..=64 with a deterministic seeded test plus a deliberately inverted-order control that must fail.
- Measured the post-change stage with the same instrument (`compare` against the frozen baseline): sorted median 10.43 s, unsorted 8.72 s, delta 1.71 s, sorted RSS 12,043,026,432 B, sorted `.rkdb` sha256 still `0976f29c…` — verdict GREEN with `score=ok`.
- Verified the tree: MSRV 1.82 clippy `-D warnings` clean on both crates, full locked suite green (30 `test result: ok` summaries, 0 failed; 260 lib tests), and the full harness discovery green at 345 tests (skipped=1).

## Measured Evidence

**Pre-change baseline (untouched tree, t4, 3 counterbalanced reps, `pre/phase8_output_stage_pre.json`):**

| Arm | Median wall | Peak RSS (median) | CV% | Counts |
|---|---|---|---|---|
| sorted | 18.730 s | 17,967,087,616 B | 11.66% (`cv_warning`) | 229,694,874 / 519,271,168 |
| unsorted | 9.820 s | 14,295,744,512 B | 1.85% | 229,694,874 / 519,271,168 |

Raw `sort_delta_s` = **8.910 s**. Sorted `.rkdb` sha256 in every rep: `0976f29c5edeaa5eb49218e2c2fd5ff84f09109c3f2aac9d83bc8cf8c8668014`.
Slice fingerprint: `71c6264bc4c2b24a2d8d7a4a5ff4b18ec602b64141de745fd210336501b92937` (1,472,481,891 B).
Provenance: binary `d107d17e…`, HEAD `4d53102`, build profile release, `git_dirty: true` (untracked harness files only).

**Post-change compare (same instrument and scope):**

| Arm | Median wall | Peak RSS (median) | CV% | Counts |
|---|---|---|---|---|
| sorted | 10.430 s | 12,043,026,432 B | 3.64% | 229,694,874 / 519,271,168 |
| unsorted | 8.720 s | 12,043,845,632 B | 1.02% | 229,694,874 / 519,271,168 |

Raw `sort_delta_s` = **1.710 s** (0.192x the pre-change 8.910 s; the gate allows <= 0.5x inclusive).
Sorted `.rkdb` sha256: `0976f29c…` — `sha256_match=True`.
Verdict line: `OUTPUT STAGE VERDICT result=GREEN sorted_wall_s=10.43 sort_delta_s=1.709999999999999 sha256_match=True score=ok`.
Peak RSS: 12,043,026,432 B <= 17,967,087,616 B (no regression).

## Task Commits

Each task was committed atomically:

1. **Task 1: Capture the pre-change output-stage baseline with a new standing measure gate** — `416c768` (feat)
2. **Task 2: End-to-end sorted `.rkdb` output — consume, parallel unstable sort, stream into the frozen writer** — `883c2aa` (feat)
3. **Task 3: Text output — numeric-key sort and an order-equivalence proof for every k** — `b6109a8` (feat)

**Plan metadata:** the final docs commit with this SUMMARY, STATE.md, ROADMAP.md, and REQUIREMENTS.md.

## Files Created/Modified

- `scripts/bench/output_stage.py` — `capture`/`compare` output-stage gate over one 4M-read slice: sorted vs `--no-sort`, parity before timing, counterbalanced rounds, honest per-rep cache state, raw delta, validated documents, exit 0/1/2.
- `scripts/bench/tests/test_output_stage.py` — 29 stdlib unit tests: argv construction, raw/unclamped delta, four-condition verdict matrix (each failure isolated), 0.5x boundary, sha mismatch RED (not invalid), fingerprint/params mismatch exit 2, rotation schedule, injected-purge rep shape, document validation.
- `tests/output_pipeline_tests.rs` — 9 integration tests: golden byte identity, strict ascending records, header record count == on-disk records and count sum == reported total, t1/t4 `.rkdb` and text identity, numeric/lexicographic text order, text-vs-binary map agreement, k 1..=64 order permutation proof, inverted-order control.
- `.planning/phases/08-output-pipeline-rkdb-v2-parity/pre/phase8_output_stage_pre.json` — immutable pre-change baseline (provenance, pinned fingerprint/counts/sha, per-rep cache_state/round/arm_order, persisted schedule, medians, raw delta).
- `src/hash/local.rs` — `LocalKmerCounts::into_pairs_into` consuming drain with dense zero-extension.
- `src/count/engine.rs` — consuming `CountResult::into_pairs` / `into_filtered_pairs`; `filtered_pairs` and `for_each_count` untouched.
- `src/cli/commands/count.rs` — `sort_pairs_ascending` (in-place parallel unstable sort), consuming streaming binary/text writers with explicit flushes, numeric-key text order, stats computed before the result is moved, idempotence unit test.

## Decisions Made

- **Baseline first, from the untouched tree:** the pre-change document was captured before any `src/` edit, with provenance (binary sha + HEAD) and the pinned slice/counts/sha; the harness's own `compare` requires identical params and slice fingerprint, so a later tree cannot be silently measured as "pre".
- **pdqsort, not merge sort:** `par_sort_unstable_by` sorts in place; `par_sort`/`par_sort_by` would allocate a temporary buffer the size of the 229M-pair slice and raise peak RSS by that whole buffer.
- **One sort buffer:** the pair vector is the only full-size buffer; partition tables are moved out and dropped as they drain, which is why post-change RSS (12.04 GB) is below the pre-change peak (17.97 GB).
- **Numeric text order is the historical order:** A<C<G<T maps to 0<1<2<3 in order of significance, so ascending numeric key equals the decoded lexicographic order; proven for every k 1..=64 and guarded by an inverted-order control.
- **Honest baseline variance:** the sorted baseline arm carries `cv_warning: true` (11.66%, third rep 22.42 s). The median is used and the warning is recorded rather than dropping the rep or re-running until a cleaner number appears.

## Deviations from Plan

None — the plan executed exactly as written. The source edit for the test helper (`run_count` reduced from 8 to 7 arguments after the MSRV clippy gate flagged `too_many_arguments`) happened inside Task 3 before its commit; no production code changed for it.

## Issues Encountered

- The pre-existing timing-sensitive harness negative control (`test_pre_engine_n_plus_one_stub_is_measured_red`, macOS `sample` returning 0 threads) failed transiently while the suite ran under load; the test and helper were left unmodified and three consecutive full discoveries then passed (`Ran 345 tests … OK (skipped=1)`). This matches the Phase 7 precedent and is not caused by the new tests (the 29 new tests are deterministic, spawn nothing, and sleep never).
- The sorted baseline arm's third rep was 22.42 s (CV 11.66%, warning recorded); the median 18.730 s was used as measured. The post-change arm was stable (CV 3.64%).
- The baseline provenance records `git_dirty: true` because the new harness files were untracked when the capture ran. The measured binary (`d107d17e…`) and HEAD (`4d53102`) are both recorded, and no `src/` file differed from HEAD at capture time.

## Known Stubs

None. No placeholder values, skipped tests, or unrun verifications were introduced.

## Threat Flags

None beyond the plan's threat model. T-08-01 (output ordering/content) is held by golden byte equality, strict ascending records, the pinned slice sha256, and the untouched fixture manifest; T-08-02 (RSS) by 12.04 GB <= 17.97 GB; T-08-03 (baseline tampering) by the untouched-tree capture plus provenance/pinned fingerprint/counts/sha and the compare identity gate; T-08-04 (partial write) by the explicit flush with error propagation; T-08-SC by unchanged manifests/lockfiles and `--locked` builds/tests.

## Next Phase Readiness

- 08-02 can build the four-arm byte differential on top of the single consuming writer path; the committed goldens and `format.rs` are untouched.
- 08-03 can target the exact comparator token `|(a, _), (b, _)| a.cmp(b)` (single occurrence in `count.rs`) for its ordering mutation-RED demonstration, and the consuming collector for duplication/overflow mutations.
- 08-04 can run `output_stage.py compare` as the formal post artifact; this execution's equivalent run (to `/tmp`, not committed) already produced GREEN with a 0.192x delta.
- No blockers.

## Self-Check

- Created files verified present: `scripts/bench/output_stage.py`, `scripts/bench/tests/test_output_stage.py`, `tests/output_pipeline_tests.rs`, `pre/phase8_output_stage_pre.json`.
- Task commits verified as ancestors of HEAD: `416c768`, `883c2aa`, `b6109a8`.
- Frozen contracts: `src/database/format.rs` git blob `eb0d5bf2…`; `tests/fixtures/` clean; `Cargo.toml`/`Cargo.lock` unchanged.

## Self-Check: PASSED

---
*Phase: 08-output-pipeline-rkdb-v2-parity*
*Completed: 2026-11-13*
