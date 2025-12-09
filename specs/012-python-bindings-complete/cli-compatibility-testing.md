# CLI与Python API兼容性测试计划

**日期**: 2025-01-09
**版本**: 1.0
**目的**: 确保Python API与CLI版本的功能完全一致

## 概述

本文档详细说明了如何验证Python API与CLI命令的一致性。每个Python API方法都将与对应的CLI命令进行对比测试，确保：
1. 输出结果完全一致
2. 性能在可接受范围内
3. 错误处理行为一致
4. 参数选项完全对应

## 测试架构

### 1. 测试框架设计

```python
# tests/python/compatibility/cli_comparator.py
import subprocess
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

class CLICompatibilityTester:
    """CLI与Python API兼容性测试框架"""

    def __init__(self, cli_path: str = "target/release/rustkmer"):
        self.cli_path = cli_path
        self.temp_dir = tempfile.mkdtemp(prefix="rustkmer_test_")

    def run_cli_command(self, args: List[str], input_data: Optional[str] = None) -> Dict[str, Any]:
        """运行CLI命令并返回结果"""
        cmd = [self.cli_path] + args
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }

    def compare_results(self, cli_result: Dict[str, Any], py_result: Any,
                       tolerance: float = 0.0) -> Dict[str, Any]:
        """比较CLI和Python API结果"""
        comparison = {
            "identical": True,
            "differences": [],
            "performance": {}
        }

        # 详细比较逻辑将在各测试方法中实现
        return comparison
```

### 2. 测试数据准备

```python
# tests/python/compatibility/test_data.py
import os
from pathlib import Path

class TestDataGenerator:
    """生成测试数据的工具类"""

    @staticmethod
    def create_test_fasta(size: int = 1000, k: int = 31) -> str:
        """生成测试用的FASTA文件"""
        import random
        bases = ['A', 'T', 'G', 'C']

        sequences = []
        for i in range(5):
            seq = ''.join(random.choices(bases, k=k=size))
            sequences.append(f">test_seq_{i+1}\n{seq}")

        return '\n'.join(sequences)

    @staticmethod
    def create_test_fastq(reads: int = 1000, read_length: int = 150) -> str:
        """生成测试用的FASTQ文件"""
        import random
        bases = ['A', 'T', 'G', 'C']
        qual_chars = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*']

        fastq_data = []
        for i in range(reads):
            seq = ''.join(random.choices(bases, k=read_length))
            qual = ''.join(random.choices(qual_chars, k=read_length))
            fastq_data.extend([
                f"@read_{i+1}",
                seq,
                "+",
                qual
            ])

        return '\n'.join(fastq_data)
```

## 具体测试用例

### 1. Count命令测试 (P1)

