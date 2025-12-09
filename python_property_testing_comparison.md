# Python属性测试框架比较：面向科学计算和算法验证

## 1. Hypothesis vs 其他属性测试框架的对比

### 1.1 主要Python属性测试框架

#### Hypothesis
**优势：**
- 最成熟和流行的Python属性测试框架
- 强大的策略生成器和类型推断
- 优秀的错误最小化和缩减算法
- 丰富的内置策略支持
- 与pytest完美集成
- 活跃的社区和文档

**劣势：**
- 学习曲线较陡峭
- 复杂的策略可能影响性能

#### QuickCheck (Python版)
**优势：**
- 原始的属性测试概念实现
- 简单直接的API

**劣势：**
- 社区活跃度较低
- 策略生成器不如Hypothesis丰富

#### Pytest-Property
**优势：**
- 轻量级
- 与pytest深度集成

**劣势：**
- 功能相对简单
- 策略生成能力有限

### 1.2 框架对比表

| 特性 | Hypothesis | QuickCheck | Pytest-Property |
|------|------------|------------|-----------------|
| 成熟度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 策略生成器 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 错误缩减 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 性能 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 科学计算支持 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| 文档质量 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 社区活跃度 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |

## 2. k-mer计数和模糊查询的属性测试设计

### 2.1 k-mer计数器的属性测试

```python
from hypothesis import given, strategies as st
from hypothesis.strategies import composite
import numpy as np
from collections import Counter

# 定义k-mer策略
@composite
def kmers_strategy(draw, min_k=1, max_k=31):
    k = draw(st.integers(min_value=min_k, max_value=max_k))
    alphabet = draw(st.sampled_from(['ATGC', 'ACGT', 'AGCT', 'TCGA']))
    sequence = draw(st.text(alphabet=alphabet, min_size=k, max_size=k*100))
    return k, sequence

@composite
def valid_kmers(draw):
    """生成有效的k-mer序列"""
    k = draw(st.integers(min_value=1, max_value=31))
    # 确保序列长度至少为k
    min_seq_len = k
    max_seq_len = k * 10  # 避免过长的序列
    sequence = draw(st.text(alphabet='ATGC', min_size=min_seq_len, max_size=max_seq_len))
    return k, sequence

# 属性测试1: k-mer计数的一致性
@given(valid_kmers())
def test_kmer_counting_consistency(k_seq_data):
    """测试k-mer计数的一致性"""
    k, sequence = k_seq_data

    # 使用我们的实现
    our_counts = rustkmer_count_kmers(sequence, k)

    # 使用参考实现
    expected_counts = {}
    for i in range(len(sequence) - k + 1):
        kmer = sequence[i:i+k]
        expected_counts[kmer] = expected_counts.get(kmer, 0) + 1

    assert our_counts == expected_counts, f"Counts differ for k={k}, seq={sequence[:50]}..."

# 属性测试2: k-mer计数的单调性
@given(
    k=st.integers(min_value=1, max_value=10),
    base_seq=st.text(alphabet='ATGC', min_size=20, max_size=50),
    append_seq=st.text(alphabet='ATGC', min_size=1, max_size=20)
)
def test_kmer_counting_monotonicity(k, base_seq, append_seq):
    """测试k-mer计数的单调性：添加序列不应该减少现有k-mer的计数"""
    base_counts = rustkmer_count_kmers(base_seq, k)

    # 追加序列
    new_seq = base_seq + append_seq
    new_counts = rustkmer_count_kmers(new_seq, k)

    # 原有的k-mer计数应该保持不变或增加
    for kmer, count in base_counts.items():
        assert new_counts.get(kmer, 0) >= count, f"Monotonicity violated for kmer: {kmer}"

# 属性测试3: 逆互补对称性
@given(
    k=st.integers(min_value=1, max_value=10),
    sequence=st.text(alphabet='ATGC', min_size=10, max_size=100)
)
def test_kmer_reverse_complement_symmetry(k, sequence):
    """测试k-mer与其逆互补的计数关系"""
    def reverse_complement(seq):
        comp = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
        return ''.join(comp[base] for base in reversed(seq))

    counts = rustkmer_count_kmers(sequence, k)
    rc_counts = rustkmer_count_kmers(reverse_complement(sequence), k)

    # 每个k-mer的计数应该等于其逆互补的计数
    for kmer in counts:
        rc_kmer = reverse_complement(kmer)
        assert counts[kmer] == rc_counts.get(rc_kmer, 0), f"Symmetry broken for {kmer}/{rc_kmer}"
```

