---
phase: 04
review: 04-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "README ships eight `count` commands the CLI rejects (positional input)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "README documents a nonexistent `--kmer-size` long flag"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "CONTRIBUTING.md states the opposite of what CI now does (stale within the same review window)"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "docs/mkdocs.yml nav references four files that do not exist — docs build cannot pass"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "docs site footer PyPI link is a 404"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "\"Verify Installation\" snippet is a Python syntax error"
  - id: WR-07
    severity: warning
    disposition: fixed
    title: "Migration table documents CLI commands the CLI rejects"
  - id: WR-08
    severity: warning
    disposition: fixed
    title: "Example scripts point users at guide documents that do not exist"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "docs/mkdocs.yml declares the `search` plugin twice; most of the docs tree is absent from nav"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "docs/README.md example treats a PyQueryResult as always-truthy"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "demo_performance.py — misleading unit name and inconsistent zero-guard"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "Inconsistent GitHub org across the doc corpus"
  - id: IN-05
    severity: info
    disposition: fixed
    title: "mkdocs preview server binds all interfaces"
  - id: IN-06
    severity: info
    disposition: deferred
    title: "Uninterpolated `{route}` placeholders in expect_err messages"
  - id: IN-09
    severity: info
    disposition: deferred
    title: "Fingerprint-less results files now pass through the fingerprints section silently"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "Windows clippy gate is red at HEAD — un-gated measurement helpers are dead code under the Windows test gating (CI merge gate failing)"
  - id: IN-08
    severity: info
    disposition: fixed
    title: "The advisory-mode PASS summary line is not pinned by any test"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Renderer hard-codes a measurement literal, violating the T-04-07 \"zero measurement literals\" contract it implements"
  - id: IN-07
    severity: info
    disposition: deferred
    title: "Leading-hyphen paths pass validate_path and reach argv positions where tools parse options"
open: 0
total: 19
recorded: 2026-10-20T11:37:14.347Z
---

# Phase 04: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | README.md: 7 count commands now pass inputs via -i and the usage template matches USER_GUIDE.md (quick-261111-spz) |
| WR-02 | warning | fixed | README.md now documents clap's derived long flag --k for field k (quick-261111-spz) |
| WR-03 | warning | fixed | CONTRIBUTING.md paragraph and gates table rewritten to match ci.yml's 3-OS pyo3-pytest job with the command-line 80% coverage gate (quick-261111-spz) |
| WR-04 | warning | fixed | mkdocs.yml nav repointed to real pages and dead Deployment/Background/Appendix sections removed; mkdocs.docs.yml logo/favicon keys dropped; strict build green (quick-261111-spz) |
| WR-05 | warning | fixed | mkdocs.docs.yml PyPI social link now targets the published pyrustkmer project (quick-261111-spz) |
| WR-06 | warning | fixed | Stray parenthesis removed from the f-string in docs/installation.md and docs/index.md (quick-261111-spz) |
| WR-07 | warning | fixed | Migration rows in docs/api-reference/index.md and overview.md now show valid CLI forms: dump without --limit (pagination is Python-only), merge via -i (quick-261111-spz) |
| WR-08 | warning | fixed | demo_pyo3_binding.py and test_pyo3_api.py now reference the real docs/guides/pyo3-binding-guide.md and docs/guides/prefix-query-guide.md (quick-261111-spz) |
| IN-01 | info | fixed | Already resolved by config relocation: search declared exactly once per live config (mkdocs.yml:40, mkdocs.docs.yml:53); root nav enumerates the full docs tree; mkdocs.docs.yml is a deliberate curated subset with exclude_docs |
| IN-02 | info | fixed | docs/README.md example now checks the found getter (if result.found:), which exists at pyo3/src/database.rs:65 (quick-261111-spz) |
| IN-03 | info | fixed | demo_performance.py: throughput variable renamed to throughput_gbps (it holds GB/s) and queries_per_second given the same zero-guard conditional as its sibling (quick-261111-spz) |
| IN-04 | info | fixed | All legacy-org GitHub URLs normalized to canonical zhangtaolab/rustkmer per live git remote: both configs' repo_name/repo_url, mkdocs.yml social link, docs/installation.md issues link (quick-261111-spz) |
| IN-05 | info | fixed | Already resolved: dev_addr absent from both live configs (repo-wide grep empty), so mkdocs' loopback default 127.0.0.1:8000 applies |
| IN-06 | info | deferred | Cosmetic TEST-code message: literal {route} in expect_err at tests/merge_bounded_memory_tests.rs:670,679; no behavior change authorized. Follow-up: interpolate the route name in the two expect_err messages (format! or drop the placeholder) in a test-hygiene pass |
| IN-09 | info | deferred | HARNESS render behavior: scripts/bench/bench.py:1268 listing loop still silently skips fingerprint-less results files; 04-05's named ValueError guards only the first mode=full methodology figure. Follow-up: emit an explicit note in the rendered fingerprints section for results files lacking an input_fingerprint, pinned by a test_render_report test (not in the current review) |
| CR-02 | critical | fixed | Already resolved: MILESTONES.md L35/L40 record CR-02 fixed by 04-05 commit 444f660 per-item cfg gating; CI green including clippy windows-latest; disposition row was stale at open (not in the current review) |
| IN-08 | info | fixed | Already resolved by 04-05 commit 78e5eec: advisory-mode PASS summary pinned by assertIn at scripts/bench/tests/test_compare.py:200 (live-verified); MILESTONES.md L35 records the rider (not in the current review) |
| CR-01 | critical | fixed | bb5ccb0 (user-approved during UAT: figure now derived from fingerprinted input size; re-render byte-identical) (not in the current review) |
| IN-07 | info | deferred | HARNESS code: scripts/bench/bench.py:186 validate_path allowlist admits leading-hyphen paths (option-injection edge in the sh -c arm); needs a behavior change + pinned test, out of this item's scope. Follow-up: reject leading-hyphen paths in validate_path (or prefix ./) with a pinned test under scripts/bench/tests/ (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.