```python
# tests/python/compatibility/test_count_compatibility.py
import pytest
from rustkmer import KmerCounter
from .cli_comparator import CLICompatibilityTester
from .test_data import TestDataGenerator

class TestCountCompatibility:
    """count命令兼容性测试"""

    def setup_method(self):
        self.tester = CLICompatibilityTester()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_count_fasta_basic(self):
        """测试基本FASTA计数功能"""
        # 创建测试数据
        fasta_content = TestDataGenerator.create_test_fasta()
        fasta_path = self.temp_dir / "test.fa"
        fasta_path.write_text(fasta_content)

        # Python API测试
        counter = KmerCounter(k=21, canonical=True)
        py_counts = counter.count_file(str(fasta_path))

        # CLI测试
        db_path = self.temp_dir / "test.rkdb"
        cli_result = self.tester.run_cli_command([
            "count", "-k", "21", "--canonical", "-o", str(db_path), str(fasta_path)
        ])

        assert cli_result["success"], f"CLI命令失败: {cli_result['stderr']}"

        # 验证创建的数据库
        from rustkmer import Database
        db = Database()
        db.load(str(db_path))

        # 比较结果
        test_kmers = list(py_counts.keys())[:10]  # 测试前10个k-mer
        for kmer in test_kmers:
            py_result = py_counts[kmer]
            cli_result = db.query(kmer)

            assert cli_result.found == (py_result > 0)
            if cli_result.found:
                assert cli_result.count == py_result, \
                    f"k-mer {kmer}: CLI={cli_result.count}, Python={py_result}"

    def test_count_fastq_basic(self):
        """测试FASTQ计数功能"""
        fastq_content = TestDataGenerator.create_test_fastq(reads=100)
        fastq_path = self.temp_dir / "test.fq"
        fastq_path.write_text(fastq_content)

        # Python API测试
        counter = KmerCounter(k=31, canonical=False)
        py_counts = counter.count_file(str(fastq_path))

        # CLI测试
        db_path = self.temp_dir / "test_fq.rkdb"
        cli_result = self.tester.run_cli_command([
            "count", "-k", "31", "-o", str(db_path), str(fastq_path)
        ])

        assert cli_result["success"]

        # 验证总数一致
        py_total = counter.get_total_count()

        db = Database()
        db.load(str(db_path))

        assert db.total_kmers == py_total

    def test_count_with_threads(self):
        """测试多线程计数"""
        fasta_content = TestDataGenerator.create_test_fasta(size=5000)
        fasta_path = self.temp_dir / "test_large.fa"
        fasta_path.write_text(fasta_content)

        threads = 4

        # Python API测试
        counter = KmerCounter(k=21, threads=threads, canonical=True)
        py_counts = counter.count_file(str(fasta_path))

        # CLI测试
        db_path = self.temp_dir / "test_threads.rkdb"
        cli_result = self.tester.run_cli_command([
            "count", "-k", "21", "--canonical", "--threads", str(threads),
            "-o", str(db_path), str(fasta_path)
        ])

        assert cli_result["success"]

        # 验证结果
        db = Database()
        db.load(str(db_path))

        # 检查统计一致性
        py_stats = {
            "total": counter.get_total_count(),
            "unique": counter.get_unique_count()
        }

        assert db.total_kmers == py_stats["total"]
        assert db.unique_kmers == py_stats["unique"]
```

### 2. Query命令测试 (P1)

```python
# tests/python/compatibility/test_query_compatibility.py
import pytest
from rustkmer import Database, KmerCounter
from .cli_comparator import CLICompatibilityTester
from .test_data import TestDataGenerator

class TestQueryCompatibility:
    """query命令兼容性测试"""

    def setup_method(self):
        self.tester = CLICompatibilityTester()
        self.temp_dir = Path(tempfile.mkdtemp())

        # 创建测试数据库
        self.setup_test_database()

    def setup_test_database(self):
        """创建测试用的数据库"""
        fasta_content = TestDataGenerator.create_test_fasta(size=2000)
        fasta_path = self.temp_dir / "seq.fa"
        fasta_path.write_text(fasta_content)

        # 使用Python API创建数据库
        counter = KmerCounter(k=21, canonical=True)
        counter.count_file(str(fasta_path))

        self.db_path = self.temp_dir / "test.rkdb"
        counter.save_to_database(str(self.db_path))

        # 加载Python数据库实例
        self.py_db = Database()
        self.py_db.load(str(self.db_path))

    def test_query_single_kmer(self):
        """测试单个k-mer查询"""
        test_kmers = [
            "ATCGATCGATCGATCGATCGAT",
            "GCTAGCTAGCTAGCTAGCTAGC",
            "TTTTTTTTTTTTTTTTTTTTT",
            "CCCCCCCCCCCCCCCCCCCCCCC"
        ]

        for kmer in test_kmers:
            # Python API查询
            py_result = self.py_db.query(kmer)

            # CLI查询
            cli_result = self.tester.run_cli_command([
                "query", str(self.db_path), kmer
            ])

            # 验证结果
            assert cli_result["success"], f"CLI查询失败: {cli_result['stderr']}"

            # 解析CLI输出
            cli_output = cli_result["stdout"].strip()
            if py_result.found:
                expected = f"{kmer}: {py_result.count}"
            else:
                expected = f"{kmer}: 0"

            assert cli_output == expected, \
                f"不一致: k-mer={kmer}, CLI='{cli_output}', Python={expected}"

    def test_query_multiple_kmers(self):
        """测试批量查询"""
        test_kmers = [
            "ATCGATCGATCGATCGATCGAT",
            "GCTAGCTAGCTAGCTAGCTAGC",
            "TTTTTTTTTTTTTTTTTTTTT",
            "CCCCCCCCCCCCCCCCCCCCCCC",
            "AAAAAAAAAAAAAAAAAAAAA"
        ]

        # 创建临时文件包含k-mer列表
        kmer_file = self.temp_dir / "kmers.txt"
        kmer_file.write_text('\n'.join(test_kmers))

        # Python API批量查询
        py_results = self.py_db.batch_query(test_kmers)

        # CLI批量查询
        cli_result = self.tester.run_cli_command([
            "query", "-f", str(kmer_file), str(self.db_path)
        ])

        assert cli_result["success"]

        # 解析并比较结果
        cli_lines = [line.strip() for line in cli_result["stdout"].strip().split('\n')]

        assert len(cli_lines) == len(test_kmers)

        for i, kmer in enumerate(test_kmers):
            py_result = py_results[i]
            cli_line = cli_lines[i]

            if py_result.found:
                expected_pattern = f"{kmer}: {py_result.count}"
            else:
                expected_pattern = f"{kmer}: 0"

            assert cli_line == expected_pattern
```

