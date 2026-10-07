---
phase: 03-memory-safety
plan: 08
subsystem: testing
tags: [rust, rkdb, golden-fixtures, differential, u64, u128, mutation-testing, dense-storage, doc-honesty]

# Dependency graph
requires:
  - phase: 03-memory-safety
    provides: "03-VERIFICATION.md finding WR-03, measured: `git diff --stat 6230ba9..HEAD -- tests/fixtures/` is empty, so the DENSE-02 golden binary re-hashed static Phase-1 files and could not see write-path drift"
  - phase: 03-memory-safety
    provides: "Plan 03-06 DELETED `src/hash/key.rs` and the key enum, which made four docstrings in this plan's sole owned file name a type that no longer exists; plan 03-07 deleted the `read_from` endianness heuristic and left the record codec and all 12 fixtures byte-identical"
provides:
  - "`dense_write_path_bytes_match_a_hand_built_reference` — the first test in the phase that drives `KmerCounter` -> `get_all_counts` -> `from_kmer_pairs` -> `to_file_path` and compares the emitted bytes against a reference the TEST builds with `to_le_bytes()`"
  - "`dense_k32_high_bytes_are_zero_on_disk` — the `2^(2k) <= 2^64` bound asserted from the FILE at its tight end: 8 low bytes of `u64::MAX` + 8 zero bytes"
  - "`write_read_write_is_byte_idempotent` — a write must depend on the data, not on insertion order or an uninitialised header field"
  - "A corrected module docstring with a per-test table of what each test observes and what it does NOT, replacing a false 'differential rather than a tautology' claim"
  - "Mutation-proven red/green split: BOTH new write-path tests RED under `v as u128 ^ (1u128 << 96)` while the committed-fixture re-hash stayed GREEN"
affects: [phase-04-benchmark, DENSE-02, golden-fixtures, W7]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 6023
  tasks: 1
  commits: 1

# Commit ledger — MEASURED with `git rev-list --count`, never narrated (#3968).
commits: 1
plan_head_before: 1c44efd
# The post-TASK state (the single task commit landed). The plan-metadata commit
# that carries this file is its child; a commit cannot contain its own hash, so
# this field names the stable, verifiable parent rather than a self-reference.
plan_head_after: 4e9af47

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The reference arm is a BYTE STRING, not a second call. `from_kmer_pairs` is a pure function of its `Vec<(u128, u32)>`; comparing it against itself on the same input is green under any corruption applied before the call, so the expected bytes must be `to_le_bytes()` of values the test computed itself"
    - "Assertion messages carry the first differing byte offset and both arms' lengths — a bare `assert_eq!` over a multi-hundred-byte arm pair prints a wall of hex without saying which arm moved"
    - "An input fixture's claimed property is asserted, not commented: the `KMER_TABLE` canonicality check turns 'already canonical k-mers' into a real gate, so a canonicalization change fails loudly instead of silently counting a different set"
    - "A test that reads a fixed-offset slice of a file pins the offset too: the one-entry data section is asserted to be exactly 20 bytes, which re-pins the 42-byte header without a second constant to drift"

key-files:
  created:
    - ".planning/phases/03-memory-safety/03-08-mutation-evidence.md — the raw captured RED run under the injected widening, committed as Task 1 step 6 evidence"
  modified:
    - "tests/golden_sha256_tests.rs — module docstring rewritten (false claim deleted, per-test observation table added, all four deleted-type mentions rewritten); `KMER_TABLE`, `hand_built_reference`, `production_write_path`, `read_data_section`, `describe_difference`, `table_is_already_canonical` added; three new tests"

