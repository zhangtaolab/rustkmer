# Implementation Tasks: Comprehensive CLI-Python API Compatibility Testing

**Branch**: `012-python-bindings-complete` | **Date**: 2025-12-09 | **Spec**: [plan.md](plan.md)
**Total Tasks**: 30 | **Priority Distribution**: P1 (10), P2 (12), P3 (8)

## Task Summary

### Phase 1: Foundation Setup (T001-T005)
**Goal**: Establish test infrastructure and data management for `/Users/forrest/Temp/demodata`

### Phase 2: Core API Testing (T006-T015)
**Goal**: Implement compatibility tests for KmerCounter and Database operations

### Phase 3: Advanced Feature Testing (T016-T025)
**Goal**: Test fuzzy queries, statistics, merging, and dump operations

### Phase 4: Cross-Cutting Concerns (T026-T030)
**Goal**: Performance benchmarking, error handling, and comprehensive reporting

---

## Phase 1: Foundation Setup

### T001: Set Up Test Infrastructure for /Users/forrest/Temp/demodata ✅ COMPLETED
**Priority**: P1 | **Estimated**: 4 hours | **Dependencies**: None

**Acceptance Criteria**:
- [X] Create directory structure in `/Users/forrest/Temp/demodata/intermediate/`
- [X] Create `/Users/forrest/Temp/demodata/test_reports/` with subdirectories
- [X] Set up test configuration management
- [X] Verify all test data paths are accessible

**Implementation Details**:
```python
# tests/python/compatibility/test_data_manager.py
class DemodataManager:
    """Manages test data from /Users/forrest/Temp/demodata"""

    def __init__(self):
        self.base_path = Path("/Users/forrest/Temp/demodata")
        self.intermediate_path = self.base_path / "intermediate"
        self.reports_path = self.base_path / "test_reports"

    def setup_directories(self):
        # Create intermediate directories
        (self.intermediate_path / "test_outputs").mkdir(parents=True, exist_ok=True)
        (self.intermediate_path / "temp_databases").mkdir(parents=True, exist_ok=True)
        (self.intermediate_path / "comparison_results").mkdir(parents=True, exist_ok=True)

        # Create report directories
        (self.reports_path / "html_reports").mkdir(parents=True, exist_ok=True)
        (self.reports_path / "json_reports").mkdir(parents=True, exist_ok=True)
```

**Files to Create**:
- `tests/python/compatibility/test_data_manager.py`
- `tests/python/compatibility/config.py`

**Validation**:
```bash
# Run directory setup test
python3 -c "from tests.python.compatibility.test_data_manager import DemodataManager; DemodataManager().setup_directories(); print('Setup complete')"
```

---

### T002: Enhance cli_comparator.py for Real Data Support ✅ COMPLETED
**Priority**: P1 | **Estimated**: 3 hours | **Dependencies**: T001

**Acceptance Criteria**:
- [X] Extend CLICompatibilityTester to handle real file paths
- [X] Add support for compressed file formats (.gz)
- [X] Implement proper error handling for missing test data
- [X] Add test data validation methods

**Implementation Details**:
```python
# tests/python/compatibility/cli_comparator.py (enhancements)
class CLICompatibilityTester:
    def __init__(self, cli_path=None, test_data_base="/Users/forrest/Temp/demodata"):
        self.cli_path = cli_path or self._find_cli_path()
        self.test_data_base = Path(test_data_base)

    def validate_test_file(self, file_path: str) -> bool:
        """Validate test file exists and is readable"""
        path = self.test_data_base / file_path
        return path.exists() and path.is_file()

    def run_cli_with_real_data(self, command: List[str], input_file: str) -> Tuple[int, str, str]:
        """Run CLI command with real test data"""
        if not self.validate_test_file(input_file):
            raise FileNotFoundError(f"Test data not found: {input_file}")
        # ... implementation
```

**Files to Modify**:
- `tests/python/compatibility/cli_comparator.py`

**Validation**:
```bash
# Test enhanced CLI comparator
python3 -m pytest tests/python/compatibility/test_cli_comparator_enhancements.py -v
```

---

### T003: Create Performance Measurement Utilities ✅ COMPLETED
**Priority**: P2 | **Estimated**: 3 hours | **Dependencies**: T001

**Acceptance Criteria**:
- [X] Implement PerformanceComparator class
- [X] Support multiple measurement runs with statistical analysis
- [X] Memory usage tracking via psutil
- [X] Generate performance comparison reports

**Implementation Details**:
```python
# tests/python/compatibility/performance_comparator.py
class PerformanceComparator:
    """Compare performance between Python API and CLI"""

    def __init__(self, runs: int = 5):
        self.runs = runs
        self.results = []

    def measure_python_api(self, func, *args, **kwargs) -> PerformanceData:
        """Measure Python API performance"""
        times = []
        memory_usage = []

        for _ in range(self.runs):
            start = time.time()
            start_mem = psutil.Process().memory_info().rss

            result = func(*args, **kwargs)

            end = time.time()
            end_mem = psutil.Process().memory_info().rss

            times.append((end - start) * 1000)  # Convert to ms
            memory_usage.append((end_mem - start_mem) / 1024 / 1024)  # Convert to MB

        return PerformanceData(times, memory_usage)
```

**Files to Create**:
- `tests/python/compatibility/performance_comparator.py`
- `tests/python/compatibility/data_models.py`

**Validation**:
```bash
# Test performance measurement
python3 -m pytest tests/python/compatibility/test_performance_comparator.py -v
```

---

### T004: Implement Test Data Validators ✅ COMPLETED
**Priority**: P2 | **Estimated**: 2 hours | **Dependencies**: T001

**Acceptance Criteria**:
- [X] Validate FASTA files in `/Users/forrest/Temp/demodata/fasta/`
- [X] Validate FASTQ files in `/Users/forrest/Temp/demodata/fastq/`
- [X] Validate existing RKDB files in `/Users/forrest/Temp/demodata/fastq/split/`
- [X] Generate test data inventory report

**Implementation Details**:
```python
# tests/python/compatibility/test_data/validators.py
class TestDataValidator:
    """Validates test data integrity"""

    def validate_fasta(self, file_path: Path) -> ValidationResult:
        """Validate FASTA file format"""
        # Check file exists, readable, valid FASTA format
        pass

    def validate_fastq(self, file_path: Path) -> ValidationResult:
        """Validate FASTQ file format"""
        # Check file exists, readable, valid FASTQ format
        pass

    def generate_inventory(self) -> TestDataInventory:
        """Generate test data inventory"""
        inventory = TestDataInventory()
        # Scan /Users/forrest/Temp/demodata and populate inventory
        return inventory
```

**Files to Create**:
- `tests/python/compatibility/test_data/validators.py`
- `tests/python/compatibility/test_data/inventory.py`

**Validation**:
```bash
# Run test data validation
python3 tests/python/compatibility/test_data/validate_all.py
```

---

### T005: Create Comprehensive Test Runner
**Priority**: P1 | **Estimated**: 4 hours | **Dependencies**: T001-T004

