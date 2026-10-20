---
phase: quick-261018-wrx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/STATE.md
autonomous: true
requirements: []
estimate:
  tokens: 10000
  raw_tokens: 6000
  tasks: 1
  confidence: low

must_haves:
  truths:
    - "`node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs state json` run with cwd at the repo root emits NO warning containing 'matches no ROADMAP heading' on stderr"
    - ".planning/STATE.md frontmatter has NO `milestone:` key and NO `milestone_name:` key (absent — explicitly NOT `milestone: null`)"
    - ".planning/STATE.md frontmatter still opens with `gsd_state_version:` exactly once (state-file FORMAT version, untouched)"
    - "`state json` stdout still reports progress total_phases 4 and completed_phases 4"
    - ".planning/ROADMAP.md is byte-identical to HEAD — no heading was renamed, no content touched"
    - "STATE.md body (decisions, BENCH-02 escalation notes, deferred items, quick-task table) is unchanged"
    - "No milestone-close/archive lifecycle action was performed"
  artifacts:
    - ".planning/STATE.md"
  key_links:
    - "absent `milestone:` key -> getMilestoneInfo free-form path returns UNSCOPED/null identity -> assertedMilestoneVersion null -> milestonedButUnbounded false -> #3354/#3642/#4094 warning + counter-withhold path inactive -> progress counters computed truthfully (4/4) instead of frozen"
---

<objective>
Silence the `gsd: warning — milestone 'v1.0' is asserted in STATE.md but matches no ROADMAP heading … (#3354/#3642/#4094)` warning by removing the fabricated `milestone: v1.0` / `milestone_name: milestone` frontmatter pair from `.planning/STATE.md`. This is a two-line deletion in ONE file; `.planning/ROADMAP.md` is not touched.

Purpose: The asserted `v1.0` was never a human decision — it is the byte-for-byte artifact of a deleted gsd-tools default. The current tool's own source (`~/.claude/gsd-core/bin/lib/roadmap-parser.cjs`, `getMilestoneInfo` doc comment, #3216 §7.2 rule 4) documents that the OLD `getMilestoneInfo` returned a fabricated `{value:'v1.0', name:'milestone'}` on every unresolved path, and that this default was deleted precisely because it was "output-identical to a successful read of a genuine v1.0 project". STATE.md's two suspicious values (`milestone: v1.0` AND the literal `milestone_name: milestone`) are exactly that fabricated pair, written by the tool in commit 65bf4f7 (2026-07-01, "docs(state): record phase 1 context session"). The ROADMAP has been free-form since its first commit 0fdd32f — title `# Roadmap: rustkmer Performance Milestone`, zero version tokens anywhere — and no PROJECT.md/greenfield artifact ever declared v1.0. Promoting `v1.0` into a ROADMAP heading would launder a deleted tool fabrication into curated project identity and pre-empt the version decision that belongs to the pending milestone close. Removing the assertion instead converges STATE.md to the tool's own steady state: for a free-form unversioned ROADMAP, `buildStateFrontmatter` writes no `milestone:` key at all.

Output: `.planning/STATE.md` frontmatter minus exactly two lines; warning gone on the read-only `state json` repro; nothing else changes.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md

Ground truth verified live at planning time (2026-10-18, branch dev, working tree clean except untracked `.opencode/`, `.planning/INBOX-TRIAGE.md`, `.planning/state.json`):

