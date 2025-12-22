import pyfastx
import argparse
import sys
import os
from pathlib import Path
from tqdm import tqdm
# from collections import defaultdict  # Not currently used
import re

try:
    import rustkmer_pyo3
except ImportError as e:
    print(f"❌ 无法导入 rustkmer_pyo3 模块: {e}")
    print("💡 请确保已正确构建 PyO3 扩展")
    sys.exit(1)


def get_N_positions(seq):
    return [i for i, c in enumerate(seq) if c == 'N']

def get_consecutive_N_regions(seq):
    """
    Identify consecutive N regions in a sequence and return them as dictionaries.
    
    Returns:
        A list of dictionaries, where each dictionary contains 'nstart' and 'nend' keys
        representing start and end positions of a consecutive N region.
        If there are no N's, returns an empty list.
        
    Example:
        For sequence "ATGNNNATCNNNGAT", the function returns 
        [{'nstart': 3, 'nend': 5}, {'nstart': 9, 'nend': 11}]
    """
    N_positions = get_N_positions(seq)
    if not N_positions:
        return []
    
    # Group consecutive N positions and create dictionaries for each region
    regions = []
    nstart = N_positions[0]
    nend = N_positions[0]
    
    for i in range(1, len(N_positions)):
        if N_positions[i] == N_positions[i-1] + 1:  # Consecutive N
            nend = N_positions[i]
        else:
            regions.append({'nstart': nstart, 'nend': nend})
            nstart = N_positions[i]
            nend = N_positions[i]
    
    regions.append({'nstart': nstart, 'nend': nend})  # Add the last region
    return regions






def build_kmer_pattern(seq, nstart, nend, kmerlen, n_length, debug_mode=False):
    
    print(f"nstart: {nstart}, nend: {nend}, kmerlen: {kmerlen}, n_length: {n_length}")
    
    # Use the provided n_length parameter, don't recalculate
    half_flanking_length = int((kmerlen-n_length) / 2)
    
    need_add_n = 0

    if nstart - half_flanking_length < 0:
        left_flanking_seq = seq[0:nstart]
        need_add_n = half_flanking_length - nstart
    else:
        left_flanking_seq = seq[nstart - half_flanking_length:nstart]

    if nend + 1 + half_flanking_length > len(seq):
        right_flanking_seq = seq[nend + 1:]
        need_add_n = half_flanking_length - (len(seq) - nend - 1)
    else:
        right_flanking_seq = seq[nend + 1:nend + 1 + half_flanking_length]

    total_n = n_length+need_add_n

    # Check if total length is insufficient and need to adjust
    if total_n + len(left_flanking_seq) + len(right_flanking_seq) < kmerlen:
        # Need to increase N count to reach kmerlen
        deficit = kmerlen - (total_n + len(left_flanking_seq) + len(right_flanking_seq))
        total_n += deficit
        need_add_n += deficit
    
    # Ensure we don't exceed sequence boundaries when recalculating
    if nstart - len(left_flanking_seq) < 0:
        left_flanking_seq = seq[0:nstart]
    if nend + 1 + len(right_flanking_seq) > len(seq):
        right_flanking_seq = seq[nend + 1:]
        available_downstream = len(seq) - nend - 1
        deficit = len(right_flanking_seq) - available_downstream
        total_n += deficit
        need_add_n += deficit
    #########################################################


    pattern = left_flanking_seq+'{N'+str(total_n)+'}'+right_flanking_seq

    if debug_mode:
        print(f"left_flanking_seq: {left_flanking_seq}, {len(left_flanking_seq)}")
        print(f"total_n: {total_n}")
        print(f"right_flanking_seq: {right_flanking_seq}, {len(right_flanking_seq)}")
        print({len(left_flanking_seq)+total_n+len(right_flanking_seq)})
        print(f"pattern: {pattern}")

    return pattern
    
    
