use std::collections::HashMap;
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::Path;

/// Count 命令结果验证器
pub struct CountValidator {
    kmer_size: u32,
}

#[derive(Debug)]
pub struct CountValidationResult {
    pub is_valid: bool,
    pub total_kmers: u64,
    pub unique_kmers: u64,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

impl CountValidator {
    /// 创建新的验证器
    pub fn new(kmer_size: u32) -> Self {
        Self { kmer_size }
    }

    /// 验证 count 操作的结果
    pub fn validate_count_result(
        &self,
        input_file: &str,
        output_db: &str,
    ) -> CountValidationResult {
        let mut result = CountValidationResult {
            is_valid: true,
            total_kmers: 0,
            unique_kmers: 0,
            errors: Vec::new(),
            warnings: Vec::new(),
        };

        // 1. 验证输出数据库文件是否存在
        if !Path::new(output_db).exists() {
            result.is_valid = false;
            result.errors.push("输出数据库文件不存在".to_string());
            return result;
        }

        // 2. 验证输入文件格式
        let input_validation = self.validate_input_file(input_file);
        if !input_validation.is_valid {
            result.is_valid = false;
            result.errors.extend(input_validation.errors);
        }

        // 3. 从输入文件计算预期的 k-mer 数量
        let expected_kmers = self.count_kmers_in_file(input_file);
        if let Ok(expected) = expected_kmers {
            result.total_kmers = expected.total;
            result.unique_kmers = expected.unique;

            // 4. 验证数据库文件大小是否合理
            self.validate_database_size(output_db, expected.total, &mut result);

            // 5. 可以添加更多验证逻辑，如：
            //    - 使用 rustkmer query 验证特定 k-mer
            //    - 检查数据库头部信息
            //    - 验证数据完整性
        } else {
            result.warnings.push("无法从输入文件计算预期的 k-mer 数量".to_string());
        }

        result
    }

    /// 验证输入文件
    fn validate_input_file(&self, file_path: &str) -> ValidationStatus {
        let mut status = ValidationStatus {
            is_valid: true,
            errors: Vec::new(),
        };

        if !Path::new(file_path).exists() {
            status.is_valid = false;
            status.errors.push("输入文件不存在".to_string());
            return status;
        }

        // 验证文件格式
        let file_path_lower = file_path.to_lowercase();
        if !file_path_lower.ends_with(".fasta")
            && !file_path_lower.ends_with(".fa")
            && !file_path_lower.ends_with(".fas")
            && !file_path_lower.ends_with(".fastq")
            && !file_path_lower.ends_with(".fq") {
            status.is_valid = false;
            status.errors.push("文件格式不支持，必须是 FASTA 或 FASTQ".to_string());
        }

        status
    }

    /// 统计文件中的 k-mer
    fn count_kmers_in_file(&self, file_path: &str) -> Result<KmerCounts, Box<dyn std::error::Error>> {
        let file = fs::File::open(file_path)?;
        let reader = BufReader::new(file);

        let mut total_kmers = 0u64;
        let mut kmer_counts: HashMap<String, u64> = HashMap::new();
        let mut current_sequence = String::new();
        let mut is_fastq = false;
        let mut line_number = 0;

        for line in reader.lines() {
            line_number += 1;
            let line = line?;

            if line.is_empty() {
                continue;
            }

            // 检测文件格式
            if line_number == 1 {
                if line.starts_with('@') {
                    is_fastq = true;
                } else if line.starts_with('>') {
                    is_fastq = false;
                } else {
                    return Err("无法识别的文件格式".into());
                }
            }

            if line.starts_with('>') || line.starts_with('@') {
                // 处理前一个序列的 k-mer
                if !current_sequence.is_empty() {
                    self.process_sequence(&current_sequence, &mut total_kmers, &mut kmer_counts);
                    current_sequence.clear();
                }
            } else if !line.starts_with('+') && !is_fastq || (is_fastq && line_number % 4 == 2) {
                // FASTA 的序列行或 FASTQ 的质量行前的序列行
                current_sequence.push_str(&line);
            }
        }

        // 处理最后一个序列
        if !current_sequence.is_empty() {
            self.process_sequence(&current_sequence, &mut total_kmers, &mut kmer_counts);
        }

        Ok(KmerCounts {
            total: total_kmers,
            unique: kmer_counts.len() as u64,
        })
    }