**Acceptance Criteria**:
- [ ] Unified test runner for all compatibility tests
- [ ] Support for running specific test categories
- [ ] Progress reporting and test result aggregation
- [ ] Export results to JSON/HTML formats

**Implementation Details**:
```python
# tests/python/compatibility/comprehensive_test_runner.py
class ComprehensiveTestRunner:
    """Unified test runner for all compatibility tests"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.data_manager = DemodataManager()
        self.cli_tester = CLICompatibilityTester()
        self.perf_comparator = PerformanceComparator()

    def run_all_tests(self) -> CompatibilityTestSuite:
        """Run all compatibility tests"""
        suite = CompatibilityTestSuite()

        # Run Phase 2 tests
        suite.add_results(self.run_phase2_tests())

        # Run Phase 3 tests
        suite.add_results(self.run_phase3_tests())

        # Run Phase 4 tests
        suite.add_results(self.run_phase4_tests())

        return suite

    def generate_report(self, suite: CompatibilityTestSuite, format: str = "html"):
        """Generate compatibility test report"""
        if format == "html":
            return HTMLReportGenerator().generate(suite)
        elif format == "json":
            return JSONReportGenerator().generate(suite)
```

**Files to Create**:
- `tests/python/compatibility/comprehensive_test_runner.py`
- `tests/python/compatibility/reporting/html_generator.py`
- `tests/python/compatibility/reporting/json_generator.py`

**Validation**:
```bash
# Test comprehensive runner
python3 tests/python/compatibility/comprehensive_test_runner.py --categories small,medium --verbose
```

---

## Phase 2: Core API Testing

### T006: Test KmerCounter with FASTA Files
**Priority**: P1 | **Estimated**: 3 hours | **Dependencies**: T001-T002

**Acceptance Criteria**:
- [ ] Test `count_file()` vs `rustkmer count` with `/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa`
- [ ] Test both compressed and uncompressed FASTA files
- [ ] Verify exact count matches
- [ ] Test different k-mer sizes (k=21, 31, 51)

**Implementation Details**:
```python
# tests/python/compatibility/test_kmer_counter_fasta.py
class TestKmerCounterFASTA:
    """Test KmerCounter compatibility with FASTA files"""

    def test_count_file_osa1_r7(self):
        """Test count_file() vs rustkmer count with osa1_r7.asm.fa"""
        fasta_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"

        # Python API
        counter = KmerCounter(k=31)
        counter.count_file(fasta_file)
        python_total = counter.get_total_count()

        # CLI
        tester = CLICompatibilityTester()
        ret_code, cli_output, _ = tester.run_cli_command([
            'count', '-k', '31', fasta_file
        ])

        cli_total = int(cli_output.split()[0])
        assert python_total == cli_total
```

**Files to Create**:
- `tests/python/compatibility/test_kmer_counter_fasta.py`

**Validation**:
```bash
# Run FASTA compatibility tests
python3 -m pytest tests/python/compatibility/test_kmer_counter_fasta.py -v
```

---

### T007: Test KmerCounter with FASTQ Files
**Priority**: P1 | **Estimated**: 3 hours | **Dependencies**: T001-T002

**Acceptance Criteria**:
- [ ] Test `count_file()` with all FASTQ files in `/Users/forrest/Temp/demodata/fastq/`
- [ ] Handle paired-end read files correctly
- [ ] Test compressed FASTQ (.fq.gz) files
- [ ] Validate k-mer counts for each replicate

**Implementation Details**:
```python
# tests/python/compatibility/test_kmer_counter_fastq.py
class TestKmerCounterFASTQ:
    """Test KmerCounter compatibility with FASTQ files"""

    @pytest.mark.parametrize("fastq_file", [
        "mrna_miR5794_rep1_pair1.fq.gz",
        "mrna_miR5794_rep1_pair2.fq.gz",
        "mrna_miR5794_rep2_pair1.fq.gz",
        "mrna_miR5794_rep2_pair2.fq.gz",
        "mrna_miR5794_rep3_pair1.fq.gz",
        "mrna_miR5794_rep3_pair2.fq.gz"
    ])
    def test_count_file_fastq_replicates(self, fastq_file):
        """Test count_file() with each FASTQ replicate"""
        fastq_path = f"/Users/forrest/Temp/demodata/fastq/{fastq_file}"

        # Python API
        counter = KmerCounter(k=31)
        counter.count_file(fastq_path)
        python_result = {
            'total': counter.get_total_count(),
            'unique': counter.get_unique_count()
        }

        # CLI
        tester = CLICompatibilityTester()
        ret_code, cli_output, _ = tester.run_cli_command([
            'count', '-k', '31', fastq_path
        ])

        # Parse CLI output and compare
        cli_parts = cli_output.split()
        cli_result = {
            'total': int(cli_parts[0]),
            'unique': int(cli_parts[1]) if len(cli_parts) > 1 else None
        }

        assert python_result['total'] == cli_result['total']
```

**Files to Create**:
- `tests/python/compatibility/test_kmer_counter_fastq.py`

**Validation**:
```bash
# Run FASTQ compatibility tests
python3 -m pytest tests/python/compatibility/test_kmer_counter_fastq.py -v
```

---

### T008: Test Database Query Operations
**Priority**: P1 | **Estimated**: 3 hours | **Dependencies**: T001-T002

**Acceptance Criteria**:
- [ ] Test `Database.query()` vs `rustkmer query` with existing RKDB files
- [ ] Use databases from `/Users/forrest/Temp/demodata/fastq/split/`
- [ ] Test with various k-mer sequences
- [ ] Validate exact count matches

**Implementation Details**:
```python
# tests/python/compatibility/test_database_query.py
class TestDatabaseQuery:
    """Test Database query compatibility"""

    @pytest.mark.parametrize("rkdb_file", [
        "mrna_miR5794_rep1_pair1.part_001.rkdb",
        "mrna_miR5794_rep1_pair1.part_002.rkdb",
        # Add more RKDB files as needed
    ])
    def test_database_vs_cli_query(self, rkdb_file):
        """Test Database.query() vs rustkmer query"""
        rkdb_path = f"/Users/forrest/Temp/demodata/fastq/split/{rkdb_file}"

        if not Path(rkdb_path).exists():
            pytest.skip(f"RKDB file not found: {rkdb_file}")

        # Test sequences
        test_sequences = [
            "ATCGATCGATCGATCGATCGATC",
            "GCTAGCTAGCTAGCTAGCTAGCT",
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAACG"
        ]

        # Load database in Python
        db = Database.load(rkdb_path)

        tester = CLICompatibilityTester()

        for seq in test_sequences:
            # Python API
            python_count = db.query(seq)

            # CLI
            ret_code, cli_output, _ = tester.run_cli_command([
                'query', rkdb_path, seq
            ])

            cli_count = int(cli_output.strip())

            assert python_count == cli_count, f"Sequence: {seq}, Python: {python_count}, CLI: {cli_count}"
```

**Files to Create**:
- `tests/python/compatibility/test_database_query.py`

**Validation**:
```bash
# Run database query compatibility tests
python3 -m pytest tests/python/compatibility/test_database_query.py -v
```

