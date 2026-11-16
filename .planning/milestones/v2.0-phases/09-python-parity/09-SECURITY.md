---
phase: "09"
slug: python-parity
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-16"
---

# Phase 09 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time (all 5 PLANs carry `<threat_model>` blocks); verified post-execution at ASVS L1 on 2026-11-16 via `/gsd-secure-phase` — a retroactive verification record for the SHIPPED phase (HYG-03), not new mitigations. Grounding: `09-VERIFICATION.md` (38/38 passed, 2026-11-14) and `09-REVIEW.md` (independent suite re-runs; 0 critical).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Python caller → PyO3 binding | Python strings/objects cross into Rust; only owned `Send` values may cross `py.detach` | untrusted Python objects |
| PyO3 binding → Rust core engine | k, canonical, threads, and file paths cross into `CountEngine` | validated numeric/path parameters |
| Input file → parser | untrusted FASTA/FASTQ bytes reach the strict `bio` readers and the window extractor | external file bytes |
| site-packages → measured artifact | the imported `.so` may be stale or shadowed | binary identity |
| in-memory pairs → on-disk `.rkdb` bytes | sorting, header flags, and record order determine every byte | serialized records |
| committed golden fixture → test assertion | the fixture is ground truth and must never be regenerated | committed evidence |
| committed baseline → comparison verdict | the baseline is the fixed reference every claim is measured against | committed evidence |
| controller → fresh worker subprocess | each measured rep is a new interpreter; the extension it imports may be stale/shadowed | subprocess artifacts |
| measured medians → PASS/FAIL exit code | a misreported verdict would manufacture a win | gate verdict |
| prior evidence artifact → before/after record | a malformed prior could misrepresent the change (`--previous`) | external JSON |
| documentation → user expectations | an inaccurate number misleads users | published docs |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-9-01 | Tampering / Elevation | `add_from_*` / `save_database` detach closures | high | mitigate | Every `py.detach` closure captures only owned `Send` values (String path, cloned `Arc<RustPyCounter>`, usize), all `move`; `Ungil` makes a GIL-bound capture a compile error (10 detach sites in `pyo3/src/counter.rs`; independently re-verified by `09-REVIEW.md`) | closed |
| T-9-02 | Tampering / Supply chain | imported `pyrustkmer` extension | high | mitigate | Rebuild from source in `.venv313`; `pyrustkmer.__version__` asserted non-empty with no skip guard (`pyo3/tests/test_version.py:24-25`); tests record the module file | closed |
| T-9-03 | Denial of service | malformed FASTA/FASTQ under `panic = "abort"` | medium | mitigate | `bio` strict readers; errors mapped to `ProcessingError` → `PyValueError` (18 error-mapping sites in `pyo3/src/counter.rs`); no `unwrap`/`expect` on Python-reachable paths (review-confirmed); malformed-input behavior asserted by tests | closed |
| T-9-04 | Tampering | `.rkdb` header/entry bytes from the new binding path | high | mitigate | Binding calls the single frozen `format.rs` constructor; cross-surface sha256 vs CLI and committed golden, t1/t4/default equality (`pyo3/tests/test_save_database_byte_identity.py`, 7 tests; cross-surface sha `a5da813e…` reproduced by review) | closed |
| T-9-05 | Tampering | pairs marked sorted without being sorted | high | mitigate | Constructor requires caller-proven order; `debug_assert` non-decreasing; only caller sorts with `par_sort_unstable_by_key` (`tests/sorted_pairs_constructor_tests.rs`, 5 tests green at review) | closed |
| T-9-06 | Repudiation | golden fixtures regenerated to green the gate | high | mitigate | Fixtures read-only in tests; `git status --porcelain -- tests/fixtures/` empty (verified 2026-11-16); the audit records the pure-addition `format.rs` proof (`evidence/format_rs_blob_audit.json`) rather than recapturing | closed |
| T-9-07 | Tampering / DoS | concurrent `save_database` snapshot during mutation | low | accept | Snapshot explicitly documented as non-linearizable (no atomicity promise); no new locking introduced. Related doc gap IN-03 (`09-REVIEW.md`) stays info-only tracked — not re-opened as a gate-blocking threat | accepted |
| T-9-08 | Repudiation / Tampering | baseline and threshold handling | high | mitigate | Baseline never edited or recaptured; thresholds in code; parity + exact counts asserted before timing; exit 1 is a real FAIL with artifact; provenance on every doc; baseline identity by name + `threads == 1`, never positional (WR-01 fixed `72a8399`) | closed |
| T-9-09 | Tampering | cross-host comparison | high | mitigate | Platform flavor, `provenance.platform`, k/canonical, regenerated-control fingerprint, baseline exact counts all guarded; mismatch exits 2 with no artifact; compare mode rejects non-1 `--threads` and requires observed thread resolution (WR-02 fixed `266492a`; `validate_worker_stats`/`validate_baseline_identity` present, 5 references in `python_bench.py`) | closed |
| T-9-10 | Tampering / Supply chain | measured Python extension | high | mitigate | Fresh worker per rep; `validate_worker_stats` requires a native `.so` under the interpreter's site-packages; module sha256 recorded; rebuilt extension version-asserted (T-9-02 guard) | closed |
| T-9-11 | Repudiation | documented before/after numbers | medium | mitigate | Numbers taken from the committed Phase 5 artifact; content pinned in docs + README (`docs/user-guide/n-read-semantics.md:46` nine-case table 37/70/37; `scripts/bench/README.md:255-265`); 09-05 re-proved them with a measured run | closed |
| T-9-12 | Tampering | `--previous` prior artifact | medium | mitigate | Strict k/canonical/case-set/shape validation before embedding (`_validated_surface_counts` :127, `ValueError` raises :131/:137/:157/:159); malformed JSON → exit 2 (`EXIT_INVALID = 2` :63-65, `invalid()` :77) | closed |
| T-9-13 | Repudiation / Tampering | measured extension and binary provenance | high | mitigate | Rebuild from the final tree in `.venv313`; `__version__` assert with no skip; module sha256 + path + git commit/dirty + binary sha256 recorded in both measured artifacts (`evidence/*.json` all carry sha256) | closed |
| T-9-14 | Tampering / Integrity | goldens, fixtures, and the frozen writer | high | mitigate | Fixtures read-only and re-hashed against the committed manifest; `git status -- tests/fixtures/` empty; the five byte/constructor tests re-run; `format.rs` change audited as pure addition (78 insertions, 0 deletions; pre-blob `eb0d5bf2…`, post-blob `dedfd95a…`) | closed |
| T-9-SC | Tampering | cargo/pip dependency set | high | mitigate | Phase installed no packages; manifests/lockfiles unchanged during the phase (post-phase dep REMOVAL hygiene `a5eecad` only removed unused crates — the safer direction); `--locked` Rust gates; venv pre-existing | closed |

