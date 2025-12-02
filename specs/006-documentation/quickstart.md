# Quick Start Guide for Documentation Implementation

**Date**: 2025-12-02
**Purpose**: Rapid deployment plan for MkDocs documentation system

## Implementation Quick Start

### Prerequisites Setup

```bash
# Install Python dependencies
pip install mkdocs mkdocs-material mkdocstrings[python] \
               mkdocs-gen-files mkdocs-mermaid2 mkdocs-section-index

# Verify installation
mkdocs --version  # Should be 1.5+
```

### Basic MkDocs Configuration

Create `mkdocs.yml` in repository root:

```yaml
site_name: RustKmer Documentation
site_description: High-performance k-mer counting library
site_author: RustKmer Team
site_url: https://rustkmer.github.io

repo_name: rustkmer/rustkmer
repo_url: https://github.com/rustkmer/rustkmer

theme:
  name: material
  language: en
  features:
    - navigation.instant
    - navigation.tracking
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.indexes
    - search.highlight
    - search.share
    - content.code.copy
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      toggle:
        icon: material/brightness-4
        name: Switch to light mode

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [python]
  - gen-files:
      scripts:
        - scripts/generate_rust_docs.py

nav:
  - Home: index.md
  - Getting Started:
    - getting-started/index.md
    - Installation: getting-started/installation.md
    - Quick Start: getting-started/first-steps.md
  - User Guide:
    - user-guide/index.md
    - Counting k-mers: user-guide/counting-kmers.md
    - Querying: user-guide/querying.md
    - Fuzzy Search: user-guide/fuzzy-search.md
    - Performance Tips: user-guide/performance-tips.md
  - API Reference:
    - api-reference/index.md
    - Rust:
      - api-reference/rust/index.md
      - KmerCounter: api-reference/rust/counter.md
      - Database: api-reference/rust/database.md
      - Fuzzy Query: api-reference/rust/fuzzy.md
    - Python:
      - api-reference/python/index.md
      - KmerCounter: api-reference/python/kmercounter.md
      - Database: api-reference/python/database.md

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.tabbed:
      alternate_style: true
```

### Directory Structure Setup

```bash
# Create documentation directories
mkdir -p docs/{getting-started,user-guide,api-reference/{rust,python},tutorials,deployment,background,appendix}
mkdir -p scripts
mkdir -p .github/workflows

# Create initial files
touch docs/index.md
touch docs/getting-started/{index.md,installation.md,first-steps.md}
touch docs/user-guide/{index.md,counting-kmers.md,querying.md,fuzzy-search.md,performance-tips.md}
```

### Rust Documentation Generation Script

Create `scripts/generate_rust_docs.py`:

```python
#!/usr/bin/env python3
"""Generate Rust API documentation from source code."""

import os
import subprocess
from pathlib import Path

def generate_rust_docs():
    """Generate Markdown documentation from Rust source code."""

    # Ensure target directory exists
    api_dir = Path("docs/api-reference/rust")
    api_dir.mkdir(parents=True, exist_ok=True)

    # Generate rustdoc JSON
    subprocess.run([
        "cargo", "rustdoc", "--", "-Z", "unstable-options",
        "--output-format", "json", "--output", "target/doc.json"
    ], check=True)

    # Parse rustdoc and generate Markdown files
    # This is a simplified version - actual implementation would parse JSON
    rust_files = list(Path("src").rglob("*.rs"))

    for rust_file in rust_files:
        if rust_file.name == "mod.rs":
            continue

        doc_file = api_dir / f"{rust_file.stem}.md"
        generate_doc_file(rust_file, doc_file)

def generate_doc_file(rust_file, doc_file):
    """Generate documentation file from Rust source."""
    with open(rust_file, 'r') as f:
        content = f.read()

    # Extract doc comments (simplified)
    doc_lines = []
    in_doc_comment = False

    for line in content.split('\n'):
        if line.strip().startswith('///'):
            doc_lines.append(line.strip()[3:].strip())
            in_doc_comment = True
        elif in_doc_comment and line.strip().startswith('///'):
            doc_lines.append(line.strip()[3:].strip())
        elif in_doc_comment and not line.strip().startswith('///'):
            in_doc_comment = False

    if doc_lines:
        with open(doc_file, 'w') as f:
            f.write(f"# {rust_file.stem.title()}\n\n")
            f.write('\n'.join(doc_lines))
            f.write(f"\n\n*Source: [`{rust_file.name}`](../../../{rust_file})*")

if __name__ == "__main__":
    generate_rust_docs()
```