---

### T009: Test Database Saving Functionality
**Priority**: P2 | **Estimated**: 2 hours | **Dependencies**: T006, T007

**Acceptance Criteria**:
- [ ] Test `save_to_database()` vs `rustkmer count -o`
- [ ] Compare saved database properties
- [ ] Verify databases are loadable by both Python and CLI
- [ ] Use intermediate directory for test databases

**Implementation Details**:
```python
# tests/python/compatibility/test_database_save.py
class TestDatabaseSave:
    """Test database saving compatibility"""

    def test_save_to_database_vs_cli(self):
        """Test save_to_database() vs rustkmer count -o"""
        input_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"

        # Python API - save database
        python_db_path = "/Users/forrest/Temp/demodata/intermediate/temp_databases/python_saved.rkdb"
        counter = KmerCounter(k=31)
        counter.count_file(input_file)
        counter.save_to_database(python_db_path)

        # CLI - save database
        cli_db_path = "/Users/forrest/Temp/demodata/intermediate/temp_databases/cli_saved.rkdb"
        tester = CLICompatibilityTester()
        ret_code, _, _ = tester.run_cli_command([
            'count', '-k', '31', '-o', cli_db_path, input_file
        ])

        assert ret_code == 0

        # Compare databases
        python_db = Database.load(python_db_path)
        cli_db = Database.load(cli_db_path)

        # Get stats from both
        python_stats = python_db.get_stats()
        cli_stats = cli_db.get_stats()

        assert python_stats.total_kmers == cli_stats.total_kmers
        assert python_stats.unique_kmers == cli_stats.unique_kmers
        assert python_stats.kmer_size == cli_stats.kmer_size
```

**Files to Create**:
- `tests/python/compatibility/test_database_save.py`

**Validation**:
```bash
# Run database save compatibility tests
python3 -m pytest tests/python/compatibility/test_database_save.py -v
```

---

### T010: Test Multiple Query Operations
**Priority**: P2 | **Estimated**: 2 hours | **Dependencies**: T008

**Acceptance Criteria**:
- [ ] Test `query_multiple()` method
- [ ] Compare with multiple CLI query invocations
- [ ] Validate all query results match
- [ ] Test with different database files

**Implementation Details**:
```python
# tests/python/compatibility/test_multiple_query.py
class TestMultipleQuery:
    """Test multiple query operations"""

    def test_query_multiple_vs_cli(self):
        """Test query_multiple() vs multiple CLI queries"""
        rkdb_path = "/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb"

        if not Path(rkdb_path).exists():
            pytest.skip(f"RKDB file not found: {rkdb_path}")

        test_sequences = [
            "ATCGATCGATCGATCGATCGATC",
            "GCTAGCTAGCTAGCTAGCTAGCT",
            "TTTTTTTTTTTTTTTTTTTTTTT"
        ]

        # Python API
        db = Database.load(rkdb_path)
        python_results = db.query_multiple(test_sequences)

        # CLI
        tester = CLICompatibilityTester()
        cli_results = []

        for seq in test_sequences:
            ret_code, cli_output, _ = tester.run_cli_command([
                'query', rkdb_path, seq
            ])
            cli_results.append(int(cli_output.strip()))

        # Compare results
        for i, seq in enumerate(test_sequences):
            assert python_results[i] == cli_results[i], f"Sequence {i}: {seq}"
```

**Files to Create**:
- `tests/python/compatibility/test_multiple_query.py`

**Validation**:
```bash
# Run multiple query compatibility tests
python3 -m pytest tests/python/compatibility/test_multiple_query.py -v
```

---

### T011: Test KmerCounter Parameter Variations
**Priority**: P2 | **Estimated**: 2 hours | **Dependencies**: T006, T007

**Acceptance Criteria**:
- [ ] Test different k-mer sizes (k=21, 31, 51)
- [ ] Test canonical vs non-canonical counting
- [ ] Test multi-threading options
- [ ] Verify parameter consistency between Python and CLI

**Implementation Details**:
```python
# tests/python/compatibility/test_kmer_counter_params.py
class TestKmerCounterParameters:
    """Test KmerCounter parameter variations"""

    @pytest.mark.parametrize("k_size", [21, 31, 51])
    @pytest.mark.parametrize("canonical", [True, False])
    def test_kmer_size_and_canonical(self, k_size, canonical):
        """Test different k-mer sizes and canonical mode"""
        input_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"

        # Python API
        counter = KmerCounter(k=k_size, canonical=canonical)
        counter.count_file(input_file)
        python_total = counter.get_total_count()

        # CLI
        tester = CLICompatibilityTester()
        cli_args = ['count', '-k', str(k_size)]
        if canonical:
            cli_args.append('--canonical')
        cli_args.append(input_file)

        ret_code, cli_output, _ = tester.run_cli_command(cli_args)
        cli_total = int(cli_output.split()[0])

        assert python_total == cli_total
```

**Files to Create**:
- `tests/python/compatibility/test_kmer_counter_params.py`

**Validation**:
```bash
# Run parameter variation tests
python3 -m pytest tests/python/compatibility/test_kmer_counter_params.py -v
```

---

### T012: Test String Input Counting
**Priority**: P2 | **Estimated**: 1 hour | **Dependencies**: None

**Acceptance Criteria**:
- [ ] Test `count_string()` method
- [ ] Compare with CLI using temporary FASTA files
- [ ] Test various sequence formats and edge cases
- [ ] Validate count accuracy

**Implementation Details**:
```python
# tests/python/compatibility/test_count_string.py
class TestCountString:
    """Test count_string() compatibility"""

    def test_count_string_vs_cli(self):
        """Test count_string() vs CLI with temp FASTA"""
        test_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCG"

        # Python API
        counter = KmerCounter(k=7)
        counter.count_string(test_sequence)
        python_total = counter.get_total_count()

        # Create temporary FASTA for CLI
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(f">test_sequence\n{test_sequence}\n")
            temp_file = f.name

        try:
            # CLI
            tester = CLICompatibilityTester()
            ret_code, cli_output, _ = tester.run_cli_command([
                'count', '-k', '7', temp_file
            ])
            cli_total = int(cli_output.split()[0])

            assert python_total == cli_total
        finally:
            os.unlink(temp_file)
```

**Files to Create**:
- `tests/python/compatibility/test_count_string.py`

**Validation**:
```bash
# Run count string compatibility tests
python3 -m pytest tests/python/compatibility/test_count_string.py -v
```

---

### T013: Test Error Handling for KmerCounter
**Priority**: P3 | **Estimated**: 2 hours | **Dependencies**: T006, T007

**Acceptance Criteria**:
- [ ] Test invalid file paths
- [ ] Test invalid k-mer sizes
- [ ] Test corrupted/malformed files
- [ ] Compare error messages and exception types

