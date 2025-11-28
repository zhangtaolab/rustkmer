# Research: 21-mer Performance Testing Analysis

**Branch**: `003-parallel-query` | **Date**: 2025-11-28
**Purpose**: Research 21-mer specific performance characteristics and multi-threading analysis using OSA1 r7 assembly data

## Executive Summary

Building on successful 13-mer performance testing, this research analyzes 21-mer k-mer database operations to determine if larger k-mer sizes benefit from multi-threading. The methodology follows established patterns while adapting for 21-mer specific memory and computational requirements.

## Decision Matrix

### Primary Database Creation Strategy
**Decision**: Use canonical 13-mer counting with sorted databases for rustkmer
**Rationale**: Ensures fair comparison with jellyfish canonical counting and provides optimal query performance through sorted binary search
**Alternatives considered**:
- Non-canonical counting (rejected: inconsistent with jellyfish default)
- Unsorted rustkmer databases (rejected: 89-177x slower query performance)

### Query Set Generation
**Decision**: Extract 10,000 random 13-mers from existing databases using deterministic seeding
**Rationale**: Ensures queries actually exist in databases while providing random, reproducible test set
**Alternatives considered**:
- Pure random sequence generation (rejected: most queries would return count=0)
- Sequential extraction (rejected: not representative of real usage patterns)

### Performance Measurement
**Decision**: Use `/usr/bin/time -v` for comprehensive resource monitoring plus rustkmer's built-in profiling
**Rationale**: Provides consistent measurement across all tools while capturing tool-specific insights
**Alternatives considered**:
- Custom timing scripts (rejected: inconsistent between tools)
- Basic time measurement (rejected: insufficient resource monitoring)

## Technical Findings

### Jellyfish Benchmarking Best Practices

#### Single-Threaded Database Creation
```bash
# Optimized for OSA1 r7 assembly (~120MB)
jellyfish count -m 13 -s 1G -t 1 -C --buffer-size 10M -o osa1_13mer.jf osa1.fasta
```

**Key Parameters**:
- `-t 1`: Force single-threaded for fair comparison
- `-s 1G`: Hash size to minimize collisions (120MB FASTA ≈ 120M potential k-mers)
- `-C`: Canonical k-mer counting (both strands)
- `--buffer-size 10M`: Optimize I/O performance

#### Query Performance Testing
```bash
# Comprehensive performance measurement
/usr/bin/time -v jellyfish query -i queries.txt osa1_13mer.jf 2> performance.log
```

### RustKmer Performance Optimization

#### Database Creation for Optimal Querying
```bash
rustkmer count -k 13 -C --canonical --sort --threads $(nproc) \
  --size 100000000 --format binary osa1.fasta -o osa1_k13_sorted.rkdb
```

**Critical Parameters**:
- `--sort`: Essential for query performance (89-177x speedup)
- `--canonical`: Matches jellyfish canonical counting
- `--threads $(nproc)`: Use all cores for database creation
- `--size 100000000`: Hash table size for expected k-mer count

#### Query Performance Comparison

**Single-threaded (equivalent to jellyfish)**:
```bash
/usr/bin/time -v rustkmer query --threads 1 --no-load database.rkdb $(cat queries.txt)
```

**Multi-threaded (rustkmer advantage)**:
```bash
/usr/bin/time -v rustkmer queryx --threads $(nproc) --batch-size 1000 --preload --profile database.rkdb --file queries.txt
```

### Performance Monitoring Capabilities

#### rustkmer queryx Built-in Profiling
- Total processing time and queries per second
- Thread efficiency and speedup factors
- Memory usage monitoring
- Adaptive performance recommendations
- Progress tracking for large query sets

#### System Resource Monitoring
- Memory usage: `Maximum resident set size` from `/usr/bin/time -v`
- CPU utilization: `Percent of CPU` usage
- I/O patterns: File system access statistics
- Context switches: System overhead measurement

## Data Management Strategy

### File Organization
```
/Users/forrest/Temp/demodata/
├── databases/
│   ├── osa1_k13_jellyfish.jf         # Jellyfish database
│   ├── osa1_k13_rustkmer_sorted.rkdb # RustKmer optimized database
│   └── queries/
│       ├── random_10k_queries.txt    # Identical query set for all tools
│       └── validation_results/       # Comparison output files
├── performance_logs/
│   ├── jellyfish_timing.log          # Jellyfish performance data
│   ├── rustkmer_single_timing.log   # RustKmer single-threaded data
│   └── rustkmer_multi_timing.log    # RustKmer multi-threaded data
└── results/
    ├── accuracy_comparison.csv      # Result accuracy validation
    └── performance_summary.json     # Comprehensive performance report
```

### Query Set Generation
```python
#!/usr/bin/env python3
import random
import sys

# Deterministic random seed for reproducibility
random.seed(42)

bases = ['A', 'C', 'G', 'T']
with open('/Users/forrest/Temp/demodata/queries/random_10k_queries.txt', 'w') as f:
    for i in range(10000):
        kmer = ''.join(random.choices(bases, k=13))
        f.write(f"{kmer}\n")
```