key-decisions:
  - "The reference arm is a byte string the test assembles, NOT a second `from_kmer_pairs` call on the same `Vec<(u128, u32)>`. That earlier shape compared one pure function with itself: under the widening mutation both arms wrote the same corrupted high eight bytes and `assert_eq!` stayed GREEN. The reference here touches the encoder and nothing else"
  - "The honest scope limit is stated in the test's own docstring rather than omitted: BOTH arms call `encode_kmer_bytes_u128`, so an encoder change moves both arms together and this test stays green. That is deliberate — the encoder is not what this test guards, `tests/merge_route_parity_tests.rs` guards the record codec, and the committed-fixture re-hash still guards committed bytes. What this test guards is the one link nothing else covers: the dense counter's widening as it reaches the file"
  - "All four mentions of the deleted key enum were rewritten to describe the MECHANISM (the dense-storage width narrowing), and the two `KmerEntry` mentions were deliberately KEPT because that type survives. No true claim was deleted to satisfy a grep gate"
  - "The k=32 tight-bound test drives the counter with `canonical: false`, because the canonical form of a 32-base T k-mer is 32 bases of A (its reverse complement encodes to 0), so NO canonical k-mer encodes to `u64::MAX`. That fact is asserted in the test (`assert_ne!` on the reverse complement) so the non-canonical choice cannot silently rot"
  - "`write_read_write_is_byte_idempotent` is labelled as what it is: it is NOT a guard for the widening mutation and stayed GREEN under it, because a consistently-corrupted write is still idempotent. Its value is a different class of drift — insertion-order dependence and uninitialised header fields — which the manifest re-hash structurally cannot see"
  - "`tests/golden_tests.rs` was deliberately left unchanged — see the judgement recorded below"

patterns-established:
  - "A test that hashes COMMITTED artifacts proves those artifacts are unchanged; it says nothing about the code that produced them. Any file whose mandate is 'no docstring may claim something false' must therefore also drive the production path, or its own green is the tautology it accuses others of"
  - "A byte-identity guard needs a reference arm that traverses NONE of the code under test. Sharing a helper between the arms is not a shortcut — it is the specific reason the guard cannot fail"

requirements-completed: [DENSE-02]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "A test in this binary drives the production dense write path (KmerCounter -> get_all_counts -> from_kmer_pairs -> to_file_path) and compares the emitted bytes against a reference the test builds itself, so a mutation of the u64 -> u128 widening turns it red"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/golden_sha256_tests.rs#dense_write_path_bytes_match_a_hand_built_reference (8 literal k=21 kmers, 8 distinct, counts up to 5; observed RED at data-section byte 12 — production 0x01 vs reference 0x00 — under the injected widening)"
        status: pass
      - kind: other
        ref: "mutation `v as u128 ^ (1u128 << 96)` in src/hash/table.rs::get_all_counts -> this test FAILED, golden_rkdb_sha256_unchanged_post_dense stayed GREEN; raw run in .planning/phases/03-memory-safety/03-08-mutation-evidence.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "The encoder's `2^(2k) <= 2^64` bound, which holds with equality at k=32, is asserted ON DISK: 8 bytes of u64::MAX little-endian followed by 8 zero bytes followed by the 4-byte little-endian count"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/golden_sha256_tests.rs#dense_k32_high_bytes_are_zero_on_disk (observed RED under the same mutation: data[8..16] read [0,0,0,0,1,0,0,0])"
        status: pass
    human_judgment: false
  - id: D3
    description: "A write depends only on the data: write, read back with the production reader, write again, and the two files are byte-identical"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/golden_sha256_tests.rs#write_read_write_is_byte_idempotent (green; correctly stayed GREEN under the widening mutation, since a consistently-corrupted write is still idempotent)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The static committed-fixture re-hash survives, and the module docstring no longer claims a pre/post differential it does not perform; the four docstring mentions of the key type plan 03-06 deleted are rewritten to describe the mechanism"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/golden_sha256_tests.rs#golden_rkdb_sha256_unchanged_post_dense + #golden_manifest_covers_every_fixture_this_binary_checks (2 tests unchanged; 12 fixtures match the manifest)"
        status: pass
      - kind: other
        ref: "grep -c 'differential rather than a tautology' -> 0 (was 1); grep -c KmerKey -> 0 (was 4); grep -vE '^\\s*//' | grep -c KmerEntry -> 0 on code lines with the 2 doc mentions kept; git status --porcelain tests/fixtures/ -> empty"
        status: pass
    human_judgment: false
  - id: D5
    description: "The reasoned decision to leave `tests/golden_tests.rs` unchanged even though it shares the static-fixture property"
    verification: []
    human_judgment: true
    rationale: "A scope judgement, not a testable behaviour. `golden_tests.rs` reads the same committed manifest and is outside this phase's diff, its own file comment is already candid that both binaries read the same manifest, and adding a second write-path differential there would duplicate the guard this plan installs without adding discrimination — a duplicated guard costs maintenance and buys no new observation. Recorded as a deliberate non-action so a later maintainer does not read the omission as an oversight."
  - id: D6
    description: "DENSE-02 is closed on evidence, not assertion: no test in the phase could previously see the dense widening drift, and now two can, both observed RED before being called done"
    requirement: DENSE-02
    verification:
      - kind: other
        ref: "cargo test -> exit 0, 19 binaries, 225 lib tests, 0 'test result: FAILED'; cargo clippy --all-targets -- -D warnings -> exit 0; rustfmt --check tests/golden_sha256_tests.rs -> clean"
        status: pass
    human_judgment: false

