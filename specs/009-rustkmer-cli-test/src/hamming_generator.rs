use std::collections::HashMap;
use std::collections::HashSet;
use rand::{Rng, SeedableRng};
use rand::rngs::StdRng;
use serde::{Deserialize, Serialize};

/// Hamming 距离测试用例生成器
pub struct HammingGenerator {
    rng: StdRng,
}

impl HammingGenerator {
    /// 创建新的生成器
    pub fn new() -> Self {
        Self {
            rng: StdRng::seed_from_u64(42),
        }
    }

    /// 使用指定种子创建生成器
    pub fn with_seed(seed: u64) -> Self {
        Self {
            rng: StdRng::seed_from_u64(seed),
        }
    }

    /// 生成指定距离的所有可能变体
    pub fn generate_all_variants(&mut self, kmer: &str, distance: usize) -> Vec<String> {
        let mut variants = HashSet::new();
        let kmer_chars: Vec<char> = kmer.chars().collect();
        let bases = ['T', 'C', 'G'];

        self.generate_all_recursive(
            kmer,
            distance,
            0,
            &mut 0,
            &mut variants,
            &bases,
            &kmer_chars,
        );

        variants.into_iter().collect()
    }

    /// 生成指定数量的变体
    pub fn generate_variants(&mut self, kmer: &str, distance: usize, count: usize) -> Vec<String> {
        let all_variants = self.generate_all_variants(kmer, distance);
        if all_variants.len() <= count {
            return all_variants;
        }

        // 随机选择指定数量的变体
        let mut indices: Vec<usize> = (0..all_variants.len()).collect();
        self.rng.shuffle(&mut indices);

        indices
            .into_iter()
            .take(count)
            .map(|i| all_variants[i].clone())
            .collect()
    }

    /// 递归生成所有变体
    fn generate_all_recursive(
        &self,
        kmer: &str,
        remaining_distance: usize,
        position: usize,
        current_distance: &mut usize,
        variants: &mut HashSet<String>,
        bases: &[char],
        kmer_chars: &[char],
    ) {
        if *current_distance == remaining_distance {
            variants.insert(kmer.to_string());
            return;
        }

        if position >= kmer.len() {
            return;
        }

        // 保持当前位置
        let mut kmer_owned = kmer.to_string();
        self.generate_all_recursive(
            &kmer_owned,
            remaining_distance,
            position + 1,
            current_distance,
            variants,
            bases,
            kmer_chars,
        );

        // 变异当前位置
        let original_char = kmer_chars[position];
        for &base in bases {
            if base != original_char {
                kmer_owned.replace_range(position..=position, &base.to_string());
                *current_distance += 1;

                self.generate_all_recursive(
                    &kmer_owned,
                    remaining_distance,
                    position + 1,
                    current_distance,
                    variants,
                    bases,
                    kmer_chars,
                );

                *current_distance -= 1;
            }
        }
    }

    /// 生成测试用例集合
    pub fn generate_test_suite(&mut self, kmer: &str, max_distance: usize) -> HammingTestSuite {
        let mut test_suite = HammingTestSuite {
            base_kmer: kmer.to_string(),
            kmer_size: kmer.len(),
            test_cases: Vec::new(),
        };

        // 为每个距离生成测试用例
        for distance in 1..=max_distance {
            let variants = self.generate_variants(kmer, distance, 10);

            for variant in variants {
                let actual_distance = self.calculate_hamming_distance(kmer, &variant);

                test_suite.test_cases.push(HammingTestCase {
                    query_kmer: kmer.to_string(),
                    target_kmer: variant.clone(),
                    target_distance: distance,
                    actual_distance,
                    is_correct: actual_distance <= distance,
                    distance_difference: actual_distance.saturating_sub(distance),
                });
            }
        }

        test_suite
    }

