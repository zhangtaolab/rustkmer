use std::collections::HashMap;
use std::process::Command;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};

/// Stats 验证错误类型
#[derive(Debug, thiserror::Error)]
pub enum StatsValidationError {
    #[error("数据库文件不存在: {0}")]
    DatabaseNotFound(String),

    #[error("统计命令执行失败: {0}")]
    StatsExecutionFailed(String),

    #[error("无效的统计输出格式: {0}")]
    InvalidOutputFormat(String),

    #[error("缺少必要的统计字段: {0}")]
    MissingRequiredField(String),

    #[error("统计值验证失败: {0}")]
    StatsValueValidationFailed(String),

    #[error("性能指标验证失败: {0}")]
    PerformanceValidationFailed(String),
}

/// 统计信息结构
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseStats {
    /// k-mer 大小
    pub kmer_size: usize,
    /// 总 k-mer 数（包括重复）
    pub total_kmers: u64,
    /// 唯一 k-mer 数
    pub unique_kmers: u64,
    /// 不同的序列数
    pub distinct_sequences: Option<u64>,
    /// 数据库文件大小
    pub file_size_bytes: Option<u64>,
    /// 加载时间（毫秒）
    pub load_time_ms: Option<u64>,
}

/// Stats 验证器
pub struct StatsValidator {
    /// 严格模式（更严格的验证）
    pub strict_mode: bool,
    /// 性能阈值（秒）
    pub performance_threshold_secs: f64,
}

impl StatsValidator {
    /// 创建新的统计验证器
    pub fn new() -> Self {
        Self {
            strict_mode: false,
            performance_threshold_secs: 10.0, // 默认10秒阈值
        }
    }

    /// 创建严格模式的验证器
    pub fn strict() -> Self {
        Self {
            strict_mode: true,
            performance_threshold_secs: 5.0, // 严格模式下5秒阈值
        }
    }

    /// 设置性能阈值
    pub fn with_performance_threshold(mut self, threshold_secs: f64) -> Self {
        self.performance_threshold_secs = threshold_secs;
        self
    }

    /// 执行 stats 命令并验证
    pub fn execute_and_validate<P: AsRef<Path>>(
        &self,
        database_path: P,
    ) -> Result<DatabaseStats> {
        let start_time = std::time::Instant::now();

        // 验证数据库文件存在
        let path = database_path.as_ref();
        if !path.exists() {
            return Err(StatsValidationError::DatabaseNotFound(path.to_string_lossy().to_string()).into());
        }

        // 执行 stats 命令
        let output = Command::new("rustkmer")
            .args(["stats", path.to_string_lossy().as_ref()])
            .output()
            .with_context(|| "无法执行 rustkmer stats")?;

        let execution_time = start_time.elapsed();

        if !output.status.success() {
            return Err(StatsValidationError::StatsExecutionFailed(
                String::from_utf8_lossy(&output.stderr).to_string()
            ).into());
        }

        // 解析统计输出
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stats = self.parse_stats_output(&stdout, path)?;

        // 验证性能
        if execution_time.as_secs_f64() > self.performance_threshold_secs {
            if self.strict_mode {
                return Err(StatsValidationError::PerformanceValidationFailed(format!(
                    "执行时间过长: {:.2}秒 > {:.2}秒",
                    execution_time.as_secs_f64(),
                    self.performance_threshold_secs
                )).into());
            } else {
                eprintln!("警告: stats 执行时间较长: {:.2}秒", execution_time.as_secs_f64());
            }
        }

        // 验证统计值
        self.validate_stats_values(&stats)?;

        Ok(stats)
    }

