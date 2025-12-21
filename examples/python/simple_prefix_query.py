import rustkmer_pyo3

# 等价于你的bash命令
# engine = rustkmer_pyo3.PyPrefixQuery("/Users/forrest/Data/data/kmer/K19/R1_001.rkdb")
# results = engine.query_hybrid("AAAAAAAA{N5}AAAAAA")
engine = rustkmer_pyo3.PyPrefixQuery("/Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb")
results = engine.query_hybrid("AAAAAAAAAAAAAAAAAAAAA{N7}AAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

for kmer, count in results.items():
    print(f"{kmer}: {count}")