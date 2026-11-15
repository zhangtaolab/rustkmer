<!-- generated-by: gsd-doc-writer -->
# Configuration Guide

## Overview

rustkmer can be configured at three levels: a TOML config file (`.rustkmerrc`), environment variables (prefix `RUSTKMER_`), and per-invocation CLI flags. A thread-safe `ConfigManager` (`src/config/manager.rs`) merges the layers in the order **defaults → config file → environment variables**, and per-operation overrides sit on top.

Two things to keep in mind when configuring the CLI:

1. **The CLI entry point does not load `.rustkmerrc` on startup.** `ConfigManager` is a library-level facility (`rustkmer::config`) intended for embedding and tooling; `src/main.rs` dispatches straight to command handlers without reading the config file. Even for library consumers, loading is explicit: `ConfigManager::new()` starts from defaults and discovers a file path, but values are only merged when you call `.load()`. The environment variables the shipped CLI actually reads directly are listed in [Directly-read environment variables](#directly-read-environment-variables).
2. **Command flags always win** for the options they expose. For example, `rustkmer count --threads 4` overrides every environment tier for that run.

## Config file format (`.rustkmerrc`)

The config file is TOML with five top-level sections. `ConfigManager` searches these locations in order and uses the first match:

1. `./.rustkmerrc` (current working directory)
2. `$HOME/.rustkmerrc`
3. `$XDG_CONFIG_HOME/rustkmer/.rustkmerrc`

Example (all five top-level sections are required — the file is deserialized directly into `GlobalConfig` without serde defaults, so omitting a section fails with a `missing field` error; a key omitted inside a present section deserializes as `None`, not the documented default):

```toml
[memory]
memory_limit = 512000000     # bytes
mmap_threshold = 50000000    # bytes
page_size = 10000
adaptive = true
force_mmap = false

[kmer_counting]
default_k = 25               # 1-64
canonical = true
threads = 2                  # 0 = auto-detect
hash_size = 1000000
sort_output = true
# min_count = 1              # optional, unset by default
# max_count = 1000           # optional, unset by default
progress = true

[database]
extension = "rkdb"
format_version = "2"
compression = true
indexing = "auto"

[output]
format = "text"              # text | json | csv | tsv
timestamps = true
statistics = true
verbose = false
quiet = false

[logging]
level = "info"
# file_path = "/var/log/rustkmer.log"  # optional, unset by default
structured = false
```

`ConfigManager::save()` serializes the current configuration back to the discovered file as pretty TOML. If no config file was discovered (and none was supplied via `ConfigManager::with_config_file`), `save()` returns the error `No configuration file specified` — it does not create a new file.

## Environment variables

### Layered-config variables (`RUSTKMER_*`)

These are applied by `ConfigManager::apply_env_overrides` after the config file is read, so they override file values. Numeric values that fail to parse are ignored; malformed booleans fall back to the noted default.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RUSTKMER_MEMORY_LIMIT` | u64 (bytes) | `1073741824` (1 GiB) | Memory limit in bytes |
| `RUSTKMER_MMAP_THRESHOLD` | u64 (bytes) | `104857600` (100 MiB) | Memory-mapping threshold in bytes |
| `RUSTKMER_PAGE_SIZE` | usize | `10000` | Page size for query results |
| `RUSTKMER_ADAPTIVE` | bool | `true` | Enable adaptive memory management |
| `RUSTKMER_FORCE_MMAP` | bool | `false` | Force memory mapping |
| `RUSTKMER_DEFAULT_K` | usize | `31` | Default k-mer size (valid: 1–64) |
| `RUSTKMER_CANONICAL` | bool | `true` | Use canonical k-mers |
| `RUSTKMER_THREADS` | usize | `0` (auto) | Thread count (0 = auto-detect, max 256) |
| `RUSTKMER_HASH_SIZE` | usize | `1000000` | Hash table size |
| `RUSTKMER_SORT_OUTPUT` | bool | `true` | Sort output by k-mer |
| `RUSTKMER_MIN_COUNT` | u32 | unset | Minimum count filter |
| `RUSTKMER_MAX_COUNT` | u32 | unset | Maximum count filter |
| `RUSTKMER_PROGRESS` | bool | `true` | Enable progress reporting |
| `RUSTKMER_FORMAT` | string | `text` | Default output format |
| `RUSTKMER_TIMESTAMPS` | bool | `true` | Enable timestamps in output |
| `RUSTKMER_STATISTICS` | bool | `true` | Enable statistics output |
| `RUSTKMER_VERBOSE` | bool | `false` | Verbose output |
| `RUSTKMER_QUIET` | bool | `false` | Quiet mode |
| `RUSTKMER_LOG_LEVEL` | string | `info` | Log level (see [Logging](#logging) for the caveat) |
| `RUSTKMER_LOG_FILE` | path | unset | Log file path |
| `RUSTKMER_STRUCTURED` | bool | `false` | Enable structured logging |

### Directly-read environment variables

These are read by the shipped CLI/lib code paths independently of `ConfigManager`:

| Variable | Read by | Effect |
|----------|---------|--------|
| `RUSTKMER_THREADS` | `count` command (`src/cli/commands/count.rs`) | Thread-count tier between `--threads` and `RAYON_NUM_THREADS` |
| `RAYON_NUM_THREADS` | `count` and `merge` commands | Rayon-standard thread count; lowest env tier |
| `RUST_LOG` | `env_logger` init in `src/main.rs` | Log filter (default `info` when unset) |
| `RUST_LOG_STYLE` | `env_logger` init in `src/main.rs` | Log output styling (`auto`, `always`, `never`) |
| `PYTHON_LIB_DIR` | Not read by any code path | `.cargo/config.toml` mentions it only in commented-out examples, so setting it has no effect; no build script, manifest, source file, or helper script reads it |
| `HOME`, `XDG_CONFIG_HOME` | `ConfigManager` file discovery | Location of `.rustkmerrc` |

The benchmark harness (`scripts/bench/bench.py`) additionally reads `RUSTKMER_BENCH_MODE` and `RUSTKMER_BENCH_INPUT` to select the input mode/inputs when the corresponding CLI flags are omitted; see the [benchmarking guide](benchmarking.md) for that resolution ladder. The opt-in Python-benchmark integration test (`scripts/bench/tests/test_python_bench.py`) runs only when `RUSTKMER_PYBENCH_VENV` points at a freshly built virtualenv and is skipped otherwise; it is not read by any shipped binary. No other runtime environment variables are read by the crate.

## Required vs optional settings

**No environment variable or config key is required.** Every setting has a default, and the CLI runs with zero configuration. Invalid values fail at validation, not at startup:

- `ConfigManager::validate_config` reports (does not throw until surfaced by the caller): `memory_limit`, `mmap_threshold`, `page_size`, and `hash_size` must be non-zero; `default_k` must be 1–64; `threads` must not exceed 256; `extension` must be non-empty.
- The `count` command rejects `--threads < 1` ("--threads must be >= 1", collected in `Commands::validate_input` in `src/cli/args.rs`) and k-mer sizes outside 1–64 (`KmerError::InvalidKmerSize`).
- The `merge` command returns an error for an unparseable `--max-memory` value (e.g. `Invalid memory limit 'abc': Invalid number: ABC` — `parse_memory_size` trims and upper-cases the value before parsing, so the echoed number is upper-case).

## Defaults

Defaults are defined in the `Default` implementations in `src/config/manager.rs`:

| Section | Key | Default |
|---------|-----|---------|
| memory | `memory_limit` | `1073741824` (1 GiB) |
| memory | `mmap_threshold` | `104857600` (100 MiB) |
| memory | `page_size` | `10000` |
| memory | `adaptive` | `true` |
| memory | `force_mmap` | `false` |
| kmer_counting | `default_k` | `31` |
| kmer_counting | `canonical` | `true` |
| kmer_counting | `threads` | `0` (auto-detect) |
| kmer_counting | `hash_size` | `1000000` |
| kmer_counting | `sort_output` | `true` |
| kmer_counting | `progress` | `true` |
| database | `extension` | `"rkdb"` |
| database | `format_version` | `"2"` |
| database | `compression` | `true` |
| database | `indexing` | `"auto"` |
| output | `format` | `"text"` |
| output | `timestamps` / `statistics` | `true` |
| output | `verbose` / `quiet` | `false` |
| logging | `level` | `"info"` |
| logging | `structured` | `false` |

Merge-specific defaults (`MergeConfig::default()` in `src/database/merge_config.rs`): `max_memory_usage` = 50% of system memory, `chunk_size` = 50,000,000 k-mers, `temp_dir` = system temp dir, `merge_mode` = `"auto"`.

## Per-environment overrides

There is no built-in environment selector: `ConfigManager` has no development/staging/production switch, and the repository ships no `.env`, `.env.development`, or `.env.production` files. The config-file search order above is fixed regardless of context.

To vary settings per environment, use one of the mechanisms the code actually supports:

1. **Environment variables in the runner** — set `RUSTKMER_*` (and `RAYON_NUM_THREADS` / `RUST_LOG`) in each environment's shell, CI job, or container definition. These override the config file for `ConfigManager` consumers and are read directly where noted above.
2. **Distinct config files** — library consumers can load an explicit file with `ConfigManager::with_config_file("/path/to/staging.rustkmerrc")`; the CLI never loads a config file, so its per-environment differences must come from flags and environment variables.
3. **Per-invocation CLI flags** — highest precedence for the options they expose (for example `--threads`, `--max-memory`, `--merge-mode`).

Because the CLI does not read `.rustkmerrc`, any environment-specific defaults used by pipelines must be passed as flags or environment variables at invocation time.

## Thread configuration

### `count` command

Precedence, highest first (implemented in `resolve_thread_count`, `src/cli/commands/count.rs`):

```text
--threads  >  RUSTKMER_THREADS  >  RAYON_NUM_THREADS  >  all CPU cores
```

Set with `rustkmer count --threads 4` or `RUSTKMER_THREADS=4 rustkmer count ...`. Malformed env values and values below 1 in either environmental tier are ignored and fall through to the next tier; a `--threads` value below 1 is a validation error instead of being silently ignored.

### `merge` command

`--num-threads` (default `0` = all cores) builds the Rayon global thread pool. When set to `0`, `RAYON_NUM_THREADS` is honored if present and parseable (`src/cli/commands/merge.rs`). Note the merge command does **not** read `RUSTKMER_THREADS`. If the global pool was already initialized earlier in the same process, the pool request is skipped with a note under `--verbose` (the existing pool stays in effect).

## Memory configuration (merge)

The `merge` command accepts a human-readable budget via `--max-memory`, parsed by `parse_memory_size` (`src/cli/commands/merge.rs` — the same parser backs the Python `max_memory=` kwarg so both surfaces accept identical grammar):

```bash
rustkmer merge -i a.rkdb b.rkdb -o merged.rkdb --max-memory 32GB
```

- **Units**: `B`, `KB`, `MB`, `GB`, `TB` (binary multipliers of 1024). A bare number is treated as bytes. Case-insensitive; whitespace is trimmed.
- **Bounds**: minimum 1 KB ("Memory size too small (minimum 1KB)"); maximum 1 TB — larger values (including arithmetic overflow) return an error, never a panic.
- **Default** (flag omitted): 50% of total system memory, read from `/proc/meminfo` on Unix; if unavailable, a fixed 32 GB fallback.

Related merge routing flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--merge-mode` | `auto` | `auto` (in-memory while the estimated footprint fits `max_memory`, otherwise streaming — `should_use_streaming` in `src/database/format.rs`), `memory` (force in-memory; rejected with an error if the estimate exceeds the budget), `streaming` (always stream) |
| `--use-prefix-cache` | off | External-sort prefix-cache merge strategy (memory-efficient, error isolation). With this route enabled, `--merge-mode` does not select the route |
| `--batch-size` | `100000` | Accepted by the CLI but not currently propagated to the prefix-cache merge, which uses an internal constant batch size. The effective default comes from the clap surface in `src/cli/args.rs`; `MergeArgs` in `src/cli/commands/merge.rs` declares a divergent `50000` default but is never parsed — `src/main.rs` copies the parsed fields in verbatim |
| `--temp-dir` | system temp | Directory for merge intermediate files |
| `--keep-intermediate` | off | Keep intermediate files for debugging |
| `--check-compatibility` | off | Compare input database headers without merging |

## Logging

The CLI initializes `env_logger` in `src/main.rs` with `Env::default().default_filter_or("info")`:

```bash
RUST_LOG=debug rustkmer count -k 31 -i reads.fastq -o db.rkdb   # verbose logging
RUST_LOG=warn rustkmer merge ...                                 # warnings and errors only
```

`RUSTKMER_LOG_LEVEL` / `RUSTKMER_LOG_FILE` / `RUSTKMER_STRUCTURED` exist in `GlobalConfig` for library consumers, but the CLI's `env_logger` reads `RUST_LOG`, not `RUSTKMER_LOG_LEVEL`.

## Database format settings

`.rkdb` files are a fixed-layout binary format defined by constants in `src/database/format.rs`:

| Constant | Value | Meaning |
|----------|-------|---------|
| `DATABASE_MAGIC` | `b"RKDB"` | 4-byte file magic |
| `DATABASE_VERSION` | `2` | On-disk format version (u16) |

Layout: a 42-byte header followed by 20-byte entries (16-byte u128 k-mer + 4-byte u32 count), written little-endian via `byteorder`. Readers reject any header `data_offset` other than 42 with an error (`DatabaseQuery::open`/`load_entries` in `src/database/query.rs`; `DatabaseHeader::validate`, `RKDatabase::from_file_path`, and `RKDatabase::read_header_of` in `src/database/format.rs`). The `[database]` config section (`extension`, `format_version`, `compression`, `indexing`) is exposed through `GlobalConfig`, but no CLI, reader, or writer code path reads these fields today — on-disk format constants are compiled in.

## Build-time configuration

### Rust (root `Cargo.toml`)

- Crate `rustkmer` 0.5.0, edition 2021, MSRV `rust-version = "1.82"`; `pyo3/Cargo.toml` builds `rustkmer-pyo3` 0.5.0 as a `cdylib` named `pyrustkmer` with the same MSRV.
- Release profile: `lto = true`, `codegen-units = 1`, `panic = "abort"` — keep these when editing `[profile.release]`.
- Features: `default = []`, `profiling = []`, `disable-zstd = []` (root); `extension-module = ["pyo3/extension-module"]` (pyo3 crate).
- `.cargo/config.toml` documents optional cross-platform Python linking via `PYTHON_LIB_DIR` (see the [Directly-read environment variables](#directly-read-environment-variables) table).

### Python bindings (`pyo3/pyproject.toml`)

- Build backend: maturin (`maturin>=1.0,<2.0`), `[tool.maturin]` with `module-name = "pyrustkmer"` and the `pyo3/extension-module` feature; `[tool.maturin.build]` passes `--release`.
- `requires-python = ">=3.11"`; runtime dependency `numpy>=1.21`.
- Optional dependency groups: `dev` (pytest, black, flake8, mypy, ...), `performance` (memory-profiler, psutil), `docs`, `jupyter`.
- Tool config in the same file: black (line length 88, py311 target), mypy (strict, python_version 3.11), coverage source `pyrustkmer`.
- pytest is configured with verbosity-only `addopts = ["-v"]`; the 80% threshold is applied by the CI `pyo3-pytest` job's pytest command line (`--cov-fail-under=80`), not by local defaults.

Build and install the extension with `maturin develop --release` (run from `pyo3/`). The legacy helper `pyo3/build_with_python.sh` is *not* a maturin wrapper: it runs `cargo clean` followed by a debug-profile `cargo build` with `PYO3_PYTHON=/usr/bin/python3` and macOS `dynamic_lookup` link flags, then test-imports the stale module name `rustkmer_pyo3` — the native module has been named `pyrustkmer` since the rename (`pyo3/Cargo.toml` `[lib] name`, `pyo3/pyproject.toml` `module-name`), so the script's import check fails even after a successful build. Prefer invoking maturin directly. Version bumps must keep the root `Cargo.toml`, `pyo3/Cargo.toml`, and `pyo3/pyproject.toml` versions in sync (`scripts/sync_versions.sh`).
