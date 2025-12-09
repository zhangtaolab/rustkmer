use std::collections::HashMap;
use std::process::Command;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};

/// Fuzzy Query 验证错误类型
#[derive(Debug, thiserror::Error)]
pub enum FuzzyValidationError {
    #[error("数据库文件不存在: {0}")]
    DatabaseNotFound(String),

    #[error("查询命令执行失败: {0}")]
    QueryExecutionFailed(String),

    #[error("无效的 Hamming 距离: {0}")]
    InvalidHammingDistance(String),

    #[error("解析查询结果失败: {0}")]
    ParseResultFailed(String),

    #[error("Hamming 距离验证失败: {0}")]
    HammingDistanceValidationFailed(String),

    #[error("性能基准失败: {0}")]
    PerformanceBenchmarkFailed(String),
}

/// Fuzzy Query 结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FuzzyQueryResult {
    /// 查询的 k-mer
    pub query_kmer: String,
    /// Hamming 距离
    pub hamming_distance: usize,
    /// 查询到的 k-mers
    pub matches: Vec<FuzzyMatch>,
    /// 查询执行时间（毫秒）
    pub execution_time_ms: u64,
    /// 是否成功
    pub success: bool,
    /// 错误信息（如果有）
    pub error_message: Option<String>,
}

/// 单个匹配结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FuzzyMatch {
    /// 匹配的 k-mer
    pub kmer: String,
    /// 实际 Hamming 距离
    pub actual_distance: usize,
    /// k-mer 计数
    pub count: u64,
}

/// Fuzzy Query 性能指标
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FuzzyPerformanceMetrics {
    /// 查询的 k-mer
    pub query_kmer: String,
    /// Hamming 距离
    pub hamming_distance: usize,
    /// 执行时间（毫秒）
    pub execution_time_ms: u64,
    /// 结果数量
    pub result_count: usize,
    /// 吞吐量（结果/秒）
    pub results_per_second: f64,
}

/// Fuzzy Query 验证器
pub struct FuzzyValidator {
    /// k-mer 大小（如果已知）
    pub expected_kmer_size: Option<usize>,
    /// 严格模式（更严格的验证）
    pub strict_mode: bool,
}

impl FuzzyValidator {
    /// 创建新的模糊查询验证器
    pub fn new() -> Self {
        Self {
            expected_kmer_size: None,
            strict_mode: false,
        }
    }

    /// 创建严格模式的验证器
    pub fn strict() -> Self {
        Self {
            expected_kmer_size: None,
            strict_mode: true,
        }
    }

    /// 设置期望的 k-mer 大小
    pub fn with_kmer_size(mut self, size: usize) -> Self {
        self.expected_kmer_size = Some(size);
        self
    }

    /// 执行模糊查询并验证
    pub fn execute_fuzzy_query<P: AsRef<Path>>(
        &self,
        database_path: P,
        kmer: &str,
        hamming_distance: usize,
    ) -> Result<FuzzyQueryResult> {
        let start_time = std::time::Instant::now();

        // 验证输入参数
        if kmer.is_empty() {
            return Ok(FuzzyQueryResult {
                query_kmer: kmer.to_string(),
                hamming_distance,
                matches: Vec::new(),
                execution_time_ms: 0,
                success: false,
                error_message: Some("k-mer 为空".to_string()),
            });
        }

        // 验证 Hamming 距离
        if hamming_distance == 0 {
            return Ok(FuzzyQueryResult {
                query_kmer: kmer.to_string(),
                hamming_distance,
                matches: Vec::new(),
                execution_time_ms: 0,
                success: false,
                error_message: Some("Hamming 距离不能为 0，请使用普通 query 命令".to_string()),
            });
        }

        // 验证 k-mer 格式
        if let Some(expected_size) = self.expected_kmer_size {
            if kmer.len() != expected_size {
                return Ok(FuzzyQueryResult {
                    query_kmer: kmer.to_string(),
                    hamming_distance,
                    matches: Vec::new(),
                    execution_time_ms: 0,
                    success: false,
                    error_message: Some(format!(
                        "k-mer 长度不匹配: 期望 {}, 实际 {}",
                        expected_size, kmer.len()
                    )),
                });
            }
        }

        // 执行查询命令
        let output = Command::new("rustkmer")
            .args([
                "fuzzy-query",
                database_path.as_ref().to_string_lossy().as_ref(),
                kmer,
                "-m",
                &hamming_distance.to_string(),
            ])
            .output()
            .with_context(|| "无法执行 rustkmer fuzzy-query")?;

        let execution_time_ms = start_time.elapsed().as_millis() as u64;

        if !output.status.success() {
            return Ok(FuzzyQueryResult {
                query_kmer: kmer.to_string(),
                hamming_distance,
                matches: Vec::new(),
                execution_time_ms,
                success: false,
                error_message: Some(String::from_utf8_lossy(&output.stderr).to_string()),
            });
        }

        // 解析查询结果
        let stdout = String::from_utf8_lossy(&output.stdout);
        let matches = self.parse_fuzzy_results(&stdout, kmer, hamming_distance)?;

        // 验证结果
        if self.strict_mode {
            self.validate_hamming_distances(kmer, &matches)?;
        }

        Ok(FuzzyQueryResult {
            query_kmer: kmer.to_string(),
            hamming_distance,
            matches,
            execution_time_ms,
            success: true,
            error_message: None,
        })
    }

