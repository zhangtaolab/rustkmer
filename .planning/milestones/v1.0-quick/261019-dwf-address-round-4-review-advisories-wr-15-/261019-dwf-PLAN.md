---
phase: quick-261019-dwf
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/io/fastq.rs
  - docs/api-reference/rust/fastq.md
  - tests/merge_bounded_memory_tests.rs
autonomous: true
requirements: ["ROUND4-REVIEW-ADVISORIES"]
estimate:
  tokens: 36000
  raw_tokens: 24000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "cargo test --lib io::fastq passes including four new tests: the WR-15 gzipped-input regression (total_sequence_length and average_quality on a .gz fixture return the exact decompressed values), the WR-16 truncated-record error test, the WR-17 ASCII-scale pin test, and the IN-12 trailing-garbage test"
    - "grep -c 'for _ in' on src/io/fastq.rs prints 0 — count_sequences no longer iterates record Results without inspecting them (WR-16)"
    - "grep -c '0-40' on src/io/fastq.rs prints 0 and grep -c '0-40' on docs/api-reference/rust/fastq.md prints 0 — the misleading Phred-range doc claim is gone from source and docs page alike (WR-17)"
    - "grep -c 'min_quality_ascii' on src/io/fastq.rs prints at least 2 (signature + doc) — the renamed parameter documents raw Phred+33 ASCII semantics with the Q20-threshold-55 worked example (WR-17)"
    - "grep -c 'byte-identical' on src/io/fastq.rs prints 0 — the MultiGzDecoder comment overclaim is replaced by an accurate statement of the trailing-garbage behavior (IN-12)"
    - "grep -c 'estimated > budget' on tests/merge_bounded_memory_tests.rs prints 0 — both tautological GUARD asserts are replaced by a strict-positivity premise check on the derived estimate (IN-13)"
    - "cargo test --test merge_bounded_memory_tests passes with the two revised GUARD asserts"
    - "count_sequences returns Err (not Ok with a miscount) on a FASTQ whose final record is truncated; the error message carries the record-reading context naming the file path"
    - "cargo test and cargo clippy --all-targets -- -D warnings both pass from the repo root"
  artifacts:
    - "src/io/fastq.rs — total_sequence_length and average_quality route through DefaultCompressedFileReader::open_compressed; count_sequences propagates record errors; filter_by_quality doc/param renamed to raw-ASCII semantics; average_quality return labeled; MultiGzDecoder comment amended; four new in-module tests"
    - "docs/api-reference/rust/fastq.md — filter_by_quality entry updated to the new signature and raw-ASCII semantics"
    - "tests/merge_bounded_memory_tests.rs — the two GUARD asserts assert estimate positivity before deriving the budget"
  key_links:
    - "total_sequence_length/average_quality -> DefaultCompressedFileReader::open_compressed (the same opener process_file, count_sequences, and the fixed FASTA analogues use)"
    - "count_sequences record errors -> ProcessingError::with_context propagation (same error contract as process_file and validate_fastq_file)"
    - "filter_by_quality doc comment in src/io/fastq.rs <-> docs/api-reference/rust/fastq.md entry must state identical raw-ASCII semantics so source and docs page cannot drift"
---

<objective>
Close the five open round-4 review advisories (WR-15, WR-16, WR-17, IN-12, IN-13) from .planning/phases/03-memory-safety/03-REVIEW.md: make the FASTQ statistic helpers compression-aware and error-honest, align the quality-scale documentation with the code via the review's non-breaking option, correct the MultiGzDecoder comment and pin its trailing-garbage behavior, and de-tautologize two premise asserts in the bounded-memory tests.

Purpose: These are public-API correctness defects in the FASTQ I/O surface (a .fastq.gz caller of total_sequence_length/average_quality gets an opaque error or garbage; a corrupt file is counted as sequences; doc-following callers of filter_by_quality get a near-no-op filter) plus test assertions that advertise protection they cannot provide.
Output: src/io/fastq.rs (3 helper fixes + comment amendment + 4 tests), docs/api-reference/rust/fastq.md (1 entry), tests/merge_bounded_memory_tests.rs (2 asserts).
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Advisory bodies (severity, evidence, suggested direction — read before editing):
@.planning/phases/03-memory-safety/03-REVIEW.md

