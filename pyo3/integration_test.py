#!/usr/bin/env python3
"""
RustKmer PyO3 简化集成测试
"""

import subprocess
import sys
import os

def run_simple_test():
    """运行简化测试"""
    print("🚀 运行 RustKmer PyO3 简化测试...")
    
    # 创建简单测试脚本
    test_script = '''
import sys
try:
    import rustkmer_pyo3
    print("SUCCESS: PyO3 module imported")
    
    # 创建计数器
    counter = rustkmer_pyo3.SimpleKmerCounter(4)
    
    # 添加 k-mer
    counter.add_kmer("ATCG")
    
    # 获取计数
    count = counter.get_count("ATCG")
    print(f"SUCCESS: ATCG count = {count}")
    
    # 获取统计
    stats = counter.get_stats()
    print(f"SUCCESS: Stats = {stats}")
    
    print("ALL_TESTS_PASSED")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
'''
    
    try:
        # 使用独立进程运行测试
        result = subprocess.run([
            sys.executable, '-c', test_script
        ], capture_output=True, text=True, timeout=30)
        
        print("测试输出:")
        print(result.stdout)
        
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        if "ALL_TESTS_PASSED" in result.stdout:
            print("✅ 所有测试通过！")
            return True
        else:
            print("❌ 测试失败")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 测试执行错误: {e}")
        return False

def main():
    print("🔧 RustKmer PyO3 最终集成测试")
    print("=" * 50)
    
    # 检查构建状态
    print("📋 检查构建状态...")
    pyproject_path = "/Users/forrest/GitHub/rustkmer/pyo3/pyproject.toml"
    if os.path.exists(pyproject_path):
        print("✅ pyproject.toml 存在")
    else:
        print("❌ pyproject.toml 不存在")
    
    # 检查源代码
    src_path = "/Users/forrest/GitHub/rustkmer/pyo3/src/lib.rs"
    if os.path.exists(src_path):
        print("✅ PyO3 源代码存在")
    else:
        print("❌ PyO3 源代码不存在")
    
    print()
    
    # 运行测试
    success = run_simple_test()
    
    print("=" * 50)
    if success:
        print("🎉 集成测试完成：PyO3 模块工作正常！")
        return 0
    else:
        print("💥 集成测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

