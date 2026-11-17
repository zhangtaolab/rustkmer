# Phase 11: Merge Characterization & Harness Prep - Pattern Map

**Mapped:** 2026-11-16
**Files analyzed:** 19 (12 new, 7 modified)
**Analogs found:** 16 / 19 (3 have no in-repo code analog: parity-gate spec doc, VALIDATION/SECURITY records — format precedents exist but content is produced by named GSD workflows)

**Phase character:** Python-harness-only extension (`scripts/bench/`, stdlib-only by contract, `bench.py:25-26`). No Rust changes. Every protocol primitive already exists — the analogs below show HOW to extend them additively without breaking committed baselines.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/bench/prepare_inputs.py` (NEW) | service (artifact build + manifest stage) | batch (8 artifacts) + file-I/O | `scripts/bench/random_slice.py` + `bench.py` provisioning/provenance | role-match |
| `scripts/bench/merge_characterize.py` (NEW, or folded into controller) | service (2-point ladder: measure → slope) | batch + transform | `scripts/bench/phase10.py` (`run_rounds`) + `output_stage.py` (`rotation_schedule`) | role-match |
| `scripts/bench/phase11.py` (NEW, OPTIONAL per CONTEXT discretion) | controller (staged rehearsal) | event-driven staged flow | `scripts/bench/phase10.py` (exit codes, `invalid()`, staged docs) | exact |
| `scripts/bench/bench.py` (MODIFY) | harness core (arm specs, cmd builders, gates, disk floor, renderer) | request-response + batch protocol | itself — extension points below | exact |
| `scripts/bench/README.md` (MODIFY) | docs (new stage docs + WARNING-2 fix at :321) | — | itself (audits read it verbatim) | exact |
| `scripts/bench/tests/test_merge_arms.py` (NEW) | test (cmd shapes, ordering assertion, gates GREEN/RED) | unit | `scripts/bench/tests/test_merge_input.py`, `test_cmd_matrix.py` | exact |
| `scripts/bench/tests/test_prepare_inputs.py` (NEW) | test (manifest build/revalidate/tamper) | unit + integration | `test_merge_input.py` fixture pattern (`build_gz_fixture`) | exact |
| `scripts/bench/tests/test_disk_floor.py` (NEW) | test (derive/block/override/recheck) | unit | `test_merge_input.py` (pure-function + loud-error style) | role-match |
| `scripts/bench/tests/test_schema.py` (MODIFY — extend) | test (new arm names tolerated) | unit | itself | exact |
| `scripts/bench/tests/test_render_report.py` (MODIFY — extend) | test (merge-verdict rows, old-file byte-compat) | unit | itself + `test_phase10_verdict.py` literal-assertion style | exact |
| `docs/benchmark-report.md` (MODIFY — banner + dataset fix, HYG-01) | docs | — | no analog — generated-file contract governs (see its entry below) | none |
| `.planning/PROJECT.md` (MODIFY — dataset description :88/:96) | docs | — | itself (factual line fixes) | exact |
| `.planning/phases/11-merge-characterization-harness-prep/PARITY-GATE.md` (NEW) | spec doc | — | no code analog — content checklist fixed by MBENCH-02 (RESEARCH Pattern 2) | none |
| `.planning/milestones/v2.0-phases/05-measurement-regression-harness/05-VALIDATION.md` (NEW via workflow) | process record | — | `07-VALIDATION.md` frontmatter format | format-only |
| `.planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/06-VALIDATION.md` (NEW via workflow) | process record | — | same | format-only |
| `.planning/milestones/v2.0-phases/08-output-pipeline-rkdb-v2-parity/08-VALIDATION.md` (NEW via workflow) | process record | — | same | format-only |
| `.planning/milestones/v2.0-phases/07-shared-counting-engine/07-VALIDATION.md` (CONFIRM/complete — draft) | process record | — | itself (frontmatter `status: draft`, `wave_0_complete: false`) | exact |
| `.planning/milestones/v2.0-phases/09-python-parity/09-SECURITY.md` (NEW via workflow) | process record | — | `v1.0-phases/04-benchmark-validation/04-SECURITY.md` frontmatter format | format-only |
| `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-SECURITY.md` (NEW via workflow) | process record | — | same | format-only |

All analog paths verified git-tracked via `git ls-files` (2026-11-16). HYG-02/03 records are produced by `/gsd-validate-phase` and `/gsd-secure-phase` — never hand-rolled (CONTEXT discretion item); the format precedents below are for review, not authorship.

## Pattern Assignments

### `scripts/bench/bench.py` modifications (harness core, request-response + batch protocol)

The extension surface, in the order the milestone research pins:

#### 1. New command builders — copy the `jellyfish_count_cmd` / `build_merge_cmd` shape

**Analog:** `scripts/bench/bench.py`

**List-form command builder pattern** (lines 237-249, 283-286):
```python
def rustkmer_count_cmd(cfg, out, rustkmer=DEFAULT_RUSTKMER):
    """rustkmer count argv derived from one BenchmarkConfig (list form).

    Inputs pass via -i (num_args = 1.., per src/cli/args.rs) — NOT as
    positional arguments. List-form subprocess with no shell: paths cannot
    inject here, so metacharacter screening is scoped to the sh -c arm.
    """
    argv = [str(rustkmer), "count", "-k", str(cfg.k)]
    if cfg.canonical:
        argv.append("-C")
    argv += ["--threads", str(cfg.threads), "-o", str(out),
             "-i", *[str(p) for p in cfg.inputs]]
    return argv


