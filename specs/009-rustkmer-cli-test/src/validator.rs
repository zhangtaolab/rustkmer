use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use serde::{Deserialize, Serialize};

pub struct TestValidator {
    validation_rules: ValidationRules,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationRules {
    /// 允许的文件格式
    pub allowed_formats: Vec<String>,
    /// 最小文件大小（字节）
    pub min_file_size: u64,
    /// 最大文件大小（字节）
    pub max_file_size: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ValidationResult {
    pub is_valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
    pub statistics: HashMap<String, u64>,
}

impl Default for ValidationRules {
    fn default() -> Self {
        Self {
            allowed_formats: vec!["fasta".to_string(), "fa".to_string(), "fas".to_string(),
                                  "fastq".to_string(), "fq".to_string()],
            min_file_size: 1,
            max_file_size: 10 * 1024 * 1024 * 1024, // 10GB
        }
    }
}

impl TestValidator {
    pub fn new() -> Self {
        Self {
            validation_rules: ValidationRules::default(),
        }
    }

    /// 验证 FASTA 文件
    pub fn validate_fasta(&self, file_path: &str) -> ValidationResult {
        let mut result = ValidationResult {
            is_valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
            statistics: HashMap::new(),
        };

        let file = match File::open(file_path) {
            Ok(f) => f,
            Err(e) => {
                result.is_valid = false;
                result.errors.push(format!("无法打开文件: {}", e));
                return result;
            }
        };

        let mut sequence_count = 0;
        let mut total_bases = 0;
        let mut current_sequence = String::new();
        let mut has_sequence = false;
        let mut line_number = 0;

        for line in BufReader::new(file).lines() {
            line_number += 1;
            let line = match line {
                Ok(l) => l,
                Err(e) => {
                    result.errors.push(format!("读取第{}行失败: {}", line_number, e));
                    result.is_valid = false;
                    continue;
                }
            };

            if line.is_empty() {
                continue;
            }

            if line.starts_with('>') {
                // 保存前一个序列的统计
                if has_sequence {
                    total_bases += current_sequence.len();
                    current_sequence.clear();
                }

                sequence_count += 1;
                has_sequence = false;

                // 验证序列标题
                if line.len() == 1 {
                    result.warnings.push("第{}行: 序列标题为空".to_string());
                }
            } else {
                has_sequence = true;
                // 验证序列字符
                for (pos, c) in line.chars().enumerate() {
                    match c.to_ascii_uppercase() {
                        'A' | 'T' | 'G' | 'C' | 'N' => {}
                        _ => {
                            result.warnings.push(
                                format!("第{}行第{}个字符: 无效的碱基字符 '{}'",
                                       line_number, pos + 1, c)
                            );
                        }
                    }
                }
                current_sequence.push_str(&line);
            }
        }

        // 保存最后一个序列
        if has_sequence {
            total_bases += current_sequence.len();
        }

        // 更新统计信息
        result.statistics.insert("序列数量".to_string(), sequence_count as u64);
        result.statistics.insert("总碱基数".to_string(), total_bases as u64);

        // 验证结果
        if sequence_count == 0 {
            result.is_valid = false;
            result.errors.push("文件中没有任何序列".to_string());
        }

        if total_bases == 0 {
            result.is_valid = false;
            result.errors.push("文件中没有任何碱基".to_string());
        }

        result
    }

    /// 验证 FASTQ 文件
    pub fn validate_fastq(&self, file_path: &str) -> ValidationResult {
        let mut result = ValidationResult {
            is_valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
            statistics: HashMap::new(),
        };

        let file = match File::open(file_path) {
            Ok(f) => f,
            Err(e) => {
                result.is_valid = false;
                result.errors.push(format!("无法打开文件: {}", e));
                return result;
            }
        };

        let mut sequence_count = 0;
        let mut total_bases = 0;
        let mut line_number = 0;
        let mut line_type = 0; // 0: header, 1: sequence, 2: plus, 3: quality

        for line in BufReader::new(file).lines() {
            line_number += 1;
            let line = match line {
                Ok(l) => l,
                Err(e) => {
                    result.errors.push(format!("读取第{}行失败: {}", line_number, e));
                    result.is_valid = false;
                    continue;
                }
            };

            match line_type {
                0 => {
                    // Header line
                    if !line.starts_with('@') {
                        result.is_valid = false;
                        result.errors.push(format!("第{}行: FASTQ头部应以@开头", line_number));
                    }
                    line_type = 1;
                }
                1 => {
                    // Sequence line
                    let seq_len = line.len();
                    if seq_len == 0 {
                        result.warnings.push(format!("第{}行: 空序列", line_number));
                    } else {
                        // 验证序列字符
                        for (pos, c) in line.chars().enumerate() {
                            match c.to_ascii_uppercase() {
                                'A' | 'T' | 'G' | 'C' | 'N' => {}
                                _ => {
                                    result.warnings.push(
                                        format!("第{}行第{}个字符: 无效的碱基字符 '{}'",
                                               line_number, pos + 1, c)
                                    );
                                }
                            }
                        }
                        total_bases += seq_len;
                    }
                    line_type = 2;
                }
                2 => {
                    // Plus line
                    if !line.starts_with('+') {
                        result.is_valid = false;
                        result.errors.push(format!("第{}行: FASTQ质量行应以+开头", line_number));
                    }
                    line_type = 3;
                }
                3 => {
                    // Quality line
                    let seq_len = line.len();
                    // 在实际验证中，应该检查质量行长度是否与序列行匹配
                    line_type = 0;
                    sequence_count += 1;
                }
            }
        }

        // 检查是否完整读取了最后一个记录
        if line_type != 0 {
            result.is_valid = false;
            result.errors.push("文件末尾有不完整的FASTQ记录".to_string());
        }

        // 更新统计信息
        result.statistics.insert("序列数量".to_string(), sequence_count as u64);
        result.statistics.insert("总碱基数".to_string(), total_bases as u64);

        // 验证结果
        if sequence_count == 0 {
            result.is_valid = false;
            result.errors.push("文件中没有任何序列".to_string());
        }

        result
    }

    /// 验证测试结果文件
    pub fn validate_results(&self, results_file: &str) -> Result<(), Box<dyn std::error::Error>> {
        // 这里可以实现验证测试结果逻辑
        // 例如检查JSON格式、必需字段等
        println!("验证测试结果文件: {}", results_file);
        Ok(())
    }

    /// 验证文件格式和大小
    pub fn validate_file(&self, file_path: &str) -> ValidationResult {
        let path = Path::new(file_path);
        let mut result = ValidationResult {
            is_valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
            statistics: HashMap::new(),
        };

        // 检查文件是否存在
        if !path.exists() {
            result.is_valid = false;
            result.errors.push("文件不存在".to_string());
            return result;
        }

        // 检查文件大小
        if let Ok(metadata) = path.metadata() {
            let file_size = metadata.len();
            result.statistics.insert("文件大小".to_string(), file_size);

            if file_size < self.validation_rules.min_file_size {
                result.is_valid = false;
                result.errors.push(format!(
                    "文件大小 ({}) 小于最小限制 ({})",
                    file_size,
                    self.validation_rules.min_file_size
                ));
            }

            if file_size > self.validation_rules.max_file_size {
                result.warnings.push(format!(
                    "文件大小 ({}) 接近或超过最大限制 ({})",
                    file_size,
                    self.validation_rules.max_file_size
                ));
            }
        }

        // 检查文件扩展名
        if let Some(extension) = path.extension() {
            let ext_str = extension.to_string_lossy().to_lowercase();
            if !self.validation_rules.allowed_formats.contains(&ext_str) {
                result.is_valid = false;
                result.errors.push(format!(
                    "不支持的文件格式: {}",
                    ext_str
                ));
            }
        } else {
            result.is_valid = false;
            result.errors.push("文件没有扩展名".to_string());
        }

        result
    }

    /// 验证数据库文件
    pub fn validate_database(&self, db_path: &str) -> ValidationResult {
        let mut result = self.validate_file(db_path);

        // 检查 .rkdb 扩展名
        if !db_path.ends_with(".rkdb") {
            result.is_valid = false;
            result.errors.push("数据库文件应以 .rkdb 结尾".to_string());
        }

        // 可以添加更多数据库特定的验证逻辑
        // 例如检查文件头、魔数等

        result
    }

    /// 比较两个文件是否相同
    pub fn compare_files(&self, file1: &str, file2: &str) -> bool {
        use std::io::Read;

        let mut f1 = match File::open(file1) {
            Ok(f) => f,
            Err(_) => return false,
        };

        let mut f2 = match File::open(file2) {
            Ok(f) => f,
            Err(_) => return false,
        };

        let mut buf1 = [0; 8192];
        let mut buf2 = [0; 8192];

        loop {
            let n1 = match f1.read(&mut buf1) {
                Ok(0) => break,
                Ok(n) => n,
                Err(_) => return false,
            };

            let n2 = match f2.read(&mut buf2) {
                Ok(0) => break,
                Ok(n) => n,
                Err(_) => return false,
            };

            if n1 != n2 || buf1[..n1] != buf2[..n2] {
                return false;
            }
        }

        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validator_creation() {
        let validator = TestValidator::new();
        assert_eq!(validator.validation_rules.allowed_formats.len(), 6);
    }

    #[test]
    fn test_nonexistent_file() {
        let validator = TestValidator::new();
        let result = validator.validate_file("/nonexistent/file.fasta");
        assert!(!result.is_valid);
        assert!(result.errors.contains(&"文件不存在".to_string()));
    }

    #[test]
    fn test_file_comparison() {
        let validator = TestValidator::new();

        // 创建临时测试文件
        use std::fs;
        use std::env;

        let temp_dir = env::temp_dir();
        let file1_path = temp_dir.join("test1.txt");
        let file2_path = temp_dir.join("test2.txt");
        let file3_path = temp_dir.join("test3.txt");

        fs::write(&file1_path, "Hello World").unwrap();
        fs::write(&file2_path, "Hello World").unwrap();
        fs::write(&file3_path, "Hello Rust").unwrap();

        assert!(validator.compare_files(
            file1_path.to_str().unwrap(),
            file2_path.to_str().unwrap()
        ));

        assert!(!validator.compare_files(
            file1_path.to_str().unwrap(),
            file3_path.to_str().unwrap()
        ));

        // 清理
        let _ = fs::remove_file(&file1_path);
        let _ = fs::remove_file(&file2_path);
        let _ = fs::remove_file(&file3_path);
    }
}