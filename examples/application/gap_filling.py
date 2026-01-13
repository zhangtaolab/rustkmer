# Try to import optional dependencies
try:
    import pyfastx
except ImportError:
    pyfastx = None
    print("Warning: pyfastx module not available. FASTA processing will not work.")

try:
    from rustkmer import Database
except ImportError:
    print("Warning: rustkmer module not available. Some functions will not work.")
    Database = None

from multiprocessing import Pool, cpu_count

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None
    print("Warning: tqdm module not available. Progress bars will not be shown.")
# from concurrent.futures import ThreadPoolExecutor, as_completed


def get_N_positions(seq):
    return [i for i, c in enumerate(seq) if c == 'N']


# 从带 N的区域中，取出上下游各特定长度的序列，例如 left_len=19, right_len=19

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


# 输入一个序列，提取 N 的位置，如果 N 超过 11 个，则减少为 11 个
def reduce_N_positions(seq, max_N=11):
    """
    Reduce the number of N's in each consecutive N region to max_N.
    If a region has fewer than max_N N's, it remains unchanged.
    If a region has more than max_N N's, it's truncated to max_N N's.
    """
    N_regions = get_consecutive_N_regions(seq)
    if not N_regions:
        return seq
    
    # Convert sequence to list for easier manipulation
    seq_list = list(seq)
    
    # Process each N region, accounting for index changes due to deletions
    offset = 0  # Track how many characters have been removed so far
    for region in N_regions:
        nstart = region['nstart'] - offset  # Adjust for previous deletions
        nend = region['nend'] - offset
        region_length = nend - nstart + 1
        
        if region_length > max_N:
            # Remove N's beyond max_N
            # This effectively shortens the sequence by removing these N's
            del seq_list[nstart + max_N : nend + 1]
            offset += (region_length - max_N)  # Update offset for next iteration
    
    return ''.join(seq_list)


# 计算统计数量输入序列 kmer count =0 

def get_kmer_list(seq, kmerlen):
    kmerlist = []
    for i in range(len(seq)-kmerlen+1):
        kmerlist.append(seq[i:i+kmerlen])
    return kmerlist

def get_kmer_count_zero(seq, kmerlen, db):
    
    kmerlist = get_kmer_list(seq, kmerlen)

    batch_query_res = db.query_exact_batch(kmerlist)
    # print(batch_query_res)
    count_zero = 0
    for res in batch_query_res:
        # print(batch_query_res[res].kmer, batch_query_res[res].count)
        
        if batch_query_res[res].count == 0:
            count_zero += 1
    return count_zero


def calculate_query_positions(nstart, nend, kmerlen, seq_length):
    """
    计算查询序列的起始和结束位置，确保长度为kmerlen
    
    Args:
        nstart: N区域的起始位置
        nend: N区域的结束位置
        kmerlen: kmer的长度
        seq_length: 序列的总长度
        
    Returns:
        tuple: (left_start, left_end) 查询序列的起始和结束位置
    """
    # 计算N区域的长度
    nlen = nend - nstart + 1
    
    # 计算需要从N区域两侧获取的碱基数量，使得总长度等于kmerlen
    kmer_left = kmerlen - nlen
    
    # 计算查询序列的起始和结束位置，以N区域为中心，向两侧扩展
    left_start = nstart - int(kmer_left / 2) 
    left_end = nend + int(kmer_left / 2)
    
    # 确保查询序列长度为kmerlen
    # 如果kmer_left是奇数，需要调整
    if kmer_left % 2 == 1:
        # 如果kmer_left是奇数，我们需要决定向左还是向右多取一个碱基
        # 这里我们选择向右多取一个碱基
        left_end += 1
    
    # 确保索引不超出序列边界
    if left_start < 0:
        # 如果左边界超出，向右调整
        left_end -= left_start  # left_start是负数，所以是减去一个负数
        left_start = 0
    elif left_end >= seq_length:
        # 如果右边界超出，向左调整
        left_start -= (left_end - seq_length + 1)
        left_end = seq_length - 1
    
    # 最终检查并确保长度正确
    current_length = left_end - left_start + 1
    if current_length != kmerlen:
        print(f"警告: 计算的序列长度({current_length})不等于kmerlen({kmerlen})")
        print(f"调整前: left_start={left_start}, left_end={left_end}")
        
        # 如果长度不正确，强制调整
        if current_length < kmerlen:
            # 序列太短，尝试向右扩展
            left_end = min(left_start + kmerlen - 1, seq_length - 1)
            # 如果仍然不够，向左扩展
            if left_end - left_start + 1 < kmerlen:
                left_start = max(0, left_end - kmerlen + 1)
        else:
            # 序列太长，截断
            left_end = left_start + kmerlen - 1
        
        print(f"调整后: left_start={left_start}, left_end={left_end}")
    
    return left_start, left_end