    /// 解析 stats 命令输出
    fn parse_stats_output(
        &self,
        output: &str,
        database_path: &Path,
    ) -> Result<DatabaseStats> {
        let mut stats = DatabaseStats {
            kmer_size: 0,
            total_kmers: 0,
            unique_kmers: 0,
            distinct_sequences: None,
            file_size_bytes: None,
            load_time_ms: None,
        };

        // 获取文件大小
        if let Ok(metadata) = fs::metadata(database_path) {
            stats.file_size_bytes = Some(metadata.len());
        }

        // 解析输出行
        let mut found_fields = HashMap::new();

        for line in output.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            // 尝试解析不同格式的输出
            self.parse_line(line, &mut found_fields);
        }

        // 提取 k-mer 大小
        if let Some(ksize) = self.extract_number_from_field(&found_fields, "k-mer") {
            stats.kmer_size = ksize;
        } else if let Some(ksize) = self.extract_number_from_field(&found_fields, "kmer") {
            stats.kmer_size = ksize;
        }

        // 提取总数
        if let Some(total) = self.extract_number_from_field(&found_fields, "total") {
            stats.total_kmers = total;
        } else if let Some(count) = self.extract_number_from_field(&found_fields, "count") {
            stats.total_kmers = count;
        }

        // 提取唯一数
        if let Some(unique) = self.extract_number_from_field(&found_fields, "unique") {
            stats.unique_kmers = unique;
        } else if let Some(distinct) = self.extract_number_from_field(&found_fields, "distinct") {
            stats.unique_kmers = distinct;
        }

        // 提取序列数（可选）
        stats.distinct_sequences = self.extract_number_from_field(&found_fields, "sequence");

