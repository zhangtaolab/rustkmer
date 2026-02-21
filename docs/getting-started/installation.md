# Installation

RustKmer offers multiple installation methods to suit different use cases and environments. Choose the one that best fits your needs.

## Quick Install

### Python with Virtual Environment (Recommended for most users) 🐍

Using a virtual environment is highly recommended to avoid conflicts with system packages:

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install RustKmer
pip install rustkmer

# Verify installation
python -c "from pyrustkmer import KmerCounter; print('✅ RustKmer installed successfully!')"

# Deactivate when done
deactivate
```

**Benefits of using .venv:**
- 🛡️ **Isolation**: Prevents conflicts with system Python packages
- 🔄 **Reproducibility**: Ensures consistent environments across projects
- 🧹 **Cleanliness**: Easy to remove or recreate environments
- 👥 **Collaboration**: Share exact environment requirements with team

### System-wide Python Installation
```bash
pip install rustkmer
```

### Modern Python with uv (Ultra-fast) ⚡

[uv](https://github.com/astral-sh/uv) is a next-generation Python package manager written in Rust that's 10-100x faster than pip:

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install uv (Windows PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or install uv with pip
pip install uv

# Create new RustKmer project with uv
uv init rustkmer-analysis
cd rustkmer-analysis

# Add RustKmer dependency
uv add rustkmer

# Run RustKmer immediately
uv run python -c "from pyrustkmer import KmerCounter; print('✅ RustKmer ready with uv!')"

# Create a simple analysis script
echo 'from pyrustkmer import KmerCounter
counter = PyCounter(21, canonical=True)
print("🧬 RustKmer is ready for k-mer analysis!")' > analysis.py

# Run your analysis
uv run python analysis.py
```

**Why choose uv?**
- 🚀 **Speed**: 10-100x faster than pip
- 🎯 **Simplicity**: Single command for environment setup
- 📦 **Projects**: Built-in project management
- 🔄 **Reliability**: Better caching and dependency resolution

### Rust (For library integration) 🦀
```bash
cargo install rustkmer
```

---

## Detailed Installation Methods

### Method 1: Python Package Manager (PyPI) with Virtual Environment 🐍

The recommended way to install RustKmer for Python development and bioinformatics workflows.

#### Step 1: Create Virtual Environment
```bash
# Create a dedicated virtual environment for RustKmer
python3 -m venv .venv
```

#### Step 2: Activate Virtual Environment
```bash
# On Linux and macOS:
source .venv/bin/activate

# On Windows (Command Prompt):
.venv\Scripts\activate.bat

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

#### Step 3: Install RustKmer
```bash
# Install the latest version
pip install rustkmer

# Install a specific version
pip install rustkmer==1.0.0

# Install with development dependencies (optional)
pip install rustkmer[dev]
```

#### Step 4: Verify Installation
```bash
python -c "from pyrustkmer import KmerCounter; print('✅ RustKmer installed successfully!')"
```

**Verification:**
```bash
python -c "from pyrustkmer import KmerCounter; print('✅ RustKmer installed successfully!')"
```

**System Requirements:**
- Python 3.8 or higher
- 64-bit operating system (Linux, macOS, Windows)
- 50MB disk space for the package

---

### Method 2: Rust Package Manager (Cargo) 🦀

Install the command-line tool for system-wide k-mer analysis.

```bash
# Install from crates.io
cargo install rustkmer

# Install from source (requires Rust toolchain)
git clone https://github.com/rustkmer/rustkmer
cd rustkmer
cargo install --path .
```

**Verification:**
```bash
rustkmer --version
# Expected output: rustkmer 1.0.0
```

**System Requirements:**
- Rust 1.80 or higher
- Cargo package manager
- Compiler toolchain (gcc/clang on Linux/macOS, MSVC on Windows)

---

### Method 3: Build from Source 🔧

For development or when you need the latest features.

#### Prerequisites

**Required Dependencies:**
- Rust 1.80+
- Python 3.8+ (for Python bindings)
- C++ compiler (gcc/clang/MSVC)
- Git

#### Build Steps

```bash
# Clone the repository
git clone https://github.com/rustkmer/rustkmer.git
cd rustkmer

# Build the Rust library
cargo build --release

# Build Python bindings (optional)
cd python
maturin develop --release

# Install command-line tool
cargo install --path .
```

**Verification:**
```bash
# Test Rust CLI
rustkmer --version

# Test Python bindings
python -c "from pyrustkmer import KmerCounter; print('✅ Build successful!')"
```

---

### Method 4: Container Installation 🐳

Using Docker for reproducible environments.

#### Pull Pre-built Image
```bash
# Pull the official image
docker pull rustkmer/rustkmer:latest

# Run container
docker run --rm -it rustkmer/rustkmer:latest rustkmer --version
```

#### Build from Source
```bash
# Clone repository
git clone https://github.com/rustkmer/rustkmer.git
cd rustkmer

