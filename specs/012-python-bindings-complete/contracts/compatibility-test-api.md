# Compatibility Testing API Specification

**Version**: 1.0
**Date**: 2025-12-09
**Purpose**: API specification for CLI-Python compatibility testing framework

## Overview

This API defines the interface for comprehensive compatibility testing between RustKmer CLI commands and Python API methods. It ensures 100% functional parity through automated testing of results, performance, and error handling.

## Core API Endpoints

### 1. Test Management API

#### Run Complete Compatibility Test Suite

```http
POST /api/v1/compatibility/run-suite
Content-Type: application/json

{
  "test_categories": ["small", "medium", "large"],
  "api_methods": ["all"],
  "include_performance": true,
  "retry_failed": 3,
  "parallel_execution": true
}
```

**Response**:
```json
{
  "suite_id": "cs_2025_12_09_001",
  "status": "running",
  "total_tests": 30,
  "estimated_duration_minutes": 45
}
```

#### Get Test Suite Status

```http
GET /api/v1/compatibility/suite/{suite_id}/status
```

**Response**:
```json
{
  "suite_id": "cs_2025_12_09_001",
  "status": "completed",
  "progress": {
    "completed": 30,
    "total": 30,
    "percentage": 100
  },
  "summary": {
    "passed": 28,
    "failed": 2,
    "performance_within_threshold": 27
  }
}
```

### 2. Individual Test Execution API

#### Run Single Compatibility Test

```http
POST /api/v1/compatibility/test
Content-Type: application/json

{
  "python_class": "KmerCounter",
  "python_method": "count_string",
  "cli_command": "rustkmer count",
  "test_parameters": {
    "sequence": "ATCGATCGATCG",
    "k": 4,
    "canonical": false
  },
  "test_data": {
    "type": "synthetic",
    "category": "small"
  },
  "performance_runs": 5
}
```

**Response**:
```json
{
  "test_id": "test_001",
  "execution": {
    "python_output": {
      "type": "integer",
      "value": 9,
      "execution_time_ms": 15.2
    },
    "cli_output": {
      "type": "integer",
      "value": 9,
      "execution_time_ms": 12.8
    },
    "is_identical": true,
    "performance_metrics": {
      "ratio": 1.19,
      "within_threshold": true
    },
    "error_comparison": {
      "both_succeeded": true
    }
  }
}
```

### 3. Test Data Management API

#### Generate Synthetic Test Data

```http
POST /api/v1/compatibility/test-data/generate
Content-Type: application/json

{
  "category": "medium",
  "format": "fasta",
  "specifications": {
    "num_sequences": 100,
    "seq_length_range": [500, 1000],
    "kmer_distribution": "uniform",
    "include_variants": true,
    "error_rate": 0.01
  }
}
```

**Response**:
```json
{
  "data_id": "synth_2025_12_09_001",
  "file_path": "/tmp/test_data/synth_001.fa",
  "metadata": {
    "size_mb": 25.4,
    "total_kmers": 45678,
    "unique_kmers": 12345
  }
}
```

### 4. Performance Benchmarking API

#### Run Performance Benchmarks

```http
POST /api/v1/compatibility/benchmark
Content-Type: application/json

{
  "operations": ["count", "query", "fuzzy-query"],
  "data_sizes": ["small", "medium", "large"],
  "runs_per_test": 10,
  "include_memory_profiling": true,
  "statistical_analysis": true
}
```

**Response**:
```json
{
  "benchmark_id": "bm_2025_12_09_001",
  "results": {
    "count_small": {
      "python_mean_ms": 15.2,
      "cli_mean_ms": 13.1,
      "ratio": 1.16,
      "within_threshold": true,
      "confidence_interval_95": [14.8, 15.6]
    },
    "count_medium": {
      "python_mean_ms": 152.3,
      "cli_mean_ms": 141.7,
      "ratio": 1.07,
      "within_threshold": true,
      "confidence_interval_95": [149.2, 155.4]
    }
  }
}
```

