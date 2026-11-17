# Phase 12 Wrap-Up Record (12-03)

**Plan:** 12-03 (wave 4, depends on 12-02) — the Phase-12 wrap-up executor of decisions D-03 and D-04
**Date:** 2026-11-17
**Decisions executed:** D-03 (artifact cleanup after evidence) and D-04 (single docs rewrite), per
`12-CONTEXT.md`; closes Phase-11 decisions D-02 (retention lifecycle) and D-05 (the docs-rewrite deferred item).

---

## 1. D-03 — merge-input artifact cleanup (strictly after evidence commits)

### Precondition asserted BEFORE any deletion (git-checked)

- All Phase-12 verdict evidence tracked and committed: `12-REVALIDATE.json`, `12-PARITY-K21.json`,
  `12-PARITY-K31.json`, `12-RESULTS-FULL-K21.json`, `12-RESULTS-FULL-K31.json`, `12-VERDICT.json`,
  `12-MERGE-REPORT.md`, `12-RENDER-PROOF.json` (each verified via `git ls-files --error-unmatch`).
- Task 1's D-04 docs rewrite commit landed first: `df81ba1` (`docs(12-03): rewrite benchmark report from
  Phase-12 merge-verdict evidence (D-04)`).
- Working tree clean in the phase dir and `docs/` (`git status --porcelain` empty) at deletion time.
- The forbidden ordering (deletion before evidence commits — research Pitfall 11) did not occur.

### Inventory recorded before deletion (manifest-matched, 8/8 exact)

Source of truth: `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/manifest.json`
(`stage: complete`). On-disk `stat` sizes matched the manifest's recorded `size_bytes` exactly for all 8
artifacts before deletion:

| Artifact | size_bytes (on-disk == manifest) |
|---|---|
| part_001.k21.rkdb | 13,292,834,822 |
| part_006.k21.rkdb | 13,294,483,202 |
| part_001.k31.rkdb | 16,641,359,442 |
| part_006.k31.rkdb | 16,642,703,542 |
| part_001.k21.jf | 6,646,418,886 |
| part_006.k21.jf | 6,647,243,076 |
| part_001.k31.jf | 9,984,817,368 |
| part_006.k31.jf | 9,985,623,828 |
| **Total** | **93,135,484,166 bytes = 86.74 GiB** |

The directory held exactly these 8 artifacts plus `manifest.json` — nothing else.

### Deletion executed

- Only the 8 artifact files were deleted, each by explicit path (no shell globbing, T-12-03);
  `manifest.json` was never touched.
- The session scratch dir `/Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch/` (already empty —
  the 12-02 parity/timed stages deleted their own transients) was removed with `rmdir`, which only succeeds
  on an empty directory.

### Disk freed (df samples, /System/Volumes/Data)

| Sample | Available (KiB) | When |
|---|---|---|
| before deletion | 357,158,896 | immediately before `rm` |
| after, sample 1 | 448,111,972 | immediately after `rm` |
| after, sample 2 (settled) | 448,110,416 | re-sample after the directory re-listing (delta vs sample 1 within ~1.5 MB — stable; no local APFS snapshots: `tmutil listlocalsnapshots` empty) |

- **Freed (measured):** 448,110,416 − 357,158,896 = 90,951,520 KiB ≈ **86.74 GiB** — matches the manifest
  total exactly (93,135,484,166 bytes = 86.74 GiB). No post-delete accounting lag remained (the Phase-11
  §6 lesson was applied: re-sample after settling; the reading stabilized within ~1.5 MB of churn).

### Retained / rebuild escape hatch (nothing one-way destroyed)

- **Retained:** `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/manifest.json` — schema v1
  `merge-input-manifest` carrying every artifact's sha256 + size_bytes + build command line, the per-k
  `hash_size_plan` (derived -s 1G / 2G with occupancy), the source fingerprints of the pinned
  part_001+part_006 pair, and binary provenance. The round-0 revalidation records
  (`12-REVALIDATE.json`, committed) document the consumed state at session time.
- **Rebuild path:** `python3 scripts/bench/prepare_inputs.py build` (~30–90 minutes) regenerates the 8
  artifacts from the pinned source pair and re-derives the -s plan; `prepare_inputs.py revalidate`
  re-checks any rebuilt set against the retained manifest records. The D-03 lifecycle decision is closed:
  keep-until-verdict (Phase-11 D-02) → verdict landed (12-02) → cleanup (this plan).

---

## 2. D-04 — docs/benchmark-report.md single rewrite

- The one-time rewrite of `docs/benchmark-report.md` was committed as `df81ba1`
  (`docs(12-03): rewrite benchmark report from Phase-12 merge-verdict evidence (D-04)`) BEFORE the D-03
  deletion ran — the commit-before-delete ordering is observable in git history.
- The rewritten doc: SUPERSEDED banner and all six stale CRR2044018 occurrences removed; dataset provenance
  corrected to CRR1936095, six single-member gzip parts (~2.79 GB each, ~16.7 GB total), pinned
  part_001+part_006 pair with source fingerprints; headline merge-verdict tables per k with the rule
  verbatim, decision NO-INVEST and exit code 0; parity evidence, per-arm methodology + rates,
  predicted-vs-measured with the ladder caveat verbatim, input fingerprints (now the Phase-12 artifact set),
  harness provenance; footer names the Phase-12 evidence JSONs as the regeneration source.
- Number discipline verified: every measurement decimal greppable in `12-MERGE-REPORT.md`; the only decimals
  outside it are the seven pinned context numbers (2.79 / 16.7 / 86.74 / 144.69 / 147.08 / 43.97 / 68.52),
  each traceable to committed provenance.

---

*Phase: 12-full-scale-merge-verdict — plan 12-03 wrap-up record*
