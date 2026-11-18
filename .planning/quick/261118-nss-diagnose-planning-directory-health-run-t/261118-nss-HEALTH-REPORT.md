# Planning Directory Health Report — 2026-11-18

| Field | Value |
|-------|-------|
| Date | 2026-11-18 |
| Branch | `dev` |
| Execution HEAD | `8c5dcdf` (full: `8c5dcdf9c1f3b397ed6d45585008a1d757708d40`) |
| Planning baseline HEAD | `c955c59` |
| Tool invocation | `node ~/.claude/gsd-core/bin/gsd-tools.cjs query validate.health` |
| Scan target | `.planning/` (project root `/Users/forrest/GitHub/rustkmer`) |

The execution-time HEAD is one commit past the planning baseline (`8c5dcdf` is the
pre-dispatch artifacts commit on top of `c955c59`); the live health output is
identical to the planning-time run, so no execution-vs-planning reconciliation
difference exists beyond the HEAD and ahead-count delta noted in Overall Status.

## Overall Status

Status: degraded
Errors: 0
Warnings: 1
Info: 0
Repairable: 0

Planning-time baseline (HEAD `c955c59`) recorded the same `status: degraded` with
0 errors, 1 warning (W019), 0 info, and `repairable_count: 0`. Execution-time
values govern; the only reconciliation deltas are operational, not health
findings: HEAD advanced from `c955c59` to `8c5dcdf` (the pre-dispatch artifacts
commit), and `origin/HEAD...HEAD` advanced from `0 behind / 33 ahead` to
`0 behind / 34 ahead`. The live status, error/warning/info counts, and
`repairable_count` are unchanged.

## Findings

| Code | Severity | Message | Repairable | Disposition |
|------|----------|---------|------------|-------------|
| W019 | warning | Unrecognized .planning/ file: .continue-here.md — not a canonical GSD artifact | false | Accepted (not repaired) |

No errors and no info items were emitted.

**W019 disposition — Accepted (not repaired).** Verbatim fix text from the tool:
"Move to .planning/milestones/ archive subdir or delete if stale. See
templates/README.md for the canonical artifact list." The warning is correct as
output and the file is intentional, so the disposition is accepted rather than
repaired:

- `.planning/.continue-here.md` is a live paused-handoff snapshot. `/gsd-pause-work`
  writes `.planning/.continue-here.md` for research scope (research notes exist but
  no phase/spike/sketch/deliberation) and for the default scope (no detectable
  context), per `~/.claude/gsd-core/workflows/pause-work.md` (path selection lines
  39-40, write step line 131). `/gsd-resume-work` reads it via the three-level glob
  `.planning/.continue-here*.md .planning/*/.continue-here*.md
  .planning/*/*/.continue-here*.md` in `~/.claude/gsd-core/workflows/resume-project.md`
  (line 90). The template exists at `~/.claude/gsd-core/templates/continue-here.md`.
- W019's registry is `CANONICAL_EXACT` in `~/.claude/gsd-core/bin/lib/artifacts.cjs`
  (declared at line 18), whose exact-match set does not list `.continue-here.md`
  under that name — which is precisely why W019 flags the file, and why the rule
  carries `repairable=false`.
- Execution-time liveness evidence: the file is 50 lines, frontmatter
  `status: paused`, `last_updated: 2026-11-18T06:10:51Z`, last touched by commit
  `2da9988` on 2026-11-18 (`docs(quick-261118-n53): close the stale macOS
  verify_threads flake records`). Planning baseline matched: 50 lines, last
  touched by `2da9988`.
- Moving or deleting the file would break resume: `/gsd-resume-work` would find no
  handoff and the paused session context would be lost. The registry omission is
  an upstream gsd-core gap (the pause/resume workflow contract places the file at
  `.planning/`, but the canonical artifact list does not recognize it), not a
  local project defect.

## Isolation / Worktree Consistency

Live values, execution time:

- `node ~/.claude/gsd-core/bin/gsd-tools.cjs query inspect-dispatch-isolation --raw`
  returned rc 0 and exactly `harness-worktree` (no trailing newline). This is the
  sentinel-free inspection verb; `query dispatch-isolation` was not run because it
  writes the executor-dispatch sentinel as a side effect.
- `node ~/.claude/gsd-core/bin/gsd-tools.cjs query config-get workflow.use_worktrees --raw`
  returned rc 1 with nothing on stdout and `Error: Key not found: workflow.use_worktrees`
  on stderr. The key is absent from `.planning/config.json` (0 occurrences), read
  with no fallback so absence stays distinguishable from an explicit value.
- `node ~/.claude/gsd-core/bin/gsd-tools.cjs query config-get runtime --raw`
  returned rc 1 with nothing on stdout and `Error: Key not found: runtime` on
  stderr. No top-level `runtime` key exists in `.planning/config.json`
  (0 occurrences).
- Corroboration against `.planning/config.json`: `use_worktrees` count = 0;
  top-level `runtime` key count = 0.

W025: not triggered.

The health workflow's exact W025 condition (from
`~/.claude/gsd-core/workflows/health.md`) is: W025 fires only when the resolved
dispatch isolation is `none` AND the project config explicitly sets
`workflow.use_worktrees` to a non-empty value that is not `false`. Here the
resolved isolation is `harness-worktree` (not `none`), and the worktrees key is
absent, so both halves of the conjunction are false and no W025 is emitted. The
verdict is recorded rather than asserted: the condition was evaluated from the
live inspect and config-get outputs above.