        Ok(stats)
    }

    /// 解析单行输出
    fn parse_line(&self, line: &str, fields: &mut HashMap<String, String>) {
        let line_lower = line.to_lowercase();

        // 尝试不同的格式
        if line.contains(':') {
            // 格式: "k-mer size: 31"
            let parts: Vec<&str> = line.splitn(2, ':').collect();
            if parts.len() == 2 {
                let key = parts[0].trim().to_lowercase();
                let value = parts[1].trim().to_string();
                fields.insert(key, value);
            }
        } else if line_lower.contains("k-mer") {
            // 格式: "k-mer 31: total 1000, unique 800"
            self.extract_key_value_pairs(line, fields);
        } else {
            // 尝试从行中提取数字
            if let Some(number) = self.extract_first_number(line) {
                // 根据上下文推断字段名
                let field_name = self.infer_field_name(line);
                if let Some(name) = field_name {
                    fields.insert(name, number.to_string());
                }
            }
        }
    }

    /// 从行中提取键值对
    fn extract_key_value_pairs(&self, line: &str, fields: &mut HashMap<String, String>) {
        let words: Vec<&str> = line.split_whitespace().collect();

        for i in 0..words.len() {
            let word_lower = words[i].to_lowercase();
            if word_lower.contains("k-mer") || word_lower.contains("kmer") {
                if i + 1 < words.len() {
                    if let Ok(ksize) = words[i + 1].parse::<usize>() {
                        fields.insert("k-mer".to_string(), ksize.to_string());
                    }
                }
            } else if word_lower == "total" || word_lower == "count:" {
                if i + 1 < words.len() {
                    if let Ok(total) = words[i + 1].parse::<u64>() {
                        fields.insert("total".to_string(), total.to_string());
                    }
                }
            } else if word_lower == "unique" || word_lower == "distinct" {
                if i + 1 < words.len() {
                    if let Ok(unique) = words[i + 1].parse::<u64>() {
                        fields.insert("unique".to_string(), unique.to_string());
                    }
                }
            }
        }
    }

    /// 从字段中提取数字
    fn extract_number_from_field(&self, fields: &HashMap<String, String>, field_name: &str) -> Option<u64> {
        for (key, value) in fields {
            if key.contains(field_name) {
                // 尝试解析数字
                if let Ok(num) = value.parse::<u64>() {
                    return Some(num);
                }
                // 如果值不是纯数字，尝试从中提取数字
                if let Some(num) = self.extract_first_number(value) {
                    return Some(num);
                }
            }
        }
        None
    }

    /// 从字符串中提取第一个数字
    fn extract_first_number(&self, s: &str) -> Option<u64> {
        s.split_whitespace()
            .find_map(|word| word.parse::<u64>().ok())
    }

    /// 推断字段名
    fn infer_field_name(&self, line: &str) -> Option<String> {
        let line_lower = line.to_lowercase();
        if line_lower.contains("k-mer") || line_lower.contains("kmer") {
            Some("k-mer".to_string())
        } else if line_lower.contains("total") || line_lower.contains("count") {
            Some("total".to_string())
        } else if line_lower.contains("unique") || line_lower.contains("distinct") {
            Some("unique".to_string())
        } else {
            None
        }
    }

    /// 验证统计值
    fn validate_stats_values(&self, stats: &DatabaseStats) -> Result<()> {
        // 验证 k-mer 大小
        if stats.kmer_size == 0 {
            return Err(StatsValidationError::StatsValueValidationFailed(
                "k-mer 大小不能为 0".to_string()
            ).into());
        }

        // 验证 k-mer 大小在合理范围内
        if stats.kmer_size > 128 {
            return Err(StatsValidationError::StatsValueValidationFailed(
                format!("k-mer 大小过大: {}", stats.kmer_size)
            ).into());
        }

        // 验证总数和唯一数的关系
        if stats.unique_kmers > stats.total_kmers {
            return Err(StatsValidationError::StatsValueValidationFailed(
                format!("唯一 k-mers ({}) 不能大于总数 ({})", stats.unique_kmers, stats.total_kmers)
            ).into());
        }

        // 严格模式下的额外验证
        if self.strict_mode {
            // 验证 k-mer 大小的合理性
            if stats.kmer_size % 2 != 0 {
                eprintln!("警告: k-mer 大小不是偶数: {}", stats.kmer_size);
            }

            // 验证是否有合理的唯一/总数比例
            if stats.total_kmers > 0 {
                let ratio = stats.unique_kmers as f64 / stats.total_kmers as f64;
                if ratio > 1.0 {
                    return Err(StatsValidationError::StatsValueValidationFailed(
                        format!("唯一/总数比例异常: {:.2}", ratio)
                    ).into());
                }
            }
        }

        Ok(())
    }

    /// 验证多个数据库的统计信息
    pub fn validate_multiple_databases<P: AsRef<Path>>(
        &self,
        database_paths: &[P],
    ) -> Result<Vec<DatabaseStats>> {
        let mut results = Vec::new();
        let mut errors = Vec::new();

        for (i, path) in database_paths.iter().enumerate() {
            match self.execute_and_validate(path) {
                Ok(stats) => results.push(stats),
                Err(e) => {
                    errors.push(format!("数据库 {}: {}", i + 1, e));
                    if self.strict_mode {
                        return Err(e);
                    } else {
                        eprintln!("警告: {}", errors.last().unwrap());
                    }
                }
            }
        }

        if !errors.is_empty() && self.strict_mode {
            return Err(anyhow::anyhow!("部分数据库验证失败: {}", errors.join("; ")));
        }

        Ok(results)
    }

    /// 生成统计报告
    pub fn generate_report(&self, stats_list: &[DatabaseStats]) -> String {
        let mut report = String::new();
        report.push_str("# 数据库统计报告\n\n");
        report.push_str(&format!("验证时间: {}\n", chrono::Utc::now().format("%Y-%m-%d %H:%M:%S UTC")));
        report.push_str(&format!("数据库数量: {}\n\n", stats_list.len()));

        report.push_str("## 统计摘要\n\n");

        if !stats_list.is_empty() {
            let total_kmers: u64 = stats_list.iter().map(|s| s.total_kmers).sum();
            let total_unique: u64 = stats_list.iter().map(|s| s.unique_kmers).sum();
            let avg_ksize = stats_list.iter().map(|s| s.kmer_size).sum::<usize>() as f64 / stats_list.len() as f64;

            report.push_str(&format!("- 总 k-mers: {}\n", total_kmers));
            report.push_str(&format!("- 总唯一 k-mers: {}\n", total_unique));
            report.push_str(&format!("- 平均 k-mer 大小: {:.1}\n", avg_ksize));
            report.push_str(&format!("- 总体唯一率: {:.2}%\n\n", (total_unique as f64 / total_kmers as f64) * 100.0));
        }

        report.push_str("## 详细统计\n\n");
        report.push_str("| 数据库 | k-mer 大小 | 总数 | 唯一数 | 唯一率 | 文件大小 |\n");
        report.push_str("|--------|------------|------|--------|--------|----------|\n");

        for (i, stats) in stats_list.iter().enumerate() {
            let uniqueness_rate = if stats.total_kmers > 0 {
                (stats.unique_kmers as f64 / stats.total_kmers as f64) * 100.0
            } else {
                0.0
            };

            let file_size = stats.file_size_bytes
                .map(|bytes| self.format_bytes(bytes))
                .unwrap_or_else(|| "N/A".to_string());

            report.push_str(&format!(
                "| DB {} | {} | {} | {} | {:.1}% | {} |\n",
                i + 1,
                stats.kmer_size,
                stats.total_kmers,
                stats.unique_kmers,
                uniqueness_rate,
                file_size
            ));
        }

        report
    }

    /// 格式化字节数
    fn format_bytes(&self, bytes: u64) -> String {
        const UNITS: &[&str] = &["B", "KB", "MB", "GB"];
        let mut size = bytes as f64;
        let mut unit_index = 0;

        while size >= 1024.0 && unit_index < UNITS.len() - 1 {
            size /= 1024.0;
            unit_index += 1;
        }

        format!("{:.1} {}", size, UNITS[unit_index])
    }
}

