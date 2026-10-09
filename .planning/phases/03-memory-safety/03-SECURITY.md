---
phase: "03"
slug: "memory-safety"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-09"
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| rkdb file input → merge core | Untrusted on-disk `.rkdb` files (possibly corrupt/foreign/adversarial) parsed by header-only readers and route validators | 42-byte headers, 20-byte records; integrity-validated (magic + version) before any field is trusted |
| User budget string → parse_memory_size | CLI `--max-memory` / Python `max_memory=` strings parsed into byte budgets | Untrusted numeric grammar; all overflow paths return Err (checked_mul), never panic |
| Shared temp_dir → merge temp artifacts | Multiple processes share one temp_dir; orphaned artifacts from killed merges live there | Shard dirs (`rustkmer-merge-*`), loose chunk files (`rustkmer_sort_*/rustkmer_merge_*.chunk`); TTL-gated sweep refuses symlinks |
| Python caller → PyDatabase.merge | Python-supplied paths, kwargs, and budgets entering the Rust core | Validated at the binding boundary (empty list, file existence, merge_mode enum, budget grammar) then routed through the same bounded core as the CLI |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering | estimate_total_kmers header read | medium | mitigate | DatabaseHeader::read_from validates magic+version; file_size/20 fallback only over-estimates (conservative routing) | closed |
| T-03-02 | Denial of Service | estimator OOM-on-estimate (pre-D-01) | high | mitigate | header-only estimator; from_file_path removed from the estimate path — covered by estimator_reads_header_only_no_materialization | closed |
| T-03-03 | Information Disclosure | reject-path error verbosity | low | accept | byte counts in Err messages, not sensitive; local CLI | closed (accepted) |
| T-03-04 | Tampering | temp-file symlink TOCTOU | medium | mitigate | tempfile O_CREAT\|O_EXCL rand-named subdirs | closed |
| T-03-05 | Denial of Service | disk exhaustion from orphaned shards | high | mitigate | process-unique subdir + TTL sweep; UAT-verified live via real SIGKILL/reclaim run (03-UAT test 21) | closed |
| T-03-06 | Tampering | cross-process merge collision | medium | mitigate | rand_bytes(8) subdir namespace; two_concurrent_merges_do_not_collide | closed |
| T-03-07 | Tampering | sweep removes non-rustkmer dir | low | accept | rustkmer-merge-* prefix + 7-day TTL | closed (accepted) |
| T-03-08 | Elevation of Privilege | temp file permissions | low | mitigate | tempfile 0600 default perms | closed |
| T-03-09 | Tampering | u128→u64 narrowing in increment | medium | mitigate | debug_assert guard on the Dense arm (table.rs:224, verified) + differential tests | closed |
| T-03-10 | Tampering | on-disk format drift from widening | high | mitigate | 12 golden sha256 baselines; green in this session's 439/0 suite | closed |
| T-03-11 | Repudiation | canonicalization correctness under u64 | high | mitigate | decoded-level differential + proptest (DENSE-03) | closed |
| T-03-12 | Information Disclosure | stale k-mer data after memory reduction | low | accept | overwrite semantics unchanged | closed (accepted) |
| T-03-13 | Tampering | 03-01 × 03-03 composition regression | high | mitigate | dense_merge_integration_tests decoded-level equality | closed |
| T-03-14 | Tampering | wave-2 gate regression (Phase 1/2) | high | mitigate | full cargo test gate — re-run this session: 439 passed / 0 failed | closed |
| T-03-15 | Tampering | invalid merge_mode string | medium | mitigate | PyValueError boundary validation; test_merge_rejects_bad_merge_mode executed this session (12/12) | closed |
| T-03-16 | Tampering | malformed max_memory string | low | mitigate | shared parse_memory_size grammar; UAT-verified live (graceful Err on absurd budgets, 03-UAT test 24) | closed |
| T-03-17 | Denial of Service | Python-triggered unbounded in-memory merge | high | mitigate | PyDatabase.merge routes through the bounded core; UAT-verified live (PyRuntimeError + no output, 03-UAT test 22) | closed |
| T-03-18 | Spoofing | path traversal via databases list | low | accept | existence validation + rkdb magic validation; local tool, user-supplied paths trusted | closed (accepted) |
| T-03-20 | Tampering | CounterTable::Dense arm of increment/get_count/merge | high | mitigate | debug_assert moved into the Dense arm with preserved message; should_panic test still matches | closed |
| T-03-21 | Tampering | stored_key_bytes / uses_dense_storage drift | medium | mitigate | both read the live CounterTable variant; measured ratio test guards re-widening | closed |
| T-03-23 | Denial of Service | per-key atomicity on both widths | medium | mitigate | single bump_entry! macro; PCOUNT-04 invariant preserved; overflow message unchanged | closed |
| T-03-24 | Tampering | KmerEntry::read_from count heuristic | critical | mitigate | heuristic deleted; plain u32::from_le_bytes; pinned by route-parity tests (5/5 green this session) | closed |
| T-03-25 | Repudiation | route-dependent output | high | mitigate | route-parity test asserts decoded maps AND designated counts with route proof | closed |
| T-03-26 | Denial of Service | StreamingMergeIterator refill error | medium | mitigate | pending_error propagation; no partial run beside an error | closed |
| T-03-27 | Tampering | merge_sorted_chunks first-entry read | medium | mitigate | match returning Err naming the chunk path | closed |
| T-03-28 | Tampering | get_all_counts dense widening | high | mitigate | hand-built byte reference + k32 high-bytes-zero assertions, RED-proven under mutation | closed |
| T-03-29 | Repudiation | golden_sha256 docstring overclaim | medium | mitigate | false claim deleted, honest scope documented | closed |
| T-03-30 | Tampering | golden manifest regeneration | medium | accept | manifest NOT regenerated; git status porcelain gate; Phase 1 D-10 forbids re-capture | closed (accepted) |
| T-03-31 | Denial of Service | routes materializing inputs | critical | mitigate | all three routes read 42-byte headers only; header-only assertion in routing tests | closed |
| T-03-32 | Tampering | crafted total_kmers header | medium | mitigate | saturating arithmetic (format.rs:939, verified); constants derived from live sizes | closed |
| T-03-33 | Elevation of Privilege | silent budget floor override | medium | mitigate | named 1 MB floor constant + log::info when raised (format.rs:18-29, verified — IN-01 fixed) | closed |
| T-03-34 | Tampering | fixed-name intermediate output collision | medium | mitigate | intermediate moved into the process-unique subdir; neither-location test | closed |
| T-03-35 | Denial of Service | merge_databases(&[], ..) panic | low | mitigate | empty-input guard hoisted (format.rs:721/:988, verified) | closed |
| T-03-37 | Tampering | placeholder-then-seek-back streaming header | critical | mitigate | field-for-field from_kmer_pairs header parity incl. file_size:0; byte-identical entry-point comparison | closed |
| T-03-38 | Denial of Service | streaming merge peak scales with dataset | critical | mitigate | entry-by-entry consumption, no intermediate collection; chunk-bounded peak — UAT-verified with real RSS measurements to 200M records (03-UAT test 19) | closed |
| T-03-39 | Repudiation | divergent route resolution between entry points | high | mitigate | single resolve_merge_route shared by both entry points | closed |
| T-03-40 | Tampering | truncated output reported as success | medium | mitigate | File::create + flush + re-seek + re-header + sync_all (format.rs:1544, verified); mid-stream errors propagate | closed |
| T-03-42 | Tampering | partial bucket output silently concatenated | critical | mitigate | error_count > 0 returns Err (WR-04); shards preserved and logged | closed |
| T-03-43 | Repudiation | failed-bucket recovery path | high | mitigate | should_remove_shards(Err)=false; shards survive for recovery | closed |
| T-03-44 | Tampering | tautological integrity accounting | high | mitigate | writer-emitted AtomicU64 + declared-vs-seen BTreeSet, observed RED under perturbation — code re-read this session (prefix_cache_merge.rs:1307-1335) | closed |
| T-03-45 | Denial of Service | read_to_end on largest bucket | high | mitigate | fixed RECORD_SIZE×100_000 blocks (WR-08) — code re-read this session | closed |
| T-03-46 | Tampering | sweep file branch deleting live chunks | medium | mitigate | TTL-gated selection; symlink refusal via file_type; one-year-TTL control test | closed |
| T-03-47 | Denial of Service | loose rustkmer_sort_*.chunk leak | medium | mitigate | sweep reclaims stale loose chunks — live-verified this session (chunk branch in temp_lifecycle.rs:164-221) | closed |
| T-03-48 | Tampering | cross-input validation gap on non-prefix routes | high | mitigate | merge_prologue header-only k/canonical validation as the shared first statement of both entry points | closed |
| T-03-49 | Tampering | prefix-cache mixed-canonical output header | medium | accept | capability deliberately preserved; residual recorded (WR-04 disposition ledger, developer triage) | closed (accepted) |
| T-03-50 | Tampering | batch-read byte conservation | critical | mitigate | record-aligned reads with carried tail; oracle-equality conservation tests >4 MB, RED-proven | closed |
| T-03-51 | Denial of Service | front-end validation materializing inputs | high | mitigate | validate_merge_compatibility reads headers only; comment-filtered from_file_path count 0 (re-verified this session) | closed |
| T-03-52 | Tampering | sorted flag truthfulness | high | mitigate | high-byte bucketing makes index-order concatenation ascending by construction; e2e order+query tests | closed |
| T-03-53 | Tampering | raw-write under canonical bucketing | high | mitigate | canonicalized processed_kmer stored (bucket key == stored key); RED-proven e2e (CR-01 closed) | closed |
| T-03-54 | Tampering | swallowed canonicalization error | medium | mitigate | Err propagated via ?; loud abort instead of corrupt placement | closed |
| T-03-55 | Repudiation | false capability-guard comment | low | mitigate | comment corrected; ANY-input semantics pinned by reversed-order assertion | closed |
| T-03-56 | Tampering | streaming writer on non-ascending runs | high | mitigate | mixed-canonical override forces sorting writer + per-file descending-run refusal at both consumption sites (03-17); 12/12 unit + 3/3 e2e green this session | closed |
| T-03-57 | Denial of Service | override removes streaming footprint in one corner | medium | accept | silent corruption strictly worse; loudly logged; opt-in corner; per-bucket scope bounds exposure | closed (accepted) |
| T-03-58 | Repudiation | overclaiming writer comments | low | mitigate | both rewritten to the real contract; negative greps gate | closed |
| T-03-SC | Tampering (supply chain) | tempfile promotion / cargo installs | high | mitigate | tempfile passed the package-legitimacy gate (OK verdict); all other plans introduced zero new dependencies | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-1 | T-03-03 | Reject-path error verbosity includes byte counts, not sensitive data; local CLI with user-supplied budget | Phase 03 plan 03-01 | 2026-10-06 |
| AR-03-2 | T-03-07 | Sweep prefix is rustkmer-specific; 7-day TTL protects in-flight merges; another tool using the exact prefix is out of scope | Phase 03 plan 03-02 | 2026-10-07 |
| AR-03-3 | T-03-12 | Memory-width change does not alter retention semantics; no stale-data vector | Phase 03 plan 03-03 | 2026-10-07 |
| AR-03-4 | T-03-18 | Local tool; user-supplied paths are trusted input; existence + magic validation already present | Phase 03 plan 03-05 | 2026-10-07 |
| AR-03-5 | T-03-30 | Golden manifest must not be regenerated (only ground truth); porcelain gate enforces | Phase 03 plan 03-08 | 2026-10-07 |
| AR-03-6 | T-03-49 | Prefix-cache mixed-canonical capability preserved deliberately; fixing WR-04 changes merge outcomes for existing callers — developer-triaged residual | Phase 03 plan 03-12 | 2026-10-07 |
| AR-03-7 | T-03-57 | Mixed-canonical override trades the streaming footprint in one opt-in corner against silent corruption; loudly logged, per-bucket bounded | Phase 03 plan 03-17 | 2026-10-09 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-09 | 51 | 51 | 0 | Claude (gsd-verify-work delegated tester, L1 grep-depth + full-suite re-run 439/0 + live CLI/Python/RSS probes) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-09