Live code under fix:
- src/io/fastq.rs — helpers at :283-305 (filter_by_quality), :392-415 (count_sequences), :424-442 (total_sequence_length), :451-486 (average_quality); gz switch comment at :67-75; concatenated-gzip regression test to mirror at :592-645
- src/io/fasta.rs — the already-fixed FASTA analogues and their gz regression tests (WR-03 fix pattern): :184-236 and :338-361
- tests/merge_bounded_memory_tests.rs — the two tautological GUARD asserts at :416-424 and :730-737
- docs/api-reference/rust/fastq.md — filter_by_quality entry at :113-125 mirrors the misleading doc claim

Verified live ground truth (2026-10-19): the four affected functions have ZERO callers outside src/io/fastq.rs's own test module and the docs page (repo-wide grep across src/, pyo3/, tests/, examples/, docs/) — no CLI, PyO3, or example consumer exists. Not exposed to Python. CI gates are `cargo clippy --all-targets -- -D warnings` and plain `cargo test` (.github/workflows/ci.yml).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: FASTQ helper behaviors — compression routing (WR-15), error propagation (WR-16), doc/code scale alignment (WR-17)</name>
  <files>src/io/fastq.rs, docs/api-reference/rust/fastq.md</files>
  <behavior>
    - Test (WR-15): a two-record FASTQ gzipped and written with a .gz suffix — total_sequence_length returns the exact sum of decompressed sequence lengths; average_quality returns the exact mean of raw Phred+33 ASCII quality bytes.
    - Test (WR-16): a FASTQ whose final record is truncated (header + sequence only, no plus/quality lines) — count_sequences returns Err whose message contains the record-reading error context naming the file; it never returns Ok counting the broken record.
    - Test (WR-17): with quality lines at ASCII 72/73 (Q39/Q40), a threshold argument of 55 (the documented stand-in for Q20) keeps those records, while a record whose quality line sits at ASCII 43 (Q10) is dropped by the same threshold.
  </behavior>
  <action>
    Fix the three fastq.rs public-helper defects from the round-4 review, mirroring the already-fixed FASTA analogues in src/io/fasta.rs.

    (a) WR-15 — compression-blind opens. `total_sequence_length` (src/io/fastq.rs:424-442) and `average_quality` (src/io/fastq.rs:451-486) each build their reader from a plain buffered constructor over the raw file handle (lines 427-429 and 454-456), so a `.fastq.gz` path is parsed as deflate bytes. Replace both opens with the module's shared compression-aware opener `DefaultCompressedFileReader::open_compressed(path)`, exactly as `count_sequences` does (src/io/fastq.rs:396-405) including its compression-name-aware open-error context wrapper, then hand the returned reader to `bio::io::fastq::Reader::new`. The `CompressedFileReader` trait is defined in this module, so no new import is needed. Keep the existing per-record error propagation in both functions unchanged. This matches the WR-03 fix the FASTA twins of these functions already received (src/io/fasta.rs:184-236).

    (b) WR-16 — swallowed parse errors. The counting loop in `count_sequences` (src/io/fastq.rs:410-413) iterates the records iterator without binding each Result, so a malformed or truncated record is tallied as a sequence and the function returns Ok. Bind each record Result and propagate failures with `ProcessingError::with_context` using the message shape the review body specifies — context naming the file path (matching the sibling functions' style) — incrementing the count only on Ok. This aligns count_sequences with the error contract `process_file` and `validate_fastq_file` already follow.

    (c) WR-17 — doc/code scale mismatch. Align documentation to the code via the review's NON-BREAKING option (the breaking Phred-decode option is deliberately deferred, see <deferred>): `filter_by_quality`'s parameter doc (src/io/fastq.rs:286) cites a numeric Phred quality range while the comparison at :295 tests raw Phred+33 ASCII byte values — a doc-following caller passing a value in that range silently disables filtering since every real quality byte is at least 33. Rename the parameter to `min_quality_ascii`, rewrite the doc to state the raw-ASCII-byte semantics with a worked example (threshold 55 corresponds to Q20), and label `average_quality`'s # Returns doc as the mean of raw Phred+33 ASCII quality bytes (do not change either function's arithmetic). Update the mirrored `filter_by_quality` entry in docs/api-reference/rust/fastq.md (lines 113-125) to the new signature, parameter name, and semantics so the docs page and the source doc comment state the same contract.

    (d) Tests — extend the existing `mod tests` following the fixture style of the concatenated-gzip regression test at src/io/fastq.rs:592-645 (gzip_bytes helper, tempfile with a `.gz` suffix so CompressionType detects it) and the FASTA gz regression at src/io/fasta.rs:338-361: the three tests listed in <behavior>. For the WR-15 fixture reuse known-content records (e.g. quals of ASCII 73 and 72) so the expected length sum and raw-ASCII mean are exact.
  </action>
  <verify>
    <automated>cargo test --lib io::fastq</automated>
  </verify>
  <done>All io::fastq unit tests pass including the three new ones; both statistic helpers open inputs through the shared compression-aware opener; count_sequences fails loudly on a truncated record; the Phred-range doc claim is gone from source and docs page, replaced by raw-ASCII semantics with the renamed parameter; grep -c 'for _ in' on src/io/fastq.rs prints 0.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: MultiGzDecoder comment correction + trailing-garbage behavior pin (IN-12)</name>
  <files>src/io/fastq.rs</files>
  <behavior>
    - Test: a valid single-record FASTQ gzipped as one member, with literal non-gzip bytes appended after the member, written to a .gz-suffixed tempfile — FastqProcessor::read_all returns Err whose message contains the module's record-reading error context (loud failure), proving the reader does not silently stop at the first member and swallow the garbage.
  </behavior>
  <action>
    Amend the MultiGzDecoder switch comment and pin its edge behavior (IN-12, src/io/fastq.rs:67-75). The comment's final sentence (:72) claims the multi-member decoder's output is byte-for-byte the same as the single-member decoder on single-member files; per the review (verified against flate2 1.1.10's multi-mode state machine) that equivalence holds only when zero bytes follow the final member — any trailing non-gzip bytes (padded writes, appended text, a torn second member) now surface as a mid-stream io error where the previous single-member decoder silently stopped at the first member and ignored the rest. Rewrite that sentence to state both facts: equivalence on single-member files with nothing after the final member, and loud failure (instead of silent truncation) on trailing garbage. Then add the regression test from <behavior> to the existing tests module: gzip one valid FASTQ member using the same gzip_bytes helper pattern as src/io/fastq.rs:592-645, append a short literal non-gzip byte string, write to a `.gz`-suffixed tempfile, and assert `FastqProcessor::read_all` (the same process_file to open_compressed path the CLI uses) returns Err containing this module's own record-reading context text in the message — do NOT pin any flate2-internal error wording, which is not stable across versions. This pins the chosen loud-failure semantics so a future flate2 semantic change fails the test instead of passing silently.
  </action>
  <verify>
    <automated>cargo test --lib io::fastq</automated>
  </verify>
  <done>The comment no longer overclaims equivalence (grep -c 'byte-identical' on src/io/fastq.rs prints 0) and accurately describes the trailing-garbage behavior; the new trailing-garbage test passes, asserting Err with the module's own error context; all other io::fastq tests still pass.</done>
</task>

<task type="auto">
  <name>Task 3: De-tautologize the two GUARD premise asserts (IN-13)</name>
  <files>tests/merge_bounded_memory_tests.rs</files>
  <action>
    Fix the two vacuous GUARD asserts in tests/merge_bounded_memory_tests.rs (IN-13): the budget derivation in the RSS-measurement test (lines 416-424) and in `streaming_route_probe_survives_the_to_path_entry_point` (lines 730-737). At both sites the guard checks that the estimate exceeds a value obtained by subtracting one from that same estimate — a comparison that can never fail — while the subtraction itself would panic on underflow in a debug build if the estimate were ever zero (e.g. an empty fixture reaching the path after a future fixture change; the second site has no fixture-size assert protecting it). At each site, assert the meaningful premise directly: that the derived estimate from `RKDatabase::estimated_bytes_for_route(MergeStrategy::InMemory, n)` is strictly greater than zero (a zero estimate means an empty fixture and no selectable streaming budget), and only then derive the budget by subtracting one. Keep the GUARD-prefixed failure-message style, reworded to state the positivity premise. Do not touch the surrounding MergeConfig construction, the temp-dir probes, or any other assertion in either test.
  </action>
  <verify>
    <automated>cargo test --test merge_bounded_memory_tests</automated>
  </verify>
  <done>Both revised tests pass; the tautological comparison is gone from the file (grep -c 'estimated > budget' on tests/merge_bounded_memory_tests.rs prints 0); each site now asserts estimate positivity before the subtraction, so an empty fixture fails the guard loudly instead of panicking on underflow.</done>
</task>

</tasks>

<deferred>
WR-17 Option A — Phred-decoding semantics (REJECTED for this quick task, deliberate): the review's first-listed fix would decode quality bytes before comparing (guarding the +33 offset) and subtract the offset in average_quality's accumulator, making the code match the current documented Phred contract. This is a public-API semantic change: it changes the scale of `average_quality`'s return value and the meaning of `filter_by_quality`'s threshold for every external crate consumer (the functions are public on `rustkmer::io::fastq` and documented on the docs site). Per quick-task scope guidance, the non-breaking doc/code alignment (Option 2) ships here instead; repo-wide grep confirms zero in-repo callers outside the module's own tests, so the alignment fully removes the misleading-contract hazard today. Flipping to Phred-native semantics (or adding Phred-named variants such as `average_phred_score` / `filter_by_phred`) should be a deliberate API decision in a future planned phase, recorded here so it is not lost.
</deferred>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| input file -> parser | Untrusted FASTQ/FASTQ.gz bytes on disk cross into bio's reader and the flate2 decoders via open_compressed |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-dwf-01 | Tampering | count_sequences (src/io/fastq.rs:410-413) | medium | mitigate | Propagate record-parse errors instead of counting malformed records as sequences — corrupt input now fails loudly (WR-16) with a test pinning the truncated-record rejection |
| T-dwf-02 | Tampering | total_sequence_length / average_quality (src/io/fastq.rs:424-486) | medium | mitigate | Route both through the shared compression-aware opener so compressed hostile inputs are decoded and validated like every sibling helper instead of yielding garbage statistics (WR-15), with a gzipped-input regression test |
| T-dwf-03 | Tampering | MultiGzDecoder switch (src/io/fastq.rs:67-75) | low | mitigate | Trailing garbage after the final gzip member already errors loudly; correct the overclaiming comment and pin the loud-failure behavior with a member-plus-junk regression test so the semantics cannot silently regress (IN-12) |
| T-dwf-04 | Tampering | test GUARD asserts (tests/merge_bounded_memory_tests.rs:416-424, 730-737) | low | mitigate | Replace tautological guards with a strict-positivity premise so an empty/degenerate fixture fails the test loudly rather than panicking on underflow or passing vacuously (IN-13) |
</threat_model>

<verification>
From the repo root:
- cargo test --lib io::fastq — all fastq unit tests including the four new ones
- cargo test --test merge_bounded_memory_tests — both revised GUARD sites
- cargo test — full suite (CI's command) passes
- cargo clippy --all-targets -- -D warnings — CI gate passes
- grep -c 'for _ in' src/io/fastq.rs — 0
- grep -c '0-40' src/io/fastq.rs and grep -c '0-40' docs/api-reference/rust/fastq.md — 0 and 0
- grep -c 'byte-identical' src/io/fastq.rs — 0
- grep -c 'estimated > budget' tests/merge_bounded_memory_tests.rs — 0
</verification>

<success_criteria>
- All five advisories WR-15, WR-16, WR-17, IN-12, IN-13 are discharged in substance with a test proving each fixed behavior (gz statistics, error propagation, ASCII-scale doc pin, trailing-garbage loud failure, non-tautological guards).
- The WR-17 fix is the review's non-breaking doc/code alignment; the breaking Phred-semantics option is recorded as deferred with reason, not silently dropped or silently taken.
- cargo test and cargo clippy --all-targets -- -D warnings pass from the repo root.
</success_criteria>

<output>
Create .planning/quick/261019-dwf-address-round-4-review-advisories-wr-15-/261019-dwf-SUMMARY.md when done
</output>