**Implementation Details**:
```python
# tests/python/compatibility/test_kmer_counter_errors.py
class TestKmerCounterErrors:
    """Test KmerCounter error handling"""

    def test_invalid_file_path(self):
        """Test error handling for invalid file paths"""
        invalid_file = "/Users/forrest/Temp/demodata/nonexistent/file.fa"

        # Python API
        counter = KmerCounter(k=31)
        with pytest.raises(FileNotFoundError):
            counter.count_file(invalid_file)

        # CLI
        tester = CLICompatibilityTester()
        ret_code, cli_output, cli_error = tester.run_cli_command([
            'count', '-k', '31', invalid_file
        ])

        assert ret_code != 0
        assert "No such file" in cli_error or "not found" in cli_error.lower()
```

**Files to Create**:
- `tests/python/compatibility/test_kmer_counter_errors.py`

**Validation**:
```bash
# Run error handling tests
python3 -m pytest tests/python/compatibility/test_kmer_counter_errors.py -v
```

---

### T014: Test Large File Performance
**Priority**: P2 | **Estimated**: 3 hours | **Dependencies**: T003, T006, T007

**Acceptance Criteria**:
- [ ] Measure performance with large FASTA/FASTQ files
- [ ] Python API ≤ 110% of CLI execution time
- [ ] Memory usage ≤ 105% of CLI baseline
- [ ] Generate performance comparison report

**Implementation Details**:
```python
# tests/python/compatibility/test_large_file_performance.py
class TestLargeFilePerformance:
    """Test performance with large files"""

    def test_performance_osa1_r7(self):
        """Benchmark performance with osa1_r7.asm.fa"""
        input_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"

        perf_comp = PerformanceComparator(runs=3)

        # Python API benchmark
        def python_count():
            counter = KmerCounter(k=31)
            counter.count_file(input_file)
            return counter.get_total_count()

        python_perf = perf_comp.measure_python_api(python_count)

        # CLI benchmark
        def cli_count():
            tester = CLICompatibilityTester()
            ret_code, cli_output, _ = tester.run_cli_command([
                'count', '-k', '31', input_file
            ])
            return int(cli_output.split()[0])

        cli_perf = perf_comp.measure_cli_command(cli_count)

        # Compare performance
        ratio = python_perf.mean_time / cli_perf.mean_time
        assert ratio <= 1.10, f"Performance regression: Python/CLI ratio = {ratio:.2f}"

        # Generate report
        report = perf_comp.generate_comparison_report(python_perf, cli_perf)
        report.save("/Users/forrest/Temp/demodata/test_reports/performance_osa1_r7.json")
```

**Files to Create**:
- `tests/python/compatibility/test_large_file_performance.py`

**Validation**:
```bash
# Run performance tests
python3 -m pytest tests/python/compatibility/test_large_file_performance.py -v -s
```

---

### T015: Test Database Load Performance
**Priority**: P2 | **Estimated**: 2 hours | **Dependencies**: T008, T003

**Acceptance Criteria**:
- [ ] Measure database loading performance
- [ ] Test with different RKDB file sizes
- [ ] Compare memory usage between Python and CLI
- [ ] Validate loading time consistency

**Implementation Details**:
```python
# tests/python/compatibility/test_database_load_performance.py
class TestDatabaseLoadPerformance:
    """Test database loading performance"""

    def test_load_performance_comparison(self):
        """Compare Database.load() vs CLI implicit loading"""
        rkdb_files = [
            "/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb",
            # Add more files as available
        ]

        perf_comp = PerformanceComparator(runs=5)

        for rkdb_file in rkdb_files:
            if not Path(rkdb_file).exists():
                continue

            # Python API load time
            def python_load():
                return Database.load(rkdb_file)

            python_perf = perf_comp.measure_python_api(python_load)

            # CLI load time (measured via query command)
            def cli_load():
                tester = CLICompatibilityTester()
                ret_code, cli_output, _ = tester.run_cli_command([
                    'query', rkdb_file, 'ATCGATCGATCGATCGATCGATC'
                ])
                return cli_output

            cli_perf = perf_comp.measure_cli_command(cli_load)

            # Performance assertion
            ratio = python_perf.mean_time / cli_perf.mean_time
            assert ratio <= 1.10, f"Load performance regression for {rkdb_file}: ratio = {ratio:.2f}"
```

**Files to Create**:
- `tests/python/compatibility/test_database_load_performance.py`

**Validation**:
```bash
# Run database load performance tests
python3 -m pytest tests/python/compatibility/test_database_load_performance.py -v
```

---

## Phase 3: Advanced Feature Testing

### T016: Test Fuzzy Query Operations
**Priority**: P1 | **Estimated**: 3 hours | **Dependencies**: T008

**Acceptance Criteria**:
- [ ] Test `FuzzyQuery` class vs `rustkmer fuzzy-query`
- [ ] Test with different mismatch thresholds
- [ ] Validate fuzzy query results match
- [ ] Use RKDB files from split directory

**Implementation Details**:
```python
# tests/python/compatibility/test_fuzzy_query.py
class TestFuzzyQuery:
    """Test fuzzy query compatibility"""

    @pytest.mark.parametrize("max_mismatches", [0, 1, 2, 3])
    def test_fuzzy_query_vs_cli(self, max_mismatches):
        """Test FuzzyQuery vs rustkmer fuzzy-query"""
        rkdb_path = "/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb"

        if not Path(rkdb_path).exists():
            pytest.skip(f"RKDB file not found: {rkdb_path}")

        query_seq = "ATCGATCGATCGATCGATCGATC"

        # Python API
        fuzzy_query = FuzzyQuery(rkdb_path)
        python_results = fuzzy_query.query(query_seq, max_mismatches)

        # CLI
        tester = CLICompatibilityTester()
        ret_code, cli_output, _ = tester.run_cli_command([
            'fuzzy-query', '-m', str(max_mismatches), rkdb_path, query_seq
        ])

        # Parse CLI output
        cli_results = []
        for line in cli_output.strip().split('\n'):
            if line:
                parts = line.split('\t')
                cli_results.append({
                    'sequence': parts[0],
                    'count': int(parts[1]),
                    'mismatches': int(parts[2])
                })

        # Compare results
        assert len(python_results) == len(cli_results)

        for py_result, cli_result in zip(python_results, cli_results):
            assert py_result['sequence'] == cli_result['sequence']
            assert py_result['count'] == cli_result['count']
            assert py_result['mismatches'] == cli_result['mismatches']
```

**Files to Create**:
- `tests/python/compatibility/test_fuzzy_query.py`

**Validation**:
```bash
# Run fuzzy query compatibility tests
python3 -m pytest tests/python/compatibility/test_fuzzy_query.py -v
```

---

### T017: Test Database Statistics
**Priority**: P1 | **Estimated**: 2 hours | **Dependencies**: T008

**Acceptance Criteria**:
- [ ] Test `Database.get_stats()` vs `rustkmer stats`
- [ ] Test with all RKDB files in split directory
- [ ] Validate all statistics match exactly
- [ ] Test stats output format consistency

