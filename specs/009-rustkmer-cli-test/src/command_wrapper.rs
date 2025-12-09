use std::process::{Command, Stdio};
use std::path::Path;
use crate::performance::PerformanceMonitor;
use crate::performance::PerformanceMetrics;

pub struct CommandWrapper {
    performance_monitor: PerformanceMonitor,
}

#[derive(Debug, Clone)]
pub struct CommandResult {
    pub exit_code: i32,
    pub stdout: String,
    pub stderr: String,
    pub execution_time: f64,
    pub success: bool,
}

#[derive(Debug, Clone)]
pub struct RustKmerCommand {
    pub command: String,
    pub args: Vec<String>,
    pub working_dir: Option<String>,
    pub timeout: Option<u64>, // 超时时间（秒）
}

impl RustKmerCommand {
    pub fn count(input_file: &str, output_file: &str, k: u32) -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec![
                "count".to_string(),
                "-k".to_string(),
                k.to_string(),
                "-o".to_string(),
                output_file.to_string(),
                input_file.to_string(),
            ],
            working_dir: None,
            timeout: Some(600), // 10分钟
        }
    }

    pub fn count_with_threads(
        input_file: &str,
        output_file: &str,
        k: u32,
        threads: u32,
    ) -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec![
                "count".to_string(),
                "-k".to_string(),
                k.to_string(),
                "-t".to_string(),
                threads.to_string(),
                "-o".to_string(),
                output_file.to_string(),
                input_file.to_string(),
            ],
            working_dir: None,
            timeout: Some(600),
        }
    }

    pub fn query(database: &str, kmer: &str) -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec![
                "query".to_string(),
                database.to_string(),
                kmer.to_string(),
            ],
            working_dir: None,
            timeout: Some(30),
        }
    }

    pub fn query_with_format(database: &str, kmer: &str, format: &str) -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec![
                "query".to_string(),
                "--format".to_string(),
                format.to_string(),
                database.to_string(),
                kmer.to_string(),
            ],
            working_dir: None,
            timeout: Some(30),
        }
    }

    pub fn dump(database: &str, output: &str) -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec![
                "dump".to_string(),
                database.to_string(),
                "-o".to_string(),
                output.to_string(),
            ],
            working_dir: None,
            timeout: Some(120),
        }
    }

    pub fn fuzzy_query(database: &str, kmer: &str, distance: u32) -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec![
                "fuzzy-query".to_string(),
                "-d".to_string(),
                distance.to_string(),
                database.to_string(),
                kmer.to_string(),
            ],
            working_dir: None,
            timeout: Some(60),
        }
    }

    pub fn stats(database: &str) -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec![
                "stats".to_string(),
                database.to_string(),
            ],
            working_dir: None,
            timeout: Some(10),
        }
    }

    pub fn merge(databases: &[String], output: &str) -> Self {
        let mut args = vec!["merge".to_string()];
        for db in databases {
            args.push(db.clone());
        }
        args.push("-o".to_string());
        args.push(output.to_string());

        Self {
            command: "rustkmer".to_string(),
            args,
            working_dir: None,
            timeout: Some(300),
        }
    }

    pub fn help() -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec!["--help".to_string()],
            working_dir: None,
            timeout: Some(5),
        }
    }

    pub fn help_command(command: &str) -> Self {
        Self {
            command: "rustkmer".to_string(),
            args: vec![command.to_string(), "--help".to_string()],
            working_dir: None,
            timeout: Some(5),
        }
    }
}

impl CommandWrapper {
    pub fn new() -> Self {
        Self {
            performance_monitor: PerformanceMonitor::new(),
        }
    }

    /// 执行命令并返回结果
    pub fn execute(&mut self, cmd: &RustKmerCommand) -> Result<CommandResult, Box<dyn std::error::Error>> {
        println!("执行命令: {} {}", cmd.command, cmd.args.join(" "));

        // 启动性能监控
        self.performance_monitor.start_monitoring();

        // 构建命令
        let mut command = Command::new(&cmd.command);
        command.args(&cmd.args);

        // 设置工作目录
        if let Some(ref dir) = cmd.working_dir {
            command.current_dir(dir);
        }

        // 执行命令
        let output = command.output()?;

        // 获取执行时间
        let execution_time = self.performance_monitor
            .start_time
            .unwrap_or_else(|| std::time::Instant::now())
            .elapsed()
            .as_secs_f64();

        let success = output.status.success();
        let exit_code = output.status.code().unwrap_or(1);

        let result = CommandResult {
            exit_code,
            stdout: String::from_utf8_lossy(&output.stdout).to_string(),
            stderr: String::from_utf8_lossy(&output.stderr).to_string(),
            execution_time,
            success,
        };

        // 记录结果
        if !result.success {
            eprintln!("命令执行失败:");
            eprintln!("  退出码: {}", result.exit_code);
            eprintln!("  标准错误: {}", result.stderr);
        }

        Ok(result)
    }

