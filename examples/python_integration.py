#!/usr/bin/env python3
"""
RustKmer Python集成示例
演示如何在Python中使用RustKmer进行高性能k-mer分析
"""

import subprocess
import tempfile
import os
import sys
import time
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RustKmerError(Exception):
    """RustKmer相关错误"""
    pass

class RustKmer:
    """RustKmer Python封装类"""

    def __init__(self, database_path: str, rustkmer_path: str = "./target/release/rustkmer"):
        """
        初始化RustKmer

        Args:
            database_path: 数据库文件路径
            rustkmer_path: RustKmer可执行文件路径
        """
        self.database_path = Path(database_path)
        self.rustkmer_path = Path(rustkmer_path)

        # 验证文件存在性
        if not self.rustkmer_path.exists():
            raise RustKmerError(f"RustKmer可执行文件不存在: {self.rustkmer_path}")

        if not self.database_path.exists():
            raise RustKmerError(f"数据库文件不存在: {self.database_path}")

        # 缓存数据库信息
        self._db_info = None

    def _run_command(self, cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """
        执行RustKmer命令

        Args:
            cmd: 命令列表
            capture_output: 是否捕获输出

        Returns:
            subprocess.CompletedProcess
        """
        try:
            if capture_output:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=300  # 5分钟超时
                )
            else:
                result = subprocess.run(
                    cmd,
                    check=True,
                    timeout=300
                )
            return result
        except subprocess.CalledProcessError as e:
            error_msg = f"RustKmer命令执行失败: {' '.join(cmd)}"
            if e.stderr:
                error_msg += f"\n错误信息: {e.stderr}"
            raise RustKmerError(error_msg)
        except subprocess.TimeoutExpired:
            raise RustKmerError(f"RustKmer命令执行超时: {' '.join(cmd)}")

    def get_database_info(self) -> Dict[str, str]:
        """
        获取数据库信息

        Returns:
            数据库信息字典
        """
        if self._db_info is None:
            cmd = [str(self.rustkmer_path), 'info', str(self.database_path)]
            result = self._run_command(cmd)

            self._db_info = {}
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    self._db_info[key.strip()] = value.strip()

        return self._db_info

    def query_kmer(self, kmer: str) -> int:
        """
        查询单个k-mer

        Args:
            kmer: k-mer序列

        Returns:
            k-mer计数
        """
        cmd = [str(self.rustkmer_path), 'query', str(self.database_path), kmer]
        result = self._run_command(cmd)

        if result.stdout.strip():
            parts = result.stdout.strip().split('\t')
            if len(parts) >= 2:
                return int(parts[1])
        return 0

    def query_kmers_batch(self, queries: List[str]) -> Dict[str, int]:
        """
        批量查询k-mers

        Args:
            queries: k-mer序列列表

        Returns:
            k-mer计数字典
        """
        # 创建临时FASTA文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            for i, query in enumerate(queries):
                f.write(f">query_{i+1}\n{query}\n")
            temp_file = f.name

        try:
            # 执行批量查询
            cmd = [
                str(self.rustkmer_path), 'query',
                str(self.database_path),
                '--sequence', temp_file
            ]
            result = self._run_command(cmd)

            # 解析结果
            results = {}
            for line in result.stdout.strip().split('\n'):
                if line and '\t' in line:
                    kmer, count = line.split('\t')
                    results[kmer] = int(count)

            return results
        finally:
            os.unlink(temp_file)

    def query_from_file(self, query_file: str, output_file: Optional[str] = None) -> Dict[str, int]:
        """
        从文件查询k-mers

        Args:
            query_file: 查询文件路径
            output_file: 输出文件路径（可选）

        Returns:
            k-mer计数字典
        """
        cmd = [
            str(self.rustkmer_path), 'query',
            str(self.database_path),
            '--sequence', query_file
        ]

        if output_file:
            cmd.extend(['-o', output_file])

        result = self._run_command(cmd)

        # 解析结果
        results = {}
        for line in result.stdout.strip().split('\n'):
            if line and '\t' in line:
                kmer, count = line.split('\t')
                results[kmer] = int(count)

        return results

    def create_database(self,
                       input_file: str,
                       kmer_size: int,
                       output_file: str,
                       threads: int = 8,
                       canonical: bool = False,
                       sort: bool = True) -> None:
        """
        创建k-mer数据库

        Args:
            input_file: 输入FASTA文件
            kmer_size: k-mer大小
            output_file: 输出数据库文件
            threads: 线程数
            canonical: 是否规范化k-mer
            sort: 是否创建排序数据库
        """
        cmd = [
            str(self.rustkmer_path), 'count',
            '-k', str(kmer_size),
            '-t', str(threads),
            '-o', output_file,
            input_file
        ]

        if canonical:
            cmd.append('-C')
        if sort:
            cmd.append('--sort')

        self._run_command(cmd, capture_output=False)

    def dump_database(self, output_file: str, max_entries: Optional[int] = None) -> None:
        """
        转储数据库内容

        Args:
            output_file: 输出文件
            max_entries: 最大条目数（可选）
        """
        cmd = [str(self.rustkmer_path), 'dump', str(self.database_path), '-o', output_file]

        if max_entries:
            cmd.extend(['--max', str(max_entries)])

        self._run_command(cmd, capture_output=False)