Informational note (not a health finding): the live `origin/HEAD...HEAD` counts
are `0 behind / 34 ahead` (planning baseline `0 behind / 33 ahead`). Because local
HEAD is ahead of the remote default branch, quick/phase executors auto-degrade to
sequential execution on the main working tree. This is expected operational
behavior under that condition, not a planning-directory defect.

## Environment Notes

The `gsd-tools` bootstrap printed the following warning to stderr on the health
run (quoted verbatim):

`gsd-tools: warning: /Users/forrest/.gsd/defaults.json sets model_profile, commit_docs, parallelization, resolve_model_ids, runtime but a project config takes precedence here — those global keys are ignored for model resolution. (#3532)`

This is tool-level and informational: the global `~/.gsd/defaults.json` keys
(including `runtime`) are ignored under project-config precedence (#3532). It is
not a `.planning/` finding, does not affect the health status, and requires no
action in this repository.

## Repairs

Repairs applied: none (repairable_count = 0).

The live `validate.health` output reported `repairable_count: 0`, so the
repair-authority gate authorizes no repair. W019 is `repairable=false` and was
not moved or deleted. `validate.health --repair` was not run. No file outside
this report was created, modified, or deleted: `.planning/STATE.md`,
`.planning/ROADMAP.md`, `.planning/config.json`, `.planning/.continue-here.md`,
archived milestone files, and all source files are untouched.

## Evidence

| Date | Command | rc | Observation |
|------|---------|----|-------------|
| 2026-11-18 | `git branch --show-current` | 0 | `dev` |
| 2026-11-18 | `git rev-parse --short HEAD` | 0 | `8c5dcdf` (planning baseline `c955c59`) |
| 2026-11-18 | `node ~/.claude/gsd-core/bin/gsd-tools.cjs query validate.health` | 0 | JSON: `status` degraded, `errors` [], warnings [W019], `info` [], `repairable_count` 0; stderr carried the #3532 bootstrap warning |
| 2026-11-18 | `node ~/.claude/gsd-core/bin/gsd-tools.cjs query inspect-dispatch-isolation --raw` | 0 | `harness-worktree` |
| 2026-11-18 | `node ~/.claude/gsd-core/bin/gsd-tools.cjs query config-get workflow.use_worktrees --raw` | 1 | stdout empty; stderr `Error: Key not found: workflow.use_worktrees` |
| 2026-11-18 | `node ~/.claude/gsd-core/bin/gsd-tools.cjs query config-get runtime --raw` | 1 | stdout empty; stderr `Error: Key not found: runtime` |
| 2026-11-18 | `grep -c 'use_worktrees' .planning/config.json` | 1 | count 0 — key absent (`grep` rc 1 simply means no match) |
| 2026-11-18 | `grep -cE '^\s*"runtime"\s*:' .planning/config.json` | 1 | count 0 — no top-level runtime key (`grep` rc 1 simply means no match) |
| 2026-11-18 | `git rev-list --left-right --count origin/HEAD...HEAD` | 0 | `0	34` (planning baseline `0	33`) |
| 2026-11-18 | `git status --porcelain -uno` | 0 | empty — no tracked modifications |
| 2026-11-18 | `wc -l .planning/.continue-here.md` | 0 | 50 lines |
| 2026-11-18 | `grep -E '^(status\|last_updated):' .planning/.continue-here.md` | 0 | `status: paused`; `last_updated: 2026-11-18T06:10:51Z` |
| 2026-11-18 | `git log -1 --format='%h %cs %s' -- .planning/.continue-here.md` | 0 | `2da9988 2026-11-18 docs(quick-261118-n53): close the stale macOS verify_threads flake records` |
| 2026-11-18 | `grep -n "continue-here" ~/.claude/gsd-core/bin/lib/artifacts.cjs` | 1 | no match — `.continue-here.md` absent from `CANONICAL_EXACT` (registry declared at line 18) |
| 2026-11-18 | `grep -n -A6 -B4 "W025" ~/.claude/gsd-core/workflows/health.md` | 0 | W025 fires only when `INSPECTED_ISOLATION = none` AND `USE_WORKTREES` non-empty AND not `false` |
| 2026-11-18 | `grep -n "continue-here" ~/.claude/gsd-core/workflows/pause-work.md ~/.claude/gsd-core/workflows/resume-project.md` | 0 | pause-work writes the path (lines 39-40, 131); resume-project globs it (line 90) |
| 2026-11-18 | `ls -la ~/.claude/gsd-core/templates/continue-here.md` | 0 | template exists (1821 bytes) |

### Verbatim `validate.health` stdout

```json
{
  "status": "degraded",
  "errors": [],
  "warnings": [
    {
      "code": "W019",
      "message": "Unrecognized .planning/ file: .continue-here.md — not a canonical GSD artifact",
      "fix": "Move to .planning/milestones/ archive subdir or delete if stale. See templates/README.md for the canonical artifact list.",
      "repairable": false
    }
  ],
  "info": [],
  "repairable_count": 0
}
```

## Change Verification

Pre-commit evidence, recorded at execution time:

- Tracked tree clean before and after this report was written:
  `git status --porcelain -uno` is empty and `git diff --name-only` is empty.
- This report is the only new artifact: it is untracked until Task 2 stages it by
  explicit path; no other path was created, modified, or staged in Task 1.
- Protected paths untouched: `.planning/STATE.md`, `.planning/ROADMAP.md`,
  `.planning/.continue-here.md`, `.planning/config.json`, and every archived
  milestone file have no diff. No source file was touched.
- No repair was run (`validate.health --repair` was not invoked), consistent with
  `Repairs applied: none (repairable_count = 0).`
- The commit hash for the product commit is recorded in
  `261118-nss-SUMMARY.md`, not in this report.
