use std::env;
use std::process;

mod performance;
mod reporter;
mod validator;
mod command_wrapper;
mod kmer_generator;
mod hamming_generator;

pub mod validators {
    pub mod count_validator;
    pub mod query_validator;
    pub mod dump_validator;
    pub mod fuzzy_validator;
    pub mod stats_validator;
    pub mod merge_validator;
    pub mod help_validator;
}

use crate::reporter::TestReporter;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("用法: rustkmer_test <command> [options]");
        eprintln!("命令:");
        eprintln!("  run           运行所有测试");
        eprintln!("  validate      验证测试结果");
        eprintln!("  report        生成测试报告");
        eprintln!("  monitor       监控运行中的测试");
        process::exit(1);
    }

    let command = &args[1];

    match command.as_str() {
        "run" => {
            // 运行测试逻辑将在各个测试脚本中实现
            println!("运行测试由 shell 脚本处理");
        }
        "validate" => {
            if args.len() < 3 {
                eprintln!("用法: rustkmer_test validate <test_result_file>");
                process::exit(1);
            }
            let validator = validator::TestValidator::new();
            if let Err(e) = validator.validate_results(&args[2]) {
                eprintln!("验证失败: {}", e);
                process::exit(1);
            }
        }
        "report" => {
            let mut reporter = TestReporter::new();
            if let Err(e) = reporter.generate_report() {
                eprintln!("报告生成失败: {}", e);
                process::exit(1);
            }
        }
        "monitor" => {
            // 监控功能
            println!("监控功能待实现");
        }
        _ => {
            eprintln!("未知命令: {}", command);
            process::exit(1);
        }
    }
}