class RustKmerAnalyzer:
    """RustKmer高级分析类"""

    def __init__(self, database_path: str):
        self.rk = RustKmer(database_path)
        self.cache = {}  # 简单查询缓存

    def analyze_kmer_distribution(self, queries: List[str]) -> pd.DataFrame:
        """
        分析k-mer分布

        Args:
            queries: k-mer列表

        Returns:
            包含分析结果的DataFrame
        """
        start_time = time.time()

        # 批量查询
        results = self.rk.query_kmers_batch(queries)
        end_time = time.time()

        # 创建DataFrame
        df = pd.DataFrame([
            {'kmer': kmer, 'count': count}
            for kmer, count in results.items()
        ])

        if not df.empty:
            # 添加统计列
            df['log_count'] = np.log10(df['count'] + 1)
            df['rank'] = df['count'].rank(ascending=False, method='min')
            df['percentile'] = df['rank'] / len(df) * 100

        logger.info(f"分析了 {len(queries)} 个k-mers，耗时 {end_time - start_time:.2f} 秒")

        return df

    def find_most_abundant_kmers(self, queries: List[str], top_n: int = 10) -> List[Tuple[str, int]]:
        """
        找到最丰富的k-mers

        Args:
            queries: k-mer列表
            top_n: 返回前N个

        Returns:
            (kmer, count)元组列表
        """
        results = self.rk.query_kmers_batch(queries)
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_n]

    def filter_kmers_by_count(self, queries: List[str], min_count: int = 1) -> Dict[str, int]:
        """
        根据计数过滤k-mers

        Args:
            queries: k-mer列表
            min_count: 最小计数阈值

        Returns:
            过滤后的k-mer字典
        """
        results = self.rk.query_kmers_batch(queries)
        return {kmer: count for kmer, count in results.items() if count >= min_count}

    def calculate_gc_content(self, kmer: str) -> float:
        """计算GC含量"""
        gc_count = kmer.count('G') + kmer.count('C')
        return gc_count / len(kmer) * 100

    def analyze_sequence_properties(self, queries: List[str]) -> pd.DataFrame:
        """
        分析k-mer序列属性

        Args:
            queries: k-mer列表

        Returns:
            包含序列属性的DataFrame
        """
        results = self.rk.query_kmers_batch(queries)

        data = []
        for kmer, count in results.items():
            gc_content = self.calculate_gc_content(kmer)
            data.append({
                'kmer': kmer,
                'count': count,
                'gc_content': gc_content,
                'length': len(kmer),
                'has_a': 'A' in kmer,
                'has_t': 'T' in kmer,
                'has_g': 'G' in kmer,
                'has_c': 'C' in kmer
            })

        return pd.DataFrame(data)

    def benchmark_query_performance(self, query_sizes: List[int]) -> pd.DataFrame:
        """
        基准测试查询性能

        Args:
            query_sizes: 不同查询大小的列表

        Returns:
            性能测试结果DataFrame
        """
        # 生成测试查询
        all_queries = []
        for i in range(max(query_sizes)):
            kmer = ''.join(np.random.choice(list('ATGC'), 21))
            all_queries.append(kmer)

        results = []
        for size in query_sizes:
            queries = all_queries[:size]

            start_time = time.time()
            query_results = self.rk.query_kmers_batch(queries)
            end_time = time.time()

            elapsed = end_time - start_time
            qps = size / elapsed if elapsed > 0 else float('inf')

            results.append({
                'query_count': size,
                'elapsed_time': elapsed,
                'qps': qps,
                'non_zero_results': sum(1 for count in query_results.values() if count > 0)
            })

        return pd.DataFrame(results)