# Metrics
duration: 4 min
completed: 2026-10-07
status: complete
---

# Phase 03 Plan 08: Real DENSE-02 Write-Path Differential Summary

**WR-03 is closed: the DENSE-02 golden binary now drives `KmerCounter` -> `get_all_counts` -> `to_file_path` and compares the emitted bytes against a reference the test assembles itself, and both new write-path tests were observed RED under an injected `u64 -> u128` widening while the old committed-fixture re-hash stayed GREEN.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-07T12:32:49Z
- **Completed:** 2026-10-07T12:37:09Z
- **Tasks:** 1
- **Files modified:** 2 (1 modified, 1 created)

## The defect this plan closes

Gap **WR-03** (= `03-VERIFICATION.md`, confirmed by `git diff --stat 6230ba9..HEAD -- tests/fixtures/` being empty). `tests/golden_sha256_tests.rs` re-hashed the 12 committed Phase-1 `.rkdb` fixtures against a committed Phase-1 manifest. **Neither was produced by any Phase-3 code at test time**, so the test went green whether the dense `u64 -> u128` widening was correct, whether the 20-byte v2 record still wrote, or whether the write path worked at all.

Worse, the docstring asserted the opposite:

> it was GREEN before the KmerKey swap landed — that pre-swap pass is what makes the post-swap pass meaningful as a differential rather than a tautology

Both passes were green for the same reason: the test never invoked the swapped code. The claim was false, and it would have misled the next maintainer into trusting a green that proved nothing.

The property DENSE-02 names was never the problem — the verifier confirmed it holds by construction. The **test** was the problem.

## Accomplishments

- **A real differential now exists.** `dense_write_path_bytes_match_a_hand_built_reference` drives the production dense path and compares the bytes on disk against a reference built from the test's own literal k-mer table with `to_le_bytes()`. The reference traverses neither `KmerCounter::get_all_counts`, nor `RKDatabase::from_kmer_pairs`, nor the record codec, nor `to_file_path` — so a widening defect moves exactly one arm.
- **The tight end of the encoder bound is asserted from the file.** `dense_k32_high_bytes_are_zero_on_disk` writes a 32-base T k-mer (encoded value exactly `u64::MAX as u128`, the `2^(2k) <= 2^64` bound at equality) and asserts the 16 k-mer bytes on disk are `u64::MAX`'s 8 little-endian bytes followed by eight `0x00`. The zero-extension is now observed in the file rather than asserted about the code.
- **Order-dependence and uninitialised header fields are covered.** `write_read_write_is_byte_idempotent` writes, reads back with the production reader, writes again, and requires byte-identity — a drift class the manifest re-hash structurally cannot see, because its fixtures are never regenerated.
- **The false claim is gone and replaced with something true.** The module docstring now carries a per-test table of what each test observes and what it does **not**, and the sentence claiming a differential is deleted rather than reworded.
- **W7 closed.** All four docstring mentions of the key type plan 03-06 deleted are rewritten to describe the mechanism. The two `KmerEntry` mentions were deliberately kept — that type survives, and deleting a true claim to satisfy a grep gate would be the same sin the file exists to prevent.
- **No golden fixture and no manifest entry was regenerated.** `git status --porcelain tests/fixtures/` is empty. Phase 1 D-10 capture-first discipline preserved.

