# Troubleshooting

Common issues and solutions for RustKmer installation and usage.

## Installation Issues

### Python Package Installation Problems

#### Problem: `pip install rustkmer` fails
**Error Messages:**
```
ERROR: Could not build wheels for rustkmer, which is required to install pyproject.toml-based projects
```

**Solutions:**

1. **Install Rust toolchain first:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
pip install rustkmer
```

2. **Update pip and setuptools:**
```bash
pip install --upgrade pip setuptools wheel
pip install rustkmer
```

3. **Install from source:**
```bash
git clone https://github.com/rustkmer/rustkmer.git
cd rustkmer
pip install -e .
```

#### Problem: ImportError on import
**Error Message:**
```
ImportError: cannot import name 'KmerCounter' from 'rustkmer'
```

**Solutions:**

1. **Check installation:**
```bash
python -c "import rustkmer; print('✅ Installation OK')"
```

2. **Reinstall with verbose output:**
```bash
pip uninstall rustkmer -y
pip install rustkmer --verbose
```

3. **Check Python version compatibility:**
```bash
python --version  # Should be 3.8+
```

### CLI Installation Problems

#### Problem: Command not found after installation
**Error Message:**
```
bash: rustkmer: command not found
```

**Solutions:**

1. **Check if Python package is installed:**
```bash
python -m rustkmer --help
```

2. **Install via cargo (alternative method):**
```bash
cargo install rustkmer
```

3. **Add Python user scripts to PATH:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Runtime Issues

### Memory Issues

#### Problem: Out of memory errors
**Error Messages:**
```
MemoryError: Unable to allocate array
Killed: 9 (out of memory)
```

**Solutions:**

1. **Use smaller k-mer size:**
```python
# Instead of k=31, use k=21 or k=13
counter = PyCounter(13, canonical=True)
```

2. **Process files in chunks:**
```python
counter.add_from_fasta("large_file.fa", chunk_size=1000000)
```

3. **Use streaming mode:**
```python
with open("large_file.fa", "r") as f:
    counter.count_stream(f)
```

4. **Monitor memory usage:**
```python
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory usage: {process.memory_info().rss / (1024**2):.1f} MB")
```

### File I/O Issues

#### Problem: File not found errors
**Error Messages:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'input.fa'
SequenceError: File not found: input.fa
```

**Solutions:**

1. **Check file exists:**
```python
import os
if not os.path.exists("input.fa"):
    print("❌ File not found!")
else:
    print("✅ File exists")
```

2. **Use absolute paths:**
```python
import os
file_path = os.path.abspath("input.fa")
counter.add_from_fasta(file_path)
```

3. **Check file permissions:**
```bash
ls -la input.fa
chmod 644 input.fa  # if needed
```

#### Problem: Corrupted or invalid FASTA/FASTQ files
**Error Messages:**
```
ParseError: Invalid FASTA format
SequenceError: Invalid nucleotide sequence
```

**Solutions:**

1. **Validate file format:**
```python
from pyrustkmer import KmerCounter, LoadMode

try:
    counter = PyCounter()
    counter.add_from_fasta("suspicious_file.fa")
    print("✅ File format is valid")
except Exception as e:
    print(f"❌ File format error: {e}")
```

2. **Check file encoding:**
```bash
file input.fa
# Should show: ASCII text or UTF-8 Unicode text
```

3. **Manual inspection:**
```bash
head -10 input.fa
# Look for proper FASTA headers (>seq_name) and valid nucleotides (ATCGN)
```

### Database Issues

#### Problem: Database load errors
**Error Messages:**
```
DatabaseError: Invalid database format
IOError: Cannot read database file
```

**Solutions:**

1. **Check database file exists and is readable:**
```python
import os
db_file = "database.rkdb"

if os.path.exists(db_file):
    if os.access(db_file, os.R_OK):
        print("✅ Database file is readable")
    else:
        print("❌ No read permissions")
else:
    print("❌ Database file not found")
```

2. **Verify database was created correctly:**
```python
from pyrustkmer import KmerCounter, LoadMode

# Recreate database if needed
counter = PyCounter(21, canonical=True)
counter.add_from_fasta("input.fa")
counter.save_database("database.rkdb")
```

3. **Check database integrity:**
```python
from pyrustkmer import Database, LoadMode

try:
    db = PyDatabase("database.rkdb", LoadMode.Preload)
    db.load("database.rkdb", False)
    stats = db.get_stats()
    print(f"✅ Database loaded: {stats.kmer_size}-mer, {stats.total_kmers} k-mers")
except Exception as e:
    print(f"❌ Database error: {e}")
```

#### Problem: Query returns no results
**Symptom:** All k-mers return `found: False`

**Solutions:**

1. **Check if k-mer size matches database:**
```python
db = PyDatabase("database.rkdb", LoadMode.Preload)
db.load("database.rkdb", False)
print(f"Database k-mer size: {db.get_kmer_size()}")

# Use correct k-mer size
kmer_size = db.get_kmer_size()
test_kmer = "ATCG" * (kmer_size // 4) + "ATCG"[:kmer_size % 4]
result = db.query_exact(test_kmer)
```

2. **Verify database has content:**
```python
stats = db.get_stats()
if stats.total_kmers == 0:
    print("❌ Empty database - recreate from source file")
else:
    print(f"✅ Database contains {stats.total_kmers} k-mers")
```

3. **Check k-mer format (uppercase only):**
```python
test_kmer = "atcgatcgatcgatcgatcg"  # Wrong case
test_kmer = test_kmer.upper()  # Correct
result = db.query_exact(test_kmer)
```

### Performance Issues

