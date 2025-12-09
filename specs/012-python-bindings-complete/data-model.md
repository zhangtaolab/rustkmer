# Data Model: CLI-Python API Compatibility Testing

**Date**: 2025-12-09
**Purpose**: Data entities and relationships for comprehensive compatibility testing

## Core Entities

### 1. CompatibilityTestSuite

Container for organizing and managing all compatibility tests.

```python
@dataclass
class CompatibilityTestSuite:
    """Container for compatibility test results"""
    suite_id: str
    test_date: datetime
    python_version: str
    cli_version: str
    total_tests: int
    passed_tests: int
    failed_tests: List[FailedTest]
    performance_summary: PerformanceSummary
```

**Relationships**:
- Has many: CompatibilityTestCase
- Has one: PerformanceSummary
- Has many: FailedTest

### 2. CompatibilityTestCase

Individual test case for comparing a specific Python API method with CLI.

```python
@dataclass
class CompatibilityTestCase:
    """Individual compatibility test case"""
    test_id: str
    python_class: str  # e.g., "KmerCounter", "Database", "FuzzyQuery"
    python_method: str  # e.g., "count_string", "query", "fuzzy_search"
    cli_command: str  # e.g., "rustkmer count", "rustkmer query"
    test_parameters: Dict[str, Any]
    test_data_path: Optional[str]
    expected_result: Optional[ExpectedResult]
```

**Relationships**:
- Generates: TestExecution
- Uses: TestData

### 3. TestExecution

Single execution of a compatibility test with results.

```python
@dataclass
class TestExecution:
    """Result of a single compatibility test execution"""
    execution_id: str
    test_case: CompatibilityTestCase
    python_output: TestOutput
    cli_output: TestOutput
    is_identical: bool
    difference_details: Optional[DifferenceDetails]
    performance_metrics: PerformanceMetrics
    error_comparison: ErrorComparison
    timestamp: datetime
```

**Relationships**:
- Belongs to: CompatibilityTestCase
- Has one: PerformanceMetrics
- Has one: ErrorComparison

### 4. TestData

Test data for compatibility testing.

```python
@dataclass
class TestData:
    """Test data for compatibility tests"""
    data_id: str
    data_type: TestDataCategory  # SMALL, MEDIUM, LARGE
    data_format: DataFormat  # FASTA, FASTQ, RKDB
    file_path: str
    metadata: TestDataMetadata
```

**TestDataCategory**:
- SMALL: <1MB, 100-1000 k-mers
- MEDIUM: 1-100MB, 1K-100K k-mers
- LARGE: >100MB, >100K k-mers

**Relationships**:
- Used by: CompatibilityTestCase

### 5. PerformanceMetrics

Performance comparison between Python API and CLI.

```python
@dataclass
class PerformanceMetrics:
    """Performance comparison metrics"""
    python_time_ms: float
    cli_time_ms: float
    python_memory_mb: float
    cli_memory_mb: float
    performance_ratio: float  # python_time / cli_time
    memory_ratio: float  # python_memory / cli_memory
    is_within_threshold: bool
    runs_count: int
    std_deviation: float
```

**Performance Thresholds**:
- Time ratio ≤ 1.10 (Python ≤ 110% of CLI)
- Memory ratio ≤ 1.05 (Python ≤ 105% of CLI)

### 6. ErrorComparison

Comparison of error handling between Python API and CLI.

```python
@dataclass
class ErrorComparison:
    """Comparison of error handling"""
    python_error: Optional[PythonError]
    cli_error: Optional[CLIError]
    error_types_match: bool
    error_messages_similar: bool  # Using similarity score
    exit_code_match: bool
```

### 7. ExpectedResult

Expected result for validation.

```python
@dataclass
class ExpectedResult:
    """Expected test result for validation"""
    result_type: ResultType  # EXACT_COUNT, DATABASE_PROPERTIES, ERROR_CODE
    expected_value: Any
    tolerance: Optional[float]  # For numerical comparisons
    validation_rules: List[ValidationRule]
```

## Value Objects

### TestOutput
```python
@dataclass
class TestOutput:
    """Output from either Python API or CLI"""
    output_type: OutputType  # INTEGER, DATABASE_FILE, TEXT, JSON, ERROR
    value: Any
    file_path: Optional[str]
    execution_time_ms: float
    memory_usage_mb: float
```

