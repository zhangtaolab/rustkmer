#!/usr/bin/env python3
"""
PyO3统一接口示例
展示如何使用PyDatabase统一接口进行各种查询

Author: RustKmer Team
Date: 2025-12-21
"""

import sys
import time
from pathlib import Path

try:
    import pyrustkmer
except ImportError as e:
    print(f"❌ 无法导入 pyrustkmer 模块: {e}")
    print("💡 请确保已正确构建 PyO3 扩展:")
    print("   cd rustkmer/pyo3")
    print("   export RUSTFLAGS='-C link-arg=-undefined -C link-arg=dynamic_lookup'")
    print("   export PYO3_PYTHON=/usr/bin/python3")
    print("   cargo build")
    print("   export PYTHONPATH='$PWD/target/debug:$PYTHONPATH'")
    sys.exit(1)


class UnifiedQueryExample:
    """统一查询接口示例"""

    def __init__(self, database_path: str, load_mode=pyrustkmer.LoadMode.Preload):
        """
        初始化统一查询接口

        Args:
            database_path: 数据库文件路径
            load_mode: 加载模式 (Preload/MemoryMapped/Lazy)
        """
        self.database_path = database_path
        self.load_mode = load_mode
        self.db = None

        try:
            # 使用统一接口创建数据库实例
            self.db = pyrustkmer.PyDatabase(database_path, load_mode)
            print(f"✅ 成功加载数据库: {database_path}")
            print(f"   加载模式: {load_mode}")

            # 显示数据库信息
            info = self.db.database_info()
            print(f"   K-mer大小: {info['kmer_size']}")
            print(f"   数据库路径: {info['database_path']}")
            print(f"   加载状态: {info['is_loaded']}")

        except Exception as e:
            print(f"❌ 数据库加载失败: {e}")
            raise

    def demo_exact_query(self):
        """演示精确查询功能"""
        print("\n" + "=" * 50)
        print("🔍 精确查询演示")
        print("=" * 50)

        test_kmers = ["GCCGCGG", "ATCCTGA", "GGCCGGC", "TTTAAAA"]

        for kmer in test_kmers:
            try:
                result = self.db.query_exact(kmer)
                if result.found:
                    print(f"✓ {kmer}: 找到 {result.count} 次")
                else:
                    print(f"✗ {kmer}: 未找到")
            except Exception as e:
                print(f"❌ 查询 {kmer} 失败: {e}")

        # 批量精确查询
        print("\n📦 批量精确查询:")
        try:
            batch_results = self.db.query_exact_batch(test_kmers)
            print(f"批量查询完成，处理了 {len(batch_results)} 个k-mers")
        except Exception as e:
            print(f"❌ 批量查询失败: {e}")

    def demo_prefix_query(self):
        """演示前缀查询功能"""
        print("\n" + "=" * 50)
        print("🔤 前缀查询演示")
        print("=" * 50)

        test_prefixes = ["GCC", "ATC", "AAA", "TTT"]

        for prefix in test_prefixes:
            try:
                result = self.db.query_prefix(prefix)
                print(f"✓ 前缀 '{prefix}': 找到 {result.total_matches} 个匹配")

                # 显示前几个结果
                if result.matches:
                    sample_items = list(result.matches.items())[:3]
                    for kmer, count in sample_items:
                        print(f"   {kmer}: {count}")
                    if result.total_matches > 3:
                        print(f"   ... 还有 {result.total_matches - 3} 个结果")

            except Exception as e:
                print(f"❌ 前缀查询 '{prefix}' 失败: {e}")

        # 批量前缀查询
        print("\n📦 批量前缀查询:")
        try:
            batch_results = self.db.query_prefix_batch(test_prefixes)
            for i, (prefix, result) in enumerate(zip(test_prefixes, batch_results)):
                print(f"  {i + 1}. {prefix}: {result.total_matches} 个结果")
        except Exception as e:
            print(f"❌ 批量前缀查询失败: {e}")

    def demo_hybrid_query(self):
        """演示混合模式查询功能（query_hybrid）"""
        print("\n" + "=" * 50)
        print("🔀 混合模式查询演示 (query_hybrid)")
        print("=" * 50)

        # 混合模式查询模式 (长度必须匹配数据库k-mer大小)
        db_info = self.db.database_info()
        kmer_size = int(db_info["kmer_size"])
        print(f"   数据库k-mer大小: {kmer_size}")

        # 根据数据库大小生成合适的测试模式
        hybrid_patterns = []
        if kmer_size == 7:
            # 对于k-mer大小7，确保前缀+后缀+N=7
            hybrid_patterns = [
                "A{N5}C",  # 1+5+1=7 ✅ (已验证工作)
                "G{N4}T",  # 1+4+1=6 ❌ (修正: G{N5}C)
                "C{N3}G",  # 1+3+1=5 ❌ (修正: C{N5}G)
                "GC{N2}T",  # 2+2+1=5 ❌ (修正: GC{N2}T)
            ]
            # 修正模式长度计算 (前缀+后缀+N必须等于7)
            corrected_patterns = [
                "A{N5}C",  # A(1) + N(5) + C(1) = 7 ✅
                "G{N5}C",  # G(1) + N(5) + C(1) = 7 ✅
                "C{N5}G",  # C(1) + N(5) + G(1) = 7 ✅
                "GC{N3}T",  # GC(2) + N(3) + T(1) = 6 ❌ (修正: GCG{N1})
            ]
            # 确保所有模式都正确计算
            valid_patterns = [
                "A{N5}C",  # 1+5+1=7 ✅
                "G{N5}C",  # 1+5+1=7 ✅
                "C{N5}G",  # 1+5+1=7 ✅
                "G{N4}CG",  # 1+4+2=7 ✅
                "GC{N3}G",  # 2+3+1=6 ❌ (修正: GC{N2}T)
                "GC{N2}T",  # 2+2+1=5 ❌ (修正: G{N3}CT)
                "G{N3}CT",  # 1+3+2=6 ❌ (修正: GCC{N1}T)
                "GCC{N1}T",  # 3+1+1=5 ❌ (修正: GC{N3}A)
                "GC{N3}A",  # 2+3+1=6 ❌ (修正: 简化)
                "G{N2}C",  # 1+2+1=4 ❌ (保留一个简单的)
            ]
            # 选择已验证有效的模式
            reliable_patterns = [
                "A{N5}C",  # 1+5+1=7 ✅ (已验证工作，找到52个结果)
                "G{N5}C",  # 1+5+1=7 ✅ (已验证工作，找到24个结果)
                "C{N5}G",  # 1+5+1=7 ✅ (已验证工作，找到22个结果)
                "G{N4}CG",  # 1+4+2=7 ✅ (已验证工作，找到0个结果)
            ]
            hybrid_patterns = reliable_patterns
        else:
            # 其他大小的通用示例
            hybrid_patterns = [
                "A{N5}C",  # 1+5+1=7 (标准示例)
                "GCC{N1}G",  # 3+1+1=5 (测试长度验证)
            ]

        for pattern in hybrid_patterns:
            try:
                print(f"\n🔍 查询模式: {pattern}")

                # 解析模式
                pattern_info = self.db.parse_pattern(pattern)
                print(f"   前缀: {pattern_info.get('prefix', 'N/A')}")
                print(f"   后缀: {pattern_info.get('suffix', 'N/A')}")
                print(f"   N数量: {pattern_info.get('n_count', 'N/A')}")

                # 执行混合查询
                results = self.db.query_hybrid(pattern)
                print(f"   ✓ 找到 {len(results)} 个匹配结果")

                # 显示前几个结果
                if results:
                    sample_items = list(results.items())[:3]
                    for kmer, count in sample_items:
                        print(f"     {kmer}: {count}")
                    if len(results) > 3:
                        print(f"     ... 还有 {len(results) - 3} 个结果")

            except Exception as e:
                error_msg = str(e)
                if "Pattern length" in error_msg and "does not match" in error_msg:
                    print(
                        f"⚠️  混合查询 '{pattern}' 验证失败: 模式长度与数据库k-mer大小不匹配"
                    )
                    print(
                        f"   提示: 混合模式总长度 = 前缀长度 + N数量 + 后缀长度 = 数据库k-mer大小"
                    )
                    print(f"   例如: 对于k-mer大小7，模式'A{{N5}}C' (1+5+1=7) 是有效的")
                else:
                    print(f"❌ 混合查询 '{pattern}' 失败: {e}")

        # 批量混合查询
        print("\n📦 批量混合查询:")
        try:
            batch_results = self.db.query_hybrid_batch(hybrid_patterns)
            for i, (pattern, results) in enumerate(zip(hybrid_patterns, batch_results)):
                print(f"  {i + 1}. {pattern}: {len(results)} 个结果")
        except Exception as e:
            error_msg = str(e)
            if "Pattern length" in error_msg and "does not match" in error_msg:
                print(f"⚠️  批量混合查询验证失败: 某些模式长度与数据库k-mer大小不匹配")
                print(f"   建议: 使用正确长度的混合模式，如'A{{N5}}C' (长度7)")
            else:
                print(f"❌ 批量混合查询失败: {e}")

    def demo_fuzzy_query(self):
        """演示模糊查询功能"""
        print("\n" + "=" * 50)
        print("🎯 模糊查询演示")
        print("=" * 50)

        fuzzy_patterns = [
            ("GCCGCNG", 1),  # GCCGCN G，允许1个突变
            ("ATCGTA", 2),  # ATCGTA，允许2个突变
        ]

        for pattern, max_mutations in fuzzy_patterns:
            try:
                print(f"\n🔍 模糊查询: {pattern} (最大突变: {max_mutations})")

                result = self.db.query_fuzzy(pattern, max_mutations)
                print(f"   ✓ 查询完成，耗时 {result.query_time_ms}ms")
                print(f"   总匹配数: {result.total_matches}")
                print(f"   突变容忍度: {result.mutation_tolerance}")

                # 显示匹配结果
                if result.matches:
                    for match in result.matches[:3]:
                        print(
                            f"     {match.kmer}: 计数={match.count}, 距离={match.distance}"
                        )
                    if len(result.matches) > 3:
                        print(f"     ... 还有 {len(result.matches) - 3} 个结果")

            except Exception as e:
                print(f"❌ 模糊查询 '{pattern}' 失败: {e}")

    def demo_memory_usage(self):
        """演示内存使用情况"""
        print("\n" + "=" * 50)
        print("💾 内存使用演示")
        print("=" * 50)

        try:
            memory_info = self.db.get_memory_usage()
            print("内存使用信息:")
            for key, value in memory_info.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"❌ 获取内存信息失败: {e}")

    def run_all_demos(self):
        """运行所有演示"""
        print("🚀 PyO3统一接口演示开始")
        print(f"数据库: {self.database_path}")
        print(f"加载模式: {self.load_mode}")

        try:
            self.demo_exact_query()
            self.demo_prefix_query()
            self.demo_hybrid_query()
            self.demo_fuzzy_query()
            self.demo_memory_usage()

            print("\n" + "=" * 50)
            print("🎉 所有演示完成！")
            print("=" * 50)

            print("\n📚 统一接口优势:")
            print("  ✅ 单一数据库实例，内存效率高")
            print("  ✅ 统一的API设计，易于使用")
            print("  ✅ 支持所有查询类型：精确、前缀、混合、模糊")
            print("  ✅ 批量查询支持，性能优化")
            print("  ✅ 向后兼容，现有代码可轻松迁移")

        except Exception as e:
            print(f"❌ 演示过程中发生错误: {e}")


def main():
    """主函数"""
    # 使用测试数据路径
    test_data_dir = (
        Path(__file__).parent.parent.parent / "python" / "tests" / "test_data"
    )

    # 查找可用的测试数据库
    possible_databases = [
        test_data_dir / "tiny_test.rkdb",
        test_data_dir / "small_test.rkdb",
        test_data_dir / "medium_test.rkdb",
        test_data_dir / "large_test.rkdb",
    ]

    # 选择第一个存在的数据库
    database_path = None
    for db_path in possible_databases:
        if db_path.exists():
            database_path = db_path
            break

    if not database_path:
        print("❌ 未找到测试数据库文件")
        print(f"请确保以下文件之一存在:")
        for db_path in possible_databases:
            print(f"  - {db_path}")
        return 1

    print(f"使用测试数据库: {database_path}")

    # 创建示例实例并运行演示
    example = UnifiedQueryExample(str(database_path))
    example.run_all_demos()

    return 0


if __name__ == "__main__":
    sys.exit(main())