# Build Docker image
docker build -t rustkmer:local .

# Run your build
docker run --rm -it rustkmer:local rustkmer --version
```

---

## Installation Verification

### Python Installation Test

```python
#!/usr/bin/env python3
"""Test RustKmer installation."""

try:
    from pyrustkmer import KmerCounter, Database
    print("✅ Python installation successful!")

    # Test basic functionality
    counter = PyCounter(21, canonical=True)
    counter.add_sequence("ATCGATCGATCGATCGATCG")

    print(f"✅ Basic functionality working!")
    print(f"   K-mer size: 21")
    print(f"   Canonical mode: True")
    print(f"   Test sequence processed successfully")

except ImportError as e:
    print(f"❌ Installation failed: {e}")
    print("Please check that RustKmer is properly installed.")
    exit(1)

except Exception as e:
    print(f"❌ Runtime error: {e}")
    exit(1)
```

### Command Line Installation Test

```bash
#!/bin/bash
"""Test RustKmer CLI installation."""

# Test command availability
if command -v rustkmer &> /dev/null; then
    echo "✅ RustKmer CLI found in PATH"

    # Test basic functionality
    rustkmer --version > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ CLI functionality working!"
        version=$(rustkmer --version)
        echo "   Version: $version"
    else
        echo "❌ CLI functionality test failed"
        exit 1
    fi
else
    echo "❌ RustKmer CLI not found in PATH"
    echo "Please ensure ~/.cargo/bin is in your PATH"
    echo "Or add it to your shell configuration:"
    echo "  export PATH=\"\$HOME/.cargo/bin:\$PATH\""
    exit 1
fi
```

---

## Platform-Specific Notes

### Linux

#### Ubuntu/Debian
```bash
# Install Python build tools
sudo apt update
sudo apt install python3-dev python3-pip

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# Install RustKmer
pip install rustkmer
```

#### CentOS/RHEL/Fedora
```bash
# Install development tools
sudo dnf install python3-devel python3-pip gcc

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# Install RustKmer
pip install rustkmer
```

### macOS

#### Homebrew (Recommended)
```bash
# Install Python and Rust
brew install python rust

# Install RustKmer
pip install rustkmer

# Add Cargo to PATH (if not already)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### MacPorts
```bash
# Install Python and Rust
sudo port install python3 rust

# Install RustKmer
pip install rustkmer
```

### Windows

#### Using Chocolatey
```powershell
# Install Python and Rust
choco install python rust

# Install RustKmer
pip install rustkmer
```

#### Manual Installation
1. Install Python from [python.org](https://python.org)
2. Install Rust from [rust-lang.org](https://rust-lang.org)
3. Add Rust to system PATH
4. Install RustKmer: `pip install rustkmer`

---

## Troubleshooting

### Common Installation Issues

#### ImportError on Python
```bash
# Error: ModuleNotFoundError: No module named 'rustkmer'
# Solution: Install using pip
pip install rustkmer

# Or ensure you're using the right Python environment
which python
python -m pip install rustkmer
```

#### Cargo Not Found
```bash
# Error: cargo: command not found
# Solution: Install Rust or add to PATH
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

#### Compilation Errors
```bash
# Error: Build failed during compilation
# Solution: Install required system dependencies

# Ubuntu/Debian
sudo apt-get install build-essential

# macOS (with Xcode command line tools)
xcode-select --install

# Windows (with Visual Studio Build Tools)
# Install Visual Studio Community with C++ development tools
```

#### Permission Errors
```bash
# Error: Permission denied when installing packages
# Solution: Use virtual environment or user installation

# Create virtual environment
python3 -m venv rustkmer_env
source rustkmer_env/bin/activate
pip install rustkmer

# Or install for current user
pip install --user rustkmer
```

### Getting Help

If you encounter installation issues:

1. **Check System Requirements**: Ensure Python 3.8+ and Rust 1.80+ are installed
2. **Verify PATH**: Make sure `pip` and/or `cargo` are in your system PATH
3. **Clear Cache**: Sometimes clearing pip cache helps: `pip cache purge`
4. **Update Packages**: Ensure `pip` and `rustup` are up to date

---

## Next Steps

Once RustKmer is installed, you're ready to start counting k-mers! Continue to [First Steps](first-steps.md) for your first k-mer counting operations.

### Quick Preview

```bash
# Python usage
from pyrustkmer import KmerCounter
counter = PyCounter(21, canonical=True)
counter.add_from_fasta("genome.fa.gz")
print(f"Counted {counter.get_stats().total_kmers):,} k-mers!")

# Command line usage
rustkmer count -k 21 -i genome.fa.gz -o genome_k21.rkdb
```

Ready to dive in? Let's move to [First Steps](first-steps.md)!