### 5. Report Generation API

#### Generate Compatibility Report

```http
POST /api/v1/compatibility/report
Content-Type: application/json

{
  "suite_id": "cs_2025_12_09_001",
  "format": "html",
  "include_charts": true,
  "include_performance_details": true,
  "highlight_failures": true
}
```

**Response**:
```json
{
  "report_id": "report_2025_12_09_001",
  "download_url": "/api/v1/compatibility/report/report_2025_12_09_001/download",
  "format": "html",
  "size_kb": 245
}
```

## Data Models

### CompatibilityTestSuite

```python
@dataclass
class CompatibilityTestSuite:
    suite_id: str
    test_date: datetime
    python_version: str
    cli_version: str
    configuration: TestConfiguration
    results: List[TestExecution]
    summary: TestSummary
```

### TestExecution

```python
@dataclass
class TestExecution:
    test_id: str
    python_class: str
    python_method: str
    cli_command: str
    test_parameters: Dict[str, Any]
    python_result: TestResult
    cli_result: TestResult
    compatibility: CompatibilityResult
    performance: PerformanceResult
    error_handling: ErrorHandlingResult
```

### CompatibilityResult

```python
@dataclass
class CompatibilityResult:
    outputs_match: bool
    difference_type: Optional[DifferenceType]
    difference_details: Optional[Dict[str, Any]]
    validation_passed: bool
```

### PerformanceResult

```python
@dataclass
class PerformanceResult:
    python_time_ms: float
    cli_time_ms: float
    ratio: float
    within_threshold: bool
    runs_count: int
    confidence_interval: Tuple[float, float]
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "COMPATIBILITY_TEST_FAILED",
    "message": "Test execution failed",
    "details": {
      "test_id": "test_001",
      "python_error": "ValueError: Invalid k-mer sequence",
      "cli_error": "rustkmer: error: Invalid sequence at position 5",
      "suggestion": "Verify input sequence contains only ACGT characters"
    },
    "timestamp": "2025-12-09T10:30:00Z"
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| TEST_NOT_FOUND | Test configuration not found |
| INVALID_PARAMETERS | Test parameters are invalid |
| PYTHON_API_ERROR | Python API raised an exception |
| CLI_EXECUTION_ERROR | CLI command failed |
| PERFORMANCE_THRESHOLD_EXCEEDED | Performance outside acceptable range |
| DATA_GENERATION_FAILED | Failed to generate test data |

## Authentication

All API endpoints require API key authentication:

```http
Authorization: Bearer <COMPATIBILITY_TEST_API_KEY>
```

## Rate Limits

- Run suite: 10 requests per hour
- Individual test: 100 requests per hour
- Report generation: 50 requests per hour
- Data generation: 20 requests per hour

## WebSocket Support

For real-time test execution updates:

```
ws://api.rustkmer.com/compatibility/updates/{suite_id}
```

Message format:
```json
{
  "type": "test_completed",
  "test_id": "test_001",
  "result": {
    "status": "passed",
    "duration_ms": 28.5
  },
  "timestamp": "2025-12-09T10:30:15Z"
}
```

## SDK Integration

### Python SDK Example

```python
from rustkmer.compatibility import CompatibilityTester

tester = CompatibilityTester(api_key="your-key")

# Run complete test suite
suite = tester.run_suite(
    categories=["small", "medium"],
    include_performance=True
)

# Wait for completion and get results
results = suite.wait_for_completion(timeout_minutes=60)

# Generate report
report = suite.generate_report(format="html")
report.save("compatibility_report.html")
```

### CLI Integration Example

```bash
# Run compatibility tests via CLI
rustkmer compatibility run \
  --categories small,medium,large \
  --include-performance \
  --output-format json \
  --output-file results.json

# Generate HTML report
rustkmer compatibility report \
  --input results.json \
  --format html \
  --output report.html
```