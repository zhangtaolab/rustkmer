#!/usr/bin/env python3
"""
测试简单的FASTA写入逻辑
"""

def test_simple_write():
    """测试简单的FASTA写入"""
    print("=== 测试简单FASTA写入 ===")
    
    # 创建一个测试序列
    test_seq = "A" * 300  # 300个A字符
    
    sequences = [
        ("TestSeq1", test_seq),
        ("TestSeq2", test_seq + "T" * 200),
    ]
    
    output_file = "/tmp/test_simple.fa"
    
    print(f"写入测试文件: {output_file}")
    print(f"序列1长度: {len(test_seq)}")
    print(f"序列2长度: {len(test_seq + 'T' * 200)}")
    
    with open(output_file, 'w') as f:
        for name, seq in sequences:
            print(f"写入序列: {name}")
            f.write(f">{name}\n")
            
            # 每行写入80个字符
            for i in range(0, len(seq), 80):
                f.write(f"{seq[i:i+80]}\n")
            f.write("\n")
    
    print("✅ 写入完成")
    
    # 读取并验证
    print("\n=== 验证写入结果 ===")
    with open(output_file, 'r') as f:
        lines = f.readlines()
        print(f"总行数: {len(lines)}")
        
        # 显示前几行
        for i, line in enumerate(lines[:10]):
            print(f"行 {i+1}: {repr(line[:50])}")
    
    # 清理
    import os
    os.remove(output_file)

if __name__ == "__main__":
    test_simple_write()