*Status: open · closed · accepted*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Info Findings Boundary (per 11-08 plan constraint)

The 8 Info findings in `09-REVIEW.md` (IN-01..IN-08: preservation-gate strength on the parent implementation, stale docstring, non-linearizable snapshot documentation, `--previous` prior-state guard breadth, cross-record join detection, importable-extension test failure mode, unreachable error arm, single-rep CV blindness) remain **info-only and tracked** (STATE.md Deferred Items). They are not re-opened as gate-blocking threats by this record; the 4 Warning findings (WR-01..WR-04) were fixed during Phase 9 (commits `72a8399`, `266492a`, `669e91f`, `af4d954`).

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| T-9-07 | T-9-07 | `save_database`'s snapshot under concurrent mutation is non-linearizable by design; `merge_local_counts` is documented concurrent-safe and no atomicity promise is made. Doc gap IN-03 tracked as info-only. | plan-time disposition (09-02-PLAN), confirmed at verification | 2026-11-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-16 | 15 | 14 | 0 | /gsd-secure-phase retroactive verification (ASVS L1, grep-depth; short-circuit: threats_open 0, plan-time register, L1 sufficient) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-16 — L1 evidence: every mitigation greps to implementation, test, or committed artifact in the archived phase tree; grounding includes `09-VERIFICATION.md` (38/38 passed, re-verified 2026-11-14) and `09-REVIEW.md` (0 critical, independent suite re-runs: cargo 5+ suites, pytest 119+9+8, bench units 65+33, full differential run exit 0).
