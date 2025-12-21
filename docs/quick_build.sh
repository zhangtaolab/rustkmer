#!/bin/bash
# MkDocs 快速构建脚本

echo "🚀 尝试运行MkDocs..."

# 检查mkdocs
if command -v mkdocs >/dev/null 2>&1; then
    echo "✅ mkdocs已安装"
    echo "🔨 开始构建..."
    mkdocs build --clean
    if [ $? -eq 0 ]; then
        echo "✅ 文档构建成功!"
        echo "📁 输出在 site/ 目录"
    else
        echo "❌ 构建失败"
    fi
else
    echo "❌ mkdocs未安装"
    echo "请运行: pip install mkdocs mkdocs-material"
fi
