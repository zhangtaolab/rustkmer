# Quickstart Guide: CLI-Python API Compatibility Testing

**Purpose**: Get started with comprehensive compatibility testing between RustKmer CLI and Python API

## Prerequisites

- RustKmer CLI built and available at `./target/release/rustkmer` or in PATH
- Python 3.10+ with RustKmer Python bindings installed
- Test data available at `/Users/forrest/Temp/demodata/`
- pytest framework installed (`pip install pytest`)

## Quick Test Example

### 1. Run Basic Compatibility Test

```bash
# Navigate to project root
cd /Users/forrest/GitHub/rustkmer

# Run a single compatibility test
python3 -c "
from rustkmer import KmerCounter
from tests.python.compatibility.cli_comparator import CLICompatibilityTester

# Create counter
counter = KmerCounter(k=31)

# Count k-mers from real data
counter.count_file('/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa')
python_count = counter.get_total_count()

# Run equivalent CLI command
tester = CLICompatibilityTester()
ret_code, cli_output, _ = tester.run_cli_command([
    'count',
    '-k', '31',
    '/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa'
])

print(f'Python API count: {python_count}')
print(f'CLI output: {cli_output.strip()}')
print(f'Results match: {python_count == int(cli_output.split()[0])}')
"
```

### 2. Test with FASTQ Data

```python
from rustkmer import KmerCounter
import os

# Test with FASTQ file
test_file = '/Users/forrest/Temp/demodata/fastq/mrna_miR5794_rep1_pair1.fq.gz'
if os.path.exists(test_file):
    counter = KmerCounter(k=21)
    counter.count_file(test_file)
    print(f"Total k-mers (k=21): {counter.get_total_count()}")
    print(f"Unique k-mers: {counter.get_unique_count()}")
```

### 3. Test Database Operations

```python
from rustkmer import Database
import os

# Test with existing RKDB file
rkdb_file = '/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb'
if os.path.exists(rkdb_file):
    # Load database
    db = Database.load(rkdb_file)

    # Query specific k-mer
    count = db.query('ATCGATCGATCGATCGATCGATC')
    print(f"K-mer count: {count}")

    # Get database stats
    stats = db.get_stats()
    print(f"Database stats: {stats}")
```

## Running Full Compatibility Test Suite

### Using the Test Runner

```bash
# Run all compatibility tests
python3 tests/python/compatibility/runner.py \
    --test-data-path /Users/forrest/Temp/demodata \
    --output-path /Users/forrest/Temp/demodata/test_reports \
    --verbose

# Run specific test categories
python3 tests/python/compatibility/runner.py \
    --categories count,query \
    --test-data-path /Users/forrest/Temp/demodata

# Run performance benchmarks
python3 tests/python/compatibility/runner.py \
    --benchmark \
    --data-sizes small,medium,large
```

### Using pytest

```bash
# Run all compatibility tests
pytest tests/python/compatibility/ -v

# Run with specific test data
pytest tests/python/compatibility/ -v \
    --test-data-path=/Users/forrest/Temp/demodata

# Generate HTML report
pytest tests/python/compatibility/ \
    --html=/Users/forrest/Temp/demodata/test_reports/compatibility_report.html
```

## Test Data Organization

### Available Test Data

```
/Users/forrest/Temp/demodata/
├── fasta/
│   ├── osa1_r7.asm.fa          # Assembly file
│   └── osa1_r7.asm.fa.gz      # Compressed version
├── fastq/
│   ├── mrna_miR5794_rep1_pair1.fq.gz
│   ├── mrna_miR5794_rep1_pair2.fq.gz
│   ├── mrna_miR5794_rep2_pair1.fq.gz
│   ├── mrna_miR5794_rep2_pair2.fq.gz
│   ├── mrna_miR5794_rep3_pair1.fq.gz
│   ├── mrna_miR5794_rep3_pair2.fq.gz
│   └── split/                   # Split files
│       ├── *.part_*.fq.gz
│       ├── *.part_*.rkdb
│       └── merged.rkdb
├── intermediate/               # Created during tests
│   ├── test_outputs/
│   ├── temp_databases/
│   └── comparison_results/
└── test_reports/              # Test reports
    ├── html_reports/
    └── json_reports/
```

