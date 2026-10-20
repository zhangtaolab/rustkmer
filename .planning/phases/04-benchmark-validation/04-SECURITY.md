---
phase: "04"
slug: benchmark-validation
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-20"
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time (all 5 PLANs carry `<threat_model>` blocks); verified post-execution at ASVS L1 during the 2026-10-20 verification refresh.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| env vars → harness | RUSTKMER_BENCH_INPUT / RUSTKMER_BENCH_MODE values cross from the caller's environment into path resolution and mode selection | untrusted config strings |
| time-output stderr → parser | OS tool output text crosses into numeric results (format drift would corrupt numbers silently) | external tool text |
| dataset paths → sh -c pipeline | User-provided input paths cross into a shell string assembled for the jellyfish gz arm — the only shell invocation in the harness | filesystem paths |
| jellyfish stats text → parity assertion | External tool's human-format output crosses into the correctness gate | external tool text |
| PR diff → baseline + workflow | A pull request can edit the committed baseline or the gate workflow it is judged by | reviewed code |
| CI runner → results.json | Shared-runner noise crosses into gate numbers (variance, not malice) | measurement noise |
| dataset files → results/report | The measured input's identity crosses into every committed claim (fingerprint is the binding) | file identity (size + sha256) |
| results JSONs → report | The report's authority derives entirely from the committed JSONs | committed evidence |
| bench.py ↔ git history | harness_source_commit() reads the repo's git log as a provenance input | commit topology |
| dev branch → GitHub Actions | The push crosses into CI; the windows-latest clippy verdict is the only authoritative lint of the Windows cfg tree | source code |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Spoofing | parse_time_output | medium | mitigate | Dual-format regexes pinned by fixture unit tests on both platforms (`tests/fixtures/time_{l_macos,v_linux}.txt`); missing RSS/wall line raises `ValueError` (bench.py:89–115) instead of best-effort parsing | closed |
| T-04-02 | Tampering | input provisioning | medium | mitigate | Input fingerprint (size_bytes + sha256) recorded per input in results.json (8 sha256 sites in bench.py); `input_fingerprint` verified present in committed 04-results-*.json | closed |
| T-04-03 | Tampering / EoP | jellyfish_count_cmd sh -c assembly | high | mitigate | `validate_path` allowlist (bench.py:186) screens every path before any shell string is assembled; single sh -c site fed only by validated paths + regex-validated constants; hostile-filename tests in test_cmd_matrix.py (18 hostile/injection references); all other invocations list-form subprocess | closed |
| T-04-04 | Spoofing | cache_state recording | medium | mitigate | `cache_state_from(in_ci, platform, purge_succeeded)` (bench.py:629) derives the label from the actual sudo -n purge outcome / GITHUB_ACTIONS marker, never configuration intent | closed |
| T-04-05 | Elevation of privilege | committed baseline + benchmark.yml | medium | mitigate | Baseline/workflow changes are ordinary reviewed diffs; README documents the same-job base-ref dual-checkout upgrade path (scripts/bench/README.md §"Upgrade path"); generous thresholds make a baseline shave conspicuous | closed |
| T-04-06 | Tampering / Spoofing | workflow steps | high | mitigate | benchmark.yml fails loudly: 0 `continue-on-error`, 0 conditional `if:` guards (verified by grep 2026-10-20; negative greps at 04-03 Task 2) | closed |
| T-04-07 | Repudiation | docs/benchmark-report.md | high | mitigate | `--render-report` is the only writer (render_report, bench.py:1319); byte-identical re-render check (14 byte/identical assertions in test_render_report.py) makes any hand-edit detectable; raw per-rep numbers committed beside medians | closed |
| T-04-08 | Tampering | milestone input provenance | medium | mitigate | Fingerprint (size + sha256 per gz) echoed in the report's input-provenance lines; substitute labeling mandatory (report line 7 banner); parity gate independently catches a semantically different input | closed |
| T-04-09 | Repudiation | report provenance self-reference | high | mitigate | `harness_source_commit()` (bench.py:977) provenance line names the bench.py commit; commit-boundary discipline enforced in 04-05 (test/feat commit pair 4eeb9d4/78e5eec; report commits ride alone); provenance pinned in test_render_report.py | closed |
| T-04-10 | Tampering | render_report methodology-figure sourcing | medium | mitigate | WR-08: figure sourced from the first mode=full entry with guarded named `ValueError` (bench.py:1332/1338) on empty/absent input_fingerprint; unit-pinned for both failure cases | closed |
| T-04-11 | Spoofing | compare.py advisory-mode PASS summary | medium | mitigate | IN-08: exit-0 advisory test pins the "wall breach(es) advisory, not gating" summary (11 advisory references in test_compare.py) so swapping it for a plain all-axes PASS line fails the suite | closed |
| T-04-SC | Tampering | package installs | high | mitigate | Stdlib-only hard constraint; import census 2026-10-20: scripts/bench uses only stdlib + local `scripts.bench` modules, zero third-party; phase installed nothing — Package Legitimacy Audit vacuously clean | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|

*Accepted risks do not resurface in future audit runs.*

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-20 | 12 | 12 | 0 | execute-phase verification refresh (ASVS L1, grep-depth) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-20 — L1 evidence: every mitigation greps to implementation or committed artifact; unittest 9/9 green + cargo test 23 binaries green at HEAD `5a2bda7` at audit time.
