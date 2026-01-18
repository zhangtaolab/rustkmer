#!/bin/bash
# Sync version between Rust CLI and PyO3
# Usage: ./scripts/sync_versions.sh [version]

set -e

# Get version from CLI Cargo.toml
CLI_VERSION=$(grep '^version' Cargo.toml | head -1 | awk -F'"' '{print $2}')

# Get version from PyO3 Cargo.toml
PYO3_VERSION=$(grep '^version' pyo3/Cargo.toml | head -1 | awk -F'"' '{print $2}')

echo "Rust CLI version: $CLI_VERSION"
echo "PyO3 version:     $PYO3_VERSION"

if [ "$CLI_VERSION" != "$PYO3_VERSION" ]; then
    echo "⚠️  Versions are different!"
    echo "Updating PyO3 to match CLI..."
    sed -i '' "s/version = \"$PYO3_VERSION\"/version = \"$CLI_VERSION\"/" pyo3/Cargo.toml
    sed -i '' "s/version = \"$PYO3_VERSION\"/version = \"$CLI_VERSION\"/" pyo3/pyproject.toml
    echo "✅ Updated to $CLI_VERSION"
else
    echo "✅ Versions are already in sync"
fi