## Triage 2026-11-11 (quick-261111-spz)

All 18 open findings triaged; each carries exactly one disposition plus a one-line rationale above.

| ID | Class | Rationale |
|----|-------|-----------|
| WR-01 | fix-now | 7 positional-input count commands + 1 wrong usage template corrected in README.md; Count accepts inputs only via -i/--directory |
| WR-02 | fix-now | README.md now documents clap's derived --k (field k), not the nonexistent --kmer-size |
| WR-03 | fix-now | CONTRIBUTING.md rewritten to match ci.yml's pyo3-pytest job (3-OS matrix, command-line coverage gate at 80%); pyo3-pytest row added to the gates table |
| WR-04 | fix-now | CI-blocking half already resolved by config relocation; residual repaired: 15 dead root-nav entries repointed/deleted, missing logo/favicon keys removed; strict build stays green |
| WR-05 | fix-now | mkdocs.docs.yml PyPI link repointed from the 404 rustkmer project to published pyrustkmer |
| WR-06 | fix-now | Stray-parenthesis f-string corrected in docs/installation.md and docs/index.md |
| WR-07 | fix-now | Invalid CLI migration rows corrected in docs/api-reference/index.md and overview.md (dump has no --limit; merge requires -i) |
| WR-08 | fix-now | Dangling guide filenames in demo_pyo3_binding.py and test_pyo3_api.py replaced with real docs/guides targets |
| IN-01 | already-fixed | Config relocation resolved both halves: search declared exactly once per live config; root nav covers the docs tree; mkdocs.docs.yml is a curated subset with exclude_docs |
| IN-02 | fix-now | docs/README.md example now uses the found getter (if result.found:) instead of the always-truthy pyclass instance check |
| IN-03 | fix-now | demo_performance.py throughput variable renamed to throughput_gbps and queries_per_second zero-guarded like its sibling |
| IN-04 | fix-now | Org split normalized to canonical github.com/zhangtaolab/rustkmer per live git remote (4 legacy URLs + repo_name display strings) |
| IN-05 | already-fixed | dev_addr absent from both live configs; mkdocs loopback default 127.0.0.1:8000 applies |
| IN-06 | defer | Cosmetic TEST-code expect_err placeholder; no behavior change authorized — test-hygiene follow-up recorded |
| IN-07 | defer | HARNESS validate_path option-injection edge; needs a behavior change + pinned test — follow-up recorded |
| IN-08 | already-fixed | Closed by 04-05 (78e5eec): advisory PASS summary pinned by assertIn at scripts/bench/tests/test_compare.py:200; MILESTONES.md L35 records the rider |
| IN-09 | defer | HARNESS listing loop silently skips fingerprint-less results files; explicit-note + test_render_report follow-up recorded |
| CR-02 | already-fixed | MILESTONES.md L35/L40 record CR-02 fixed (04-05 commit 444f660 per-item cfg gating; CI green incl. clippy windows-latest); row was stale at open |

**Vocabulary mapping.** The four-way triage classes map to the native dispositions as follows: fix-now (applied in this item) and already-fixed both map to `fixed`; defer maps to `deferred`; wont-fix would map to `skipped` — none were classified wont-fix.

**Provenance.** The current review (04-REVIEW.md, 2026-10-20) holds 14 findings (WR-01..08, IN-01..06). IN-07, IN-08, IN-09 and CR-01, CR-02 are carried rows from an earlier round, flagged "not in the current review"; CR-01 was already `fixed` (bb5ccb0) and its row is preserved byte-identical.

**Path note.** STATE.md's blocker cites `.planning/phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md` — that path is stale. The live document is `.planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md` (this file).

**Count reconciliation.** 18 open matched the live doc at triage time (19 rows total including the already-fixed CR-01). After triage: 15 fixed (11 fix-now applied + 4 already-fixed closures evidenced), 3 deferred (IN-06, IN-07, IN-09 — all with concrete recommended follow-ups), 0 open, 0 critical open. No src/, tests/, scripts/, pyo3/, or .github/ file was modified — the deferred findings are recorded, not fixed.