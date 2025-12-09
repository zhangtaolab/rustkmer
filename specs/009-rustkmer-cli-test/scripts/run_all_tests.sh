#!/bin/bash

# RustKmer CLI 全面测试脚本
# 运行所有 rustkmer CLI 命令的测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
TEST_DIR="/Users/forrest/Temp/demodata/rustkmer_cli_test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$TEST_DIR/logs"
REPORT_DIR="$TEST_DIR/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/test_run_$TIMESTAMP.log"

# 创建必要的目录
mkdir -p "$LOG_DIR" "$REPORT_DIR"

# 日志函数
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

# 检查 rustkmer 是否安装
check_rustkmer() {
    log "检查 rustkmer 是否安装..."
    if ! command -v rustkmer &> /dev/null; then
        log_error "rustkmer 未找到，请先安装 rustkmer"
        exit 1
    fi

    RUSTKMER_VERSION=$(rustkmer --version 2>&1 || echo "unknown")
    log_success "rustkmer 版本: $RUSTKMER_VERSION"
}

# 检查测试数据目录
check_test_data() {
    log "检查测试数据目录..."
    if [ ! -d "/Users/forrest/Temp/demodata" ]; then
        log_error "测试数据目录不存在: /Users/forrest/Temp/demodata"
        exit 1
    fi

    # 统计 FASTA/FASTQ 文件
    FASTA_COUNT=$(find /Users/forrest/Temp/demodata -type f \( -name "*.fasta" -o -name "*.fa" -o -name "*.fas" \) 2>/dev/null | wc -l)
    FASTQ_COUNT=$(find /Users/forrest/Temp/demodata -type f \( -name "*.fastq" -o -name "*.fq" \) 2>/dev/null | wc -l)

    log_info "找到 $FASTA_COUNT 个 FASTA 文件，$FASTQ_COUNT 个 FASTQ 文件"

    if [ $FASTA_COUNT -eq 0 ] && [ $FASTQ_COUNT -eq 0 ]; then
        log_error "没有找到 FASTA/FASTQ 文件用于测试"
        exit 1
    fi
}

# 运行单个测试脚本
run_test_script() {
    local script_name=$1
    local script_path="$SCRIPT_DIR/$script_name"

    if [ -f "$script_path" ]; then
        log "运行测试脚本: $script_name"
        if bash "$script_path" 2>&1 | tee -a "$LOG_FILE"; then
            log_success "$script_name 测试通过"
            return 0
        else
            log_error "$script_name 测试失败"
            return 1
        fi
    else
        log_error "测试脚本不存在: $script_path"
        return 1
    fi
}

# 生成汇总报告
generate_summary() {
    local report_file="$REPORT_DIR/test_report_$TIMESTAMP.md"

    cat > "$report_file" << EOF
# RustKmer CLI 测试报告

**生成时间**: $(date)
**测试分支**: 009-rustkmer-cli-test
**RustKmer 版本**: $(rustkmer --version 2>&1 || echo "unknown")

## 测试概述

本报告包含 rustkmer CLI 所有命令的测试结果。

## 测试环境

- **操作系统**: $(uname -s)
- **CPU 信息**: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || lscpu | grep "Model name" | cut -d: -f2- | xargs)
- **内存总量**: $(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024/1024)"GB"}' || free -h | grep "Mem:" | awk '{print $2}')
- **Rust 版本**: $(rustc --version 2>/dev/null || echo "unknown")

## 测试结果

详见日志文件: test_run_$TIMESTAMP.log

EOF

    log_success "测试报告已生成: $report_file"
}

# 主函数
main() {
    log "开始 RustKmer CLI 全面测试"
    log "测试ID: $TIMESTAMP"

    # 检查前置条件
    check_rustkmer
    check_test_data

    # 运行各个测试
    local failed_tests=()
    local total_tests=0
    local passed_tests=0

    # 定义测试脚本列表（按优先级顺序）
    local test_scripts=(
        "test_count.sh"
        "test_query.sh"
        "test_dump.sh"
        "test_fuzzy_query.sh"
        "test_stats.sh"
        "test_merge.sh"
        "test_help.sh"
    )

    # 运行每个测试脚本
    for script in "${test_scripts[@]}"; do
        ((total_tests++))
        if run_test_script "$script"; then
            ((passed_tests++))
        else
            failed_tests+=("$script")
        fi
        echo "" | tee -a "$LOG_FILE"
    done

    # 生成汇总报告
    generate_summary

    # 输出最终结果
    log "测试完成！"
    log_info "总测试数: $total_tests"
    log_success "通过测试: $passed_tests"

    if [ ${#failed_tests[@]} -gt 0 ]; then
        log_error "失败测试: ${#failed_tests[@]}"
        log_error "失败的测试脚本:"
        for failed in "${failed_tests[@]}"; do
            log_error "  - $failed"
        done
        exit 1
    else
        log_success "所有测试通过！"
        exit 0
    fi
}

# 运行主函数
main "$@"