use std::collections::HashMap;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};

/// Dump 验证错误类型
#[derive(Debug, thiserror::Error)]
pub enum DumpValidationError {
    #[error("输出文件不存在: {0}")]
    OutputFileNotFound(String),

    #[error("输出文件为空: {0}")]
    OutputFileEmpty(String),

    #[error("无效的输出格式: {0}")]
    InvalidOutputFormat(String),

    #[error("k-mer 格式错误: {0}")]
    InvalidKmerFormat(String),

    #[error("JSON 解析失败: {0}")]
    JsonParseFailed(String),

    #[error("性能基准失败: {0}")]
    PerformanceBenchmarkFailed(String),
}

/// Dump 输出格式枚举
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DumpOutputFormat {
    Text,
    Json,
}

/// Dump 验证结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DumpValidationResult {
    /// 输出文件路径
    pub output_file: String,
    /// 输出格式
    pub format: DumpOutputFormat,
    /// 验证是否成功
    pub success: bool,
    /// 总行数
    pub total_lines: usize,
    /// 有效 k-mer 行数
    pub valid_kmer_lines: usize,
    /// 空行数
    pub empty_lines: usize,
    /// 错误行数
    pub error_lines: usize,
    /// 文件大小（字节）
    pub file_size: u64,
    /// k-mer 大小分布
    pub kmer_size_distribution: HashMap<usize, usize>,
    /// 错误消息（如果有）
    pub error_message: Option<String>,
}

/// Dump 性能指标
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DumpPerformanceMetrics {
    /// 执行时间（秒）
    pub execution_time_seconds: f64,
    /// 数据库大小（字节）
    pub database_size_bytes: u64,
    /// 输出大小（字节）
    pub output_size_bytes: u64,
    /// 吞吐量（字节/秒）
    pub throughput_bytes_per_second: f64,
    /// 内存使用峰值（字节）
    pub peak_memory_bytes: Option<u64>,
}

/// Dump 验证器
pub struct DumpValidator {
    /// k-mer 大小（如果已知）
    pub expected_kmer_size: Option<usize>,
    /// 严格模式（更严格的验证）
    pub strict_mode: bool,
}

impl DumpValidator {
    /// 创建新的 dump 验证器
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

    /// 验证 dump 输出文件
    pub fn validate_dump_output<P: AsRef<Path>>(&self, output_file: P) -> Result<DumpValidationResult> {
        let output_path = output_file.as_ref();
        let file_path = output_path.to_string_lossy().to_string();

        // 检查文件是否存在
        if !output_path.exists() {
            return Ok(DumpValidationResult {
                output_file: file_path.clone(),
                format: DumpOutputFormat::Text,
                success: false,
                total_lines: 0,
                valid_kmer_lines: 0,
                empty_lines: 0,
                error_lines: 0,
                file_size: 0,
                kmer_size_distribution: HashMap::new(),
                error_message: Some(DumpValidationError::OutputFileNotFound(file_path).to_string()),
            });
        }

        // 获取文件大小
        let metadata = fs::metadata(output_path)
            .with_context(|| format!("无法读取文件元数据: {}", file_path))?;
        let file_size = metadata.len();

        // 检查文件是否为空
        if file_size == 0 {
            return Ok(DumpValidationResult {
                output_file: file_path.clone(),
                format: DumpOutputFormat::Text,
                success: false,
                total_lines: 0,
                valid_kmer_lines: 0,
                empty_lines: 0,
                error_lines: 0,
                file_size,
                kmer_size_distribution: HashMap::new(),
                error_message: Some(DumpValidationError::OutputFileEmpty(file_path).to_string()),
            });
        }

        // 读取文件内容
        let content = fs::read_to_string(output_path)
            .with_context(|| format!("无法读取文件内容: {}", file_path))?;

        // 检测文件格式
        let format = self.detect_output_format(&content);

        // 根据格式进行验证
        match format {
            DumpOutputFormat::Json => self.validate_json_output(&content, &file_path, file_size),
            DumpOutputFormat::Text => self.validate_text_output(&content, &file_path, file_size),
        }
    }

    /// 检测输出格式
    fn detect_output_format(&self, content: &str) -> DumpOutputFormat {
        // 检查是否以 { 开始（JSON）
        let trimmed = content.trim_start();
        if trimmed.starts_with('{') || trimmed.starts_with('[') {
            return DumpOutputFormat::Json;
        }

        // 默认为文本格式
        DumpOutputFormat::Text
    }