## Task Commits

1. **Task 1: Replace the false differential claim with a real write-path differential** — `4e9af47` (test)

Task 1 is a `tracer` task. Its feedback gate re-ran the plan's `<verify>` verbatim end-to-end and passed (5 passed, exit 0); with no expansion task in the plan, that was the whole of the tracer.

**Plan metadata:** *(the commit carrying this file — a commit cannot record its own hash)*

## Files Created/Modified

- `tests/golden_sha256_tests.rs` — module docstring rewritten; `KMER_TABLE` / `hand_built_reference` / `production_write_path` / `read_data_section` / `describe_difference` / `table_is_already_canonical` added; three new tests; the two existing tests and their manifest helpers untouched
- `.planning/phases/03-memory-safety/03-08-mutation-evidence.md` — **new**: the raw captured RED run under the injected widening

Nothing else was edited. `src/` is byte-identical to its pre-plan state, and `src/hash/table.rs` in particular was restored from the committed state rather than reverted by hand.

## RED evidence — observed, not asserted

The dense widening in `src/hash/table.rs::get_all_counts` was changed from `*r.key() as u128` to `*r.key() as u128 ^ (1u128 << 96)`, the binary was run, and the tree was then restored with `git checkout -- src/hash/table.rs`.

| Test | Under the injected widening |
|---|---|
| `dense_write_path_bytes_match_a_hand_built_reference` | **RED** — `first difference at data-section byte 12: production arm 0x01, test-built reference 0x00 (production arm 160 bytes, reference 160 bytes)` |
| `dense_k32_high_bytes_are_zero_on_disk` | **RED** — `left: [0, 0, 0, 0, 1, 0, 0, 0]`, `right: [0, 0, 0, 0, 0, 0, 0, 0]` |
| `golden_rkdb_sha256_unchanged_post_dense` | **GREEN** ← the whole point: the old binary could not see this defect |
| `write_read_write_is_byte_idempotent` | GREEN — correct, and it is not a guard for this defect (a consistently-corrupted write is still idempotent) |
| `golden_manifest_covers_every_fixture_this_binary_checks` | GREEN |

**BOTH** write-path tests went red, not one. That is the load-bearing observation of this plan: a reference arm sharing `from_kmer_pairs` and the record codec with the arm under test would have stayed green, and only the k=32 assertion would have caught the mutation. A single catching test is not the same claim as a differential that catches it. The full raw run is committed at `.planning/phases/03-memory-safety/03-08-mutation-evidence.md`.

## Decisions Made