    /// 生成边界测试用例
    pub fn generate_edge_cases(&mut self) -> Vec<HammingEdgeCase> {
        let mut edge_cases = Vec::new();

        // 全A序列
        edge_cases.push(HammingEdgeCase {
            name: "全A序列距离测试".to_string(),
            original: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_string(),
            distance_1: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAT".to_string(),
            distance_2: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAATT".to_string(),
            distance_3: "AAAAAAAAAAAAAAAAAAAAAAAAAAAATC".to_string(),
        });

        // 全T序列
        edge_cases.push(HammingEdgeCase {
            name: "全T序列距离测试".to_string(),
            original: "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT".to_string(),
            distance_1: "ATTTTTTTTTTTTTTTTTTTTTTTTTTTTTT".to_string(),
            distance_2: "ATTTTTTTTTTTTTTTTTTTTTTTTTTTTCT".to_string(),
            distance_3: "ATTTTTTTTTTTTTTTTTTTTTTTTTTTTCC".to_string(),
        });

        // 混合模式
        edge_cases.push(HammingEdgeCase {
            name: "混合模式距离测试".to_string(),
            original: "ATCGATCGATCGATCGATCGATCGATCGATCG".to_string(),
            distance_1: "TTCGATCGATCGATCGATCGATCGATCGATCG".to_string(),
            distance_2: "TTCGATCGATCGATCGATCGATCGATCGATCC".to_string(),
            distance_3: "TTCGATCGATCGATCGATCGATCGATCGTTTT".to_string(),
        });

        // 重复模式
        edge_cases.push(HammingEdgeCase {
            name: "重复模式距离测试".to_string(),
            original: "ATATATATATATATATATATATATATATATA".to_string(),
            distance_1: "TTATATATATATATATATATATATATATATA".to_string(),
            distance_2: "TTATATATATATATATATATATATATATACC".to_string(),
            distance_3: "TTATATATATATATATATATATATATATCGC".to_string(),
        });

        edge_cases
    }

    /// 生成随机测试用例
    pub fn generate_random_cases(&mut self, count: usize, kmer_size: usize) -> Vec<HammingTestCase> {
        let mut cases = Vec::new();
        let bases = ['A', 'T', 'C', 'G'];

        for _ in 0..count {
            // 生成随机 k-mer
            let mut kmer = String::new();
            for _ in 0..kmer_size {
                kmer.push(bases[self.rng.gen_range(0..4)]);
            }

            // 生成随机距离和变体
            let distance = self.rng.gen_range(1..=3);
            let variants = self.generate_variants(&kmer, distance, 5);

            for variant in variants {
                let actual_distance = self.calculate_hamming_distance(&kmer, &variant);

                cases.push(HammingTestCase {
                    query_kmer: kmer.clone(),
                    target_kmer: variant,
                    target_distance: distance,
                    actual_distance,
                    is_correct: actual_distance <= distance,
                    distance_difference: actual_distance.saturating_sub(distance),
                });
            }
        }

        cases
    }

    /// 计算两个序列的 Hamming 距离
    pub fn calculate_hamming_distance(&self, seq1: &str, seq2: &str) -> usize {
        if seq1.len() != seq2.len() {
            return usize::MAX;
        }

        seq1.chars()
            .zip(seq2.chars())
            .map(|(a, b)| if a == b { 0 } else { 1 })
            .sum()
    }

    /// 生成性能测试用例
    pub fn generate_performance_cases(&mut self, database_sizes: Vec<usize>) -> Vec<HammingPerformanceCase> {
        let mut cases = Vec::new();
        let base_kmer = "ATCGATCGATCGATCGATCGATCGATCGATCG";

        for &size in &database_sizes {
            for distance in [1, 2, 3] {
                cases.push(HammingPerformanceCase {
                    database_size: size,
                    kmer_size: 31,
                    hamming_distance: distance,
                    query_kmer: base_kmer.to_string(),
                    expected_min_results: self.estimate_min_results(size, distance),
                });
            }
        }

        cases
    }

    /// 估算最小结果数
    fn estimate_min_results(&self, database_size: usize, distance: usize) -> usize {
        // 简单的启发式：结果数量与数据库大小和距离成正比
        // 实际实现会依赖于具体的数据库结构
        match distance {
            1 => (database_size / 4).min(1000),
            2 => (database_size / 2).min(5000),
            3 => database_size.min(10000),
            _ => 0,
        }
    }

    /// 生成并发测试用例
    pub fn generate_concurrent_cases(&mut self, thread_count: usize) -> Vec<HammingConcurrentCase> {
        let mut cases = Vec::new();
        let base_sequences = vec![
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
            "ATCGATCGATCGATCGATCGATCGATCGATCG",
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ];

        for i in 0..thread_count {
            let query_kmer = base_sequences[i % base_sequences.len()].to_string();
            let distance = (i % 3) + 1;

            cases.push(HammingConcurrentCase {
                thread_id: i,
                query_kmer: query_kmer.clone(),
                hamming_distance: distance,
                expected_max_time_ms: 1000 + (distance * 500), // 距离越大，预期时间越长
            });
        }

        cases
    }
}

/// Hamming 距离测试用例
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HammingTestCase {
    /// 查询的 k-mer
    pub query_kmer: String,
    /// 目标 k-mer（用于验证）
    pub target_kmer: String,
    /// 目标 Hamming 距离
    pub target_distance: usize,
    /// 实际 Hamming 距离
    pub actual_distance: usize,
    /// 是否正确（实际距离 <= 目标距离）
    pub is_correct: bool,
    /// 距离差异（如果实际距离大于目标距离）
    pub distance_difference: usize,
}

