---
phase: "11"
slug: "merge-characterization-harness-prep"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-17"
---

# Phase 11 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Harness → tool subprocesses | `bench.py` / `prepare_inputs.py` / `merge_characterize.py` spawn `rustkmer` and `jellyfish` via list-form argv, no shell | artifact paths, `-s`/`-t` flags (operator-controlled, validated) |
| On-disk artifacts (outside repo) | `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` consumed by measurement and Phase 12 round 0 | artifact bytes — integrity guarded by manifest sha256 + revalidate |
| Evidence JSON committed to repo | ladder/rehearsal/prepare records under `.planning/phases/11-*/` | measurement provenance consumed by D-10 floor derivation and Phase 12 scheduling |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-11-01 | Tampering | jellyfish_merge_cmd / build_merge_cmd path handling | medium | mitigate | `validate_path` before argv (bench.py, 9 sites); list-form arms, no shell; ordering assertion fails loud | closed |
| T-11-02 | DoS (gate corruption) | arm spec wiring into run_comparison_protocol | medium | mitigate | `assert_arm_ordering` (bench.py) raises RuntimeError on count-before-merge ordering violation before the protocol runs | closed |
| T-11-03 | Tampering | artifact bytes between build and use | high | mitigate | manifest sha256 per artifact + `revalidate` verb re-hashes all 8 records, fails loud (prepare_inputs.py, 27 sha256/revalidate sites) | closed |
| T-11-04 | Tampering | prepare stage subprocess argv | medium | mitigate | `validate_path` screening (T-04-03 stance); list-form subprocess only, zero `shell=True` across harness | closed |
| T-11-05 | Repudiation | provenance of who/what built each artifact | medium | mitigate | `binary_provenance` (hashes executable bytes) + `command_line` recorded per artifact — no manual transcription | closed |
| T-11-06 | DoS (gate corruption) | jellyfish info / stats parsing | medium | mitigate | fail-loud parsers raise on missing fields instead of recording empty occupancy | closed |
| T-11-07 | Repudiation | stale v1.0 verdict cited as current | medium | mitigate | SUPERSEDED banner at docs/benchmark-report.md:1 + D-06 grep sweep with zero-unlabeled-cite gate; rule in 11-HYGIENE-RECORD.md | closed |
| T-11-08 | Tampering | merged artifacts consumed by the gate | high | mitigate | per-k-mer dump-vs-dump deep leg cannot pass a corrupted merge (incl. canonicality mixing, Pitfall 1); aggregate legs fail fast first | closed |
| T-11-09 | DoS (gate corruption) | dump parsing (normalize_dump_lines) | medium | mitigate | fail-loud parsing: malformed/empty dump lines raise with offending content | closed |
| T-11-10 | Tampering | artifact bytes from build until Phase 12 use | high | mitigate | manifest sha256 + revalidate re-run in 11-05 verify (2 records in 11-PREPARE-RECORD.md); Phase 12 round 0 re-runs again | closed |
| T-11-11 | DoS (resource exhaustion) | ~70–87 GiB artifact build on shared volume | high | mitigate | budget arithmetic §5 in 11-PREPARE-RECORD.md before .jf builds; blocking checkpoint reviewed 359 GiB free vs 54 GiB projection; APFS-lag lesson recorded | closed |
| T-11-12 | Repudiation | artifact provenance | medium | mitigate | stage-recorded binary_provenance + command_line (same mechanism as T-11-05) | closed |
| T-11-13 | Tampering | slice/scratch path handling | medium | mitigate | `refuse_repo_root` reused (merge_characterize.py:415,472); list-form subprocesses; prepare-stage paths screened by 11-02 guard | closed |
| T-11-14 | DoS (resource exhaustion) | ladder scratch on shared volume | medium | mitigate | GiB-scale rungs; `scratch_cleaned: true` recorded in 11-LADDER-RESULTS.json, scratch removed from disk | closed |
| T-11-15 | DoS (gate corruption) | route attribution + stats parsing | low | mitigate | fail-loud parsing; route recorded `not-reported` (5 sites) when tool does not state it — no invention | closed |
| T-11-16 | DoS (resource exhaustion) | full-scale Phase 12 session disk usage | high | mitigate | derived floor 136 GiB tripwire-pinned, exit-3 block with stated shortfall, `--disk-floor-override` prints shortfall, per-rep re-check in protocol loop (D-10/D-11/D-12) | closed |
| T-11-17 | Repudiation | rehearsal evidence framing | low | mitigate | RSS context-only in 11-REHEARSAL-RESULTS.json; no memory-win claim over streaming comparator; t1 semantics per research A6 | closed |
| T-11-18 | Repudiation | stale pool-size formula misleading operators (WARNING-2) | low | mitigate | README states exactly-2-at-N=1 / 2N+1-at-N>1 citing thread_pool_size_tests.rs; stale "requested + 1" = 0 hits | closed |
| T-11-19 | Repudiation | evidence-debt records forged by hand | low | mitigate | HYG-02/HYG-03 produced through named workflows (validate/secure-phase); archive records verified with valid frontmatter (4×VALIDATION validated, 2×SECURITY) | closed |
| T-11-SC | Tampering | npm/pip/cargo installs (×8 plans) | high | mitigate | zero package installs — new harness files import stdlib only (argparse/datetime/json/os/pathlib/re/shutil/subprocess/sys/contextlib/io/types/unittest + local `scripts` package); binaries pinned in 11-RESEARCH.md; Package Legitimacy Audit N/A | closed |

*Status: closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|

*No accepted risks.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-17 | 27 | 27 | 0 | orchestrator (L1 grep-depth, ASVS 1) — verify:post secure-phase hook |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-17
