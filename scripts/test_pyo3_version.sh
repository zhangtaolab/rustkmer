#!/bin/bash
# Test with specific PyO3 version
# Usage: ./scripts/test_pyo3_version.sh <version> [env]
# Example: ./scripts/test_pyo3_version.sh 0.23.0 py312

set -e

PYO3_VERSION=${1:-0.22.6}
ENV=${2:-py312}
CONDA_BASE="/Users/forrest/miniconda3"
PYTHON="$CONDA_BASE/envs/$ENV/bin/python"
MATURIN="$CONDA_BASE/bin/maturin"

echo "🔧 Testing PyO3 $PYO3_VERSION with $ENV"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYO3_DIR="$SCRIPT_DIR/../pyo3"

cd "$PYO3_DIR"

# Backup original files
cp Cargo.toml Cargo.toml.backup
cp pyproject.toml pyproject.toml.bak 2>/dev/null || true

echo "📌 Switching PyO3 to version $PYO3_VERSION..."
sed -i '' 's/features = \["pyo3\/extension-module"\]/features = []/' pyproject.toml

if [[ "$PYO3_VERSION" =~ ^0\.2[5-9] ]] || [[ "$PYO3_VERSION" =~ ^0\.[3-9][0-9] ]]; then
    echo "📌 PyO3 0.25+ detected: updating Cargo.toml for compatibility..."
    
    python3 << 'PYEOF'
import re

with open('Cargo.toml', 'r') as f:
    content = f.read()

old_patterns = [
    r'pyo3 = \{ version = "0\.22", features = \["extension-module"\] \}',
    r'pyo3 = \{ version = "0\.23", features = \["extension-module"\] \}', 
    r'pyo3 = \{ version = "0\.24", features = \["extension-module"\] \}',
]
new_dep = 'pyo3 = { version = "0.25" }'

for pattern in old_patterns:
    content = re.sub(pattern, new_dep, content)

with open('Cargo.toml', 'w') as f:
    f.write(content)
    
print("✅ Cargo.toml updated successfully")
PYEOF
fi

# Build
echo "📦 Building wheel..."
unset VIRTUAL_ENV && unset CONDA_PREFIX
rm -rf target/
PYO3_PYTHON=$PYTHON $MATURIN build --release

# Restore original files
mv Cargo.toml.backup Cargo.toml 2>/dev/null || true
mv pyproject.toml.bak pyproject.toml 2>/dev/null || true
rm -f pyproject.toml.bak 2>/dev/null || true

# Install and validate
echo "📥 Installing and validating..."
$PYTHON -m pip install target/wheels/*.whl --quiet

if $PYTHON -c "
import rustkmer_pyo3
classes = ['PyDatabase', 'PyQueryResult', 'PyDatabaseStats', 'PyFuzzyQuery', 'PyKmerCounter']
all_ok = all(hasattr(rustkmer_pyo3, cls) for cls in classes)
print('✅ 验证通过' if all_ok else '❌ 验证失败')
exit(0 if all_ok else 1)
" 2>&1; then
    echo "🎉 PyO3 $PYO3_VERSION with $ENV: ✅ SUCCESS"
else
    echo "💥 PyO3 $PYO3_VERSION with $ENV: ❌ FAILED"
    exit 1
fi
