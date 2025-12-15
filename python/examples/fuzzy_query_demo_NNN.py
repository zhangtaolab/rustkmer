import pyfastx
from rustkmer import Database

def test_fuzzy_query():
    """测试fuzzy_query功能"""
    # 配置信息
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"
    kmerlen = 19
    
    # 初始化数据库
    db = Database(db_path)
    
    # 测试查询kmer
    query_kmer = "GCCGCGNNNNNNNGCCACC"
    print(f"测试查询kmer: {query_kmer}")
    print(f"查询kmer长度: {len(query_kmer)}")
    
    # 执行模糊查询
    fuzzy_query_res = db.fuzzy_query(query_kmer, max_variants=9999999999)
    
    # 检查结果
    if fuzzy_query_res.matches:
        print(f"找到 {len(fuzzy_query_res.matches)} 个匹配")
        
        # 打印前10个匹配
        print("\n前10个匹配:")
        for i, res in enumerate(fuzzy_query_res.matches[:10]):
            print(f"  {i+1}: kmer={res.kmer}, count={res.count}")
        
        # 检查两边的序列是否保持不变
        print("\n检查两边的序列是否保持不变:")
        for i, res in enumerate(fuzzy_query_res.matches[:10]):
            # 提取kmer中对应N区域的部分
            kmer_left = kmerlen - 7  # N区域长度为7
            left_context_len = int(kmer_left / 2)
            
            # 提取左边序列（应该是GCCGCG）
            left_context = res.kmer[:left_context_len]
            # 提取右边序列（应该是GCCACC）
            right_context = res.kmer[left_context_len+7:]
            
            print(f"  {i+1}: 左边序列={left_context}, 右边序列={right_context}")
            
            # 验证左边序列是否为GCCGCG
            if left_context == "GCCGCG":
                print(f"    ✓ 左边序列正确: {left_context}")
            else:
                print(f"    ✗ 左边序列错误: {left_context} (应该是GCCGCG)")
            
            # 验证右边序列是否为GCCACC
            if right_context == "GCCACC":
                print(f"    ✓ 右边序列正确: {right_context}")
            else:
                print(f"    ✗ 右边序列错误: {right_context} (应该是GCCACC)")
    else:
        print("没有找到匹配")

if __name__ == "__main__":
    test_fuzzy_query()