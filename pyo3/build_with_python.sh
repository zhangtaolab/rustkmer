#!/bin/bash
# PyO3构建脚本 - 包含正确的Python链接设置

echo "🔧 设置Python链接环境..."

# 获取Python配置
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_PATH=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('LDLIBRARY'))")
PYTHON_PREFIX=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('prefix'))")

echo "Python版本: $PYTHON_VERSION"
echo "Python路径: $PYTHON_PATH"
echo "Python前缀: $PYTHON_PREFIX"

# 设置构建环境变量
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
export PYO3_PYTHON=/usr/bin/python3

echo "🚀 开始构建PyO3扩展..."

# 清理之前的构建
cargo clean

# 构建
cargo build

if [ $? -eq 0 ]; then
    echo "✅ PyO3构建成功!"
    
    # 设置Python路径
    export PYTHONPATH="/Users/forrest/Github/rustkmer/pyo3/target/debug:$PYTHONPATH"
    echo "📁 PYTHONPATH已设置: $PYTHONPATH"
    
    # 测试导入
    echo "🧪 测试Python导入..."
    python3 -c "
import sys
sys.path.insert(0, '/Users/forrest/Github/rustkmer/pyo3/target/debug')
try:
    import rustkmer_pyo3
    print('✅ rustkmer_pyo3导入成功!')
    print('📚 可用类:', [x for x in dir(rustkmer_pyo3) if not x.startswith('_')])
except ImportError as e:
    print('❌ 导入失败:', e)
"
    
else
    echo "❌ PyO3构建失败!"
    exit 1
fi