    /// 验证 JSON 格式输出
    fn validate_json_output(&self, content: &str, file_path: &str, file_size: u64) -> Result<DumpValidationResult> {
        // 尝试解析 JSON
        let parsed: serde_json::Value = serde_json::from_str(content)
            .map_err(|e| DumpValidationError::JsonParseFailed(e.to_string()))?;

        let mut result = DumpValidationResult {
            output_file: file_path.to_string(),
            format: DumpOutputFormat::Json,
            success: true,
            total_lines: 0,
            valid_kmer_lines: 0,
            empty_lines: 0,
            error_lines: 0,
            file_size,
            kmer_size_distribution: HashMap::new(),
            error_message: None,
        };

        // 验证 JSON 结构
        if let serde_json::Value::Object(map) = parsed {
            // 检查常见的字段
            if let Some(kmers) = map.get("kmers") {
                if let serde_json::Value::Array(kmer_array) = kmers {
                    result.total_lines = kmer_array.len();

                    for kmer_entry in kmer_array {
                        if let serde_json::Value::Object(entry_map) = kmer_entry {
                            // 检查序列字段
                            if let Some(seq) = entry_map.get("sequence") {
                                if let serde_json::Value::String(seq_str) = seq {
                                    if self.is_valid_kmer(seq_str) {
                                        result.valid_kmer_lines += 1;
                                        let size = seq_str.len();
                                        *result.kmer_size_distribution.entry(size).or_insert(0) += 1;
                                    } else {
                                        result.error_lines += 1;
                                    }
                                }
                            }
                        } else {
                            result.error_lines += 1;
                        }
                    }
                }
            }
        }

        // 设置成功状态
        if result.error_lines > 0 && self.strict_mode {
            result.success = false;
            result.error_message = Some("JSON 格式验证失败（严格模式）".to_string());
        }

        Ok(result)
    }

    /// 验证文本格式输出
    fn validate_text_output(&self, content: &str, file_path: &str, file_size: u64) -> Result<DumpValidationResult> {
        let mut result = DumpValidationResult {
            output_file: file_path.to_string(),
            format: DumpOutputFormat::Text,
            success: true,
            total_lines: 0,
            valid_kmer_lines: 0,
            empty_lines: 0,
            error_lines: 0,
            file_size,
            kmer_size_distribution: HashMap::new(),
            error_message: None,
        };

        // 逐行验证
        for line in content.lines() {
            result.total_lines += 1;

            let trimmed = line.trim();
            if trimmed.is_empty() {
                result.empty_lines += 1;
                continue;
            }

            // 解析行（可能是 "kmer" 或 "kmer count" 格式）
            let parts: Vec<&str> = trimmed.split_whitespace().collect();
            if parts.is_empty() {
                result.error_lines += 1;
                continue;
            }

            let kmer = parts[0];
            if self.is_valid_kmer(kmer) {
                result.valid_kmer_lines += 1;
                let size = kmer.len();
                *result.kmer_size_distribution.entry(size).or_insert(0) += 1;

                // 检查计数格式
                if parts.len() > 1 {
                    if !parts[1].chars().all(|c| c.is_ascii_digit()) {
                        result.error_lines += 1;
                    }
                }
            } else {
                result.error_lines += 1;
            }
        }

        // 检查 k-mer 大小一致性
        if let (Some(expected_size), true) = (self.expected_kmer_size, !result.kmer_size_distribution.is_empty()) {
            if result.kmer_size_distribution.len() > 1 {
                result.success = false;
                result.error_message = Some(format!(
                    "k-mer 大小不一致，期望: {}, 实际: {:?}",
                    expected_size,
                    result.kmer_size_distribution.keys().collect::<Vec<_>>()
                ));
            } else if let Some(&actual_size) = result.kmer_size_distribution.keys().next() {
                if actual_size != expected_size {
                    result.success = false;
                    result.error_message = Some(format!(
                        "k-mer 大小不匹配，期望: {}, 实际: {}",
                        expected_size, actual_size
                    ));
                }
            }
        }

        // 设置成功状态
        if result.error_lines > 0 && self.strict_mode {
            result.success = false;
            if result.error_message.is_none() {
                result.error_message = Some("文本格式验证失败（严格模式）".to_string());
            }
        }

        Ok(result)
    }

    /// 检查是否是有效的 k-mer
    fn is_valid_kmer(&self, kmer: &str) -> bool {
        if kmer.is_empty() {
            return false;
        }

        // 检查是否只包含 ATCG
        kmer.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G'))
    }

    /// 计算性能指标
    pub fn calculate_performance_metrics(
        &self,
        database_size: u64,
        output_size: u64,
        execution_time_seconds: f64,
    ) -> Result<DumpPerformanceMetrics> {
        if execution_time_seconds <= 0.0 {
            return Err(DumpValidationError::PerformanceBenchmarkFailed(
                "无效的执行时间".to_string()
            ).into());
        }

        let throughput = output_size as f64 / execution_time_seconds;

        Ok(DumpPerformanceMetrics {
            execution_time_seconds,
            database_size_bytes: database_size,
            output_size_bytes: output_size,
            throughput_bytes_per_second: throughput,
            peak_memory_bytes: None, // 需要外部工具测量
        })
    }

