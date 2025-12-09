use std::collections::HashMap;
use std::fs;
use std::path::Path;
use chrono::{DateTime, Local};
use serde::{Deserialize, Serialize};
use crate::performance::PerformanceMetrics;

#[derive(Debug, Serialize, Deserialize)]
pub struct TestResult {
    pub test_id: String,
    pub scenario_id: String,
    pub dataset_path: String,
    pub status: TestStatus,
    pub performance_metrics: Option<PerformanceMetrics>,
    pub output_files: Vec<String>,
    pub error_message: Option<String>,
    pub validation_results: ValidationResults,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum TestStatus {
    PASSED,
    FAILED,
    ERROR,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ValidationResults {
    pub 功能正确性: bool,
    pub 输出格式正确: bool,
    pub 数据完整性: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestReport {
    pub report_id: String,
    pub generation_time: DateTime<Local>,
    pub rustkmer_version: String,
    pub system_environment: SystemEnvironment,
    pub test_results_summary: TestResultsSummary,
    pub performance_summary: PerformanceSummary,
    pub discovered_issues: Vec<Issue>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SystemEnvironment {
    pub 操作系统: String,
    pub CPU信息: String,
    pub 内存总量: String,
    pub Rust版本: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestResultsSummary {
    pub 总测试数: i32,
    pub 通过数: i32,
    pub 失败数: i32,
    pub 错误数: i32,
    pub 成功率: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PerformanceSummary {
    pub 平均执行时间: f64,
    pub 最大内存使用: i64,
    pub 并行效率: Vec<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Issue {
    pub issue_id: String,
    pub severity: IssueSeverity,
    pub issue_type: IssueType,
    pub description: String,
    pub reproduction_steps: Vec<String>,
    pub expected_behavior: String,
    pub actual_behavior: String,
    pub suggested_fix: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum IssueSeverity {
    CRITICAL,
    HIGH,
    MEDIUM,
    LOW,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum IssueType {
    BUG,
    PERFORMANCE,
    DOCUMENTATION,
    FEATURE,
}

pub struct TestReporter {
    test_results: Vec<TestResult>,
    issues: Vec<Issue>,
}

impl TestReporter {
    pub fn new() -> Self {
        Self {
            test_results: Vec::new(),
            issues: Vec::new(),
        }
    }

    /// 添加测试结果
    pub fn add_test_result(&mut self, result: TestResult) {
        self.test_results.push(result);
    }

    /// 添加问题记录
    pub fn add_issue(&mut self, issue: Issue) {
        self.issues.push(issue);
    }

    /// 生成测试报告
    pub fn generate_report(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let report = self.create_report()?;

        // 保存 JSON 格式
        let json_path = "/Users/forrest/Temp/demodata/rustkmer_cli_test/reports/test_report_latest.json";
        let json = serde_json::to_string_pretty(&report)?;
        fs::write(json_path, json)?;

        // 生成 Markdown 格式
        let markdown_path = format!(
            "/Users/forrest/Temp/demodata/rustkmer_cli_test/reports/test_report_{}.md",
            report.generation_time.format("%Y%m%d_%H%M%S")
        );
        let markdown = self.generate_markdown_report(&report)?;
        fs::write(markdown_path, markdown)?;

        println!("测试报告已生成");
        Ok(())
    }

    /// 创建报告对象
    fn create_report(&self) -> Result<TestReport, Box<dyn std::error::Error>> {
        let rustkmer_version = self.get_rustkmer_version()?;
        let system_env = self.get_system_environment()?;
        let summary = self.calculate_summary();
        let perf_summary = self.calculate_performance_summary();

        Ok(TestReport {
            report_id: format!("report_{}", Local::now().timestamp()),
            generation_time: Local::now(),
            rustkmer_version,
            system_environment: system_env,
            test_results_summary: summary,
            performance_summary: perf_summary,
            discovered_issues: self.issues.clone(),
        })
    }

    /// 获取 rustkmer 版本
    fn get_rustkmer_version(&self) -> Result<String, Box<dyn std::error::Error>> {
        use std::process::Command;

        let output = Command::new("rustkmer")
            .arg("--version")
            .output()?;

        if output.status.success() {
            Ok(String::from_utf8(output.stdout)?.trim().to_string())
        } else {
            Ok("unknown".to_string())
        }
    }

    /// 获取系统环境信息
    fn get_system_environment(&self) -> Result<SystemEnvironment, Box<dyn std::error::Error>> {
        use std::process::Command;

        // 操作系统
        let os_output = Command::new("uname").arg("-s").output()?;
        let os_name = String::from_utf8(os_output.stdout)?.trim().to_string();

        // CPU 信息
        let cpu_info = if cfg!(target_os = "macos") {
            let output = Command::new("sysctl")
                .args(&["-n", "machdep.cpu.brand_string"])
                .output()?;
            String::from_utf8(output.stdout)?.trim().to_string()
        } else {
            "Unknown CPU".to_string()
        };

        // 内存总量
        let memory_info = if cfg!(target_os = "macos") {
            let output = Command::new("sysctl")
                .args(&["-n", "hw.memsize"])
                .output()?;
            let memsize = String::from_utf8(output.stdout)?.trim().parse::<u64>()?;
            format!("{}GB", memsize / 1024 / 1024 / 1024)
        } else {
            "Unknown".to_string()
        };

        // Rust 版本
        let rust_version = Command::new("rustc")
            .arg("--version")
            .output()
            .map(|output| String::from_utf8(output.stdout).unwrap_or_default())
            .unwrap_or_else(|_| "unknown".to_string())
            .trim()
            .to_string();

        Ok(SystemEnvironment {
            操作系统: os_name,
            CPU信息: cpu_info,
            内存总量: memory_info,
            Rust版本: rust_version,
        })
    }

    /// 计算测试结果摘要
    fn calculate_summary(&self) -> TestResultsSummary {
        let total = self.test_results.len() as i32;
        let mut passed = 0;
        let mut failed = 0;
        let mut error = 0;

        for result in &self.test_results {
            match result.status {
                TestStatus::PASSED => passed += 1,
                TestStatus::FAILED => failed += 1,
                TestStatus::ERROR => error += 1,
            }
        }

        let success_rate = if total > 0 {
            (passed as f64 / total as f64) * 100.0
        } else {
            0.0
        };

        TestResultsSummary {
            总测试数: total,
            通过数: passed,
            失败数: failed,
            错误数: error,
            成功率: success_rate,
        }
    }

    /// 计算性能摘要
    fn calculate_performance_summary(&self) -> PerformanceSummary {
        let mut execution_times = Vec::new();
        let mut memory_usage = Vec::new();

        for result in &self.test_results {
            if let Some(ref metrics) = result.performance_metrics {
                execution_times.push(metrics.execution_time);
                memory_usage.push(metrics.max_rss_kb);
            }
        }

        let avg_execution_time = if !execution_times.is_empty() {
            execution_times.iter().sum::<f64>() / execution_times.len() as f64
        } else {
            0.0
        };

        let max_memory = if !memory_usage.is_empty() {
            *memory_usage.iter().max().unwrap()
        } else {
            0
        };

        PerformanceSummary {
            平均执行时间: avg_execution_time,
            最大内存使用: max_memory,
            并行效率: vec![], // 需要根据实际测试结果填充
        }
    }

    /// 生成 Markdown 格式报告
    fn generate_markdown_report(&self, report: &TestReport) -> Result<String, Box<dyn std::error::Error>> {
        let mut markdown = String::new();

        // 标题
        markdown.push_str("# RustKmer CLI 测试报告\n\n");

        // 基本信息
        markdown.push_str(&format!(
            "**生成时间**: {}\n",
            report.generation_time.format("%Y-%m-%d %H:%M:%S")
        ));
        markdown.push_str(&format!(
            "**测试分支**: 009-rustkmer-cli-test\n"
        ));
        markdown.push_str(&format!(
            "**RustKmer 版本**: {}\n\n",
            report.rustkmer_version
        ));

        // 测试概述
        markdown.push_str("## 测试概述\n\n");
        markdown.push_str("本报告包含 rustkmer CLI 所有命令的测试结果。\n\n");

        // 测试环境
        markdown.push_str("## 测试环境\n\n");
        markdown.push_str("- **操作系统**: ");
        markdown.push_str(&report.system_environment.操作系统);
        markdown.push_str("\n");
        markdown.push_str("- **CPU 信息**: ");
        markdown.push_str(&report.system_environment.CPU信息);
        markdown.push_str("\n");
        markdown.push_str("- **内存总量**: ");
        markdown.push_str(&report.system_environment.内存总量);
        markdown.push_str("\n");
        markdown.push_str("- **Rust 版本**: ");
        markdown.push_str(&report.system_environment.Rust版本);
        markdown.push_str("\n\n");

        // 测试结果汇总
        markdown.push_str("## 测试结果汇总\n\n");
        markdown.push_str("| 指标 | 数值 |\n");
        markdown.push_str("|------|------|\n");
        markdown.push_str(&format!("| 总测试数 | {} |\n", report.test_results_summary.总测试数));
        markdown.push_str(&format!("| 通过数 | {} |\n", report.test_results_summary.通过数));
        markdown.push_str(&format!("| 失败数 | {} |\n", report.test_results_summary.失败数));
        markdown.push_str(&format!("| 错误数 | {} |\n", report.test_results_summary.错误数));
        markdown.push_str(&format!("| 成功率 | {:.1}% |\n\n", report.test_results_summary.成功率));

        // 性能摘要
        markdown.push_str("## 性能摘要\n\n");
        markdown.push_str("- **平均执行时间**: ");
        markdown.push_str(&format!("{:.2} 秒\n", report.performance_summary.平均执行时间));
        markdown.push_str("- **最大内存使用**: ");
        markdown.push_str(&format!("{} KB\n\n", report.performance_summary.最大内存使用));

        // 详细测试结果
        markdown.push_str("## 详细测试结果\n\n");
        for (i, result) in self.test_results.iter().enumerate() {
            markdown.push_str(&format!("### {}. {}\n\n", i + 1, result.test_id));
            markdown.push_str(&format!("- **场景**: {}\n", result.scenario_id));
            markdown.push_str(&format!("- **数据集**: {}\n", result.dataset_path));
            markdown.push_str(&format!("- **状态**: {:?}\n", result.status));

            if let Some(ref metrics) = result.performance_metrics {
                markdown.push_str("- **执行时间**: {:.2} 秒\n", metrics.execution_time);
                markdown.push_str("- **内存使用**: {} KB\n", metrics.max_rss_kb);
            }

            if let Some(ref error) = result.error_message {
                markdown.push_str(&format!("- **错误**: {}\n", error));
            }

            markdown.push_str("\n");
        }

        // 发现的问题
        if !report.discovered_issues.is_empty() {
            markdown.push_str("## 发现的问题\n\n");
            for (i, issue) in report.discovered_issues.iter().enumerate() {
                markdown.push_str(&format!("### {}. {}\n\n", i + 1, issue.description));
                markdown.push_str(&format!("- **严重程度**: {:?}\n", issue.severity));
                markdown.push_str(&format!("- **类型**: {:?}\n", issue.issue_type));

                if !issue.reproduction_steps.is_empty() {
                    markdown.push_str("- **重现步骤**:\n");
                    for step in &issue.reproduction_steps {
                        markdown.push_str(&format!("  1. {}\n", step));
                    }
                }

                markdown.push_str(&format!("- **期望行为**: {}\n", issue.expected_behavior));
                markdown.push_str(&format!("- **实际行为**: {}\n", issue.actual_behavior));

                if let Some(ref fix) = issue.suggested_fix {
                    markdown.push_str(&format!("- **建议修复**: {}\n", fix));
                }

                markdown.push_str("\n");
            }
        }

        Ok(markdown)
    }
}