### 2.2 模糊查询的属性测试

```python
@composite
def fuzzy_query_data(draw):
    """生成模糊查询测试数据"""
    # 生成目标序列
    target_seq = draw(st.text(alphabet='ATGC', min_size=50, max_size=200))

    # 生成查询序列（可能是目标序列的子序列或变异版本）
    mutation_rate = draw(st.floats(min_value=0.0, max_value=0.3))
    query_seq = generate_mutated_sequence(target_seq, mutation_rate)

    # 设置模糊匹配参数
    max_distance = draw(st.integers(min_value=0, max_value=10))
    return target_seq, query_seq, max_distance

def generate_mutated_sequence(sequence, mutation_rate):
    """生成变异序列"""
    import random
    result = list(sequence)
    num_mutations = int(len(sequence) * mutation_rate)

    for _ in range(num_mutations):
        pos = random.randint(0, len(result) - 1)
        # 随机替换、插入或删除
        mutation_type = random.choice(['substitute', 'insert', 'delete'])

        if mutation_type == 'substitute':
            result[pos] = random.choice('ATGC')
        elif mutation_type == 'insert' and pos < len(result) - 1:
            result.insert(pos, random.choice('ATGC'))
        elif mutation_type == 'delete' and len(result) > 1:
            del result[pos]

    return ''.join(result)

@given(fuzzy_query_data())
def test_fuzzy_query_distance_properties(target_seq, query_seq, max_distance):
    """测试模糊查询的距离属性"""
    matches = rustkmer_fuzzy_search(target_seq, query_seq, max_distance)

    # 属性1: 所有匹配的距离都应该<= max_distance
    for match in matches:
        assert match.distance <= max_distance, f"Match distance {match.distance} exceeds max {max_distance}"

    # 属性2: 如果max_distance=0，应该等同于精确匹配
    if max_distance == 0:
        exact_matches = rustkmer_exact_search(target_seq, query_seq)
        assert len(matches) == len(exact_matches), "Zero distance should equal exact matching"

@given(
    target_seq=st.text(alphabet='ATGC', min_size=100, max_size=500),
    query_seq=st.text(alphabet='ATGC', min_size=5, max_size=50),
    max_distance=st.integers(min_value=1, max_value=5)
)
def test_fuzzy_query_symmetry(target_seq, query_seq, max_distance):
    """测试模糊查询的对称性（距离函数）"""
    matches = rustkmer_fuzzy_search(target_seq, query_seq, max_distance)

    for match in matches:
        # 如果A到B的距离是d，那么B到A的距离也应该是d
        reverse_matches = rustkmer_fuzzy_search(query_seq, match.sequence, max_distance)
        # 应该能找到对应的匹配
        found_match = any(
            rm.sequence == target_seq[match.start:match.end]
            for rm in reverse_matches
        )
        assert found_match, "Symmetry property violated in fuzzy matching"
```

## 3. 验证基因组学算法数学属性的最佳实践

### 3.1 数值稳定性测试

```python
from hypothesis import given, assume
import math

@given(
    sequences=st.lists(st.text(alphabet='ATGC', min_size=1, max_size=100), min_size=2, max_size=10)
)
def test_sequence_divergence_symmetry(sequences):
    """测试序列分歧度的对称性"""
    if len(sequences) < 2:
        return

    # d(A, B) 应该等于 d(B, A)
    div_ab = calculate_divergence(sequences[0], sequences[1])
    div_ba = calculate_divergence(sequences[1], sequences[0])

    assert math.isclose(div_ab, div_ba, rel_tol=1e-10), "Divergence should be symmetric"

@given(
    sequences=st.lists(st.text(alphabet='ATGC', min_size=10, max_size=100), min_size=3, max_size=5)
)
def test_sequence_divergence_triangle_inequality(sequences):
    """测试序列分歧度的三角不等式"""
    if len(sequences) < 3:
        return

    # d(A, C) <= d(A, B) + d(B, C)
    div_ac = calculate_divergence(sequences[0], sequences[2])
    div_ab = calculate_divergence(sequences[0], sequences[1])
    div_bc = calculate_divergence(sequences[1], sequences[2])

    assert div_ac <= div_ab + div_bc + 1e-10, "Triangle inequality violated for divergence"
```