**Implementation Details**:
```python
# tests/python/compatibility/test_database_stats.py
class TestDatabaseStats:
    """Test database statistics compatibility"""

    def test_stats_vs_cli(self):
        """Test Database.get_stats() vs rustkmer stats"""
        rkdb_files = [
            "mrna_miR5794_rep1_pair1.part_001.rkdb",
            "mrna_miR5794_rep1_pair1.part_002.rkdb",
            # Add all available RKDB files
        ]

        tester = CLICompatibilityTester()

        for rkdb_file in rkdb_files:
            rkdb_path = f"/Users/forrest/Temp/demodata/fastq/split/{rkdb_file}"

            if not Path(rkdb_path).exists():
                continue

            # Python API
            db = Database.load(rkdb_path)
            python_stats = db.get_stats()

            # CLI
            ret_code, cli_output, _ = tester.run_cli_command([
                'stats', rkdb_path
            ])

            # Parse CLI output
            cli_lines = [line.strip() for line in cli_output.split('\n') if line.strip()]
            cli_stats = {}
            for line in cli_lines:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    cli_stats[key] = value

            # Compare statistics
            assert str(python_stats.total_kmers) == cli_stats.get('Total k-mers')
            assert str(python_stats.unique_kmers) == cli_stats.get('Unique k-mers')
            assert str(python_stats.kmer_size) == cli_stats.get('K-mer size')
            assert python_stats.canonical == (cli_stats.get('Canonical mode') == 'Yes')
```

**Files to Create**:
- `tests/python/compatibility/test_database_stats.py`

**Validation**:
```bash
# Run database stats compatibility tests
python3 -m pytest tests/python/compatibility/test_database_stats.py -v
```

---

### T018: Test Database Merge Operations
**Priority**: P1 | **Estimated**: 4 hours | **Dependencies**: T008, T017

**Acceptance Criteria**:
- [ ] Test `DatabaseMerger.merge_databases()` vs `rustkmer merge`
- [ ] Use split files from `/Users/forrest/Temp/demodata/fastq/split/`
- [ ] Compare merged database properties
- [ ] Validate merge results are identical

**Implementation Details**:
```python
# tests/python/compatibility/test_database_merge.py
class TestDatabaseMerge:
    """Test database merge compatibility"""

    def test_merge_vs_cli(self):
        """Test DatabaseMerger vs rustkmer merge"""
        # Find all part_*.rkdb files for one replicate
        split_dir = Path("/Users/forrest/Temp/demodata/fastq/split")
        rkdb_files = sorted(split_dir.glob("mrna_miR5794_rep1_pair1.part_*.rkdb"))

        if len(rkdb_files) < 2:
            pytest.skip("Need at least 2 RKDB files for merge test")

        # Python API merge
        python_merge_path = "/Users/forrest/Temp/demodata/intermediate/temp_databases/python_merged.rkdb"
        merger = DatabaseMerger()
        merger.merge_databases([str(f) for f in rkdb_files], python_merge_path)

        # CLI merge
        cli_merge_path = "/Users/forrest/Temp/demodata/intermediate/temp_databases/cli_merged.rkdb"
        tester = CLICompatibilityTester()
        merge_args = ['merge']
        merge_args.extend([str(f) for f in rkdb_files])
        merge_args.extend(['-o', cli_merge_path])

        ret_code, _, _ = tester.run_cli_command(merge_args)
        assert ret_code == 0

        # Compare merged databases
        python_db = Database.load(python_merge_path)
        cli_db = Database.load(cli_merge_path)

        python_stats = python_db.get_stats()
        cli_stats = cli_db.get_stats()

        assert python_stats.total_kmers == cli_stats.total_kmers
        assert python_stats.unique_kmers == cli_stats.unique_kmers
        assert python_stats.kmer_size == cli_stats.kmer_size
```

**Files to Create**:
- `tests/python/compatibility/test_database_merge.py`

**Validation**:
```bash
# Run database merge compatibility tests
python3 -m pytest tests/python/compatibility/test_database_merge.py -v
```

---

### T019: Test Database Dump Operations
**Priority**: P1 | **Estimated**: 3 hours | **Dependencies**: T008

**Acceptance Criteria**:
- [ ] Test `Database.dump()` vs `rustkmer dump`
- [ ] Validate dump output format consistency
- [ ] Compare dumped k-mer counts
- [ ] Test with different output formats

**Implementation Details**:
```python
# tests/python/compatibility/test_database_dump.py
class TestDatabaseDump:
    """Test database dump compatibility"""

    def test_dump_vs_cli(self):
        """Test Database.dump() vs rustkmer dump"""
        rkdb_path = "/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb"

        if not Path(rkdb_path).exists():
            pytest.skip(f"RKDB file not found: {rkdb_path}")

        # Python API dump
        python_dump_path = "/Users/forrest/Temp/demodata/intermediate/test_outputs/python_dump.txt"
        db = Database.load(rkdb_path)
        db.dump(python_dump_path)

        # CLI dump
        cli_dump_path = "/Users/forrest/Temp/demodata/intermediate/test_outputs/cli_dump.txt"
        tester = CLICompatibilityTester()
        ret_code, _, _ = tester.run_cli_command([
            'dump', rkdb_path, cli_dump_path
        ])

        assert ret_code == 0

        # Compare dump files
        python_lines = set()
        with open(python_dump_path) as f:
            for line in f:
                if line.strip():
                    seq, count = line.strip().split('\t')
                    python_lines.add((seq, int(count)))

        cli_lines = set()
        with open(cli_dump_path) as f:
            for line in f:
                if line.strip():
                    seq, count = line.strip().split('\t')
                    cli_lines.add((seq, int(count)))

        assert python_lines == cli_lines
```

**Files to Create**:
- `tests/python/compatibility/test_database_dump.py`

**Validation**:
```bash
# Run database dump compatibility tests
python3 -m pytest tests/python/compatibility/test_database_dump.py -v
```

---

### T020: Test Concurrent Database Access
**Priority**: P3 | **Estimated**: 3 hours | **Dependencies**: T008

**Acceptance Criteria**:
- [ ] Test concurrent database queries
- [ ] Test concurrent database loading
- [ ] Verify thread safety of Python API
- [ ] Compare with concurrent CLI processes

**Implementation Details**:
```python
# tests/python/compatibility/test_concurrent_access.py
class TestConcurrentAccess:
    """Test concurrent database access"""

    def test_concurrent_queries(self):
        """Test concurrent database queries"""
        rkdb_path = "/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb"

        if not Path(rkdb_path).exists():
            pytest.skip(f"RKDB file not found: {rkdb_path}")

        test_sequences = [
            "ATCGATCGATCGATCGATCGATC",
            "GCTAGCTAGCTAGCTAGCTAGCT",
            "TTTTTTTTTTTTTTTTTTTTTTT"
        ]

        def worker_query(sequence):
            db = Database.load(rkdb_path)
            return db.query(sequence)

        # Run concurrent queries
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker_query, seq) for seq in test_sequences * 10]
            python_results = [f.result() for f in futures]

        # Verify consistency
        for i in range(0, len(python_results), len(test_sequences)):
            batch = python_results[i:i+len(test_sequences)]
            assert batch == python_results[:len(test_sequences)]
```

**Files to Create**:
- `tests/python/compatibility/test_concurrent_access.py`

