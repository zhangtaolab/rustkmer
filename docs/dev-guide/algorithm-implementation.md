# 🔧 前缀查询和后缀查询算法实现详解

## 📋 目录

1. [前缀查询算法](#1-前缀查询算法)
2. [后缀查询算法](#2-后缀查询算法)
3. [智能策略选择算法](#3-智能策略选择算法)
4. [具体执行策略](#4-具体执行策略)
5. [性能优化技术](#5-性能优化技术)

---

## 1. 前缀查询算法

### 核心函数：`extract_kmers_by_prefix()`

```rust
pub fn extract_kmers_by_prefix(
    database: &RKDatabase,
    prefix: &str,
) -> ProcessingResult<PrefixQueryResult>
```

### 算法流程：

#### Step 1: 输入验证
```rust
// 验证前缀非空
if prefix.is_empty() {
    return Err(KmerError::InvalidParameters("Prefix cannot be empty"));
}

// 验证字符有效性 (只允许 A,T,C,G)
if !prefix.chars().all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G')) {
    return Err(KmerError::InvalidParameters("Invalid characters"));
}

// 验证前缀长度 < k-mer大小
if prefix_len >= kmer_size {
    return Err(KmerError::InvalidParameters("Prefix too long"));
}
```

#### Step 2: 编码前缀到搜索范围
```rust
fn encode_prefix_to_range(prefix: &str, kmer_size: usize) -> ProcessingResult<(u128, u128)> {
    // 1. 编码前缀
    let prefix_encoded = encode_kmer_u128(prefix)?;
    
    // 2. 计算剩余位数
    let remaining_bits = (kmer_size - prefix.len()) * 2;
    
    // 3. 计算搜索范围
    let max_suffix = (1u128 << remaining_bits) - 1;  // 所有位置填T的最大值
    let range_start = prefix_encoded << remaining_bits;
    let range_end = range_start | max_suffix;
    
    Ok((range_start, range_end))
}
```

**示例**：
- 前缀: "AAATT" (k=19)
- 编码: 0xA... (简化表示)
- 剩余位数: (19-5) × 2 = 28位
- 搜索范围: [0xAAATT000...0, 0xAAATTTTTTT...T]

#### Step 3: 根据数据库类型选择搜索策略

**排序数据库 - 二分查找**：
```rust
fn extract_prefix_matches_binary_search(
    all_kmers: &[(u128, u32)],
    prefix_range: &(u128, u128),
    kmer_size: usize,
    prefix: &str,
) -> ProcessingResult<Vec<(String, u64)>> {
    // 1. 二分查找定位起始位置
    let start_idx = match all_kmers.binary_search_by_key(&prefix_range.0, |&(kmer, _)| kmer) {
        Ok(idx) => idx,
        Err(idx) => idx,
    };
    
    // 2. 线性扫描直到超出范围
    for i in start_idx..all_kmers.len() {
        let (encoded_kmer, count) = all_kmers[i];
        
        if encoded_kmer > prefix_range.1 {
            break; // 超出搜索范围
        }
        
        // 3. 解码并验证前缀匹配
        let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
        if decoded_kmer.starts_with(prefix) {
            matches.push((decoded_kmer, count as u64));
        }
    }
    
    Ok(matches)
}
```

**未排序数据库 - 线性搜索**：
```rust
fn extract_prefix_matches_linear(
    all_kmers: &[(u128, u32)],
    kmer_size: usize,
    prefix: &str,
) -> ProcessingResult<Vec<(String, u64)>> {
    for &(encoded_kmer, count) in all_kmers {
        let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
        if decoded_kmer.starts_with(prefix) {
            matches.push((decoded_kmer, count as u64));
        }
    }
    Ok(matches)
}
```

---

## 2. 后缀查询算法

### 核心函数：`extract_kmers_by_suffix()`

```rust
pub fn extract_kmers_by_suffix(
    database: &RKDatabase,
    suffix: &str,
) -> ProcessingResult<SuffixQueryResult>
```

### 算法流程：

#### Step 1: 输入验证 (与前缀相同)
- 非空验证
- 字符有效性验证 (A,T,C,G)
- 长度验证

#### Step 2: 后缀匹配算法
```rust
fn extract_suffix_matches(
    all_kmers: &[(u128, u32)],
    kmer_size: usize,
    suffix: &str,
) -> ProcessingResult<Vec<(String, u64)>> {
    let mut matches = Vec::new();
    
    for &(encoded_kmer, count) in all_kmers {
        // 1. 解码k-mer
        let decoded_kmer = decode_kmer_u128(encoded_kmer, kmer_size);
        
        // 2. 检查是否以后缀结尾
        if decoded_kmer.ends_with(suffix) {
            matches.push((decoded_kmer, count as u64));
        }
    }
    
    Ok(matches)
}
```

**注意**: 后缀查询目前使用线性搜索，因为后缀匹配难以用简单的数值范围来表示。

---

## 3. 智能策略选择算法

### 核心函数：`decide_query_strategy()`

```rust
fn decide_query_strategy(
    pattern: &str,
    n_positions: &[usize],
    total_variants: usize,
) -> ProcessingResult<QueryStrategy>
```

### 策略决策逻辑：

#### Step 1: 变体数量评估
```rust
// 如果变体数量很少 (<=16)，直接生成变体可能更高效
if total_variants <= 16 {
    return Ok(QueryStrategy {
        strategy_type: StrategyType::VariantGeneration,
        efficiency_rating: "⭐⭐⭐".to_string(),
        description: format!("Small variant count ({}) acceptable", total_variants),
        estimated_variants: total_variants,
    });
}
```

#### Step 2: N位置分析
```rust
let start_n = min(n_positions);    // 第一个N的位置
let end_n = max(n_positions);      // 最后一个N的位置
let n_count = n_positions.len();   // N的总数
let pattern_len = pattern.len();   // 模式长度
```

#### Step 3: 四大策略判断

**策略1: 前缀匹配 (N在末尾)**
```rust
// AAAANNN 模式: start_n = 4, pattern_len = 7, n_count = 3
// 判断条件: start_n == pattern_len - n_count
if start_n == pattern_len - n_count {
    let prefix = &pattern[..start_n];  // 提取 "AAAA"
    return Ok(QueryStrategy {
        strategy_type: StrategyType::PrefixMatching,
        efficiency_rating: "⭐⭐⭐⭐⭐".to_string(),
        description: format!("N at end, use prefix matching: '{}'", prefix),
        estimated_variants: 0,
    });
}
```

**策略2: 后缀匹配 (N在开头)**
```rust
// NNNAAA 模式: end_n = 2, n_count = 3
// 判断条件: end_n == n_count - 1
if end_n == n_count - 1 {
    let suffix = &pattern[n_count..];  // 提取 "AAA"
    return Ok(QueryStrategy {
        strategy_type: StrategyType::SuffixMatching,
        efficiency_rating: "⭐⭐⭐⭐⭐".to_string(),
        description: format!("N at start, use suffix matching: '{}'", suffix),
        estimated_variants: 0,
    });
}
```

**策略3: 混合匹配 (N在中间)**
```rust
// AAANNNAAA 模式: start_n = 3, end_n = 5, pattern_len = 9
// 判断条件: start_n > 0 && end_n < pattern_len - 1
if start_n > 0 && end_n < pattern_len - 1 {
    let prefix = &pattern[..start_n];       // 提取 "AA"
    let suffix = &pattern[end_n + 1..];     // 提取 "AAA"
    return Ok(QueryStrategy {
        strategy_type: StrategyType::HybridMatching,
        efficiency_rating: "⭐⭐⭐⭐".to_string(),
        description: format!("N in middle, hybrid: prefix='{}' suffix='{}'", prefix, suffix),
        estimated_variants: 0,
    });
}
```

**策略4: 变体生成 (N分散)**
```rust
// 其他情况：N分散分布，需要生成所有变体
Ok(QueryStrategy {
    strategy_type: StrategyType::VariantGeneration,
    efficiency_rating: "⭐⭐".to_string(),
    description: format!("N scattered, variant generation required ({} variants)", total_variants),
    estimated_variants: total_variants,
})
```

---

## 4. 具体执行策略

### 4.1 前缀匹配策略执行
```rust
fn extract_with_prefix_strategy(
    database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
) -> ProcessingResult<Vec<(String, u64)>> {
    // 1. 提取固定前缀
    let prefix_end = min(n_positions);
    let prefix = &pattern[..prefix_end];
    
    // 2. 使用前缀查询
    let prefix_result = extract_kmers_by_prefix(database, prefix)?;
    
    // 3. 过滤匹配完整模式的结果
    let mut matches = Vec::new();
    for (kmer, count) in prefix_result.matches {
        if kmer.starts_with(prefix) && matches_pattern(&kmer, pattern, n_positions) {
            matches.push((kmer, count));
        }
    }
    
    Ok(matches)
}
```

### 4.2 后缀匹配策略执行
```rust
fn extract_with_suffix_strategy(
    database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
) -> ProcessingResult<Vec<(String, u64)>> {
    // 1. 提取固定后缀
    let suffix_start = max(n_positions) + 1;
    let suffix = &pattern[suffix_start..];
    
    // 2. 使用后缀查询
    let suffix_result = extract_kmers_by_suffix(database, suffix)?;
    
    // 3. 过滤匹配完整模式的结果
    let mut matches = Vec::new();
    for (kmer, count) in suffix_result.matches {
        if kmer.ends_with(suffix) && matches_pattern(&kmer, pattern, n_positions) {
            matches.push((kmer, count));
        }
    }
    
    Ok(matches)
}
```

### 4.3 混合匹配策略执行
```rust
fn extract_with_hybrid_strategy(
    database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
) -> ProcessingResult<Vec<(String, u64)>> {
    // 1. 提取前缀和后缀
    let start_n = min(n_positions);
    let end_n = max(n_positions);
    let prefix = &pattern[..start_n];
    let suffix = &pattern[end_n + 1..];
    
    // 2. 使用前缀查询 (更高效)
    let prefix_result = extract_kmers_by_prefix(database, prefix)?;
    
    // 3. 同时检查后缀和完整模式匹配
    let mut matches = Vec::new();
    for (kmer, count) in prefix_result.matches {
        if kmer.ends_with(suffix) && matches_pattern(&kmer, pattern, n_positions) {
            matches.push((kmer, count));
        }
    }
    
    Ok(matches)
}
```

### 4.4 变体生成策略执行
```rust
fn extract_with_variant_strategy(
    database: &RKDatabase,
    pattern: &str,
    n_positions: &[usize],
    total_variants: usize,
) -> ProcessingResult<Vec<(String, u64)>> {
    // 1. 检查变体数量限制
    if total_variants > 10000 {
        return Err(KmerError::TooManyVariants { actual: total_variants, limit: 10000 });
    }
    
    // 2. 生成所有变体
    let variants = generate_variants(pattern, n_positions)?;
    
    // 3. 查询每个变体
    let mut matches = Vec::new();
    for variant in variants {
        let result = database.query_kmer(&variant)?;
        if let Some(count) = result {
            matches.push((variant, count as u64));
        }
    }
    
    Ok(matches)
}
```

---

## 5. 性能优化技术

### 5.1 编码范围优化
- **前缀编码**: 使用位运算快速计算搜索范围
- **数值范围**: 将字符串匹配转换为数值区间查询

### 5.2 二分查找优化
- **排序数据库**: O(log n) 时间复杂度定位起始位置
- **范围遍历**: 只遍历匹配范围内的k-mer

### 5.3 组合爆炸保护
- **变体数量限制**: 超过10,000个变体时拒绝查询
- **策略自动切换**: 根据变体数量自动选择最优策略

### 5.4 内存优化
- **懒加载**: 只在需要时解码k-mer
- **结果过滤**: 在解码后立即过滤不匹配的结果

---

## 🎯 实际应用示例

### 示例1: AAAANNN 模式
```rust
// 输入: pattern = "AAAANNN", n_positions = [4, 5, 6]
// 策略决策: start_n=4, pattern_len=7, n_count=3
// 判断: 4 == 7-3 → 前缀匹配策略

// 执行步骤:
// 1. 提取前缀: "AAAA"
// 2. 编码前缀到范围: [0xAAAA00000..., 0xAAAATTTTT...]
// 3. 二分查找定位: O(log n)
// 4. 范围遍历验证: 只检查匹配范围内的k-mer
// 5. 过滤结果: 确保N位置匹配
```

### 示例2: NNNAAA 模式
```rust
// 输入: pattern = "NNNAAA", n_positions = [0, 1, 2]
// 策略决策: end_n=2, n_count=3
// 判断: 2 == 3-1 → 后缀匹配策略

// 执行步骤:
// 1. 提取后缀: "AAA"
// 2. 线性搜索: 检查所有k-mer是否以"AAA"结尾
// 3. 过滤结果: 确保N位置匹配
```

### 示例3: AAANNNAAA 模式
```rust
// 输入: pattern = "AAANNNAAA", n_positions = [3, 4, 5]
// 策略决策: start_n=3, end_n=5, pattern_len=9
// 判断: 3 > 0 && 5 < 9-1 → 混合匹配策略

// 执行步骤:
// 1. 提取前缀: "AA"
// 2. 提取后缀: "AAA"
// 3. 前缀查询: 获取所有以"AA"开头的k-mer
// 4. 双重过滤: 同时检查后缀和N位置匹配
```

---

## 📊 性能对比总结

| 策略类型 | 时间复杂度 | 空间复杂度 | 适用场景 | 效率评级 |
|----------|------------|------------|----------|----------|
| **前缀匹配** | O(log n + k) | O(1) | N在末尾 | ⭐⭐⭐⭐⭐ |
| **后缀匹配** | O(n) | O(1) | N在开头 | ⭐⭐⭐⭐⭐ |
| **混合匹配** | O(log n + m) | O(1) | N在中间 | ⭐⭐⭐⭐ |
| **变体生成** | O(4^k) | O(4^k) | N分散 | ⭐⭐ |

**注**: 
- n = 数据库中k-mer总数
- k = N的个数
- m = 匹配结果数量

这个实现为你的问题提供了完整的答案：**对于AAAANNN、NNNAAA这种N在边缘的情况，前后缀查询确实比变体生成高效得多！**