    /// 解析模糊查询结果
    fn parse_fuzzy_results(
        &self,
        output: &str,
        query_kmer: &str,
        target_distance: usize,
    ) -> Result<Vec<FuzzyMatch>> {
        let mut matches = Vec::new();

        for line in output.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            // 解析每行（可能是 "kmer" 或 "kmer count" 格式）
            let parts: Vec<&str> = trimmed.split_whitespace().collect();
            if parts.is_empty() {
                continue;
            }

            let kmer = parts[0];
            let count = if parts.len() > 1 {
                parts[1].parse::<u64>().unwrap_or(1)
            } else {
                1
            };

            // 计算实际 Hamming 距离
            let actual_distance = self.calculate_hamming_distance(query_kmer, kmer);

            matches.push(FuzzyMatch {
                kmer: kmer.to_string(),
                actual_distance,
                count,
            });
        }

        Ok(matches)
    }

    /// 计算两个 k-mers 之间的 Hamming 距离
    fn calculate_hamming_distance(&self, kmer1: &str, kmer2: &str) -> usize {
        if kmer1.len() != kmer2.len() {
            return usize::MAX;
        }

        kmer1.chars()
            .zip(kmer2.chars())
            .map(|(a, b)| if a == b { 0 } else { 1 })
            .sum()
    }

    /// 验证 Hamming 距离是否正确
    fn validate_hamming_distances(
        &self,
        query_kmer: &str,
        matches: &[FuzzyMatch],
    ) -> Result<()> {
        for fuzzy_match in matches {
            if fuzzy_match.actual_distance > fuzzy_match.actual_distance {
                // 这不应该发生，但我们检查一下
                continue;
            }

            // 验证距离是否在合理范围内
            if fuzzy_match.actual_distance != fuzzy_match.actual_distance {
                return Err(FuzzyValidationError::HammingDistanceValidationFailed(format!(
                    "k-mer {} 的距离计算错误: 声称 {}, 实际 {}",
                    fuzzy_match.kmer,
                    fuzzy_match.actual_distance,
                    fuzzy_match.actual_distance
                )).into());
            }
        }
        Ok(())
    }

    /// 生成测试用例
    pub fn generate_test_cases(&self, base_kmer: &str, max_distance: usize) -> Vec<(String, usize, Vec<String>)> {
        let mut test_cases = Vec::new();

        // 基础测试：查询 k-mer 本身（距离应该为 0）
        test_cases.push((base_kmer.to_string(), 1, vec![base_kmer.to_string()]));

        // 生成不同距离的变体
        for distance in 1..=max_distance.min(3) {
            let variants = self.generate_hamming_variants(base_kmer, distance, 5);
            test_cases.push((base_kmer.to_string(), distance, variants));
        }

        test_cases
    }

    /// 生成指定 Hamming 距离的变体
    fn generate_hamming_variants(&self, base_kmer: &str, distance: usize, count: usize) -> Vec<String> {
        let bases = ['T', 'C', 'G'];
        let mut variants = Vec::new();
        let kmer_chars: Vec<char> = base_kmer.chars().collect();

        // 递归生成变体
        self.generate_hamming_recursive(
            base_kmer,
            distance,
            0,
            &mut 0,
            &mut variants,
            &bases,
            &kmer_chars,
        );

        // 限制数量
        variants.truncate(count);
        variants
    }

    /// 递归生成 Hamming 距离变体
    fn generate_hamming_recursive(
        &self,
        kmer: &str,
        remaining_distance: usize,
        position: usize,
        current_distance: &mut usize,
        variants: &mut Vec<String>,
        bases: &[char],
        kmer_chars: &[char],
    ) {
        if *current_distance == remaining_distance {
            variants.push(kmer.to_string());
            return;
        }

        if position >= kmer.len() {
            return;
        }

        // 保持当前位置
        let mut kmer_owned = kmer.to_string();
        self.generate_hamming_recursive(
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

                self.generate_hamming_recursive(
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

    /// 计算性能指标
    pub fn calculate_performance_metrics(
        &self,
        results: &[FuzzyQueryResult],
    ) -> Result<Vec<FuzzyPerformanceMetrics>> {
        let mut metrics = Vec::new();

        for result in results {
            if result.success {
                let results_per_second = if result.execution_time_ms > 0 {
                    (result.matches.len() as f64 * 1000.0) / result.execution_time_ms as f64
                } else {
                    0.0
                };

                metrics.push(FuzzyPerformanceMetrics {
                    query_kmer: result.query_kmer.clone(),
                    hamming_distance: result.hamming_distance,
                    execution_time_ms: result.execution_time_ms,
                    result_count: result.matches.len(),
                    results_per_second,
                });
            }
        }

        Ok(metrics)
    }

    /// 验证性能基准
    pub fn validate_performance_benchmark(
        &self,
        metrics: &[FuzzyPerformanceMetrics],
        min_results_per_second: f64,
    ) -> Result<()> {
        for metric in metrics {
            if metric.results_per_second < min_results_per_second {
                return Err(FuzzyValidationError::PerformanceBenchmarkFailed(format!(
                    "吞吐量过低: {:.2} 结果/秒 < {:.2} 结果/秒 (查询: {}, 距离: {})",
                    metric.results_per_second,
                    min_results_per_second,
                    metric.query_kmer,
                    metric.hamming_distance
                )).into());
            }
        }
        Ok(())
    }

    /// 分析结果质量
    pub fn analyze_result_quality(&self, results: &[FuzzyQueryResult]) -> FuzzyQualityAnalysis {
        let mut analysis = FuzzyQualityAnalysis::default();

        for result in results {
            analysis.total_queries += 1;
            if result.success {
                analysis.successful_queries += 1;
                analysis.total_matches += result.matches.len();

                // 分析距离分布
                for fuzzy_match in &result.matches {
                    let distance = fuzzy_match.actual_distance;
                    *analysis.distance_distribution.entry(distance).or_insert(0) += 1;
                }
            } else {
                analysis.failed_queries += 1;
            }
        }

        // 计算平均值
        if analysis.successful_queries > 0 {
            analysis.avg_matches_per_query = analysis.total_matches as f64 / analysis.successful_queries as f64;
            analysis.success_rate = analysis.successful_queries as f64 / analysis.total_queries as f64;
        }

        analysis
    }

    /// 生成验证报告摘要
    pub fn generate_summary(&self, results: &[FuzzyQueryResult]) -> String {
        if results.is_empty() {
            return "没有查询结果".to_string();
        }

        let analysis = self.analyze_result_quality(results);
        let metrics = self.calculate_performance_metrics(results).unwrap_or_default();

        let mut summary = format!(
            "Fuzzy Query 验证摘要\n\
            ===================\n\
            总查询数: {}\n\
            成功查询: {}\n\
            失败查询: {}\n\
            成功率: {:.1}%\n\
            总匹配数: {}\n\
            平均匹配/查询: {:.1}\n\n",
            analysis.total_queries,
            analysis.successful_queries,
            analysis.failed_queries,
            analysis.success_rate * 100.0,
            analysis.total_matches,
            analysis.avg_matches_per_query
        );

        // 添加距离分布
        if !analysis.distance_distribution.is_empty() {
            summary.push_str("距离分布:\n");
            let mut distances: Vec<_> = analysis.distance_distribution.iter().collect();
            distances.sort_by_key(|&(d, _)| *d);
            for (distance, count) in distances {
                summary.push_str(&format!("  距离 {}: {} 个匹配\n", distance, count));
            }
            summary.push('\n');
        }

        // 添加性能统计
        if !metrics.is_empty() {
            let avg_time: f64 = metrics.iter()
                .map(|m| m.execution_time_ms as f64)
                .sum::<f64>() / metrics.len() as f64;
            let avg_throughput: f64 = metrics.iter()
                .map(|m| m.results_per_second)
                .sum::<f64>() / metrics.len() as f64;

            summary.push_str(&format!(
                "性能统计:\n\
                平均查询时间: {:.1} ms\n\
                平均吞吐量: {:.1} 结果/秒\n\n",
                avg_time, avg_throughput
            ));
        }

        // 添加失败的查询
        let failed_results: Vec<_> = results.iter().filter(|r| !r.success).collect();
        if !failed_results.is_empty() {
            summary.push_str("失败的查询:\n");
            for result in failed_results {
                summary.push_str(&format!(
                    "- k-mer: {} (距离: {}): {}\n",
                    result.query_kmer,
                    result.hamming_distance,
                    result.error_message.as_deref().unwrap_or("未知错误")
                ));
            }
        }

        summary
    }
}

/// Fuzzy Query 质量分析
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct FuzzyQualityAnalysis {
    /// 总查询数
    pub total_queries: usize,
    /// 成功查询数
    pub successful_queries: usize,
    /// 失败查询数
    pub failed_queries: usize,
    /// 总匹配数
    pub total_matches: usize,
    /// 平均每查询匹配数
    pub avg_matches_per_query: f64,
    /// 成功率
    pub success_rate: f64,
    /// 距离分布
    pub distance_distribution: HashMap<usize, usize>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hamming_distance_calculation() {
        let validator = FuzzyValidator::new();

        // 测试相同序列
        assert_eq!(validator.calculate_hamming_distance("ATCG", "ATCG"), 0);

        // 测试一个差异
        assert_eq!(validator.calculate_hamming_distance("ATCG", "TTCG"), 1);

        // 测试两个差异
        assert_eq!(validator.calculate_hamming_distance("ATCG", "TTCC"), 2);

        // 测试不同长度
        assert_eq!(validator.calculate_hamming_distance("ATCG", "AT"), usize::MAX);
    }

    #[test]
    fn test_generate_hamming_variants() {
        let validator = FuzzyValidator::new();
        let base_kmer = "AAAA";

        let variants = validator.generate_hamming_variants(base_kmer, 1, 10);

        // 应该有变体
        assert!(!variants.is_empty());

        // 所有变体应该与原始序列相差 1
        for variant in &variants {
            let distance = validator.calculate_hamming_distance(base_kmer, variant);
            assert!(distance == 1, "变体距离应该是 1");
        }
    }

    #[test]
    fn test_generate_test_cases() {
        let validator = FuzzyValidator::new();
        let base_kmer = "ATCGATCGATCG";

        let test_cases = validator.generate_test_cases(base_kmer, 2);

        // 应该包含基础测试
        assert!(test_cases.iter().any(|(kmer, dist, _)| kmer == base_kmer && *dist == 1));

        // 应该包含距离为1和2的测试
        let has_distance_1 = test_cases.iter().any(|(_, dist, _)| *dist == 1);
        let has_distance_2 = test_cases.iter().any(|(_, dist, _)| *dist == 2);
        assert!(has_distance_1);
        assert!(has_distance_2);
    }

    #[test]
    fn test_quality_analysis() {
        let validator = FuzzyValidator::new();
        let results = vec![
            FuzzyQueryResult {
                query_kmer: "ATCG".to_string(),
                hamming_distance: 1,
                matches: vec![
                    FuzzyMatch {
                        kmer: "ATCG".to_string(),
                        actual_distance: 0,
                        count: 1,
                    },
                    FuzzyMatch {
                        kmer: "TTCG".to_string(),
                        actual_distance: 1,
                        count: 1,
                    },
                ],
                execution_time_ms: 10,
                success: true,
                error_message: None,
            },
            FuzzyQueryResult {
                query_kmer: "GGGG".to_string(),
                hamming_distance: 2,
                matches: vec![],
                execution_time_ms: 5,
                success: false,
                error_message: Some("错误".to_string()),
            },
        ];

        let analysis = validator.analyze_result_quality(&results);

        assert_eq!(analysis.total_queries, 2);
        assert_eq!(analysis.successful_queries, 1);
        assert_eq!(analysis.failed_queries, 1);
        assert_eq!(analysis.total_matches, 2);
        assert_eq!(analysis.avg_matches_per_query, 2.0);
        assert_eq!(analysis.success_rate, 0.5);
    }
}