def get_candidate_kmer(results):
    for i, (kmer, count_str) in enumerate(list(results.items())[:5]):
        print(f"  {i + 1}. {kmer[:30]}...{kmer[-20:]} (计数: {count_str})")

        # 按count降序排序 (count_str应该是字符串，需要转换为数字)
        try:
            results_list = sorted(
                results.items(), key=lambda x: int(x[1]), reverse=True
            )
            print("\\n排序后的结果:")
            for i, (kmer, count_str) in enumerate(results_list[:3]):
                print(f"  {i + 1}. 计数: {count_str}, kmer: {kmer[:30]}...{kmer[-20:]}")

            # 获取最高计数的kmer
            max_count = int(results_list[0][1])
            max_count_kmers = [
                result for result in results_list if int(result[1]) == max_count
            ]

            print(f"\\n最高计数 ({max_count}) 的kmer有 {len(max_count_kmers)} 个")

            # 如果有多个相同计数的kmer，选择 polymers 最少的
            if len(max_count_kmers) > 1:
                print("选择polymers最少的kmer...")
                # 这里需要实现polymers计算逻辑
                # 暂时选择第一个
                chosen_kmer = max_count_kmers[0][0]
                print(f"选择: {chosen_kmer}")
            else:
                chosen_kmer = max_count_kmers[0][0]
                print(f"唯一选择: {chosen_kmer}")

        except ValueError as e:
            print(f"转换计数时出错: {e}")
            # 如果无法转换为数字，直接使用第一个结果
            chosen_kmer = list(results.keys())[0]
            print(f"使用第一个结果: {chosen_kmer}")

        return chosen_kmer


def replace_N_region(seq, kmer_pattern, chosen_kmer):
    """
    Replace N region in sequence based on kmer_pattern and chosen_kmer.
    
    Args:
        seq: Original sequence containing N regions
        kmer_pattern: Pattern like 'TGGGTT{N45}GAGAAT' containing upstream{N_count}downstream
        chosen_kmer: Full kmer sequence that matches the pattern
        
    Returns:
        Sequence with N region replaced by the appropriate part of chosen_kmer
    """
    import re
    
    # 解析 kmer_pattern 来提取上游和下游序列
    pattern_match = re.match(r'^(.+?)\{N(\d+)\}(.+)$', kmer_pattern)
    if not pattern_match:
        print(f"❌ 无法解析 kmer_pattern: {kmer_pattern}")
        return seq
    
    upstream_seq = pattern_match.group(1)
    n_length = int(pattern_match.group(2))
    downstream_seq = pattern_match.group(3)
    
    print(f"解析模式:")
    print(f"  上游序列: {upstream_seq}")
    print(f"  N长度: {n_length}")
    print(f"  下游序列: {downstream_seq}")
    
    # 在序列中查找上游序列的位置
    upstream_pos = seq.find(upstream_seq)
    if upstream_pos == -1:
        print(f"❌ 在序列中找不到上游序列: {upstream_seq}")
        return seq
    
    # 在序列中查找下游序列的位置
    downstream_pos = seq.find(downstream_seq, upstream_pos + len(upstream_seq))
    if downstream_pos == -1:
        print(f"❌ 在序列中找不到下游序列: {downstream_seq}")
        return seq
    
    print(f"找到位置:")
    print(f"  上游位置: {upstream_pos}")
    print(f"  下游位置: {downstream_pos}")
    
    # 验证 chosen_kmer 的格式
    if not chosen_kmer.startswith(upstream_seq):
        print(f"❌ chosen_kmer 不以上游序列开头")
        return seq
    
    if not chosen_kmer.endswith(downstream_seq):
        print(f"❌ chosen_kmer 不以下游序列结尾")
        return seq
    
    # 提取 chosen_kmer 中需要填充到 N 区域的部分
    # chosen_kmer 格式: upstream_seq + fill_sequence + downstream_seq
    # N 区域应该被 fill_sequence 替换
    fill_start = len(upstream_seq)
    fill_end = len(chosen_kmer) - len(downstream_seq)
    fill_sequence = chosen_kmer[fill_start:fill_end]
    
    print(f"提取的填充序列: {fill_sequence}")
    
    # 构建新序列：上游序列 + 填充序列 + 下游序列
    new_seq = (seq[:upstream_pos] + 
               upstream_seq + 
               fill_sequence + 
               downstream_seq + 
               seq[downstream_pos + len(downstream_seq):])
    
    print(f"替换完成")
    return new_seq