**Validation**:
```bash
# Run concurrent access tests
python3 -m pytest tests/python/compatibility/test_concurrent_access.py -v
```

---

### T021: Test Database Format Compatibility
**Priority**: P2 | **Estimated**: 2 hours | **Dependencies**: T008, T019

**Acceptance Criteria**:
- [ ] Test databases created by Python API work with CLI
- [ ] Test databases created by CLI work with Python API
- [ ] Verify database format version compatibility
- [ ] Test cross-platform database compatibility

**Implementation Details**:
```python
# tests/python/compatibility/test_format_compatibility.py
class TestFormatCompatibility:
    """Test database format compatibility"""

    def test_python_created_db_cli_compatible(self):
        """Test databases created by Python API work with CLI"""
        input_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"

        # Create database with Python API
        python_db_path = "/Users/forrest/Temp/demodata/intermediate/temp_databases/python_format_test.rkdb"
        counter = KmerCounter(k=31)
        counter.count_file(input_file)
        counter.save_to_database(python_db_path)

        # Use with CLI query
        tester = CLICompatibilityTester()
        ret_code, cli_output, _ = tester.run_cli_command([
            'query', python_db_path, 'ATCGATCGATCGATCGATCGATC'
        ])

        assert ret_code == 0
        assert int(cli_output.strip()) >= 0

        # Use with CLI stats
        ret_code, stats_output, _ = tester.run_cli_command([
            'stats', python_db_path
        ])

        assert ret_code == 0
        assert 'Total k-mers' in stats_output

    def test_cli_created_db_python_compatible(self):
        """Test databases created by CLI work with Python API"""
        input_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"

        # Create database with CLI
        cli_db_path = "/Users/forrest/Temp/demodata/intermediate/temp_databases/cli_format_test.rkdb"
        tester = CLICompatibilityTester()
        ret_code, _, _ = tester.run_cli_command([
            'count', '-k', '31', '-o', cli_db_path, input_file
        ])

        assert ret_code == 0

        # Load with Python API
        db = Database.load(cli_db_path)
        count = db.query('ATCGATCGATCGATCGATCGATC')
        assert count >= 0

        stats = db.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0
```

**Files to Create**:
- `tests/python/compatibility/test_format_compatibility.py`

**Validation**:
```bash
# Run format compatibility tests
python3 -m pytest tests/python/compatibility/test_format_compatibility.py -v
```

---

### T022: Test Custom Alphabet Handling
**Priority**: P3 | **Estimated**: 2 hours | **Dependencies**: T006, T007

**Acceptance Criteria**:
- [ ] Test DNA alphabet (ACGT)
- [ ] Test RNA alphabet (ACGU)
- [ ] Test ambiguous nucleotides (N, etc.)
- [ ] Verify consistent behavior between Python and CLI

**Implementation Details**:
```python
# tests/python/compatibility/test_alphabet_handling.py
class TestAlphabetHandling:
    """Test alphabet handling compatibility"""

    def test_dna_alphabet(self):
        """Test DNA alphabet handling"""
        test_sequence = "ACGTACGTACGTACGTACGTACGT"

        # Python API
        counter = KmerCounter(k=7)
        counter.count_string(test_sequence)
        python_count = counter.get_total_count()

        # CLI with temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(f">dna_test\n{test_sequence}\n")
            temp_file = f.name

        try:
            tester = CLICompatibilityTester()
            ret_code, cli_output, _ = tester.run_cli_command([
                'count', '-k', '7', temp_file
            ])
            cli_count = int(cli_output.split()[0])

            assert python_count == cli_count
        finally:
            os.unlink(temp_file)

    def test_rna_alphabet(self):
        """Test RNA alphabet handling"""
        test_sequence = "ACGUACGUACGUACGUACGUACGU"

        # Python API
        counter = KmerCounter(k=7)
        counter.count_string(test_sequence)
        python_count = counter.get_total_count()

        # CLI with temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(f">rna_test\n{test_sequence}\n")
            temp_file = f.name

        try:
            tester = CLICompatibilityTester()
            ret_code, cli_output, _ = tester.run_cli_command([
                'count', '-k', '7', temp_file
            ])
            cli_count = int(cli_output.split()[0])

            assert python_count == cli_count
        finally:
            os.unlink(temp_file)
```

**Files to Create**:
- `tests/python/compatibility/test_alphabet_handling.py`

**Validation**:
```bash
# Run alphabet handling tests
python3 -m pytest tests/python/compatibility/test_alphabet_handling.py -v
```

---

### T023: Test Memory-Mapped Database Access
**Priority**: P2 | **Estimated**: 2 hours | **Dependencies**: T008, T015

**Acceptance Criteria**:
- [ ] Test memory-mapped database loading
- [ ] Verify memory efficiency with large databases
- [ ] Test multiple memory-mapped databases simultaneously
- [ ] Compare memory usage with regular loading

**Implementation Details**:
```python
# tests/python/compatibility/test_memory_mapped_access.py
class TestMemoryMappedAccess:
    """Test memory-mapped database access"""

    def test_memory_mapped_vs_regular_loading(self):
        """Compare memory-mapped vs regular database loading"""
        rkdb_path = "/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb"

        if not Path(rkdb_path).exists():
            pytest.skip(f"RKDB file not found: {rkdb_path}")

        # Regular loading
        start_mem = psutil.Process().memory_info().rss
        db_regular = Database.load(rkdb_path, memory_mapped=False)
        regular_mem = psutil.Process().memory_info().rss - start_mem

        # Memory-mapped loading
        start_mem = psutil.Process().memory_info().rss
        db_mmap = Database.load(rkdb_path, memory_mapped=True)
        mmap_mem = psutil.Process().memory_info().rss - start_mem

        # Both should work identically
        test_seq = "ATCGATCGATCGATCGATCGATC"
        regular_count = db_regular.query(test_seq)
        mmap_count = db_mmap.query(test_seq)

        assert regular_count == mmap_count

        # Memory-mapped should use less initial memory
        # (Note: actual memory usage may vary based on OS)
        # This is more of a smoke test
        assert mmap_mem >= 0
        assert regular_mem >= 0
```

**Files to Create**:
- `tests/python/compatibility/test_memory_mapped_access.py`

**Validation**:
```bash
# Run memory-mapped access tests
python3 -m pytest tests/python/compatibility/test_memory_mapped_access.py -v
```

---

### T024: Test Progress Reporting
**Priority**: P3 | **Estimated**: 2 hours | **Dependencies**: T014

**Acceptance Criteria**:
- [ ] Test progress reporting for large files
- [ ] Verify progress callbacks work correctly
- [ ] Compare progress output with CLI verbose mode
- [ ] Test progress cancellation

