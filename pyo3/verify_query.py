#!/usr/bin/env python3
"""
简单的 PyO3 模块验证脚本
"""

import subprocess
import sys

def check_pyo3_functionality():
    """检查 PyO3 功能"""
    
    # 创建一个简单的测试脚本
    test_code = '''
import sys
print("Python version:", sys.version)
print("Testing PyO3 module...")

try:
    import rustkmer_pyo3
    print("✅ Module imported successfully")
    
    # 检查可用的类
    classes = [attr for attr in dir(rustkmer_pyo3) if not attr.startswith('_')]
    print("Available classes:", classes)
    
    # 测试基本功能
    if 'PyKmerCounter' in classes:
        print("Testing PyKmerCounter...")
        counter = rustkmer_pyo3.PyKmerCounter(4, False)
        print("✅ PyKmerCounter created")
        
        # 添加 k-mer
        counter.add_kmer("ATCG")
        print("✅ Added k-mer")
        
        # 查询计数
        count = counter.query("ATCG")
        print("✅ Query result:", count)
        print("   kmer:", count.kmer)
        print("   count:", count.count)
        print("   found:", count.found)
        
        print("SUCCESS: All basic tests passed")
    else:
        print("❌ PyKmerCounter not available")
        
except Exception as e:
    print("❌ Error:", e)
    import traceback
    traceback.print_exc()
'''
    
    try:
        # 运行测试
        result = subprocess.run([
            sys.executable, '-c', test_code
        ], capture_output=True, text=True, timeout=30, env={'PYTHONPATH': '/Users/forrest/GitHub/rustkmer/.venv-py311/lib/python3.11/site-packages'})
        
        print("测试输出:")
        print(result.stdout)
        
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        if "SUCCESS: All basic tests passed" in result.stdout:
            print("✅ PyO3 查询功能正常工作！")
            return True
        else:
            print("❌ PyO3 查询功能测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        return False

def main():
    print("🔧 PyO3 查询功能验证")
    print("=" * 50)
    
    success = check_pyo3_functionality()
    
    print("=" * 50)
    if success:
        print("🎉 验证完成：PyO3 查询功能正常工作！")
        return 0
    else:
        print("💥 验证失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
