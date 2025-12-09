# RustKmer CLI-Python Compatibility Testing Framework

This framework provides comprehensive compatibility testing between RustKmer's CLI and Python API implementations, ensuring functional parity and performance monitoring across different platforms and environments.

## Overview

The compatibility testing framework consists of several modules that work together to:

1. **Run compatibility tests** between CLI and Python API implementations
2. **Monitor performance** and detect regressions over time
3. **Generate detailed reports** with visualizations
4. **Test across platforms** and configurations
5. **Stress test** with large datasets
6. **Automate reporting** and notifications

## Module Structure

```
tests/python/compatibility/
├── README.md                      # This file
├── runner.py                     # Main test runner
├── reporting.py                   # Report generation and comparison
├── performance_regression.py       # Performance tracking and regression detection
├── auto_reporter.py               # Automated report aggregation and publishing
├── cross_platform.py             # Cross-platform testing matrix
├── stress_test.py                # Large dataset stress testing
└── examples/                      # Example usage and configurations
```

## Quick Start

### Basic Compatibility Test

```python
from tests.python.compatibility.runner import CompatibilityTestRunner

# Create test runner
runner = CompatibilityTestRunner()

# Run all compatibility tests
suite = runner.run_all_tests()

# Print summary
print(f"Pass rate: {suite.pass_rate:.1f}%")
print(f"Total time: {suite.total_time:.2f}s")
```

### Generate Performance Report

```python
from tests.python.compatibility.reporting import ReportGenerator, ResultComparator

# Load test results
with open('compatibility_report.json', 'r') as f:
    test_data = json.load(f)

# Compare results
comparator = ResultComparator()
comparison = comparator.compare_results(test_data['results'])
test_data['comparison'] = comparison.__dict__

# Generate reports
generator = ReportGenerator()
html_report = generator.generate_html_report(test_data)
markdown_report = generator.generate_markdown_report(test_data)
plots = generator.generate_performance_plots(test_data['results'])

print(f"HTML report: {html_report}")
print(f"Markdown report: {markdown_report}")
print(f"Performance plots: {plots}")
```

### Performance Regression Testing

```python
from tests.python.compatibility.performance_regression import PerformanceTracker, RegressionTestRunner

# Initialize tracker
tracker = PerformanceTracker()

# Run regression test
runner = RegressionTestRunner(tracker)
result, regressions = runner.run_regression_test(test_iterations=3)

# Check for regressions
if regressions:
    print(f"⚠️  Detected {len(regressions)} regressions")
    for regression in regressions:
        print(f"  - {regression.test_name}: {regression.regression_percent:.1f}%")
else:
    print("✅ No regressions detected")
```

### Cross-Platform Testing

```python
from tests.python.compatibility.cross_platform import CrossPlatformTester

# Create tester
tester = CrossPlatformTester()

# Run matrix test
results = tester.run_matrix_test(output_dir="matrix_results")

# The results include:
# - Platform information (OS, architecture, memory, etc.)
# - Performance metrics for different dataset sizes
# - Compatibility results across k-mer sizes
```

### Stress Testing

```python
from tests.python.compatibility.stress_test import StressTester

# Create stress tester
tester = StressTester()

# Run stress tests (up to 1GB by default)
results = tester.run_stress_tests(max_size_mb=1000)

# Or run memory stress test
memory_result = tester.run_memory_stress_test(
    dataset_size_mb=500,
    duration_minutes=10
)
```

## Configuration

### Test Runner Configuration

The test runner can be configured with different scenarios:

```python
# Register custom tests
runner = CompatibilityTestRunner()

def test_custom_feature(cli_tester, python_tester, temp_dir):
    # Custom test implementation
    # Return TestResult object
    pass

runner.register_test(test_custom_feature)
```

### Stress Test Configuration

```python
# Custom stress test configuration
config = {
    "test_scenarios": [
        {
            "name": "custom_scenario",
            "description": "Custom test scenario",
            "size_mb": 50,
            "k_sizes": [16, 31],
            "sequences": ["ATCGATCG...", "GCTAGCTA..."]  # Custom sequences
        }
    ]
}

tester = StressTester()
tester.test_configs = config
```

### Auto Reporter Configuration

Create a configuration file (`config.json`):

```json
{
    "email": {
        "enabled": true,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your-email@gmail.com",
        "password": "your-password",
        "from_address": "your-email@gmail.com",
        "to_addresses": ["team@example.com"]
    },
    "webhook": {
        "enabled": true,
        "url": "https://hooks.slack.com/services/...",
        "secret": "webhook-secret"
    }
}
```

## CI/CD Integration

### GitHub Actions

The framework includes a pre-configured GitHub Actions workflow (`.github/workflows/python-compatibility-tests.yml`) that:

- Tests on multiple operating systems (Ubuntu, macOS, Windows)
- Tests with multiple Python versions (3.8 - 3.13)
- Runs performance regression tests
- Generates and publishes compatibility reports
- Sends notifications on failures

### Local Testing