### 3. Fuzzy Query命令测试 (P2)

```python
# tests/python/compatibility/test_fuzzy_query_compatibility.py
import pytest
from rustkmer import Database, KmerCounter, FuzzyQuery
from .cli_comparator import CLICompatibilityTester
from .test_data import TestDataGenerator

class TestFuzzyQueryCompatibility:
    """fuzzy-query命令兼容性测试"""

    def setup_method(self):
        self.tester = CLICompatibilityTester()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.setup_test_database()

    def setup_test_database(self):
        """创建测试数据库"""
        # 创建包含已知变异的序列
        sequences = [
            "ATCGATCGATCGATCGATCGAT",  # 原始序列
            "ATCGATCGATCGATCGATCGAT",  # 相同
            "ATCGATCGATCGATCGATCGAA",  # 1个突变
            "TTCGATCGATCGATCGATCGAT",  # 1个突变
            "ATCGATCGATCGATCGATCGAC",  # 1个突变
        ]

        fasta_content = "\n".join([f">seq_{i+1}\n{seq}" for i, seq in enumerate(sequences)])
        fasta_path = self.temp_dir / "test.fa"
        fasta_path.write_text(fasta_content)

        counter = KmerCounter(k=21, canonical=False)
        counter.count_file(str(fasta_path))

        self.db_path = self.temp_dir / "test.rkdb"
        counter.save_to_database(str(self.db_path))

        self.py_db = Database()
        self.py_db.load(str(self.db_path))

    def test_fuzzy_query_basic(self):
        """测试基本模糊查询"""
        query = "ATCGATCGATCGATCGATCGAT"  # 原始序列
        distance = 1

        # Python API模糊查询
        py_fuzzy = FuzzyQuery(self.py_db, max_distance=distance)
        py_results = py_fuzzy.search(query)

        # CLI模糊查询
        cli_result = self.tester.run_cli_command([
            "fuzzy-query", "-d", str(distance), str(self.db_path), query
        ])

        assert cli_result["success"]

        # 解析CLI输出
        cli_matches = []
        for line in cli_result["stdout"].strip().split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 2:
                    cli_matches.append({
                        'kmer': parts[0],
                        'count': int(parts[1])
                    })

        # 比较结果
        assert len(cli_matches) == py_results.total_matches, \
            f"匹配数量不一致: CLI={len(cli_matches)}, Python={py_results.total_matches}"

        # 验证具体匹配
        cli_match_dict = {m['kmer']: m['count'] for m in cli_matches}
        for match in py_results.matches:
            assert match.kmer in cli_match_dict, \
                f"Python匹配的k-mer {match.kmer} 不在CLI结果中"
            assert cli_match_dict[match.kmer] == match.count, \
                f"k-mer {match.kmer} 计数不一致: CLI={cli_match_dict[match.kmer]}, Python={match.count}"

    def test_fuzzy_query_with_wildcards(self):
        """测试通配符模糊查询"""
        pattern = "A*CG*T"  # 使用通配符

        # Python API不支持通配符模糊查询，需要测试不同的方法
        # 这里可能需要调整测试策略

        # CLI测试
        cli_result = self.tester.run_cli_command([
            "fuzzy-query", "-d", "1", "--wildcard", str(self.db_path), pattern
        ])

        # 记录CLI行为，为Python API实现提供参考
        assert cli_result["success"]
        print(f"CLI通配符结果: {cli_result['stdout']}")
```

