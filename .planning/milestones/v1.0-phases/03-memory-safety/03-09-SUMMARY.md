---
phase: 03-memory-safety
plan: 09
subsystem: database
tags: [rust, rkdb, merge-routing, admission-control, memory, raII, pyo3, tdd]

# Dependency graph
requires:
  - phase: 03-memory-safety
    provides: "Plan 03-01 made merge routing budget-dependent, added the header-only `estimate_total_kmers` (D-01) and the D-02 reject; 03-07 deleted the `read_from` endianness heuristic and left `src/database/format.rs` with a clean record reader"
  - phase: 03-memory-safety
    provides: "Plan 03-02 added `create_merge_temp_subdir` / `MERGE_TEMP_PREFIX` / `sweep_stale_merge_dirs` and `ExternalSortMerger::merge_temp_subdir_path` — the RAII subdir this plan moves the prefix-cache intermediate result into"
  - phase: 03-memory-safety
    provides: "03-VERIFICATION.md gap G2 (= code-review CR-02) plus WR-01, WR-06, WR-07, IN-01, IN-02, IN-03 and deferred item (b) — the findings this plan closes"
provides:
  - "`RKDatabase::read_header_of(path)` — a 42-byte header read applying `from_file_path`'s identical `data_offset != 42` rejection and error text"
  - "No merge route materializes an input it does not need: the streaming route reads 42 bytes, the prefix-cache route holds `Vec<DatabaseHeader>`, `ExternalSortMerger::new` reads headers only"
  - "`RKDatabase::estimated_bytes_for_route(MergeStrategy, u64)` — the single place a route's per-k-mer cost becomes a number, with `INMEMORY_BYTES_PER_KMER = 96` derived from three live structures"
  - "A budget of `48 * N` demonstrably routes to STREAMING where the retired 24 B/k-mer model routed in-memory (observed RED with the old constant restored)"
  - "The Python copy of the admission model repaired (24 -> 96) and paired to the core's own echoed figure, so the two cannot drift apart silently again"
  - "`merge_databases(&[], ..)` returns Err on all three selectors instead of panicking on `&input_paths[0]`"
  - "The prefix-cache intermediate result is inside the RAII subdir and is reclaimed; a user's `--max-memory` is no longer overridden by a 1 GB floor"
affects: [phase-04-benchmark, merge-routing, MERGE-01, MERGE-02, MERGE-03, T-03-31, T-03-32, T-03-33, T-03-34, T-03-35, 03-10]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 18050
  tasks: 3
  commits: 4

# Commit ledger — MEASURED with `git rev-list --count`, never narrated (#3968).
commits: 4
plan_head_before: 8122730
# The post-TASK state (all three task commits landed, plus one added-coverage
# commit — see Deviations 8). The plan-metadata commit that carries this file is
# its child; a commit cannot contain its own hash, so this field names the
# stable, verifiable parent rather than a self-reference.
plan_head_after: dc1c25a

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Header-only read as a reusable primitive: `read_header_of` is now the single door through which every merge route learns an input's shape, and it is the same door `from_file_path` uses for its own validation — one rejection, one error text, two readers that cannot disagree"
    - "One number, one owner: the admission estimate is computed once in `merge_databases` and handed to `should_use_streaming`, which is now a pure comparison. Two sites computing the same quantity with two literals is how the 24 drifted from the structures it was supposed to describe"
    - "A per-route constant carries its derivation in its own doc comment, and the derivation is checkable: `size_of::<KmerEntry>() == 32` and `size_of::<(u128, u32)>() == 32` are asserted in the test, so a layout change turns the comment false and says so"
    - "Routing a validator through a stricter reader is a behaviour change, not a refactor. The doc says so in those words, in the direction that matters: a file the estimator used to trust and no reader accepts now falls back with a `log::warn!`"
    - "A route proof is only as strong as the error it matches. `Failed to create temp file` + the nonexistent directory's own name is the streaming route's real signature; `contains(\"temp\") || contains(\"No such file\")` is satisfied by half the crate's failure modes"
    - "Cross-language constants are paired BEHAVIOURALLY, not by comment: the Python copy is asserted against the figure the core echoes in its own rejection message, because two comments cannot be shown to agree"

key-files:
  created: []
  modified:
    - "src/database/format.rs — `read_header_of`; `estimate_total_kmers` delegates to it; `estimated_bytes_for_route` + the three derived constants; saturating `total_kmers` fold; the empty-input guard hoisted to the dispatcher; the prefix-cache path holds `Vec<DatabaseHeader>`; `validate_header_compatibility`; the RAII-subdir intermediate result; `PREFIX_CACHE_MIN_BUFFER_MB`; `DatabaseHeader::total_kmers` documented as the RECORD count; two new unit tests"
    - "src/database/prefix_cache_merge.rs — `ExternalSortMerger::new` reads headers only (was: every input loaded twice, the first one used only for its header)"
    - "src/database/merge_config.rs — `use_streaming`'s doc comment states it is ACCEPTED AND IGNORED and names the real selectors (WR-07). No field added or removed"
    - "src/hash/table.rs — `KmerCounter::total_kmers()` documented as the SUM OF COUNTS, cross-referencing the different number on `DatabaseHeader::total_kmers` (IN-03)"
    - "tests/merge_routing_tests.rs — 6 new tests; the route-probe assertion 03-07 reported as too weak tightened; `patch_header_u64` + `assert_streaming_route_proved` helpers"
    - "pyo3/tests/test_database_merge.py — `BYTES_PER_KMER_ESTIMATE` 24 -> 96, plus `test_python_budget_model_tracks_the_core` (W1's repair)"

key-decisions:
  - "`read_header_of` applies `from_file_path`'s `data_offset != 42` rejection, and `estimate_total_kmers` now routes through it. This is NOT 'semantics preserved exactly': a header that parses with any other data_offset moves from 'header trusted' to 'file-size fallback with a log::warn!'. That is the SAFE direction — `from_file_path` refuses such a file outright, so the estimator was previously the MORE permissive of the two and would admit a merge that then failed on read. The doc comment says this in those words so the next reader does not 'restore' the looser behaviour"
  - "The `&[&Self]` compatibility adapter the plan asked for was DELETED rather than kept under `#[allow(dead_code)]`. After the header refactor it had no caller at all, and a private shim retained 'just in case' is a second thing to keep correct that reads like a live path. One implementation of the rules survives either way; this one has zero dead lines"
  - "`INMEMORY_BYTES_PER_KMER`'s comment makes NO direction claim. The real peak is `32*N + 64*U .. 32*N + 68*U` (the hash map is drained and freed before `from_kmer_pairs` allocates its `Vec<KmerEntry>`), the two candidates differ by ~6%, and hashbrown's control bytes and load factor are not modelled at all — so any claim that 96 over- or under-states the peak would be arithmetic the comment cannot support. The phrase 'UNDER-estimate' appears nowhere in the file"
  - "The per-route constants are DERIVED, and the derivation is checkable rather than asserted: `KmerEntry` and `(u128, u32)` are both exactly 32 B (20 B of payload padded to `u128`'s 16-byte alignment), so 32 + 32 + 32 = 96 is not a guess. The test pins both `size_of`s and labels them a floor, not the evidence"
  - "`should_use_streaming` lost its duplicated estimate entirely and now takes `estimated_memory: u64`. The plan offered this explicitly; keeping a second computation of the same number in the predicate is what allowed the two sites to disagree"
  - "`estimated_bytes_for_route` takes a `MergeStrategy` and returns bytes. It does NOT return a strategy from `merge_databases` — 03-01 deliberately declined that API in favour of the behavioural `temp_dir` probe, and that discipline is unchanged. Every route claim in the new tests is still proved by an observed side effect"
  - "The route-probe assertion 03-07 reported as too weak was tightened (it is this plan's file). `contains(\"temp\") || contains(\"No such file\")` is satisfied by a k-mer-size mismatch, a bad input path, and a corrupt input; the replacement asserts the chunk-creation operation AND the nonexistent directory's own name, which is the signature only the streaming path can produce. The Python file already asserted this exact pair, so the Rust side now matches it"
  - "The Python-side gates are grep- and arithmetic-based, NOT executed. maturin refuses to build the extension (`python-source = \".\"` with a `pyo3/pyrustkmer/` that has never existed) and every pyo3 pytest run exits 1 against `--cov-fail-under=80` on a compiled extension. A pytest run would assert against a prebuilt `.so`, i.e. a green that means nothing"
  - "The saturating-sum test asserts on the D-02 message, not merely on 'no panic'. Asserting only the absence of a panic would pass if the saturated figure were recomputed correctly somewhere and then lost before the message; reading `u64::MAX` out of the rejection message proves the saturated value survived the whole path"
  - "The prefix-cache reclamation test asserts BOTH halves separately — nothing survives in the subdir, and nothing survives at the old shared-`temp_dir` path. Checking only one would pass if the file had merely moved somewhere else outside RAII"
  - "`use_streaming` is documented, not deprecated and not removed. Deprecating a public field with five construction sites would fail `-D warnings` in three files this plan has no business touching; removing it is a breaking public-API change. Naming the trap is the honest half of the fix and the rename is recorded as an explicit deferral"

