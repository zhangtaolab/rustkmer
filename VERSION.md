# Version Management

This document describes the version management strategy for RustKmer.

## Version Policy

RustKmer consists of two main components:
- **Rust CLI** (`rustkmer`) - Command-line tool
- **PyO3** (`pyrustkmer`) - Python bindings

Both components are versioned together using **Semantic Versioning (SemVer)**:
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

## Version Synchronization

Both components should always be released with the same version number.

### Current Version

```
Rust CLI: 0.5.0
PyO3:     0.5.0
```

### Synchronization

Use the provided sync script to ensure versions stay in sync:

```bash
# Check if versions are in sync
./scripts/sync_versions.sh

# Or set a specific version
./scripts/sync_versions.sh 0.5.0
```

### Manual Update

When updating version, update these files:

1. **Rust CLI**:
   - `Cargo.toml` (root): `version = "X.Y.Z"`
   - `src/cli/args.rs`: Uses `env!("CARGO_PKG_VERSION")` (auto-syncs)

2. **PyO3**:
   - `pyo3/Cargo.toml`: `version = "X.Y.Z"`
   - `pyo3/pyproject.toml`: `version = "X.Y.Z"`

## Release Process

1. Update version in all files
2. Run `./scripts/sync_versions.sh` to verify
3. Update CHANGELOG.md
4. Create release commit
5. Build and test both components
6. Publish to respective package managers

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 0.5.0 | 2026-01-18 | Current version |
| 0.4.1 | 2026-01-18 | PyO3 unified API |
| 0.4.0 | 2026-01-17 | Initial PyO3 release |
| 0.2.0 | 2026-01-16 | CLI refactoring |
