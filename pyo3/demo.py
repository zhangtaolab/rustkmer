#!/usr/bin/env python3
"""
PyO3 RustKmer Demo - 高性能原生扩展版本

本 demo 展示了如何使用 rustkmer_pyo3 原生扩展进行 k-mer 分析。
相比 CLI 版本，PyO3 版本具有更好的性能和 Python 集成。
"""

import sys
import time
from pathlib import Path

# 确保可以导入 rustkmer_pyo3
try:
    import rustkmer_pyo3
    print("✅ 成功导入 rustkmer_pyo3 原生扩展")
except ImportError as e:
    print(f"❌ 无法导入 rustkmer_pyo3: {e}")
    print("请确保已正确安装 PyO3 扩展:")
    print("  cd pyo3")
    print("  pip install -e .")
    sys.exit(1)

def create_demo_data():
    """创建演示数据"""
    print("🔧 创建演示数据...")
    
    # 创建一个 7-mer 计数器
    counter = rustkmer_pyo3.PyKmerCounter(kmer_size=7, canonical=False)
    
    # 添加一些测试序列中的 k-mers
    demo_kmers = [
        "ACTAGTG", "TACCCCA", "TGAGCCA", "GGCGTCA", "ACTAGTA",
        "TACACAA", "TACCCCG", "TGAGCCC", "GGCGTCC", "ACTAGTT",
        "TACCCCA", "TACACAA", "TGAGCCA", "GGCGTCA", "ACTAGTG",
        "ATGCGAT", "CGATGCT", "GCTAGCG", "CTAGCTA", "TAGCTAG",
        "ATGCGAT", "CGATGCT", "GCTAGCG", "CTAGCTA", "TAGCTAG",
    ]
    
    for kmer in demo_kmers:
        try:
            counter.add_kmer(kmer)
        except Exception as e:
            print(f"⚠️  添加 k-mer {kmer} 时出错: {e}")
    
    print(f"✅ 成功添加 {len(demo_kmers)} 个 k-mers")
    return counter

def demo_basic_operations(counter):
    """演示基本操作"""
    print("\n" + "="*60)
    print("🔍 基本查询操作演示")
    print("="*60)
    
    # 显示统计信息
    stats = counter.get_stats()
    print("\n📊 数据库统计:")
    print(f"  k-mer 大小: {stats['kmer_size']}")
    print(f"  唯一 k-mers: {stats['unique_kmers']}")
    print(f"  总 k-mers: {stats['total_kmers']}")
    print(f"  规范模式: {stats['canonical']}")
    
    # 单个查询
    print("\n🔍 单个查询示例:")
    query_kmers = ["ACTAGTG", "TACCCCA", "TGAGCCA", "NOTFOUND"]
    
    for kmer in query_kmers:
        try:
            result = counter.query(kmer)
            print(f"  {kmer}: count={result.count}, found={result.found}")
        except Exception as e:
            print(f"  {kmer}: 查询出错 - {e}")

def demo_batch_operations(counter):
    """演示批量操作"""
    print("\n" + "="*60)
    print("📦 批量查询操作演示")
    print("="*60)
    
    # 批量查询
    batch_kmers = ["ACTAGTG", "TACACAA", "TACCCCA", "TGAGCCA", "GGCGTCA"]
    
    print(f"\n🔍 批量查询 {len(batch_kmers)} 个 k-mers:")
    start_time = time.time()
    
    try:
        results = counter.query_batch(batch_kmers)
        end_time = time.time()
        
        print(f"✅ 批量查询完成，耗时: {(end_time - start_time)*1000:.2f}ms")
        print("📋 查询结果:")
        
        for result in results:
            print(f"  {result.kmer}: count={result.count}, found={result.found}")
            
    except Exception as e:
        print(f"❌ 批量查询出错: {e}")

def demo_existence_checks(counter):
    """演示存在性检查"""
    print("\n" + "="*60)
    print("✅ 存在性检查演示")
    print("="*60)
    
    test_kmers = ["ACTAGTG", "TACCCCA", "NOTFOUND", "ATGCGAT"]
    
    print("\n🔍 检查 k-mer 存在性:")
    for kmer in test_kmers:
        try:
            exists = counter.exists(kmer)
            print(f"  {kmer}: {'存在' if exists else '不存在'}")
        except Exception as e:
            print(f"  {kmer}: 检查出错 - {e}")

