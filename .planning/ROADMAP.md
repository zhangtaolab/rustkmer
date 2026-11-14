# Roadmap: rustkmer

## Milestones

- ✅ **v1.0 Performance** — Phases 1-4 (shipped 2026-10-20)
- ✅ **v2.0 k=21 Counting Parity** — Phases 5-10 (shipped 2026-11-14; Phase 11 conditional, not triggered)

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
- [ ] Phase 11: Minimizer Partitioning & Memory Ceiling — **DEFERRED** (D3 not triggered 2026-11-14: Stage A hit parity on both k and both surfaces and peak memory was below jellyfish; MINIM-01..03 deferred)

**Outcome:** overall **YES** — k=21 CLI 144.69 s / Python 165.05 s vs jellyfish 194.85 / 197.95 s; k=31 CLI 147.08 s / Python 178.22 s vs jellyfish 1380.92 / 187.14 s; exact count parity; lower peak memory than jellyfish at both k; dev-host evidence only. BENCH-V2-01 (KMC3) descoped 2026-11-13.

Full detail: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) · Requirements: [milestones/v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md) · Audit: [milestones/v2.0-MILESTONE-AUDIT.md](milestones/v2.0-MILESTONE-AUDIT.md)

</details>

## Backlog

### Phase 999.1: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 22: pyo3 0.27 no longer auto-emits -undefined dynamic_lookup; pyo3/build.rs should call pyo3_build_config::add_extension_module_link_args() so the documented manual-build workaround links as-is again (this session injected it via RUSTFLAGS) (deferred 2026-10-09)

### Phase 999.2: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 22: dev-venv pitfall: a stale pyrustkmer 0.4.1 package directory in site-packages silently shadows a manually installed pyrustkmer.so extension (deferred 2026-10-09)

### Phase 999.3: Follow-up — Phase 03 deferred UAT follow-up: Test 21 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 21: deferred-items.md's claim that loose *.chunk files are never swept is stale — temp_lifecycle.rs now sweeps them (CHUNK_FILE_PREFIXES); update the record (deferred 2026-10-09)

### v2.0 carry-forward (from the milestone audit, 2026-11-14)

- Phase 5/6/7/8 Nyquist coverage TODO: run `/gsd-validate-phase <N>` (Phase 7's VALIDATION.md is still `draft`; Phases 5/6/8 have none)
- `cargo fmt --all --check` drift on files untouched by their phase (Phase 06/08 deferred items, acknowledged at v2.0 close)
- Phase 9: 8 Info review findings; SECURITY.md absent for Phases 9 and 10
- Benchmark harness: CLI stage does not structurally consume the slice gate (WARNING-1); README pool-size formula drift (WARNING-2)
- MINIM-01..03 (minimizer partitioning / memory ceiling) deferred from Phase 11 — revisit in a later milestone if a memory ceiling is wanted