def basic_usage_example():
    """基本使用示例"""
    print("=== RustKmer基本使用示例 ===")

    # 数据库文件路径（需要先创建）
    database_path = "example_data/sample_k21.rkdb"

    # 检查数据库是否存在
    if not os.path.exists(database_path):
        print(f"数据库文件不存在: {database_path}")
        print("请先运行基本使用脚本创建数据库")
        return

    try:
        # 初始化RustKmer
        rk = RustKmer(database_path)

        # 显示数据库信息
        print("数据库信息:")
        info = rk.get_database_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
        print()

        # 单个查询示例
        print("单个查询示例:")
        test_kmers = [
            "ATGCGATGCTAGCGCTAGCTAT",
            "GCTAGCTAGCTAGCTAGCTAC",
            "CCCCCCCCCCCCCCCCCCCCC"  # 应该不存在
        ]

        for kmer in test_kmers:
            count = rk.query_kmer(kmer)
            print(f"  {kmer}: {count}")
        print()

        # 批量查询示例
        print("批量查询示例:")
        batch_results = rk.query_kmers_batch(test_kmers)
        for kmer, count in batch_results.items():
            print(f"  {kmer}: {count}")
        print()

    except RustKmerError as e:
        print(f"RustKmer错误: {e}")


def advanced_analysis_example():
    """高级分析示例"""
    print("=== RustKmer高级分析示例 ===")

    database_path = "example_data/sample_k21.rkdb"

    if not os.path.exists(database_path):
        print(f"数据库文件不存在: {database_path}")
        return

    try:
        # 初始化分析器
        analyzer = RustKmerAnalyzer(database_path)

        # 生成测试查询
        print("生成测试查询...")
        test_queries = []
        for i in range(1000):
            kmer = ''.join(np.random.choice(list('ATGC'), 21))
            test_queries.append(kmer)

        print(f"生成了 {len(test_queries)} 个测试查询")
        print()

        # 分析k-mer分布
        print("k-mer分布分析:")
        df = analyzer.analyze_kmer_distribution(test_queries[:100])  # 先测试100个

        if not df.empty:
            print(f"  总k-mers: {len(df)}")
            print(f"  非零计数: {(df['count'] > 0).sum()}")
            print(f"  平均计数: {df['count'].mean():.2f}")
            print(f"  中位数计数: {df['count'].median():.2f}")
            print(f"  最大计数: {df['count'].max()}")
            print()

            # 显示前10个最丰富的k-mers
            print("前10个最丰富的k-mers:")
            top_kmers = df.nlargest(10, 'count')
            for _, row in top_kmers.iterrows():
                print(f"  {row['kmer']}: {row['count']}")
            print()

        # 序列属性分析
        print("序列属性分析:")
        seq_df = analyzer.analyze_sequence_properties(test_queries[:50])
        if not seq_df.empty:
            print(f"  平均GC含量: {seq_df['gc_content'].mean():.2f}%")
            print(f"  GC含量范围: {seq_df['gc_content'].min():.2f}% - {seq_df['gc_content'].max():.2f}%")
            print()

        # 性能基准测试
        print("性能基准测试:")
        query_sizes = [10, 50, 100, 500, 1000]
        perf_df = analyzer.benchmark_query_performance(query_sizes)

        for _, row in perf_df.iterrows():
            print(f"  {row['query_count']} 查询: {row['elapsed_time']:.3f}s, QPS: {row['qps']:.0f}")
        print()

    except RustKmerError as e:
        print(f"RustKmer错误: {e}")