**Implementation Details**:
```python
# tests/python/compatibility/test_progress_reporting.py
class TestProgressReporting:
    """Test progress reporting compatibility"""

    def test_progress_callback(self):
        """Test progress callback functionality"""
        input_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"

        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        # Python API with progress
        counter = KmerCounter(k=31)
        counter.count_file(input_file, progress_callback=progress_callback)

        # Verify progress was reported
        assert len(progress_updates) > 0

        # Progress should be between 0 and 1
        for p in progress_updates:
            assert 0 <= p <= 1

        # Final progress should be 1.0
        assert abs(progress_updates[-1] - 1.0) < 1e-6

        # CLI verbose mode
        tester = CLICompatibilityTester()
        ret_code, cli_output, _ = tester.run_cli_command([
            'count', '-k', '31', '-v', input_file
        ])

        assert ret_code == 0
        # CLI should show progress in verbose mode
        assert '%' in cli_output or 'Progress' in cli_output
```

**Files to Create**:
- `tests/python/compatibility/test_progress_reporting.py`

**Validation**:
```bash
# Run progress reporting tests
python3 -m pytest tests/python/compatibility/test_progress_reporting.py -v -s
```

---

### T025: Test Database Version Migration
**Priority**: P3 | **Estimated**: 2 hours | **Dependencies**: T021

**Acceptance Criteria**:
- [ ] Test database version detection
- [ ] Test database upgrade/downgrade compatibility
- [ ] Verify error handling for incompatible versions
- [ ] Test version-aware CLI and Python API

**Implementation Details**:
```python
# tests/python/compatibility/test_version_migration.py
class TestVersionMigration:
    """Test database version migration"""

    def test_version_detection(self):
        """Test database version detection"""
        rkdb_path = "/Users/forrest/Temp/demodata/fastq/split/mrna_miR5794_rep1_pair1.part_001.rkdb"

        if not Path(rkdb_path).exists():
            pytest.skip(f"RKDB file not found: {rkdb_path}")

        # Python API should detect version
        db = Database.load(rkdb_path)
        assert hasattr(db, 'version')

        # CLI should handle version transparently
        tester = CLICompatibilityTester()
        ret_code, cli_output, _ = tester.run_cli_command([
            'stats', rkdb_path
        ])

        assert ret_code == 0
        # Should not have version errors
        assert 'version' not in cli_output.lower() or 'incompatible' not in cli_output.lower()
```

**Files to Create**:
- `tests/python/compatibility/test_version_migration.py`

**Validation**:
```bash
# Run version migration tests
python3 -m pytest tests/python/compatibility/test_version_migration.py -v
```

---

## Phase 4: Cross-Cutting Concerns

### T026: Test Error Handling Compatibility
**Priority**: P2 | **Estimated**: 3 hours | **Dependencies**: T013, T016, T018

**Acceptance Criteria**:
- [ ] Validate error message consistency
- [ ] Test exception type matching
- [ ] Test error codes and exit status
- [ ] Create error handling validator

**Implementation Details**:
```python
# tests/python/compatibility/error_handling_validator.py
class ErrorHandlingValidator:
    """Validates error handling compatibility between Python API and CLI"""

    def __init__(self):
        self.cli_tester = CLICompatibilityTester()
        self.error_mappings = {
            'FileNotFoundError': 'No such file',
            'ValueError': 'Invalid',
            'RuntimeError': 'Error',
            'IOError': 'Input/output error'
        }

    def validate_error_handling(self, python_func, cli_args, expected_error_type=None):
        """Validate error handling between Python and CLI"""
        python_error = None
        cli_error = None

        # Test Python API error
        try:
            python_func()
        except Exception as e:
            python_error = e

        # Test CLI error
        ret_code, _, cli_stderr = self.cli_tester.run_cli_command(cli_args)

        if ret_code != 0:
            cli_error = cli_stderr

        # Validate error types match
        if expected_error_type:
            assert isinstance(python_error, expected_error_type)

        # Validate error messages are similar
        if python_error and cli_error:
            similarity = self._calculate_similarity(str(python_error), cli_error)
            assert similarity > 0.5, f"Error messages too different: Python='{python_error}', CLI='{cli_error}'"

        return ErrorComparison(python_error, cli_error)
```

**Files to Create**:
- `tests/python/compatibility/error_handling_validator.py`
- `tests/python/compatibility/test_comprehensive_error_handling.py`

**Validation**:
```bash
# Run comprehensive error handling tests
python3 -m pytest tests/python/compatibility/test_comprehensive_error_handling.py -v
```

---

### T027: Generate Comprehensive Performance Report
**Priority**: P2 | **Estimated**: 3 hours | **Dependencies**: T014, T015, T026

**Acceptance Criteria**:
- [ ] Aggregate performance metrics from all tests
- [ ] Generate HTML report with charts
- [ ] Include performance trend analysis
- [ ] Save to `/Users/forrest/Temp/demodata/test_reports/`

**Implementation Details**:
```python
# tests/python/compatibility/reporting/performance_reporter.py
class PerformanceReporter:
    """Generates comprehensive performance reports"""

    def generate_html_report(self, test_results: List[TestResult]) -> str:
        """Generate HTML performance report"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>RustKmer CLI-Python API Compatibility Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .metric { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
                .pass { background-color: #d4edda; }
                .fail { background-color: #f8d7da; }
                .chart-container { width: 600px; height: 400px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1>Compatibility Test Report</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Tests Run: {total_tests}</p>
                <p>Passed: {passed_tests}</p>
                <p>Failed: {failed_tests}</p>
                <p>Performance Within Threshold: {performance_ok}</p>
            </div>

            <div class="charts">
                <h2>Performance Comparison</h2>
                <div class="chart-container">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>

            <div class="details">
                <h2>Test Results</h2>
                {test_details}
            </div>

            <script>
                // Performance chart
                const ctx = document.getElementById('performanceChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'bar',
                    data: {
                        labels: {chart_labels},
                        datasets: [{{
                            label: 'Performance Ratio (Python/CLI)',
                            data: {chart_data},
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }}]
                    },
                    options: {
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 1.5
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """

        # Generate report data
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.passed)
        failed_tests = total_tests - passed_tests
        performance_ok = sum(1 for r in test_results if r.performance_ratio <= 1.10)

        # Render template
        return html_template.format(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            performance_ok=performance_ok,
            test_details=self._generate_test_details(test_results),
            chart_labels=json.dumps([r.test_name for r in test_results]),
            chart_data=json.dumps([r.performance_ratio for r in test_results])
        )
```

**Files to Create**:
- `tests/python/compatibility/reporting/performance_reporter.py`
- `tests/python/compatibility/reporting/chart_generator.py`

**Validation**:
```bash
# Generate performance report
python3 tests/python/compatibility/generate_performance_report.py
```

---

### T028: Test Cross-Platform Compatibility
**Priority**: P3 | **Estimated**: 3 hours | **Dependencies**: All previous tasks

**Acceptance Criteria**:
- [ ] Test file path handling on different platforms
- [ ] Verify end-of-line handling in text outputs
- [ ] Test path separators and absolute/relative paths
- [ ] Validate Unicode/UTF-8 handling