For local development:

```bash
# Run basic compatibility tests
python tests/python/compatibility/runner.py

# Run with custom output
python tests/python/compatibility/runner.py \
    --output my_results.json \
    --cli-binary ./target/release/rustkmer

# Run stress tests
python tests/python/compatibility/stress_test.py \
    --max-size 1000 \
    --output stress_results

# Run performance regression tests
python tests/python/compatibility/performance_regression.py \
    --iterations 5 \
    --baseline-days 14
```

## Report Types

### 1. Compatibility Test Report

Generated after each test run, includes:
- Test execution summary
- Pass/fail status for each test
- Performance comparison between CLI and Python
- Error messages for failed tests

### 2. Performance Report

Includes:
- Performance ratios and trends
- Execution time comparisons
- Memory usage analysis
- Regression detection
- Visual charts and graphs

### 3. Cross-Platform Matrix

Shows:
- Results across different operating systems
- Architecture-specific behavior
- Python version compatibility
- Platform-specific notes and recommendations

### 4. Stress Test Report

Contains:
- Large dataset performance metrics
- Memory usage patterns
- Scalability analysis
- Resource utilization statistics

## Interpreting Results

### Performance Ratios

The performance ratio is calculated as:
```
performance_ratio = python_execution_time / cli_execution_time
```

- **< 1.0**: Python is faster than CLI
- **≈ 1.0**: Performance parity between implementations
- **> 1.0**: Python is slower than CLI

### Pass Criteria

A test is considered passed when:
1. Both CLI and Python execute successfully
2. Both produce equivalent outputs (exact or acceptable approximation)
3. Performance ratio is within acceptable bounds (default: < 10x)
4. Memory usage is reasonable (Python may use up to 5x CLI memory)

### Regression Detection

Performance regressions are detected when:
- Current performance is >20% worse than baseline (30-day default)
- Multiple consecutive measurements show degradation
- Statistical significance threshold is met

## Troubleshooting

### Common Issues

1. **Build Errors**
   ```bash
   # Ensure RustKmer is built with release optimizations
   cargo build --release

   # Build Python bindings
   cd python && maturin develop --release
   ```

2. **Import Errors**
   ```bash
   # Check Python path
   python -c "import rustkmer; print('OK')"

   # Rebuild if necessary
   cd python && maturin develop --release
   ```

3. **Memory Issues**
   - Monitor available memory before large tests
   - Use `--max-size` parameter to limit test size
   - Consider running tests on machines with more RAM

4. **Performance Anomalies**
   - Check system load during testing
   - Run multiple iterations for stability
   - Review system resource utilization

### Debug Mode

Enable debug output for detailed test execution:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run tests with debug logging
runner = CompatibilityTestRunner()
suite = runner.run_all_tests()
```

## Contributing

### Adding New Tests

1. Create a test function following the existing pattern:

```python
def test_new_feature(cli_tester: CLITester, python_tester: PythonTester, temp_dir: Path) -> TestResult:
    """Test new compatibility feature"""
    try:
        # Run CLI command
        cli_output, cli_time = cli_tester.run_command("new-command", ["--flag", "value"])

        # Run Python equivalent
        python_output, python_time = python_tester.new_method("value")

        # Compare results
        passed = cli_output == python_output

        return TestResult(
            test_name="new_feature",
            passed=passed,
            cli_output=cli_output,
            python_output=python_output,
            execution_time_cli=cli_time,
            execution_time_python=python_time,
            performance_ratio=python_time / cli_time if cli_time > 0 else None
        )
    except Exception as e:
        return TestResult(
            test_name="new_feature",
            passed=False,
            cli_output=None,
            python_output=None,
            execution_time_cli=0,
            execution_time_python=0,
            error=str(e)
        )
```

2. Register the test with the runner:

```python
runner = CompatibilityTestRunner()
runner.register_test(test_new_feature)
```

### Adding Custom Report Formats

Extend the `ReportGenerator` class:

```python
class CustomReportGenerator(ReportGenerator):
    def generate_csv_report(self, report_data: Dict[str, Any]) -> str:
        """Generate CSV format report"""
        # Custom CSV generation logic
        pass
```

## Best Practices

### Test Design

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Cleanup**: Clean up temporary files after each test
3. **Timeouts**: Set reasonable timeouts for large dataset tests
4. **Resource Limits**: Monitor memory and CPU usage during tests

### Performance Testing

1. **Multiple Iterations**: Run tests multiple times for stability
2. **Warm-up**: Allow for JIT compilation in Python
3. **Environment Control**: Test on consistent hardware when possible
4. **Baseline Tracking**: Maintain performance baselines over time

### CI/CD Integration

1. **Parallel Execution**: Use matrix builds for efficiency
2. **Artifact Collection**: Save test reports as build artifacts
3. **Failure Notifications**: Set up alerts for critical regressions
4. **Historical Tracking**: Maintain performance trend data

## License

This compatibility testing framework is part of the RustKmer project and follows the same license terms.