**Matcher semantics (from gsd-tools source, `~/.claude/gsd-core/bin/lib/`):**
- The warning fires in `buildStateFrontmatter` (state.cjs:2734-2737) when `milestonedButUnbounded = !milestoneBounded && roadmapHasAnyMilestoneSection && !milestoneExplicitlyNull`.
- `hasAnyMilestoneSection` (roadmap-parser.cjs:532) is `countMilestoneHeadings(...) >= 1`: any level 1-3 non-`Phase` heading whose OWN TEXT carries a milestone vocabulary signal (`v\d+\.\d+`, ✅/📋/🚧, or the word "Milestone"). This project's LEVEL-1 TITLE `# Roadmap: rustkmer Performance Milestone` carries the word "Milestone" — that alone classifies the ROADMAP as milestoned.
- `isMilestoneBounded` requires a level 1-3 non-Phase heading containing the asserted version token (`v1.0\b`). No such heading exists → unbounded → warning + all four progress counters withheld at stored values (#3354/#3642/#4094).
- Read-only repro: `cmdStateJson` ("state json") calls `buildStateFrontmatter` and NEVER writes (its own doc comment: "one snapshot read"). Empirically confirmed: emits the warning today, exit 0, STATE.md sha identical before/after. This is the verify gate.
- `quick-tasks-append` emitted the same warning only because its read-modify-write passes through the same frontmatter builder — do NOT use it as the gate (it appends a row).

**Why the key must be ABSENT, not `milestone: null` (#5038):** an explicit null on a sectioned ROADMAP (the title's "Milestone" word keeps `hasAnyMilestoneSection` true) triggers `explicitNullWithheld` — the four progress counters are frozen SILENTLY forever, with no warning to ever flag it. Absent key: `assertedMilestoneVersion` stays null → `milestoneBounded` vacuously true → counters computed truthfully.

**Empirically validated in scratch sims at planning time** (full `.planning` copies in /tmp, `state json` run):
- Sim B (this plan — keys removed): no warning, no milestone keys, progress 4/4, percent 100.
- Sim A (rejected — `v1.0` added to ROADMAP title): also silences the warning and would resolve `milestone_name: Performance Milestone`, but legitimizes the fabricated version (see Purpose). Both sims prove no counter clobber either way: the three `### Phase 999.x` Backlog headings are excluded as sentinels (`isSentinelPhaseId` 999-rule) and the milestone window is the whole document before AND after, so `total_phases` stays `max(4 disk, 4 roadmap) = 4`.

**Deliberately OUT of scope (do not touch):**
- `.planning/state.json` (untracked runtime cache, `"milestone": "v1.0"` at line 4): derived by `publishStateContract` from `getMilestoneInfo` on every `state.*`/`phase.*`/`milestone.complete` write — it self-heals to null after this fix on the next GSD state write. Not consumed by the warning path.
- `.planning/WINDOWS.md` per-row `"milestone": "v1.0"` stamps: record-time historical stamps (#4487), parse-tolerant, never compared to the current milestone — historical records stay as recorded.
- `gsd_state_version: "1.0"` in STATE.md frontmatter: the STATE file FORMAT version, coincidentally "1.0", unrelated to milestone identity. MUST remain.
- The pending milestone close: Phase-04 escalation notes ("escalated to /gsd-complete-milestone", BENCH-02 measured NO verdict) stay byte-identical. Choosing the real version (v1.0 or otherwise) belongs to that lifecycle step, which this plan explicitly does NOT perform. Follow-up only.
- Note (informational, no action): the stored `total_plans: 5 / completed_plans: 9` (completed > total) is stale; once counters are unwithheld, the next natural state write records the disk-derived 31/31. The read-only verify gate does not force this.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove the fabricated milestone identity pair from STATE.md frontmatter (RED-observe, then GREEN)</name>
  <files>.planning/STATE.md</files>
  <action>
    RED first — with cwd at the repo root, run the read-only repro and observe the milestone-mismatch warning is present (sensitivity proof for the gate):
    `node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs state json >/dev/null` — stderr must contain the gsd warning tagged `(#3354/#3642/#4094)`. (This command never writes; confirmed by source inspection and sha comparison at planning time.)

    Then edit `.planning/STATE.md` YAML frontmatter ONLY: delete exactly these two lines (locate by content with `grep -n`, not by fixed line number — currently lines 3 and 17):
    - `milestone: v1.0`
    - `milestone_name: milestone`

    Delete the lines outright — do NOT replace either with `null`, `none`, `~`, or empty (an explicit null plus this ROADMAP's milestone-vocabulary title would silently freeze all four progress counters forever per #5038; absence is the only correct shape).

    Do NOT touch anything else:
    - `gsd_state_version:` stays (state-file format version, not a milestone version).
    - Every other frontmatter key (`current_phase`, `status`, `stopped_at`, `last_*`, `state_head`, the whole `progress:` block) stays byte-identical.
    - The entire body below the closing `---` stays byte-identical — decisions, BENCH-02 escalation notes, deferred items, quick-task table, session continuity.
    - `.planning/ROADMAP.md`, `.planning/state.json`, `.planning/WINDOWS.md` are not edited.
    - Do NOT run `/gsd-complete-milestone`, `milestone complete`, any archive/cleanup command, or any command that writes STATE.md (no `state sync`, no `quick-tasks-append`) — the fix is a hand edit plus read-only verification.

    Before committing, confirm the diff is exactly two deleted frontmatter lines: `git diff -- .planning/STATE.md`.
  </action>
  <verify>
    <automated>test "$(grep -c '^milestone:' .planning/STATE.md)" = "0" && test "$(grep -c '^milestone_name:' .planning/STATE.md)" = "0" && test "$(grep -c '^gsd_state_version:' .planning/STATE.md)" = "1" && test -z "$(git diff HEAD -- .planning/ROADMAP.md)" && S=$(shasum .planning/STATE.md | cut -d' ' -f1) && node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs state json >/tmp/wrx-state-json.out 2>/tmp/wrx-state-json.err && test "$S" = "$(shasum .planning/STATE.md | cut -d' ' -f1)" && ! grep -q 'matches no ROADMAP heading' /tmp/wrx-state-json.err && grep -q '"total_phases": 4' /tmp/wrx-state-json.out && grep -q '"completed_phases": 4' /tmp/wrx-state-json.out</automated>
  </verify>
  <done>
    The read-only `state json` repro emits no `matches no ROADMAP heading` warning, leaves STATE.md byte-identical (sha guard), and still reports total_phases 4 / completed_phases 4; STATE.md frontmatter carries neither `milestone:` nor `milestone_name:` while keeping `gsd_state_version:`; ROADMAP.md is unchanged against HEAD; `git diff -- .planning/STATE.md` shows exactly two deleted frontmatter lines; no lifecycle (milestone close/archive) action was performed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Editor -> .planning/STATE.md | Local, git-tracked planning bookkeeping; no external input, no code, no network, no package installs |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-WRX-01 | Tampering | .planning/STATE.md frontmatter edit | low | mitigate | Content-addressed two-line deletion (grep-located, not line-numbered) plus an automated gate that asserts `gsd_state_version:` survives, the body/ROADMAP stay untouched (`git diff HEAD` guard), and progress counters still report 4/4 — an over-broad edit fails the gate. |
| T-WRX-02 | Repudiation | milestone identity history | low | mitigate | The fabricated-default provenance (old getMilestoneInfo `{v1.0, milestone}` default, commit 65bf4f7) and the rejected Sim-A alternative are recorded in this plan and must be echoed in the SUMMARY, so the retraction of `v1.0` is a documented decision rather than a silent disappearance. No package installs occur, so no T-WRX-SC row is warranted. |
</threat_model>

<verification>
- The Task 1 automated gate is the full read-only proof: key absence, format-version survival, ROADMAP byte-identity vs HEAD, `state json` warning-free, STATE.md sha unchanged across the gate run itself (the read-only contract, self-enforced), and counters intact (4/4).
- RED/GREEN discipline: the same `state json` command must show the warning BEFORE the edit (observed in the task action) and must not show it after — the gate is the GREEN half; if the RED half does not reproduce, stop and report (the tool version may have changed).
- Both directions were empirically validated at planning time (2026-10-18) against scratch copies of this repo's `.planning`: keys-removed silences the warning with counters 4/4/percent 100.
- The unrelated `#3532 defaults.json model_profile` stderr warning from `state json` is expected noise — the gate greps only for `matches no ROADMAP heading`.
</verification>

<success_criteria>
- The `#3354/#3642/#4094` milestone-mismatch warning no longer fires on the read-only `state json` path, and progress counters are computed (not withheld) with values consistent with 4 phases complete.
- `.planning/STATE.md` differs from HEAD by exactly two deleted frontmatter lines; ROADMAP.md, state.json, WINDOWS.md, and all decision/escalation records are untouched.
- The choice of fix (remove fabricated assertion) vs the alternative (add v1.0 to a ROADMAP heading) is documented with provenance in the SUMMARY, and the milestone-close lifecycle step is recorded as explicit follow-up, not performed.
</success_criteria>

<output>
Commit the two-line deletion with a message such as: `docs(quick-261018-wrx): remove fabricated milestone v1.0 identity from STATE.md (old tool default; ROADMAP is free-form)`. Create the summary at .planning/quick/261018-wrx-fix-state-md-roadmap-milestone-mismatch-/261018-wrx-SUMMARY.md recording: the fabricated-default provenance (old getMilestoneInfo default pair, written by tool at 65bf4f7), why key-absence beats `milestone: null` (#5038 counter freeze), why ROADMAP-side v1.0 was rejected, the self-healing notes for state.json/WINDOWS.md, and the follow-up: run `/gsd-complete-milestone` when ready to close the Performance Milestone — that flow is where a real version identifier gets chosen and declared.
</output>
