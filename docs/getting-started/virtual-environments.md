# Virtual Environments Guide

This guide explains how to use Python virtual environments with RustKmer to ensure clean, isolated development environments.

## 🎯 Why Use Virtual Environments?

### Benefits
- **🛡️ Isolation**: Prevents conflicts between project dependencies
- **🔄 Reproducibility**: Ensures consistent environments across different machines
- **🧹 Cleanliness**: Easy to remove and recreate environments
- **👥 Collaboration**: Share exact environment requirements with team members
- **🔒 Security**: Contains dependencies to specific projects

### When to Use Virtual Environments
- ✅ **Development**: When writing Python code with RustKmer
- ✅ **Research**: For bioinformatics projects with specific dependencies
- ✅ **Production**: When deploying applications with specific versions
- ✅ **Testing**: To create isolated test environments

## 🚀 Quick Setup

### Step 1: Create Virtual Environment
```bash
# Create virtual environment named .venv
python3 -m venv .venv

# Alternative: Create with specific Python version
python3.9 -m venv .venv
```

### Step 2: Activate Environment

#### Linux / macOS
```bash
# Using bash/zsh
source .venv/bin/activate

# Verify activation
which python
# Should show: /path/to/project/.venv/bin/python
```

#### Windows
```powershell
# PowerShell
.venv\Scripts\Activate.ps1

# Command Prompt
.venv\Scripts\activate.bat

# Verify activation
where python
# Should show: C:\path\to\project\.venv\Scripts\python.exe
```

### Step 3: Install RustKmer
```bash
# Upgrade pip first
pip install --upgrade pip

# Install RustKmer
pip install rustkmer

# For development with extra dependencies
pip install rustkmer[dev]

# Verify installation
python -c "from rustkmer import KmerCounter; print('✅ RustKmer installed successfully!')"
```

### Step 4: Start Working
```bash
# Your Python prompt should show (.venv)
# Create a test script
echo 'from rustkmer import KmerCounter
counter = KmerCounter(k=21)
print("🧬 RustKmer is ready!")' > test_rustkmer.py

# Run it
python test_rustkmer.py
```

### Step 5: Deactivate When Done
```bash
# Deactivate the virtual environment
deactivate

# Your Python prompt returns to normal
```

## 📁 Directory Structure

```
my_project/
├── .venv/                 # Virtual environment directory
│   ├── bin/              # Executables (Linux/macOS)
│   ├── Scripts/          # Executables (Windows)
│   ├── include/          # C header files
│   ├── lib/              # Python libraries
│   └── share/            # Shared data
├── requirements.txt      # Project dependencies
├── main.py              # Your Python code
└── README.md            # Project documentation
```

## 📋 Environment Management

### Common Commands
```bash
# Create new environment
python3 -m venv .venv

# Activate environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# List installed packages
pip list

# Show package information
pip show rustkmer

# Upgrade pip
pip install --upgrade pip

# Upgrade specific package
pip install --upgrade rustkmer

# Uninstall package
pip uninstall rustkmer

# Deactivate environment
deactivate
```

### Saving Dependencies
```bash
# Save current environment to requirements.txt
pip freeze > requirements.txt

# Install from requirements.txt
pip install -r requirements.txt

# Save only main dependencies (exclude sub-dependencies)
pip list --format=freeze > requirements-main.txt
```

## 🔧 Advanced Usage

### Custom Environment Names
```bash
# Create environment with custom name
python3 -m venv rustkmer_env

# Activate custom environment
source rustkmer_env/bin/activate

# Deactivate
deactivate
```

### Environment with Specific Python Version
```bash
# Use Python 3.9
python3.9 -m venv .venv-py39

# Use Python 3.10
python3.10 -m venv .venv-py310

# Check Python version in environment
source .venv-py39/bin/activate
python --version
```

### Pre-commit Hooks Setup
```bash
# Install pre-commit in your environment
pip install pre-commit

# Set up hooks for your project
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## 🛠️ Development Workflow

### For RustKmer Development
```bash
# 1. Create environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install development dependencies
pip install -r requirements-dev.txt

# 3. Install RustKmer in development mode
cd rustkmer/
pip install -e .

# 4. Run tests
pytest tests/

# 5. Deactivate when done
deactivate
```

### For Bioinformatics Projects
```bash
# 1. Create environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install RustKmer and bioinformatics tools
pip install rustkmer pandas matplotlib seaborn biopython

