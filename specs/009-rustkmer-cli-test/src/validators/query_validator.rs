use std::collections::HashMap;
use std::process::Command;
use std::fs;
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};

/// 查询验证错误类型
#[derive(Debug, thiserror::Error)]
pub enum QueryValidationError {
    #[error("数据库文件不存在: {0}")]
    DatabaseNotFound(String),

    #[error("查询命令执行失败: {0}")]
    QueryExecutionFailed(String),

    #[error("k-mer 格式无效: {0}")]
    InvalidKmer(String),

    #[error("解析查询结果失败: {0}")]
    ParseResultFailed(String),

    #[error("期望计数不匹配: 期望 {expected}, 实际 {actual}")]
    CountMismatch { expected: u64, actual: u64 },

    #[error("数据库完整性验证失败: {0}")]
    DatabaseIntegrityFailed(String),
}

/// 查询结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResult {
    /// k-mer 序列
    pub kmer: String,
    /// 查询到的计数
    pub count: u64,
    /// 查询执行时间（毫秒）
    pub execution_time_ms: u64,
    /// 是否成功
    pub success: bool,
    /// 错误信息（如果有）
    pub error_message: Option<String>,
}

/// 数据库信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseInfo {
    /// 数据库文件路径
    pub path: String,
    /// k-mer 大小
    pub kmer_size: usize,
    /// 数据库中的总 k-mer 数
    pub total_kmers: u64,
    /// 唯一 k-mer 数
    pub unique_kmers: u64,
    /// 数据库文件大小（字节）
    pub file_size: u64,
}

/// 查询验证器
pub struct QueryValidator {
    /// 数据库信息缓存
    database_cache: HashMap<String, DatabaseInfo>,
}

impl QueryValidator {
    /// 创建新的查询验证器
    pub fn new() -> Self {
        Self {
            database_cache: HashMap::new(),
        }
    }

    /// 验证数据库文件
    pub fn validate_database(&mut self, database_path: &str) -> Result<DatabaseInfo> {
        // 检查缓存
        if let Some(info) = self.database_cache.get(database_path) {
            return Ok(info.clone());
        }

        // 检查文件是否存在
        if !std::path::Path::new(database_path).exists() {
            return Err(QueryValidationError::DatabaseNotFound(database_path.to_string()).into());
        }

        // 获取文件大小
        let metadata = fs::metadata(database_path)
            .with_context(|| format!("无法读取数据库文件元数据: {}", database_path))?;
        let file_size = metadata.len();

        // 使用 rustkmer stats 获取数据库信息
        let output = Command::new("rustkmer")
            .args(["stats", database_path])
            .output()
            .with_context(|| "无法执行 rustkmer stats")?;

        if !output.status.success() {
            return Err(QueryValidationError::DatabaseIntegrityFailed(
                String::from_utf8_lossy(&output.stderr).to_string()
            ).into());
        }

        // 解析 stats 输出
        let stdout = String::from_utf8_lossy(&output.stdout);
        let info = self.parse_stats_output(database_path, &stdout, file_size)?;

        // 缓存结果
        self.database_cache.insert(database_path.to_string(), info.clone());
        Ok(info)
    }

    /// 解析 stats 输出
    fn parse_stats_output(&self, database_path: &str, output: &str, file_size: u64) -> Result<DatabaseInfo> {
        let mut kmer_size = 0;
        let mut total_kmers = 0u64;
        let mut unique_kmers = 0u64;

        for line in output.lines() {
            if line.contains("k-mer size") || line.contains("k-mer length") {
                if let Some(num) = line.chars()
                    .filter(|c| c.is_ascii_digit())
                    .collect::<String>()
                    .parse::<usize>() {
                    kmer_size = num;
                }
            } else if line.contains("total") && line.contains("k-mers") {
                if let Some(num) = line.chars()
                    .filter(|c| c.is_ascii_digit())
                    .collect::<String>()
                    .parse::<u64>() {
                    total_kmers = num;
                }
            } else if line.contains("unique") && line.contains("k-mers") {
                if let Some(num) = line.chars()
                    .filter(|c| c.is_ascii_digit())
                    .collect::<String>()
                    .parse::<u64>() {
                    unique_kmers = num;
                }
            }
        }

        Ok(DatabaseInfo {
            path: database_path.to_string(),
            kmer_size,
            total_kmers,
            unique_kmers,
            file_size,
        })
    }