def process_match(res, befor_polish, nstart, nend, kmerlen, db):
    """
    处理单个匹配结果，生成polish后的序列并计算零计数kmer数量
    
    Args:
        res: 匹配结果对象
        befor_polish: 需要polish的序列片段
        nstart: N区域的起始位置
        nend: N区域的结束位置
        kmerlen: kmer的长度
        db: 数据库对象
        
    Returns:
        dict: 包含polish结果的字典
    """
    # 获取匹配的kmer序列
    match_kmer = res.kmer
    # print(f"匹配的kmer: {match_kmer}")
    
    # 创建polish后的序列副本
    polished_seq = list(befor_polish)
    
    # 计算N区域在befor_polish中的位置
    # 在befor_polish中，N区域从位置19开始（因为前面取了19个字符）
    n_start_in_befor = 19
    n_end_in_befor = n_start_in_befor + (nend - nstart)
    
    # 计算kmer中对应N区域的部分
    kmer_left = kmerlen - (nend - nstart + 1)
    left_context_len = int(kmer_left / 2)
    
    # 提取kmer中用于填充N区域的部分
    fill_start = left_context_len
    fill_end = fill_start + (nend - nstart + 1)
    fill_sequence = match_kmer[fill_start:fill_end]
    
    # 用填充序列替换N区域
    for i, pos in enumerate(range(n_start_in_befor, n_end_in_befor + 1)):
        polished_seq[pos] = fill_sequence[i]
    
    # 转换回字符串
    polished_sequence = ''.join(polished_seq)
    # print(f"Polish后的序列: {polished_sequence}")
    
    # 计算polish后序列中零计数kmer的数量
    zero_count = get_kmer_count_zero(polished_sequence, 19, db)
    # print(f"零计数kmer数量: {zero_count}")
    
    # 返回结果
    return {
        'match_kmer': match_kmer,
        'fill_sequence': fill_sequence,
        'polished_sequence': polished_sequence,
        'count': res.count if hasattr(res, 'count') else None,
        'zero_count': zero_count
    }


