# Roadmap: rustkmer

## Milestones

- ✅ **v1.0 Performance** — Phases 1-4 (shipped 2026-10-20)

## Phases

<details>
<summary>✅ v1.0 Performance (Phases 1-4) — SHIPPED 2026-10-20</summary>

- [x] Phase 1: Foundation & Quality (4/4 plans) — completed 2026-07-01
- [x] Phase 2: Parallel Counting (5/5 plans) — completed 2026-07-01
- [x] Phase 3: Memory Safety (17/17 plans) — completed 2026-10-09
- [x] Phase 4: Benchmark & Validation (5/5 plans) — completed 2026-10-18

Full detail: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) · Summary: [MILESTONES.md](MILESTONES.md)

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
