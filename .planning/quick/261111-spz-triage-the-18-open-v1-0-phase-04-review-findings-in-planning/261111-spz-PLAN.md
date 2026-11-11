---
phase: quick
plan: 261111-spz
type: execute
wave: 1
depends_on: ["261111-sq0"]   # shared README.md: sq0 edits version-floor statements (L262-263, L912); this item edits CLI command examples (L273-556)
files_modified:
  - README.md
  - CONTRIBUTING.md
  - docs/api-reference/index.md
  - docs/api-reference/overview.md
  - mkdocs.yml
  - mkdocs.docs.yml
  - docs/installation.md
  - docs/index.md
  - docs/README.md
  - examples/python/demo_pyo3_binding.py
  - examples/python/test_pyo3_api.py
  - examples/python/demo_performance.py
  - .planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md
autonomous: true
must_haves:
  truths:
    - "All 18 open findings in the live disposition doc carry exactly one recorded disposition plus a one-line rationale; frontmatter open count is 0; all 19 rows (incl. CR-01 fixed) are preserved."
    - "The 11 fix-now docs/examples defects are corrected in place and every negative gate below reads zero on the post-fix tree."
    - "Zero behavior change: src/, tests/, scripts/, pyo3/, and .github/ are untouched (git status proof); IN-06/IN-07/IN-09 are deferred with concrete recommended follow-ups, not edited."
    - "Each task lands as one atomic commit of exactly its own file set; the union of the three commits (first commit's parent..last commit) equals exactly the 13-file files_modified set."
    - "mkdocs build -f mkdocs.docs.yml --strict stays green; nav paths in BOTH live configs all resolve; the canonical GitHub org everywhere is zhangtaolab/rustkmer (per live git remote)."
  artifacts:
    - ".planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md updated in place (frontmatter dispositions + table + appended triage section)."
    - "Corrected docs/examples files listed in files_modified (all except the disposition doc)."
  key_links:
    - "README CLI examples <-> src/cli/args.rs clap contract: Count takes inputs only via -i/--directory; the derived long flag for field k is --k; Dump has no --limit; Merge requires -i with num_args 2.. ."
    - "CONTRIBUTING CI claims <-> .github/workflows/ci.yml pyo3-pytest job (L133-183): 3-OS matrix, pytest tests/ with command-line --cov=pyrustkmer --cov-fail-under=80; local addopts are only -v."
    - "Disposition rows <-> evidence: 04-REVIEW.md (current 14-finding round), MILESTONES.md L35/L40 + 04-05-SUMMARY.md (CR-02/IN-08 closures), live greps (IN-01/IN-05)."
---

