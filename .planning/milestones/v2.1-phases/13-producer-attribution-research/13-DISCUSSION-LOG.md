# Phase 13: Producer Attribution Research - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-17 (initial pass); updated 2026-11-17 (second `--auto` pass)
**Phase:** 13-Producer Attribution Research
**Areas discussed:** Measurement vehicle, D3 gate memo, Full-scale input sources, Session scale & input lifecycle; then D3 bar pre-registration, Decision surface scope, Decompression scope, Arm A/B workload shape, Attribution table composition, Fresh-base branch handling

---

## Initial Pass (2026-11-17)

`--auto` mode: all 4 gray areas auto-selected.

---

## Measurement vehicle

### Q1: How are arms A-D driven?

| Option | Description | Selected |
|--------|-------------|----------|
| Harness driver script (recommended) | merge_characterize.py pattern — stdlib-only, provenance per run, evidence JSON per arm-k, fail-loud | ✓ |
| Hand-run CLI invocations | No new code but provenance transcription is error-prone | |
| Rust-side instrumentation | Violates measurement-only/no-code-changes constraint | |

**User's choice:** Harness driver script (auto-selected recommended)
**Notes:** `--features profiling` sub-timers are arm C's cross-check, not the headline source (plain-vs-gzip differential + pure-read control).

---

## D3 gate memo

### Q1: Where does the go/no-go decision live?

| Option | Description | Selected |
|--------|-------------|----------|
| Committed phase-dir memo (recommended) | 13-GATE-MEMO.md + 13-ATTRIBUTION.json; ROADMAP §Phase 14 annotated with the conditional pointer | ✓ |
| REQUIREMENTS.md annotation only | No derivation evidence attached | |
| STATE.md only | Not durable across sessions | |

**User's choice:** Committed phase-dir memo (auto-selected recommended)
**Notes:** Reversibility: costly — the memo is Phase 14's gate input; NO-GO closes PEXT-03/04 by recorded decision.

---

## Full-scale input sources

### Q1: Cite v2.0 walls directly or re-measure?

| Option | Description | Selected |
|--------|-------------|----------|
| Fingerprint-gated reuse (recommended) | Compare current binary sha256 vs v2.0's recorded fingerprint; identical → cite 144.69/147.08 s (CLI) + 165.05/178.22 s (Python); differs → re-measure base walls fresh | ✓ |
| Always re-measure | Costs ~30 min extra; fresh attribution-consistent numbers | |
| Always cite v2.0 | Fingerprint drift risk — attribution math on a changed binary | |

**User's choice:** Fingerprint-gated reuse (auto-selected recommended)
**Notes:** PEXT-01 fingerprinted-builds requirement applies either way.

---

## Session scale & input lifecycle

### Q1: Reps and plain-input handling?

| Option | Description | Selected |
|--------|-------------|----------|
| 3 reps + dedicated plain dir, delete post-memo (recommended) | 4 arms × 2 k × 3 reps ≈ 24 runs ≈ 1.5-2 h; ~60 GB plain inputs outside repo, provenance-recorded, deleted after memo | ✓ |
| More reps (5) | Tighter spread, +1 h for ratio measurements of diminishing value | |
| Keep plain inputs | Holds ~60 GB for no purpose after the memo cites recorded evidence | |

**User's choice:** 3 reps + decompress-once + post-memo deletion (auto-selected recommended)
**Notes:** Disk check before decompression; ~450 GiB free post-12-03 cleanup.

---

## Update Pass (2026-11-17, `--auto`)

Context already existed and 3 plans had been created. Per `--auto` mode: auto-selected
"Update it" and "Continue and replan after". The research Open Questions 1-4 and the
plan-time pre-registrations were the gray areas still open; each was auto-resolved to its
recommended option and folded into CONTEXT.md as D-05..D-10.

---

## D3 bar pre-registration

### Q1: What numeric bar should the D3 gate apply, and at which k?

| Option | Description | Selected |
|--------|-------------|----------|
| 10.0% derated, ≥ semantics, both-k conjunction (recommended) | Predicted full-wall improvement ≥ 10.0% on the conservative (E=0.5 at 16 extractor threads) model; either k below the bar is NO-GO; bar fixed before measurement | ✓ |
| 5.0% derated, either-k | More permissive; more likely GO | |
| 15.0% derated, both-k | More conservative; risks NO-GO despite a real win | |
| Qualitative bar, no numeric threshold | Pre-registration discipline lost; gate credibility weakens | |

