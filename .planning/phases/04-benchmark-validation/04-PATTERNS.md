# Phase 4: Benchmark & Validation - Pattern Map

**Mapped:** 2026-10-09
**Files analyzed:** 13 (new) + 2 deletions (optional, planner decision)
**Analogs found:** 9 / 11 creatable-file groups (several are partial matches — see No Analog Found)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/bench/bench.py` | utility (harness orchestrator) | batch (subprocess measurement) | `src/cli/commands/benchmark.rs` (schema mining only) + RESEARCH.md code examples | partial (role only; analog is dead code) |
| `scripts/bench/compare.py` | utility (gate comparator) | transform (JSON in → verdict out) | none in repo | none |
| `scripts/bench/gen_synthetic.py` | utility (data generator) | file-I/O (deterministic write) | `test_data/generate_test_data.py` | exact (role + flow) |
| `scripts/bench/make_slice.sh` | utility (shell script) | streaming (`gzcat \| head`) | `scripts/sync_versions.sh` (header/structure only) | role-match |
| `scripts/bench/baselines/bench_baseline.json` | config (data) | n/a | none (new schema) | none |
| `scripts/bench/tests/test_time_parser.py` | test | transform | `pyo3/tests/test_core.py` (class-based structure only) | role-match |
| `scripts/bench/tests/test_degradation.py` | test | transform | `pyo3/tests/test_core.py` | role-match |
| `scripts/bench/tests/test_compare.py` | test | transform | `pyo3/tests/test_core.py` | role-match |
| `scripts/bench/tests/test_schema.py` | test | transform | `pyo3/tests/test_core.py` | role-match |
| `scripts/bench/tests/test_cmd_matrix.py` | test | transform | `pyo3/tests/test_core.py` | role-match |
| `scripts/bench/tests/test_generator.py` | test | file-I/O | `pyo3/tests/test_core.py` | role-match |
| `scripts/bench/tests/fixtures/time_l_macos.txt`, `time_v_linux.txt` | test fixture (data) | n/a | none (capture fresh) | none |
| `.github/workflows/benchmark.yml` | config (CI workflow) | batch | `.github/workflows/ci.yml` | exact (role + flow) |
| DELETE `.github/workflows/performance-regression.yml` | config (dead CI) | n/a | — (deletion task) | n/a |
| DELETE `src/cli/commands/benchmark.rs` | dead Rust prototype | n/a | — (deletion task; mine schema first) | n/a |

**Product-behavior constraint:** no file under `src/` other than the optional dead-code deletion. `rustkmer count`/`merge`/`stats` are observed, never modified.

## Pattern Assignments

### `scripts/bench/bench.py` (utility, subprocess measurement)

**Analogs:** `src/cli/commands/benchmark.rs` (JSON result-schema ideas ONLY — it is unregistered dead code and an anti-pattern for orchestration per RESEARCH.md) + RESEARCH.md "Code Examples" (verified measurement core).

**What to mine from `src/cli/commands/benchmark.rs` lines 32-52** — result schema shape (serde struct; translate to versioned JSON keys):

```rust
pub struct BenchmarkResult {
    pub test_name: String,
    pub tool: String,
    pub kmer_size: usize,
    pub file_path: String,
    pub execution_time_seconds: f64,
    pub memory_usage_mb: Option<f64>,   // harness replaces with real peak_rss_bytes
    pub success: bool,
    pub error_message: Option<String>,
    pub timestamp: u64,
}
```

**Do NOT copy from benchmark.rs:** its orchestration shells out to `cargo run --release` (lines 286-302) instead of the built release binary, and `memory_usage_mb: None, // TODO` (line 312) — both cited as reasons it stays dead in RESEARCH.md Anti-Patterns.

**Measurement core to copy** (RESEARCH.md lines 367-389, verified live this session — dual-platform RSS parser, stdlib only):

```python
import re, subprocess, sys

MAC_RSS = re.compile(r"^\s*(\d+)\s+maximum resident set size\s*$")   # bytes
LIN_RSS = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")  # kbytes

def measure(argv: list[str]) -> dict:
    time_flag = "-l" if sys.platform == "darwin" else "-v"
    proc = subprocess.run(["/usr/bin/time", time_flag, *argv],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{argv[0]} failed rc={proc.returncode}: {proc.stderr[-500:]}")
    peak = None
    for line in proc.stderr.splitlines():
        if m := MAC_RSS.match(line):
            peak = int(m.group(1))                      # already bytes on macOS
        elif m := LIN_RSS.match(line):
            peak = int(m.group(1)) * 1024               # kbytes -> bytes
    assert peak is not None, "no RSS line parsed — format drift?"
    return {"peak_rss_bytes": peak}
```

**Matched command construction** (RESEARCH.md lines 397-405 — encodes BENCH-02 fairness; flags verified against `src/cli/args.rs` and jellyfish 2.3.1 `--help`):