patterns-established:
  - "A model constant must carry the derivation of its own value, and the derivation must be checkable from outside. `size_of` in a test is a floor and a drift alarm, not evidence — the behavioural evidence is the `48 * N` routing test"
  - "Reusing a reader to satisfy a caller can tighten the caller. When that happens the change belongs in the doc comment, in the safe direction, spelled out — otherwise the next reader 'restores' the more permissive version and reinstates the bug"
  - "When a whole-file grep gate and a code change disagree, distinguish the two: a gate that can be satisfied by rewording prose is measuring prose. Report the measurement and add a gate that measures the property"
  - "A dead adapter is worse than no adapter. When a refactor leaves a private shim with zero callers, delete it: the plan's intent (one implementation) is served more honestly by zero dead lines than by an `#[allow(dead_code)]` that looks live"
  - "A saturating sum is a correctness requirement in admission control, not a style preference. `.iter().sum()` panics in debug builds, and the component whose whole job is surviving hostile input is exactly where a panic is least acceptable. The test must be observed RED for that claim to be evidence"

requirements-completed: [MERGE-01, MERGE-02, MERGE-03]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "No merge route materializes an input database it does not need: `merge_databases_streaming` reads 42 bytes, `merge_databases_prefix_cache` holds `Vec<DatabaseHeader>`, and `ExternalSortMerger::new` reads headers only"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#header_only_read_agrees_with_the_materializing_loader (field-for-field agreement with from_file_path on a well-formed file; a header claiming 5e9 k-mers over an empty body returns 5e9, which is only possible if nothing was loaded — ~100 GB would be needed to materialize it)"
        status: pass
      - kind: other
        ref: "grep -vE '^\\s*//' src/database/format.rs | grep -c 'RKDatabase::from_file_path(&input_paths\\[0\\])' -> 0; grep -vE '^\\s*//' src/database/prefix_cache_merge.rs | grep -c 'RKDatabase::from_file_path' -> 0 — both DISCRIMINATE (was 1 each)"
        status: pass
      - kind: integration
        ref: "cargo test -> exit 0, 409 passed, 0 failed across 19 binaries"
        status: pass
    human_judgment: false
  - id: D2
    description: "The in-memory route is charged 96 bytes per k-mer, derived from the three structures that route holds live; streaming and prefix-cache report a diagnostic-only 32; `Hybrid` is defined as the in-memory peak"
    requirement: MERGE-02
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#estimated_bytes_per_route_reflects_each_routes_peak (the three products, the Hybrid case, u64::MAX saturation, plus size_of::<KmerEntry>() == 32 and size_of::<(u128,u32)>() == 32 pinning the derivation; observed RED with the old constant restored)"
        status: pass
      - kind: other
        ref: "grep -c 'saturating_mul(24)' src/database/format.rs -> 0 (was 2); grep -vE '^\\s*//' src/database/format.rs | grep -c 'UNDER-estimate' -> 0 (the prohibited false direction claim is not in the source)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The model change is BEHAVIOURAL: a budget strictly between the old and new per-k-mer costs (48 * N) now hard-routes to streaming, where the retired 24 B/k-mer model routed in-memory"
    requirement: MERGE-02
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#model_change_routes_a_budget_the_old_model_admitted_to_streaming (budget 48N; streaming proven by the nonexistent-temp_dir chunk-creation failure; an in-memory control at the derived estimate proves the probe discriminates). Observed RED with INMEMORY_BYTES_PER_KMER set back to 24: the guard fired with 'the derived estimate (4800) must EXCEED the budget (9600)'"
        status: pass
      - kind: other
        ref: "pre-fix arithmetic: 24N = 4800 <= 9600 = 48N, so over_budget was false and the merge returned Ok (in-memory). Post-fix 96N = 19200 > 9600, so it streams"
        status: pass
    human_judgment: false
  - id: D4
    description: "A crafted `.rkdb` header claiming near-max k-mers saturates the admission sum instead of panicking, and the saturated figure survives all the way into the D-02 rejection message"
    requirement: MERGE-02
    verification:
      - kind: unit
        ref: "src/database/format.rs::summing_two_near_max_headers_saturates_instead_of_panicking (two headers at 2^63 each; observed RED pre-fix with 'attempt to add with overflow' at iter/traits/accum.rs:206, i.e. a debug-build panic inside the admission gate)"
        status: pass
      - kind: unit
        ref: "cargo test --lib summing_two_near_max_headers_saturates_instead_of_panicking -> 1 passed"
        status: pass
    human_judgment: false
  - id: D5
    description: "W1: the Python copy of the admission model is repaired (24 -> 96) and pinned to the core's own echoed figures, so the two cross-language copies cannot drift apart silently again"
    requirement: MERGE-02
    verification:
      - kind: other
        ref: "grep -c 'BYTES_PER_KMER_ESTIMATE[ ]=[ ]96' pyo3/tests/test_database_merge.py -> 1; grep -c 'BYTES_PER_KMER_ESTIMATE[ ]=[ ]24' -> 0; grep -c 'test_python_budget_model_tracks_the_core' -> 2; git status --porcelain pyo3/src/ -> empty (only the TEST file changed)"
        status: pass
      - kind: other
        ref: "extension-free arithmetic: N=120 records, _within_budget = 2*96*120 = 23040 > the core's 11520. With the OLD python 24 it was 5760 <= 11520, so test_inmemory_route_never_touches_temp_dir would have raised the D-02 RuntimeError outright — the repair was mandatory, not cosmetic"
        status: pass
      - kind: manual_procedural
        ref: "NOT EXECUTED — see the residual below. pyo3/tests/test_database_merge.py was never run: `pyrustkmer.so` in the venv is a prebuilt artifact, `maturin build`/`develop` refuse to run at all (python-source=\".\" with a pyo3/pyrustkmer/ that has never existed), and addopts hard-codes --cov-fail-under=80 against a compiled extension so every pytest run exits 1 even when green. .github/workflows/ci.yml has no pyo3 pytest job at all"
        status: unknown
    human_judgment: true
    rationale: "This deliverable is correct-by-construction and verified two ways that do not require executing Python — grep on the constant, and extension-free arithmetic on the budget helpers — but neither is a test run. The only executable evidence for the Python surface would be a rebuilt extension, and the one-line `pyo3/pyproject.toml` fix that would allow it is recorded in deferred-items.md and deliberately out of this plan's scope. A human should treat the Python half as unverified-until-rebuild and weigh it accordingly at ship time."
  - id: D6
    description: "The prefix-cache intermediate result lives inside the process-unique RAII subdir and is reclaimed, and a user's `--max-memory` is no longer silently overridden by a 1 GB per-bucket floor (IN-01)"
    requirement: MERGE-03
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#prefix_cache_intermediate_result_is_inside_the_raii_subdir_and_reclaimed (asserts absence in the subdir AND at the old shared-temp_dir path). Observed RED against the old fixed location: 'the intermediate result must not be written to the shared temp dir at /tmp/.tmpXXXX/external_sort_merge_output.tmp'"
        status: pass
      - kind: other
        ref: "grep -c 'PREFIX_CACHE_MIN_BUFFER_MB' src/database/format.rs -> 4 (declaration, doc, comparison, log); grep -c 'merge_temp_subdir_path' -> 1; the only surviving `config.temp_dir.join(\"external_sort_merge_output.tmp\")` is the `None` fallback arm at the match"
        status: pass
      - kind: integration
        ref: "cargo test --test merge_cleanup_tests -> exit 0, 26 passed (MERGE-03's RAII/sweep suite unaffected)"
        status: pass
    human_judgment: false
  - id: D7
    description: "WR-06: `merge_databases(&[], ..)` returns Err naming the cause on all three selectors, and never panics"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merge_databases_with_empty_input_list_returns_err (std::panic::catch_unwind around the call; asserts the exact message on 'auto', 'memory', 'streaming' and use_prefix_cache)"
        status: pass
      - kind: other
        ref: "grep -c 'At least one input database is required' src/database/format.rs -> 3 (the two pre-existing per-strategy guards plus the new one at the top of the dispatcher)"
        status: pass
    human_judgment: false
  - id: D8
    description: "WR-07 and IN-03 are closed by NAMING, not by renaming: the dead `MergeConfig::use_streaming` field says it is ignored, and both `total_kmers` meanings are documented at both sites"
    requirement: MERGE-02
    verification:
      - kind: other
        ref: "grep -c 'ACCEPTED AND IGNORED' src/database/merge_config.rs -> 1; grep -c 'RECORD count' src/database/format.rs -> 1; grep -c 'SUM OF COUNTS' src/hash/table.rs -> 1; grep -rn 'use_streaming' src/ shows only the field, its default, its writers, and the dispatcher's unrelated local"
        status: pass
      - kind: integration
        ref: "cargo clippy --all-targets -- -D warnings -> exit 0 on both the root crate and pyo3 (no deprecation warnings introduced, so the five construction sites stay clean)"
        status: pass
    human_judgment: false
  - id: D9
    description: "IN-02 is verified STALE: the 4 `useless_borrows_in_formatting` sites named in deferred-items.md no longer exist and the clippy gate is clean"
    requirement: MERGE-02
    verification:
      - kind: other
        ref: "src/io/fastq.rs:216 writes `self.file_path` (no `&`); src/io/fastq.rs:343 writes `path`; src/io/fasta.rs:56 writes `self.file_path`; src/io/fasta.rs:153 is not a `format!` at all (it is a `)?;` statement close). No `format!` in either file passes `&self.file_path` or `&path`"
        status: pass
      - kind: other
        ref: "cargo clippy --all-targets -- -D warnings -> exit 0 on the root crate, which is the exact command deferred-items.md gives as the reproduction for the entry"
        status: pass
    human_judgment: false
  - id: D10
    description: "The streaming route proof carried by the two over-budget tests is no longer satisfied by an unrelated failure (the weakness 03-07 reported and left for this plan's file)"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#assert_streaming_route_proved — asserts BOTH 'Failed to create temp file' AND the nonexistent directory's own file name; applied by merge_over_budget_hard_routes_to_streaming, merge_explicit_streaming_mode_always_streams and model_change_routes_a_budget_the_old_model_admitted_to_streaming"
        status: pass
      - kind: integration
        ref: "cargo test --test merge_routing_tests -> exit 0, 33 passed (the tightened assertion still holds against the real error)"
        status: pass
    human_judgment: false
  - id: D11
    description: "IN-03's documented semantic change: routing the estimator through `read_header_of` means a header carrying an unaccepted `data_offset` now falls back to the file-size bound instead of being trusted"
    requirement: MERGE-02
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#header_only_read_and_estimator_reject_an_unaccepted_data_offset (read_header_of and from_file_path produce the IDENTICAL error text; the estimate equals (file_size - 42) / 20 rather than the header's total_kmers)"
        status: pass
    human_judgment: false

