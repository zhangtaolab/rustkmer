# Tutorials

Step-by-step tutorials for common RustKmer workflows and use cases, from basic operations to advanced bioinformatics applications.

## Tutorial Overview

These tutorials guide you through practical applications of RustKmer with real-world examples and complete code solutions.

### Getting Started

If you're new to RustKmer, start with these foundational tutorials:

1. **[First Steps](../getting-started/first-steps.md)** - Your first k-mer counting operations
2. **[Basic Workflow](basic-workflow.md)** - Complete end-to-end example
3. **[Installation](../getting-started/installation.md)** - Setup RustKmer on your system

---

## Available Tutorials

### 🎯 Essential Tutorials

| Tutorial | Difficulty | Time Required | Prerequisites |
|----------|------------|---------------|----------------|
| **[Basic Workflow](basic-workflow.md)** | Beginner | 15 minutes | Basic Python/CLI knowledge |
| **[Integration](integration.md)** | Intermediate | 30 minutes | Python programming, file handling |
| **[Large Genomes](large-genomes.md)** | Advanced | 45 minutes | Memory management, bioinformatics |

### 🧬 Bioinformatics Applications

| Tutorial | Difficulty | Time Required | Use Case |
|----------|------------|---------------|----------|
| **[Metagenomics Classification](metagenomics.md)** | Intermediate | 30 minutes | Species identification |
| **[Variant Detection](variant-detection.md)** | Advanced | 60 minutes | SNP/indel finding |
| **[Assembly Support](assembly-support.md)** | Advanced | 45 minutes | Genome assembly validation |

### 🔧 Performance & Optimization

| Tutorial | Difficulty | Time Required | Focus |
|----------|------------|---------------|--------|
| **[Performance Tuning](performance-tuning.md)** | Intermediate | 25 minutes | Speed optimization |
| **[Memory Management](memory-management.md)** | Advanced | 35 minutes | Large dataset handling |
| **[Batch Processing](batch-processing.md)** | Intermediate | 20 minutes | High-throughput workflows |

---

## Tutorial Features

Each RustKmer tutorial includes:

### ✅ Complete Code Examples
- Working Python scripts and shell commands
- Real data files and expected outputs
- Error handling and troubleshooting

### 📊 Performance Metrics
- Execution time benchmarks
- Memory usage analysis
- Comparison with other tools

### 🎯 Practical Applications
- Real bioinformatics workflows
- Industry-standard practices
- Scalable solutions

### 🔧 Step-by-Step Guidance
- Detailed explanations
- Common pitfalls and solutions
- Best practices and tips

---

## Learning Path

### For Beginners
1. **[First Steps](../getting-started/first-steps.md)** - Understand basic concepts
2. **[Basic Workflow](basic-workflow.md)** - Complete a practical project
3. **[Integration](integration.md)** - Connect to existing workflows

### For Bioinformatics Researchers
1. **[Performance Tuning](performance-tuning.md)** - Optimize for large datasets
2. **[Metagenomics Classification](metagenomics.md)** - Species identification
3. **[Variant Detection](variant-detection.md)** - Find genetic variations

### For Software Developers
1. **[Integration](integration.md)** - API integration patterns
2. **[Memory Management](memory-management.md)** - Resource optimization
3. **[Batch Processing](batch-processing.md)** - Production workflows

---

## Prerequisites

### Basic Requirements
- **Python 3.8+** or **Rust 1.80+**
- **Command line familiarity**
- **Basic genomic data understanding** (FASTA/FASTQ)

### For Advanced Tutorials
- **Python programming** (intermediate level)
- **Bioinformatics concepts** (optional, helpful)
- **Large dataset handling** (recommended)

### Software Dependencies
```bash
# Python
pip install rustkmer matplotlib pandas numpy

# Optional for advanced tutorials
pip install biopython pysam

# Rust (if using Rust API)
cargo install rustkmer
```

---

## Tutorial Data

Most tutorials use sample data files that can be created easily:

```bash
# Create sample FASTA file
cat > sample.fa << 'EOF'
>sample_sequence_1
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
>sample_sequence_2
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
EOF

# Create sample query file
echo -e "ATCGATCGATCGATCGATCG\nGCTAGCTAGCTAGCTAGCTAGCTA\nTTTTTTTTTTTTTTTTTTTTT" > queries.txt
```

For tutorials requiring real genomic data:
- **Small test datasets** (<10MB) are included
- **Large datasets** are optional with download links
- **Cloud datasets** are available for select tutorials

---

## Running Tutorials

### Local Environment
```bash
# Clone repository
git clone https://github.com/rustkmer/rustkmer.git
cd rustkmer/docs/tutorials

# Run tutorial script
python3 basic-workflow.py
```

### Docker Environment
```bash
# Use official RustKmer image
docker run -it --rm -v $(pwd):/workspace rustkmer/rustkmer:latest
cd /workspace/docs/tutorials

# Run tutorials
python3 basic-workflow.py
```

### Interactive Jupyter
```bash
# Install Jupyter support
pip install jupyter

# Start notebook server
jupyter notebook

# Open tutorial notebooks
```

---

## Expected Outcomes

After completing these tutorials, you'll be able to:

### ✅ Core Skills
- **Count k-mers** from genomic data efficiently
- **Query databases** with exact and fuzzy searches
- **Process large datasets** with memory optimization
- **Integrate RustKmer** into existing workflows

### 🎯 Advanced Capabilities
- **Design experiments** with appropriate parameters
- **Optimize performance** for specific use cases
- **Handle errors** and edge cases gracefully
- **Scale solutions** for production use

### 🔬 Bioinformatics Applications
- **Analyze genomes** for research projects
- **Process sequencing data** from various platforms
- **Detect variants** and genetic differences
- **Classify metagenomic** samples

---

## Getting Help

### Tutorial Support
- **GitHub Issues**: Report bugs in tutorial code
- **Discussions**: Ask questions and share results
- **Examples**: Check the [Python API examples](../api-reference/python/examples.md)

### Additional Resources
- **[API Reference](../api-reference/)** - Complete function documentation
- **[User Guide](../user-guide/)** - Comprehensive usage guide
- **[Performance Tips](../user-guide/performance-tips.md)** - Optimization strategies

---

## Contributing

Help improve RustKmer tutorials!

### Tutorial Contributions
- **New tutorials** for additional use cases
- **Improvements** to existing content
- **Bug fixes** and error corrections
- **Performance updates** and benchmarks

### Contribution Guidelines
1. **Test thoroughly** with multiple datasets
2. **Include prerequisites** and expected outputs
3. **Document edge cases** and error handling
4. **Follow existing style** and format patterns

---

## Ready to Start?

Choose your first tutorial based on your experience level:

🚀 **New to RustKmer?** → [Basic Workflow](basic-workflow.md)

🧬 **Bioinformatics researcher?** → [Metagenomics Classification](metagenomics.md)

⚙️ **Software developer?** → [Integration](integration.md)

🎯 **Looking for performance?** → [Performance Tuning](performance-tuning.md)

---

## Need Help?

- **Documentation**: [Getting Started](../getting-started/) for basics
- **API Reference**: [Python API](../api-reference/python/) for complete reference
- **Community**: [GitHub Discussions](https://github.com/rustkmer/rustkmer/discussions) for questions
- **Issues**: [GitHub Issues](https://github.com/rustkmer/rustkmer/issues) for bugs