### DifferenceDetails
```python
@dataclass
class DifferenceDetails:
    """Details of differences between outputs"""
    difference_type: DifferenceType
    python_value: Any
    cli_value: Any
    difference_magnitude: Optional[float]
    is_acceptable: bool
```

## Enums

```python
from enum import Enum

class OutputType(Enum):
    INTEGER = "integer"
    DATABASE_FILE = "database_file"
    TEXT = "text"
    JSON = "json"
    ERROR = "error"

class TestDataCategory(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class DataFormat(Enum):
    FASTA = "fasta"
    FASTQ = "fastq"
    RKDB = "rkdb"

class ResultType(Enum):
    EXACT_COUNT = "exact_count"
    DATABASE_PROPERTIES = "database_properties"
    ERROR_CODE = "error_code"

class DifferenceType(Enum):
    EXACT_MATCH = "exact_match"
    NUMERICAL_DIFFERENCE = "numerical_difference"
    TYPE_MISMATCH = "type_mismatch"
    MISSING_OUTPUT = "missing_output"
    EXTRA_OUTPUT = "extra_output"
```

## Aggregates and Roots

### CompatibilityTestManager (Aggregate Root)

```python
class CompatibilityTestManager:
    """Manages the complete compatibility testing process"""

    def __init__(self):
        self.test_suites: List[CompatibilityTestSuite] = []
        self.test_data_repository = TestDataRepository()
        self.result_analyzer = ResultAnalyzer()

    def run_compatibility_tests(self) -> CompatibilityTestSuite
    def generate_report(self, suite: CompatibilityTestSuite) -> TestReport
    def validate_test_data(self) -> ValidationResult
```

## Repository Interfaces

```python
class TestDataRepository:
    """Repository for test data management"""

    def find_by_category(self, category: TestDataCategory) -> List[TestData]
    def find_by_format(self, format: DataFormat) -> List[TestData]
    def generate_synthetic_data(self, spec: SyntheticDataSpec) -> TestData
```

class TestExecutionRepository:
    """Repository for test execution results"""

    def save(self, execution: TestExecution) -> None
    def find_by_test_case(self, test_case: CompatibilityTestCase) -> List[TestExecution]
    def find_performance_history(self, method: str) -> List[PerformanceMetrics]
```

## Domain Services

### ResultAnalyzer
```python
class ResultAnalyzer:
    """Analyzes compatibility test results"""

    def compare_outputs(self, python: TestOutput, cli: TestOutput) -> ComparisonResult
    def validate_performance(self, metrics: PerformanceMetrics) -> ValidationResult
    def calculate_similarity_score(self, str1: str, str2: str) -> float
```

### PerformanceBenchmark
```python
class PerformanceBenchmark:
    """Handles performance benchmarking"""

    def measure_python_api(self, method: str, params: Dict) -> PerformanceData
    def measure_cli_command(self, command: List[str]) -> PerformanceData
    def calculate_ratios(self, python: PerformanceData, cli: PerformanceData) -> PerformanceMetrics
```

## Validation Rules

```python
@dataclass
class ValidationRule:
    """Rule for validating test results"""
    rule_type: ValidationType
    parameter: str
    condition: str
    expected_value: Any

class ValidationType(Enum):
    EXACT_EQUALITY = "exact_equality"
    WITHIN_TOLERANCE = "within_tolerance"
    PATTERN_MATCH = "pattern_match"
    FILE_EXISTS = "file_exists"
```

## Integration Events

```python
@dataclass
class TestCompleted:
    """Event fired when a test completes"""
    test_id: str
    result: TestExecution
    timestamp: datetime

@dataclass
class TestSuiteCompleted:
    """Event fired when a test suite completes"""
    suite_id: str
    summary: TestSuiteSummary
    timestamp: datetime
```

## State Transitions

### Test Execution State Machine

```
[STARTED] -> (executing) -> [COMPLETED]
    |
    v
[FAILED] -> (retry) -> [STARTED]
    |
    v
[SKIPPED]
```

## Data Model Relationships Summary

```
CompatibilityTestSuite (1) -> (*) CompatibilityTestCase
CompatibilityTestCase (1) -> (*) TestExecution
TestExecution (1) -> (1) PerformanceMetrics
TestExecution (1) -> (1) ErrorComparison
CompatibilityTestCase (*) -> (*) TestData
```