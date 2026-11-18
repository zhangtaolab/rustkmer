# Roadmap: rustkmer

## Milestones

- ✅ **v1.0 Performance** — Phases 1-4 (shipped 2026-10-20)
- ✅ **v2.0 k=21 Counting Parity** — Phases 5-10 (shipped 2026-11-14; v2.0's conditional Phase 11 not triggered)
- ✅ **v2.1 Merge Verdict & Producer Research** — Phases 11-13 executed; Phase 14 NOT EXECUTED (D3 NO-GO) (shipped 2026-11-18)

## Phases

<details>
<summary>✅ v1.0 Performance (Phases 1-4) — SHIPPED 2026-10-20</summary>

- [x] Phase 1: Foundation & Quality (4/4 plans) — completed 2026-07-01
- [x] Phase 2: Parallel Counting (5/5 plans) — completed 2026-07-01
- [x] Phase 3: Memory Safety (17/17 plans) — completed 2026-10-09
- [x] Phase 4: Benchmark & Validation (5/5 plans) — completed 2026-10-18

Full detail: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) · Summary: [MILESTONES.md](MILESTONES.md)

</details>

<details>
<summary>✅ v2.0 k=21 Counting Parity (Phases 5-10) — SHIPPED 2026-11-14</summary>

**Milestone Goal:** Match or beat Jellyfish2 on human-scale k=21 counting (and k=31 under fair, matched-hash comparison) on BOTH the CLI and Python surfaces, closing the BENCH-02 gap outright.

- [x] Phase 5: Measurement & Regression Harness (7/7 plans) — completed 2026-11-12
- [x] Phase 6: Parallelism Correctness & Hot Path (5/5 plans) — completed 2026-11-12
- [x] Phase 7: Shared Counting Engine (4/4 plans) — completed 2026-11-13
- [x] Phase 8: Output Pipeline & .rkdb v2 Parity (4/4 plans) — completed 2026-11-13
- [x] Phase 9: Python Parity (5/5 plans) — completed 2026-11-13
- [x] Phase 10: Benchmark Verdict (4/4 plans) — completed 2026-11-14
- [ ] Phase 11: Minimizer Partitioning & Memory Ceiling — **DEFERRED** (D3 not triggered 2026-11-14: Stage A hit parity on both k and both surfaces and peak memory was below jellyfish; MINIM-01..03 deferred — permanently descoped 2026-11-16)

**Outcome:** overall **YES** — k=21 CLI 144.69 s / Python 165.05 s vs jellyfish 194.85 / 197.95 s; k=31 CLI 147.08 s / Python 178.22 s vs jellyfish 1380.92 / 187.14 s; exact count parity; lower peak memory than jellyfish at both k; dev-host evidence only. BENCH-V2-01 (KMC3) descoped 2026-11-13.

Full detail: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) · Requirements: [milestones/v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md) · Audit: [milestones/v2.0-MILESTONE-AUDIT.md](milestones/v2.0-MILESTONE-AUDIT.md)

</details>

<details>
<summary>✅ v2.1 Merge Verdict & Producer Research (Phases 11-13 executed; Phase 14 NOT EXECUTED) — SHIPPED 2026-11-18</summary>

**Milestone Goal:** Decide where the next performance investment goes — benchmark `rustkmer merge` against `jellyfish merge` at full scale for a measured invest/no-invest verdict (wall time is the primary decision axis; jellyfish is the sole comparator), research the producer-bound counting bottleneck (parallel extraction) with predicted-win sizing and a conditional implementation phase (v2.0 D3 pattern), close v2.0 carry-forward hygiene gaps, and hold the memory-below-jellyfish guardrail (k=21 43.97 GiB / k=31 68.52 GiB references).

