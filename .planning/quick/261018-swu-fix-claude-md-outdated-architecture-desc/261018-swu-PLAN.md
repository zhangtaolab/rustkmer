---
phase: quick-261018-swu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .claude/CLAUDE.md
autonomous: true
requirements: ["QUICK-261018-CLAUDEMD-ARCH"]
estimate:
  tokens: 15000
  raw_tokens: 10000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "No sentence in .claude/CLAUDE.md describes KmerCounter as a lock-guarded HashMap; the sharded CounterTable (dense/wide DashMap) design is described instead"
    - "No sentence in .claude/CLAUDE.md claims the count command processes files sequentially with a single worker thread"
    - "The Threading constraint documents chunked rayon par_iter counting (CHUNK_SIZE 4096) and the --threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > all-cores precedence via resolve_thread_count"
    - "The stack dependency list names dashmap as the counting-table map (hashbrown rescoped to non-counter uses)"
    - "All 14 GSD managed-block markers survive and every other line of .claude/CLAUDE.md is byte-identical (verified via git diff line count)"
  artifacts:
    - ".claude/CLAUDE.md with corrected Component Responsibilities row, Pattern Overview counting sentence, Data Flow bullet, Key Abstractions pattern + line pin, Threading constraint, stack dependency line, and domain-layer crate list"
  key_links:
    - ".claude/CLAUDE.md KmerCounter descriptions -> src/hash/table.rs CounterTable::{Dense,Wide} DashMap arms (lines 37-42) + Cargo.toml dashmap 6.2.1 (line 61)"
    - ".claude/CLAUDE.md Threading constraint -> src/cli/commands/count.rs CHUNK_SIZE=4096 (line 30), chunked par_iter in process_fasta_file/process_fastq_file, resolve_thread_count (line 836) with precedence documented at lines 789 and 827-828"
---

<objective>
Correct the two verified-false architectural claims in .claude/CLAUDE.md so agents loading project context see the real counter design (sharded DashMap CounterTable) and the real count-command behavior (chunked rayon parallelism with a four-tier thread precedence), plus the directly-adjacent counting-map wording in the same file.

Purpose: .claude/CLAUDE.md is the context every future agent loads; its architecture block still describes the pre-Phase-2/3 design (a lock-guarded HashMap counter and single-threaded counting) that was replaced by plans 02-02/02-01/03-06. The regenerated source of truth (.planning/codebase/ARCHITECTURE.md, updated 2026-10-18) is already correct — only the embedded copy in .claude/CLAUDE.md (dated Jul 1) is stale.
Output: .claude/CLAUDE.md with seven surgical line-level corrections; nothing else in the file changes.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.claude/CLAUDE.md
@.planning/STATE.md

# Ground truth (verified against src/ during planning — do not re-derive)
@src/hash/table.rs
@src/cli/commands/count.rs

# Wording sources (already correct; mirror their vocabulary)
@.planning/codebase/ARCHITECTURE.md
@.planning/codebase/STACK.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Correct the five stale architecture-block claims in .claude/CLAUDE.md</name>
  <files>.claude/CLAUDE.md</files>
  <action>
