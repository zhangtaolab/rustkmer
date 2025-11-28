#!/bin/bash
# RustKmer基本使用示例
# 演示k-mer计数和查询的基本操作

set -e

echo "=== RustKmer基本使用示例 ==="
echo ""

# 检查RustKmer是否已编译
if ! command -v cargo &> /dev/null; then
    echo "错误: 需要安装Rust和Cargo"
    exit 1
fi

if [ ! -f "target/release/rustkmer" ]; then
    echo "编译RustKmer..."
    cargo build --release
fi

RUSTKMER="./target/release/rustkmer"
EXAMPLE_DIR="example_data"
mkdir -p "$EXAMPLE_DIR"

# 1. 创建示例FASTA文件
echo "1. 创建示例FASTA文件..."
cat > "$EXAMPLE_DIR/sample.fa" << 'EOF'
>seq1
ATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGCT
>seq2
GCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAC
>seq3
ATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT
>seq4
CGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGCTAGCTACGCTAGCTAGCTAGC
>seq5
TAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC
EOF

echo "创建的示例文件: $EXAMPLE_DIR/sample.fa"
echo ""

# 2. 基本k-mer计数
echo "2. 基本k-mer计数 (k=21)..."
echo "创建排序数据库..."
$RUSTKMER count \
    -k 21 \
    -t 4 \
    --sort \
    -o "$EXAMPLE_DIR/sample_k21.rkdb" \
    "$EXAMPLE_DIR/sample.fa"

echo "数据库信息:"
$RUSTKMER info "$EXAMPLE_DIR/sample_k21.rkdb"
echo ""

# 3. 单个k-mer查询
echo "3. 单个k-mer查询示例..."
KMER1="ATGCGATGCTAGCGCTAGCTAT"
KMER2="GCTAGCTAGCTAGCTAGCTAC"
KMER3="CCCCCCCCCCCCCCCCCCCCC"  # 不存在的k-mer

echo "查询: $KMER1"
$RUSTKMER query "$EXAMPLE_DIR/sample_k21.rkdb" "$KMER1"

echo "查询: $KMER2"
$RUSTKMER query "$EXAMPLE_DIR/sample_k21.rkdb" "$KMER2"

echo "查询: $KMER3 (应该为0)"
$RUSTKMER query "$EXAMPLE_DIR/sample_k21.rkdb" "$KMER3"
echo ""

# 4. 创建查询文件
echo "4. 创建批量查询文件..."
cat > "$EXAMPLE_DIR/queries.fa" << 'EOF'
>query_1
ATGCGATGCTAGCGCTAGCTAT
>query_2
GCTAGCTAGCTAGCTAGCTAC
>query_3
ATGCTAGCTAGCTAGCTAGCTA
>query_4
CGCTAGCTAGCTAGCTAGCTA
>query_5
TAGCTAGCTAGCTAGCTAGCTA
>query_6
AAAAAAAAAAAAAAAAAAAA  # 不存在
>query_7
CCCCCCCCCCCCCCCCCCCCC  # 不存在
EOF

echo "查询文件: $EXAMPLE_DIR/queries.fa"
echo "查询数量: $(grep -c '^>' "$EXAMPLE_DIR/queries.fa")"
echo ""

# 5. 批量查询
echo "5. 批量查询示例..."
echo "执行批量查询..."
$RUSTKMER query \
    "$EXAMPLE_DIR/sample_k21.rkdb" \
    --sequence "$EXAMPLE_DIR/queries.fa" \
    -o "$EXAMPLE_DIR/query_results.txt"

echo "批量查询结果:"
cat "$EXAMPLE_DIR/query_results.txt"
echo ""

# 6. 结果分析
echo "6. 结果分析..."
TOTAL_QUERIES=$(grep -c '^>' "$EXAMPLE_DIR/queries.fa")
NON_ZERO_COUNTS=$(awk '$2 > 0' "$EXAMPLE_DIR/query_results.txt" | wc -l)
ZERO_COUNTS=$((TOTAL_QUERIES - NON_ZERO_COUNTS))

echo "总查询数: $TOTAL_QUERIES"
echo "计数 > 0: $NON_ZERO_COUNTS"
echo "计数 = 0: $ZERO_COUNTS"
echo ""

if [ "$NON_ZERO_COUNTS" -gt 0 ]; then
    echo "前5个非零计数结果:"
    awk '$2 > 0' "$EXAMPLE_DIR/query_results.txt" | head -5
    echo ""
fi

# 7. 性能测试
echo "7. 性能测试..."
echo "测试单个查询性能..."
time $RUSTKMER query "$EXAMPLE_DIR/sample_k21.rkdb" "$KMER1" > /dev/null

echo "测试批量查询性能..."
time $RUSTKMER query "$EXAMPLE_DIR/sample_k21.rkdb" --sequence "$EXAMPLE_DIR/queries.fa" > /dev/null
echo ""

# 8. 交互式查询示例（注释掉，避免阻塞）
echo "8. 交互式查询示例..."
echo "要启动交互式查询模式，运行:"
echo "$RUSTKMER query $EXAMPLE_DIR/sample_k21.rkdb -i"
echo ""

# 9. 数据库转储
echo "9. 数据库内容示例..."
echo "转储前10个k-mer计数:"
$RUSTKMER dump "$EXAMPLE_DIR/sample_k21.rkdb" | head -10
echo ""

# 10. 不同k-mer大小比较
echo "10. 不同k-mer大小比较..."
for K in 15 21 31; do
    echo "测试 k=$K..."
    $RUSTKMER count \
        -k "$K" \
        -t 2 \
        --sort \
        -o "$EXAMPLE_DIR/sample_k${K}.rkdb" \
        "$EXAMPLE_DIR/sample.fa"

    # 测试查询
    TEST_KMER="ATGCGATGCTAGCGCTAGCTAT"  # 长度21，仅用于k=21测试
    if [ "$K" -le 21 ]; then
        COUNT=$($RUSTKMER query "$EXAMPLE_DIR/sample_k${K}.rkdb" "${TEST_KMER:0:$K}" | awk '{print $2}')
        echo "k=$K, 查询结果: $COUNT"
    fi

    # 显示数据库大小
    SIZE=$(ls -lh "$EXAMPLE_DIR/sample_k${K}.rkdb" | awk '{print $5}')
    echo "数据库大小: $SIZE"
    echo ""
done

# 11. 清理和总结
echo "11. 生成的文件:"
ls -la "$EXAMPLE_DIR/"
echo ""

echo "=== 示例完成 ==="
echo ""
echo "要点总结:"
echo "1. 使用 --sort 标志创建排序数据库以获得最佳性能"
echo "2. 批量查询比单个查询效率高得多"
echo "3. 查询结果格式: kmer<TAB>count"
echo "4. 使用 info 命令查看数据库详细信息"
echo "5. 对于大规模查询，建议使用批量处理"
echo ""
echo "生成的文件可用于进一步测试和分析。"