### 3.2 概率分布测试

```python
@given(
    population_size=st.integers(min_value=100, max_value=10000),
    sample_size=st.integers(min_value=10, max_value=1000),
    num_trials=st.integers(min_value=100, max_value=1000)
)
def test_sampling_distribution_properties(population_size, sample_size, num_trials):
    """测试抽样分布的统计属性"""
    assume(sample_size < population_size)

    # 生成总体数据
    population = [i % 100 for i in range(population_size)]

    # 进行多次抽样
    sample_means = []
    for _ in range(num_trials):
        sample = random_sample(population, sample_size)
        sample_means.append(sum(sample) / len(sample))

    # 验证中心极限定理：样本均值应该接近总体均值
    population_mean = sum(population) / len(population)
    sample_mean_mean = sum(sample_means) / len(sample_means)

    # 允许一定的误差范围
    error_margin = math.sqrt(population_size / sample_size) / math.sqrt(num_trials)
    assert abs(sample_mean_mean - population_mean) < error_margin, \
        f"Sample mean {sample_mean_mean} too far from population mean {population_mean}"
```

## 4. 处理大规模数据集的属性测试策略

### 4.1 分层测试策略

```python
from hypothesis import given, settings, HealthCheck
from hypothesis.strategies import just, sampled_from

# 小规模测试 - 快速反馈
@settings(max_examples=100, deadline=1000)
@given(
    sequences=st.lists(st.text(alphabet='ATGC', min_size=10, max_size=100), min_size=1, max_size=10)
)
def test_small_scale_properties(sequences):
    """小规模数据的快速属性测试"""
    # 基本功能测试
    for seq in sequences:
        kmer_counts = rustkmer_count_kmers(seq, k=5)
        assert sum(kmer_counts.values()) == max(0, len(seq) - 5 + 1)

# 中等规模测试 - 性能和正确性
@settings(max_examples=20, deadline=10000, suppress_health_check=[HealthCheck.too_slow])
@given(
    sequences=st.lists(st.text(alphabet='ATGC', min_size=1000, max_size=10000), min_size=1, max_size=5)
)
def test_medium_scale_properties(sequences):
    """中等规模数据的属性测试"""
    for seq in sequences:
        # 测试内存使用是否合理
        start_memory = get_memory_usage()
        kmer_counts = rustkmer_count_kmers(seq, k=21)
        end_memory = get_memory_usage()

        # 内存增长应该与k-mer数量成正比
        memory_growth = end_memory - start_memory
        max_kmers = 4 ** 21  # 理论最大值
        assert memory_growth < max_kmers * 8, "Memory usage seems too high"

# 大规模测试 - 只运行在CI环境中
@settings(max_examples=5, deadline=60000, suppress_health_check=[HealthCheck.too_slow])
@given(
    large_sequence=st.just("A" * 1000000 + "T" * 1000000 + "G" * 1000000 + "C" * 1000000)
)
def test_large_scale_properties(large_sequence):
    """大规模数据的压力测试"""
    # 测试是否能处理大序列而不崩溃
    kmer_counts = rustkmer_count_kmers(large_sequence, k=31)

    # 验证基本计数属性
    total_counts = sum(kmer_counts.values())
    expected_total = len(large_sequence) - 31 + 1
    assert total_counts == expected_total, "Large scale counting failed"
```

### 4.2 增量测试和缓存策略

```python
class TestIncrementalProperties:
    """使用类来缓存测试数据，避免重复生成"""

    @classmethod
    def setup_class(cls):
        """生成一次测试数据，所有测试共享"""
        cls.test_sequences = generate_test_sequences()
        cls.expected_results = compute_expected_results(cls.test_sequences)

    @given(st.integers(min_value=1, max_value=31))
    def test_cached_properties(self, k):
        """使用缓存数据的属性测试"""
        for seq in self.test_sequences[:10]:  # 只测试前10个以节省时间
            if len(seq) >= k:
                result = rustkmer_count_kmers(seq, k)
                expected = self.expected_results[k][seq]
                assert result == expected
```

