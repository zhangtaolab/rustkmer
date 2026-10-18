import sys
from pathlib import Path

import pyrustkmer

# 数据库路径：命令行参数 > 仓库内置测试数据库
default_db = (
    Path(__file__).resolve().parents[2] / "test_data" / "databases" / "small_test.rkdb"
)
db_path = sys.argv[1] if len(sys.argv) > 1 else str(default_db)

# 新的统一接口示例
# 等价于你的bash命令，但使用统一的PyDatabase接口
engine = pyrustkmer.PyDatabase(db_path, pyrustkmer.LoadMode.MemoryMapped)

# 混合模式查询（query_hybrid功能）
print("=== 混合模式查询 ===")
print("注意: 模式长度必须匹配数据库k-mer大小")

# 从数据库读取k-mer大小，派生总长度为k的混合模式
k = engine.kmer_size
pattern = sys.argv[2] if len(sys.argv) > 2 else "A{N%d}C" % (k - 2)

try:
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

# 前缀查询（前缀从k长度的探针切片得到）
prefix_results = engine.query_prefix(("A" * k)[:3])
print(f"前缀查询结果数量: {len(prefix_results.matches)}")

# 数据库信息
info = engine.database_info()
print(f"数据库信息: kmer_size={info['kmer_size']}, load_mode={info['load_mode']}")

# 模式解析
pattern_info = engine.parse_pattern(pattern)
print(f"模式解析: {pattern_info}")

print("\n=== 批量查询示例 ===")

# 获取数据库信息，确保模式长度匹配
db_info = engine.database_info()
kmer_size = int(db_info["kmer_size"])
print(f"数据库k-mer大小: {kmer_size}")

# 批量混合查询（所有模式总长度都等于k-mer大小）
batch_patterns = [
    "A{N%d}C" % (kmer_size - 2),  # 1 + (k-2) + 1 = k
    "T{N%d}A" % (kmer_size - 2),  # 1 + (k-2) + 1 = k
    "G{N%d}C" % (kmer_size - 2),  # 1 + (k-2) + 1 = k
]

try:
    batch_results = engine.query_hybrid_batch(batch_patterns)
    for i, (pattern, results) in enumerate(zip(batch_patterns, batch_results)):
        print(f"模式 {i + 1} ({pattern}): {len(results)} 个结果")
except Exception as e:
    error_msg = str(e)
    if "Pattern length" in error_msg and "does not match" in error_msg:
        print(f"⚠️  模式长度验证失败")
        print(f"   提示: 混合模式总长度必须等于数据库k-mer大小 ({kmer_size})")
        print(f"   格式: 前缀长度 + N数量 + 后缀长度 = {kmer_size}")
        print(
            f"   例如: 对于k-mer大小7，'A{{N5}}C' (1+5+1=7) 是有效的"
        )
    else:
        print(f"❌ 批量查询失败: {e}")

print("\n🎉 统一接口演示完成！")
