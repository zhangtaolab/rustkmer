#!/usr/bin/env python3
"""
最终测试FASTA格式修复
"""

def test_fasta_format():
    """测试FASTA格式是否正确"""
    print("=== 测试FASTA格式修复 ===")
    
    # 模拟处理后的序列数据（模拟从程序中得到的）
    sequences = [
        ("Chr10:14146-14400", "TAAACCAAAACCCTAAACACAATAAAAACACAATGGCTCACCTTAGGAATTATACCCCTCTTAAAATGACTGAAATGAGAAGCTTGGGCAATTGGAGGATGCACAGATTACTACCAACAATTCCCTGCAATCCATTCCCATATTACAGTGTCAATAGCTTATAACTTCGTCTGGGACCCCAGTCCAAGTGAGGCCCATATAGGGTGCACCCCAATCTAGTGAAGCACGACCCGTGGACCCTCTTGATCGTCCTCCCACCTCTA"),
        ("Chr10:23555-23784", "CAGTGTATGCTTACCTGTTTGTGATTGTATGCATTATACGAGCAATATGTGTTGCAAAACTAATGACATGGCTCGCATTGTCTGTTTTGATTGTTTTTTTTTTTGGGTGCTCGGTGCTCAGTTCGTGTGACAAACCCCAGTTTCCATCACCGTCTCTGATTCAGATATTATTATTCATCCGTCTAAATTACAGGGCAAAGCTTTTTTTTTAAGAAATAATACAGGGCA"),
    ]
    
    output_file = "/tmp/test_fixed.fa"
    
    print(f"测试写入到: {output_file}")
    
    # 使用修复后的写入逻辑
    with open(output_file, 'w') as f:
        for name, seq in sequences:
            # 清理序列名称中的换行符和特殊字符
            clean_name = name.strip()
            print(f"写入序列: {clean_name} (长度: {len(seq)})")
            
            f.write(f">{clean_name}\n")
            
            # 每行写入80个字符
            for i in range(0, len(seq), 80):
                line = seq[i:i+80]
                f.write(f"{line}\n")
            f.write("\n")
    
    print("✅ 写入完成")
    
    # 验证结果
    print("\n=== 验证结果 ===")
    with open(output_file, 'r') as f:
        content = f.read()
        
        # 检查第一行
        lines = content.split('\n')
        first_line = lines[0]
        print(f"第一行: {repr(first_line[:100])}")
        
        # 检查序列名称行
        if first_line.startswith('>') and '\n' not in first_line[1:]:
            print("✅ 序列名称格式正确（没有内嵌换行符）")
        else:
            print("❌ 序列名称格式有问题")
        
        # 检查序列行长度
        seq_lines = []
        i = 1  # 跳过序列名称行
        while i < len(lines) and lines[i]:
            seq_lines.append(lines[i])
            i += 1
        
        print(f"第一个序列的序列行数: {len(seq_lines)}")
        for j, line in enumerate(seq_lines):
            if line:  # 忽略空行
                print(f"  行 {j+1}: 长度={len(line)}")
    
    # 清理
    import os
    os.remove(output_file)
    print("🧹 清理测试文件")

if __name__ == "__main__":
    test_fasta_format()
