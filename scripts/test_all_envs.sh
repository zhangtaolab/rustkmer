#!/bin/bash
# Test current PyO3 version across all conda environments
# Usage: ./scripts/test_all_envs.sh

set -e

CONDA_BASE="/Users/forrest/miniconda3"
MATURIN="$CONDA_BASE/bin/maturin"

echo "🧪 Testing PyO3 bindings across all Python versions..."
echo "================================================"

for env in py311 py312 py313; do
    PYTHON="$CONDA_BASE/envs/$ENV/bin/python"
    
    if [ ! -f "$PYTHON" ]; then
        echo "⚠️  Skipping $env (not found)"
        continue
    fi
    
    echo ""
    echo "🔧 Testing $env (Python: $($PYTHON --version))"
    echo "------------------------------------------------"
    
    # Build
    echo "📦 Building wheel..."
    unset VIRTUAL_ENV && unset CONDA_PREFIX
    cd /Users/forrest/GitHub/rustkmer/pyo3
    rm -rf target/
    PYO3_PYTHON=$PYTHON $MATURIN build --release
    
    # Install
    echo "📥 Installing wheel..."
    $PYTHON -m pip install target/wheels/*.whl --quiet
    
    # Validate
    echo "✅ Validating..."
    if $PYTHON -c "
import rustkmer_pyo3
modes = [rustkmer_pyo3.LoadMode.Preload, rustkmer_pyo3.LoadMode.MemoryMapped, rustkmer_pyo3.LoadMode.Lazy]
classes = ['PyDatabase', 'PyQueryResult', 'PyDatabaseStats', 'PyFuzzyQuery', 'PyKmerCounter']
all_ok = all(hasattr(rustkmer_pyo3, cls) for cls in classes)
print('✅ 全部验证通过' if all_ok else '❌ 验证失败')
exit(0 if all_ok else 1)
" 2>&1; then
        echo "🎉 $env: ✅ SUCCESS"
    else
        echo "💥 $env: ❌ FAILED"
        exit 1
    fi
done

echo ""
echo "================================================"
echo "🎉 所有环境测试通过！"