- **The reference arm is a byte string, not a second call.** The plan's own earlier draft compared `from_kmer_pairs` against `from_kmer_pairs` on the same `Vec<(u128, u32)>` — a pure function compared with itself, green under any corruption applied before the call. The expected bytes here are `to_le_bytes()` of values the test computed from its own literal table.
- **The scope limit is stated in the test, not omitted.** Both arms call `encode_kmer_bytes_u128`, so an encoder change moves both arms together and this test stays green. That is deliberate and it is now written down where the next maintainer will read it. The encoder is covered by the committed-fixture re-hash and the record codec by `tests/merge_route_parity_tests.rs`; what this test covers is the one link nothing else does.
- **`KmerCounter::increment` takes an already-encoded `u128`.** Canonicalization happens in the CLI (`src/cli/commands/count.rs:396`), not in the counter, so the test's `encode_kmer_bytes_u128` call is input construction — the same step `process_one_record` performs — not a shared dependency with the code under test. The plan's phrasing ("`KmerCounter`'s canonicalization is a no-op on it") described a canonicalization step the counter does not have; the requirement it encodes is still right, so the fixture is canonical anyway and its canonicality is now **asserted** by `table_is_already_canonical` rather than assumed in a comment.
- **The k=32 test drives the counter with `canonical: false`.** The canonical form of a 32-base T k-mer is 32 bases of A, so no canonical k-mer encodes to `u64::MAX` — the bound value is only reachable on the non-canonical path, which is exactly what `count --no-canonical` produces. The header flag is irrelevant to the claim under test. `assert_ne!(reverse_complement_u128(encoded, 32), encoded)` pins that reasoning inside the test so it cannot silently rot.
- **`write_read_write_is_byte_idempotent` is labelled as what it is**, not as a widening guard. It stayed GREEN under the mutation, and that is correct: a consistently-corrupted write is still idempotent. Its value is a different class of drift.
- **All four `KmerKey` mentions rewritten; both `KmerEntry` mentions kept.** No true claim was removed to satisfy a gate.

## Judgement on `tests/golden_tests.rs` — deliberately unchanged

`tests/golden_tests.rs` reads the same `golden_manifest.sha256` and therefore shares the static-fixture property: 12 committed files against a committed manifest, none produced by Phase-3 code at test time. It was left alone, for three reasons:

1. It is a Phase-1 artifact outside this phase's diff, and this plan's `files_modified` is exactly one file.
2. Its own file comment is already candid that both binaries read the same manifest — the overclaim this plan had to remove existed only here.
3. Adding a second write-path differential there would **duplicate** the guard this plan installs without adding discrimination. A duplicated guard costs maintenance and buys no new observation; a duplicated *differential* is worse, because a second copy of a differential is a second thing to keep independent, and independence is the property most easily lost by accident.

Left unchanged, deliberately. If a future phase wants the write-path guard in that binary too, it should move the guard there rather than copy it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's k=32 test premise was unsatisfiable at canonical: true**
- **Found during:** Task 1, designing the tight-bound fixture
- **Issue:** The plan's step 4 asks for "a k-mer whose encoded value is exactly `u64::MAX as u128`" at k=32, with no statement about the canonical flag. At k=32 a 32-base T k-mer encodes to `u64::MAX`, but its reverse complement is 32 bases of A, which encodes to `0` — so the canonical form of that k-mer is a *different* value. No **canonical** k-mer encodes to `u64::MAX`, and the tight end of the bound is therefore only reachable on the non-canonical path (which is a real production path: `count --no-canonical`). Implementing the step literally with `canonical: true` would have made the fixture's encoded value something other than `u64::MAX`, silently weakening the test from "the tight bound" to "some k-mer".
- **Fix:** The k=32 test drives `KmerCounter::new(32, false, 1, 1)` and passes `canonical: false` to the database constructor, with the reasoning recorded in the test's own docstring AND pinned by an assertion (`assert_ne!(reverse_complement_u128(encoded, 32), encoded)`) so the choice cannot rot. The test still asserts the exact `u64::MAX` value it was written to assert, and still asserts the eight zero high bytes.
- **Files modified:** `tests/golden_sha256_tests.rs`
- **Verification:** `cargo test --test golden_sha256_tests` → 5 passed; under the injected widening this test went RED at `data[8..16]`, which is the assertion the plan wanted it to carry.
- **Committed in:** `4e9af47`