/// 边界测试用例
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HammingEdgeCase {
    /// 测试名称
    pub name: String,
    /// 原始序列
    pub original: String,
    /// 距离为1的变体
    pub distance_1: String,
    /// 距离为2的变体
    pub distance_2: String,
    /// 距离为3的变体
    pub distance_3: String,
}

/// 性能测试用例
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HammingPerformanceCase {
    /// 数据库大小
    pub database_size: usize,
    /// k-mer 大小
    pub kmer_size: usize,
    /// Hamming 距离
    pub hamming_distance: usize,
    /// 查询 k-mer
    pub query_kmer: String,
    /// 预期最小结果数
    pub expected_min_results: usize,
}

/// 并发测试用例
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HammingConcurrentCase {
    /// 线程ID
    pub thread_id: usize,
    /// 查询 k-mer
    pub query_kmer: String,
    /// Hamming 距离
    pub hamming_distance: usize,
    /// 预期最大时间（毫秒）
    pub expected_max_time_ms: u64,
}

/// Hamming 测试套件
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HammingTestSuite {
    /// 基础 k-mer
    pub base_kmer: String,
    /// k-mer 大小
    pub kmer_size: usize,
    /// 测试用例列表
    pub test_cases: Vec<HammingTestCase>,
}

impl HammingTestSuite {
    /// 分析测试结果
    pub fn analyze_results(&self) -> HammingAnalysis {
        let mut analysis = HammingAnalysis::default();

        analysis.total_cases = self.test_cases.len();
        analysis.kmer_size = self.kmer_size;

        for test_case in &self.test_cases {
            analysis.total_tested += 1;

            if test_case.is_correct {
                analysis.correct_tests += 1;
            } else {
                analysis.incorrect_tests += 1;
            }

            // 统计距离分布
            *analysis.distance_counts
                .entry(test_case.target_distance)
                .or_insert(0) += 1;

            // 统计实际距离分布
            *analysis.actual_distance_counts
                .entry(test_case.actual_distance)
                .or_insert(0) += 1;

            // 统计距离差异
            if test_case.distance_difference > 0 {
                *analysis.distance_differences
                    .entry(test_case.distance_difference)
                    .or_insert(0) += 1;
            }
        }

        // 计算平均值
        if analysis.total_tested > 0 {
            analysis.accuracy = analysis.correct_tests as f64 / analysis.total_tested as f64;
        }

        analysis
    }
}

/// Hamming 分析结果
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HammingAnalysis {
    /// k-mer 大小
    pub kmer_size: usize,
    /// 总用例数
    pub total_cases: usize,
    /// 已测试的用例数
    pub total_tested: usize,
    /// 正确的测试数
    pub correct_tests: usize,
    /// 错误的测试数
    pub incorrect_tests: usize,
    /// 准确率
    pub accuracy: f64,
    /// 目标距离分布
    pub distance_counts: HashMap<usize, usize>,
    /// 实际距离分布
    pub actual_distance_counts: HashMap<usize, usize>,
    /// 距离差异分布
    pub distance_differences: HashMap<usize, usize>,
}

impl Default for HammingAnalysis {
    fn default() -> Self {
        Self {
            kmer_size: 0,
            total_cases: 0,
            total_tested: 0,
            correct_tests: 0,
            incorrect_tests: 0,
            accuracy: 0.0,
            distance_counts: HashMap::new(),
            actual_distance_counts: HashMap::new(),
            distance_differences: HashMap::new(),
        }
    }
}

/// 预定义的测试模式
pub struct HammingTestPatterns;

impl HammingTestPatterns {
    /// 获取常用的测试序列
    pub fn common_sequences() -> Vec<String> {
        vec![
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_string(),
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT".to_string(),
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC".to_string(),
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG".to_string(),
            "ATCGATCGATCGATCGATCGATCGATCGATCG".to_string(),
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA".to_string(),
            "TATATATATATATATATATATATATATATATA".to_string(),
            "CGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC".to_string(),
            "ATATATATATATATATATATATATATATATA".to_string(),
            "ATCGATCGATCGATCGATCGATCGATCGATCG".to_string(),
        ]
    }

    /// 获取边界测试序列
    pub fn edge_sequences() -> Vec<String> {
        vec![
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_string(),  // 全A
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT".to_string(),  // 全T
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC".to_string(),  // 全C
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG".to_string(),  // 全G
            "ATCGATCGATCGATCGATCGATCGATCGATCG".to_string(),  // 交替模式
            "TATATATATATATATATATATATATATATA".to_string(),  // 重复A/T
            "CGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC".to_string(),  // 重复C/G
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAT".to_string(),  // 结尾不同
            "TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_string(),  // 开头不同
            "AAAAAAATTTTAAAAAAAAAAAAAAAAAAAA".to_string(),  // 中间不同
        ]
    }