### Test Data Categories

1. **Small Tests**:
   - First 1000 lines of `osa1_r7.asm.fa`
   - Single part file from split directory

2. **Medium Tests**:
   - Complete `osa1_r7.asm.fa`
   - One replicate pair of FASTQ files

3. **Large Tests**:
   - All FASTQ replicates combined
   - Merge operations with split files

## Common Test Patterns

### KmerCounter vs CLI Count

```python
def test_count_compatibility():
    """Test KmerCounter.count_file() vs rustkmer count"""
    import tempfile
    from rustkmer import KmerCounter
    from tests.python.compatibility.cli_comparator import CLICompatibilityTester

    # Test parameters
    k = 31
    input_file = '/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa'

    # Python API
    counter = KmerCounter(k=k)
    counter.count_file(input_file)
    python_total = counter.get_total_count()

    # CLI command
    tester = CLICompatibilityTester()
    ret_code, cli_output, _ = tester.run_cli_command([
        'count', '-k', str(k), input_file
    ])

    cli_total = int(cli_output.split()[0])

    assert python_total == cli_total, f"Python: {python_total}, CLI: {cli_total}"
```

### Database vs CLI Query

```python
def test_query_compatibility():
    """Test Database.query() vs rustkmer query"""
    from rustkmer import Database
    from tests.python.compatibility.cli_comparator import CLICompatibilityTester

    # Test parameters
    db_path = '/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb'
    query_seq = 'ATCGATCGATCGATCGATCGATC'

    # Python API
    db = Database.load(db_path)
    python_count = db.query(query_seq)

    # CLI command
    tester = CLICompatibilityTester()
    ret_code, cli_output, _ = tester.run_cli_command([
        'query', db_path, query_seq
    ])

    cli_count = int(cli_output.strip())

    assert python_count == cli_count, f"Python: {python_count}, CLI: {cli_count}"
```

## Performance Testing

### Benchmarking Individual Operations

```python
import time
import subprocess
from rustkmer import KmerCounter

def benchmark_count_operation():
    """Benchmark counting operation"""
    test_file = '/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa'

    # Python API benchmark
    start = time.time()
    counter = KmerCounter(k=31)
    counter.count_file(test_file)
    python_time = time.time() - start

    # CLI benchmark
    start = time.time()
    result = subprocess.run([
        './target/release/rustkmer', 'count', '-k', '31', test_file
    ], capture_output=True, text=True)
    cli_time = time.time() - start

    ratio = python_time / cli_time
    print(f"Python time: {python_time:.3f}s")
    print(f"CLI time: {cli_time:.3f}s")
    print(f"Ratio (Python/CLI): {ratio:.2f}")

    # Check performance threshold (Python should be <= 110% of CLI)
    assert ratio <= 1.10, f"Performance regression: ratio={ratio:.2f}"
```

## Troubleshooting

### Common Issues

1. **File not found errors**:
   ```python
   import os
   if not os.path.exists('/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa'):
       print("Test data not found. Check /Users/forrest/Temp/demodata/ directory")
   ```

2. **CLI not in PATH**:
   ```bash
   export PATH=$PATH:/Users/forrest/GitHub/rustkmer/target/release
   ```

3. **Permission errors**:
   ```bash
   chmod -R 755 /Users/forrest/Temp/demodata
   ```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug output in compatibility tests
tester = CLICompatibilityTester(debug=True)
```

## Next Steps

1. Run basic compatibility tests to verify setup
2. Execute full test suite for comprehensive coverage
3. Review performance benchmarks
4. Generate HTML reports for detailed analysis
5. Investigate any failed tests and fix issues

## Additional Resources

- [RustKmer Documentation](https://github.com/yourorg/rustkmer/docs)
- [Python API Reference](python/rustkmer/README.md)
- [CLI Manual](rustkmer --help)