    /// 验证 k-mer 格式
    pub fn validate_kmer(&self, kmer: &str, expected_length: usize) -> Result<()> {
        if kmer.is_empty() {
            return Err(QueryValidationError::InvalidKmer("k-mer 为空".to_string()).into());
        }

        if kmer.len() != expected_length {
            return Err(QueryValidationError::InvalidKmer(
                format!("k-mer 长度不匹配: 期望 {}, 实际 {}", expected_length, kmer.len())
            ).into());
        }

        // 检查是否只包含 ATCG
        if !kmer.chars().all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G')) {
            return Err(QueryValidationError::InvalidKmer(
                format!("k-mer 包含无效字符: {}", kmer)
            ).into());
        }

        Ok(())
    }

    /// 执行单个查询并验证
    pub fn execute_query(&self, database_path: &str, kmer: &str) -> Result<QueryResult> {
        let start_time = std::time::Instant::now();

        let output = Command::new("rustkmer")
            .args(["query", database_path, kmer])
            .output()
            .with_context(|| "无法执行 rustkmer query")?;

        let execution_time_ms = start_time.elapsed().as_millis() as u64;

        if !output.status.success() {
            return Ok(QueryResult {
                kmer: kmer.to_string(),
                count: 0,
                execution_time_ms,
                success: false,
                error_message: Some(String::from_utf8_lossy(&output.stderr).to_string()),
            });
        }

        // 解析查询结果
        let stdout = String::from_utf8_lossy(&output.stdout);
        let count = self.parse_query_count(&stdout)?;

        Ok(QueryResult {
            kmer: kmer.to_string(),
            count,
            execution_time_ms,
            success: true,
            error_message: None,
        })
    }

    /// 解析查询结果计数
    fn parse_query_count(&self, output: &str) -> Result<u64> {
        // 查找数字模式
        for line in output.lines() {
            // 提取第一个数字（假设格式为 "k-mer: X" 或 "Count: X"）
            if let Some(num_str) = line.split_whitespace()
                .find(|s| s.chars().all(|c| c.is_ascii_digit())) {
                return Ok(num_str.parse::<u64>()
                    .with_context(|| format!("无法解析数字: {}", num_str))?);
            }
        }

        // 如果没有找到明确的数字，尝试在整个输出中查找
        let mut found_numbers = Vec::new();
        for word in output.split_whitespace() {
            if word.chars().all(|c| c.is_ascii_digit()) {
                found_numbers.push(word);
            }
        }

        if found_numbers.len() == 1 {
            Ok(found_numbers[0].parse::<u64>()?)
        } else if found_numbers.is_empty() {
            Ok(0) // 假设没有数字意味着计数为0
        } else {
            Err(QueryValidationError::ParseResultFailed(
                format!("找到多个可能的计数: {:?}", found_numbers)
            ).into())
        }
    }

    /// 验证查询准确性
    pub fn validate_query_accuracy(
        &mut self,
        database_path: &str,
        test_cases: &[(String, Option<u64>)],
    ) -> Result<Vec<QueryResult>> {
        let database_info = self.validate_database(database_path)?;
        let mut results = Vec::new();

        for (kmer, expected_count) in test_cases {
            // 验证 k-mer 格式
            if let Err(e) = self.validate_kmer(kmer, database_info.kmer_size) {
                results.push(QueryResult {
                    kmer: kmer.clone(),
                    count: 0,
                    execution_time_ms: 0,
                    success: false,
                    error_message: Some(format!("k-mer 验证失败: {}", e)),
                });
                continue;
            }

            // 执行查询
            let result = self.execute_query(database_path, kmer)?;

            // 验证结果（如果有期望值）
            if let (Some(expected), Some(actual)) = (expected_count, result.success.then_some(result.count)) {
                if expected != actual {
                    results.push(QueryResult {
                        kmer: kmer.clone(),
                        count: actual,
                        execution_time_ms: result.execution_time_ms,
                        success: false,
                        error_message: Some(format!(
                            "计数不匹配: 期望 {}, 实际 {}",
                            expected, actual
                        )),
                    });
                } else {
                    results.push(result);
                }
            } else {
                results.push(result);
            }
        }

        Ok(results)
    }

    /// 生成测试 k-mers
    pub fn generate_test_kmers(&self, database_path: &str, count: usize) -> Result<Vec<String>> {
        // 使用 dump 命令获取一些实际的 k-mers
        let temp_file = format!("{}.dump.tmp", database_path);

        let output = Command::new("rustkmer")
            .args(["dump", database_path, "-o", &temp_file])
            .output()
            .with_context(|| "无法执行 rustkmer dump")?;

        if !output.status.success() {
            // 如果 dump 失败，返回一些默认的测试 k-mers
            return Ok(self.generate_default_kmers(count));
        }

        // 读取 dump 文件
        let content = fs::read_to_string(&temp_file)
            .with_context(|| format!("无法读取 dump 文件: {}", temp_file))?;

        // 清理临时文件
        let _ = fs::remove_file(&temp_file);

        // 解析 k-mers
        let mut kmers = Vec::new();
        for line in content.lines() {
            // 假设每行是一个 k-mer 或格式为 "kmer count"
            let parts: Vec<&str> = line.split_whitespace().collect();
            if !parts.is_empty() {
                let kmer = parts[0];
                if kmer.len() >= 21 && kmer.chars().all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G')) {
                    kmers.push(kmer.to_uppercase());
                    if kmers.len() >= count {
                        break;
                    }
                }
            }
        }

        // 如果没有找到足够的 k-mers，用默认值补充
        while kmers.len() < count {
            kmers.extend(self.generate_default_kmers(count - kmers.len()));
        }

        Ok(kmers)
    }

    /// 生成默认测试 k-mers
    fn generate_default_kmers(&self, count: usize) -> Vec<String> {
        let bases = ['A', 'T', 'C', 'G'];
        let mut kmers = Vec::new();

        for i in 0..count {
            let mut kmer = String::new();
            for j in 0..31 {
                kmer.push(bases[(i * 31 + j) % 4]);
            }
            kmers.push(kmer);
        }

        kmers
    }

    /// 计算查询性能统计
    pub fn calculate_performance_stats(&self, results: &[QueryResult]) -> Result<QueryPerformanceStats> {
        let successful_queries: Vec<_> = results.iter()
            .filter(|r| r.success)
            .collect();

        if successful_queries.is_empty() {
            return Ok(QueryPerformanceStats::default());
        }

        let total_time: u64 = successful_queries.iter()
            .map(|r| r.execution_time_ms)
            .sum();

        let avg_time = total_time as f64 / successful_queries.len() as f64;
        let min_time = successful_queries.iter()
            .map(|r| r.execution_time_ms)
            .min()
            .unwrap_or(0);
        let max_time = successful_queries.iter()
            .map(|r| r.execution_time_ms)
            .max()
            .unwrap_or(0);

        let total_counts: u64 = successful_queries.iter()
            .map(|r| r.count)
            .sum();

        Ok(QueryPerformanceStats {
            total_queries: results.len(),
            successful_queries: successful_queries.len(),
            failed_queries: results.len() - successful_queries.len(),
            avg_execution_time_ms: avg_time,
            min_execution_time_ms: min_time,
            max_execution_time_ms: max_time,
            total_kmer_count: total_counts,
        })
    }
}

