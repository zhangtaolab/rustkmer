#!/usr/bin/env python3
"""
PyO3 RustKmer Subprocess Demo

This script demonstrates using PyO3 bindings for k-mer querying
with subprocess-style parallel processing.

Author: RustKmer Team
"""

import sys
import time
from pathlib import Path

# Import the PyO3 bindings
import rustkmer_pyo3
from rustkmer import Database

    
    # Database and test file paths
db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"
example_path = "/Users/forrest/Data/data/kmer/K19/tmp.txt"

kmer_example = {}
        
with open(example_path) as f:
            for line in f:
                line = line.strip("\t")
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        kmer = parts[0]
                        count = int(parts[1])
                        kmer_example[kmer] = count
        
print(f"✅ Read {len(kmer_example)} k-mers from example file")
# print(kmer_example)
    # Check if files exist

cli_start_time = time.time()

# test CLI query
db_cli = Database(db_path)
cli_query_matches = 0
for kmer in kmer_example:
    result = db_cli.query(kmer)
    # print(f"{kmer}: {result.count}")
    if result.count == kmer_example[kmer]:
        cli_query_matches += 1
cli_query_time = time.time() - cli_start_time
print(f"✅ CLI query time: {cli_query_time:.1f} seconds")

print(f"✅ CLI query matches: {cli_query_matches} / {len(kmer_example)}")

cli_batch_start_time = time.time()
batch_list = list(kmer_example.keys())
batch_result = db_cli.query_batch(batch_list)
cli_batch_time = time.time() - cli_batch_start_time
print(f"✅ CLI batch query time: {cli_batch_time:.1f} seconds")


print("--------------------------------")
print("PyO3 Preload Mode")
pyo3_start_time = time.time()
pyo3_db = rustkmer_pyo3.PyDatabase(db_path, rustkmer_pyo3.LoadMode.Preload)
pyo3_db_load_time = time.time() - pyo3_start_time
print(f"✅ PyO3 database load time: {pyo3_db_load_time:.4f} seconds")

pyo3_query_start_time = time.time()
pyo3_query_matches = 0
for kmer in kmer_example:
    result1 = pyo3_db.query(kmer)
    if result1.count == kmer_example[kmer]:
        pyo3_query_matches += 1
        # print(f"{kmer}: {result1.count}, {kmer_example[kmer]}")
pyo3_query_time = time.time() - pyo3_query_start_time
print(f"✅ PyO3 query time: {pyo3_query_time:.4f} seconds")
print(f"✅ PyO3 query matches: {pyo3_query_matches} / {len(kmer_example)}")
# pyo3_db.close()

time.sleep(5)
print("--------------------------------")
time.sleep(5)
# print("PyO3 Non-Preload Mode")

# pyo3 non-preload mode
print("PyO3 Non-Preload Mode")
pyo3_non_preload_start_time = time.time()
pyo3_non_preload_db = rustkmer_pyo3.PyDatabase(db_path, rustkmer_pyo3.LoadMode.MemoryMapped)
pyo3_non_preload_db_load_time = time.time() - pyo3_non_preload_start_time
print(f"✅ PyO3 non-preload database load time: {pyo3_non_preload_db_load_time:.4f} seconds")


pyo3_non_preload_query_start_time = time.time()
pyo3_non_preload_query_matches = 0
for kmer in kmer_example:
    each_start_time = time.time()
    result = pyo3_non_preload_db.query(kmer)
    if result.count == kmer_example[kmer]:
        pyo3_non_preload_query_matches += 1
        # print(f"{kmer}: {result.count}, {kmer_example[kmer]}")
        # print(f"✅ PyO3 non-preload query time: {time.time() - each_start_time:.1f} seconds")
pyo3_non_preload_query_time = time.time() - pyo3_non_preload_query_start_time
print(f"✅ PyO3 non-preload query time: {pyo3_non_preload_query_time:.4f} seconds")
print(f"✅ PyO3 non-preload query matches: {pyo3_non_preload_query_matches} / {len(kmer_example)}")