## 5. 与PyTest集成的建议

### 5.1 配置和标记

```python
# pytest.ini 或 pyproject.toml 配置
[tool:pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    property: marks tests as property-based tests
    large_scale: marks tests that use large datasets
addopts = -v --strict-markers

# conftest.py
import pytest
import hypothesis

def pytest_collection_modifyitems(config, items):
    """为Hypothesis测试添加property标记"""
    for item in items:
        if hasattr(item, 'callspec'):
            # Hypothesis测试
            if 'hypothesis' in item.nodeid:
                item.add_marker(pytest.mark.property)
```

### 5.2 测试组织结构

```python
# tests/test_kmer_properties.py
class TestKmerCountingProperties:
    """k-mer计数的属性测试集合"""

    @pytest.mark.property
    @given(valid_kmers())
    def test_consistency(self, k_seq_data):
        """基础一致性测试"""
        pass

    @pytest.mark.property
    @given(valid_kmers())
    def test_monotonicity(self, k_seq_data):
        """单调性测试"""
        pass

    @pytest.mark.slow
    @pytest.mark.property
    @settings(max_examples=10)
    @given(fuzzy_query_data())
    def test_large_scale_consistency(self, query_data):
        """大规模一致性测试"""
        pass

# tests/test_integration.py
class TestIntegrationProperties:
    """集成测试的属性测试"""

    @pytest.mark.integration
    @pytest.mark.property
    @given(
        sequences=st.lists(st.text(alphabet='ATGC', min_size=100, max_size=1000), min_size=5, max_size=20)
    )
    def test_end_to_end_properties(self, sequences):
        """端到端的属性测试"""
        # 测试整个流水线的属性
        pass
```

### 5.3 报告和调试

```python
# 自定义Hypothesis报告
from hypothesis import settings, Verbosity
import sys

# 在测试中增加详细的失败报告
@settings(verbosity=Verbosity.verbose, max_examples=1000)
@given(valid_kmers())
def test_with_detailed_reporting(k_seq_data):
    """带有详细报告的测试"""
    try:
        k, sequence = k_seq_data
        result = rustkmer_count_kmers(sequence, k)
        # ... 测试逻辑
    except AssertionError as e:
        # 额外的调试信息
        print(f"Failed for k={k}, seq_length={len(sequence)}")
        print(f"First 50 chars: {sequence[:50]}")
        raise

# 使用hypothesis profile管理不同的测试配置
hypothesis.register_profile("fast", max_examples=100, deadline=1000)
hypothesis.register_profile("thorough", max_examples=1000, deadline=10000)
hypothesis.register_profile("ci", max_examples=500, deadline=5000)

# 运行时使用: pytest --hypothesis-profile=thorough
```

### 5.4 性能基准测试

```python
# tests/test_performance_properties.py
import time
import pytest
from hypothesis import given, settings
from hypothesis.strategies import integers, text

class TestPerformanceProperties:
    """性能相关的属性测试"""

    @pytest.mark.benchmark
    @settings(max_examples=10)
    @given(
        seq_length=integers(min_value=1000, max_value=100000),
        k=integers(min_value=5, max_value=31)
    )
    def test_time_complexity_property(self, seq_length, k):
        """验证时间复杂度属性"""
        sequence = "ATGC" * (seq_length // 4)

        start_time = time.time()
        result = rustkmer_count_kmers(sequence, k)
        end_time = time.time()

        execution_time = end_time - start_time

        # 验证时间复杂度是O(n)而不是O(n²)
        # 对于线性算法，时间应该与序列长度成正比
        max_expected_time = seq_length * 0.001  # 假设每1000个字符最多1ms
        assert execution_time < max_expected_time, \
            f"Performance regression: {execution_time:.3f}s for {seq_length} chars"
```

## 6. 测试生成策略

### 6.1 智能数据生成

