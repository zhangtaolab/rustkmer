# Phase 13: Producer Attribution Research - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-17
**Phase:** 13-Producer Attribution Research
**Areas discussed:** Measurement vehicle, D3 gate memo, Full-scale input sources, Session scale & input lifecycle

---

## Area Selection

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

## Claude's Discretion

- Driver script CLI shape/name; evidence-JSON schema (merge_characterize + phase11 patterns)
- Arm C sub-timer invocation details; arm D null-consumer construction
- Memo structure (both ceilings, arithmetic, citation table)
- Per-part attribution as context rows (×6 topology)

## Deferred Ideas

- zlib-rs switch — only if inflate measured ≥ ~20% of producer wall (ROADMAP Note)
- Per-part attribution as headline (vs context)
- Producer-per-file parallel topology — Phase 14 territory if GO

## (auto mode record)

- All questions auto-selected the recommended (first) option, single pass, no AskUserQuestion.
- Total: 4 areas, 4 questions, 0 user prompts.
