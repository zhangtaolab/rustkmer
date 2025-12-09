use std::collections::HashMap;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::{BufRead, BufReader};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    /// 执行时间（秒）
    pub execution_time: f64,
    /// 用户CPU时间（秒）
    pub user_cpu_time: f64,
    /// 系统CPU时间（秒）
    pub system_cpu_time: f64,
    /// 最大RSS内存（KB）
    pub max_rss_kb: i64,
    /// 平均RSS内存（KB）
    pub avg_rss_kb: i64,
    /// 上下文切换次数
    pub context_switches: i64,
    /// 页面错误次数
    pub page_faults: i64,
    /// 磁盘读取量（字节）
    pub disk_read_bytes: i64,
    /// 磁盘写入量（字节）
    pub disk_write_bytes: i64,
    /// CPU使用率（百分比）
    pub cpu_usage_percent: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TimeSeriesMetrics {
    /// 时间戳（秒）
    pub timestamp: f64,
    /// 内存使用量（KB）
    pub memory_kb: i64,
    /// CPU使用率（百分比）
    pub cpu_percent: f64,
}

pub struct PerformanceMonitor {
    start_time: Option<Instant>,
    metrics_history: Vec<TimeSeriesMetrics>,
}

impl PerformanceMonitor {
    pub fn new() -> Self {
        Self {
            start_time: None,
            metrics_history: Vec::new(),
        }
    }

    /// 开始监控
    pub fn start_monitoring(&mut self) {
        self.start_time = Some(Instant::now());
        self.metrics_history.clear();
    }

    /// 采样当前性能指标
    pub fn sample(&mut self, pid: u32) -> Result<(), Box<dyn std::error::Error>> {
        let timestamp = self.start_time
            .unwrap_or_else(|| Instant::now())
            .elapsed()
            .as_secs_f64();

        // 获取内存使用量
        let memory_kb = self.get_memory_usage(pid)?;

        // 获取CPU使用率（简化实现）
        let cpu_percent = self.get_cpu_usage(pid)?;

        self.metrics_history.push(TimeSeriesMetrics {
            timestamp,
            memory_kb,
            cpu_percent,
        });

        Ok(())
    }

    /// 获取进程内存使用量（KB）
    fn get_memory_usage(&self, pid: u32) -> Result<i64, Box<dyn std::error::Error>> {
        #[cfg(unix)]
        {
            use std::fs;
            let status_path = format!("/proc/{}/status", pid);

            if let Ok(file) = File::open(&status_path) {
                for line in BufReader::new(file).lines() {
                    if let Ok(line) = line {
                        if line.starts_with("VmRSS:") {
                            let parts: Vec<&str> = line.split_whitespace().collect();
                            if parts.len() >= 2 {
                                return Ok(parts[1].parse::<i64>()?);
                            }
                        }
                    }
                }
            }

            // macOS 使用 ps 命令
            let output = Command::new("ps")
                .args(&["-o", "rss=", "-p", &pid.to_string()])
                .output()?;

            let rss_str = String::from_utf8(output.stdout)?.trim().to_string();
            if !rss_str.is_empty() {
                return Ok(rss_str.parse::<i64>()?);
            }
        }

        Ok(0)
    }

    /// 获取CPU使用率（简化实现）
    fn get_cpu_usage(&self, pid: u32) -> Result<f64, Box<dyn std::error::Error>> {
        #[cfg(unix)]
        {
            let output = Command::new("ps")
                .args(&["-o", "%cpu=", "-p", &pid.to_string()])
                .output()?;

            let cpu_str = String::from_utf8(output.stdout)?.trim().to_string();
            if !cpu_str.is_empty() {
                return Ok(cpu_str.parse::<f64>()?);
            }
        }

        Ok(0.0)
    }

    /// 运行命令并收集性能指标
    pub fn run_command_with_metrics(
        &mut self,
        command: &str,
        args: &[&str],
    ) -> Result<(String, PerformanceMetrics), Box<dyn std::error::Error>> {
        self.start_monitoring();

        // 使用 /usr/bin/time 获取详细的性能指标
        let time_output = Command::new("/usr/bin/time")
            .args(&[
                "-v",  // 详细输出
                "-p",  # 可移植格式
            ])
            .arg(command)
            .args(args)
            .output()?;

        let output = String::from_utf8(time_output.stdout)?;
        let stderr = String::from_utf8(time_output.stderr)?;

        // 解析 time 命令的输出
        let metrics = self.parse_time_output(&stderr)?;

        Ok((output, metrics))
    }