```python
from hypothesis.strategies import composite, sampled_from, integers, floats, lists
import random

@composite
def realistic_genomic_sequences(draw):
    """生成更真实的基因组序列"""
    # 真实基因组的GC含量通常在40%-60%之间
    gc_content = draw(floats(min_value=0.4, max_value=0.6))
    seq_length = draw(integers(min_value=100, max_value=10000))

    # 生成具有指定GC含量的序列
    num_gc = int(seq_length * gc_content)
    num_at = seq_length - num_gc

    bases = ['G'] * num_gc + ['C'] * num_gc + ['A'] * num_at + ['T'] * num_at
    random.shuffle(bases)

    return ''.join(bases)

@composite
def problematic_sequences(draw):
    """生成可能导致边界问题的序列"""
    problem_type = draw(sampled_from([
        'homopolymer',      # 单一碱基重复
        'tandem_repeat',    # 串联重复
        'low_complexity',   # 低复杂度
        'palindrome'        # 回文序列
    ]))

    repeat_length = draw(integers(min_value=5, max_value=20))
    num_repeats = draw(integers(min_value=3, max_value=10))

    if problem_type == 'homopolymer':
        base = draw(sampled_from('ATGC'))
        return base * (repeat_length * num_repeats)
    elif problem_type == 'tandem_repeat':
        motif = draw(sampled_from(['AT', 'GC', 'ATG', 'CGT']))
        return motif * num_repeats
    elif problem_type == 'low_complexity':
        pattern = draw(sampled_from(['ATAT', 'GCGC', 'ATGCATGC']))
        return pattern * num_repeats
    else:  # palindrome
        half = draw(text(alphabet='ATGC', min_size=repeat_length))
        return half + half[::-1]

# 使用示例
@given(realistic_genomic_sequences())
def test_realistic_sequence_properties(sequence):
    """测试真实基因序列的属性"""
    # 验证GC含量在合理范围内
    gc_count = sequence.count('G') + sequence.count('C')
    gc_content = gc_count / len(sequence)
    assert 0.35 <= gc_content <= 0.65, "GC content out of expected range"

@given(problematic_sequences())
def test_problematic_sequence_handling(sequence):
    """测试问题序列的处理"""
    # 应该能够处理而不崩溃
    result = rustkmer_count_kmers(sequence, k=5)
    assert isinstance(result, dict)
```

### 6.2 状态机测试

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, Bundle

class KmerDatabaseStateMachine(RuleBasedStateMachine):
    """k-mer数据库操作的状态机测试"""

    def __init__(self):
        super().__init__()
        self.db = None
        self.inserted_sequences = []
        self.expected_kmers = {}

    @initialize()
    def setup(self):
        self.db = RustKmerDB()
        self.inserted_sequences = []
        self.expected_kmers = {}

    @rule(sequence=realistic_genomic_sequences())
    def insert_sequence(self, sequence):
        """插入序列"""
        self.db.insert(sequence)
        self.inserted_sequences.append(sequence)

        # 更新预期的k-mer计数
        k = 5  # 固定k-mer大小
        for i in range(len(sequence) - k + 1):
            kmer = sequence[i:i+k]
            self.expected_kmers[kmer] = self.expected_kmers.get(kmer, 0) + 1

    @rule(k=integers(min_value=1, max_value=31))
    def query_count(self, k):
        """查询k-mer计数"""
        if not self.inserted_sequences:
            return

        # 合并所有插入的序列
        all_sequences = ''.join(self.inserted_sequences)

        # 查询数据库
        db_counts = self.db.query_kmers(k)

        # 计算预期结果
        expected_counts = {}
        for i in range(len(all_sequences) - k + 1):
            kmer = all_sequences[i:i+k]
            expected_counts[kmer] = expected_counts.get(kmer, 0) + 1

        assert db_counts == expected_counts, "Database counts don't match expected"

TestKmerDatabase = KmerDatabaseStateMachine.TestCase
```

## 总结

选择Hypothesis作为Python属性测试框架的主要原因是：

1. **成熟度和稳定性**：经过多年发展的稳定框架
2. **强大的策略生成器**：支持复杂数据类型的生成
3. **优秀的错误缩减**：能找到最小的反例
4. **丰富的生态系统**：与pytest等工具的深度集成
5. **科学计算支持**：对数值计算和统计测试有良好支持

对于k-mer计数和模糊查询这样的生物信息学算法，属性测试特别有价值，因为：

- 能够发现传统测试难以覆盖的边界情况
- 验证数学和统计属性的正确性
- 通过大量随机输入提高测试覆盖率
- 支持大规模数据的性能和正确性验证

通过合理设计测试策略和使用Hypothesis的强大功能，可以显著提高算法的可靠性和正确性。