- [x] Phase 11: Merge Characterization & Harness Prep (8/8 plans) — completed 2026-11-17
- [x] Phase 12: Full-Scale Merge Verdict (4/4 plans) — completed 2026-11-17
- [x] Phase 13: Producer Attribution Research (3/3 plans) — completed 2026-11-17
- [ ] Phase 14: Parallel Extraction — **NOT EXECUTED** (D3 NO-GO recorded 2026-11-17: derated predicted win 9.62% at k=21 / 10.80% at k=31 vs the pre-registered 10.0% both-k bar; PEXT-03/PEXT-04 remain unexecuted by recorded decision)

**Outcome:** merge verdict **NO-INVEST** — rustkmer merge medians 63.34 s (k=21) / 82.86 s (k=31) beat jellyfish merge 88.44 s / 114.70 s, three-way parity green at both k before any timed rep. Producer attribution measured at full scale: route-send dominant (91.80 / 92.99 s) over parse+extract (20.96 / 20.85 s) and inflate (26.25 / 21.02 s). D3 gate NO-GO. Hygiene debt closed (benchmark report rewritten from committed evidence; Nyquist 5-8; SECURITY 9-10; six-part dataset correction). No performance change landed; memory guardrail holds by status quo.

Full detail: [milestones/v2.1-ROADMAP.md](milestones/v2.1-ROADMAP.md) · Requirements: [milestones/v2.1-REQUIREMENTS.md](milestones/v2.1-REQUIREMENTS.md)

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Quality | v1.0 | 4/4 | Complete | 2026-07-01 |
| 2. Parallel Counting | v1.0 | 5/5 | Complete | 2026-07-01 |
| 3. Memory Safety | v1.0 | 17/17 | Complete | 2026-10-09 |
| 4. Benchmark & Validation | v1.0 | 5/5 | Complete | 2026-10-18 |
| 5. Measurement & Regression Harness | v2.0 | 7/7 | Complete | 2026-11-12 |
| 6. Parallelism Correctness & Hot Path | v2.0 | 5/5 | Complete | 2026-11-12 |
| 7. Shared Counting Engine | v2.0 | 4/4 | Complete | 2026-11-13 |
| 8. Output Pipeline & .rkdb v2 Parity | v2.0 | 4/4 | Complete | 2026-11-13 |
| 9. Python Parity | v2.0 | 5/5 | Complete | 2026-11-13 |
| 10. Benchmark Verdict | v2.0 | 4/4 | Complete | 2026-11-14 |
| 11. Merge Characterization & Harness Prep | v2.1 | 8/8 | Complete | 2026-11-17 |
| 12. Full-Scale Merge Verdict | v2.1 | 4/4 | Complete | 2026-11-17 |
| 13. Producer Attribution Research | v2.1 | 3/3 | Complete | 2026-11-17 |
| 14. Parallel Extraction | v2.1 | NOT EXECUTED | Not executed — D3 NO-GO (2026-11-17) | - |
## Backlog

### Phase 999.1: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (RESOLVED 2026-11-18)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [x] Test 22: pyo3 0.27 no longer auto-emits -undefined dynamic_lookup; pyo3/build.rs should call pyo3_build_config::add_extension_module_link_args() so the documented manual-build workaround links as-is again (this session injected it via RUSTFLAGS) (deferred 2026-10-09). Caveat: if this lands, pyo3-build-config must be re-added as a `[build-dependencies]` entry in `pyo3/Cargo.toml` (removed by quick 261111-sq1 because build.rs does not call it today).

**Resolution (2026-11-18, quick 261118-c2r, commit aaacda3):** `pyo3/build.rs` now calls `pyo3_build_config::add_extension_module_link_args()` unconditionally and `pyo3-build-config = "0.27.2"` is re-added as a `[build-dependencies]` entry (lockfile delta: one line). Proven end-to-end: `cargo build --manifest-path pyo3/Cargo.toml --features extension-module --locked` exits 0 with RUSTFLAGS/CARGO_ENCODED_RUSTFLAGS unset and the cdylib link carries `-C link-arg=-undefined -C link-arg=dynamic_lookup`; the pre-fix build failed with exit 101 (`_PyBaseObject_Type` undefined). The three documented RUSTFLAGS exports were replaced with the automatic-mechanism note.