    /// 执行命令并收集性能指标
    pub fn execute_with_metrics(
        &mut self,
        cmd: &RustKmerCommand,
    ) -> Result<(CommandResult, PerformanceMetrics), Box<dyn std::error::Error>> {
        println!("执行命令（带性能监控）: {} {}", cmd.command, cmd.args.join(" "));

        // 使用 /usr/bin/time 收集性能指标
        let mut time_cmd = Command::new("/usr/bin/time");
        time_cmd.args(&["-v", "-p"]);
        time_cmd.arg(&cmd.command);
        time_cmd.args(&cmd.args);

        // 设置工作目录
        if let Some(ref dir) = cmd.working_dir {
            time_cmd.current_dir(dir);
        }

        // 执行命令
        let output = time_cmd.output()?;

        let success = output.status.success();
        let exit_code = output.status.code().unwrap_or(1);

        // 解析性能指标
        let metrics = self.performance_monitor.parse_time_output(
            &String::from_utf8_lossy(&output.stderr)
        )?;

        let command_result = CommandResult {
            exit_code,
            stdout: String::from_utf8_lossy(&output.stdout).to_string(),
            stderr: String::from_utf8_lossy(&output.stderr).to_string(),
            execution_time: metrics.execution_time,
            success,
        };

        Ok((command_result, metrics))
    }

    /// 批量执行查询命令
    pub fn batch_query(
        &mut self,
        database: &str,
        kmers: &[String],
    ) -> Result<Vec<CommandResult>, Box<dyn std::error::Error>> {
        let mut results = Vec::new();

        println!("批量查询 {} 个 k-mers...", kmers.len());

        for (i, kmer) in kmers.iter().enumerate() {
            let cmd = RustKmerCommand::query(database, kmer);
            let result = self.execute(&cmd)?;

            results.push(result);

            // 显示进度
            if (i + 1) % 100 == 0 || i + 1 == kmers.len() {
                println!("  已处理 {}/{} 个查询", i + 1, kmers.len());
            }
        }

        Ok(results)
    }

    /// 验证输出文件是否创建
    pub fn verify_output_files(&self, expected_files: &[String]) -> bool {
        for file in expected_files {
            if !Path::new(file).exists() {
                eprintln!("输出文件不存在: {}", file);
                return false;
            }
        }
        true
    }

    /// 获取文件大小
    pub fn get_file_size(&self, file_path: &str) -> Result<u64, Box<dyn std::error::Error>> {
        let metadata = std::fs::metadata(file_path)?;
        Ok(metadata.len())
    }

    /// 清理临时文件
    pub fn cleanup_files(&self, files: &[String]) {
        for file in files {
            if Path::new(file).exists() {
                if let Err(e) = std::fs::remove_file(file) {
                    eprintln!("警告: 无法删除文件 {}: {}", file, e);
                }
            }
        }
    }

    /// 检查命令是否存在
    pub fn check_command_exists(&self, command: &str) -> bool {
        Command::new(command)
            .arg("--version")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .is_ok()
    }

    /// 获取命令版本信息
    pub fn get_command_version(&self, command: &str) -> Result<String, Box<dyn std::error::Error>> {
        let output = Command::new(command).arg("--version").output()?;
        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
        } else {
            Err(format!("无法获取 {} 版本信息", command).into())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_command_wrapper_creation() {
        let wrapper = CommandWrapper::new();
        // 测试创建成功
    }

    #[test]
    fn test_rustkmer_command_creation() {
        let cmd = RustKmerCommand::count("test.fasta", "output.rkdb", 31);
        assert_eq!(cmd.command, "rustkmer");
        assert_eq!(cmd.args[0], "count");
        assert_eq!(cmd.args[2], "31");
        assert_eq!(cmd.timeout, Some(600));
    }

    #[test]
    fn test_count_with_threads() {
        let cmd = RustKmerCommand::count_with_threads("test.fasta", "output.rkdb", 31, 4);
        assert!(cmd.args.contains(&"-t".to_string()));
        assert!(cmd.args.contains(&"4".to_string()));
    }

    #[test]
    fn test_query_command() {
        let cmd = RustKmerCommand::query("test.rkdb", "ATCG");
        assert_eq!(cmd.args[0], "query");
        assert_eq!(cmd.args[2], "ATCG");
        assert_eq!(cmd.timeout, Some(30));
    }

    #[test]
    fn test_fuzzy_query() {
        let cmd = RustKmerCommand::fuzzy_query("test.rkdb", "ATCG", 2);
        assert_eq!(cmd.args[0], "fuzzy-query");
        assert!(cmd.args.contains(&"-2".to_string()));
    }

    #[test]
    fn test_merge_command() {
        let databases = vec![
            "db1.rkdb".to_string(),
            "db2.rkdb".to_string(),
            "db3.rkdb".to_string(),
        ];
        let cmd = RustKmerCommand::merge(&databases, "merged.rkdb");
        assert_eq!(cmd.args[0], "merge");
        assert_eq!(cmd.args[1], "db1.rkdb");
        assert_eq!(cmd.args[2], "db2.rkdb");
        assert_eq!(cmd.args[3], "db3.rkdb");
    }
}