### 4. Stats命令测试 (P2)

```python
# tests/python/compatibility/test_stats_compatibility.py
import pytest
from rustkmer import Database, KmerCounter
from .cli_comparator import CLICompatibilityTester
from .test_data import TestDataGenerator

class TestStatsCompatibility:
    """stats命令兼容性测试"""

    def setup_method(self):
        self.tester = CLICompatibilityTester()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.setup_test_database()

    def setup_test_database(self):
        """创建测试数据库"""
        # 创建有明确计数分布的序列
        sequences = []
        # 添加出现频率不同的k-mers
        for _ in range(100):
            sequences.append("ATCGATCGATCGATCGATCGAT")  # 高频
        for _ in range(50):
            sequences.append("GCTAGCTAGCTAGCTAGCTAGC")  # 中频
        for _ in range(10):
            sequences.append("TTTTTTTTTTTTTTTTTTTTT")  # 低频

        fasta_content = "\n".join([f">seq_{i+1}\n{seq}" for i, seq in enumerate(sequences)])
        fasta_path = self.temp_dir / "test.fa"
        fasta_path.write_text(fasta_content)

        counter = KmerCounter(k=21, canonical=True)
        counter.count_file(str(fasta_path))

        self.db_path = self.temp_dir / "test.rkdb"
        counter.save_to_database(str(self.db_path))

        self.py_db = Database()
        self.py_db.load(str(self.db_path))

    def test_stats_basic(self):
        """测试基本统计功能"""
        # Python API统计
        py_stats = self.py_db.get_stats()

        # CLI统计
        cli_result = self.tester.run_cli_command([
            "stats", str(self.db_path)
        ])

        assert cli_result["success"]

        # 解析CLI输出
        cli_stats = self.parse_stats_output(cli_result["stdout"])

        # 比较关键统计指标
        assert cli_stats["total_kmers"] == py_stats.total_kmers
        assert cli_stats["unique_kmers"] == py_stats.unique_kmers
        assert cli_stats["max_count"] == py_stats.max_count
        assert cli_stats["min_count"] == py_stats.min_count

        # 允许浮点数有小幅差异
        assert abs(cli_stats["coverage"] - py_stats.coverage_estimate) < 0.01

    def test_stats_with_histogram(self):
        """测试带直方图的统计"""
        # Python API统计
        py_stats = self.py_db.get_stats()
        py_hist = py_stats.histogram

        # CLI统计（带--histogram参数）
        cli_result = self.tester.run_cli_command([
            "stats", "--histogram", str(self.db_path)
        ])

        assert cli_result["success"]

        # 解析直方图
        cli_hist = self.parse_histogram_output(cli_result["stdout"])

        # 验证直方图一致性
        for count, frequency in py_hist.items():
            if count in cli_hist:
                assert cli_hist[count] == frequency, \
                    f"直方图不一致: count={count}, CLI={cli_hist[count]}, Python={frequency}"

    def parse_stats_output(self, output: str) -> Dict[str, Any]:
        """解析CLI stats输出"""
        stats = {}
        for line in output.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                if key in ['total_kmers', 'unique_kmers', 'max_count', 'min_count']:
                    stats[key] = int(value.replace(',', ''))
                elif key == 'coverage':
                    stats[key] = float(value.rstrip('%')) / 100.0
                # 其他字段根据需要添加

        return stats

    def parse_histogram_output(self, output: str) -> Dict[int, int]:
        """解析直方图输出"""
        histogram = {}
        in_histogram = False

        for line in output.strip().split('\n'):
            if 'Histogram' in line or 'Count Distribution' in line:
                in_histogram = True
                continue

            if in_histogram and ':' in line:
                try:
                    count_str, freq_str = line.split(':', 1)
                    count = int(count_str.strip())
                    freq = int(freq_str.strip().replace(',', ''))
                    histogram[count] = freq
                except ValueError:
                    continue

        return histogram
```