    /// 验证性能基准
    pub fn validate_performance_benchmark(
        &self,
        metrics: &DumpPerformanceMetrics,
        min_throughput_mb_per_sec: f64,
    ) -> Result<()> {
        let throughput_mb_per_sec = metrics.throughput_bytes_per_second / (1024.0 * 1024.0);

        if throughput_mb_per_sec < min_throughput_mb_per_sec {
            return Err(DumpValidationError::PerformanceBenchmarkFailed(format!(
                "吞吐量过低: {:.2} MB/s < {:.2} MB/s",
                throughput_mb_per_sec, min_throughput_mb_per_sec
            )).into());
        }

        Ok(())
    }

    /// 生成验证报告摘要
    pub fn generate_summary(&self, results: &[DumpValidationResult]) -> String {
        if results.is_empty() {
            return "没有验证结果".to_string();
        }

        let total_files = results.len();
        let successful_files = results.iter().filter(|r| r.success).count();
        let total_size: u64 = results.iter().map(|r| r.file_size).sum();
        let total_kmers: usize = results.iter().map(|r| r.valid_kmer_lines).sum();

        let mut summary = format!(
            "Dump 验证摘要\n\
            ============\n\
            总文件数: {}\n\
            成功验证: {}\n\
            失败验证: {}\n\
            总输出大小: {} 字节\n\
            总 k-mer 数: {}\n\n",
            total_files,
            successful_files,
            total_files - successful_files,
            total_size,
            total_kmers
        );

        // 添加失败的文件列表
        let failed_results: Vec<_> = results.iter().filter(|r| !r.success).collect();
        if !failed_results.is_empty() {
            summary.push_str("失败的文件:\n");
            for result in failed_results {
                summary.push_str(&format!(
                    "- {} (错误: {})\n",
                    result.output_file,
                    result.error_message.as_deref().unwrap_or("未知错误")
                ));
            }
            summary.push('\n');
        }

        // 添加 k-mer 大小分布
        let mut size_distribution = HashMap::new();
        for result in results {
            for (size, count) in &result.kmer_size_distribution {
                *size_distribution.entry(*size).or_insert(0) += count;
            }
        }

        if !size_distribution.is_empty() {
            summary.push_str("k-mer 大小分布:\n");
            let mut sizes: Vec<_> = size_distribution.iter().collect();
            sizes.sort_by_key(|&(size, _)| size);
            for (size, count) in sizes {
                summary.push_str(&format!("- {}-mers: {}\n", size, count));
            }
        }

        summary
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_validate_text_output() {
        let validator = DumpValidator::new();

        // 创建临时文件
        let mut temp_file = NamedTempFile::new().expect("无法创建临时文件");

        // 写入有效的 k-mer 数据
        writeln!(temp_file, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA 10").unwrap();
        writeln!(temp_file, "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT 5").unwrap();
        writeln!(temp_file, "").unwrap(); // 空行
        writeln!(temp_file, "ATCGATCGATCGATCGATCGATCGATCGATCG").unwrap();

        let result = validator.validate_dump_output(temp_file.path()).unwrap();

        assert!(result.success);
        assert_eq!(result.total_lines, 4);
        assert_eq!(result.valid_kmer_lines, 3);
        assert_eq!(result.empty_lines, 1);
        assert_eq!(result.error_lines, 0);
    }

    #[test]
    fn test_validate_invalid_kmers() {
        let validator = DumpValidator::new();

        let mut temp_file = NamedTempFile::new().expect("无法创建临时文件");

        // 写入无效的 k-mer 数据
        writeln!(temp_file, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA 10").unwrap();
        writeln!(temp_file, "ATCGXATCGATCGATCGATCGATCGATCGATCG").unwrap(); // 包含 X
        writeln!(temp_file, "NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN").unwrap(); // 包含 N

        let result = validator.validate_dump_output(temp_file.path()).unwrap();

        // 默认模式下应该成功（但有错误行）
        assert!(result.success);
        assert_eq!(result.valid_kmer_lines, 1);
        assert_eq!(result.error_lines, 2);
    }

    #[test]
    fn test_strict_mode() {
        let validator = DumpValidator::strict();

        let mut temp_file = NamedTempFile::new().expect("无法创建临时文件");

        // 写入无效的 k-mer 数据
        writeln!(temp_file, "ATCGXATCGATCGATCGATCGATCGATCGATCG").unwrap();

        let result = validator.validate_dump_output(temp_file.path()).unwrap();

        // 严格模式下应该失败
        assert!(!result.success);
        assert!(result.error_message.is_some());
    }

    #[test]
    fn test_kmer_size_validation() {
        let validator = DumpValidator::new().with_kmer_size(31);

        let mut temp_file = NamedTempFile::new().expect("无法创建临时文件");

        // 写入正确大小的 k-mers
        writeln!(temp_file, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA").unwrap();

        let result = validator.validate_dump_output(temp_file.path()).unwrap();
        assert!(result.success);

        // 测试错误大小的 k-mers
        let mut temp_file2 = NamedTempFile::new().expect("无法创建临时文件");
        writeln!(temp_file2, "AAAAAAAAAA").unwrap(); // 10 个 A

        let result2 = validator.validate_dump_output(temp_file2.path()).unwrap();
        assert!(!result2.success);
        assert!(result2.error_message.is_some());
    }
}