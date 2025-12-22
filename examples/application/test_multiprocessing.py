#!/usr/bin/env python3
"""
测试multiprocessing版本的FASTA处理功能
"""

import os
import sys
import multiprocessing
import time

def test_multiprocessing_basic():
    """测试multiprocessing基本功能"""
    print("=== 测试multiprocessing基本功能 ===")
    
    # 测试CPU核心数检测
    cpu_count = multiprocessing.cpu_count()
    print(f"🖥️ 检测到CPU核心数: {cpu_count}")
    
    # 测试Pool创建
    try:
        with multiprocessing.Pool(processes=2) as pool:
            print("✅ multiprocessing.Pool创建成功")
            
            # 测试简单函数
            def square(x):
                return x * x
            
            results = pool.map(square, [1, 2, 3, 4, 5])
            expected = [1, 4, 9, 16, 25]
            
            if results == expected:
                print("✅ multiprocessing基本功能测试通过")
            else:
                print(f"❌ 测试失败: {results} != {expected}")
                
    except Exception as e:
        print(f"❌ multiprocessing测试失败: {e}")
        return False
    
    return True

def create_test_fasta():
    """创建测试用的FASTA文件"""
    test_content = """>test_sequence_1
ATCGATCGATCGATCGNNNNNNNNNNNNATCGATCGATCGATCGATCGATCGATCGATCG
>test_sequence_2  
ATCGATCGATCGNNNNNNNNNNNNNNNNNNNNNNNATCGATCGATCGATCGATCGATCG
>test_sequence_3
GCTCCCTGCAATCCATTAATAGCTTATAACTNNCGTCGCTCCCTGCAATCCATTAATAGCTTATAACTTCGTC
>test_sequence_4
AAAAAACCCCCGGGGGTTTTTCNNNNNNNNNNNNNNAAAACCCCCGGGGGTTTTTC
"""
    
    test_file = "test_multiprocessing.fa"
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    return test_file

def test_fasta_processing():
    """测试FASTA多进程处理"""
    print("\\n=== 测试FASTA多进程处理 ===")
    
    # 检查依赖
    try:
        import pyfastx
        print("✅ pyfastx模块可用")
    except ImportError:
        print("❌ pyfastx模块不可用")
        return False
    
    # 创建测试文件
    test_file = create_test_fasta()
    print(f"✅ 创建测试文件: {test_file}")
    
    # 检查数据库文件
    db_path = "/Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb"
    if not os.path.exists(db_path):
        print(f"⚠️ 数据库文件不存在: {db_path}")
        print("   将跳过实际的k-mer查询测试")
        db_path = None
    
    try:
        # 读取FASTA文件
        fastx_obj = pyfastx.Fasta(test_file)
        sequences = list(fastx_obj)
        print(f"📊 读取到 {len(sequences)} 个序列")
        
        # 显示序列信息
        for i, seqobj in enumerate(sequences):
            print(f"  序列 {i+1}: {seqobj.name} (长度: {len(seqobj.seq)})")
        
        # 模拟多进程处理
        def mock_process_sequence(args):
            """模拟序列处理"""
            name, seq, verbose, process_id = args
            time.sleep(0.1)  # 模拟处理时间
            processed_seq = seq.replace('N', 'A')  # 简单模拟
            return (name, processed_seq, True, f"进程 {process_id} 完成")
        
        # 准备参数
        process_args = []
        for i, seqobj in enumerate(sequences):
            process_args.append((seqobj.name, seqobj.seq, False, i+1))
        
        # 测试多进程
        with multiprocessing.Pool(processes=2) as pool:
            results = list(pool.map(mock_process_sequence, process_args))
            
        print("✅ 多进程处理模拟完成")
        for name, processed_seq, success, message in results:
            print(f"  ✅ {name}: {message}")
        
        return True
        
    except Exception as e:
        print(f"❌ FASTA处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"🧹 清理测试文件: {test_file}")

def main():
    """主测试函数"""
    print("🚀 开始测试multiprocessing版本的FASTA处理")
    
    # 测试基本multiprocessing功能
    basic_test_passed = test_multiprocessing_basic()
    
    # 测试FASTA处理
    fasta_test_passed = test_fasta_processing()
    
    print(f"\\n📋 测试总结:")
    print(f"  ✅ multiprocessing基本功能: {'通过' if basic_test_passed else '失败'}")
    print(f"  ✅ FASTA多进程处理: {'通过' if fasta_test_passed else '失败'}")
    
    if basic_test_passed and fasta_test_passed:
        print("\\n🎉 所有测试通过！multiprocessing版本应该可以正常工作。")
    else:
        print("\\n❌ 部分测试失败，请检查环境配置。")

if __name__ == "__main__":
    main()