    /// 获取性能测试序列
    pub fn performance_sequences() -> Vec<PerformanceTestSequence> {
        vec![
            PerformanceTestSequence {
                name: "高重复度序列".to_string(),
                sequence: "ATATATATATATATATATATATATATATATA".to_string(),
                expected_variants_distance_1: 31,
                expected_variants_distance_2: 496,
                expected_variants_distance_3: 4960,
            },
            PerformanceTestSequence {
                name: "低重复度序列".to_string(),
                sequence: "ATCGATCGATCGATCGATCGATCGATCGATCG".to_string(),
                expected_variants_distance_1: 31,
                expected_variants_distance_2: 496,
                expected_variants_distance_3: 4960,
            },
            PerformanceTestSequence {
                name: "周期性序列".to_string(),
                sequence: "ATCGATCGATCGATCGATCGATCGATCGATCG".to_string(),
                expected_variants_distance_1: 31,
                expected_variants_distance_2: 496,
                expected_variants_distance_3: 4960,
            },
        ]
    }
}

/// 性能测试序列
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceTestSequence {
    /// 序列名称
    pub name: String,
    /// 序列内容
    pub sequence: String,
    /// 距离1的预期变体数
    pub expected_variants_distance_1: usize,
    /// 距离2的预期变体数
    pub expected_variants_distance_2: usize,
    /// 距离3的预期变体数
    pub expected_variants_distance_3: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hamming_generator() {
        let mut generator = HammingGenerator::new();

        // 测试生成变体
        let variants = generator.generate_variants("AAAA", 1, 5);
        assert_eq!(variants.len(), 5);

        // 验证所有变体的距离都是1
        for variant in &variants {
            let distance = generator.calculate_hamming_distance("AAAA", variant);
            assert_eq!(distance, 1, "变体距离应该是 1");
        }
    }

    #[test]
    fn test_generate_test_suite() {
        let mut generator = HammingGenerator::new();
        let test_suite = generator.generate_test_suite("ATCG", 2);

        assert_eq!(test_suite.base_kmer, "ATCG");
        assert_eq!(test_suite.kmer_size, 4);
        assert!(!test_suite.test_cases.is_empty());

        // 验证测试用例包含不同距离
        let has_distance_1 = test_suite.test_cases.iter().any(|c| c.target_distance == 1);
        let has_distance_2 = test_suite.test_cases.iter().any(|c| c.target_distance == 2);
        assert!(has_distance_1);
        assert!(has_distance_2);
    }

    #[test]
    fn test_edge_cases() {
        let mut generator = HammingGenerator::new();
        let edge_cases = generator.generate_edge_cases();

        assert_eq!(edge_cases.len(), 4);

        // 验证每个边界用例都有相应的变体
        for edge_case in &edge_cases {
            assert!(!edge_case.original.is_empty());
            assert!(!edge_case.distance_1.is_empty());
            assert!(!edge_case.distance_2.is_empty());
            assert!(!edge_case.distance_3.is_empty());
        }
    }

    #[test]
    fn test_performance_cases() {
        let mut generator = HammingGenerator::new();
        let performance_cases = generator.generate_performance_cases(vec![100, 1000, 10000]);

        assert_eq!(performance_cases.len(), 9); // 3个大小 × 3个距离

        // 验证每个性能用例都有合理的参数
        for case in &performance_cases {
            assert!(case.database_size > 0);
            assert_eq!(case.kmer_size, 31);
            assert!(case.hamming_distance >= 1);
            assert!(!case.query_kmer.is_empty());
        }
    }

    #[test]
    fn test_concurrent_cases() {
        let mut generator = HammingGenerator::new();
        let concurrent_cases = generator.generate_concurrent_cases(4);

        assert_eq!(concurrent_cases.len(), 4);

        // 验证每个并发用例都有唯一的线程ID
        let mut thread_ids = std::collections::HashSet::new();
        for case in &concurrent_cases {
            assert!(!thread_ids.contains(&case.thread_id));
            thread_ids.insert(case.thread_id);
        }
    }

    #[test]
    fn test_hamming_analysis() {
        let mut generator = HammingGenerator::new();
        let test_suite = generator.generate_test_suite("ATCG", 2);

        // 修改一些测试用例来模拟不同结果
        let mut test_suite = test_suite;
        if let Some(test_case) = test_suite.test_cases.get_mut(0) {
            test_case.is_correct = false; // 模拟错误情况
        }

        let analysis = test_suite.analyze_results();

        assert!(analysis.total_cases > 0);
        assert!(analysis.accuracy < 1.0);
        assert_eq!(analysis.kmer_size, 4);
    }
}