def build_merge_cmd(rustkmer, out_db, input_dbs):
    """rustkmer merge command (list form)."""
    return [str(rustkmer), "merge", "-i", *[str(p) for p in input_dbs],
            "-o", str(out_db)]
```
Extension: `build_merge_cmd` gains a `num_threads=None` param (`argv += ["--num-threads", str(num_threads)]` when set) — the flag exists in `src/cli/args.rs` `Merge` variant (default `"0"` = all cores). `merge-t1` arm passes `num_threads=1`; `merge` arm passes nothing (defaults).

**Do NOT copy flag strings between jellyfish subcommands** — in `count`, `-m` is mer length; in `merge`, `-m` is MIN mode. New `jellyfish_merge_cmd` gets its own literal set, modeled on the `jellyfish_count_cmd` guard pattern (lines 252-280):
```python
    if not HASH_SIZE_RE.match(str(cfg.hash_size)):
        raise ValueError(f"hash_size rejected (unsafe characters): "
                         f"{cfg.hash_size!r}")
    ...
    if any(p.endswith(".gz") for p in inputs):
        pipeline = (f"{cfg.decompressor} {' '.join(inputs)} | "
                    f"jellyfish count {' '.join(common)} /dev/stdin")
        return ["sh", "-c", pipeline]
    return ["jellyfish", "count", *common, *inputs]
```
`jellyfish merge` inputs are `.jf` files (never `.gz`) → list form only, no `sh -c`, but still run `validate_path` on every path (T-04-03 consistency, lines 222-234).

#### 2. Arm specs + ordering — extend the spec-dict list; assert count-before-merge

**Analog:** `bench.py` lines 1420-1432 (arm_specs) and 1308-1325 (warmup/order coupling the assertion must protect):
```python
        arm_specs = [
            {"name": "count-A", "tool": "rustkmer", "out": db_a,
             "cmd": rustkmer_count_cmd(cfg_a, db_a, args.rustkmer)},
            {"name": "count-B", "tool": "rustkmer", "out": db_b,
             "cmd": rustkmer_count_cmd(cfg_b, db_b, args.rustkmer)},
            {"name": "jellyfish-count-A", "tool": "jellyfish", "out": jf_a,
             "cmd": jellyfish_count_cmd(cfg_a, jf_a)},
        ]
        if not args.skip_merge:
            arm_specs.append(
                {"name": "merge", "tool": "rustkmer", "out": db_merged,
                 "cmd": build_merge_cmd(args.rustkmer, db_merged,
                                        [db_a, db_b])})