### Phase 999.2: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (RESOLVED 2026-11-18)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [x] Test 22: dev-venv pitfall: a stale pyrustkmer 0.4.1 package directory in site-packages silently shadows a manually installed pyrustkmer.so extension (deferred 2026-10-09)

**Resolution (2026-11-18, quick 261118-d69):** the pitfall is documented in
`pyo3/README.md` under Installation: a `pyrustkmer/` package directory wins
import resolution over a same-named top-level extension file in the same
`sys.path` entry, so a hand-copied `pyrustkmer.so` is silently never loaded. The
section gives the detection commands (the `sysconfig` site-packages listing for
`pyrustkmer*` plus `pyrustkmer.__file__`) and the remediation (prefer
`maturin develop --release`; remove the shadowing package directory before
hand-installing the `.so`). `pyo3/tests/test_version.py` now also fails
structurally when a `pyrustkmer/__init__.py` package directory coexists with a
top-level `pyrustkmer` extension file on any import root, exercised against
synthetic `tmp_path` layouts plus the live interpreter. Observed result:
`pytest pyo3/tests/test_version.py` reports 7 passed on 2026-11-18 in the
healthy 0.5.0 layout.

### Phase 999.3: Follow-up — Phase 03 deferred UAT follow-up: Test 21 (RESOLVED 2026-11-18)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [x] Test 21: deferred-items.md's claim that loose *.chunk files are never swept is stale — temp_lifecycle.rs now sweeps them (CHUNK_FILE_PREFIXES); update the record (deferred 2026-10-09)

**Resolution (2026-11-18, quick 261118-csg):** the Phase 03 deferred-items entry no longer makes the stale claim; it records the gap in past tense and carries a dated Resolved paragraph. The sweep-coverage gap was closed by plan 03-11 (commit `83a6ac2`, 2026-10-08): `sweep_stale_merge_dirs` selects loose chunk files via `CHUNK_FILE_PREFIXES` + `CHUNK_FILE_SUFFIX` under the same TTL and symlink refusal as the directory branch, pinned by `tests/merge_cleanup_tests.rs::sweep_reclaims_stale_loose_chunk_files` (re-run 2026-11-18: 1 passed, 0 failed).

*999.1-999.3 were tracked opportunistically under HYG-04 (Phase 11) and all resolved 2026-11-18 (999.1 quick 261118-c2r; 999.2 quick 261118-d69; 999.3 quick 261118-csg) — not gate-blocking.*

### v2.0 carry-forward (from the milestone audit, 2026-11-14 — status updated 2026-11-16)

- Phase 5/6/7/8 Nyquist coverage → **PROMOTED** to v2.1 requirement HYG-02 (Phase 11)
- `SECURITY.md` absent for Phases 9 and 10 → **PROMOTED** to v2.1 requirement HYG-03 (Phase 11); the 8 Info findings in `09-REVIEW.md` were **RESOLVED** 2026-11-18 by quick 261118-fsk (commit `fcbe3d2`; 7 Fixed, 1 Accepted)
- `cargo fmt --all --check` drift → **RESOLVED** by quick 261116-ks7 (commit ee742dc)
- Benchmark harness WARNING-1 (CLI stage does not structurally consume the slice gate) and WARNING-2 (README pool-size formula drift) → opportunistic when `scripts/bench/` is touched (Phase 11 does touch it)
- MINIM-01..03 (minimizer partitioning / memory ceiling) → **PERMANENTLY DESCOPED** (user decision 2026-11-16: the memory bar is "below jellyfish", already met at both k; KMC-class RAM is not a goal)

### Deferred to v2.2+ (post-verdict; from REQUIREMENTS.md)

- **MBF-01**: rustkmer merge flag tuning / config sweep — only if the Phase 12 verdict says INVEST
- **MBF-02**: N-way merge scaling and r1+r2 input variants — post-verdict
- **PEXT-05**: extractor topology refinements beyond the first landed design — post-verdict