**2. [Rule 1 - Bug] The `:111-114` threat paragraph carried the same false claim the plan exists to remove**
- **Found during:** Task 1, step 1a
- **Issue:** The plan says "Keep the `:111-114` threat paragraph as it is; its `KmerEntry` reference is TRUE and must stay." The mention is true, but the paragraph around it is not: "the failure mode this guards is a write path that stops zero-extending `u64 -> u128`, or that changes `KmerEntry`'s 16 + 4 byte v2 layout, or that alters the header literal. **Any of those makes the 12 hashes diverge.**" They do not. That sentence is WR-03 restated in the test's own docstring, and this plan's entire purpose is to remove exactly that claim. Keeping it verbatim would have shipped the defect in a reworded location.
- **Fix:** The paragraph was kept and its `KmerEntry` mention preserved, but re-scoped honestly: it now names the failure modes the **binary as a whole** guards, and states explicitly that this particular test can detect a hand-edited or truncated committed fixture and cannot detect any of the three drift modes. The plan's instruction to keep it "as it is" was read as protecting the mention, not the false sentence.
- **Files modified:** `tests/golden_sha256_tests.rs`
- **Verification:** the `KmerEntry` mention survives at the same paragraph; the mutation run confirms the paragraph's new claim is true — the fixture re-hash stayed GREEN under a real write-path defect.
- **Committed in:** `4e9af47`

**3. [Rule 1 - Bug] The plan described canonicalization as something `KmerCounter` does**
- **Found during:** Task 1, step 3
- **Issue:** The plan's step 3 says each table k-mer must be already canonical "so `KmerCounter`'s canonicalization is a no-op on it". `KmerCounter` does not canonicalize — `increment` takes an already-encoded `u128`, and canonicalization happens in the CLI at `src/cli/commands/count.rs:396`. The requirement behind the sentence is still correct (the test's table must be what a canonical-mode run would hold), but stated as written it describes a code path that does not exist, in a file whose mandate is that no docstring claims something false.
- **Fix:** The fixture is canonical anyway, and its canonicality is now **asserted** by a new `table_is_already_canonical` helper that runs `canonical_kmer_u128` over every table entry and fails with an explicit message if any entry's canonical form differs. The test's docstring states where canonicalization actually happens and why encoding here is input construction rather than a shared dependency.
- **Files modified:** `tests/golden_sha256_tests.rs`
- **Verification:** 5 passed; the canonicality check runs on every execution of the differential and would fail loudly, rather than letting a canonicalization change silently shrink the compared set.
- **Committed in:** `4e9af47`