def create_database_example():
    """创建数据库示例"""
    print("=== 创建数据库示例 ===")

    # 创建示例FASTA文件
    example_fa = "example_data/example_genome.fa"
    os.makedirs("example_data", exist_ok=True)

    with open(example_fa, 'w') as f:
        f.write(">seq1\n")
        f.write("ATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCT\n")
        f.write(">seq2\n")
        f.write("GCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAC\n")
        f.write(">seq3\n")
        f.write("ATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT\n")

    try:
        # 使用基本的RustKmer实例来创建数据库
        temp_rk = RustKmer.__new__(RustKmer)  # 跳过初始化验证

        output_db = "example_data/example_k21.rkdb"
        print(f"创建数据库: {output_db}")

        temp_rk.create_database(
            input_file=example_fa,
            kmer_size=21,
            output_file=output_db,
            threads=4,
            canonical=False,
            sort=True
        )

        print("数据库创建成功!")

        # 验证数据库
        rk = RustKmer(output_db)
        info = rk.get_database_info()
        print("数据库信息:")
        for key, value in info.items():
            print(f"  {key}: {value}")

    except RustKmerError as e:
        print(f"创建数据库失败: {e}")


def export_results_example():
    """导出结果示例"""
    print("=== 导出结果示例 ===")

    database_path = "example_data/sample_k21.rkdb"

    if not os.path.exists(database_path):
        print(f"数据库文件不存在: {database_path}")
        return

    try:
        rk = RustKmer(database_path)

        # 生成测试查询
        test_queries = []
        for i in range(100):
            kmer = ''.join(np.random.choice(list('ATGC'), 21))
            test_queries.append(kmer)

        # 执行查询
        results = rk.query_kmers_batch(test_queries)

        # 转换为DataFrame
        df = pd.DataFrame([
            {'kmer': kmer, 'count': count}
            for kmer, count in results.items()
        ])

        # 排序
        df = df.sort_values('count', ascending=False)

        # 添加统计列
        df['rank'] = range(1, len(df) + 1)
        df['percentile'] = df['rank'] / len(df) * 100

        # 导出到CSV
        output_csv = "example_data/kmer_analysis_results.csv"
        df.to_csv(output_csv, index=False)

        print(f"结果已导出到: {output_csv}")
        print(f"总计 {len(df)} 个k-mer")
        print(f"非零计数: {(df['count'] > 0).sum()}")

        # 显示前几行
        print("\n前10个结果:")
        print(df.head(10).to_string(index=False))

    except RustKmerError as e:
        print(f"导出结果失败: {e}")


def main():
    """主函数"""
    print("RustKmer Python集成示例")
    print("=" * 50)
    print()

    # 运行所有示例
    examples = [
        create_database_example,
        basic_usage_example,
        advanced_analysis_example,
        export_results_example
    ]

    for example_func in examples:
        try:
            example_func()
            print("-" * 50)
            print()
        except Exception as e:
            print(f"示例执行失败 {example_func.__name__}: {e}")
            print("-" * 50)
            print()


if __name__ == "__main__":
    main()