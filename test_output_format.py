#!/usr/bin/env python3
"""
测试FASTA文件输出格式
"""

def test_fasta_output():
    """测试FASTA文件输出格式"""
    print("=== 测试FASTA文件输出格式 ===")
    
    # 模拟序列数据
    sequences = [
        ("Chr10:14146-14400", "TAAACCAAAACCCTAAACACAATAAAAACACAATGGCTCACCTTAGGAATTATACCCCTCTTAAAATGACTGAAATGAGAAGCTTGGGCAATTGGAGGATGCACAGATTACTACCAACAATTCCCTGCAATCCATTCCCATATTACAGTGTCAATAGCTTATAACTTCGTCTGGGACCCCAGTCCAAGTGAGGCCCATATAGGGTGCACCCCAATCTAGTGAAGCACGACCCGTGGACCCTCTTGATCGTCCTCCCACCTCTA"),
        ("Chr10:23555-23784", "CAGTGTATGCTTACCTGTTTGTGATTGTATGCATTATACGAGCAATATGTGTTGCAAAACTAATGACATGGCTCGCATTGTCTGTTTTGATTGTTTTTTTTTTTGGGTGCTCGGTGCTCAGTTCGTGTGACAAACCCCAGTTTCCATCACCGTCTCTGATTCAGATATTATTATTCATCCGTCTAAATTACAGGGCAAAGCTTTTTTTTTAAGAAATAATACAGGGCA")
    ]
    
    # 测试输出
    output_file = "/tmp/test_output.fa"
    print(f"写入测试文件: {output_file}")
    
    with open(output_file, 'w') as f:
        for name, seq in sequences:
            f.write(f">{name}\n")
            # 每行写入80个字符
            for i in range(0, len(seq), 80):
                f.write(f"{seq[i:i+80]}\n")
            f.write("\n")
    
    print("✅ 文件写入完成")
    
    # 读取并显示结果
    print("\n=== 读取并显示文件内容 ===")
    with open(output_file, 'r') as f:
        content = f.read()
        print(content)
    
    # 验证格式
    print("\n=== 验证格式 ===")
    lines = content.strip().split('\n')
    i = 0
    while i < len(lines):
        if lines[i].startswith('>'):
            name = lines[i]
            print(f"序列名称: {name}")
            i += 1
            
            # 读取序列行
            seq_lines = []
            while i < len(lines) and not lines[i].startswith('>'):
                seq_lines.append(lines[i])
                i += 1
            
            # 验证每行长度
            print(f"序列行数: {len(seq_lines)}")
            for j, seq_line in enumerate(seq_lines):
                print(f"  行 {j+1}: 长度={len(seq_line)} '{seq_line[:20]}...'")
                
            print()
    
    # 清理
    import os
    os.remove(output_file)
    print("🧹 清理测试文件")

if __name__ == "__main__":
    test_fasta_output()
