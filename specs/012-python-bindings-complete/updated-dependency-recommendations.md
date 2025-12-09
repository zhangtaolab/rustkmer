# Updated Dependency Recommendations

**Date**: 2025-12-09 (Updated with crates.io verification)
**Purpose**: Updated recommendations for all RustKmer dependencies based on crates.io verification

## Summary

All dependencies have been checked against the latest versions available on crates.io. Most dependencies have updates available, ranging from minor patches to major version upgrades.

## Critical Updates (High Priority)

### 1. PyO3 Migration
```toml
# Current:
[dependencies.pyo3]
version = "0.23.4"
features = ["extension-module"]
optional = true

# Update to:
[dependencies.pyo3]
version = "0.27.2"
features = ["extension-module"]
optional = true
```
**Note**: Requires code migration as documented in the main plan.

### 2. Bioinformatics Library Update
```toml
# Current:
bio = "2.0"

# Update to:
bio = "3.0.0"
```
**Impact**: Major version update - may have breaking changes. Test thoroughly.

### 3. thiserror Update
```toml
# Current:
thiserror = "2.0"

# Update to:
thiserror = "2.0.17"
```

## Minor Updates (Recommended - Low Risk)

### Core Dependencies
```toml
clap = { version = "4.5.53", features = ["derive"] }  # from 4.5
anyhow = "1.0.100"  # from 1.0
rayon = "1.11.0"  # from 1.10
```

### Serialization
```toml
serde = { version = "1.0.228", features = ["derive"] }  # from 1.0
serde_json = "1.0.145"  # from 1.0
bincode = "2.0.1"  # from 1.3 (Major update - test compatibility)
```

### Utilities
```toml
memmap2 = "0.9.9"  # from 0.9
byteorder = "1.5.0"  # from 1.5 (already at latest, but add full version)
csv = "1.4.0"  # from 1.3
smallvec = "1.13.2"  # from 1.13 (2.0 is alpha)
hashbrown = "0.16.1"  # from 0.14 (Major update - evaluate carefully)
ahash = "0.8.12"  # from 0.8
```

### Statistics and Testing
```toml
tdigest = "0.2.3"  # from 0.2
proptest = "1.9.0"  # from 1.5
parking_lot = "0.12.5"  # from 0.12
criterion = { version = "0.8.1", features = ["html_reports"] }  # from 0.5 (Major update)
```

### System and CLI
```toml
num_cpus = "1.17.0"  # from 1.16
indicatif = "0.18.3"  # from 0.17
inquire = "0.8.1"  # from 0.7
walkdir = "2.5.0"  # from 2.4
```

### Compression
```toml
niffler = "3.0.0"  # from 2.5 (Major update)
flate2 = "1.1.5"  # from 1.0
bzip2 = "0.6.1"  # from 0.4
xz2 = "0.1.7"  # from 0.1 (already at latest)
```

### Cryptography and Time
```toml
sha2 = "0.10.8"  # from 0.10 (0.11 is release candidate)
chrono = { version = "0.4.42", features = ["serde"] }  # from 0.4
log = "0.4.29"  # from 0.4
env_logger = "0.11.8"  # from 0.11
```

### Development Dependencies
```toml
tempfile = "3.23.0"  # from 3.12
rand = "0.8.5"  # from 0.8 (0.10 is release candidate)
rand_chacha = "0.3.1"  # from 0.3
```

## Major Updates Requiring Careful Evaluation

### 1. hashbrown: 0.14 → 0.16.1
- **Breaking Changes**: Yes
- **Benefits**: Performance improvements, new features
- **Action**: Test in separate branch first

### 2. bincode: 1.3 → 2.0.1
- **Breaking Changes**: Yes
- **Benefits**: Better performance, improved API
- **Action**: Test serialization compatibility

### 3. niffler: 2.5 → 3.0.0
- **Breaking Changes**: Yes
- **Benefits**: Improved compression support
- **Action**: Test file I/O compatibility

### 4. bio: 2.0 → 3.0.0
- **Breaking Changes**: Yes
- **Benefits**: Latest bioinformatics features
- **Action**: Test all bioinformatics functionality

### 5. criterion: 0.5 → 0.8.1
- **Breaking Changes**: Yes
- **Benefits**: Better benchmarking features
- **Action**: Update benchmarking code if needed

## Release Candidates (Optional)

- sha2: 0.11.0-rc.3
- rand: 0.10.0-rc.5
- rand_chacha: 0.10.0-rc.1
- smallvec: 2.0.0-alpha.12

**Recommendation**: Wait for stable releases unless you need specific features.

## Update Strategy

### Phase 1: Immediate Updates (Low Risk)
1. thiserror: 2.0 → 2.0.17
2. All patch updates where major version is the same
3. Add exact version numbers where currently using partial versions

### Phase 2: Minor Version Updates (Week 1)
1. clap: 4.5 → 4.5.53
2. serde family updates
3. chrono, log, env_logger
4. Compression libraries (flate2, bzip2)
5. Test after each batch

### Phase 3: Major Updates (Week 2-3)
1. Create feature branch
2. Test bio 3.0.0 compatibility
3. Evaluate hashbrown 0.16.1
4. Test bincode 2.0.1 with existing data
5. Update if compatibility confirmed

### Phase 4: PyO3 Migration (Already Planned)
1. Follow separate PyO3 migration plan
2. Update to 0.27.2 with code changes

## Testing Requirements

### After Each Update Group
```bash
# Basic compilation
cargo check
cargo build

# Run tests
cargo test --all-features

# Python bindings if applicable
cargo test --features python
```

### For Major Updates
- Full integration test suite
- Performance benchmarks
- Compatibility tests with existing data files
- Review breaking change documentation

## Benefits of Updates

1. **Security**: Latest patches include security fixes
2. **Performance**: Many updates include performance improvements
3. **Features**: Access to new features and improvements
4. **Maintenance**: Reduces technical debt
5. **Ecosystem**: Better compatibility with latest Rust tools

## Risk Mitigation

1. **Git Branching**: Create feature branches for major updates
2. **Incremental Updates**: Apply changes in small batches
3. **Testing**: Comprehensive testing after each update
4. **Documentation**: Update version requirements in README
5. **CI/CD**: Ensure CI tests pass with new versions

## Conclusion

While most dependencies have updates available, many are minor patch updates that are safe to apply. Major version updates should be evaluated carefully in a separate branch. The PyO3 migration remains the highest priority for the 012-python-bindings-complete branch.

The RustKmer project is generally well-maintained with dependencies that are actively developed and regularly updated.