#!/usr/bin/env python3
"""
测试多线程FASTA处理功能
"""

import os
import sys
import tempfile
import shutil

def create_test_fasta():
    """创建测试用的FASTA文件"""
    test_content = """>sequence_1
ATCGATCGATCGATCGNNNNNNNNNNNNATCGATCGATCGATCGATCGATCGATCGATCG
>sequence_2  
ATCGATCGATCGNNNNNNNNNNNNNNNNNNNNNNNATCGATCGATCGATCGATCGATCG
>sequence_3
GCTCCCTGCAATCCATTAATAGCTTATAACTNNCGTCGCTCCCTGCAATCCATTAATAGCTTATAACTTCGTC
>sequence_4
AAAAAACCCCCGGGGGTTTTTCNNNNNNNNNNNNNNAAAACCCCCGGGGGTTTTTC
>sequence_5
CCCTTTGGGAAACCCATCGNNNNNNNNNNNNNNNNNNNNNNNNNTTTAGGCCTAAGG
"""
    
    # 创建临时测试文件
    test_file = "test_multithread.fa"
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    return test_file

def main():
    print("=== 多线程FASTA处理测试 ===")
    
    # 创建测试文件
    test_file = create_test_fasta()
    print(f"✅ 创建测试文件: {test_file}")
    
    # 检查是否有数据库文件
    db_path = "/Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb"
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请修改测试脚本中的数据库路径")
        return
    
    # 测试多线程处理
    output_file = "test_multithread_output.fa"
    
    print(f"\\n🚀 开始多线程处理测试...")
    print(f"输入文件: {test_file}")
    print(f"输出文件: {output_file}")
    print(f"数据库: {db_path}")
    
    # 运行多线程版本
    cmd = f"""python3 pyo3_fill_fasta.py \\
        -i {test_file} \\
        -o {output_file} \\
        -d {db_path} \\
        -t 2 \\
        --max_n_length 20 \\
        --max_retry 3 \\
        --each_add_n 2 \\
        -v"""
    
    print(f"执行命令:")
    print(cmd)
    
    os.system(cmd)
    
    # 检查输出文件
    if os.path.exists(output_file):
        print(f"✅ 输出文件创建成功: {output_file}")
        
        # 显示输出文件内容摘要
        with open(output_file, 'r') as f:
            content = f.read()
            lines = content.split('\\n')
            seq_count = sum(1 for line in lines if line.startswith('>'))
            print(f"📊 输出统计: {seq_count} 个序列")
            
    else:
        print(f"❌ 输出文件创建失败")
    
    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"🧹 清理测试文件: {test_file}")
    
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"🧹 清理输出文件: {output_file}")

if __name__ == "__main__":
    main()