**4. [Rule 3 - Blocking] `*.txt` is gitignored, so the raw mutation evidence could not be committed**
- **Found during:** Task 1, staging the evidence file
- **Issue:** `.gitignore:56` carries a blanket `*.txt`, so `git add` of the captured `cargo test` output was refused. The project's `git.branching_strategy` is `none` and committing directly on `dev` is the configured behaviour, so this was purely a staging blocker.
- **Fix:** The evidence was re-emitted as `.planning/phases/03-memory-safety/03-08-mutation-evidence.md` — a fenced ```` ```text ```` block inside an HTML comment header naming the mutation and the revert command. Content is byte-identical to the raw run; the extension change was the only difference. **No `-f` was used** and no gitignored path was force-staged.
- **Files modified:** `.planning/phases/03-memory-safety/03-08-mutation-evidence.md`
- **Verification:** `git check-ignore` on the `.md` path returns non-zero (not ignored); the file is committed in `4e9af47`.
- **Committed in:** `4e9af47`

---

**Total deviations:** 4 auto-fixed (3 bug, 1 blocking)
**Impact on plan:** No scope expansion — one file modified, one evidence file created, `src/` byte-identical. Deviations 1 and 2 are the substantive ones: read literally, the plan would have shipped a k=32 fixture that is not the tight bound (test silently weaker than claimed) and would have kept the false "any of those makes the 12 hashes diverge" sentence alive in the one file whose mandate is that no docstring claims something false. Deviation 3 made a claimed fixture property an assertion instead of a comment.

## Plan acceptance gates — measured

### Task 1 (all PASS)

| Gate | Expected | Measured |
|---|---|---|
| `cargo test --test golden_sha256_tests` | exit 0, 5 passed | **exit 0, 5 passed** |
| `grep -c dense_write_path_bytes_match_a_hand_built_reference` | ≥ 1 | **2** |
| `grep -c dense_k32_high_bytes_are_zero_on_disk` | ≥ 1 | **2** |
| `grep -c write_read_write_is_byte_idempotent` | ≥ 1 | **2** |
| `grep -c 'differential rather than a tautology'` | 0 | **0** — *discriminates* (was 1) |
| `grep -c KmerCounter` | ≥ 1 | **7** — *discriminates* (was 0) |
| `grep -c to_le_bytes` | ≥ 2 | **7** |
| `grep -vE '^\s*//' \| grep -c KmerEntry` | 0 | **0** — *regression gate only: 0 before and 0 after; it constrains future edits from routing the reference through the record codec, it does not distinguish this tree from the broken one* |
| `grep -c KmerKey` | 0 | **0** — *discriminates* (was 4) |
| `git status --porcelain tests/fixtures/` | empty | **empty** — no fixture or manifest regenerated |
| `git status --porcelain src/` | empty after revert | **empty** |
| BOTH new write-path tests RED under the mutation; fixture re-hash GREEN | recorded | **recorded above, raw run committed** |

### Plan-level verification

| # | Check | Result |
|---|---|---|
| 1 | `cargo test --test golden_sha256_tests` | **exit 0, 5 passed** |
| 2 | widening mutation: both new write-path tests RED, fixture re-hash GREEN | **as recorded above** |
| 3 | `git status --porcelain tests/fixtures/` and `src/` | **both empty** |
| 4 | `grep -c KmerKey tests/golden_sha256_tests.rs` | **0** (was 4) |
| 5 | `cargo clippy --all-targets -- -D warnings` (root crate) | **exit 0** |
| 6 | `cargo test` (full suite) | **exit 0** — 19 binaries, 225 lib tests, zero `test result: FAILED` |

### Two gates honestly labelled non-discriminating

Recorded so they are not read as evidence:

- **`grep -vE '^\s*//' … | grep -c KmerEntry` == 0** is a **regression** gate. It is 0 before this plan and 0 after; it does not distinguish the fixed tree from the broken one. It is satisfied, and it is worth having, because it fails if a future edit routes the reference arm back through the record codec — which is a code line. The discriminating weight sits in the mutation red-proof and in `dense_k32_high_bytes_are_zero_on_disk`.
- **`write_read_write_is_byte_idempotent` stayed GREEN under the mutation**, and is not presented as a guard for it. It covers a different class of drift.

The plan's acceptance criteria also anticipated the first of these correctly: the bare `grep -c KmerEntry` would have counted PROSE (2 today, at `:5` and `:113`) and reported a false failure. The comment-excluding form measures what the gate's stated purpose actually needs.

## Known Stubs

None. Every assertion in the new tests is wired to live production code or to a value the test computes from its own literal table; no fixture is mocked, no count is hard-coded to make a test pass, and no `#[ignore]`d test was added. The two pre-existing structural `0 passed` result lines in `cargo test` (`unittests src/main.rs` has no `#[cfg(test)]` module; `tests/golden_generate.rs`'s single test is `#[ignore]`d by design) are pre-existing and untouched, as plan 03-06 recorded.

## Issues Encountered

