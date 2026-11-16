---
phase: "10"
slug: benchmark-verdict
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-16"
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time (all 4 PLANs carry `<threat_model>` blocks); verified post-execution at ASVS L1 on 2026-11-16 via `/gsd-secure-phase` — a retroactive verification record for the SHIPPED phase (HYG-03), not new mitigations. Grounding: `10-VERIFICATION.md` (8/8 passed, 2026-11-14) and `10-REVIEW.md` + `10-REVIEW-DISPOSITION.md` (all findings dispositioned).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| measured subprocess → `/usr/bin/time` stderr → artifact | the only source of wall and peak-memory numbers; parse drift silently corrupts every claim | external tool text |
| harness controller → verdict block → report | the verdict must be a pure function of recorded medians | gate verdict |
| `.venv313` site-packages → measured artifact | the imported extension (or a stale/shadowed copy) is the measured subject | binary identity |
| Python worker payload → controller | counts, module path, resolved thread count cross a process boundary as JSON | subprocess JSON |
| committed baseline → gate | the parity reference is the only authority for pinned counts | committed evidence |
| dataset files → measured invocation | the input bytes define the workload | external file bytes |
| measured run → evidence document | a killed or short-rep session must never become a `mode=full` result | committed evidence |
| scratch volume → run continuity | ~22 GB databases plus `.jf` per k can exhaust the volume | disk budget |
| measured CLI distinct → Python projection → run/no-run decision | the projection decides whether a ~45-60 min measurement is attempted | gate decision |
| two measurement sessions → one verdict | cross-session comparison can fabricate a result | measurement identity |
| verdict document → committed report | a YES/NO is a claim about the milestone | committed evidence |
| frozen repository contracts → phase commit | production code may not be edited to change a measured outcome | reviewed code |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-10-01 | Repudiation / Tampering | verdict block and report renderer | high | mitigate | Verdict is a pure function of recorded medians; renderer carries no measurement literal and no clock; byte-identical re-render + mutate-one-number tests prove hand edits detectable (`scripts/bench/tests/test_phase10_verdict.py`, 99 tests) | closed |
| T-10-02 | Spoofing | arm construction and verdict filtering | high | mitigate | One `BenchmarkConfig` per arm derives both tools' commands; verdict filters `threads == ACCEPTANCE_THREADS` (= 16, `phase10.py:102`, filter `:244`); t1 arm structurally excluded; no `--size` flag ever emitted | closed |
| T-10-03 | Tampering | zero-count / missing-rep acceptance | high | mitigate | `validate_worker_stats` (`python_bench.py:260`) and `check_rep_identity` (`:329`) reject zero/non-integer counts, module drift, thread drift; `verdict_block` rejects zero reps / non-positive median; every exit-2 path writes no document | closed |
| T-10-04 | Spoofing / Tampering | `py-t16` measured module | high | mitigate | Rebuild-required message; `_native_module_file` (`python_bench.py:662`) resolves the inner `.so`; `validate_worker_stats` requires a native suffix and site-prefix resolution; module sha256 recorded and identical across reps | closed |
| T-10-05 | Repudiation | rendered report statements | high | mitigate | Mandatory statements are exact literal text asserted by tests (KMC3 descope, cold-cache partial census, dev-host-only statement, t16-only rule, both surfaces' provenance — assertion cases in `test_phase10_verdict.py`) | closed |
| T-10-06 | Elevation / Tampering | committed baselines and CI baseline slots | high | mitigate | No baseline writes and no `--emit-baseline` in the phase controller; reference sha256 pinned before consumption; `git status --porcelain -- scripts/bench/baselines/` empty (verified 2026-11-16); report states dev-host-only | closed |
| T-10-07 | Tampering | dataset and reference identity | high | mitigate | Every artifact records both parts' `{path,size_bytes,sha256}` (`10-results-full-k21.json` `input_fingerprint`: part_001 2,785,381,389 B `dae91042…`); slice gate fingerprint-bound; three-way live parity passed on the measured input before medians trusted | closed |
| T-10-08 | Repudiation | partial or failed full run | high | mitigate | `run_rounds` requires every arm's full rep count; `write_doc` (`phase10.py:872`) runs `validate_schema` + `validate_provenance` before the first byte; any non-zero child or missing stats file raises before the write; document written once after the last post-arm stats read (10-03-SUMMARY: pre-run artifact written only after identity assertion + scratch deletion succeed; failed session exits 2 with no destination file) | closed |
| T-10-09 | Denial of service | disk exhaustion mid-session | medium | mitigate | `check_disk_floor` (`bench.py:1288`) aborts at the 150 GiB floor before provisioning; scratch databases deleted after stats + sha256 recorded (10-03-SUMMARY: 240 GiB free after per-k scratch deletion) | closed |
| T-10-10 | Denial of service | Python full arm memory | high | mitigate | Preflight from the measured distinct count (`86 x D` vs 110 GiB budget) is a blocking decision (`10-python-preflight.json` with overall verdict + provenance); blocked arm recorded as BLOCKED with explicit user options; no engine edit, no silent skip; mid-run failure leaves no artifact | closed |
| T-10-11 | Spoofing | cross-session / per-surface comparison | high | mitigate | Each surface compared to the jellyfish median from its OWN counterbalanced session; `cross_session` block requires identical counts, inputs, fingerprints; the k=31 jellyfish session outlier (1380.92 s CLI vs 187.14 s Python, identical counts) is disclosed mechanically, not hidden — divergence/agreement both asserted (`test_phase10_verdict.py:913/:922`) | closed |
| T-10-12 | Repudiation | verdict truthfulness | high | mitigate | The match-or-beat rule is literal in the verdict document and report (`10-verdict.json`); equality is YES by construction and tested; artifacts are immutable evidence with input sha256; render stage byte-deterministic; the k=21 NO at phase gate was kept and escalated honestly | closed |
| T-10-SC | Tampering / Supply chain | package installs | high | accept | Phase installed no package: stdlib harness, preinstalled jellyfish 2.3.1, no crate/pip addition (verified: no install commits; review confirms). Disposition is accept — the register entry stays reserved; a block would be vacuous | accepted |

*Status: open · closed · accepted*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Recorded Measurement Facts (disclosed, not defects)

Per the v2.0 milestone audit and the verdict documents: the k=31 jellyfish median differs 7.38x between the CLI session and the Python session with identical counts, inputs, and ~94.5 GB peak — disclosed mechanically by the cross-session block (T-10-11 mitigation); the verdict is robust to it (both rustkmer arms beat the faster reference). Cold-cache is only partially satisfied (30/30 reps `unavailable`, no sudo purge) and the report states this. Dev-host evidence only; no CI-class baseline was written. The CLI-gate enforcement warning from the review was dispositioned in `10-REVIEW-DISPOSITION.md`. These are recorded methodology facts, not open threats.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| T-10-SC (×4 plans) | T-10-SC | No package is installed by this phase (stdlib harness, preinstalled jellyfish, no crate/pip addition); blocking a reserved vacuous entry serves nothing. | plan-time disposition (all 4 PLANs), confirmed at verification | 2026-11-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-16 | 13 | 12 | 0 | /gsd-secure-phase retroactive verification (ASVS L1, grep-depth; short-circuit: threats_open 0, plan-time register, L1 sufficient) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-16 — L1 evidence: every mitigation greps to implementation, test, or committed artifact (`phase10.py`, `python_bench.py`, `test_phase10_verdict.py`, the committed results/preflight/verdict JSONs); grounding includes `10-VERIFICATION.md` (8/8 passed, re-verified 2026-11-14), `10-REVIEW-DISPOSITION.md` (all findings dispositioned), and the v2.0 milestone audit (verdict YES at k=21 and k=31, exact parity, 0 open review findings).