/// 查询性能统计
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryPerformanceStats {
    /// 总查询数
    pub total_queries: usize,
    /// 成功查询数
    pub successful_queries: usize,
    /// 失败查询数
    pub failed_queries: usize,
    /// 平均执行时间（毫秒）
    pub avg_execution_time_ms: f64,
    /// 最小执行时间（毫秒）
    pub min_execution_time_ms: u64,
    /// 最大执行时间（毫秒）
    pub max_execution_time_ms: u64,
    /// 总 k-mer 计数
    pub total_kmer_count: u64,
}

impl Default for QueryPerformanceStats {
    fn default() -> Self {
        Self {
            total_queries: 0,
            successful_queries: 0,
            failed_queries: 0,
            avg_execution_time_ms: 0.0,
            min_execution_time_ms: 0,
            max_execution_time_ms: 0,
            total_kmer_count: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kmer_validation() {
        let validator = QueryValidator::new();

        // 测试有效的 k-mer
        assert!(validator.validate_kmer("ATCGATCGATCGATCGATCGATCGATCGATCG", 31).is_ok());

        // 测试无效的 k-mer
        assert!(validator.validate_kmer("ATCGX", 5).is_err());
        assert!(validator.validate_kmer("", 31).is_err());
        assert!(validator.validate_kmer("ATCG", 5).is_err());
    }
}