def polish_all_gap_regions(seq_before_gap_fill_reduced, N_regions_reduced, kmerlen, db, top_n=1000):
    """
    对所有N区域进行polish处理
    
    Args:
        seq_before_gap_fill_reduced: 处理后的序列
        N_regions_reduced: N区域信息列表
        kmerlen: kmer的长度
        db: 数据库对象
        top_n: 选择count值最高的前top_n个匹配结果进行后续polish
        
    Returns:
        dict: 包含所有N区域polish结果的字典
    """
    # 创建一个字典来存储所有N区域的polish结果
    all_results = {}
    
    # 处理每个N区域
    for region_idx, region in enumerate(N_regions_reduced):
        print(f"\n处理第 {region_idx+1} 个N区域 (位置 {region['nstart']}-{region['nend']})")
        
        nstart = region['nstart']
        nend = region['nend']
        
        # 计算查询序列的起始和结束位置
        left_start, left_end = calculate_query_positions(
            nstart, nend, kmerlen, len(seq_before_gap_fill_reduced)
        )
        
        # 从序列中提取查询kmer
        query_kmer = seq_before_gap_fill_reduced[left_start:left_end+1]
        
        print(f"查询kmer: {query_kmer}")
        print(f"查询kmer长度: {len(query_kmer)}")
        
        # 获取需要polish的序列片段
        befor_polish = seq_before_gap_fill_reduced[nstart-19:nend+19]
        
        # 执行模糊查询
        fuzzy_query_res = db.fuzzy_query(query_kmer, max_variants=9999999999, mutations=0)
        
        # 创建一个列表来存储当前N区域的所有polish结果
        polish_results = []
        
        # 检查是否有匹配
        if fuzzy_query_res.matches:
            print(f"找到 {len(fuzzy_query_res.matches)} 个匹配")
            
            # 如果匹配数量少于top_n，使用全部匹配；否则选择最高的前top_n个
            if len(fuzzy_query_res.matches) <= top_n:
                selected_matches = fuzzy_query_res.matches
                print(f"匹配数量少于{top_n}，使用全部 {len(selected_matches)} 个匹配进行处理")
            else:
                # 按照count值排序，选择最高的前top_n个
                sorted_matches = sorted(fuzzy_query_res.matches, key=lambda x: x.count, reverse=True)
                selected_matches = sorted_matches[:top_n]
                print(f"选择count最高的前 {len(selected_matches)} 个匹配进行处理")
            
            # 智能选择处理方式：匹配数量多时使用多线程
            # if len(selected_matches) > 10:
            #     # 多线程处理
            #     print(f"🔄 使用多线程处理 {len(selected_matches)} 个匹配结果")
            #     polish_results = []
                
            #     # 使用线程池执行多线程处理
            #     with ThreadPoolExecutor(max_workers=min(cpu_count(), len(selected_matches))) as executor:
            #         # 提交所有任务
            #         future_to_res = {
            #             executor.submit(process_match, res, befor_polish, nstart, nend, kmerlen, db): res 
            #             for res in selected_matches
            #         }
                    
            #         # 收集结果并显示进度
            #         for future in tqdm(as_completed(future_to_res), 
            #                           total=len(selected_matches), 
            #                           desc="多线程处理匹配"):
            #             try:
            #                 result = future.result()
            #                 polish_results.append(result)
            #             except Exception as e:
            #                 print(f"⚠️ 处理匹配时出错: {e}")
            # else:
                # 单线程处理（避免小数据集的多线程开销）
            print("📝 使用单线程处理匹配结果")
            polish_results = []
            for res in tqdm(selected_matches, desc="Processing matches"):
                    # 处理匹配结果
                    result = process_match(res, befor_polish, nstart, nend, kmerlen, db)
                    polish_results.append(result)
            
            # 找出零计数kmer数量最少的结果，如果零计数相同，选择多聚体较少的
            # 先按零计数排序
            sorted_by_zero_count = sorted(polish_results, key=lambda x: x['zero_count'])
            min_zero_count = sorted_by_zero_count[0]['zero_count']
            
            # 找出所有零计数最少的结果
            min_zero_count_results = [r for r in sorted_by_zero_count if r['zero_count'] == min_zero_count]
            
            # 在零计数最少的结果中，选择多聚体较少的
            def count_polymers(seq):
                """计算序列中的多聚体数量和最长多聚体长度"""
                # 计算每种碱基的数量
                count_A = seq.count('A')
                count_C = seq.count('C')
                count_G = seq.count('G')
                count_T = seq.count('T')
                
                # 计算多聚体数量（连续相同碱基的数量）
                # 例如：AACCCAA中，AA是2聚体，CCC是3聚体
                polymers = 0
                max_polymer_length = 0
                
                # 遍历序列，查找连续的相同碱基
                i = 0
                while i < len(seq):
                    current_base = seq[i]
                    if current_base not in ['A', 'C', 'G', 'T']:  # 跳过非碱基字符
                        i += 1
                        continue
                    
                    # 计算连续相同碱基的长度
                    j = i
                    while j < len(seq) and seq[j] == current_base:
                        j += 1
                    
                    # 如果连续长度大于等于2，则是一个多聚体
                    if j - i >= 2:
                        polymers += 1
                        # 更新最长多聚体长度
                        max_polymer_length = max(max_polymer_length, j - i)
                    
                    i = j
                
                return polymers, max_polymer_length
            
            # 在零计数最少的结果中，选择多聚体长度最小的
            best_result = min(min_zero_count_results, key=lambda x: count_polymers(x['fill_sequence'])[1])
            
            print(f"\n第 {region_idx+1} 个N区域的最佳结果:")
            print(f"  匹配kmer: {best_result['match_kmer']}")
            print(f"  填充序列: {best_result['fill_sequence']}")
            print(f"  零计数kmer数量: {best_result['zero_count']}")
            polymers_count, max_polymer_length = count_polymers(best_result['fill_sequence'])
            print(f"  填充序列多聚体数量: {polymers_count}")
            print(f"  最长多聚体长度: {max_polymer_length}")
            
            # 将最佳结果添加到总结果中
            all_results[region_idx] = {
                'region': region,
                'best_result': best_result,
                'all_results': polish_results,
                'total_matches': len(fuzzy_query_res.matches),
                'selected_matches': len(selected_matches)
            }
        else:
            print(f"第 {region_idx+1} 个N区域没有找到匹配，无法进行polish")
            all_results[region_idx] = {
                'region': region,
                'best_result': None,
                'all_results': [],
                'total_matches': 0,
                'selected_matches': 0
            }
    
    return all_results


