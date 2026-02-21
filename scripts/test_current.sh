#!/bin/bash
# Test current PyO3 version in current conda environment
# Usage: ./scripts/test_current.sh [py311|py312|py313]

set -e

ENV=${1:-py311}
PYTHON="/Users/forrest/miniconda3/envs/$ENV/bin/python"
MATURIN="/Users/forrest/miniconda3/bin/maturin"

echo "🔧 Testing PyO3 bindings with $ENV (Python: $($PYTHON --version))"

# Build
echo "📦 Building wheel..."
unset VIRTUAL_ENV && unset CONDA_PREFIX
cd /Users/forrest/GitHub/rustkmer/pyo3
rm -rf target/
PYO3_PYTHON=$PYTHON $MATURIN build --release

# Install
echo "📥 Installing wheel..."
$PYTHON -m pip install target/wheels/*.whl

# Validate
echo "✅ Validating installation..."
$PYTHON -c "
import rustkmer_pyo3
print('✅ 导入成功')
modes = [rustkmer_pyo3.LoadMode.Preload, rustkmer_pyo3.LoadMode.MemoryMapped, rustkmer_pyo3.LoadMode.Lazy]
print(f'✅ LoadMode: {len(modes)} modes')
classes = ['PyDatabase', 'PyQueryResult', 'PyDatabaseStats', 'PyFuzzyQuery', 'PyKmerCounter']
all_ok = True
for cls in classes:
    if hasattr(rustkmer_pyo3, cls):
        print(f'✅ {cls}')
    else:
        print(f'❌ {cls} 缺失')
        all_ok = False
print('✅ 测试通过！' if all_ok else '❌ 测试失败')
exit(0 if all_ok else 1)
"

echo "🎉 $ENV 测试完成！"