In .claude/CLAUDE.md, inside the GSD:architecture block only, correct five stale claims. Use the Edit tool with each single stale line as old_string — never rewrite the file, never touch sections outside the named lines. Ground truth: src/hash/table.rs defines a private two-variant CounterTable enum — Dense(DashMap&lt;u64, u32&gt;) for k &lt;= 32 (16-byte slots), Wide(DashMap&lt;u128, u32&gt;) for 33..=64 — behind a u128-keyed public API (enum at src/hash/table.rs:37-42, table field at :111); counting is parallel — src/cli/commands/count.rs fills bounded CHUNK_SIZE (4096-record) Vecs and hands each chunk to rayon par_iter (const at :30, par_iter loops in process_fasta_file/process_fastq_file), with thread precedence --threads &gt; RUSTKMER_THREADS &gt; RAYON_NUM_THREADS &gt; all cores implemented by resolve_thread_count_from (:802) / resolve_thread_count (:836, doc at :827-828); dashmap 6.2.1 is a direct dependency (Cargo.toml:61). Five edits:
(1) Component Responsibilities table row for KmerCounter (~line 262): replace the middle cell that describes a lock-guarded HashMap counter with "Concurrent in-memory counter — sharded `dashmap::DashMap` behind a private `CounterTable` enum: `Dense(DashMap<u64, u32>)` for k ≤ 32, `Wide(DashMap<u128, u32>)` for k 33–64; public API stays u128-keyed". Keep the row's pipe structure (3 cells) and the `src/hash/table.rs` file column; no pipe characters inside cell text.
(2) Pattern Overview counting sentence (~line 275): the phrase "an in-memory `HashMap`" becomes "an in-memory sharded concurrent map (`CounterTable`: dense `DashMap<u64, u32>` / wide `DashMap<u128, u32>`)"; leave the rest of the sentence (sorting, flat .rkdb/text output) unchanged.
(3) Data Flow bullet on KmerCounter shared state (~line 312): replace the parenthetical describing the lock-wrapped map with "(a sharded `CounterTable` — dense `DashMap<u64, u32>` for k ≤ 32, wide `DashMap<u128, u32>` for 33–64, DashMap interior mutability — plus atomics for totals)".
(4) Key Abstractions "Accumulate counts during counting" entry (~lines 321-323): Pattern line becomes "concurrent counter over a `CounterTable` enum — `Dense(DashMap<u64, u32>)` for k ≤ 32, `Wide(DashMap<u128, u32>)` for 33–64 — with atomic totals and overflow protection; width chosen at `KmerCounter::new` and hidden behind the u128-typed public API"; on the Examples line, update the stale line pin `src/hash/table.rs:14` to `src/hash/table.rs:37` (the CounterTable enum).
(5) Architectural Constraints Threading bullet (~line 348): replace the entire bullet — both the counter-lock sub-claim and the sequential single-worker count-command sub-claim — with: "**Threading:** Single-process; parallelism via Rayon thread pool. Counting is parallel — readers fill bounded `CHUNK_SIZE` (4096-record) chunks handed to rayon `par_iter` (`src/cli/commands/count.rs`); `KmerCounter` relies on DashMap interior mutability for concurrent increments. Thread-count precedence: `--threads` > `RUSTKMER_THREADS` > `RAYON_NUM_THREADS` > all cores (`resolve_thread_count`, `src/cli/commands/count.rs:787`–`847`)."
Do NOT alter the GSD marker comments, the anti-pattern headers, or the data_offset constraint bullet (a separate data_offset claim in that section is also suspected stale per STATE.md decisions 01-03/03-09 — flag it in the SUMMARY as an observed out-of-scope item, do not fix it here).
  </action>
  <verify>
    <automated>test $(grep -c 'parking_lot::RwLock' .claude/CLAUDE.md) -eq 0 && test $(grep -c 'num_threads = 1' .claude/CLAUDE.md) -eq 0 && test $(grep -c 'DashMap<u64, u32>' .claude/CLAUDE.md) -ge 4 && test $(grep -c 'RUSTKMER_THREADS' .claude/CLAUDE.md) -ge 1 && grep -q 'CHUNK_SIZE' .claude/CLAUDE.md && test $(grep -c 'GSD:' .claude/CLAUDE.md) -eq 14 && grep '^| `KmerCounter`' .claude/CLAUDE.md | awk -F'|' '{exit !(NF==5)}' && echo TASK1-PASS</automated>
  </verify>
  <done>All five architecture-block claims now match src/ ground truth; zero lock-guarded-counter mentions and zero sequential-counting claims remain in .claude/CLAUDE.md; the KmerCounter table row is still a valid 3-cell markdown row; all 14 GSD markers intact.</done>
</task>

<task type="auto">
  <name>Task 2: Fix the adjacent stack-block dependency line and run the final file-wide sweep</name>
  <files>.claude/CLAUDE.md</files>
  <action>