- **`cargo` is not on `PATH`** in this executor's environment. Resolved with `export PATH="$HOME/.cargo/bin:$PATH"`, as plans 03-06 and 03-07 also had to.
- **`/tmp/opencode` is not writable** (`Permission denied`), as plan 03-07 recorded. The plan start-time and commit-ledger scratch files were written under `$(git rev-parse --git-dir)` instead.
- **`*.txt` is gitignored** (Deviation 4) — the third instance in this phase of a git-level or `.gitignore`-level constraint on where evidence may live. The general lesson, now seen three times: a whole-file `grep -c` gate constrains documentation, and a blanket ignore rule constrains the extension of an evidence artifact. Neither is about the code under test.
- **Whole-file `grep -c` gates constrain documentation, not just code** (plan 03-06 Deviation 5, plan 03-07 Deviation 5d). This plan avoided it by construction: the rewritten docstring explains the deleted-type rewrite without ever naming the type, so `grep -c KmerKey` reads 0 while the reasoning is still fully present.

## Self-Check: PASSED

- **Modified file exists and is committed:** `tests/golden_sha256_tests.rs` — verified present, and clean in `git status --short`.
- **Created file exists and is committed:** `.planning/phases/03-memory-safety/03-08-mutation-evidence.md` — verified present, and not gitignored (`git check-ignore` exits 1).
- **Commit exists and is an ancestor of HEAD:** `4e9af47` — verified via `git merge-base --is-ancestor`.
- **`commits: 1` is MEASURED, not narrated:** `git rev-list --count 1c44efd..HEAD` → 1, with `plan_head_before: 1c44efd` and `plan_head_after: 4e9af47`. Non-zero, so the code changes are genuinely committed and not sitting in the working tree.
- **`actuals.tokens: 6023`** is `chars/4` over the realized `tests/` diff (24,093 chars) — the same scale as the plan's `estimateTokens` scale, not a harness token count. This plan's frontmatter carries no `estimate` block, so there is nothing to pair it against yet.
- **No mutation residue:** `git status --porcelain src/` prints nothing; `src/hash/table.rs` was restored with `git checkout --` from the committed state, not reverted by hand.
- **No accidental deletions:** `git show --first-parent --diff-filter=D --name-only HEAD` prints nothing.
- **Out-of-scope files untouched:** `src/cli/commands/count.rs` and `tests/parallel_count_tests.rs` (pre-existing rustfmt drift, left alone as instructed), `src/database/format.rs` (03-07's), `src/hash/*` (03-06's), `tests/merge_route_parity_tests.rs` (03-07's), `tests/golden_tests.rs` (deliberate), and all of `tests/fixtures/` — `git status --porcelain` empty for every one.
- **`rustfmt --check` clean** on the one file this plan touched. No pre-existing rustfmt drift was reformatted.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **WR-03 is closed on evidence.** DENSE-02 no longer rests on a test that cannot fail: the dense widening is observed on the disk by two independent assertions, both seen RED, and the fixture re-hash survives for the one thing it genuinely detects.
- **W7 is closed.** No docstring in this binary names the type plan 03-06 deleted. A whole-wave grep for it across `src/` and `tests/` now returns nothing outside `src/hash/table.rs`'s historical-reference comments (which 03-06 kept deliberately, to document the T-03-09 panic message's provenance).
- **03-09 can proceed.** Nothing this plan changed is in its scope: `tests/merge_routing_tests.rs` and the admission model are untouched, and no per-k-mer constant is pinned in this file. The `write_read_write_is_byte_idempotent` test uses a `tempfile::TempDir`, so it does not collide with a merge temp-dir convention.
- **03-10 can proceed.** `pyo3/` is byte-identical; this plan ran no pytest and changed no Python surface. The residual 03-07 recorded (03-10's `PyDatabase::merge` semantics change shipping with zero Python-level verification) is unchanged and still worth weighing at ship time.
- **Still open from `03-VERIFICATION.md`: G2** — no merge strategy is memory-bounded (`format.rs:852` loads an input in full on the over-budget path; `:869-876` accumulates the entire merged output). Neither half of the phase's central deliverable is closed until that lands, and G2 is the last of the three gaps.

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*
