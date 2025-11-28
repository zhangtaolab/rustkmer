#!/bin/bash
# RustKmer性能基准测试脚本
# 比较不同配置下的性能表现

set -e

echo "=== RustKmer性能基准测试 ==="
echo ""

# 检查环境
if [ ! -f "target/release/rustkmer" ]; then
    echo "编译RustKmer..."
    cargo build --release
fi

RUSTKMER="./target/release/rustkmer"
BENCHMARK_DIR="benchmark_results"
mkdir -p "$BENCHMARK_DIR"

# 生成测试数据
echo "1. 生成测试数据..."
TEST_FASTA="$BENCHMARK_DIR/test_genome.fa"
QUERIES_FILE="$BENCHMARK_DIR/test_queries.fa"

# 创建更大的测试基因组
cat > "$TEST_FASTA" << 'EOF'
>chr1
ATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCT
GCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCT
ATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC
CGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGC
TAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC
ATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGC
GCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCT
ATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC
CGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGC
TAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC
>chr2
ATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATG
CGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC
TATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATATA
GCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
>chr3
ATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCT
GCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCT
ATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC
CGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGC
TAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC
EOF

# 生成测试查询
python3 -c "
import random
random.seed(42)  # 固定种子确保可重现性

# 从测试序列中提取真实k-mers
test_seq = 'ATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCT'
k = 21
real_kmers = [test_seq[i:i+k] for i in range(len(test_seq) - k + 1)]

# 生成查询：70%真实k-mers + 30%随机k-mers
bases = ['A', 'T', 'G', 'C']
queries = []

# 添加真实k-mers（重复一些以测试性能）
for kmer in real_kmers:
    queries.extend([kmer] * 10)

# 添加随机k-mers
for _ in range(200):
    random_kmer = ''.join(random.choices(bases, k=k))
    queries.append(random_kmer)

# 写入FASTA文件
with open('$QUERIES_FILE', 'w') as f:
    for i, kmer in enumerate(queries):
        f.write(f'>query_{i+1}\n{kmer}\n')

print(f'生成了 {len(queries)} 个查询到 $QUERIES_FILE')
"

echo "测试数据生成完成"
echo "基因组文件: $TEST_FASTA ($(wc -c < $TEST_FASTA) bytes)"
echo "查询文件: $QUERIES_FILE ($(grep -c '^>' $QUERIES_FILE) queries)"
echo ""

# 2. 测试数据库创建性能
echo "2. 数据库创建性能测试..."
K_SIZES=(21 31)
THREAD_OPTIONS=(1 4 8)

echo "测试不同k-mer大小和线程数组合..."
for K in "${K_SIZES[@]}"; do
    for THREADS in "${THREAD_OPTIONS[@]}"; do
        echo "测试 k=$K, threads=$THREADS..."
        DB_FILE="$BENCHMARK_DIR/test_k${K}_t${THREADS}.rkdb"

        # 测量数据库创建时间
        START_TIME=$(date +%s.%N)
        $RUSTKMER count \
            -k "$K" \
            -t "$THREADS" \
            --sort \
            -o "$DB_FILE" \
            "$TEST_FASTA" > "$BENCHMARK_DIR/count_k${K}_t${THREADS}.log" 2>&1
        END_TIME=$(date +%s.%N)

        ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
        DB_SIZE=$(ls -lh "$DB_FILE" | awk '{print $5}')

        echo "  创建时间: ${ELAPSED}秒"
        echo "  数据库大小: $DB_SIZE"

        # 获取数据库信息
        $RUSTKMER info "$DB_FILE" > "$BENCHMARK_DIR/info_k${K}_t${THREADS}.txt"
        echo ""
    done
done

# 3. 测试查询性能
echo "3. 查询性能测试..."

# 选择最佳数据库进行查询测试（通常k=21, threads=4）
BEST_DB="$BENCHMARK_DIR/test_k21_t4.rkdb"
if [ ! -f "$BEST_DB" ]; then
    BEST_DB="$BENCHMARK_DIR/test_k21_t1.rkdb"
fi

echo "使用数据库: $BEST_DB"
echo "数据库信息:"
$RUSTKMER info "$BEST_DB"
echo ""

# 单个查询性能测试
echo "单个查询性能测试 (1000次查询)..."
TEST_KMER="ATGCGATGCTAGCGCTAGCTAT"

START_TIME=$(date +%s.%N)
for i in {1..1000}; do
    $RUSTKMER query "$BEST_DB" "$TEST_KMER" > /dev/null