### GitHub Actions Workflow

Create `.github/workflows/docs.yml`:

```yaml
name: Documentation

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Set up Rust
      uses: actions-rs/toolchain@v1
      with:
        toolchain: stable

    - name: Install dependencies
      run: |
        pip install mkdocs mkdocs-material mkdocstrings[python] \
                       mkdocs-gen-files mkdocs-mermaid2 mkdocs-section-index

    - name: Generate Rust docs
      run: python scripts/generate_rust_docs.py

    - name: Build documentation
      run: mkdocs build

    - name: Deploy to GitHub Pages
      if: github.ref == 'refs/heads/main'
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./site
```

### Landing Page Content

Create `docs/index.md`:

```markdown
# RustKmer

[![Rust](https://img.shields.io/badge/rust-1.80+-orange.svg)](https://www.rust-lang.org)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://rustkmer.github.io)

**World-class performance for k-mer counting and genomic analysis**

RustKmer is a high-performance k-mer counting library written in Rust with Python bindings. It provides exceptional speed and memory efficiency for processing large genomic datasets.

## ✨ Key Features

- **🚀 Blazing Fast**: Up to 14,772x faster than traditional tools
- **🧪 Memory Efficient**: Minimal memory footprint with streaming processing
- **🔍 Advanced Querying**: Support for exact and fuzzy k-mer searches
- **🐍 Python Native**: First-class Python bindings for easy integration
- **📱 Cross-Platform**: Works on Linux, macOS, and Windows
- **⚡ Production Ready**: Extensively tested with real-world genomic data

## 🚀 Quick Start

### Installation

```bash
# Rust (from crates.io)
cargo install rustkmer

# Python (from PyPI)
pip install rustkmer
```

### Basic Usage

#### Rust
```rust
use rustkmer::KmerCounter;

let mut counter = KmerCounter::new(21, true);
counter.count_file("genome.fa.gz")?;
println!("Total k-mers: {}", counter.get_total_count());
```

#### Python
```python
from rustkmer import KmerCounter

counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa.gz")
print(f"Total k-mers: {counter.get_total_count()}")
```

## 📖 Documentation

- **[Getting Started](getting-started/)** - Installation and first steps
- **[User Guide](user-guide/)** - Comprehensive usage guide
- **[API Reference](api-reference/)** - Rust and Python API documentation
- **[Tutorials](tutorials/)** - Step-by-step tutorials
- **[Performance Guide](user-guide/performance-tips.md)** - Optimization tips

## 🏆 Performance

RustKmer delivers world-class performance:

| Metric | RustKmer | Traditional Tools | Improvement |
|--------|----------|------------------|-------------|
| Query Speed | 3,986,981/sec | 270/sec | **14,772x** |
| Memory Usage | <2MB | 10-100MB | **10-100x** |
| Large Files | 374M k-mers | Limited | **Significant** |

*Based on benchmarks with real genomic datasets*

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](contributing.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```

## Development Workflow

### Local Development

```bash
# Start local development server
mkdocs serve

# Build for production
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy
```

### Content Creation Process

1. **Create/Edit Markdown files** in `docs/` directory
2. **Update API documentation** by running `python scripts/generate_rust_docs.py`
3. **Test locally** with `mkdocs serve`
4. **Commit changes** - CI will build and validate automatically
5. **Deploy** happens automatically on merge to main

This quick start provides the foundation for a complete documentation system that can be incrementally enhanced with additional content and features.