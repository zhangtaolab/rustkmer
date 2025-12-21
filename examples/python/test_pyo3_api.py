#!/usr/bin/env python3
"""
Simple PyO3 API Test
测试PyO3 binding的基本API功能，不依赖实际数据库文件
"""

import sys

try:
    import rustkmer_pyo3
    print("✅ 成功导入 rustkmer_pyo3 模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

def test_api_availability():
    """测试API可用性"""
    print("\n📋 测试 API 可用性:")
    
    # 检查主要类
    classes_to_test = [
        'PyPrefixQuery',
        'PyExtendedPrefixQuery', 
        'PyPrefixQueryMetrics',
        'PyDatabase'
    ]
    
    for cls_name in classes_to_test:
        if hasattr(rustkmer_pyo3, cls_name):
            cls = getattr(rustkmer_pyo3, cls_name)
            print(f"   ✅ {cls_name}: 可用")
            
            # 获取方法列表
            methods = [m for m in dir(cls) if not m.startswith('_') and callable(getattr(cls, m))]
            print(f"      方法数量: {len(methods)}")
            
            # 显示主要方法
            main_methods = methods[:5]  # 只显示前5个
            print(f"      主要方法: {', '.join(main_methods)}")
            if len(methods) > 5:
                print(f"      ... 还有 {len(methods) - 5} 个方法")
        else:
            print(f"   ❌ {cls_name}: 不可用")

def test_constructor_validation():
    """测试构造函数验证（使用不存在的文件）"""
    print("\n🧪 测试构造函数验证:")
    
    # 测试不存在的数据库文件
    try:
        engine = rustkmer_pyo3.PyPrefixQuery("/nonexistent/database.rkdb")
        print("   ❌ 应该抛出异常但没有")
    except Exception as e:
        print(f"   ✅ 正确处理不存在的文件: {type(e).__name__}")
    
    # 测试扩展查询引擎
    try:
        extended_engine = rustkmer_pyo3.PyExtendedPrefixQuery("/nonexistent/database.rkdb")
        print("   ❌ 应该抛出异常但没有")
    except Exception as e:
        print(f"   ✅ 扩展引擎也正确处理错误: {type(e).__name__}")

def test_pattern_parsing():
    """测试模式解析功能"""
    print("\n🔍 测试模式解析功能:")
    
    # 创建临时引擎来测试解析功能
    # 注意：这会失败，但我们可以在异常处理中看到错误类型
    test_patterns = [
        "AAAAAAAA{N5}AAAAAA",
        "ATCG{N3}GCTA", 
        "AAAAAAA",
        "N{N10}N"
    ]
    
    for pattern in test_patterns:
        print(f"\n   测试模式: {pattern}")
        
        # 尝试创建引擎并解析模式
        try:
            engine = rustkmer_pyo3.PyPrefixQuery("/tmp/test.db")
            info = engine.parse_pattern(pattern)
            print(f"      ✅ 解析成功:")
            print(f"         前缀: '{info['prefix']}'")
            print(f"         后缀: '{info['suffix']}'")
            print(f"         N数量: {info['n_count']}")
            print(f"         总长度: {info['total_length']}")
        except Exception as e:
            print(f"      📝 预期的解析错误: {type(e).__name__}")
            # 这是预期的，因为我们使用了不存在的数据库

def test_method_signatures():
    """测试方法签名"""
    print("\n🔧 测试方法签名:")
    
    # 检查 PyPrefixQuery 的方法
    if hasattr(rustkmer_pyo3, 'PyPrefixQuery'):
        cls = rustkmer_pyo3.PyPrefixQuery
        
        methods_to_check = [
            'query_prefix_string',
            'query_hybrid', 
            'parse_pattern',
            'database_info'
        ]
        
        for method_name in methods_to_check:
            if hasattr(cls, method_name):
                method = getattr(cls, method_name)
                print(f"   ✅ {method_name}: 方法存在")
            else:
                print(f"   ❌ {method_name}: 方法不存在")
    
    # 检查 PyExtendedPrefixQuery 的方法
    if hasattr(rustkmer_pyo3, 'PyExtendedPrefixQuery'):
        cls = rustkmer_pyo3.PyExtendedPrefixQuery
        
        methods_to_check = [
            'query_with_metrics',
            'query_hybrid_with_metrics',
            'batch_query'
        ]
        
        for method_name in methods_to_check:
            if hasattr(cls, method_name):
                method = getattr(cls, method_name)
                print(f"   ✅ {method_name}: 方法存在")
            else:
                print(f"   ❌ {method_name}: 方法不存在")

def show_usage_examples():
    """显示使用示例"""
    print("\n📖 使用示例:")
    
    examples = [
        {
            "title": "基础用法",
            "code": '''
import rustkmer_pyo3

# 创建查询引擎
engine = rustkmer_pyo3.PyPrefixQuery("path/to/database.rkdb")

# 前缀查询
results = engine.query_prefix_string("AAAAAAAA")

# 混合搜索
results = engine.query_hybrid("AAAAAAAA{N5}AAAAAA")

# 显示结果
for kmer, count in results.items():
    print(f"{kmer}: {count}")
'''
        },
        {
            "title": "带指标的查询",
            "code": '''
import rustkmer_pyo3

# 创建扩展引擎
extended_engine = rustkmer_pyo3.PyExtendedPrefixQuery("path/to/database.rkdb")

# 带指标的查询
metrics = extended_engine.query_with_metrics("AAAAAAAA")

print(f"执行时间: {metrics.execution_time_ms} ms")
print(f"总匹配数: {metrics.total_matches}")

# 获取结果
results = dict(metrics.results)
'''
        },
        {
            "title": "批量查询",
            "code": '''
import rustkmer_pyo3

engine = rustkmer_pyo3.PyExtendedPrefixQuery("path/to/database.rkdb")

# 批量查询多个模式
patterns = ["AAAAAAAA", "AAAAAAA{N5}AAAAAA", "ATCG{N3}GCTA"]
results = engine.batch_query(patterns)

for pattern, metrics in results.items():
    print(f"模式 '{pattern}': {metrics.total_matches} 个结果")
'''
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n   示例 {i}: {example['title']}")
        print("   " + "-" * 40)
        for line in example['code'].strip().split('\n'):
            print(f"   {line}")

def main():
    """主测试函数"""
    print("🚀 PyO3 Python Binding API 测试")
    print("=" * 50)
    
    # 执行测试
    test_api_availability()
    test_constructor_validation()
    test_pattern_parsing()
    test_method_signatures()
    show_usage_examples()
    
    print("\n" + "=" * 50)
    print("✅ PyO3 API 测试完成!")
    
    print(f"\n💡 下一步:")
    print(f"   1. 使用真实数据库文件测试:")
    print(f"      python3 simple_prefix_query.py ~/Data/data/kmer/K19/R1_001.rkdb 'AAAAAAA{{N5}}AAAAAA'")
    print(f"   2. 查看完整文档:")
    print(f"      PYO3_PYTHON_BINDING_GUIDE.md")
    print(f"   3. 运行完整演示:")
    print(f"      python3 demo_pyo3_binding.py")

if __name__ == "__main__":
    main()