# Metrics
duration: 12 min
completed: 2026-10-07
status: complete
---

# Phase 03 Plan 09: Header-Only Merge Routes + Recalibrated Admission Model Summary

**No merge route loads an input database it does not need — the route chosen *because* the inputs do not fit used to load one in full — and the in-memory route is now charged 96 bytes per k-mer instead of 24, which moves a whole class of budgets from "admitted in memory" to "routed to streaming".**

## Performance

- **Duration:** 12 min
- **Started:** 2026-10-07T12:40:56Z
- **Completed:** 2026-10-07T12:53:00Z
- **Tasks:** 3
- **Files modified:** 6 (0 created, 6 modified)
- **Commits:** 4 (3 task commits + 1 added-coverage commit, Deviation 8)

## The defect this plan closes

Gap **G2** (= code-review **CR-02**) has two halves. Plan 03-01 fixed the *estimator*: the function whose whole job is to prevent OOM was itself the OOM, because it called `RKDatabase::from_file_path(path)` per input purely to read one `u64` from a 42-byte header. But the same materialization survived unaltered in all three strategies the estimator routes *into*:

```text
format.rs:869   merge_databases_streaming  -> from_file_path(&input_paths[0])   for TWO header fields
format.rs:1146  merge_databases_prefix_cache -> held Vec<RKDatabase> live through the final read-back
prefix_cache_merge.rs:76,83  ExternalSortMerger::new -> loaded every input TWICE, first one used only for its header
```

And the constant that decides admission (`total_kmers * 24`, review finding **WR-01**) described roughly a quarter of the peak it was meant to bound — so a merge the gate admitted could still exhaust memory. It modelled the *in-memory* route, which is the route it admitted.

## Accomplishments