<objective>
Triage the 18 open v1.0 Phase-04 review findings recorded in
`.planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md`
(live-verified path; STATE.md's `.planning/phases/...` path is stale), apply only
trivial docs/examples-level corrections in place, and record a disposition +
one-line rationale for every finding. Code-level harness/test findings
(IN-06/07/08/09) get a disposition + recommended follow-up with NO behavior change.

Purpose: clear the milestone-close blocker ("18 open code-review findings ...
triage before/with /gsd-complete-milestone", STATE.md Blockers) without touching
runtime behavior.
Output: updated disposition doc + corrected docs/examples files, landed as 3 atomic per-task commits.

Planning shape note: docs-only triage — no runtime layers are modified, the
architecture is already proven, so a tracer slice would add no information
(horizontal task shape, the --no-tracer condition). No external API integration
(detector: detected=false), no ORM schema files, no assumption-delta signals —
those checkpoints are skipped.

Commit contract (quick-batch executor, isolation=none): the executor works on the
primary checkout and lands EACH task as ONE atomic commit staging exactly that
task's file set by explicit path (git add -- <paths>; never git add -A). The
orchestrator afterwards commits only the PLAN/SUMMARY/STATE artifacts — SUMMARY.md
itself stays uncommitted. Do NOT touch BATCH.json, STATE.md, or ROADMAP.md.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW.md
@.planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md
@.claude/CLAUDE.md

## Live-verified triage census (planning-time observation, 2026-11-11)

The disposition doc records 19 rows / 18 open — matches the item's stated count.
The current review (04-REVIEW.md, 2026-10-20) contains 14 findings (WR-01..08,
IN-01..06); five rows are carried from an earlier round and flagged "not in the
current review" (IN-07, IN-08, IN-09, CR-01, CR-02). CR-01 is already `fixed`.

Pre-agreed classification (each finding gets exactly ONE disposition; executor
records these, grounded in the cited live evidence):

| ID | Class | Live evidence / rationale |
|----|-------|---------------------------|
| WR-01 | fix-now | 7 positional-input count commands + 1 wrong usage template still in README.md (L273,299,305,433,457,471,477,556); Count accepts inputs only via -i/--directory |
| WR-02 | fix-now | README.md:461 still documents the nonexistent long flag; clap field `k` derives `--k` |
| WR-03 | fix-now | CONTRIBUTING.md:46 still claims CI skips Python tests + a local addopts coverage gate; ci.yml:133-183 pyo3-pytest job contradicts both |
| WR-04 | fix-now | CI-blocking half already resolved by config relocation (mkdocs.docs.yml strict build passes, exit 0); residual: root mkdocs.yml has 15 dead nav entries; mkdocs.docs.yml:32-33 reference missing docs/assets/ logo+favicon |
| WR-05 | fix-now | mkdocs.docs.yml:115 still links the 404 PyPI project; published project is pyrustkmer |
| WR-06 | fix-now | Stray-parenthesis f-string still at docs/installation.md:32 and docs/index.md:56 |
| WR-07 | fix-now | Invalid CLI column rows still at docs/api-reference/index.md:228-229 and overview.md:382 |
| WR-08 | fix-now | Dangling guide filenames still printed by demo_pyo3_binding.py:284,286 and test_pyo3_api.py:225; real targets exist under docs/guides/ |
| IN-01 | already-fixed | Relocation resolved both halves: `search` declared exactly once per live config (mkdocs.yml:40, mkdocs.docs.yml:53); root mkdocs.yml nav now enumerates the full docs tree (its dead entries are repaired under WR-04); mkdocs.docs.yml is a deliberate curated subset with exclude_docs |
| IN-02 | fix-now | docs/README.md:133 still uses always-truthy pyclass instance check; `.found` getter exists (pyo3/src/database.rs:65) |
| IN-03 | fix-now | demo_performance.py:121-125: throughput variable misnamed (prints GB/s) and queries_per_second lacks the zero-guard its sibling has; examples-level trivial |
| IN-04 | fix-now | Org split persists; canonical = github.com/zhangtaolab/rustkmer per live `git remote -v`; 4 legacy-org URLs remain (mkdocs.yml:7,116; mkdocs.docs.yml:4; docs/installation.md:212) |
| IN-05 | already-fixed | dev_addr key absent from both live configs (repo-wide grep empty); mkdocs default 127.0.0.1:8000 applies |
| IN-06 | defer | Literal route placeholder still in expect_err at tests/merge_bounded_memory_tests.rs:670,679; cosmetic TEST-code message; no behavior change authorized |
| IN-07 | defer | scripts/bench/bench.py:186 validate_path allowlist admits leading-hyphen paths (option-injection edge in the sh -c arm); HARNESS code; needs a behavior change + pinned test |
| IN-08 | already-fixed | Closed by 04-05 (78e5eec): advisory PASS summary pinned by assertIn at scripts/bench/tests/test_compare.py:200 (live-verified); MILESTONES.md L35 records the rider |
| IN-09 | defer | scripts/bench/bench.py:1268 listing loop still silently skips fingerprint-less results files; 04-05's named ValueError guards only the first mode=full methodology figure; HARNESS render behavior |
| CR-02 | already-fixed | MILESTONES.md L35/L40 record CR-02 fixed (04-05 commit 444f660 per-item cfg gating; CI green incl. clippy windows-latest); disposition row is stale at open |

Totals: 11 fix-now, 4 already-fixed, 3 defer, 0 wont-fix. No critical remains open.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Correct CLI-facing docs (WR-01, WR-02, WR-03, WR-07)</name>
  <files>README.md, CONTRIBUTING.md, docs/api-reference/index.md, docs/api-reference/overview.md</files>
  <read_first>
    .planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW.md (WR-01/02/03/07 sections carry the exact defects and Fix directives),
    src/cli/args.rs (Count/Dump/Merge clap contract — read-only ground truth),
    .github/workflows/ci.yml lines 133-183 (pyo3-pytest job — read-only; sibling 261111-spy owns workflow edits),
    CONTRIBUTING.md lines 28-50 (gates table + stale paragraph)
  </read_first>
  <action>
    Apply the four review Fix directives verbatim in spirit, docs-only:
    (a) WR-01: in README.md insert the -i flag before each positional input path at L273, 299, 305, 433, 471, 477, 556 (leave L474/L654, already correct), and rewrite the L457 usage template to the form USER_GUIDE.md already uses: count [OPTIONS] -k <K> -i <INPUT>... -o <OUTPUT>.
    (b) WR-02: at README.md:461 replace the documented long-flag spelling with clap's derived form for field k (short -k, long --k), per the review's Fix line.
    (c) WR-03: rewrite the CONTRIBUTING.md:46 paragraph to state what ci.yml actually does — a pyo3-pytest job on all three OSes (build wheel, install, run pytest tests/ with the coverage gate passed on the command line at 80 percent), local pytest in pyo3/ runs plain with no forced coverage flags — and add a pyo3-pytest row to the "Build and test commands" gates table so the table matches its "exact gates CI runs" claim. Do not edit ci.yml itself.
    (d) WR-07: fix only the CLI column of the migration rows — docs/api-reference/index.md:228 (drop the nonexistent dump pagination flag; note pagination is Python-only) and :229 (merge inputs via -i), plus docs/api-reference/overview.md:382 (same dump fix). For consistency also normalize overview.md:383's ellipsis merge row to the explicit -i form. Python-side cells are valid; leave them untouched.
    Do not touch src/, tests/, scripts/, or any workflow file.
    (e) Commit this task atomically: stage exactly README.md, CONTRIBUTING.md, docs/api-reference/index.md, docs/api-reference/overview.md by path (git add -- <paths>), then commit with message docs(quick-261111-spz): correct CLI-facing docs (WR-01/02/03/07). Stage nothing else.
  </action>
  <verify>
    <automated>cd /Users/forrest/GitHub/rustkmer &amp;&amp; test "$(grep -cE 'rustkmer count .* -o [A-Za-z0-9_.&lt;&gt;]+ [A-Za-z0-9_.&lt;&gt;]+\.(fa|fastq|fq|fasta)' README.md)" = 0 &amp;&amp; test "$(grep -c 'count -k &lt;KMER_SIZE&gt; -o &lt;OUTPUT&gt; \[OPTIONS\] &lt;INPUT&gt;' README.md)" = 0 &amp;&amp; test "$(grep -c -- '--kmer-size' README.md)" = 0 &amp;&amp; test "$(grep -c 'CI does not run the Python test suite' CONTRIBUTING.md)" = 0 &amp;&amp; test "$(grep -c 'pyo3-pytest' CONTRIBUTING.md)" -ge 1 &amp;&amp; test "$(grep -cE 'rustkmer dump [^|]*--limit|rustkmer merge [a-z]+\.rkdb' docs/api-reference/index.md docs/api-reference/overview.md | awk -F: '{s+=$NF} END {print s}')" = 0 &amp;&amp; C=$(git rev-parse HEAD) &amp;&amp; FILES=$(git diff --name-only "$C^..$C") &amp;&amp; test "$(printf '%s\n' "$FILES" | LC_ALL=C sort | tr '\n' ' ')" = "CONTRIBUTING.md README.md docs/api-reference/index.md docs/api-reference/overview.md "</automated>
    Baselines at HEAD (must flip): positional-count gate 7, template gate 1, long-flag gate 1, stale-claim gate 1, pyo3-pytest pin 0, migration-row gate 2+1.
  </verify>
  <done>README's eight count commands all use -i (or the corrected template); the documented long flag matches clap; CONTRIBUTING's paragraph and gates table match ci.yml's pyo3-pytest job; all three cited migration rows show valid CLI invocations; all six gates read their post-fix values; the task is landed as one atomic commit containing exactly these 4 files.</done>
</task>

<task type="auto">
  <name>Task 2: Correct docs-site configs and snippets (WR-04, WR-05, WR-06, IN-02, IN-04; evidence-check IN-01/IN-05)</name>
  <files>mkdocs.yml, mkdocs.docs.yml, docs/installation.md, docs/index.md, docs/README.md</files>
  <read_first>
    .planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW.md (WR-04/05/06, IN-01/02/04/05 sections),
    mkdocs.yml and mkdocs.docs.yml (the two live successor configs; docs/mkdocs.yml no longer exists),
    .github/workflows/docs.yml (builds mkdocs.docs.yml with --strict — read-only)
  </read_first>
  <action>
    (a) WR-04 residual, root mkdocs.yml nav: repoint the Tutorials entry under User Guide (L58) to the real top-level tutorials/index.md; repoint KmerCounter to api-reference/rust/kmer_counter.md and CLI to api-reference/rust/args.md (both verified to exist); DELETE the Deployment, Background, and Appendix nav sections wholesale — docs/deployment/, docs/background/, docs/appendix/ do not exist (15 dead entries total at baseline). Do not fabricate pages.
    (b) WR-04 residual, mkdocs.docs.yml: remove the theme logo and favicon keys (L32-33) — docs/assets/ does not exist and adding binary assets is out of scope; the strict build already passes without them.
    (c) WR-05: in mkdocs.docs.yml:115 point the PyPI social link at the published pyrustkmer project (https://pypi.org/project/pyrustkmer/).
    (d) WR-06: in docs/installation.md:32 and docs/index.md:56 remove the stray closing parenthesis inside the f-string expression so the snippet is valid Python (the review's Fix line shows the exact corrected form).
    (e) IN-02: in docs/README.md:133 replace the always-truthy instance check with the found-getter check (if result.found:) — the getter exists at pyo3/src/database.rs:65.
    (f) IN-04: normalize every legacy-org GitHub URL to the canonical zhangtaolab org (live git remote): mkdocs.yml repo_url (L7) and social link (L116), mkdocs.docs.yml repo_url (L4), docs/installation.md issues link (L212). Also update the repo_name display strings in both configs to zhangtaolab/rustkmer for consistency. Leave site_url (Pages deploy target) and the already-canonical references (CONTRIBUTING.md, mkdocs.docs.yml:113, docs/installation.md:100) untouched.
    (g) IN-01 / IN-05: verification only — confirm each config declares the search plugin exactly once and neither config overrides the preview-server bind address (mkdocs then defaults to loopback); record the evidence in Task 3's disposition rows. No edit needed.
    (h) Commit this task atomically: stage exactly mkdocs.yml, mkdocs.docs.yml, docs/installation.md, docs/index.md, docs/README.md by path, then commit with message docs(quick-261111-spz): repair docs-site configs and snippets (WR-04/05/06, IN-02/04). Stage nothing else.
  </action>
  <verify>
    <automated>cd /Users/forrest/GitHub/rustkmer &amp;&amp; test "$(grep -c 'total_kmers)}' docs/installation.md docs/index.md | awk -F: '{s+=$NF} END {print s}')" = 0 &amp;&amp; test "$(grep -c 'pypi.org/project/rustkmer' mkdocs.docs.yml)" = 0 &amp;&amp; test "$(grep -c 'pypi.org/project/pyrustkmer' mkdocs.docs.yml)" -ge 1 &amp;&amp; test "$(grep -c '^if result:$' docs/README.md)" = 0 &amp;&amp; test "$(grep -c 'if result.found:' docs/README.md)" -ge 1 &amp;&amp; test "$(grep -c 'github.com/rustkmer/rustkmer' mkdocs.yml mkdocs.docs.yml docs/installation.md CONTRIBUTING.md | awk -F: '{s+=$NF} END {print s}')" = 0 &amp;&amp; python3 -c "import re,os,sys; missing=[]; [missing.extend(p for p in re.findall(r'([A-Za-z0-9_./-]+\.md)', re.search(r'\nnav:\n(.*?)\n[a-z_]+:', open(c).read(), re.S).group(1)) if not os.path.isfile(os.path.join('docs',p))) for c in ('mkdocs.yml','mkdocs.docs.yml')]; print('MISSING:',missing); sys.exit(1 if missing else 0)" &amp;&amp; test "$(grep -c 'dev_addr' mkdocs.yml mkdocs.docs.yml | awk -F: '{s+=$NF} END {print s}')" = 0 &amp;&amp; mkdocs build -f mkdocs.docs.yml --strict --site-dir /tmp/spz-mkdocs-verify &amp;&amp; C=$(git rev-parse HEAD) &amp;&amp; FILES=$(git diff --name-only "$C^..$C") &amp;&amp; test "$(printf '%s\n' "$FILES" | LC_ALL=C sort | tr '\n' ' ')" = "docs/README.md docs/index.md docs/installation.md mkdocs.docs.yml mkdocs.yml "</automated>
    Baselines at HEAD: snippet gate 1+1, PyPI-404 gate 1, truthy gate 1, legacy-org gate 2+1+0+1, root-nav missing 15 / docs-nav missing 0, dev_addr 0, mkdocs strict exit 0 (must stay 0).
  </verify>
  <done>Both configs' nav paths all resolve (0 missing); logo/favicon keys removed; PyPI link targets pyrustkmer; both installation snippets are valid Python; the docs/README example checks the found getter; every GitHub URL uses the canonical org; mkdocs.docs.yml strict build exits 0; the task is landed as one atomic commit containing exactly these 5 files.</done>
</task>

<task type="auto">
  <name>Task 3: Correct example scripts (WR-08, IN-03) and record the full 18-finding triage</name>
  <files>examples/python/demo_pyo3_binding.py, examples/python/test_pyo3_api.py, examples/python/demo_performance.py, .planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md</files>
  <read_first>
    .planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW.md (WR-08, IN-03 sections),
    .planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md (format legend: native dispositions open/fixed/skipped/deferred; reasons go in the Source cell),
    .planning/MILESTONES.md lines 30-45 (CR-02/IN-08 closure evidence),
    .planning/milestones/v1.0-phases/04-benchmark-validation/04-05-SUMMARY.md (CR-02 cfg gating, IN-08 test pin, WR-08-phase04 fingerprint guard)
  </read_first>
  <action>
    (a) WR-08: in demo_pyo3_binding.py (L284, L286) and test_pyo3_api.py (L225) replace the two dangling guide filenames with the real targets docs/guides/pyo3-binding-guide.md and docs/guides/prefix-query-guide.md (string-only edits inside the existing print statements; keep the surrounding Chinese prose intact).
    (b) IN-03: in demo_performance.py rename the misnamed throughput variable at L121-122 to throughput_gbps (it holds GB/s), and give queries_per_second at L124 the same zero-guard style its sibling at L121 uses (conditional expression guarding a zero sum). Examples-level only; do not touch scripts/bench/ harness code.
    (c) Disposition doc — update BOTH the YAML frontmatter findings list and the markdown table so every one of the 18 open rows carries its census disposition: the 11 fix-now rows and the 4 already-fixed rows become fixed; the 3 defer rows (IN-06, IN-07, IN-09) become deferred. CR-01's existing fixed row stays byte-identical. Set the frontmatter open count to 0; keep total at 19. In each Source cell write a one-line rationale (avoid literal pipe characters — the legend says they are escaped prose): for fix-now rows cite the corrected file(s) + quick-261111-spz; for already-fixed rows cite the evidence (IN-01: config relocation, single search plugin per config, root nav covers tree; IN-05: no preview bind-address override in either live config, mkdocs loopback default; IN-08: 04-05 commit 78e5eec, test_compare.py:200 assertIn; CR-02: MILESTONES.md L35/L40, 04-05 commit 444f660, CI windows-latest clippy green); for deferred rows write the reason plus a recommended follow-up — IN-06: interpolate the route name in the two expect_err messages (format! or drop the placeholder) in a test-hygiene pass; IN-07: reject leading-hyphen paths in validate_path (or prefix ./) with a pinned test under scripts/bench/tests/; IN-09: emit an explicit note in the rendered fingerprints section for results files lacking an input_fingerprint, pinned by a test_render_report test.
    (d) Append a "## Triage 2026-11-11 (quick-261111-spz)" section: a table mapping each of the 18 ids to its four-way class (fix-now / defer / already-fixed / wont-fix) with the one-line rationale from the census; a vocabulary-mapping note (fix-now applied and already-fixed map to native fixed; defer maps to deferred; wont-fix would map to skipped — none); a provenance note (current review holds 14 findings; IN-07/08/09 and CR-01/02 are carried rows from an earlier round); a path note (STATE.md's .planning/phases/... path is stale, live path is under .planning/milestones/v1.0-phases/); and the count reconciliation (18 open matched the live doc; 0 critical open after triage). Preserve the doc's existing legend text.
    (e) Scope guard: make NO edit under src/, tests/, scripts/, pyo3/, or .github/ — the three deferred findings are recorded, not fixed.
    (f) Commit this task atomically: stage exactly examples/python/demo_pyo3_binding.py, examples/python/test_pyo3_api.py, examples/python/demo_performance.py, and .planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md by path, then commit with message docs(quick-261111-spz): fix example refs and record Phase-04 review triage (WR-08, IN-03). Stage nothing else; the SUMMARY.md created afterwards stays uncommitted (orchestrator-owned).
  </action>
  <verify>
    <automated>cd /Users/forrest/GitHub/rustkmer &amp;&amp; test "$(grep -c 'PYO3_PYTHON_BINDING_GUIDE\|PREFIX_QUERY_USAGE_GUIDE' examples/python/demo_pyo3_binding.py examples/python/test_pyo3_api.py | awk -F: '{s+=$NF} END {print s}')" = 0 &amp;&amp; test "$(grep -c 'docs/guides/pyo3-binding-guide.md' examples/python/demo_pyo3_binding.py)" -ge 1 &amp;&amp; test "$(grep -c 'throughput_mbps' examples/python/demo_performance.py)" = 0 &amp;&amp; test "$(grep -c 'throughput_gbps' examples/python/demo_performance.py)" -ge 2 &amp;&amp; grep -n 'queries_per_second =' examples/python/demo_performance.py | grep -q 'if\|or ' &amp;&amp; python3 -m py_compile examples/python/demo_pyo3_binding.py examples/python/test_pyo3_api.py examples/python/demo_performance.py &amp;&amp; D=.planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md &amp;&amp; test "$(grep -c 'disposition: open' "$D")" = 0 &amp;&amp; grep -q '^open: 0' "$D" &amp;&amp; test "$(grep -c '^  - id: ' "$D")" -ge 19 &amp;&amp; test "$(grep -c 'disposition: deferred' "$D")" -ge 3 &amp;&amp; test "$(grep -c '| open |' "$D")" = 0 &amp;&amp; grep -q 'Triage 2026-11-11 (quick-261111-spz)' "$D" &amp;&amp; test "$(grep -c '{route}' tests/merge_bounded_memory_tests.rs)" -ge 2 &amp;&amp; test -z "$(git status --porcelain -- src/ tests/ scripts/ pyo3/ .github/)" &amp;&amp; C=$(git rev-parse HEAD) &amp;&amp; FILES=$(git diff --name-only "$C^..$C") &amp;&amp; test "$(printf '%s\n' "$FILES" | LC_ALL=C sort | tr '\n' ' ')" = ".planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md examples/python/demo_performance.py examples/python/demo_pyo3_binding.py examples/python/test_pyo3_api.py "</automated>
    Baselines at HEAD: dangling-guide gate 2+1, misnamed-variable gate 2, untriaged-rows gate 18, deferred-rows gate 0, route-placeholder gate 2 (must STAY 2 — proof of no test edit).
  </verify>
  <done>Both example scripts reference real guides and compile; the throughput variable is correctly named and guarded; the disposition doc records all 18 triage decisions (15 fixed, 3 deferred, 0 open) with rationales and follow-ups, preserves all 19 rows and the CR-01 row, and carries the appended triage section; git status proves zero changes under src/, tests/, scripts/, pyo3/, .github/; the task is landed as one atomic commit containing exactly these 4 files.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| docs/examples -> user copy-paste | Corrected CLI commands and Python snippets are executed by users; wrong fixes propagate (mitigated by grounding every fix in src/cli/args.rs and the PyO3 surface) |
| disposition record -> milestone close | The triage record gates /gsd-complete-milestone; a silently dropped row would hide an open finding |

## STRIDE Threat Register

Quick-item namespace T-SPZ-* (this is a quick-batch item, not phase 04 planning — avoids collision with the existing T-04-XX register in the phase's PLAN files).

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-SPZ-01 | Tampering | 04-REVIEW-DISPOSITION.md rewrite | medium | mitigate | Row-preservation gates: 19 id rows retained, CR-01 row unchanged, open count 0, exactly 3 deferred — a dropped or silently flipped row fails Task 3 verify |
| T-SPZ-02 | Information Disclosure | mkdocs preview binding (IN-05) | low | mitigate | Verify dev_addr absent from both live configs so mkdocs' loopback default applies; gate greps both configs |
| T-SPZ-03 | Elevation of Privilege | scripts/bench/bench.py validate_path (IN-07) | medium | accept | Pre-existing harness edge: leading-hyphen paths could parse as options in the sh -c arm; paths are operator-supplied and metacharacter screening is active; item scope forbids harness behavior changes — deferred with a pinned-test follow-up recorded in the disposition doc; below the high blocking threshold |
| T-SPZ-SC | Tampering | npm/pip/cargo installs | low | accept | No package-manager install tasks in this plan (mkdocs and PyYAML already present in the environment); no new dependency or supply-chain install surface is introduced |
</threat_model>

<verification>
Phase-level checks (all cwd at checkout root, run after the task commits):
1. Every Task 1-3 automated gate passes after that task's commit (baselines recorded per task); each per-task commit-range gate (<task-commit>^..<task-commit>, with the task commit at HEAD) proves the commit touched exactly its own file set.
2. `mkdocs build -f mkdocs.docs.yml --strict --site-dir /tmp/spz-mkdocs-verify` exits 0 (was 0 at baseline; must not regress).
3. `git status --porcelain -- src/ tests/ scripts/ pyo3/ .github/` is empty after all commits — the no-behavior-change contract.
4. Disposition doc: 19 rows, 0 open, 15 fixed, 3 deferred; triage section present; CR-01 row untouched.
5. Full-scope lock — run after Task 3's commit; with exactly 3 task commits, HEAD~3 is the parent of the item's first commit and HEAD its last: `FILES=$(git diff --name-only HEAD~3..HEAD) &amp;&amp; test "$(printf '%s\n' "$FILES" | LC_ALL=C sort | tr '\n' ' ')" = ".planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md CONTRIBUTING.md README.md docs/README.md docs/api-reference/index.md docs/api-reference/overview.md docs/index.md docs/installation.md examples/python/demo_performance.py examples/python/demo_pyo3_binding.py examples/python/test_pyo3_api.py mkdocs.docs.yml mkdocs.yml "` — the union of changed files equals exactly the 13-file files_modified set (the orchestrator also performs the advisory scope-conformance check at merge).
</verification>

<success_criteria>
- All 18 open findings triaged with exactly one disposition + one-line rationale each; 0 remain open.
- 11 trivial docs/examples corrections applied and gate-proven; 4 already-fixed closures evidenced; 3 code-level findings deferred with concrete follow-ups.
- No src/, tests/, scripts/, pyo3/, or .github/ file modified; exactly 3 atomic per-task commits whose union is exactly the 13-file set; SUMMARY.md left uncommitted for the orchestrator.
- mkdocs.docs.yml strict build green; both configs' nav fully resolving; canonical org consistent.
</success_criteria>

<output>
Create `.planning/quick/261111-spz-triage-the-18-open-v1-0-phase-04-review-findings-in-planning/261111-spz-SUMMARY.md` when done.
Task deliverables are already committed — one atomic commit per task, per the commit contract in the objective. SUMMARY.md itself stays uncommitted: the orchestrator commits PLAN/SUMMARY/STATE artifacts only. Do not touch BATCH.json, STATE.md, or ROADMAP.md.
</output>