**Implementation Details**:
```python
# tests/python/compatibility/test_platform_compatibility.py
class TestPlatformCompatibility:
    """Test cross-platform compatibility"""

    def test_path_separators(self):
        """Test path separator handling"""
        # Test with forward slashes
        forward_path = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"

        # Test with backslashes (Windows style)
        backslash_path = forward_path.replace('/', '\\')

        # Python API should handle both
        counter = KmerCounter(k=31)

        # Test forward slash
        counter.count_file(forward_path)
        count1 = counter.get_total_count()

        # Reset and test backslash (if on Windows)
        counter = KmerCounter(k=31)
        if os.name == 'nt':
            counter.count_file(backslash_path)
            count2 = counter.get_total_count()
            assert count1 == count2

    def test_unicode_sequences(self):
        """Test Unicode sequence handling"""
        # Use Unicode in sequence description (not sequence itself)
        counter = KmerCounter(k=7)

        # Test with metadata
        sequence = "ATCGATCGATCG"
        counter.count_string(sequence)
        count = counter.get_total_count()
        assert count == 7  # (len(sequence) - k + 1)
```

**Files to Create**:
- `tests/python/compatibility/test_platform_compatibility.py`

**Validation**:
```bash
# Run platform compatibility tests
python3 -m pytest tests/python/compatibility/test_platform_compatibility.py -v
```

---

### T029: Create Test Suite Integration
**Priority**: P1 | **Estimated**: 3 hours | **Dependencies**: T005, T027

**Acceptance Criteria**:
- [ ] Integrate all tests into unified test suite
- [ ] Create pytest configuration file
- [ ] Add test markers for different categories
- [ ] Enable test discovery and selection

**Implementation Details**:
```ini
# pytest.ini
[tool:pytest]
testpaths = tests/python/compatibility
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    small: Tests with small datasets
    medium: Tests with medium datasets
    large: Tests with large datasets
    performance: Performance benchmark tests
    compatibility: Core compatibility tests
    error_handling: Error handling validation tests
```

```python
# tests/python/compatibility/conftest.py
import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_base():
    """Base path for test data"""
    return Path("/Users/forrest/Temp/demodata")

@pytest.fixture(scope="session")
def fasta_files(test_data_base):
    """List of available FASTA files"""
    fasta_dir = test_data_base / "fasta"
    return list(fasta_dir.glob("*.fa*")) if fasta_dir.exists() else []

@pytest.fixture(scope="session")
def fastq_files(test_data_base):
    """List of available FASTQ files"""
    fastq_dir = test_data_base / "fastq"
    fastq_files = list(fastq_dir.glob("*.fq*")) if fastq_dir.exists() else []
    # Skip split directory for this fixture
    return [f for f in fastq_files if 'split' not in str(f)]

@pytest.fixture(scope="session")
def rkdb_files(test_data_base):
    """List of available RKDB files"""
    split_dir = test_data_base / "fastq" / "split"
    return list(split_dir.glob("*.rkdb")) if split_dir.exists() else []

@pytest.fixture
def temp_db_path():
    """Temporary path for test databases"""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
        path = f.name
    yield path
    if Path(path).exists():
        Path(path).unlink()
```

**Files to Create**:
- `pytest.ini`
- `tests/python/compatibility/conftest.py`
- `tests/python/compatibility/__init__.py`

**Validation**:
```bash
# Run test suite with markers
python3 -m pytest tests/python/compatibility -m "not large" -v
python3 -m pytest tests/python/compatibility -m performance -v
```

---

### T030: Final Integration and Documentation
**Priority**: P1 | **Estimated**: 2 hours | **Dependencies**: T029

**Acceptance Criteria**:
- [ ] Create final documentation for compatibility tests
- [ ] Add README for running tests with real data
- [ ] Verify all tests pass end-to-end
- [ ] Archive test results to `/Users/forrest/Temp/demodata/test_reports/`

**Implementation Details**:
```markdown
# tests/python/compatibility/README.md

# CLI-Python API Compatibility Tests

This directory contains comprehensive compatibility tests between RustKmer CLI commands and Python API methods using real biological data from `/Users/forrest/Temp/demodata`.

## Running Tests

### Quick Start
```bash
# Run all compatibility tests
python3 -m pytest tests/python/compatibility -v

# Run only small and medium tests
python3 -m pytest tests/python/compatibility -m "not large" -v

# Run performance benchmarks
python3 -m pytest tests/python/compatibility -m performance -v -s
```

### Using Real Test Data
Tests use data from `/Users/forrest/Temp/demodata`:
- FASTA files: `fasta/osa1_r7.asm.fa`
- FASTQ files: `fastq/mrna_miR5794_*.fq.gz`
- RKDB databases: `fastq/split/*.rkdb`

### Generating Reports
```bash
# Generate HTML compatibility report
python3 tests/python/compatibility/comprehensive_test_runner.py \
    --output-format html \
    --output-path /Users/forrest/Temp/demodata/test_reports/compatibility_report.html

# Generate performance benchmark report
python3 tests/python/compatibility/generate_performance_report.py
```

## Test Categories

- **small**: Small datasets (<1MB)
- **medium**: Medium datasets (1-100MB)
- **large**: Large datasets (>100MB)
- **performance**: Performance benchmark tests
- **compatibility**: Core compatibility tests
- **error_handling**: Error handling validation
```

**Files to Create**:
- `tests/python/compatibility/README.md`
- `tests/python/compatibility/run_all_tests.py`

**Validation**:
```bash
# Final test run
python3 tests/python/compatibility/run_all_tests.py

# Check report generation
ls -la /Users/forrest/Temp/demodata/test_reports/
```

---

## Task Dependencies Graph

```
Phase 1 (Foundation)
T001 → T002 → T003 → T004 → T005

Phase 2 (Core API)
T005 → T006, T007, T008
T006, T007 → T009, T011
T008 → T010, T013
T003 + T006, T007 → T014
T003 + T008 → T015

Phase 3 (Advanced)
T008 → T016, T017, T019
T008, T017 → T018
T014 → T024
T019, T021 → T021
T014, T015 → T022, T023

Phase 4 (Cross-Cutting)
T013, T016, T018 → T026
T014, T015, T026 → T027
All previous → T028
T005, T027 → T029
T029 → T030
```

## Success Metrics

- All 30 tasks completed successfully
- 100% test coverage of Python API methods
- Python API performance within 110% of CLI baseline
- Zero critical compatibility issues
- Comprehensive documentation and reports generated

## Final Deliverables

1. Complete test suite in `tests/python/compatibility/`
2. Test reports in `/Users/forrest/Temp/demodata/test_reports/`
3. Performance benchmarks and comparisons
4. Error handling validation report
5. HTML documentation for running tests

---

## Quick Start Commands

```bash
# 1. Run all compatibility tests
cd /Users/forrest/GitHub/rustkmer
python3 -m pytest tests/python/compatibility -v

# 2. Generate comprehensive report
python3 tests/python/compatibility/comprehensive_test_runner.py \
    --output-format html \
    --output-path /Users/forrest/Temp/demodata/test_reports/final_report.html

# 3. View results
open /Users/forrest/Temp/demodata/test_reports/final_report.html
```

**Total Estimated Time**: 90-120 hours
**Priority Focus**: P1 tasks (50 hours), P2 tasks (30 hours), P3 tasks (30 hours)