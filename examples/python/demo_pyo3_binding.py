#!/usr/bin/env python3
"""
PyO3 Binding Demo Script
演示如何使用 PyO3 Python binding 执行前缀查询

Usage:
    python3 demo_pyo3_binding.py
"""

import sys
import os
import tempfile
import subprocess

# 添加当前目录到 Python 路径
sys.path.insert(0, '/Users/forrest/Github/rustkmer/examples/python')

try:
    import rustkmer_pyo3
    PYO3_AVAILABLE = True
except ImportError:
    PYO3_AVAILABLE = False
    print("⚠️  PyO3 扩展未加载，请先构建扩展")


def create_test_database():
    """创建一个测试数据库"""
    print("🔧 创建测试数据库...")
    
    # 创建临时FASTA文件
    fasta_content = """>test_sequence_1
AAAAAAAAAAATTTTTTTTTTCCCCCCCCCCGGGGGGGGGG
>test_sequence_2  
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
>test_sequence_3
AAAAAAAAAAACCCCCCCCGGGGGGGGGGTTTTTTTTTT
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        f.write(fasta_content)
        fasta_file = f.name
    
    # 创建临时数据库文件
    db_file = tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False)
    db_file.close()
    
    try:
        # 使用Rust CLI创建数据库
        cmd = [
            '/Users/forrest/Github/rustkmer/target/release/rustkmer',
            'build-kmer-db',
            fasta_file,
            db_file.name,
            '--kmer-size', '19',
            '--load-mode', 'memory'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 测试数据库创建成功: {db_file.name}")
            return db_file.name
        else:
            print(f"❌ 数据库创建失败: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ 创建数据库时出错: {e}")
        return None
    finally:
        # 清理临时FASTA文件
        os.unlink(fasta_file)


def demo_basic_usage():
    """演示基础使用方法"""
    print("\n" + "="*60)
    print("🎯 PyO3 Binding 基础使用演示")
    print("="*60)
    
    if not PYO3_AVAILABLE:
        print("❌ PyO3 扩展不可用，跳过演示")
        return
    
    # 显示可用的类
    print("\n📋 可用的 PyO3 类:")
    classes = [x for x in dir(rustkmer_pyo3) if not x.startswith('_') and x[0].isupper()]
    for cls in classes:
        print(f"   • {cls}")
    
    # 创建测试数据库
    db_path = create_test_database()
    if not db_path:
        print("❌ 无法创建测试数据库，跳过实际演示")
        return
    
    try:
        print(f"\n🔍 初始化查询引擎...")
        engine = rustkmer_pyo3.PyPrefixQuery(db_path)
        print("✅ 查询引擎创建成功!")
        
        # 显示数据库信息
        print(f"\n📊 数据库信息:")
        db_info = engine.database_info()
        for key, value in db_info.items():
            print(f"   {key}: {value}")
        
        # 演示前缀查询
        print(f"\n🔤 前缀查询演示:")
        prefix_patterns = ["AAAAAAAAA", "ATCGATCGAT"]
        for pattern in prefix_patterns:
            try:
                results = engine.query_prefix_string(pattern)
                print(f"   模式 '{pattern}': 找到 {len(results)} 个结果")
                if results:
                    sample = list(results.items())[:3]
                    for kmer, count in sample:
                        print(f"     {kmer}: {count}")
                    if len(results) > 3:
                        print(f"     ... 还有 {len(results) - 3} 个结果")
            except Exception as e:
                print(f"   模式 '{pattern}': 查询失败 - {e}")
        
        # 演示混合搜索
        print(f"\n🎯 混合搜索演示:")
        hybrid_patterns = ["AAAAA{N5}GGGGG", "ATCG{N3}GCTA"]
        for pattern in hybrid_patterns:
            try:
                # 先解析模式
                pattern_info = engine.parse_pattern(pattern)
                print(f"   模式解析 '{pattern}':")
                print(f"     前缀: '{pattern_info['prefix']}'")
                print(f"     后缀: '{pattern_info['suffix']}'")
                print(f"     N数量: {pattern_info['n_count']}")
                
                # 执行查询
                results = engine.query_hybrid(pattern)
                print(f"     查询结果: 找到 {len(results)} 个结果")
                if results:
                    sample = list(results.items())[:2]
                    for kmer, count in sample:
                        print(f"       {kmer}: {count}")
                    
            except Exception as e:
                print(f"   模式 '{pattern}': 查询失败 - {e}")
        
        # 演示扩展查询引擎
        print(f"\n📈 扩展查询引擎演示:")
        try:
            extended_engine = rustkmer_pyo3.PyExtendedPrefixQuery(db_path)
            
            # 带指标的查询
            metrics = extended_engine.query_prefix_metrics("AAAAAAAAA")
            print(f"   前缀查询指标:")
            print(f"     执行时间: {metrics.execution_time_ms} ms")
            print(f"     总匹配数: {metrics.total_matches}")
            print(f"     内存块大小: {metrics.block_size}")
            
        except Exception as e:
            print(f"   扩展引擎演示失败: {e}")
        
    finally:
        # 清理测试数据库
        try:
            os.unlink(db_path)
            print(f"\n🧹 清理测试数据库: {db_path}")
        except:
            pass


def demo_command_equivalence():
    """演示命令等价性"""
    print("\n" + "="*60)
    print("🔄 命令等价性演示")
    print("="*60)
    
    print("\n📝 Rust CLI 命令:")
    print("   ./target/release/rustkmer prefix-query ~/Data/data/kmer/K19/R1_001.rkdb AAAAAAAA{N5}AAAAAA")
    
    print("\n🐍 Python PyO3 等价代码:")
    print("""
   import rustkmer_pyo3
   
   # 创建查询引擎
   engine = rustkmer_pyo3.PyPrefixQuery("~/Data/data/kmer/K19/R1_001.rkdb")
   
   # 执行混合搜索
   results = engine.query_hybrid("AAAAAAAA{N5}AAAAAA")
   
   # 处理结果
   for kmer, count in results.items():
       print(f"{kmer}: {count}")
    """)
    
    print("\n📋 简化脚本使用:")
    print("   python3 simple_prefix_query.py ~/Data/data/kmer/K19/R1_001.rkdb 'AAAAAAAA{N5}AAAAAA'")
    
    print("\n🎛️  完整脚本使用:")
    print("   python3 prefix_query_pyo3_binding.py ~/Data/data/kmer/K19/R1_001.rkdb 'AAAAAAAA{N5}AAAAAA' --with-metrics")


def demo_pattern_syntax():
    """演示模式语法"""
    print("\n" + "="*60)
    print("📝 模式语法演示")
    print("="*60)
    
    patterns = {
        "纯前缀": "AAAAAAAA",
        "中等前缀": "ATCGATCGATCG",
        "短前缀+混合": "A{N5}T",
        "长前缀+混合": "ATCGATCG{N3}GCTA", 
        "复杂混合": "AAAAA{N2}TTTTT{N2}GGGGG",
        "全N": "NNNNNNNNNNNNNNNNNNN"
    }
    
    print("\n🔍 支持的模式类型:")
    for desc, pattern in patterns.items():
        print(f"   {desc}: {pattern}")
    
    if PYO3_AVAILABLE:
        # 创建临时数据库用于模式演示
        db_path = create_test_database()
        if db_path:
            try:
                engine = rustkmer_pyo3.PyPrefixQuery(db_path)
                
                print(f"\n🧪 模式解析演示:")
                for desc, pattern in list(patterns.items())[:3]:  # 只演示前3个
                    try:
                        info = engine.parse_pattern(pattern)
                        print(f"   {desc} ({pattern}):")
                        print(f"     前缀: '{info['prefix']}'")
                        print(f"     后缀: '{info['suffix']}'")
                        print(f"     N数量: {info['n_count']}")
                        print(f"     总长度: {info['total_length']}")
                    except Exception as e:
                        print(f"   {desc} ({pattern}): 解析失败 - {e}")
                
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass


def main():
    """主演示函数"""
    print("🚀 PyO3 Python Binding 完整演示")
    print("="*60)
    
    # 检查PyO3可用性
    if not PYO3_AVAILABLE:
        print("⚠️  PyO3 扩展未加载")
        print("💡 请先运行以下命令构建扩展:")
        print("   cd rustkmer/pyo3")
        print("   export RUSTFLAGS='-C link-arg=-undefined -C link-arg=dynamic_lookup'")
        print("   export PYO3_PYTHON=/usr/bin/python3")  
        print("   cargo build")
        print("   export PYTHONPATH='$PWD/target/debug:$PYTHONPATH'")
        return
    
    # 执行演示
    demo_basic_usage()
    demo_command_equivalence()
    demo_pattern_syntax()
    
    print("\n" + "="*60)
    print("✅ PyO3 Binding 演示完成!")
    print("="*60)
    
    print(f"\n📚 更多信息请参考:")
    print(f"   • PYO3_PYTHON_BINDING_GUIDE.md - 完整使用指南")
    print(f"   • README.md - 项目总览")
    print(f"   • PREFIX_QUERY_USAGE_GUIDE.md - 前缀查询指南")


if __name__ == "__main__":
    main()

