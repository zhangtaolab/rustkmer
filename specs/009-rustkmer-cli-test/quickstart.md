# RustKmer CLI Testing Framework - Quick Start Guide

## Overview

This guide provides a quick introduction to using the comprehensive RustKmer CLI testing framework. The framework tests all aspects of the RustKmer CLI tool including functionality, performance, error handling, and help documentation.

## Prerequisites

1. **Install RustKmer CLI**:
   ```bash
   rustkmer --version
   ```
   Expected output: `rustkmer 0.1.0` or similar

2. **Prepare test directories**:
   ```bash
   mkdir -p /Users/forrest/Temp/demodata/rustkmer_cli_test/{logs,reports,databases,outputs}
   ```

3. **Verify test data availability**:
   ```bash
   ls /Users/forrest/Temp/demodata/*.fa* /Users/forrest/Temp/demodata/*.fq* 2>/dev/null | head -5
   ```

## Running Tests

### Quick Test - Verify Everything Works

```bash
# Test basic functionality
cd /Users/forrest/GitHub/rustkmer/specs/009-rustkmer-cli-test/scripts

# Run a quick test to ensure the framework is working
rustkmer --help 2>&1 | head -5
echo "---"
./test_help.sh 2>&1 | tail -10
```

### 1. Run Complete Test Suite

```bash
# Run all tests (takes ~10-15 minutes)
cd /Users/forrest/GitHub/rustkmer/specs/009-rustkmer-cli-test/scripts
./run_all_tests.sh

# Generate final report
./generate_final_report.sh
```

### 2. Run Individual Command Tests

#### ✅ Implemented Commands

```bash
# Count k-mers in sequence files
./test_count.sh

# Query k-mer counts from database
./test_query.sh

# Dump database to text format
./test_dump.sh

# Fuzzy query with Hamming distance
./test_fuzzy_query.sh

# Help system and documentation
./test_help.sh
```

#### ⚠️ Framework-Ready Commands

```bash
# Statistics (framework ready, command not yet implemented)
./test_stats.sh

# Database merging (framework ready, command not yet implemented)
./test_merge.sh
```

### 3. Run Rust Unit Tests

```bash
# Run all unit tests
cd /Users/forrest/GitHub/rustkmer/specs/009-rustkmer-cli-test
cargo test

# Run specific test modules
cargo test test_count
cargo test test_query
cargo test test_edge_cases
cargo test test_error_handling
cargo test test_memory_limits
```

## Understanding Test Results

### Test Output Location

```
/Users/forrest/Temp/demodata/rustkmer_cli_test/
├── logs/          # Detailed test logs
├── reports/       # Test reports (Markdown)
├── databases/     # Generated test databases
└── outputs/       # Command outputs
```

### Interpreting Results

- ✅ **Passed**: Command works as expected
- ⚠️ **Skipped**: Command not implemented (expected)
- ✗ **Failed**: Unexpected error (investigate)

### Example Output

```
=== RustKmer Count Command Test ===
✓ Test passed: Basic count functionality
✓ Test passed: k=21 k-mer size
✓ Test passed: k=31 k-mer size
⚠ Test skipped: k=127 (k-mer size not supported)

Total tests: 10
Passed: 9
Failed: 0
Success rate: 90.0%
```

## Advanced Usage

### Running Performance Tests

```bash
# Run benchmarks
cd /Users/forrest/GitHub/rustkmer/specs/009-rustkmer-cli-test/benches
cargo bench -- count_benchmark
```

### Testing with Custom Data

```bash
# Copy your FASTA files to test data directory
cp your_file.fa /Users/forrest/Temp/demodata/rustkmer_cli_test/test_data/

# Run tests with custom data
TEST_DATA_DIR=/Users/forrest/Temp/demodata/rustkmer_cli_test/test_data \
  ./test_count.sh
```

### Debug Mode

```bash
# Enable verbose output
export DEBUG=true
export VERBOSE=true

# Run tests with debug information
./test_count.sh
```

## Test Framework Architecture

### Components

1. **Test Scripts** (`scripts/`): Bash scripts for end-to-end testing
2. **Validators** (`src/validators/`): Rust modules for output validation
3. **Unit Tests** (`tests/`): Rust unit tests for edge cases
4. **Benchmarks** (`benches/`): Performance benchmarks
5. **Reports** (`docs/`): Test documentation and results

### Adding New Tests

1. Create test script: `scripts/test_newfeature.sh`
2. Create validator: `src/validators/newfeature_validator.rs`
3. Create unit tests: `tests/test_newfeature_*.rs`
4. Update `run_all_tests.sh` to include new tests

## Troubleshooting

### Common Issues

**Issue**: "rustkmer: command not found"
```bash
# Ensure rustkmer is in PATH
which rustkmer
# Or run with full path
/path/to/rustkmer --help
```

**Issue**: "No test data found"
```bash
# Verify test data location
ls /Users/forrest/Temp/demodata/
# Download test data if needed
```

**Issue**: Permission denied
```bash
# Fix permissions
chmod +x scripts/*.sh
mkdir -p /Users/forrest/Temp/demodata/rustkmer_cli_test/{logs,reports}
```

