---
phase: "12"
slug: "full-scale-merge-verdict"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-17"
---

# Phase 12 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Controller → tool subprocesses | `phase11.py` drives `rustkmer`/`jellyfish` through the Plan-11 builders (list-form argv, validate_path inside builders) | artifact paths, stage flags — no new argv construction |
| Recorded evidence → renderer | `render_report_text` reads only validated committed JSONs; no measurement literals, no clock | evidence bytes — byte-identical re-render proof pins the render |
| On-disk artifacts (consumed read-only, then deleted) | 8 artifacts re-hashed at round 0 and per stage start; manifest.json retained after cleanup | artifact bytes — identity preserved in the retained manifest |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-12-01 | Tampering | render stage / render_report_text | high | mitigate | Mechanical renderer (6 refs): every number from validated JSONs, no literals/clock; byte-identical double-render + 12-RENDER-PROOF.json sha256 (T-04-07 pattern); validate-then-write | closed |
| T-12-02 | Tampering | input artifacts between stages | high | mitigate | revalidate_stage + assert_binary_identity (14 refs): round-0 re-hash of all 8 artifacts, unrecorded rejection, re-run at parity/timed stage starts, source-fingerprint cross-check (real path shape fixed pre-session, 68e2f3e) | closed |
| T-12-03 | Tampering | subprocess argv construction | medium | mitigate | list-form argv via bench.py builders (validate_path inside builders, 9 sites verified Phase 11); shell=True = 0 in phase11.py | closed |
| T-12-04 | DoS (local) | disk guards | medium | mitigate | controller-computed 282 GiB budget through check_disk_floor at round 0 (exit-3 block + stated shortfall); ensure_disk_headroom per measured rep; explicit-flag override only (7 refs; D-12) | closed |
| T-12-05 | Tampering | new gates (Leg-2 diff, verdict rule, schedule, conservation) | high | mitigate | GREEN/RED unit proofs for every gate — 73-test suite; first-difference naming, empty-dump loud errors, t1-excluded verdict, EXACT anchor mismatch raise, cross-rep conservation raise | closed |
| T-12-06 | Information | evidence documents | medium | mitigate | write_doc/write_evidence_doc validate_provenance at write time (14 refs); fingerprints from fingerprint()/revalidate_stage, never hand-transcribed | closed |
| T-12-SC | Tampering | npm/pip/cargo installs (×4 plans) | high | mitigate | zero installs — phase11.py imports stdlib only (argparse/datetime/hashlib/json/math/os/pathlib/platform/shutil/statistics/subprocess/sys/time + local scripts pkg); binaries pinned by identity tripwires; mid-execution install proposals halt for a blocking checkpoint | closed |
| T-12-04 (12-03 variant) | DoS (local) | deletion freeing space | low | accept | deletion only frees ~86.74 GiB; no allocation risk introduced — accepted, recorded in 12-WRAPUP.md | closed (accepted) |

*Status: closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-12-01 | T-12-04 (12-03 variant) | Deletion frees space only; no allocation risk | workflow (plan disposition) | 2026-11-17 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-17 | 8 register rows (T-12-01..06 + T-12-SC + accepted variant) | 8 | 0 | orchestrator (L1 grep-depth, ASVS 1) — verify:post secure-phase hook |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-17