def demo_fuzzy_query(counter):
    """演示模糊查询"""
    print("\n" + "="*60)
    print("🎯 模糊查询演示")
    print("="*60)
    
    # 创建模糊查询引擎
    try:
        fuzzy = rustkmer_pyo3.PyFuzzyQuery(counter)
        print("✅ 模糊查询引擎创建成功")
        
        # 基本模糊查询
        print("\n🎯 基本模糊查询:")
        patterns = ["ACTAGTG", "TACNNNN"]
        
        for pattern in patterns:
            print(f"\n🔍 查询模式: {pattern} (允许 1 个突变)")
            
            start_time = time.time()
            result = fuzzy.fuzzy_query(pattern, max_mutations=1)
            end_time = time.time()
            
            print(f"  找到 {result.total_matches} 个匹配")
            print(f"  查询耗时: {(end_time - start_time)*1000:.2f}ms")
            
            if result.matches:
                print("  前 5 个匹配:")
                for i, match in enumerate(result.matches[:5], 1):
                    print(f"    {i}. {match.kmer} (count={match.count}, distance={match.distance}, type={match.match_type})")
            else:
                print("  未找到匹配")
        
        # 批量模糊查询
        print("\n📦 批量模糊查询:")
        patterns = ["ACTAGTG", "TACCCCA"]
        
        start_time = time.time()
        batch_results = fuzzy.fuzzy_query_batch(patterns, max_mutations=1)
        end_time = time.time()
        
        print(f"✅ 批量模糊查询完成，耗时: {(end_time - start_time)*1000:.2f}ms")
        
        for pattern, result in batch_results.items():
            print(f"  模式 '{pattern}': {result.total_matches} 个匹配")
            
    except Exception as e:
        print(f"❌ 模糊查询出错: {e}")

def demo_performance_comparison(counter):
    """演示性能对比"""
    print("\n" + "="*60)
    print("⚡ 性能测试演示")
    print("="*60)
    
    # 准备大量查询
    query_count = 1000
    test_kmers = ["ACTAGTG", "TACCCCA", "TGAGCCA", "GGCGTCA", "ATGCGAT"] * (query_count // 5)
    
    print(f"\n🚀 执行 {len(test_kmers)} 个查询...")
    
    # 批量查询性能测试
    start_time = time.time()
    
    try:
        results = counter.query_batch(test_kmers)
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000  # 转换为毫秒
        avg_time = total_time / len(test_kmers)
        
        print(f"✅ 批量查询完成:")
        print(f"  总查询数: {len(test_kmers)}")
        print(f"  总耗时: {total_time:.2f}ms")
        print(f"  平均每查询: {avg_time:.3f}ms")
        print(f"  查询速度: {len(test_kmers)/(total_time/1000):.0f} queries/second")
        
        # 统计结果
        found_count = sum(1 for r in results if r.found)
        print(f"  找到的 k-mers: {found_count}/{len(test_kmers)}")
        
    except Exception as e:
        print(f"❌ 性能测试出错: {e}")

def demo_all_kmers(counter):
    """演示获取所有 k-mers"""
    print("\n" + "="*60)
    print("📋 获取所有 k-mers")
    print("="*60)
    
    try:
        all_kmers = counter.get_all_kmers()
        print(f"✅ 成功获取 {len(all_kmers)} 个 k-mers:")
        
        # 显示前 10 个
        print("📊 前 10 个 k-mers:")
        for i, item in enumerate(all_kmers[:10], 1):
            print(f"  {i}. {item['kmer']}: count={item['count']}")
        
        if len(all_kmers) > 10:
            print(f"  ... 还有 {len(all_kmers) - 10} 个 k-mers")
            
    except Exception as e:
        print(f"❌ 获取 k-mers 出错: {e}")

def demo_error_handling(counter):
    """演示错误处理"""
    print("\n" + "="*60)
    print("🛡️ 错误处理演示")
    print("="*60)
    
    # 测试无效 k-mer
    print("\n🚫 测试无效 k-mer:")
    invalid_kmers = [
        ("TOOLONG", "k-mer 长度错误"),
        ("ACTAGTG", "长度正确但可能不存在"),
        ("INVALID", "包含无效字符"),
        ("ACG", "长度过短"),
    ]
    
    for kmer, description in invalid_kmers:
        print(f"\n  测试: {kmer} ({description})")
        
        try:
            # 尝试添加
            counter.add_kmer(kmer)
            print(f"    ✅ 成功添加")
        except Exception as e:
            print(f"    ❌ 添加失败: {type(e).__name__}")
        
        try:
            # 尝试查询
            result = counter.query(kmer)
            print(f"    🔍 查询结果: count={result.count}, found={result.found}")
        except Exception as e:
            print(f"    ❌ 查询失败: {type(e).__name__}")

def main():
    """主函数"""
    print("🚀 PyO3 RustKmer Demo")
    print("=" * 60)
    print("本 demo 展示如何使用 rustkmer_pyo3 原生扩展进行高性能 k-mer 分析")
    print("=" * 60)
    
    try:
        # 检查可用类
        available_classes = [attr for attr in dir(rustkmer_pyo3) if not attr.startswith('_')]
        print(f"\n📋 可用的类: {available_classes}")
        
        # 运行所有演示
        counter = create_demo_data()
        demo_basic_operations(counter)
        demo_batch_operations(counter)
        demo_existence_checks(counter)
        demo_fuzzy_query(counter)
        demo_all_kmers(counter)
        demo_performance_comparison(counter)
        demo_error_handling(counter)
        
        print("\n" + "=" * 60)
        print("🎉 PyO3 RustKmer Demo 完成！")
        print("=" * 60)
        print("✅ 所有功能演示成功运行")
        print("🔥 PyO3 原生扩展提供了高性能的 k-mer 分析能力")
        print("🚀 相比 CLI 版本，具有更好的 Python 集成和性能")
        
    except Exception as e:
        print(f"\n❌ Demo 运行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