## Validation and Accuracy

### Result Comparison Strategy
1. **Query Execution**: Run identical 10,000 queries on all three tools
2. **Result Collection**: Capture k-mer sequence and count for each query
3. **Accuracy Validation**: Compare rustkmer results against jellyfish baseline
4. **Performance Analysis**: Measure throughput, memory usage, and resource efficiency

### Expected Outcomes
- **Accuracy**: 100% result consistency between jellyfish and rustkmer
- **Single-threaded Performance**: Comparable throughput between tools
- **Multi-threaded Advantage**: 2-10x speedup with rustkmer queryx for 10,000 queries
- **Memory Efficiency**: RustKmer's sorted databases provide better cache locality

## Implementation Workflow

### Phase 1: Environment Setup
1. Verify jellyfish installation and single-threaded capability
2. Build rustkmer in release mode for optimal performance
3. Create directory structure in `/Users/forrest/Temp/demodata/`
4. Validate OSA1 r7 assembly file accessibility

### Phase 2: Database Generation
1. Generate jellyfish database with single-threaded counting
2. Generate rustkmer database with sorted optimization
3. Validate database integrity and k-mer count consistency
4. Create deterministic 10,000 query set

### Phase 3: Performance Testing
1. Execute jellyfish single-threaded query benchmark
2. Execute rustkmer single-threaded query benchmark
3. Execute rustkmer multi-threaded queryx benchmark
4. Collect comprehensive performance metrics

### Phase 4: Analysis and Reporting
1. Validate result accuracy across all tools
2. Generate performance comparison reports
3. Create recommendations for optimal usage patterns
4. Document scaling characteristics and resource requirements

## Quality Assurance

### Reproducibility Measures
- Fixed random seed (42) for query generation
- Consistent file paths and naming conventions
- Multiple test runs for statistical validity
- Environment documentation for cross-platform compatibility

### Fair Comparison Principles
- Identical query sets for all tools
- Single-threaded baseline for both tools
- Comprehensive resource monitoring
- Transparent methodology documentation

## Risk Mitigation

### Potential Issues and Solutions
1. **Memory constraints**: Use appropriate hash sizes and monitor memory usage
2. **File system I/O**: Use local storage for consistent performance
3. **System load**: Run benchmarks on quiescent systems
4. **Version compatibility**: Document exact tool versions and parameters

## 21-mer Specific Analysis

### Performance Impact Analysis
**Key Finding from 13-mer Testing**: Multi-threading provides no significant performance benefit (only 0.6% difference) because k-mer database queries are memory-bound operations.

**21-mer Hypothesis**: The memory-bound limitation will be even more pronounced with 21-mers due to:
- Larger key sizes (42 bits vs 26 bits for 13-mers) = 62% larger memory footprint
- Increased hash collision probability requiring more complex resolution
- Reduced cache efficiency due to larger data structures
- Higher memory bandwidth requirements

### Database Generation Requirements
```bash
# Jellyfish 21-mer database (single-threaded)
jellyfish count -m 21 -s 2G -t 1 -C -o osa1_k21_jellyfish.jf osa1_r7.asm.fa

# RustKmer 21-mer database (single-threaded for fair comparison)
rustkmer count -k 21 -C --sort --threads 1 --size 200000000 --format binary osa1_r7.asm.fa
```

### Expected Performance Characteristics
- **Database Size**: 600-800MB (50-80% larger than 13-mer databases)
- **Unique k-mers**: ~31M+ (similar to 13-mers but with larger keys)
- **Query throughput**: 15,000-20,000 queries/sec (slower than 13-mers due to larger keys)
- **Memory usage**: 2-4GB for comfortable processing
- **Multi-threading benefit**: Expected to be minimal (similar to 13-mer results)

### Property-Based Testing Requirements
**Decision**: Implement focused property-based testing for 21-mer operations using Rust's `proptest` crate.

**Rationale**: 21-mers have larger search spaces and more complex memory access patterns. Property-based testing ensures algorithmic correctness across diverse genomic sequences and edge cases.

**Test Coverage**:
- Hash function consistency across 21-mer encoding
- Binary search correctness with larger keys
- Thread safety validation for concurrent database access
- Memory usage bounds validation
- Edge case handling for boundary conditions

## Sources and References

- [Jellyfish Documentation](https://github.com/gmarcais/Jellyfish)
- [RustKmer Codebase Analysis](/Users/forrest/GitHub/rustkmer/src/)
- [Unix time command documentation](https://man7.org/linux/man-pages/man1/time.1.html)
- [Bioinformatics benchmarking best practices](https://bioinformatics.org/benchmarking/)
- [OSA1 r7 assembly documentation](https://www.ncbi.nlm.nih.gov/assembly/GCF_000002315.4/)
- [13-mer Performance Results](/Users/forrest/Temp/demodata/test_runs/osa1_performance_test/PERFORMANCE_COMPARISON_SUMMARY.md)