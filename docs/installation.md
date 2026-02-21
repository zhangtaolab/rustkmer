# Installation

This guide will help you install RustKmer for Python on your system.

## Requirements

- Python 3.10 or higher
- Operating system: Linux, macOS, or Windows
- Rust compiler (optional, for building from source)

## Install from PyPI

The easiest way to install RustKmer is using pip:

```bash
pip install rustkmer
```

This will install the pre-compiled binary wheels for your platform.

### Verify Installation

```python
from pyrustkmer import PyCounter, LoadMode

print("RustKmer imported successfully!")

# Test basic functionality
counter = PyCounter(7)
counter.add_sequence("ATCGATCGATCGATCGATCGATC")
print(f"Total k-mers: {counter.get_stats().total_kmers)}")
```

## Platform-Specific Instructions

### Linux

For most Linux distributions, the pip installation should work out of the box:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-venv
pip install rustkmer

# CentOS/RHEL/Fedora
sudo dnf install python3-pip
pip install rustkmer
```

### macOS

```bash
# Using Homebrew (recommended)
brew install python@3.10
pip3 install rustkmer

# Or using system Python
python3 -m pip install rustkmer
```

### Windows

```powershell
# Using PowerShell (recommended)
python -m pip install rustkmer

# Or using pip in command prompt
pip install rustkmer
```

## Build from Source

If pre-compiled wheels are not available for your platform or you want to build the latest development version:

### Prerequisites

1. Install Rust compiler:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

2. Install Python development headers:
```bash
# Linux (Ubuntu/Debian)
sudo apt install python3-dev

# macOS
xcode-select --install

# Windows
# Install Visual Studio Build Tools or Visual Studio Community
```

### Clone and Build

```bash
git clone https://github.com/rustkmer/rustkmer.git
cd rustkmer

# Install in development mode
pip install -e .
```

### Build from PyPI Source

```bash
pip install --no-binary rustkmer rustkmer
```

## Virtual Environment Setup

It's recommended to use a virtual environment:

```bash
# Create virtual environment
python -m venv rustkmer-env

# Activate
# Linux/macOS:
source rustkmer-env/bin/activate
# Windows:
rustkmer-env\Scripts\activate

# Install
pip install rustkmer
```

## Docker Installation

For containerized deployments:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy and install RustKmer
COPY . /app
WORKDIR /app
RUN pip install -e .

# Example usage
CMD ["python", "-c", "from pyrustkmer import PyCounter, LoadMode; print('RustKmer installed successfully!')"]
```

## Troubleshooting

### Common Issues

#### 1. "Failed building wheel" error

This usually means Rust is not installed or not in PATH:

```bash
# Check Rust installation
rustc --version
cargo --version

# If not installed, install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

#### 2. "Python.h: No such file or directory"

You need Python development headers:

```bash
# Ubuntu/Debian
sudo apt install python3-dev

# CentOS/RHEL/Fedora
sudo dnf install python3-devel

# macOS
xcode-select --install

# Windows
# Install Visual Studio Build Tools with C++ support
```

#### 3. Permission denied

Use a virtual environment or install with user flag:

```bash
pip install --user rustkmer
```

#### 4. Version conflicts

Ensure you have Python 3.10+:

```bash
python --version
# Should show Python 3.10.x or higher
```

### Getting Help

If you encounter issues:

1. Check the [GitHub Issues](https://github.com/rustkmer/rustkmer/issues)
2. Provide your system information:
   ```bash
   python --version
   pip --version
   rustc --version
   ```
3. Include the full error message and installation command used

## Next Steps

After successful installation:

1. Read the [Quick Start guide](user-guide/quickstart.md) to learn basic usage
2. Check out the [Examples](examples/) for practical use cases
3. Refer to the [API Reference](api-reference/) for detailed documentation

## Version Compatibility

| RustKmer Version | Python Version | Status |
|------------------|----------------|--------|
| 0.1.x | 3.10+ | ✅ Stable |
| 0.0.x | 3.8+ | ⚠️ Legacy |

## Release Notes

### Version 0.1.0 (Latest)
- Complete Python API with all CLI features
- Performance optimizations for large datasets
- Fuzzy query with wildcard support
- Database merging and statistics
- Cross-platform compatibility

## Uninstallation

To uninstall RustKmer:

```bash
pip uninstall rustkmer
```

If you installed Rust specifically for RustKmer and no longer need it:

```bash
rustup self uninstall
```