```
Ordering facts that make the new assertion load-bearing (lines 1308-1312, 1316-1317):
```python
    # One warmup run per tool, executed and discarded before round 1.
    for tool in tools:
        spec = next(s for s in arm_specs if s["tool"] == tool)
        measure(spec["cmd"])
        cooldown_gap()
    ...
        for tool in schedule[str(rnd)]:
            for spec in [s for s in arm_specs if s["tool"] == tool]:
```
The warmup executes the FIRST spec of each tool and same-tool arms run in spec order — so the new arms must be appended as: `jellyfish-count-A`, `jellyfish-count-B`, `jellyfish-merge` (within jellyfish); `count-A`, `count-B`, `merge`, `merge-t1` (within rustkmer). Add an explicit ordering assertion + unit test before wiring.

#### 3. Parity gates — mirror the existing count-parity and conservation shapes

**Count-parity gate** (lines 1436-1449) — the shape the three-way merge gate mirrors:
```python
        by_name = {a["name"]: a for a in arms}
        if (by_name["jellyfish-count-A"]["distinct_kmers"]
                != by_name["count-A"]["distinct_kmers"]
                or by_name["jellyfish-count-A"]["total_kmers"]
                != by_name["count-A"]["total_kmers"]):
            raise RuntimeError(
                f"parity failed on the measured input: jellyfish "
                f"distinct={...} total={...} vs rustkmer unique={...} "
                f"total={...} — methodology finding (Pitfall 10), not a "
                f"comparable measurement")
```
**Merge-conservation shape** (lines 1479-1496, self-check):
```python
        merged_total = (by_name["count-A"]["total_kmers"]
                        + by_name["count-B"]["total_kmers"])
        if "merge" in by_name:
            if by_name["merge"]["total_kmers"] != merged_total:
                raise RuntimeError(
                    f"self-check: merged total_kmers "
                    f"{by_name['merge']['total_kmers']} != sum of inputs "
                    f"{merged_total} (count conservation)")
            if by_name["merge"]["distinct_kmers"] < max(
                    by_name["count-A"]["distinct_kmers"],
                    by_name["count-B"]["distinct_kmers"]):
                raise RuntimeError(...)
