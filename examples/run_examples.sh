#!/bin/bash
# RustKmer示例执行脚本
# 一键运行所有示例和测试

set -e

echo "=== RustKmer示例执行脚本 ==="
echo ""

# 检查RustKmer是否已编译
if [ ! -f "target/release/rustkmer" ]; then
    echo "🔨 编译RustKmer..."
    cargo build --release
    echo "✅ 编译完成"
    echo ""
fi

# 设置示例脚本权限
echo "🔧 设置示例脚本权限..."
chmod +x examples/basic_usage.sh
chmod +x examples/performance_benchmark.sh
echo "✅ 权限设置完成"
echo ""

# 创建示例数据目录
mkdir -p example_data
echo "📁 示例数据目录已准备"
echo ""

echo "🚀 可用示例:"
echo "1. 基本使用示例 - 演示k-mer计数和查询基本操作"
echo "2. 性能基准测试 - 比较不同配置下的性能表现"
echo "3. Python集成示例 - Python API使用示例"
echo ""

# 交互式菜单
echo "请选择要运行的示例:"
echo "1) 运行基本使用示例"
echo "2) 运行性能基准测试"
echo "3) 运行Python集成示例"
echo "4) 运行所有示例"
echo "5) 退出"
echo ""

read -p "请输入选择 (1-5): " choice

case $choice in
    1)
        echo "🏃 运行基本使用示例..."
        ./examples/basic_usage.sh
        ;;
    2)
        echo "🏃 运行性能基准测试..."
        ./examples/performance_benchmark.sh
        ;;
    3)
        echo "🏃 运行Python集成示例..."
        if command -v python3 &> /dev/null; then
            python3 examples/python_integration.py
        else
            echo "❌ 未找到python3，请先安装Python"
            exit 1
        fi
        ;;
    4)
        echo "🏃 运行所有示例..."
        echo ""
        echo "--- 基本使用示例 ---"
        ./examples/basic_usage.sh
        echo ""
        echo "--- 性能基准测试 ---"
        ./examples/performance_benchmark.sh
        echo ""
        echo "--- Python集成示例 ---"
        if command -v python3 &> /dev/null; then
            python3 examples/python_integration.py
        else
            echo "⚠️  跳过Python示例 - 未找到python3"
        fi
        ;;
    5)
        echo "👋 退出"
        exit 0
        ;;
    *)
        echo "❌ 无效选择，请输入1-5"
        exit 1
        ;;
esac

echo ""
echo "✅ 示例执行完成！"
echo ""
echo "📊 生成的结果文件:"
if [ -d "example_data" ]; then
    ls -la example_data/
fi

if [ -d "benchmark_results" ]; then
    ls -la benchmark_results/
fi

echo ""
echo "📖 更多信息请查看:"
echo "- 用户指南: USER_GUIDE.md"
echo "- 项目README: README.md"
echo "- 性能分析: specs/003-parallel-query/"
echo ""
echo "🎉 感谢使用RustKmer！"