def main():


    kmerlen = 57

    db_path = "/Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb"

    max_n_length = 43

    max_retry = 10

    each_add_n = 4

    try:
        db = rustkmer_pyo3.PyDatabase(db_path, rustkmer_pyo3.LoadMode.Preload)
        print(f"✅ 成功加载数据库: {db_path}")
    except Exception as e:
        print(f"❌ 无法加载数据库: {e}")
        sys.exit(1)


    seq = "CAGCCCGCCTTTTATACTGTAGGTTACATGTGTCTCCAAGTAAGACTTGAANACATAGAACCCAATACGATATCCGGNNNNNNNNNNNNNNNNNNGAGTAGGACTCCGTAATCACCNNGCCCAGGAAGATATCTCTCTTTACCCTTAATAGACTTCCTTGTTTGCTTATGGAAACAAACCGTATACGTTTGGGTATGCCATACTCTTATATTCCATTAGTCGTAGAGGATGAGG"


    print(f"{seq}")
    

    pre_n_regions = get_consecutive_N_regions(seq)
    pre_n_regions_count = len(pre_n_regions)
    # 使用循环处理所有N区域，每次填充后重新计算
    max_iterations = pre_n_regions_count+3  # 防止无限循环
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n=== 第 {iteration} 轮处理 ===")
        
        # 重新计算当前序列中的N区域
        n_regions = get_consecutive_N_regions(seq)
        n_regions_count = len(n_regions)
        print(f"N区域数量: {n_regions_count}")
        print(f"N区域: {n_regions}")
        
        if n_regions_count == 0:
            print("✅ 所有N区域已填充完成")
            break
        
        # 处理第一个N区域（从左到右）
        chosen_kmer = ''
        kmer_pattern = ''

        n_region = n_regions[0]  # 总是处理第一个（最左边的）N区域
        n_start = n_region['nstart']
        n_end = n_region['nend']
        print(f"处理N区域: 起始位置: {n_start}, 结束位置: {n_end}")
        
        # 确定初始N长度
        if n_end - n_start + 1 > max_n_length:
            n_length = max_n_length
        else:
            n_length = n_end - n_start + 1
        
        print(f"初始N长度: {n_length}")
        
        # 尝试查询和填充
        filled = False
        
        for retry_i in range(max_retry):
            if retry_i == 0:
                current_n_length = n_length
            else:
                current_n_length = n_length + each_add_n * retry_i
                print(f"第 {retry_i+1} 次尝试: N长度调整为 {current_n_length}")
            
            pattern = build_kmer_pattern(seq, n_start, n_end, kmerlen, current_n_length, debug_mode=True)
            print(f"查询模式: {pattern}")
            
            try:
                results = db.query_hybrid(pattern)
                print(f"查询结果数量: {len(results)}")
                
                if len(results) > 0:
                    print("查询结果:")
                    chosen_kmer = get_candidate_kmer(results)
                    print(f"选择的kmer: {chosen_kmer}")
                    kmer_pattern = pattern
                    filled = True
                    break
                    
            except Exception as e:
                print(f"查询失败: {e}")
                continue
        
        if not filled:
            print(f"❌ 无法填充N区域 [位置 {n_start}-{n_end}]")
            # 如果无法填充，跳过这个N区域（将其缩减为较短的N区域）
            print("跳过这个N区域，继续下一个...")
            # 创建一个临时序列，将这个N区域替换为较短的N序列
            seq = seq[:n_start] + 'N' * 10 + seq[n_end+1:]
            continue
        
        # 执行替换
        if chosen_kmer and kmer_pattern:
            print(f"执行替换...")
            seq = replace_N_region(seq, kmer_pattern, chosen_kmer)
            print(f"替换后的序列: {seq[:200]}...")
            print(f"序列长度: {len(seq)}")

    if iteration >= max_iterations:
        print(f"⚠️ 达到最大迭代次数 ({max_iterations})，停止处理")
    
    print(f"\n最终序列:")
    print(seq)


if __name__ == "__main__":
    main()