### 5. Merge命令测试 (P3)

```python
# tests/python/compatibility/test_merge_compatibility.py
import pytest
from rustkmer import Database, KmerCounter, merge_databases, MergeStrategy
from .cli_comparator import CLICompatibilityTester
from .test_data import TestDataGenerator

class TestMergeCompatibility:
    """merge命令兼容性测试"""

    def setup_method(self):
        self.tester = CLICompatibilityTester()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.setup_test_databases()

    def setup_test_databases(self):
        """创建多个测试数据库"""
        # 数据库1
        seqs1 = ["ATCG" * 10, "GCTA" * 10]
        fasta1 = "\n".join([f">seq1_{i}\n{seq}" for i, seq in enumerate(seqs1)])
        fasta1_path = self.temp_dir / "db1.fa"
        fasta1_path.write_text(fasta1)

        counter1 = KmerCounter(k=21, canonical=True)
        counter1.count_file(str(fasta1_path))
        self.db1_path = self.temp_dir / "db1.rkdb"
        counter1.save_to_database(str(self.db1_path))

        # 数据库2（部分重叠）
        seqs2 = ["ATCG" * 5 + "TTTT" * 5, "AAAA" * 10]
        fasta2 = "\n".join([f">seq2_{i}\n{seq}" for i, seq in enumerate(seqs2)])
        fasta2_path = self.temp_dir / "db2.fa"
        fasta2_path.write_text(fasta2)

        counter2 = KmerCounter(k=21, canonical=True)
        counter2.count_file(str(fasta2_path))
        self.db2_path = self.temp_dir / "db2.rkdb"
        counter2.save_to_database(str(self.db2_path))

    def test_merge_sum_strategy(self):
        """测试求和合并策略"""
        # Python API合并
        py_merged_path = self.temp_dir / "py_merged.rkdb"
        py_merged_db = merge_databases(
            [str(self.db1_path), str(self.db2_path)],
            py_merged_path,
            strategy=MergeStrategy.SUM
        )

        # CLI合并
        cli_merged_path = self.temp_dir / "cli_merged.rkdb"
        cli_result = self.tester.run_cli_command([
            "merge", "-o", cli_merged_path,
            "--strategy", "sum",
            str(self.db1_path), str(self.db2_path)
        ])

        assert cli_result["success"]

        # 比较合并结果
        cli_merged_db = Database()
        cli_merged_db.load(str(cli_merged_path))

        # 验证总数
        assert cli_merged_db.total_kmers == py_merged_db.total_kmers
        assert cli_merged_db.unique_kmers == py_merged_db.unique_kmers

        # 验证特定k-mer的计数
        test_kmers = ["ATCGATCGATCGATCGATCGAT"]
        for kmer in test_kmers:
            py_result = py_merged_db.query(kmer)
            cli_result = cli_merged_db.query(kmer)

            assert py_result.found == cli_result.found
            if py_result.found:
                assert py_result.count == cli_result.count
```