- **The header read is a reusable primitive, not a one-off.** `RKDatabase::read_header_of` is the single door through which every merge route learns an input's shape, and it is the *same* door `from_file_path` uses for its own validation — one rejection, one error text, two readers that cannot disagree. Two new tests assert the agreement field for field, and that a header claiming 5 billion k-mers over an empty body is readable (which is only possible if nothing was loaded; materializing it would need ~100 GB).
- **The prefix-cache path's peak lost every input database.** It held `Vec<RKDatabase>` alive all the way through the final `from_file_path(&temp_output)`, so peak was all-inputs-plus-full-output. It now holds `Vec<DatabaseHeader>` — ~42 bytes per input — and the compatibility rules moved into `validate_header_compatibility` with byte-identical error strings.
- **The model is derived, and the derivation is checkable.** `size_of::<KmerEntry>()` and `size_of::<(u128, u32)>()` are both exactly 32 bytes on this target (20 B of payload padded to `u128`'s 16-byte alignment), so 32 + 32 + 32 = 96 is arithmetic, not a guess. The test pins both `size_of`s and labels them a floor rather than the evidence.
- **The model change is behavioural, and was observed RED.** A budget of `48 * N` sits above the retired `24 * N` and below the new `96 * N`. With the old constant restored, the new test fired its guard with *"the derived estimate (4800) must EXCEED the budget (9600)"* — i.e. the merge would have run in memory and the test would have passed for the wrong reason. It also carries an in-memory control at the derived estimate, so "it streamed" is not the only thing proven.
- **The Python half of the model was not optional.** `BYTES_PER_KMER_ESTIMATE` is the only cross-language copy of the constant. Left at 24 it would have made `_within_budget` return 5,760 against the core's new 11,520 — so `test_inmemory_route_never_touches_temp_dir` would have raised the D-02 `RuntimeError` outright, and `test_streaming_and_inmemory_routes_produce_identical_data` would have quietly taken the streaming route on *both* arms. Both arithmetic facts are recorded below. The two copies are now paired by `test_python_budget_model_tracks_the_core`, which parses the figures the core echoes in its own rejection rather than trusting a comment to stay in sync.
- **A hostile header can no longer kill the admission gate.** `.iter().sum()` panicked with *"attempt to add with overflow"* on two crafted headers in a debug build — the one component whose entire job is surviving hostile input. Observed RED at `iter/traits/accum.rs:206` before the fix; the test then reads the saturated figure back out of the D-02 message, so it proves the value survived the whole path rather than merely proving no panic.
- **Two deferred items closed at once.** The prefix-cache intermediate `.rkdb` moved into the process-unique `rustkmer-merge-<rand>/` subdir, so RAII reclaims it with the shards (the disk-exhaustion half of MERGE-03) and two concurrent merges can no longer overwrite each other's result under a fixed basename (T-03-06). Its reclamation test asserts absence in *both* the subdir and the old shared-`temp_dir` path, and was observed RED against the old location.
- **`--max-memory` is no longer silently overridden.** A hard 1 GB per-bucket floor overrode `--max-memory 256MB` by 4x, on exactly the path that flag exists to constrain. Replaced with a 1 MB named constant plus one `log::info!` naming both numbers — the "don't be pathologically small" intent preserved, the silence removed.
- **`merge_databases(&[], ..)` errors instead of panicking** on `&input_paths[0]`, on all three selectors.
- **A route proof that could not fail was tightened.** 03-07 reported that `tests/merge_routing_tests.rs:283` accepted any error containing `"temp"` or `"No such file"` — which a k-mer-size mismatch, a bad input path, or a corrupt input all satisfy. The replacement asserts the chunk-creation operation *and* the nonexistent directory's own name, the same pair the Python file already asserted. Three tests now use it, including the new model-change test.

## Task Commits

Each task was committed atomically:

1. **Task 1: A header-only read, and the three call sites that stopped needing a whole database** — `8cbaa11` (refactor)
2. **Task 2: The prefix-cache intermediate joins the RAII subdir, and the 1 GB floor stops overriding the user's budget** — `11a43dd` (fix)
3. **Task 3: Charge each route the peak it actually reaches, and prove the model discriminates** — `33882b1` (fix)

Plus one added-coverage commit, because the plan required the external-sort error strings to be byte-identical and nothing was asserting it (Deviation 8):

4. **Task 1 (coverage gap closed after the fact): assert the external-sort compatibility errors kept their exact text** — `dc1c25a` (test)

Task 1 is a `tracer` task; its feedback gate re-ran the plan's `<verify>` verbatim end-to-end and passed (⚡ Tracer verified end-to-end — expanding), after which Tasks 2 and 3 landed.

**Plan metadata:** *(the commit carrying this file — a commit cannot record its own hash)*

## Files Created/Modified

- `src/database/format.rs` — `read_header_of`; `estimate_total_kmers` delegates to it (with the semantic change documented in words, not as "preserved"); `estimated_bytes_for_route` + `INMEMORY_BYTES_PER_KMER` / `STREAMING_BYTES_PER_KMER` / `PREFIX_CACHE_BYTES_PER_KMER`; saturating `total_kmers` fold; the empty-input guard hoisted above the sweep; the prefix-cache path on `Vec<DatabaseHeader>`; `validate_header_compatibility`; the intermediate result under `merge_temp_subdir_path()`; `PREFIX_CACHE_MIN_BUFFER_MB`; the routing log line extended with all three per-route figures; `DatabaseHeader::total_kmers` documented as the RECORD count; `summing_two_near_max_headers_saturates_instead_of_panicking` added to the **existing** `merge_admission_control` test module
- `src/database/prefix_cache_merge.rs` — `ExternalSortMerger::new` reads headers only; the comment records that `read_record_at` was already a plain `u32::from_le_bytes` and never carried the endianness heuristic, i.e. the reader was the outlier plan 03-07 fixed
- `src/database/merge_config.rs` — `use_streaming`'s doc comment: ACCEPTED AND IGNORED, names `merge_mode` / `use_prefix_cache` as the real selectors. No field added, removed, or deprecated
- `src/hash/table.rs` — `KmerCounter::total_kmers()` documented as the SUM OF COUNTS, cross-referencing the different number on `DatabaseHeader::total_kmers`
- `tests/merge_routing_tests.rs` — 6 new tests plus `patch_header_u64` and `assert_streaming_route_proved`; the two weak route-probe assertions tightened
- `pyo3/tests/test_database_merge.py` — `BYTES_PER_KMER_ESTIMATE` 24 → 96, plus `test_python_budget_model_tracks_the_core` and the `re` import it needs

`pyo3/src/` is byte-identical (`git status --porcelain pyo3/src/` empty). `tests/fixtures/` untouched. `src/database/streaming_merge.rs` untouched. `src/cli/`, `src/io/`, `tests/merge_route_parity_tests.rs`, `tests/golden_sha256_tests.rs` and `tests/dense_*` untouched.

## The derived constants, and what they do NOT claim

| Route | Constant | Basis | Status |
|---|---|---|---|
| InMemory | 96 | 32 (`Vec<KmerEntry>` per input record) + 32 (hashbrown `(u128,u32)` bucket) + 32 (`Vec<(u128,u32)>` drained from it) | **admission gate** |
| Streaming | 32 | one `chunk_size` buffer + a heap of run heads — O(chunk), not O(N) | **diagnostic only, never rejects** |
| PrefixCache | 32 | one bucket resident, bounded by the per-bucket threshold — O(bucket) | **diagnostic only, never rejects** |
| Hybrid | 96 | hybrid starts in memory, so its first-resort peak is the in-memory one | defined, not a panic/zero |

**On the in-memory constant, stated plainly because the plan flagged it as load-bearing:** `merge_databases_inmemory` does *not* hold all three structures for the same k-mer at the same instant. `all_kmers` is consumed by `into_iter()` and its table is freed at the end of that drain, before `from_kmer_pairs` allocates its `Vec<KmerEntry>`. So the true peak is at most `32*N + 68*U` and at least `32*N + 64*U` (N = total input records, U = unique), and the two candidates differ by about 6%. **96 sits at neither extreme, and the source comment says exactly that and nothing more.** A claim that it over- or under-states the peak would be arithmetic the comment cannot support — hashbrown's control bytes and load factor are not modelled at all. The value is rounded up from the dominant structure's own size because a gate that errs toward streaming is safe; the instrument that will actually *measure* the peak is plan 03-10's `/proc/self/status` test. The phrase "UNDER-estimate" appears nowhere in the file (`grep -vE '^\s*//' | grep -c` → 0).

## RED evidence — observed, not reconstructed

Each mutation below was applied, the test run, and the change reverted by a second targeted edit (not by hand-restoring a large file).

| Test | Pre-fix result |
|---|---|
| `summing_two_near_max_headers_saturates_instead_of_panicking` | **FAILED** — `panicked at .../iter/traits/accum.rs:206: attempt to add with overflow`. The admission gate aborted on two crafted headers. |
| `model_change_routes_a_budget_the_old_model_admitted_to_streaming` (with `INMEMORY_BYTES_PER_KMER` = 24) | **FAILED** — `GUARD: the derived estimate (4800) must EXCEED the budget (9600)`. Under the old model this budget was admitted in memory, so the merge would have returned `Ok` and the test would have passed for the wrong reason. |
| `estimated_bytes_per_route_reflects_each_routes_peak` (same mutation) | **FAILED** — the in-memory product is 24N, not 96N |
| `prefix_cache_intermediate_result_is_inside_the_raii_subdir_and_reclaimed` (path forced back to `config.temp_dir`) | **FAILED** — `the intermediate result must not be written to the shared temp dir at /tmp/.tmpXXXX/external_sort_merge_output.tmp` |
| `prefix_cache_kmer_size_mismatch_keeps_its_error_text` (database 1's k-mer count reported in database 2's diagnostic line) | **FAILED** — the verbose-diagnostic assertion, which no wording assertion above it could catch |

Post-fix: `cargo test` exits 0 — **409 passed, 0 failed** across 19 binaries (including 226 lib tests and 33 in `merge_routing_tests`). `cargo clippy --all-targets -- -D warnings` exits 0 on the root crate and inside `pyo3/`.

## The Python model repair, and why it was mandatory

`pyo3/tests/test_database_merge.py` carries the only cross-language copy of the admission constant. Arithmetic on the file's own helpers, computed **without importing `pyrustkmer`** (fixture: 60 + 60 = 120 records):

| | `_estimated_bytes` | `_within_budget` (= estimate × 2) | vs the core's 11,520 |
|---|---|---|---|
| Python 24 + core 96 (unrepaired) | 2,880 | **5,760** | **below** → `merge_mode="memory"` hits the D-02 reject and raises `RuntimeError` |
| Python 96 + core 96 (repaired) | 11,520 | 23,040 | above → the in-memory arm merges |

`_over_budget` returns 1,024, which is below both the old (2,880) and new (11,520) estimates, so the over-budget arms were never at risk. `test_python_budget_model_tracks_the_core` drives the D-02 rejection, parses `estimated memory (N bytes for M k-mers)` out of the core's own message, and asserts **both** figures — the byte count against `total_kmers * BYTES_PER_KMER_ESTIMATE` and the k-mer count against the sum of `db.get_stats().total_kmers` read in Python. The second assertion matters as much as the first: it pins the *record count* reading of `total_kmers` (IN-03) across the language boundary, so a future switch to the sum-of-counts reading fails loudly instead of silently scaling every budget in the file by the average count.

**Caveat, and it is not a small one:** the installed `pyrustkmer.so` is a **prebuilt artifact**, not a build of the Rust on disk. maturin refuses to run at all (`python-source = "."` with `module-name = "pyrustkmer"` while `pyo3/pyrustkmer/` has never existed in git history), and `addopts` hard-codes `--cov-fail-under=80` against a compiled extension, so every pyo3 pytest run exits 1 even when green. `.github/workflows/ci.yml` has **no pyo3 pytest job at all**. So: **maturin and pytest were deliberately NOT invoked**, this plan's Python-side gates are grep- and arithmetic-based, and the Python edit is kept correct-by-construction for the next rebuild. The Rust-side evidence for the model change is `model_change_routes_a_budget_the_old_model_admitted_to_streaming`.

## Decisions Made

- **The estimator is now the stricter of the two readers, and that is the fix.** See Deviations 4 — the single most consequential decision in this plan, because it is a behaviour change that could easily have been mis-described as a refactor.
- **The `&[&Self]` adapter the plan asked for was deleted rather than kept.** See Deviations 1.
- **No direction claim about 96.** See "The derived constants" above. This is the decision the adversarial review flagged as load-bearing, and it is also the reason the constant's doc comment is long: a short comment here would have had to either omit the derivation or make a claim it cannot support.
- **The two `size_of` assertions are labelled a floor, not the evidence** — following 03-06's lesson that a layout constant cannot go red under a source change. The behavioural evidence is the `48 * N` test.
- **`should_use_streaming` lost its duplicated estimate entirely.** The plan offered this ("better, delete the duplicated estimate … becoming a pure comparison over a value it is handed") and it is the right call: two sites computing the same quantity with two literals is how they drifted in the first place.
- **The saturating test asserts on the D-02 message, not merely on "no panic".** Asserting only the absence of a panic would pass if the saturated figure were recomputed correctly somewhere and then lost before the message. Reading `u64::MAX` out of the rejection proves the value survived end to end.
- **The reclamation test asserts both locations separately.** Checking only the subdir would pass if the file had merely moved somewhere else outside RAII; checking only `temp_dir` would pass if the subdir copy still existed.
- **The route-probe assertion was tightened, not left.** The plan flagged it as a known pre-existing weakness in a file it owns, and the tightening is low-risk and empirically verified: the tightened form still passes against the real error string.
- **`use_streaming` is documented, not deprecated and not removed.** Deprecating a public field with five construction sites would fail `-D warnings` in three files this plan has no business touching; removal is a breaking public-API change. Naming the trap is the honest half; the rename is deferred with the reason recorded below.

## Deferrals — explicit, with reasons, so the next reader does not re-derive them

- **WR-07 — `MergeConfig::use_streaming` rename.** DEFERRED. The field is a public member of a public struct; removing it is a breaking API change, and `#[deprecated]` would turn its five construction sites (`src/cli/commands/merge.rs:603`, `src/database/merge_config.rs:35` and `:174`, `src/database/format.rs` × 2, `src/database/merge_tests.rs:46`) into warnings and fail the `-D warnings` gate in files this plan is not authorised to touch. **Shipped instead:** a doc comment stating the field is ACCEPTED AND IGNORED and naming `merge_mode` / `use_prefix_cache` as the supported selectors. A silent trap is now a labelled one.
- **IN-03 — `total_kmers` rename.** DEFERRED for both meanings. `DatabaseHeader::total_kmers`, `PyDatabaseStats.total_kmers` and `KmerCounter::total_kmers` are all public. **Shipped instead:** each of the two Rust sites documents which meaning it carries and cross-references the other, with the reasoning for why the admission model depends on getting it right.
- **deferred-items.md's IN-02 entry itself.** Still says `status: open`. `deferred-items.md` is not in this plan's `files_modified`, so the entry was left as-is; the verification is recorded here and the entry should be marked closed by whoever next owns that file.

## IN-02 verification — the recorded clippy entry is stale

`deferred-items.md` records 4 `clippy::useless_borrows_in_formatting` errors in `src/io/{fasta,fastq}.rs` as `status: open`, and gives `cargo clippy --all-targets -- -D warnings` as the reproduction. Checked directly:

| Named site | Actual state |
|---|---|
| `src/io/fastq.rs:215` | `:216` is `format!("Error reading FASTQ record from file: {}", self.file_path, …)` — `self.file_path`, **no `&`** |
| `src/io/fastq.rs:342` | `:343` is `format!("Error reading FASTQ record during validation: {:?}", path, …)` — `path`, **no `&`** |
| `src/io/fasta.rs` (4th site) | `:56` is `format!("Error reading FASTA record from file: {}", self.file_path)` — **no `&`** |
| `src/io/fasta.rs:153` | **not a `format!` at all** — it is the `)?;` statement close of the preceding `with_context` call |
| whole-file | no `format!` in either file passes `&self.file_path` or `&path` |

`cargo clippy --all-targets -- -D warnings` exits 0 on the root crate — the exact command the entry names. **The entry is stale; the lint is clean.** The next reader should not re-investigate it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The plan's thin `&[&Self]` adapter was dead code the moment the header refactor landed**
- **Found during:** Task 1, first `cargo build`
- **Issue:** Plan step 4 asked to "keep `validate_compatibility_external_sort(&[&Self], bool)` as a thin adapter … to avoid two copies of the compatibility rules". After `merge_databases_prefix_cache` switched to `Vec<DatabaseHeader>`, that function had **zero callers** — it is a private fn, and `grep -rn` found no other reference. Rust's `dead_code` lint fired, and `cargo clippy --all-targets -- -D warnings` (a blocking acceptance criterion of Task 3) failed on it.
- **Fix:** Deleted it rather than marking `#[allow(dead_code)]`. The plan's *intent* — one implementation of the rules — is served by `validate_header_compatibility` alone, and is served *more* honestly with zero dead lines: a private shim retained "just in case" is a second thing to keep correct that reads like a live path. The plan's `key_links` and Artifacts list only require `validate_header_compatibility` to exist, which it does.
- **Files modified:** `src/database/format.rs`
- **Verification:** `cargo clippy --all-targets -- -D warnings` → exit 0 on both crates; `grep -c 'validate_compatibility_external_sort' src/database/format.rs` → 1 (the doc comment that explains the removal). The error text is now **asserted**, not just claimed — see Deviation 8.
- **Committed in:** `8cbaa11`

**2. [Rule 1 - Bug] Switching from accessors to raw header fields left two now-unnecessary conversions**
- **Found during:** Task 1, first clippy run
- **Issue:** `merge_databases_streaming` previously took `kmer_size` from `first_db.kmer_size()` (a `usize` accessor) and passed it as `kmer_size as u8`. It now reads `header.kmer_size` directly, so the cast is a no-op → `clippy::unnecessary_cast`. Same cause in `validate_compatibility_external_sort`, where `kmer_size` came from the `usize` accessor and the return was `kmer_size.try_into().unwrap()`; from a raw `u8` field that is `clippy::useless_conversion`.
- **Fix:** Both simplified to pass the `u8` through. No behaviour change — the function signatures (`from_kmer_pairs(…, kmer_size: u8, …)` and `-> (u8, bool)`) already expected `u8`.
- **Files modified:** `src/database/format.rs`
- **Verification:** `cargo clippy --all-targets -- -D warnings` → exit 0; full suite green.
- **Committed in:** `8cbaa11`

**3. [Rule 1 - Bug] The updated `should_use_streaming` test introduced a `clippy::useless_vec`**
- **Found during:** Task 3, clippy run after the signature change
- **Issue:** `let paths = vec![a, b];` — clippy prefers an array when only `.iter()` follows.
- **Fix:** `let paths = [a, b];`
- **Files modified:** `src/database/format.rs`
- **Verification:** clippy exit 0; the test still derives its total from the real 42-byte headers.
- **Committed in:** `33882b1`

**4. [Rule 1 - Behaviour change, documented] `estimate_total_kmers` routing through `read_header_of` is a real change, and the plan required it to be stated as one**
- **Found during:** Task 1, implementing plan step 2
- **Issue:** The plan flagged this itself, and it is worth restating because "refactor" would have been the wrong word in the commit log. `read_header_of` applies `from_file_path`'s `data_offset != 42` rejection; `estimate_total_kmers` did not. A file whose header *parses* but carries any other `data_offset` therefore moves from "header trusted, return its `total_kmers`" to "file-size fallback, with a `log::warn!`". **This is the safe direction, not a regression:** `from_file_path` refuses such a file outright, so the estimator was previously the *more permissive* of the two — it would trust a `data_offset` no reader in the crate accepts, admit a merge on that estimate, and then have the merge fail on read. The `log::warn!` keeps the fallback visible.
- **Fix:** Implemented as the plan directs, and the doc comment states the change in those words — including the sentence "this is not a pure refactor" — so the next reader does not "restore" the looser behaviour. A dedicated test asserts all three observable consequences (identical error text from both readers; the message names the offending offset; the estimate falls back to `(file_size - 42) / 20`).
- **Files modified:** `src/database/format.rs`, `tests/merge_routing_tests.rs`
- **Verification:** `header_only_read_and_estimator_reject_an_unaccepted_data_offset` — patches `data_offset` to 64 at byte offset 26, asserts `read_header_of` and `from_file_path` produce **byte-identical** error text, and that the estimator returns the file-size bound rather than the header's 30 records.
- **Committed in:** `8cbaa11`

**5. [Rule 1 - Plan gate] `grep -c 'db_refs'` reads 2, not 0 — both in an unrelated test local**
- **Found during:** Task 1, running the plan's acceptance criteria
- **Issue:** The criterion reads "prints `0` — the prefix-cache path holds headers, not databases". The two surviving occurrences are `let db_refs: Vec<&RKDatabase>` and its use in `test_validate_compatibility_all_compatible`, which exercises the **in-memory** route's `validate_compatibility(&[&Self])` — a different function that legitimately takes databases. The prefix-cache path itself has zero occurrences.
- **Fix:** Reported as **2**, with the explanation. Renaming that test local purely to satisfy a grep would have made the gate green without making the property one bit truer, which is the wrong trade. **Discriminating gates substituted**, both of which do discriminate: inside `merge_databases_prefix_cache` there is no `from_file_path` of any input and no `Vec<RKDatabase>`; and the new `header_only_read_agrees_with_the_materializing_loader` test fails if `merge_databases_prefix_cache` reaches for a body.
- **Files modified:** none (measurement + gate selection only)
- **Verification:** `grep -n 'db_refs' src/database/format.rs` → `:1584` and `:1585`, both inside the test module. WINDOWS entry appended.
- **Committed in:** n/a

**6. [Rule 1 - Plan gate] `grep -c 'saturating_add(total)'` is unsatisfiable by natural code**
- **Found during:** Task 3, running the plan's acceptance criteria
- **Issue:** The criterion expects the literal substring `saturating_add(total)`. The saturating fold is naturally written `.fold(0u64, |total, count| total.saturating_add(count))`, which contains `saturating_add(count)` — the accumulator is the receiver, not the argument. No non-contrived formulation produces the literal.
- **Fix:** Reported as **0**, with the fold quoted verbatim at `src/database/format.rs:967`. **The evidence is behavioural and stronger than the grep:** `summing_two_near_max_headers_saturates_instead_of_panicking` was **observed RED** with the non-saturating `.iter().sum()` restored (`attempt to add with overflow`), and it drives the real public entry point, so it proves the saturated value reaches the D-02 message rather than merely that a `saturating_add` token exists.
- **Files modified:** none (measurement only)
- **Verification:** `grep -vE '^\s*//' src/database/format.rs | grep -c 'saturating_add'` → 2, both real code (the fold and `merge_databases_inmemory`'s per-k-mer accumulate). WINDOWS entry appended.
- **Committed in:** n/a

**7. [Rule 3 - Blocking] `.planning/WINDOWS.md`'s rendered table had drifted from its fenced JSON, blocking every `windows append`**
- **Found during:** writing this summary's broken-windows ledger
- **Issue:** `gsd_run windows append` refused with "Ledger table … disagrees with the fenced JSON entries … for row id(s): 8". The drift is one word: the table's `reason` cell for row 8 read "route parity asserted on…" where the JSON (the stated source of truth) reads "route parity **is** asserted on…". Left by plan 03-07, unrelated to this plan's scope, but it blocks the tooling.
- **Fix:** Repaired the single word so the table matches the JSON. No semantic content changed, and no other row was touched.
- **Files modified:** `.planning/WINDOWS.md` (planning artifact only — no product code)
- **Verification:** `windows append` then succeeded; three entries appended (one `unrun-verify` for the un-executable Python half, two `deviation` for gates 5 and 6 above).
- **Committed in:** the plan-metadata commit

**8. [Rule 2 - Missing Critical] The external-sort error strings were preserved but nothing asserted it**
- **Found during:** writing this summary's Self-Check, when I checked whether my own claim was true
- **Issue:** Plan step 4 required the external-sort compatibility error strings to be **byte-identical** to the pre-refactor ones, "because `tests/merge_routing_tests.rs` and the PyO3 docstring describe them". They are byte-identical — the `format!` arguments were not touched — but I was about to write that into the SUMMARY as a verified claim, and on checking there was **no test** covering that function at all. `test_validate_compatibility_kmer_size_mismatch` looks like it does, but it exercises `validate_compatibility` (the *in-memory* route's validator, which legitimately takes `&[&Self]`), not the external-sort one. Writing "pinned by the existing test" would have been a false claim in exactly the class this phase has spent three plans removing.
- **Fix:** Added `prefix_cache_kmer_size_mismatch_keeps_its_error_text`, which drives the real prefix-cache route with two genuinely incompatible inputs (k=31, k=51) and asserts the message's exact wording, its hint line, and — the part the refactor actually risked — that the `verbose` diagnostic reports **each database's own header values**. Also removed the false claim from Deviation 1 rather than leaving it standing.
- **Files modified:** `tests/merge_routing_tests.rs`
- **Verification:** **Observed RED** under a mutation that reports database 1's k-mer count in database 2's diagnostic line. Restored from the pre-mutation copy and re-verified clean (`git diff --stat src/database/format.rs` empty after restore).
- **Committed in:** `dc1c25a`

---

**Total deviations:** 8 auto-fixed (5 bug / 2 plan-gate corrections / 1 blocking tooling)
**Impact on plan:** Deviations 1–3 are corrections needed to satisfy the plan's own `-D warnings` gate. Deviation 4 is the plan's own instruction executed faithfully and then made *testable* rather than merely described. Deviations 5–6 are two of the same recurring pattern this phase has now hit three times (03-06, 03-07, 03-09): a whole-file `grep` gate measures prose, so the measurement is reported and a discriminating gate substituted. Deviation 8 is the one worth carrying forward: it is a claim I was about to make that turned out to be untested, caught by checking instead of asserting. No file outside the plan's `files_modified` was edited except the planning ledger named in Deviation 7.

## Plan acceptance gates — measured

### Task 1

| Gate | Expected | Measured |
|---|---|---|
| `grep -c 'fn read_header_of' src/database/format.rs` | ≥ 1 | **1** — *invariant only, would be 1 before and after* |
| `grep -vE '^\s*//' format.rs \| grep -c 'RKDatabase::from_file_path(&input_paths\[0\])'` | 0 | **0** (was 1) — *DISCRIMINATES* |
| `grep -vE '^\s*//' prefix_cache_merge.rs \| grep -c 'RKDatabase::from_file_path'` | 0 | **0** (was 2) — *DISCRIMINATES* |
| `grep -vE '^\s*//' format.rs \| grep -c 'db_refs'` | 0 | **2** — both in an unrelated test local; see Deviation 5 |
| `grep -c 'At least one input database is required' format.rs` | ≥ 3 | **3** |
| `cargo test --test merge_routing_tests` | exit 0 | **exit 0, 33 passed** |
| `cargo test --test dense_merge_integration_tests` | exit 0 | **exit 0, 3 passed** (4-way composition gate) |
| `cargo test --test merge_route_parity_tests` (03-07's) | exit 0 | **exit 0, 5 passed** — its `384 * N` budget exceeds the new 96, so 03-07's in-memory arm survived the model change |

### Task 2

| Gate | Expected | Measured |
|---|---|---|
| `grep -c 'PREFIX_CACHE_MIN_BUFFER_MB' format.rs` | ≥ 2 | **4** (declaration, doc reference, comparison, log line) |
| `config.temp_dir.join("external_sort_merge_output.tmp")` survives only in the `None` fallback | confirm by reading | **confirmed** — one occurrence, at the `None` arm of the `match` |
| `grep -c 'merge_temp_subdir_path' format.rs` | ≥ 1 | **1** — the call site (the accessor itself is 03-02's, `d493bfb`) |
| `cargo test --test merge_routing_tests` | exit 0, new test present | **exit 0, 33 passed**, `prefix_cache_intermediate_result_is_inside_the_raii_subdir_and_reclaimed ... ok`; **observed RED** pre-fix |
| `cargo test --test merge_cleanup_tests` | exit 0 | **exit 0, 26 passed** |

### Task 3

| Gate | Expected | Measured |
|---|---|---|
| `grep -c 'INMEMORY_BYTES_PER_KMER'` / `STREAMING_…` / `PREFIX_CACHE_…` | each ≥ 2 | **5 / 4 / 3** |
| `grep -vE '^\s*//' format.rs \| grep -c 'UNDER-estimate'` | 0 | **0** — the prohibited false direction claim is not in the source |
| `grep -c 'saturating_mul(24)' format.rs` | 0 | **0** (was 2 in code; both prose mentions reworded) — *DISCRIMINATES* |
| `grep -c 'saturating_add(total)' format.rs` | ≥ 1 | **0** — unsatisfiable form artifact; see Deviation 6 |
| `cargo test --lib summing_two_near_max_headers_saturates_instead_of_panicking` | 1 passed | **1 passed** — *DISCRIMINATES*: **RED** with "attempt to add with overflow" pre-fix |
| `grep -c 'estimated_bytes_for_route' format.rs` | ≥ 2 | **5** (definition, doc × 2, the `merge_databases` call, the test) |
| `grep -c 'RECORD count' format.rs` / `'SUM OF COUNTS' table.rs` | ≥ 1 each | **1 / 1** |
| `grep -c 'ACCEPTED AND IGNORED' merge_config.rs` | ≥ 1 | **1** |
| `grep -c 'BYTES_PER_KMER_ESTIMATE[ ]=[ ]96'` / `[ ]=[ ]24` | ≥ 1 / 0 | **1 / 0** |
| `grep -c 'test_python_budget_model_tracks_the_core'` | ≥ 1 | **2** (definition + the constant's comment) |
| `git status --porcelain pyo3/src/` | empty | **empty** — only the test file changed |
| `cargo test --test merge_routing_tests` | exit 0 | **exit 0, 33 passed** |
| `cargo test` | exit 0 | **exit 0, 409 passed, 0 failed, 19 binaries** |
| `cargo clippy --all-targets -- -D warnings` (root, pyo3) | exit 0 | **exit 0 / exit 0** |
| `rustfmt --check` on the 5 touched Rust files | clean | **clean** |
| RED evidence recorded for the 5 discriminating tests | yes | **recorded above** |

### Which gates are NOT evidence

Per the plan's own warning, several of these are **INVARIANT** or **REGRESSION** gates, not proof the fix works: `fn read_header_of` count (1 before and after), `At least one input database is required` count, `merge_temp_subdir_path` count, the `size_of` pins, and the `At least one input…` / constant-count greps. The behavioural evidence that this plan's changes matter is the `48 * N` model-change routing test, the near-max saturating-sum unit test, the prefix-cache reclamation test, the two header-only tests, and the external-sort error-text test — **all five of which were observed RED** against pre-fix code or a mutation.

## Residual — MERGE-02/MERGE-04's Python surface ships unexecuted

Carried forward from 03-07, and this plan adds to it rather than relieving it:

- **No pyo3 test in this phase can be executed.** `maturin build`/`develop` refuse to run (`pyo3/pyproject.toml` sets `python-source = "."` with `module-name = "pyrustkmer"` while `pyo3/pyrustkmer/` has never existed in git history — CI's `pyo3-build` job runs `maturin build`, so that job cannot be green as configured), and `addopts` hard-codes `--cov-fail-under=80` against a compiled extension, so every pytest run exits 1 even when green. `.github/workflows/ci.yml` has no pyo3 pytest job at all.
- **This plan changed a number the Python side depends on and could not run a single Python assertion about it.** Its own gates are grep-based and extension-free arithmetic, both recorded above. `test_python_budget_model_tracks_the_core` is correct-by-construction and will be the first thing to fail when the extension is rebuilt — **if** the two copies have drifted by then, which is exactly the point of writing it.
- **Plan 03-10 (wave 3) still changes `PyDatabase::merge` semantics with zero Python-level verification**, for the same reason. A human should weigh both at ship time.
- **The one-line fix that would unblock all of it** is deleting the `python-source` key from `[tool.maturin]` — a pure-Rust extension with no Python sources to package. It is recorded in `deferred-items.md` and is a packaging-config change outside this plan's scope.

## Known Stubs

None. Every assertion added by this plan is wired to live production code; no fixture is mocked, no value is hard-coded to make a test pass, and no `#[ignore]`d or `todo!` test was left behind. The one `unrun-verify` entry in the broken-windows ledger is the pyo3 situation above, which is a tooling defect in `pyo3/pyproject.toml`, not a stub in this plan's code.

## Threat surface scan

No new trust boundary is crossed beyond the plan's own STRIDE register. `read_header_of` and `estimated_bytes_for_route` are read-only public observations on existing data; `read_header_of` opens a file with the same permissions and the same validation `from_file_path` already applies. No new network endpoint, no new auth path, no new file access pattern, no schema change. The register entries T-03-31 … T-03-35 are all implemented and each has a test named above.

## Issues Encountered

- **`cargo` is not on `PATH`** in this executor's environment. Resolved with `export PATH="$HOME/.cargo/bin:$PATH"`, as plans 03-06 and 03-07 also had to do.
- **`gsd_run` is not on `PATH`** either. Resolved by invoking `.opencode/gsd-core/bin/gsd_run` with `$PWD/.opencode/gsd-core/bin` prepended.
- **`/tmp/opencode` is not writable** (`Permission denied`), so the `size_of` probe was run in a `mktemp -d` directory instead. Result: `KmerEntry` and `(u128, u32)` are both exactly 32 B — which is what let the constant's derivation be stated as arithmetic rather than as an assertion.
- **`ProcessingError` is not `anyhow::Error`.** The tightened route-probe helper initially took `&anyhow::Error`; the merge API returns `ProcessingResult`, so the signature is `&rustkmer::ProcessingError`. No new derives were added to `src/error.rs`.
- **Whole-file `grep -c` gates constrain documentation, not just code** (Deviations 5 and 6, and the reworded `saturating_mul(24)` prose). Same lesson as 03-06's Deviation 5 and 03-07's Deviation 5; recorded a third time because it has now recurred in three consecutive plans in this phase.

## Self-Check: PASSED

- **Commits exist and are ancestors of HEAD:** `8cbaa11`, `11a43dd`, `33882b1`, `dc1c25a` — verified via `git merge-base --is-ancestor`.
- **`commits: 4` is MEASURED, not narrated:** `git rev-list --count 8122730..HEAD` → 4, with `plan_head_before: 8122730` and `plan_head_after: dc1c25a`.
- **`actuals.tokens: 18050`** is `chars/4` over the realized `src/` + `tests/` + `pyo3/tests/` diff (72,202 chars) — the same scale as an `estimateTokens`, not a harness token count. This plan's frontmatter carries no `estimate` block, so there is nothing to pair it against yet.
- **No accidental deletions:** `git show --first-parent --diff-filter=D --name-only HEAD` prints nothing for each of the three task commits.
- **Out-of-scope files untouched:** `pyo3/src/`, `tests/fixtures/`, `src/database/streaming_merge.rs`, `tests/merge_route_parity_tests.rs`, `tests/golden_sha256_tests.rs`, `src/cli/`, `src/io/` — all clean via `git status --porcelain` / `git diff`.
- **No mutation residue:** every RED run was reverted by a second targeted edit; the final `INMEMORY_BYTES_PER_KMER` is 96 and the final sum is the saturating fold (both re-read from disk after the revert and confirmed by the green suite).
- **No production `unwrap()`/`expect()` added** — the five in the diff are all inside the pre-existing `#[cfg(test)]` module, which already uses them throughout.
- **`rustfmt --check` clean** on all five touched Rust files. Pre-existing rustfmt drift in `src/cli/commands/count.rs` and `tests/parallel_count_tests.rs` was left alone by formatting the files explicitly rather than running `rustfmt src/lib.rs` (which follows `mod` declarations and would have reached them — the trap `deferred-items.md` warns about).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **G2 is half-closed and the remaining half is now correctly scoped.** Every merge route's *inputs* are header-only. The substantive half — streaming the merged output instead of accumulating it at `format.rs:887-908` — is plan 03-10's, and it depends on this plan. The peak arithmetic this plan's comment documents (`32N + 64U .. 32N + 68U`) is exactly what 03-10's `/proc/self/status` test should MEASURE, so the two are now complementary rather than redundant.
- **Plan 03-10 is safe to run against this tree.** No per-k-mer constant is pinned in a way that this change breaks: `tests/merge_route_parity_tests.rs` pins none at all and its `384 * N` budget exceeds the new 96 (`grep -c BYTES_PER_KMER` → 0). The 1 GB floor is gone, so `--max-memory` is finally honoured on the prefix-cache path.
- **One thing 03-10 should know:** `merge_databases_streaming` now takes `kmer_size`/`canonical` from a `DatabaseHeader` rather than an `RKDatabase`. If 03-10 restructures that function, keep the read header-only — the `header_only_read_agrees_with_the_materializing_loader` test exists to catch exactly that regression.
- **Still open from `03-VERIFICATION.md`:** nothing from G1 (03-06) or G3 (03-07). G2 closes when 03-10 lands. After that, `/gsd-verify-work 03` should be able to re-verify all three gap-closure runs.
- **Deferred items this plan did not touch, and should not:** the prefix-cache partial-merge silent loss (WR-04 — worse than recorded, and the verifier escalated it), the `rustkmer_sort_*.chunk` sweep gap, and the two `pyo3` tooling defects that block every Python-level check in this phase.

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*