    /// 处理单个序列的 k-mer
    fn process_sequence(
        &self,
        sequence: &str,
        total_kmers: &mut u64,
        kmer_counts: &mut HashMap<String, u64>,
    ) {
        // 过滤非 ACGTN 的字符
        let filtered_sequence: String = sequence
            .chars()
            .filter(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'G' | 'C' | 'N'))
            .collect();

        // 如果序列长度小于 k-mer 大小，跳过
        if filtered_sequence.len() < self.kmer_size as usize {
            return;
        }

        // 滑动窗口提取 k-mer
        for i in 0..=filtered_sequence.len() - self.kmer_size as usize {
            let kmer = &filtered_sequence[i..i + self.kmer_size as usize];

            // 跳过包含 N 的 k-mer
            if !kmer.contains('N') {
                *total_kmers += 1;
                *kmer_counts.entry(kmer.to_uppercase()).or_insert(0) += 1;
            }
        }
    }

    /// 验证数据库文件大小
    fn validate_database_size(&self, db_path: &str, expected_kmers: u64, result: &mut CountValidationResult) {
        if let Ok(metadata) = fs::metadata(db_path) {
            let file_size = metadata.len();

            // 粗略估计：每个 k-mer 大约需要 12 字节（8字节计数 + 4字节k-mer）
            let estimated_min_size = expected_kmers * 12;

            // 加上一些头部开销（约1KB）
            let estimated_size = estimated_min_size + 1024;

            if file_size < estimated_min_size / 2 {
                result.warnings.push(format!(
                    "数据库文件大小可能过小: {} 字节（预期至少 {} 字节）",
                    file_size,
                    estimated_min_size / 2
                ));
            } else if file_size > estimated_size * 3 {
                result.warnings.push(format!(
                    "数据库文件大小可能过大: {} 字节（预期约 {} 字节）",
                    file_size,
                    estimated_size
                ));
            }
        }
    }

    /// 验证并行处理的结果一致性
    pub fn validate_parallel_consistency(
        &self,
        single_thread_db: &str,
        multi_thread_db: &str,
    ) -> ValidationStatus {
        let mut status = ValidationStatus {
            is_valid: true,
            errors: Vec::new(),
        };

        // 这里可以实现更复杂的验证逻辑
        // 例如：使用 rustkmer dump 比较两个数据库的内容

        if !Path::new(single_thread_db).exists() || !Path::new(multi_thread_db).exists() {
            status.is_valid = false;
            status.errors.push("一个或两个数据库文件不存在".to_string());
            return status;
        }

        // 简单的文件大小比较
        if let (Ok(single_meta), Ok(multi_meta)) = (
            fs::metadata(single_thread_db),
            fs::metadata(multi_thread_db),
        ) {
            let size_diff = (single_meta.len() as i64 - multi_meta.len() as i64).abs();
            let size_percent_diff = size_diff as f64 / single_meta.len() as f64;

            if size_percent_diff > 0.01 {
                // 1% 的差异
                status.errors.push(format!(
                    "并行处理结果不一致：文件大小差异 {:.2}%",
                    size_percent_diff * 100.0
                ));
                status.is_valid = false;
            }
        }

        status
    }
}

#[derive(Debug)]
struct ValidationStatus {
    is_valid: bool,
    errors: Vec<String>,
}

#[derive(Debug)]
struct KmerCounts {
    total: u64,
    unique: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_count_validator_creation() {
        let validator = CountValidator::new(31);
        assert_eq!(validator.kmer_size, 31);
    }

    #[test]
    fn test_nonexistent_file() {
        let validator = CountValidator::new(31);
        let result = validator.validate_count_result("/nonexistent/file.fasta", "/tmp/output.rkdb");
        assert!(!result.is_valid);
    }
}