```python
def rustkmer_cmd(k, threads, inputs, out):
    return ["target/release/rustkmer", "count", "-k", str(k), "-C",
            "--threads", str(threads), "-o", out, *inputs]

def jellyfish_cmd(k, threads, gz_inputs, out, hash_size="10G", decompressor="gzcat"):
    inner = (f"{decompressor} {' '.join(gz_inputs)} | "
             f"jellyfish count -m {k} -s {hash_size} -t {threads} -C -o {out} /dev/stdin")
    return ["sh", "-c", inner]
```

**Script skeleton convention** (from `test_data/generate_test_data.py` lines 1-6, 37, 93): shebang `#!/usr/bin/env python3`, module docstring, `main()` + `if __name__ == "__main__": main()`. Add `argparse` (stdlib) for `--mode/--out/--self-check/--parity-only` per RESEARCH.md Pattern 5.

**Error handling:** raise on non-zero exit AND on sanity failure (`distinct_kmers > 0` after every run — non-negotiable per RESEARCH.md Pitfall 1); record `cache_state` per run (Pitfall 9); `df` guardrail before mode=full (Pitfall 8).

---

### `scripts/bench/gen_synthetic.py` (utility, deterministic file-I/O)

**Analog:** `test_data/generate_test_data.py` (exact role+flow match)

**Generator core pattern** (lines 8-11 — extend with seeding and FASTQ format):

```python
def generate_random_dna_sequence(length):
    """Generate a random DNA sequence of specified length."""
    bases = ['A', 'T', 'C', 'G']
    return ''.join(random.choice(bases) for _ in range(length))
```

**Delta vs analog (per RESEARCH.md Pattern 4):**
- Analog is NOT seeded — harness generator MUST call `random.seed(args.seed)` (default 42) for byte-identical output across machines.
- Analog writes FASTA; generator writes 4-line FASTQ records (`@header`, seq, `+`, quality line — quality chars fixed, e.g. `'I' * length`).
- CLI: `--reads N --length 150 --seed 42 --out path`; `--reads` sized so measured op ≥5 s (RESEARCH.md Pitfall 7; ≥200k reads).
- Keep the analog's print-progress style (lines 53-57) if desired; output path must be parameterized (analog hardcodes its own dir — do not copy that, lines 39, 51).

---

### `scripts/bench/compare.py` (utility, JSON transform / gate)

**No repo analog.** Build from RESEARCH.md Pattern 5 + Don't-Hand-Roll table: argparse (`--baseline --current --wall-threshold 0.25 --rss-threshold 0.15`), validate both JSONs against the versioned schema first (V5 control: malformed input → hard error), exit 1 on breach, 0 within. Stdlib `json` + `sys` only. Unit-tested by `test_compare.py`.

---

### `scripts/bench/make_slice.sh` (utility, streaming shell)

**Analog (structure only):** `scripts/sync_versions.sh` lines 1-6 — `#!/bin/bash`, usage comment header, `set -e`.

**Core line** (RESEARCH.md "Deterministic slice", verified recipe):

```bash
gzcat "${INPUT}" | head -n $((4 * N_READS)) > slice.fq
```

Use `gunzip -c` (portable) or platform-branch; NEVER `zcat` on macOS (RESEARCH.md Pitfall 1).

---

### `scripts/bench/tests/*.py` (tests, stdlib unittest)

**Analog:** `pyo3/tests/test_core.py` — copy the *class-based test organization and docstring-per-test style* (lines 1-55):

```python
class TestPyDatabase:
    """Test PyDatabase class."""

    def test_query_kmer(self, tiny_db_path):
        """Test querying a k-mer."""
```

