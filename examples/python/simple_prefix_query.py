import rustkmer_pyo3

# 新的统一接口示例
# 等价于你的bash命令，但使用统一的PyDatabase接口
engine = rustkmer_pyo3.PyDatabase(
    "/Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb", 
    rustkmer_pyo3.LoadMode.MemoryMapped
)

# 混合模式查询（query_hybrid功能）
print("=== 混合模式查询 ===")
print("注意: 模式长度必须匹配数据库k-mer大小")

try:
    # 使用已知的有效模式（k-mer大小57）
    pattern = "AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # 20+7+30=57
    print(f"查询模式: {pattern}")
    
    results = engine.query_hybrid(pattern)
    
    print(f"查询成功！找到 {len(results)} 个匹配结果")
    # 只显示前几个结果以避免输出过多
    count = 0
    for kmer, count_val in results.items():
        print(f"{kmer}: {count_val}")
        count += 1
        if count >= 5:  # 只显示前5个结果
            if len(results) > 5:
                print(f"... 还有 {len(results) - 5} 个结果")
            break
    
except Exception as e:
    error_msg = str(e)
    if "Pattern length" in error_msg and "does not match" in error_msg:
        print(f"⚠️  模式长度验证失败")
        print(f"   错误: {error_msg}")
        print(f"   提示: 请确保混合模式总长度等于数据库k-mer大小")
    else:
        print(f"❌ 混合查询失败: {e}")

# 展示其他统一接口功能
print("\n=== 其他查询功能 ===")

# 前缀查询
prefix_results = engine.query_prefix("AAAAAAAAAAAAAAAAAAAAA")
print(f"前缀查询结果数量: {len(prefix_results.matches)}")

# 数据库信息
info = engine.database_info()
print(f"数据库信息: kmer_size={info['kmer_size']}, load_mode={info['load_mode']}")

# 模式解析
pattern_info = engine.parse_pattern("AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
print(f"模式解析: {pattern_info}")

print("\n=== 批量查询示例 ===")

# 获取数据库信息，确保模式长度匹配
db_info = engine.database_info()
kmer_size = int(db_info['kmer_size'])
print(f"数据库k-mer大小: {kmer_size}")

# 批量混合查询（确保所有模式都匹配数据库大小）
batch_patterns = [
    "AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # 20+7+30=57 ✅
    "AAAAAAAAAAAAAAAAAAAA{N8}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # 4+49+4=57 ✅
    "AAAAAAAAAAAAAAAAAAAAAAA{N6}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"      # 3+51+3=57 ✅
]

try:
    batch_results = engine.query_hybrid_batch(batch_patterns)
    for i, (pattern, results) in enumerate(zip(batch_patterns, batch_results)):
        print(f"模式 {i+1} ({pattern}): {len(results)} 个结果")
except Exception as e:
    error_msg = str(e)
    if "Pattern length" in error_msg and "does not match" in error_msg:
        print(f"⚠️  模式长度验证失败")
        print(f"   提示: 混合模式总长度必须等于数据库k-mer大小 ({kmer_size})")
        print(f"   格式: 前缀长度 + N数量 + 后缀长度 = {kmer_size}")
        print(f"   例如: 对于k-mer大小57，'ATCG{{N49}}ATCG' (4+49+4=57) 是有效的")
    else:
        print(f"❌ 批量查询失败: {e}")

print("\n🎉 统一接口演示完成！")