# 3. Save dependencies
pip freeze > requirements.txt

# 4. Start your analysis
python analyze_kmers.py
```

## 🐛 Troubleshooting

### Common Issues

#### Python Not Found
```bash
# Error: python3: command not found
# Solution: Use python instead of python3
python -m venv .venv
```

#### Activation Fails
```bash
# Error: .venv/bin/activate: No such file or directory
# Solution: Check if venv was created successfully
ls -la .venv/

# Recreate if necessary
rm -rf .venv
python3 -m venv .venv
```

#### Permission Denied (Windows PowerShell)
```powershell
# Error: Scripts\Activate.ps1 cannot be loaded
# Solution: Change execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Package Installation Fails
```bash
# Error: Could not build wheels for rustkmer
# Solution: Check Rust installation
rustc --version
cargo --version

# Install Rust if missing
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

#### Import Error
```bash
# Error: ModuleNotFoundError: No module named 'rustkmer'
# Solution: Check if you're in the right environment
which python
pip list | grep rustkmer

# Reinstall if necessary
pip uninstall rustkmer
pip install rustkmer
```

### Recovery Commands
```bash
# Reset environment completely
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Clear pip cache if installation fails
pip cache purge
pip install rustkmer
```

## 📚 Best Practices

### 1. Always Use Virtual Environments
```bash
# ✅ Good: Use virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install rustkmer

# ❌ Bad: Install globally
pip install rustkmer
```

### 2. Keep .venv Out of Version Control
```gitignore
# .gitignore
.venv/
__pycache__/
*.pyc
```

### 3. Document Dependencies
```bash
# Always create requirements.txt
pip freeze > requirements.txt

# Or use specific versions
echo "rustkmer==1.0.0" > requirements.txt
echo "pandas>=1.3.0" >> requirements.txt
```

### 4. Use Meaningful Environment Names
```bash
# ✅ Good: Descriptive names
python3 -m venv rustkmer-analysis
python3 -m venv ml-experiment

# ❌ Less clear: Generic names
python3 -m venv env
python3 -m venv venv
```

### 5. Regular Maintenance
```bash
# Regularly update packages
pip list --outdated
pip install --upgrade package-name

# Clean up unused packages
pip uninstall package-name
```

## 🔄 Environment Sharing

### Export Environment
```bash
# Save all packages
pip freeze > requirements.txt

# Save only top-level packages
pip list --not-required --format=freeze > requirements-main.txt
```

### Recreate Environment
```bash
# Clone repository
git clone https://github.com/user/project.git
cd project

# Create and activate environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Using conda (Alternative)
```bash
# Create conda environment
conda create -n rustkmer python=3.9
conda activate rustkmer

# Install RustKmer
pip install rustkmer

# Export environment
conda env export > environment.yml

# Recreate from file
conda env create -f environment.yml
```

## ⚡ Modern Alternative: Using uv

[uv](https://github.com/astral-sh/uv) is an extremely fast Python package and project manager written in Rust. It's 10-100x faster than pip and creates virtual environments instantly.

### Install uv
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```

### Create Project with uv
```bash
# Create new project
uv init rustkmer-project
cd rustkmer-project

# Add RustKmer dependency
uv add rustkmer

# Add development dependencies
uv add --dev pytest pandas matplotlib

# Run Python
uv run python -c "from rustkmer import KmerCounter; print('✅ RustKmer ready!')"
```

### uv vs Traditional venv
```bash
# Traditional venv (slower)
python3 -m venv .venv
source .venv/bin/activate
pip install rustkmer

# uv (much faster)
uv venv
source .venv/bin/activate
uv pip install rustkmer

# Or even better: let uv manage everything
uv add rustkmer
```

### Advantages of uv
- **🚀 Speed**: 10-100x faster than pip
- **🎯 Simplicity**: Single tool for all Python project management
- **📦 Projects**: Built-in project management with pyproject.toml
- **🔄 Caching**: Smart caching for repeatable builds
- **🐍 Modern**: Designed for modern Python workflows

---

## 🎉 Next Steps

Now that you have RustKmer installed in a virtual environment:

1. **[First Steps](first-steps.md)** - Learn basic k-mer operations
2. **[User Guide](../user-guide/)** - Explore advanced features
3. **[API Reference](../api-reference/)** - Detailed Python API documentation
4. **[Examples](../tutorials/)** - Practical examples and workflows

Happy k-mer counting! 🧬✨