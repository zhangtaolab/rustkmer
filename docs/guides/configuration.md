<!-- generated-by: gsd-doc-writer -->
# Configuration Guide

## Overview

rustkmer can be configured at three levels: a TOML config file (`.rustkmerrc`), environment variables (prefix `RUSTKMER_`), and per-invocation CLI flags. A thread-safe `ConfigManager` (`src/config/manager.rs`) merges the layers in the order **defaults → config file → environment variables**, and per-operation overrides sit on top.

Two things to keep in mind when configuring the CLI:

1. **The CLI entry point does not load `.rustkmerrc` on startup.** `ConfigManager` is a library-level facility (`rustkmer::config`) intended for embedding and tooling; `src/main.rs` dispatches straight to command handlers. The environment variables the shipped CLI actually reads directly are listed in [Directly-read environment variables](#directly-read-environment-variables).
2. **Command flags always win** for the options they expose. For example, `rustkmer count --threads 4` overrides every environment tier for that run.

## Config file format (`.rustkmerrc`)

The config file is TOML with five top-level sections. `ConfigManager` searches these locations in order and uses the first match:

1. `./.rustkmerrc` (current working directory)
2. `$HOME/.rustkmerrc`
3. `$XDG_CONFIG_HOME/rustkmer/.rustkmerrc`

Minimal working example (all keys are optional — any omitted key falls back to its default):

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

`ConfigManager::save()` serializes the current configuration back to the discovered file as pretty TOML.

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
| `PYTHON_LIB_DIR` | build-time linking (see `.cargo/config.toml`) | Optional Python library path when building the PyO3 extension with unusual Python installs |
| `HOME`, `XDG_CONFIG_HOME` | `ConfigManager` file discovery | Location of `.rustkmerrc` |

## Required vs optional settings

**No environment variable or config key is required.** Every setting has a default, and the CLI runs with zero configuration. Invalid values fail at validation, not at startup:

- `ConfigManager::validate_config` reports (does not throw until surfaced by the caller): `memory_limit`, `mmap_threshold`, `page_size`, and `hash_size` must be non-zero; `default_k` must be 1–64; `threads` must not exceed 256; `extension` must be non-empty.
- The `count` command rejects `--threads < 1` ("--threads must be >= 1") and k-mer sizes outside 1–64 (`KmerError::InvalidKmerSize`, matching the u128 encoding bound in `src/kmer/encoding.rs`).
- The `merge` command returns an error for an unparseable `--max-memory` value (e.g. `Invalid memory limit 'abc': Invalid number: abc`).

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

## Thread configuration

### `count` command

Precedence, highest first (implemented in `resolve_thread_count`, `src/cli/commands/count.rs`):

```text
--threads  >  RUSTKMER_THREADS  >  RAYON_NUM_THREADS  >  all CPU cores
```

Set with `rustkmer count --threads 4` or `RUSTKMER_THREADS=4 rustkmer count ...`. Malformed or `< 1` env values fall through to the next tier instead of erroring.

### `merge` command

`--num-threads` (default `0` = all cores) builds the Rayon global thread pool. When set to `0`, `RAYON_NUM_THREADS` is honored if present and parseable (`src/cli/commands/merge.rs`). Note the merge command does **not** read `RUSTKMER_THREADS`.

## Memory configuration (merge)

The `merge` command accepts a human-readable budget via `--max-memory`, parsed by `parse_memory_size` (`src/cli/commands/merge.rs` — the same parser backs the Python `max_memory=` kwarg so both surfaces accept identical grammar):

```bash
rustkmer merge -i a.rkdb b.rkdb -o merged.rkdb --max-memory 32GB
```

- **Units**: `B`, `KB`, `MB`, `GB`, `TB` (binary multipliers of 1024). A bare number is treated as bytes. Case-insensitive; whitespace is trimmed.
- **Ceiling**: 1 TB — larger values (including arithmetic overflow) return an error, never a panic.
- **Default** (flag omitted): 50% of total system memory, read from `/proc/meminfo` on Unix; if unavailable, a fixed 32 GB fallback.

Related merge routing flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--merge-mode` | `auto` | `auto` (in-memory when estimated footprint is small), `memory` (force in-memory), `streaming` (always stream) |
| `--use-prefix-cache` | off | External-sort prefix-cache merge strategy (memory-efficient, error isolation) |
| `--batch-size` | `100000` | K-mers per buffer flush in prefix-cache mode. The effective default comes from the clap surface in `src/cli/args.rs`; `MergeArgs` in `src/cli/commands/merge.rs` declares a divergent `50000` default but is never parsed — `src/main.rs` copies the parsed fields in verbatim |
| `--temp-dir` | system temp | Directory for merge intermediate files |
| `--keep-intermediate` | off | Keep intermediate files for debugging |

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

Layout: a 42-byte header followed by 20-byte entries (16-byte u128 k-mer + 4-byte u32 count), written little-endian via `byteorder`. Readers reject any header `data_offset` other than 42 with an error (`load_entries` in `src/database/query.rs` and `DatabaseHeader::validate` in `src/database/format.rs`). The `[database]` config section (`extension`, `format_version`, `compression`, `indexing`) only affects library-side defaults — on-disk constants are compiled in.

## Build-time configuration

### Rust (root `Cargo.toml`)

- Crate `rustkmer` 0.5.0, edition 2021; `pyo3/Cargo.toml` builds `rustkmer-pyo3` 0.5.0 as a `cdylib` named `pyrustkmer`.
- Release profile: `lto = true`, `codegen-units = 1`, `panic = "abort"` — keep these when editing `[profile.release]`.
- Features: `default = []`, `profiling = []`, `disable-zstd = []` (root); `extension-module = ["pyo3/extension-module"]` (pyo3 crate).
- `.cargo/config.toml` documents optional cross-platform Python linking via `PYTHON_LIB_DIR` (see the [Directly-read environment variables](#directly-read-environment-variables) table).

### Python bindings (`pyo3/pyproject.toml`)

- Build backend: maturin (`maturin>=1.0,<2.0`), `[tool.maturin]` with `module-name = "pyrustkmer"` and the `pyo3/extension-module` feature; `[tool.maturin.build]` passes `--release`.
- `requires-python = ">=3.11"`; runtime dependency `numpy>=1.21`.
- Optional dependency groups: `dev` (pytest, black, flake8, mypy, ...), `performance` (memory-profiler, psutil), `docs`, `jupyter`.
- Tool config in the same file: black (line length 88, py311 target), mypy (strict, python_version 3.11), coverage source `pyrustkmer`.
- pytest is configured with verbosity-only `addopts = ["-v"]`; the 80% threshold is applied by the CI `pyo3-pytest` job's pytest command line, not by local defaults.

Build and install the extension with `maturin develop --release` (helper script: `pyo3/build_with_python.sh`). Version bumps must keep the root `Cargo.toml`, `pyo3/Cargo.toml`, and `pyo3/pyproject.toml` versions in sync (`scripts/sync_versions.sh`).