## 性能对比测试

### 性能测试框架

```python
# tests/python/compatibility/performance_comparison.py
import time
import statistics
from contextlib import contextmanager
from .cli_comparator import CLICompatibilityTester

class PerformanceComparator:
    """性能对比测试框架"""

    def __init__(self):
        self.tester = CLICompatibilityTester()

    @contextmanager
    def timer(self):
        """计时上下文管理器"""
        start = time.time()
        yield
        end = time.time()
        yield end - start

    def benchmark_query_performance(self, db_path: str, kmer_list: List[str],
                                   iterations: int = 5) -> Dict[str, Any]:
        """对比查询性能"""
        py_times = []
        cli_times = []

        # Python API性能测试
        from rustkmer import Database
        db = Database()
        db.load(db_path)

        for _ in range(iterations):
            with self.timer() as py_t:
                for kmer in kmer_list:
                    db.query(kmer)
            py_times.append(py_t)

        # CLI性能测试
        kmer_file = "/tmp/test_kmers.txt"
        with open(kmer_file, 'w') as f:
            f.write('\n'.join(kmer_list))

        for _ in range(iterations):
            with self.timer() as cli_t:
                self.tester.run_cli_command([
                    "query", "-f", kmer_file, db_path
                ])
            cli_times.append(cli_t)

        return {
            "python": {
                "mean": statistics.mean(py_times),
                "median": statistics.median(py_times),
                "std": statistics.stdev(py_times) if len(py_times) > 1 else 0
            },
            "cli": {
                "mean": statistics.mean(cli_times),
                "median": statistics.median(cli_times),
                "std": statistics.stdev(cli_times) if len(cli_times) > 1 else 0
            },
            "ratio": statistics.mean(cli_times) / statistics.mean(py_times)
        }
```

## 持续集成集成

### GitHub Actions工作流更新

```yaml
# .github/workflows/compatibility-tests.yml
name: CLI-Python Compatibility Tests

on:
  push:
    branches: [ main, "012-python-bindings-complete" ]
  pull_request:
    branches: [ main ]

jobs:
  compatibility:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Setup Rust
      uses: dtolnay/rust-toolchain@stable

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Build CLI
      run: cargo build --release

    - name: Build Python bindings
      run: |
        pip install maturin
        maturin develop --release

    - name: Run compatibility tests
      run: |
        python -m pytest tests/python/compatibility/ -v

    - name: Run performance comparison
      run: |
        python tests/python/compatibility/performance_comparison.py

    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: compatibility-results-${{ matrix.os }}-py${{ matrix.python-version }}
        path: |
          test_results/
          performance_reports/
```

## 执行计划

### 第一阶段：实现测试框架
1. 创建CLICompatibilityTester基类
2. 实现TestDataGenerator
3. 建立基础的测试数据集

### 第二阶段：核心功能测试
1. 实现count命令测试
2. 实现query命令测试
3. 确保P1功能完全兼容

### 第三阶段：高级功能测试
1. 实现fuzzy-query测试
2. 实现stats测试
3. 实现merge测试

### 第四阶段：性能和稳定性
1. 实现性能对比测试
2. 大数据集测试
3. 边界情况测试

### 第五阶段：CI/CD集成
1. 集成到GitHub Actions
2. 自动化报告生成
3. 性能回归检测

## 成功标准

1. **功能一致性**：所有Python API输出与CLI完全一致
2. **性能要求**：Python API性能在CLI的110%以内
3. **测试覆盖**：100%的API功能都有兼容性测试
4. **自动化**：所有测试在CI中自动运行

这个测试计划确保Python API与CLI版本的功能完全一致，为用户提供无缝的切换体验。