#### Problem: Slow processing speed
**Symptoms:**
- Counting takes very long time
- Memory usage keeps increasing
- High CPU usage with no progress

**Solutions:**

1. **Use appropriate k-mer size:**
```python
# Faster but less specific (k=13)
counter = PyCounter(13, canonical=True)

# Balanced (k=21, recommended default)
counter = PyCounter(21, canonical=True)

# Slower but more specific (k=31)
counter = PyCounter(31, canonical=True)
```

2. **Optimize thread count:**
```python
import multiprocessing

# Use available CPU cores
threads = multiprocessing.cpu_count()
counter = PyCounter(21, threads=threads)
```

3. **Enable canonical mode for genomes:**
```python
# Reduces database size ~2x for genomic data
counter = PyCounter(21, canonical=True)
```

4. **Use uncompressed files for speed:**
```bash
# Faster but uses more disk space
gunzip input.fa.gz
rustkmer count -i input.fa -o output.rkdb
```

### Fuzzy Search Issues

#### Problem: Fuzzy query not working
**Error Messages:**
```
AttributeError: 'Database' object has no attribute 'fuzzy_query'
```

**Solution:**
```python
# Fuzzy search is planned but not yet implemented
# Use exact queries for now:

db = PyDatabase("database.rkdb", LoadMode.Preload)
db.load("database.rkdb", False)

# Instead of fuzzy_query, try multiple exact queries:
possible_variants = [
    "ATCGATCGATCGATCGATCG",
    "ATCGATCGATCGATCGATCC",  # 1 substitution
    "ATCGATCGATCGATCGATCT",  # 1 substitution
]

results = []
for variant in possible_variants:
    result = db.query_exact(variant)
    if result.found:
        results.append((variant, result.count))

print(f"Found {len(results)} similar sequences")
```

## Platform-Specific Issues

### macOS

#### Problem: Permission denied errors
**Solutions:**
```bash
# Give Python permission to access files
xattr -d com.apple.quarantine $(which python3)

# Or run from allowed directory
cd ~/Documents
rustkmer count -i input.fa -o output.rkdb
```

#### Problem: M1/M2 Mac compatibility
**Solutions:**
```bash
# Ensure Rosetta is installed for Intel binaries
softwareupdate --install-rosetta --agree-to-license

# Use arm64-optimized Python
python3 --version  # Should show arm64
```

### Linux

#### Problem: Missing system dependencies
**Solutions:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential python3-dev

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

#### Problem: Limited memory on small systems
**Solutions:**
```python
# For systems with < 4GB RAM
counter = PyCounter(13, canonical=True)  # Use smaller k

# Process in very small chunks
counter.add_from_fasta("large_file.fa", chunk_size=100000)

# Use disk-based processing when possible
```

### Windows

#### Problem: Path separators
**Solutions:**
```python
import os

# Use os.path.join for cross-platform compatibility
input_file = os.path.join("data", "input.fa")
output_file = os.path.join("data", "output.rkdb")

counter.add_from_fasta(input_file)
counter.save_database(output_file)
```

#### Problem: Long file names
**Solutions:**
```python
# Use shorter file names or relative paths
import os

# Enable long path support (Windows 10+)
import ctypes
kernel32 = ctypes.windll.kernel32
kernel32.SetDllDirectoryW(None)
```

## Debugging Tips

### Enable Verbose Output

**Python:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

counter = PyCounter(21, canonical=True)
counter.add_from_fasta("input.fa")  # Will show debug info
```

**CLI:**
```bash
rustkmer count -i input.fa -o output.rkdb --verbose
```

### Check Versions

```python
import rustkmer
import sys
import platform

print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"RustKmer version: {rustkmer.__version__ if hasattr(rustkmer, '__version__') else 'unknown'}")
```

### Test with Small Examples

```python
# Create minimal test case
test_sequence = "ATCGATCGATCGATCGATCG"

with open("test.fa", "w") as f:
    f.write(">test\n")
    f.write(test_sequence + "\n")

# Test basic functionality
counter = PyCounter(21)
counter.add_from_fasta("test.fa")
print(f"✅ Basic test: {counter.get_stats().total_kmers)} k-mers")
```

## Getting Help

If you're still experiencing issues:

### 1. Check the Documentation
- [Installation Guide](installation.md)
- [User Guide](../user-guide/)
- [API Reference](../api-reference/)

### 2. Search Existing Issues
- [GitHub Issues](https://github.com/rustkmer/rustkmer/issues)

### 3. Ask for Help
- [GitHub Discussions](https://github.com/rustkmer/rustkmer/discussions)
- [Community Forum](https://github.com/rustkmer/rustkmer/discussions)

### 4. Report a Bug
When reporting bugs, include:
1. **System information:** OS, Python version, RustKmer version
2. **Error message:** Full traceback or error output
3. **Minimal example:** Code that reproduces the issue
4. **Input files:** Small test files that show the problem
5. **Expected vs actual behavior:** What you expected vs what happened

### Example Bug Report Template

```markdown
## System Information
- OS: Ubuntu 22.04
- Python: 3.9.7
- RustKmer: 0.1.0

## Issue Description
Counting large FASTA files fails with memory error

## Error Message
```
MemoryError: Unable to allocate array
```

## Minimal Example
```python
from pyrustkmer import KmerCounter, LoadMode
counter = PyCounter(31)
counter.add_from_fasta("large_file.fa")  # 10GB file
```

## Expected Behavior
Should count k-mers without running out of memory

## Actual Behavior
Crashes with MemoryError after processing 2GB
```

---

Remember: Most issues can be resolved by using smaller k-mer sizes, processing files in chunks, or ensuring sufficient system resources are available.