**Issue**: Tests hanging
```bash
# Check if tests are actually running
ps aux | grep rustkmer
# Kill any stuck processes
pkill -f rustkmer
```

### Getting Help

1. Check test logs for detailed error messages:
   ```bash
   ls -la /Users/forrest/Temp/demodata/rustkmer_cli_test/logs/
   tail -20 /Users/forrest/Temp/demodata/rustkmer_cli_test/logs/*.log
   ```

2. Review known issues:
   ```bash
   cat /Users/forrest/GitHub/rustkmer/specs/009-rustkmer-cli-test/docs/issues_found.md
   ```

3. Run with debug mode:
   ```bash
   DEBUG=true ./test_count.sh 2>&1 | tee debug.log
   ```

## Best Practices

### Before Running Tests

1. Ensure sufficient disk space (recommended: 10GB)
2. Close memory-intensive applications
3. Run tests on a quiet system for accurate performance metrics

### During Testing

1. Monitor system resources if running large tests
2. Check logs periodically for any issues
3. Allow tests to complete fully for accurate results

### After Testing

1. Review test reports for any failures
2. Archive important test results
3. Clean up temporary test files if needed

## Contributing

To contribute to the testing framework:

1. Fork the repository
2. Create a feature branch
3. Add your tests following existing patterns
4. Update documentation
5. Submit a pull request

## Next Steps

1. **Review Test Results**: Check the generated reports for any issues
2. **Customize Tests**: Adapt tests for your specific use cases
3. **Extend Framework**: Add new test modules as needed
4. **Integrate CI**: Set up automated testing in your CI pipeline

---

## Quick Reference

```bash
# Essential commands
cd /Users/forrest/GitHub/rustkmer/specs/009-rustkmer-cli-test

# Run everything
./run_all_tests.sh && ./generate_final_report.sh

# Check results
ls -la /Users/forrest/Temp/demodata/rustkmer_cli_test/reports/
cat /Users/forrest/Temp/demodata/rustkmer_cli_test/reports/final_test_report_*.md | tail -20

# Unit tests
cargo test

# Performance tests
cargo bench

# Help
./test_help.sh
```
./specs/009-rustkmer-cli-test/scripts/test_fuzzy_query.sh

# stats
./specs/009-rustkmer-cli-test/scripts/test_stats.sh

# merge
./specs/009-rustkmer-cli-test/scripts/test_merge.sh
```

### 3. 性能测试

```bash
# 运行性能基准测试
./specs/009-rustkmer-cli-test/scripts/benchmark.sh
```

## 查看测试报告

测试完成后，报告保存在：
```
/Users/forrest/Temp/demodata/rustkmer_cli_test/reports/
├── test_report_YYYYMMDD_HHMMSS.md    # 主测试报告
├── performance_report_YYYYMMDD.md     # 性能专项报告
└── error_summary_YYYYMMDD.md          # 错误汇总
```

## 测试数据要求

### 支持的文件格式
- FASTA (.fasta, .fa, .fas)
- FASTQ (.fastq, .fq)

### 推荐的测试数据集
1. **小文件** (< 10MB)：用于快速功能验证
2. **中等文件** (10MB - 100MB)：用于性能测试
3. **大文件** (> 100MB)：用于压力测试

## 自定义测试

### 修改测试参数

编辑 `config/test_config.yaml`：

```yaml
test_parameters:
  kmer_sizes: [21, 31, 63]
  thread_counts: [1, 2, 4, 8]
  timeout_seconds: 600

performance_thresholds:
  max_execution_time_mb: 600  # 1GB数据最大执行时间（秒）
  max_memory_gb: 8           # 最大内存使用（GB）
```

### 添加新的测试用例

1. 在相应的测试脚本中添加新函数
2. 更新 `data/test_cases.yaml`
3. 重新运行测试

## 故障排除

### 常见问题

1. **权限错误**
   ```bash
   chmod +x specs/009-rustkmer-cli-test/scripts/*.sh
   ```

2. **路径不存在**
   ```bash
   # 确保测试目录存在
   mkdir -p /Users/forrest/Temp/demodata/rustkmer_cli_test/{test_data,databases,outputs,reports,logs}
   ```

3. **RustKmer 未安装**
   ```bash
   # 重新构建
   cargo build --release
   export PATH=$PATH:$PWD/target/release
   ```

### 调试模式

```bash
# 启用详细日志
export RUST_LOG=debug
export TEST_DEBUG=1

# 运行单个测试
./specs/009-rustkmer-cli-test/scripts/test_count.sh --debug
```

## 性能优化建议

1. **SSD 存储**：使用 SSD 存储测试数据以提高 I/O 性能
2. **内存充足**：确保系统有足够的内存（> 16GB）
3. **CPU 核心**：多核 CPU 可以更好地测试并行性能

## 贡献指南

1. 发现问题时，请在 `issues/` 目录创建问题报告
2. 改进测试时，请更新相关文档
3. 提交前请运行完整测试确保没有回归

## 联系方式

如有问题，请查看：
- 错误日志：`/Users/forrest/Temp/demodata/rustkmer_cli_test/logs/`
- 测试报告：`/Users/forrest/Temp/demodata/rustkmer_cli_test/reports/`