**Critical divergence:** analog imports `pytest` and uses fixtures (`tiny_db_path` from `pyo3/tests/conftest.py`) — the harness tests MUST use **stdlib `unittest` only** (`import unittest`, `class X(unittest.TestCase)`, `self.assertEqual/assertRaises`, `unittest.main()`), discoverable via `python3 -m unittest discover -s scripts/bench/tests`. This is a locked RESEARCH.md decision (dodges the repo's pyo3 pytest/addopts breakage). No conftest.py, no fixtures — build inputs in `setUp`/tempdirs (`tempfile` stdlib).

Test contents map 1:1 to RESEARCH.md Validation Architecture table: `test_time_parser` (parse both fixture files + reject garbage), `test_degradation` (mode ladder resolver table), `test_compare` (boundary JSON pairs), `test_schema` (schema_version + per-rep wall_s/peak_rss_bytes), `test_cmd_matrix` (golden argv pairs), `test_generator` (same seed → identical bytes).

**Fixtures:** `fixtures/time_l_macos.txt` / `time_v_linux.txt` — capture real `/usr/bin/time` output fresh on each platform (macOS locally; Linux format from RESEARCH.md Pattern 1 line 223: `Maximum resident set size (kbytes): 62384`).

---

### `.github/workflows/benchmark.yml` (config, CI gate)

**Analog:** `.github/workflows/ci.yml` (exact role match — copy its workflow hygiene verbatim)

**Trigger + permissions pattern** (ci.yml lines 7-25 — branch set is `[dev, main]`, NOT the dead `main/develop` of performance-regression.yml):

```yaml
on:
  pull_request:
    branches: [dev, main]
  push:
    branches: [dev, main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read    # pull_request (NOT pull_request_target) — T-01-SC least privilege
```

**Matrix + cache pattern** (ci.yml lines 41-46, 52-68 — ubuntu+macOS matrix, per-job cache namespace):

```yaml
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
```

**Gate steps** (RESEARCH.md Pattern 5 / lines 418-426):

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: cargo build --release
      - run: python3 scripts/bench/bench.py --mode synthetic --out results.json
      - run: python3 scripts/bench/compare.py
              --baseline scripts/bench/baselines/bench_baseline.json
              --current results.json
              --wall-threshold 0.25 --rss-threshold 0.15
```

**Do NOT copy from `performance-regression.yml`** (the file being deleted): `pull-requests: write`/`issues: write` permissions, no-op `if [ -f script ]` guards (its core disease — every step silently skips), `schedule` cron, artifact/PR-comment machinery, pip-installing pytest/memory-profiler. benchmark.yml needs no pip installs at all (stdlib only). Gate steps must fail loudly, mirroring ci.yml's documented "no continue-on-error, no `|| true`" rule (ci.yml lines 3-6).

---

### Deletions (planner decision, RESEARCH.md Open Q3 + Anti-Patterns)

- `src/cli/commands/benchmark.rs` — unregistered (absent from `args.rs`/`main.rs` dispatch); mine the JSON schema (above) before deleting. Confirm no `mod benchmark;` reference breaks `cargo clippy --all-targets -- -D warnings`.
- `.github/workflows/performance-regression.yml` — dead branches + nonexistent scripts; superseded by benchmark.yml.

## Shared Patterns

### Script header / entry point
**Source:** `test_data/generate_test_data.py` lines 1-6, 37-39, 93-94
**Apply to:** all `scripts/bench/*.py`
```python
#!/usr/bin/env python3
"""One-line purpose."""

import ...

def main():
    ...

if __name__ == "__main__":
    main()
```

### Stdlib-only constraint (hard gate)
**Source:** RESEARCH.md Package Legitimacy Audit (vacuously clean — must stay that way)
**Apply to:** every new file. Allowed imports: `subprocess, json, argparse, random, unittest, statistics, hashlib, platform, re, sys, os, tempfile, pathlib`. No pytest, no numpy, no pip installs in CI.

### Sanity assertion after every measured run
**Source:** RESEARCH.md Pitfall 1 (three silent zero-count false successes reproduced this session)
**Apply to:** `bench.py` measurement loop
```python
assert stats["unique_kmers"] > 0, f"empty count from {cmd} — silent input failure?"
```

### CI least-privilege hygiene
**Source:** `.github/workflows/ci.yml` lines 7-25
**Apply to:** `benchmark.yml` — `pull_request` (never `pull_request_target`), `permissions: contents: read`, `concurrency` group, `fail-fast: false` matrix, explicit `timeout-minutes`.

### Error handling style
**Source:** repo convention (`set -e` in `scripts/sync_versions.sh` line 5; ci.yml fail-loud rule lines 3-6)
**Apply to:** all harness files — hard errors, no best-effort skips, non-zero exit on any validation failure.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `scripts/bench/compare.py` | utility | transform | No JSON-threshold comparator exists in repo (performance-regression.yml's comparator script never existed) — use RESEARCH.md Pattern 5 |
| `scripts/bench/baselines/bench_baseline.json` | config/data | n/a | New versioned schema (`schema_version`, `mode`, `input_fingerprint`, per-arm reps with `wall_s`+`peak_rss_bytes`, medians) per RESEARCH.md Don't-Hand-Roll table |
| `scripts/bench/tests/fixtures/*.txt` | test data | n/a | Capture fresh `/usr/bin/time` output per platform |
| stdlib-unittest test style | test | — | Repo's only Python tests (`pyo3/tests/`) are pytest+conftest based — deliberately NOT copied; follow RESEARCH.md's stdlib-unittest decision, borrowing only class organization from `test_core.py` |

## Metadata

**Analog search scope:** `.github/workflows/`, `scripts/`, `pyo3/tests/`, `test_data/`, `src/cli/commands/`
**Files scanned:** ~20 (all tracked per `git ls-files` verification on ci.yml, generate_test_data.py, benchmark.rs, test_core.py)
**Pattern extraction date:** 2026-10-09
