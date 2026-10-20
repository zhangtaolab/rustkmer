# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Performance

**Shipped:** 2026-10-20
**Phases:** 4 | **Plans:** 31 (of which 12 were Phase-3 gap-closure rounds) | **Sessions:** multi-session per phase (per-plan durations logged in archived STATE history)

### What Was Built
- CI merge gate (fmt / clippy `-D warnings` / test / pyo3 wheel build, 3-OS) + library hygiene: `log` facade, single-source `.rkdb` write, English-only strings (syn-enforced)
- Lock-free multi-core counting on both surfaces (DashMap + rayon, `--threads` chain, GIL release) with 1-vs-N golden-baseline differential proofs
- Bounded-memory merge (header-only admission control, streaming / prefix-cache routing, RAII temp lifecycle + TTL sweep, shared CLI/Python entry point) and dense u64 counting storage for k ≤ 32 (~0.52× bytes/entry, `.rkdb` v2 byte-identical)
- Reproducible benchmark harness + CI regression gate (25% wall / 15% RSS thresholds, per-platform committed baselines, full/slice/synthetic ladder) and the human-scale Jellyfish2 verdict: k=31 faster AND leaner; k=21 ~5x slower — honestly recorded and accepted as a known gap

### What Worked
- Golden-capture-first (D-10): committing pre-refactor baselines before every risky swap caught real drift (03-03's 2-character transcription error; PCOUNT-04's exact-count parity)
- Verification-driven gap closure: `03-VERIFICATION.md` gaps opened four closure rounds that fixed genuinely broken things (an endianness heuristic corrupting counts > 1M, a truncating streaming merge, an inverted density claim) — the verifier was worth the rounds
- Mutation-tested gates: proving a new test CAN fail (inject a defect, watch it go red, revert) turned several vacuous-green gates into real ones
- Honest measurement discipline: counterbalanced reps, per-rep cache_state recording, parity gates before timing, mechanically rendered reports — a measured NO (BENCH-02 k=21) was escalated and accepted rather than tuned away

### What Was Inefficient
- Phase 3 needed 17 plans (12 in gap-closure): several defects (endianness heuristic, strand-dropping iterator, silent partial merges) predated the phase and surfaced only once the streaming route became the default — earlier route-parity differentials would have caught them sooner
- Bookkeeping drift: REQUIREMENTS.md BENCH-02 was flipped `[x]` by a bookkeeping commit while the committed report said NO (W2) — the checkbox consumer trusted frontmatter over the evidence
- 46 commits sat unpushed for days; the windows-latest clippy leg never ran against 4 code commits until the close-day push (W1)
- Tooling format mismatches: 03-17-SUMMARY frontmatter unparseable YAML; legacy Phase 1/2 SUMMARYs lack `requirements-completed`, forcing manual cross-checks in the audit

### Patterns Established
- Observe, never re-derive: `stored_key_bytes()`/`uses_dense_storage()` read the LIVE variant; budget assertions derive from `estimate_total_kmers`, never hard-coded constants
- One door per fact: `read_header_of` is the only way merge routes learn input shape; `parse_memory_size` is shared by CLI and Python; the admission constant is computed once
- Route claims need route proofs: a "streaming route" test arm must prove the route itself (temp-dir probe), not just the output
- Per-item cfg gating over file-top allows (keeps `-D warnings` meaningful for platform-dead code)

### Key Lessons
1. Density lives on the table, not the key — an enum key pays max-variant size (32 B) whichever arm is populated; `CounterTable::Dense/Wide` is what actually halves memory
2. A GREEN gate that cannot fail reports nothing — mutation-test every verification gate once
3. Two sites computing the same quantity with two literals WILL drift — single-source constants and pair copies behaviorally (parse the echoed figures, don't compare comments)
4. Honest measurement beats a tuned verdict: BENCH-02's k=21 NO, escalated and accepted with v2 work staged, preserved more trust than a massaged YES would have
5. Push early: CI only gates what it can see; long unpushed tips accumulate unvalidated assumptions

### Cost Observations
- Model mix: not recorded this milestone (start tracking at v2)
- Sessions: Phases 1–2 completed 2026-07-01 in one day each; Phase 3 was the long tail (2026-10-07→10-09, 4 verification rounds); Phase 4 ran 2026-10-10→10-18 including a 3.2 h full-scale benchmark
- Notable: per-plan execution averaged ~17 min excluding benchmark wall-clock; verification rounds (not execution) dominated Phase 3 elapsed time

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | multi | 4 | GSD adopted on brownfield v0.5.0; verification-driven gap-closure loop established |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | full suite 439/0 green | not tracked | stdlib-only benchmark harness (no new runtime deps) |

### Top Lessons (Verified Across Milestones)

1. *(first milestone — candidates above; promote once v2 confirms)*
2. *(first milestone — candidates above; promote once v2 confirms)*