Two remaining adjacent corrections plus a final consistency sweep, again via scoped Edit calls only:
(1) In the GSD:stack block, the Key Dependencies line crediting `hashbrown` 0.14 + `ahash` 0.8 as the map powering the k-mer counting table (~line 66) is stale — the counting table is dashmap since plan 02-02. Insert a new line directly above it: "- `dashmap` 6.2.1 - Concurrent sharded map for the k-mer counting table (`src/hash/table.rs`); pins `hashbrown` ^0.14.5 internally." and rescope the existing hashbrown line to non-counter uses: "- `hashbrown` 0.14 + `ahash` 0.8 - Hash maps outside the counter (e.g. the in-memory merge accumulator, `src/database/format.rs`)." Mirror the wording of the regenerated source .planning/codebase/STACK.md (line 57 documents dashmap 6.2.1).
(2) In the architecture block's Domain-layer "Depends on" crate list (~line 294), append `dashmap` to the enumerated external crates so the layer dependency list matches the counter's actual dependency.
(3) Final sweep: re-read the full file once and confirm no other line describes the counter as lock-guarded or counting as sequential; then run the automated gate. Confirm via `git diff --stat .claude/CLAUDE.md` that only .claude/CLAUDE.md changed and the diff is confined to the eight targeted lines (five from Task 1, two from edit 1 here, one from edit 2 here).
  </action>
  <verify>
    <automated>test $(grep -c 'dashmap' .claude/CLAUDE.md) -ge 2 && grep -q '`dashmap` 6.2.1' .claude/CLAUDE.md && test $(grep -c 'parking_lot::RwLock' .claude/CLAUDE.md) -eq 0 && test $(grep -c 'num_threads = 1' .claude/CLAUDE.md) -eq 0 && test $(grep -c 'GSD:' .claude/CLAUDE.md) -eq 14 && git diff --numstat .claude/CLAUDE.md | awk '{exit !($2 <= 10)}' && echo TASK2-PASS</automated>
  </verify>
  <done>The stack block names dashmap 6.2.1 as the counting-table map with hashbrown rescoped to non-counter uses; the domain-layer crate list includes dashmap; the full-file sweep finds no residual stale counter/threading claim; git diff touches only .claude/CLAUDE.md with at most ~10 changed lines and all GSD markers intact.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none) | Documentation-only change to a repo-internal markdown file; no code, no external input, no network, no package installs |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261018-swu-01 | Repudiation (information integrity) | .claude/CLAUDE.md | medium | mitigate | Accuracy gates in both tasks (negative greps for the stale literals, positive greps for DashMap/CHUNK_SIZE/RUSTKMER_THREADS, GSD-marker count, git diff line bound) make a partial or over-broad edit fail loudly |
</threat_model>

<verification>
- Task 1 and Task 2 automated gates both print their PASS sentinel.
- `git diff .claude/CLAUDE.md` shows only the eight targeted lines changed; every hunk sits inside the GSD:architecture or GSD:stack blocks.
- Spot-check semantic accuracy: the new KmerCounter row and Key Abstractions pattern match src/hash/table.rs:37-42 verbatim in vocabulary (CounterTable, Dense, Wide, DashMap); the new Threading bullet matches src/cli/commands/count.rs:30 (CHUNK_SIZE 4096) and :787-847 (resolve_thread_count precedence).
</verification>

<success_criteria>
- .claude/CLAUDE.md describes the counter as the sharded CounterTable dense/wide DashMap design and counting as chunked-parallel with the four-tier thread precedence — zero remaining mentions of a lock-guarded HashMap counter or single-worker sequential counting.
- dashmap 6.2.1 appears in the stack dependency list; hashbrown is scoped to non-counter uses.
- File integrity: 14 GSD markers, valid markdown table row, diff confined to the targeted lines.
- SUMMARY notes the observed-but-unfixed stale data_offset/anti-pattern claims for a possible follow-up quick task.
</success_criteria>

<output>
Create .planning/quick/261018-swu-fix-claude-md-outdated-architecture-desc/261018-swu-SUMMARY.md when done
</output>
