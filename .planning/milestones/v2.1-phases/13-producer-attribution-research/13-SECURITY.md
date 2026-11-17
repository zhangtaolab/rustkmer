---
phase: "13"
slug: "producer-attribution-research"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-17"
---

# Phase 13 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Tool output → evidence doc | `/usr/bin/time` stderr, probe JSON, cargo output cross into recorded evidence; a mis-parse becomes a recorded "measurement" | timing/RSS/JSON artifacts — integrity-critical |
| Paths → subprocess argv | Dataset, scratch, and binary paths reach subprocesses (list-form argv; no shell) | filesystem paths — injection surface |
| Scratch trees → repo | Probe materialization and plain inputs live outside the repo; in-tree writes would contaminate provenance | build artifacts, binaries |
| Evidence doc → memo/decision | A partial or slice-scale doc silently feeding the D3 decision corrupts the phase gate | committed JSON → committed memo |
| Live dataset → engine/probes | Swapped or partially decompressed inputs would silently change what the arms measured | 6 gzip parts + 6 plain parts, sha256-fingerprinted |
| Deletion → evidence integrity | Deleting bytes before their provenance is committed makes the recorded runs unreproducible-in-principle | plain FASTQ parts, probe scratch |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-13-01 | Tampering | `measured_run` / probe-JSON parsing (`scripts/bench/phase13.py`) | high | mitigate | Fail-loud rc checks, units-pinned parse_time_output, `json.loads` + k-field/zero-entry guards, schema assertions before any math; unit-proven (80-test module) | closed |
| T-13-02 | Denial of Service (disk) | plain inputs (~60 GB) + per-rep outputs + probe trees | medium | mitigate | `ensure_free_space` before decompression (463.2 GB free vs 81.4 GB required, recorded `disk_check_passed: true`); per-rep scratch-output deletion; post-memo deletion + `scratch_cleaned: true` | closed |
| T-13-03 | Tampering (provenance) | repo tree contaminated by probe builds → fingerprint gate meaningless | high | mitigate | `refuse_repo_root` materialization into `/tmp/phase13-probe-scratch`; `binary_provenance.git_dirty` asserted false; evidence doc records `git_dirty: false` | closed |
| T-13-04 | Repudiation | silent partial-session acceptance (crashed arm reported complete) | medium | mitigate | Exit-code contract 0/2, incremental per-run doc writes, memo derivation refuses incomplete matrices or non-full records; matrix-completeness gate green | closed |
| T-13-05 | Tampering | live `measured_run` / probe-JSON parsing during the session | high | mitigate | Plan-13-01 fail-loud guards execute per run (rc checks, k-field cross-checks, zero-nano guards); any guard abort is exit-2, never a recorded number | closed |
| T-13-06 | Denial of Service (disk) | plain inputs (~60 GB) + per-rep outputs during the ~2 h session | medium | mitigate | Prep-stage disk arithmetic before decompression; per-rep output deletion inside `run_measure`; volume re-check per the driver's per-rep guard | closed |
| T-13-07 | Tampering (provenance) | mid-session repo contamination or binary swap invalidating recorded fingerprints | high | mitigate | `git_dirty: false` at prep; `tree-clean` closing gate passed over `src/`, `pyo3/src/`, `examples/`; probe binaries fingerprinted and recorded per run | closed |
| T-13-08 | Repudiation | crashed session reported as a complete measurement | medium | mitigate | Incremental per-run doc writes + matrix-completeness python gate (`matrix-ok`) before any downstream consumption; exit-2 on any incomplete state | closed |
| T-13-09 | Tampering | memo content (`13-GATE-MEMO.md`) | high | mitigate | Deterministic render from committed evidence + byte-identical re-render proof (`13-RENDER-PROOF.json`, `byte_identical: true`) + section-content gate; zero hand-typed measurement numbers | closed |
| T-13-10 | Repudiation | D-04 deletion ordering | medium | mitigate | Deletion gated on the committed memo (`ff16c08` precedes `a46b9ea`); provenance verified present in the committed evidence before deletion (`lifecycle-ok`); wrap-up with regeneration path committed | closed |
| T-13-SC | Tampering | cargo builds (locked graph; zero registry installs) | high | mitigate | RESEARCH Package Legitimacy Audit verdict "(none installed)"; all builds `cargo build --release --locked`; every scratch probe's `Cargo.lock` seeded from a committed, sha256-verified fixture before its `--locked` build; no npm/pip/cargo registry install occurs in this phase | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| — | — | No accepted risks. | — | — |

*Accepted risks do not resurface in future audit runs.*

*No accepted risks.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-17 | 11 | 11 | 0 | gsd-secure-phase (ASVS L1, grep-depth; register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-17