    /// 解析 /usr/bin/time 的输出
    fn parse_time_output(&self, time_output: &str) -> Result<PerformanceMetrics, Box<dyn std::error::Error>> {
        let mut metrics = PerformanceMetrics {
            execution_time: 0.0,
            user_cpu_time: 0.0,
            system_cpu_time: 0.0,
            max_rss_kb: 0,
            avg_rss_kb: 0,
            context_switches: 0,
            page_faults: 0,
            disk_read_bytes: 0,
            disk_write_bytes: 0,
            cpu_usage_percent: 0.0,
        };

        // 解析 real time
        for line in time_output.lines() {
            if line.contains("Elapsed (wall clock) time") {
                if let Some(time_str) = line.split(':').nth(1) {
                    let time_str = time_str.trim();
                    let parts: Vec<&str> = time_str.split(':').collect();
                    if parts.len() == 2 {
                        let minutes = parts[0].parse::<f64>()?;
                        let seconds = parts[1].trim().parse::<f64>()?;
                        metrics.execution_time = minutes * 60.0 + seconds;
                    } else {
                        metrics.execution_time = time_str.parse::<f64>()?;
                    }
                }
            } else if line.contains("User time") {
                if let Some(time_str) = line.split(':').nth(1) {
                    metrics.user_cpu_time = time_str.trim().parse::<f64>()?;
                }
            } else if line.contains("System time") {
                if let Some(time_str) = line.split(':').nth(1) {
                    metrics.system_cpu_time = time_str.trim().parse::<f64>()?;
                }
            } else if line.contains("Maximum resident set size") {
                if let Some(size_str) = line.split(':').nth(1) {
                    metrics.max_rss_kb = size_str.trim().parse::<i64>()?;
                }
            } else if line.contains("Major (requiring I/O) page faults") {
                if let Some(faults_str) = line.split(':').nth(1) {
                    metrics.page_faults = faults_str.trim().parse::<i64>()?;
                }
            } else if line.contains("Voluntary context switches") {
                if let Some(switches_str) = line.split(':').nth(1) {
                    metrics.context_switches = switches_str.trim().parse::<i64>()?;
                }
            }
        }

        // 计算 CPU 使用率
        if metrics.execution_time > 0.0 {
            metrics.cpu_usage_percent =
                ((metrics.user_cpu_time + metrics.system_cpu_time) / metrics.execution_time) * 100.0;
        }

        // 计算平均内存使用
        if !self.metrics_history.is_empty() {
            let total: i64 = self.metrics_history.iter().map(|m| m.memory_kb).sum();
            metrics.avg_rss_kb = total / self.metrics_history.len() as i64;
        }

        Ok(metrics)
    }

    /// 获取性能指标历史
    pub fn get_metrics_history(&self) -> &[TimeSeriesMetrics] {
        &self.metrics_history
    }

    /// 保存性能指标到文件
    pub fn save_metrics_to_file(
        &metrics: &PerformanceMetrics,
        file_path: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let json = serde_json::to_string_pretty(metrics)?;
        std::fs::write(file_path, json)?;
        Ok(())
    }

    /// 从文件加载性能指标
    pub fn load_metrics_from_file(
        file_path: &str,
    ) -> Result<PerformanceMetrics, Box<dyn std::error::Error>> {
        let json = std::fs::read_to_string(file_path)?;
        let metrics: PerformanceMetrics = serde_json::from_str(&json)?;
        Ok(metrics)
    }

    /// 生成性能摘要报告
    pub fn generate_performance_summary(
        metrics_list: &[PerformanceMetrics],
    ) -> HashMap<String, f64> {
        let mut summary = HashMap::new();

        if !metrics_list.is_empty() {
            let total_time: f64 = metrics_list.iter().map(|m| m.execution_time).sum();
            let avg_time = total_time / metrics_list.len() as f64;
            let max_memory: i64 = metrics_list.iter().map(|m| m.max_rss_kb).max().unwrap_or(0);
            let avg_memory: i64 = metrics_list.iter().map(|m| m.avg_rss_kb).sum() / metrics_list.len() as i64;

            summary.insert("平均执行时间".to_string(), avg_time);
            summary.insert("最大内存使用".to_string(), max_memory as f64);
            summary.insert("平均内存使用".to_string(), avg_memory as f64);
        }

        summary
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_performance_monitor_creation() {
        let monitor = PerformanceMonitor::new();
        assert!(monitor.metrics_history.is_empty());
        assert!(monitor.start_time.is_none());
    }

    #[test]
    fn test_metrics_serialization() {
        let metrics = PerformanceMetrics {
            execution_time: 10.5,
            user_cpu_time: 8.2,
            system_cpu_time: 2.3,
            max_rss_kb: 1024000,
            avg_rss_kb: 512000,
            context_switches: 1000,
            page_faults: 50,
            disk_read_bytes: 1048576,
            disk_write_bytes: 524288,
            cpu_usage_percent: 85.0,
        };

        let json = serde_json::to_string(&metrics).unwrap();
        let deserialized: PerformanceMetrics = serde_json::from_str(&json).unwrap();

        assert_eq!(metrics.execution_time, deserialized.execution_time);
        assert_eq!(metrics.max_rss_kb, deserialized.max_rss_kb);
    }
}