def apply_all_polish_results(seq_before_gap_fill_reduced, all_results):
    """
    将所有N区域的polish结果应用到原始序列中
    
    Args:
        seq_before_gap_fill_reduced: 原始序列
        all_results: 所有N区域的polish结果
        
    Returns:
        str: 应用所有polish结果后的序列
    """
    # 将序列转换为列表以便修改
    seq_list = list(seq_before_gap_fill_reduced)
    
    # 按照N区域的起始位置排序，确保从后往前处理（避免位置偏移）
    sorted_regions = sorted(all_results.items(), key=lambda x: x[1]['region']['nstart'], reverse=True)
    
    for region_idx, result_data in sorted_regions:
        region = result_data['region']
        best_result = result_data['best_result']
        
        if best_result is None:
            print(f"跳过N区域 {region_idx+1} (位置 {region['nstart']}-{region['nend']}): 没有找到匹配")
            continue
            
        nstart = region['nstart']
        nend = region['nend']
        
        # 计算N区域在原始序列中的长度
        original_n_len = nend - nstart + 1
        
        # 获取调整级别
        adjustment_level = best_result.get('adjustment_level', 0)
        
        # 获取填充序列
        fill_sequence = best_result['fill_sequence']
        
        # 计算填充后的N区域长度
        filled_n_len = original_n_len + adjustment_level
        
        # 确保填充序列长度与填充后的N区域长度匹配
        if len(fill_sequence) != filled_n_len:
            print(f"警告: 调整后的N区域长度({filled_n_len})与填充序列长度({len(fill_sequence)})不匹配")
            # 如果填充序列太长，截断；如果太短，用N填充
            if len(fill_sequence) > filled_n_len:
                fill_sequence = fill_sequence[:filled_n_len]
            else:
                fill_sequence = fill_sequence + 'N' * (filled_n_len - len(fill_sequence))
        
        # 替换N区域及周围的序列
        # 如果有调整，需要扩展替换范围
        end_pos = nend + adjustment_level
        
        for i, pos in enumerate(range(nstart, end_pos + 1)):
            if pos < len(seq_list):
                seq_list[pos] = fill_sequence[i]
        
        print(f"已应用N区域 {region_idx+1} (位置 {region['nstart']}-{region['nend']}) 的polish结果")
    
    # 转换回字符串
    return ''.join(seq_list)


def main():
    """
    主函数，配置参数并执行gap filling
    
    Args:
        top_n: 选择count值最高的前top_n个匹配结果进行后续polish
    """
    # 配置信息
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"
    kmerlen = 19
    seq_before_gap_fill = "CGCCGCCCCGGCCCCCGCGCCGCGNNNNNNNGCCACCGCCGCCCGCGCCGCCCGCGCTCGCGCGCACTGTCGCCCGNNNNNNNNNNNGGCCGGCCGTCCGCCCGCGCGCCCGCCGCCCGCNNNNNNNNNNNNNNNNNNNNNNNNCGCCCGCGCGACGCCGACGCCGCACGGCCGCCGNNNNNNNNNNNNNNNNNNNNNNNNNNCCGCGCCACGTCGCCGTGTTCCCNNCGCGC"
    top_n=5000
    
    # 初始化数据库
    db = Database(db_path)
    
    print("原始序列:")
    print(seq_before_gap_fill)
    
    # 获取原始序列中的N区域
    N_regions = get_consecutive_N_regions(seq_before_gap_fill)
    print(f"Found {len(N_regions)} N regions:")
    for i, region in enumerate(N_regions):
        print(f"Region {i+1}: positions {region['nstart']} to {region['nend']} (length: {region['nend']-region['nstart']+1})")
    
    # 减少N区域的长度
    seq_before_gap_fill_reduced = reduce_N_positions(seq_before_gap_fill)
    print("\n减少N区域后的序列:")
    print(seq_before_gap_fill_reduced)
    
    # 获取减少后的N区域
    N_regions_reduced = get_consecutive_N_regions(seq_before_gap_fill_reduced)
    print(f"Found {len(N_regions_reduced)} N regions:")
    for i, region in enumerate(N_regions_reduced):
        print(f"Region {i+1}: positions {region['nstart']} to {region['nend']} (length: {region['nend']-region['nstart']+1})")
    
    # 处理所有N区域
    all_results = polish_all_gap_regions(seq_before_gap_fill_reduced, N_regions_reduced, kmerlen, db, top_n)
    
    # 将所有polish结果应用到原始序列中
    fully_polished_sequence = apply_all_polish_results(seq_before_gap_fill_reduced, all_results)
    
    print("\n最终polish后的序列:")
    print(fully_polished_sequence)
    
    # 检查最终序列中是否还有N
    final_N_regions = get_consecutive_N_regions(fully_polished_sequence)
    if final_N_regions:
        print(f"\n警告: 最终序列中仍有 {len(final_N_regions)} 个N区域:")
        for i, region in enumerate(final_N_regions):
            print(f"Region {i+1}: positions {region['nstart']} to {region['nend']} (length: {region['nend']-region['nstart']+1})")
    else:
        print("\n成功: 最终序列中没有N区域")
    
    return fully_polished_sequence


if __name__ == "__main__":
    # 使用默认参数运行main函数
    main()