impl Default for StatsValidator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    #[test]
    fn test_stats_validator_creation() {
        let validator = StatsValidator::new();
        assert!(!validator.strict_mode);
        assert_eq!(validator.performance_threshold_secs, 10.0);

        let strict_validator = StatsValidator::strict();
        assert!(strict_validator.strict_mode);
        assert_eq!(strict_validator.performance_threshold_secs, 5.0);
    }

    #[test]
    fn test_parse_stats_output() {
        let validator = StatsValidator::new();

        // 测试不同的输出格式
        let outputs = vec![
            "k-mer size: 31\nTotal k-mers: 1000\nUnique k-mers: 800",
            "k-mer 31: total 1000, unique 800",
            "K-mer Size = 31\nTotal Count = 1000\nUnique Count = 800",
        ];

        for output in outputs {
            let mut fields = HashMap::new();
            for line in output.lines() {
                validator.parse_line(line, &mut fields);
            }

            assert!(fields.contains_key("k-mer"));
            assert!(fields.contains_key("total"));
            assert!(fields.contains_key("unique"));
        }
    }

    #[test]
    fn test_extract_number_from_field() {
        let validator = StatsValidator::new();

        let mut fields = HashMap::new();
        fields.insert("k-mer size".to_string(), "31".to_string());
        fields.insert("total k-mers".to_string(), "1000".to_string());
        fields.insert("unique k-mers".to_string(), "800".to_string());

        assert_eq!(validator.extract_number_from_field(&fields, "k-mer"), Some(31));
        assert_eq!(validator.extract_number_from_field(&fields, "total"), Some(1000));
        assert_eq!(validator.extract_number_from_field(&fields, "unique"), Some(800));
        assert_eq!(validator.extract_number_from_field(&fields, "nonexistent"), None);
    }

    #[test]
    fn test_format_bytes() {
        let validator = StatsValidator::new();

        assert_eq!(validator.format_bytes(500), "500.0 B");
        assert_eq!(validator.format_bytes(1536), "1.5 KB");
        assert_eq!(validator.format_bytes(1048576), "1.0 MB");
        assert_eq!(validator.format_bytes(1073741824), "1.0 GB");
    }
}