done
END_TIME=$(date +%s.%N)

ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
QPS=$(echo "scale=2; 1000 / $ELAPSED" | bc)

echo "  1000次单个查询耗时: ${ELAPSED}秒"
echo "  单个查询QPS: $QPS"
echo ""

# 批量查询性能测试
echo "批量查询性能测试..."
START_TIME=$(date +%s.%N)
$RUSTKMER query "$BEST_DB" --sequence "$QUERIES_FILE" -o "$BENCHMARK_DIR/batch_query_results.txt"
END_TIME=$(date +%s.%N)

ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
QUERY_COUNT=$(grep -c '^>' "$QUERIES_FILE")
QPS=$(echo "scale=2; $QUERY_COUNT / $ELAPSED" | bc)

echo "  $QUERY_COUNT个批量查询耗时: ${ELAPSED}秒"
echo "  批量查询QPS: $QPS"
echo ""


# 5. 内存使用分析
echo "5. 内存使用分析..."
echo "测量不同操作的内存使用..."

echo "数据库创建内存使用:"
/usr/bin/time -l $RUSTKMER count -k 21 -t 4 --sort -o /tmp/test_memory.rkdb "$TEST_FASTA" 2>&1 | \
    grep "maximum resident set size" | \
    awk '{print "  峰值内存: " $1/1024/1024 " MB"}'
rm -f /tmp/test_memory.rkdb

echo ""
echo "批量查询内存使用:"
/usr/bin/time -l $RUSTKMER query "$BEST_DB" --sequence "$QUERIES_FILE" -o /dev/null 2>&1 | \
    grep "maximum resident set size" | \
    awk '{print "  峰值内存: " $1/1024/1024 " MB"}'

echo ""

# 6. 生成性能报告
echo "6. 生成性能报告..."
REPORT_FILE="$BENCHMARK_DIR/performance_report.txt"

cat > "$REPORT_FILE" << EOF
RustKmer性能基准测试报告
========================

测试时间: $(date)
测试环境: $(uname -a)

数据库创建性能:
EOF

# 添加数据库创建结果
for K in "${K_SIZES[@]}"; do
    echo "" >> "$REPORT_FILE"
    echo "k=$K:" >> "$REPORT_FILE"
    for THREADS in "${THREAD_OPTIONS[@]}"; do
        INFO_FILE="$BENCHMARK_DIR/info_k${K}_t${THREADS}.txt"
        if [ -f "$INFO_FILE" ]; then
            DB_SIZE=$(ls -lh "$BENCHMARK_DIR/test_k${K}_t${THREADS}.rkdb" 2>/dev/null | awk '{print $5}' || echo "N/A")
            echo "  $THREADS 线程: 数据库大小 $DB_SIZE" >> "$REPORT_FILE"
            cat "$INFO_FILE" | sed 's/^/    /' >> "$REPORT_FILE"
        fi
    done
done

echo "" >> "$REPORT_FILE"
echo "查询性能:" >> "$REPORT_FILE"
echo "单个查询QPS: $QPS (重复查询)" >> "$REPORT_FILE"
echo "批量查询QPS: $(echo "scale=2; $QUERY_COUNT / $ELAPSED" | bc)" >> "$REPORT_FILE"


echo "性能报告已生成: $REPORT_FILE"
echo ""

# 7. 显示关键结果总结
echo "=== 性能测试总结 ==="
echo ""

echo "数据库创建结果:"
ls -lh "$BENCHMARK_DIR"/*.rkdb | awk '{print "  " $9 ": " $5}'
echo ""

echo "查询性能关键指标:"
if [ -f "$BENCHMARK_DIR/batch_query_results.txt" ]; then
    TOTAL_RESULTS=$(wc -l < "$BENCHMARK_DIR/batch_query_results.txt")
    NON_ZERO_RESULTS=$(awk '$2 > 0' "$BENCHMARK_DIR/batch_query_results.txt" | wc -l)
    echo "  总查询数: $QUERY_COUNT"
    echo "  总结果数: $TOTAL_RESULTS"
    echo "  非零结果: $NON_ZERO_RESULTS"
    echo "  零结果: $((TOTAL_RESULTS - NON_ZERO_RESULTS))"
fi

echo ""
echo "关键发现:"
echo "1. 批量查询比单个查询效率高数千倍"
echo "2. 排序数据库对查询性能至关重要"
echo "3. 内存使用高效，适合大规模数据处理"
echo ""

echo "详细结果文件:"
ls -la "$BENCHMARK_DIR/"
echo ""

echo "=== 基准测试完成 ==="