```
New merge-parity block extends this with: `merge.total == jellyfish-merge.total == Σ inputs`; `merge.distinct == jellyfish-merge.distinct` (union semantics); all Total values read from the stats-JSON **sum-of-counts** definition — the `stats()` reader (lines 289-301) is the only sanctioned source:
```python
def stats(db_path, rustkmer):
    """Return the parsed `rustkmer stats -f json` dict for db_path.

    Reads the snake_case serde keys (unique_kmers / total_kmers) — never the
    text-format prose labels.
    """
    proc = subprocess.run([str(rustkmer), "stats", "-f", "json", str(db_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(...)
    return json.loads(proc.stdout)
```

#### 4. Single-rep CI path (MBENCH-05) — extend, never fork the schema

**Analog:** `bench.py` lines 1450-1464 (rustkmer-only arms already include merge without jellyfish) and `validate_schema` lines 422-452 (name-tolerant):
```python
    else:
        # Single-rep run (CI path): rustkmer-only arms, no jellyfish needed.
        arms = [
            measure_arm("count-A", ...),
            measure_arm("count-B", ...),
        ]
        if not args.skip_merge:
            arms.append(measure_arm(
                "merge",
                build_merge_cmd(args.rustkmer, db_merged, [db_a, db_b]),
                args.reps, args.rustkmer, db_merged))
```
`validate_schema` (lines 440-445) checks only `"name"` + non-empty `reps` per arm — new arm names ride through untouched. `SCHEMA_VERSION = 1` stays (line 44).

#### 5. Disk pre-flight — extend `check_disk_floor` per D-10/11/12

**Analog:** `bench.py` lines 1263-1277 + constant 61-64:
```python
DEFAULT_DISK_FLOOR_GB = 150    # Pitfall 8: full-run .rkdb artifacts alone can
                               # reach 55-60 GB per database + merge scratch
CV_WARNING_THRESHOLD_PCT = 10.0
DISK_FLOOR_EXIT = 3
...
def check_disk_floor(directory, floor_gb):
    """Abort with exit 3 before any mode=full measurement when free space on
    the output directory's volume is below the floor ..."""
    st = os.statvfs(str(directory))
    free_bytes = st.f_bavail * st.f_frsize
    required_bytes = int(floor_gb * (1 << 30))
    if free_bytes < required_bytes:
        print(f"bench.py: disk guardrail: {free_bytes} bytes free on "
              f"{directory} but the configured floor is {required_bytes} "
              f"bytes ({floor_gb} GiB) — aborting before any measurement "
              f"(exit {DISK_FLOOR_EXIT})", file=sys.stderr)
        sys.exit(DISK_FLOOR_EXIT)
    return free_bytes
```
Extensions: replace the 150 default with the derived value ONLY after prepare + ladder measurements exist (D-10 sequencing — Pitfall 4); add `--disk-floor-override` (D-11: print shortfall + explicit opt-in, never silent-continue); add a lightweight per-rep re-check reusing this same primitive (D-12). Note current guard fires only in `mode == "full"` (lines 1379-1382) — decide whether the rehearsal's slice runs get a scaled floor.

#### 6. Renderer — conditional merge handling, never a rewrite

**Analog:** `bench.py` lines 1623-1641:
```python
def _arm_row(arm, base_arm):
    """One table row: medians, deltas vs the jellyfish baseline arm, raw reps."""
    wall, rss = arm["median_wall_s"], arm["median_peak_rss_bytes"]
    if arm["name"] == "merge":
        # No jellyfish counterpart exists for the merge operation — a delta
        # against the jellyfish COUNT arm would be semantically void.
        d_wall = d_rss = "n/a"
```
The `n/a` special case is load-bearing for old results files — extend conditionally (when a `jellyfish-merge` arm exists in the same results file), don't remove.

**Renderer narrative debt** (lines 1883-1892 `halt_note`, 1942-1947 dataset-provenance block):
```python
        "## Dataset provenance",
        "",
        "**CRR2044018 is the user-approved substitute for CRR1936095** "
        "(CRR1936095 was absent from this host's disk; the substitution was "
        "approved 2026-10-09). ...",
```
The banner (D-05) is a deliberate supersede marker; any future re-render drops it, and these hardcoded v1.0 strings resurrect stale claims. Record as post-verdict debt (research Open Question 4) unless the planner scopes the minimal narrative fix.

---

### `scripts/bench/prepare_inputs.py` (NEW — service, batch + file-I/O)

**Primary analog:** `scripts/bench/random_slice.py` — the in-repo template for a standalone stage that builds artifacts AND records a manifest bound by fingerprints.

**Stage skeleton + manifest-recording pattern** (`random_slice.py` lines 25-58, 116-128):
```python
def reservoir_slice(gz_path, n_reads, seed, out_path, manifest_path):
    """Write a seeded random-record FASTQ slice and its selection manifest.

    Args: ...
    Raises:
        ValueError: If arguments, paths, or FASTQ record framing are invalid.
        RuntimeError: If decompression fails or the source has no records.
    """
    if isinstance(n_reads, bool) or not isinstance(n_reads, int) or n_reads < 1:
        raise ValueError(f"n_reads must be a positive integer, got {n_reads!r}")
    ...
    source = Path(validate_path(gz_path))
    if not source.is_file():
        raise ValueError(f"input not found or not a file: {source}")
    source_fingerprint = fingerprint(source)
    ...
    manifest = {
        "source": source_fingerprint,
        "seed": seed,
        "requested_reads": n_reads,
        "selected_reads": len(selected),
        "selected_indices": [index for index, _ in selected],
        "output_sha256": output_hash.hexdigest(),
        "record_lines": 4,
    }
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return manifest
```
Reuse verbatim from `bench.py`: `fingerprint()` (lines 304-312), `stats()` (289-301), `parse_jellyfish_stats` (712-719, fail-loud on missing lines), `binary_provenance()` (345+, `PROVENANCE_KEYS` at 322-323), `rustkmer_count_cmd` / `jellyfish_count_cmd` builders. The manifest record shape is fixed by RESEARCH Pattern 1 (schema_version 1, kind `merge-input-manifest`, per-artifact `{path, size_bytes, sha256, command_line, k, canonical, hash_size, distinct, total}`, `source_fingerprints`, `provenance`) — field shapes mirror `fingerprint()`/`PROVENANCE_KEYS` exactly so `validate_provenance` and Phase 12 tooling read them unchanged.

**Import-fixup pattern** for direct script execution (`random_slice.py` lines 18-22; `bench.py` `provision_random_slice` lines 631-637 shows the reverse direction):
```python
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import fingerprint, validate_path
```

**Build-order rule (from D-04 + research Pattern 1):** `.rkdb` first (produces first-ever per-part Distinct) → derive `-s` with occupancy assertion (≤ ~0.75 × slots) → `.jf` per k-pair with identical `-m/-s/-C` → `jellyfish info` recorded → manifest written. **Anti-pattern:** never default to `DEFAULT_HASH_SIZE = "10G"` for per-part artifacts (sized for union counts; hundreds of GiB).

**Out-of-repo guard (D-03/Pitfall 9):** `bench.py:49` `DEFAULT_SCRATCH = HERE / "scratch"` is inside the repo — the prepare stage must default to the data-adjacent dir and REFUSE an artifact root inside `REPO_ROOT`.

**Part-pair resolution** — copy from `phase10.py` lines 1999-2037:
```python
_SPLIT_PART_TOKENS = (".part_001", ".part_006")

def strip_compression_suffix(name):
    for suffix in _COMPRESSION_SUFFIXES:   # (".fastq.gz", ".fq.gz")
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return None

def require_split_parts(inputs):
    """Exactly part_001 then part_006, matched on the stripped stem."""
    paths = [Path(p) for p in inputs]
    if len(paths) != 2:
        raise ValueError(
            f"the full-scale/slice stages require exactly the two split "
            f"parts, got {len(paths)}: {[str(path) for path in paths]}")
    ...
    if not (stems[0].endswith(_SPLIT_PART_TOKENS[0])
            and stems[1].endswith(_SPLIT_PART_TOKENS[1])):
        raise ValueError(...)
    return paths
```
**Anti-pattern:** `gather_inputs` on the split dir (bench.py:481-497) sorts six parts and `provision_full` (667-674) takes the first two → part_001+part_002, silently wrong; `--merge-input` raises outside slice mode (529-547).

**Pre-gate anchors (verified committed values):** k=21 union Distinct 897,266,581 / Total 8,967,099,203; k=31 union Distinct 1,146,353,600 / Total 8,275,694,030 (`.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-full-k{21,31}.json`). Invariants: `p1.Total + p2.Total == union Total`; `merged.Distinct == union Distinct`; source fingerprints part_001 sha256 `dae91042…` (2,785,381,389 B) / part_006 sha256 `b197f16c…` (2,785,388,289 B).

---

### `scripts/bench/phase11.py` (NEW, OPTIONAL — controller, staged event-driven flow)

**Analog:** `scripts/bench/phase10.py` — exact template.

**Exit-code contract + loud-invalid pattern** (phase10.py lines 97-99, 178-182):
```python
EXIT_OK = 0
EXIT_NO = 1
EXIT_INVALID = 2
...
def invalid(message):
    """Print an input/infra problem and exit 2 — never a verdict."""
    print(f"phase10.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)
```

**Import block** (phase10.py lines 65-95) — imports protocol primitives from `scripts.bench.bench` by name (`measure`, `attempt_cache_purge`, `reduce_arm`, `check_disk_floor`, `fingerprint`, `binary_provenance`, `validate_schema`, `validate_provenance`, ...) plus `from scripts.bench.output_stage import rotation_schedule` (line 95).

**Fixed-location constants + pinned-token pattern** (phase10.py lines 131-141):
```python
DEFAULT_DATA_DIR = Path(
    "/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split")
...
PINNED_SOURCE_SHA256 = (
    "dae91042e42c1a0562a2bda66b7a3409665cddc87e702d99b922e44160c1b0de")
```
Phase 11 equivalent: artifacts root `CRR1936095-merge-inputs/` beside the data dir (D-03), manifest path constant.

**If deferred to Phase 12 instead:** drive staged `bench.py`/`prepare_inputs.py` invocations — CONTEXT leaves this open (research Open Question 3).

---

### `scripts/bench/merge_characterize.py` (NEW or folded — service, batch + transform)

**Analog:** `phase10.py` `run_rounds` (lines 346-452) — the reference implementation with injectable test seams:
```python
def run_rounds(specs, reps, cooldown_s, measure_fn=None, purge_fn=None,
               sleep_fn=None, on_rep=None, counts_fn=None):
    """Warmups + counterbalanced measured rounds; return {arm: [rep dicts]}.

    ...
    The injectable seams default to the module-level primitives at CALL time
    (not at definition time), so a test can patch `phase10.measure` /
    `phase10.attempt_cache_purge` / `time.sleep` and still drive the real
    stage entry points.
    """
    measure_fn = measure if measure_fn is None else measure_fn
    purge_fn = attempt_cache_purge if purge_fn is None else purge_fn
    sleep_fn = time.sleep if sleep_fn is None else sleep_fn
    ...
    schedule = rotation_schedule(names, reps)
```
**Per-arm rotation** (`output_stage.py` lines 121-137) — preferred over `bench.py` `round_schedule` (lines 1196-1205, tool-order-only alternation) for the 6-arm set:
```python
def rotation_schedule(arm_names, reps):
    """Pure counterbalanced round-robin schedule (unit-testable, no I/O).

    Round r (0-based) starts at arm index r mod len(arm_names); every round
    contains every arm exactly once. ...
    """
    names = list(arm_names)
    if not names:
        raise ValueError("rotation_schedule needs at least one arm name")
    if reps < 1:
        raise ValueError(f"rotation_schedule needs reps >= 1, got {reps}")
    n = len(names)
    return [[names[(r + i) % n] for i in range(n)] for r in range(reps)]
```
Ladder mechanics: 2 slice pairs (~10% / ~40% of part scale) via `random_slice.reservoir_slice` (seeded, manifest per slice) — one slice from part_001, one from part_006, same N and seed discipline; each side runs prepare → per-part counts → both merges. Record per rung: wall, output sizes, entry counts, `cache_state`, route attribution. Reduction reuses `reduce_arm` (bench.py lines 1239-1260, CV% threshold `CV_WARNING_THRESHOLD_PCT = 10.0`).

---

### `scripts/bench/tests/test_merge_arms.py` (NEW — test, unit)

**Analog:** `scripts/bench/tests/test_merge_input.py` (full read) — module docstring contract, gz fixture builder, loud-rejection assertions:
```python
"""Unit tests for the 04-04 milestone knobs: --merge-input and --skip-merge.

... Stdlib unittest only — the tiny .gz
fixtures are built with the system `gzip` CLI (same pattern as
test_degradation.py).
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.bench.bench import merge_input_for, provision_slice


def build_gz_fixture(directory, name, seq, n_reads=100):
    """Write a deterministic .fq.gz fixture with per-call sequence content."""
    lines = []
    for i in range(1, n_reads + 1):
        lines.append(f"@{name}{i:07d}\n")
        lines.append(seq + "\n")
        lines.append("+\n")
        lines.append("I" * len(seq) + "\n")
    plain = directory / f"{name}.fq"
    plain.write_text("".join(lines), newline="\n")
    subprocess.run(["gzip", "-k", "-f", str(plain)], check=True)
    return directory / f"{name}.fq.gz"
```
Class conventions: one class per function-under-test, docstring on class and every test method, `assertRaises(ValueError)` for loud-rejection cases, `tempfile.TemporaryDirectory()` + `addCleanup`. Same shape applies to `test_prepare_inputs.py` (add tamper-a-byte → revalidate-fails case) and `test_disk_floor.py` (pure-function derive + exit-code block + override). Extensions to `test_schema.py`/`test_render_report.py` follow each file's existing class layout; `test_phase10_verdict.py` shows the verbatim-literal assertion style if render tests need it.

---

### `docs/benchmark-report.md` banner (HYG-01, D-05) — docs, no code analog

**Governing contract:** the file footer (verified):
```
*Generated file — do not edit by hand. Regenerate with `python3
scripts/bench/bench.py --render-report --results <jsons> --out
docs/benchmark-report.md`; the evidence JSONs are committed beside this
report under `.planning/milestones/v1.0-phases/04-benchmark-validation/`.*
```
The banner is a deliberate, acknowledged exception to the do-not-edit contract (a supersede marker on a v1.0 artifact, pointing to `.planning/milestones/` v2.0 evidence) + the dataset correction (six single-member gzip parts ~16.7 GB, not "two parts ~5.2 GB"). Accept that a re-render drops it; the drift sweep (D-06) greps `420%|CRR2044018|5.2 GB` across `docs/`, `README.md`, `USER_GUIDE.md`, `PROJECT_SUMMARY.md`, `.planning/PROJECT.md` (:88, :96 verified stale) and fixes factual drift only. **Anti-pattern:** hand-editing without acknowledging the generator in the phase record.

---

### HYG-02 / HYG-03 records (format precedents — content produced by named workflows)

**VALIDATION.md frontmatter** (`07-VALIDATION.md`, verified):
```yaml
---
phase: "07"
slug: "shared-counting-engine"
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-11-12"
---
```
Structure: `## Test Infrastructure` table (Framework / Config file / Quick run command / Full suite command / Harness gates / Estimated runtime) → `## Sampling Rate`. Targets: `05-VALIDATION.md`, `06-VALIDATION.md`, `08-VALIDATION.md` (new); confirm `07` draft. All beside archived artifacts under `.planning/milestones/v2.0-phases/<dir>/` (inventory verified 2026-11-16: 05/06/08 have none; 09/10 have VALIDATION.md already). **Anti-pattern:** creating fresh `.planning/phases/05-…` dirs for archived phases (Pitfall 7).

**SECURITY.md frontmatter** (`v1.0-phases/04-benchmark-validation/04-SECURITY.md`, verified):
```yaml
---
phase: "04"
slug: benchmark-validation
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-20"
---
```
Structure: `## Trust Boundaries` table (Boundary / Description / Data Crossing) → `## Threat Register` table (Threat ID / Category / Component / Severity / Disposition / Mitigation / Status). Targets: `09-python-parity/09-SECURITY.md`, `10-benchmark-verdict/10-SECURITY.md` (no SECURITY.md exists anywhere — verified). Authored/verified by `/gsd-secure-phase`, not hand-written.

---

## Shared Patterns

### List-form subprocess + path screening (T-04-03)
**Source:** `bench.py:190-195, 222-234`
**Apply to:** every new command builder and subprocess invocation in `prepare_inputs.py`, `merge_characterize.py`, `phase11.py`
```python
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9./_-]+$")
...
def validate_path(path):
    """T-04-03 mitigation: screen a path before it enters any shell string. ..."""
    text = str(path)
    if not text:
        raise ValueError("path rejected (empty)")
    if not SAFE_PATH_RE.match(text):
        raise ValueError(f"path rejected (unsafe characters): {text!r}")
    return text
```
New `.jf`-based arms need no shell at all; only the existing gz-pipeline arm uses `sh -c`.

### Fail-loud subprocess stance
**Source:** `bench.py:173-186` (`measure`), `:328-342` (`_provenance_tool_output`), `:289-301` (`stats`)
**Apply to:** all new subprocess wrappers (jellyfish info parsing, dump comparators, manifest revalidation)
```python
    proc = subprocess.run(["/usr/bin/time", time_flag, *argv],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"measured command failed rc={proc.returncode}: {argv}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
```
A parse that tolerates a missing line lets a gate run against nothing (`parse_jellyfish_stats` docstring, `bench.py:712-719`). No error swallowing in new gates.

### Fingerprints + provenance reuse (D-04)
**Source:** `bench.py:304-312` (`fingerprint`), `:322-323` (`PROVENANCE_KEYS`), `:345-375` (`binary_provenance`)
**Apply to:** `prepare_inputs.py` manifest (verbatim shapes so Phase 12 round-0 revalidation reads one format), ladder evidence, rehearsal docs
```python
def fingerprint(path):
    """{'path', 'size_bytes', 'sha256'} for one input file (threat T-04-02)."""
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return {"path": str(p), "size_bytes": p.stat().st_size,
            "sha256": h.hexdigest()}
```
Golden baselines / pinned references are ground truth, never regenerated (`bench.py:684-695` comment block: "NEVER applied to a random sample; a changed dataset is a loud methodology finding, not a re-pin").

### Exit-code contracts
**Source:** `bench.py:64` (`DISK_FLOOR_EXIT = 3`), `:680-681` (parity 1 / jellyfish-missing 2), `phase10.py:97-99` (0/1/2)
**Apply to:** disk-floor hard block (D-11), any phase11 controller, CI degradation path

### Honest labels (cache_state)
**Source:** `bench.py:1208-1236` (`cache_state_from`, `attempt_cache_purge`)
**Apply to:** rehearsal + ladder reps — record the actual purge outcome, never claim cold
```python
    if in_ci:
        return "runner-fresh"
    if platform != "darwin":
        return "unavailable"
    return "purged" if purge_succeeded else "unavailable"
```

### No schema fork (SCHEMA_VERSION 1)
**Source:** `bench.py:44`, `validate_schema :422-452` (name-tolerant arm checks)
**Apply to:** MBENCH-05 CI rung + renderer extensions — old committed baselines stay loadable; `_arm_row`'s merge `n/a` branch (1623-1641) is load-bearing for old files.

### Stdlib-only unittest, discover-run
**Source:** `bench.py:25-26` (contract), `tests/test_merge_input.py` (style), `.github/workflows/benchmark.yml` (`python3 -m unittest discover -s scripts/bench/tests -t .`)
**Apply to:** all three new test modules; per-module run `... -k <module>`

### Known-flake awareness
**Source:** `.planning/STATE.md:74` (documented handling)
**Apply to:** any red in `test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` — purge stale `target/` artifacts before trusting it; ~50% macOS `sample`-race flake, pre-existing.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/phases/11-.../PARITY-GATE.md` | spec doc | — | No written gate-spec precedent exists in-repo; content checklist is fixed by MBENCH-02 (RESEARCH Pattern 2): pre-gate reconciliation, ground-truth leg, dump-vs-dump cross-tool leg (`rustkmer dump` vs `jellyfish dump -c`, strip `#`, `LC_ALL=C sort`, `cmp`), `total_kmers` definition named per check, canonicality assertion. Location/format = planner discretion. |
| `docs/benchmark-report.md` superseded banner | docs | — | First deliberate hand-edit of a generated file; governed by the footer's generator contract (documented above), not by a copyable pattern. |
| `05/06/08-VALIDATION.md`, `09/10-SECURITY.md` | process records | — | Format precedents exist (shown above) but content must be produced through `/gsd-validate-phase` and `/gsd-secure-phase`, which own their verification. |

## Metadata

**Analog search scope:** `scripts/bench/` (primary), `scripts/bench/tests/`, `src/cli/args.rs` + `src/cli/commands/dump.rs` + `src/database/format.rs` (Rust CLI surface, read-only references), `.planning/milestones/v1.0-phases/04-benchmark-validation/` and `.planning/milestones/v2.0-phases/` (hygiene record formats), `docs/`
**Files scanned:** ~30 (bench.py in 7 targeted ranges totaling ~1,100 lines; phase10.py in 3 ranges; random_slice.py, test_merge_input.py, output_stage.py + rotation section, both hygiene-format files, report footer — full/partial reads)
**Tracked-source gate:** all named analog paths verified via `git ls-files` (no gitignored mirrors referenced)
**Pattern extraction date:** 2026-11-16
