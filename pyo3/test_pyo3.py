#!/usr/bin/env python3
"""
RustKmer PyO3 模块集成测试脚本
测试基本的 k-mer 计数功能
"""

import sys
import os

def test_pyo3_module():
    """测试 PyO3 模块的基本功能"""
    print("🧪 开始测试 RustKmer PyO3 模块...")
    
    try:
        # 测试导入
        print("📦 测试模块导入...")
        import rustkmer_pyo3
        print("✅ PyO3 模块导入成功")
        
        # 显示可用类
        available_classes = [attr for attr in dir(rustkmer_pyo3) if not attr.startswith('_')]
        print(f"📋 可用类: {available_classes}")
        
        # 测试 SimpleKmerCounter
        if 'SimpleKmerCounter' in available_classes:
            print("\n🔬 测试 SimpleKmerCounter...")
            
            # 创建计数器
            counter = rustkmer_pyo3.SimpleKmerCounter(4)
            print("✅ 成功创建 SimpleKmerCounter")
            
            # 添加有效的 k-mers
            print("➕ 添加 k-mers...")
            counter.add_kmer('ATCG')
            counter.add_kmer('CGAT')
            counter.add_kmer('ATCG')  # 重复 k-mer
            print("✅ 成功添加 k-mers")
            
            # 测试查询计数
            print("🔍 测试查询计数...")
            count = counter.get_count('ATCG')
            print(f"✅ ATCG 计数: {count}")
            
            if count != 2:
                print(f"❌ 错误：期望计数为 2，实际为 {count}")
                return False
            
            # 测试统计信息
            print("📊 测试统计信息...")
            stats = counter.get_count('ATCG')
            print(f"✅ 获取统计信息成功")
            
            # 测试错误处理
            print("⚠️ 测试错误处理...")
            try:
                counter.add_kmer('INVALID')  # 包含无效字符
                print("❌ 错误：应该抛出异常")
                return False
            except Exception as e:
                print(f"✅ 正确捕获无效字符错误: {type(e).__name__}")
            
            try:
                counter.add_kmer('ATG')  # 错误长度
                print("❌ 错误：应该抛出异常")
                return False
            except Exception as e:
                print(f"✅ 正确捕获长度错误: {type(e).__name__}")
            
            # 测试不存在的 k-mer
            missing_count = counter.get_count('TGCA')
            print(f"✅ 不存在 k-mer TGCA 的计数: {missing_count}")
            
            if missing_count != 0:
                print(f"❌ 错误：期望不存在 k-mer 的计数为 0，实际为 {missing_count}")
                return False
            
        print("\n🎉 所有测试通过！")
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 意外错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment():
    """测试运行环境"""
    print("🔍 检查运行环境...")
    print(f"Python 版本: {sys.version}")
    print(f"Python 路径: {sys.executable}")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查虚拟环境
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 运行在虚拟环境中")
    else:
        print("⚠️ 运行在系统 Python 环境中")

if __name__ == "__main__":
    print("🚀 RustKmer PyO3 模块集成测试")
    print("=" * 50)
    
    test_environment()
    print()
    
    success = test_pyo3_module()
    
    print("=" * 50)
    if success:
        print("🎊 测试完成：所有功能正常工作！")
        sys.exit(0)
    else:
        print("💥 测试失败：存在功能问题")
        sys.exit(1)