**User's choice:** 10.0% derated, ≥, both-k (auto-selected recommended)
**Notes:** The bar, E=0.5, and 16 extractor threads are pre-registered constants asserted in unit tests; the idealized E=M bound is reported but never used for the bar. Bar changes after measurement would invalidate pre-registration.

---

## Decision surface scope

### Q1: Does the predicted-win / gate cover the CLI count wall only, or both surfaces?

| Option | Description | Selected |
|--------|-------------|----------|
| CLI-only decision + Python context with caveat (recommended) | CLI wall is the primary decision axis; Python walls (165.05/178.22 s) cited as context with module fingerprint + binary-fingerprint caveat | ✓ |
| Re-measure both surfaces and gate on the worse one | Doubles session cost; Python shares the engine | |
| CLI-only decision, omit Python entirely | Loses relevant context for Phase 14 | |

**User's choice:** CLI-only decision surface (auto-selected recommended)
**Notes:** The memo's headline is not dual-surface; adding Python later is a new measurement, not a re-decision.

---

## Decompression scope

### Q1: Decompress only the pinned pair (~17-19.5 GB) or all six parts (~52-60 GB)?

| Option | Description | Selected |
|--------|-------------|----------|
| All six parts: pair gates, four extras feed excluded context matrix (recommended) | Per-part spread recorded for Phase-14 sizing; `context=true`/`excluded=true` keeps it out of gate math | ✓ |
| Pinned pair only | Cheaper; loses per-part spread context | |
| Pinned pair only, no context matrix | Cheapest; explicitly drops the ×6 topology context | |

**User's choice:** All six parts with excluded context matrix (auto-selected recommended)
**Notes:** Deletion-after-memo applies either way; disk ~450 GiB supports ~60 GB plain inputs.

---

## Arm A/B workload shape

### Q1: Should stock arms A/B write a `.rkdb` output or run output-less?

| Option | Description | Selected |
|--------|-------------|----------|
| Write `-o` to scratch, delete per rep (recommended) | Fresh base measures the same workload as v2.0 walls (which included sort+write) | ✓ |
| Output-less runs | Not comparable to v2.0; distorts the base | |
| Both as separate arms | Extra runs for a comparability question already answered by v2.0's flags | |

**User's choice:** `-o` to scratch, per-rep deletion (auto-selected recommended)
**Notes:** Temp-lifecycle discipline; stats recorded before deletion.

---

## Attribution table composition

### Q1: Should the attribution table name the count-phase output stage and the read-delta correction?

| Option | Description | Selected |
|--------|-------------|----------|
| Producer stages + `output_stage_s` + delta correction (recommended) | Names inflate/parse/extract/route-send + output stage; records raw A−B delta and read_gz − read_plain with signs unclamped | ✓ |
| Producer stages only | Omits the composition split; predicted full wall would miss sort+write | |
| Producer stages + output as a footnote | Loses the explicit arithmetic term in the model | |

**User's choice:** Include `output_stage_s` + delta correction (auto-selected recommended)
**Notes:** `predicted_full_wall = max(parallelizable floor, worker floor) + output_stage_s`; zero/negative corrected inflate recorded as measured, never clamped.

---

## Fresh-base branch handling

### Q1: Given the current release binary fingerprint differs from v2.0, how is the base handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Re-measure fresh base; v2.0 cited only as corroboration (recommended) | Current sha256 `4539b893…` ≠ v2.0 `8f38d20c…`; arm A's own medians are the only decision denominator | ✓ |
| Use v2.0 walls as base with caveat | Attribution math on a changed binary; violates D-03 | |
| Block the phase until the binary matches | Unnecessary — the fingerprint gate exists precisely for this | |

**User's choice:** `re-measure` branch (auto-selected recommended)
**Notes:** Binary rebuilt clean from HEAD with `git_dirty: false` asserted; no memo percentage may use a v2.0 wall as denominator while the mismatch stands.

---

## Claude's Discretion

- Driver script CLI shape/name; evidence-JSON schema (merge_characterize + phase11 patterns)
- Arm C sub-timer invocation details; probe materialization (k=31 variant, null consumer) in /tmp scratch with `refuse_repo_root`
- Memo structure within the deterministic-render contract
- Cooldown/thermal/incremental-write mechanics

## Deferred Ideas

- zlib-rs switch — only if inflate measured ≥ ~20% of producer wall (Phase 14 planning)
- Per-part attribution as a headline — resolved as excluded context only (D-07)
- Producer-per-file parallel topology — Phase 14 territory if GO

## (auto mode record)

- Initial pass: 4 areas, 4 questions, all recommended options, no AskUserQuestion.
- Update pass: 6 areas, 6 questions, all recommended options, no AskUserQuestion; single pass per the auto-mode cap.
