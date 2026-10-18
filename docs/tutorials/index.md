<!-- generated-by: gsd-doc-writer -->
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

All tutorials live in this directory:

| Tutorial | Difficulty | Time Required | Prerequisites |
|----------|------------|---------------|----------------|
| **[Basic Workflow](basic-workflow.md)** | Beginner | 15 minutes | Basic Python/CLI knowledge |
| **[Batch Processing](batch-processing.md)** | Intermediate | 20 minutes | High-throughput workflows |
| **[Integration](integration.md)** | Intermediate | 30 minutes | Python programming, file handling |
| **[Large Genomes](large-genomes.md)** | Advanced | 45 minutes | Memory management, bioinformatics |

### Further Reading by Topic

The topics below are covered by the user guide, examples, and guides rather than standalone tutorials:

| Topic | Where to Read |
|-------|---------------|
| Performance tuning | [Performance Tips](../user-guide/performance-tips.md) |
| Fuzzy / pattern search | [Fuzzy Search Guide](../user-guide/fuzzy-search.md), [Hybrid Search Guide](../guides/hybrid-search-guide.md) |
| Prefix queries | [Prefix Query Guide](../guides/prefix-query-guide.md) |
| Worked code examples | [Examples](../examples/basic-usage.md) (batch processing, merging, fuzzy search, statistics) |
| Python binding internals | [PyO3 Binding Guide](../guides/pyo3-binding-guide.md) |
| CLI usage | [CLI Guide](../user-guide/cli.md) |

---

## Tutorial Features

Each RustKmer tutorial includes:

### Complete Code Examples
- Working Python scripts and shell commands
- Real data files and expected outputs
- Error handling and troubleshooting

### Performance Metrics
- Execution time benchmarks
- Memory usage analysis
- Comparison with other tools

### Practical Applications
- Real bioinformatics workflows
- Industry-standard practices
- Scalable solutions

### Step-by-Step Guidance
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
1. **[Basic Workflow](basic-workflow.md)** - Core counting and querying
2. **[Batch Processing](batch-processing.md)** - Multi-sample analysis
3. **[Fuzzy Search Guide](../user-guide/fuzzy-search.md)** - Pattern matching applications

### For Software Developers
1. **[Integration](integration.md)** - API integration patterns
2. **[Large Genomes](large-genomes.md)** - Resource optimization
3. **[Batch Processing](batch-processing.md)** - Production workflows

---

## Prerequisites

### Basic Requirements
- **Python 3.11+** (for the `pyrustkmer` package) or **Rust 1.80+** (for the CLI)
- **Command line familiarity**
- **Basic genomic data understanding** (FASTA/FASTQ)

### For Advanced Tutorials
- **Python programming** (intermediate level)
- **Bioinformatics concepts** (optional, helpful)
- **Large dataset handling** (recommended)

### Software Dependencies
```bash
# Python
pip install pyrustkmer matplotlib pandas numpy

# Optional for advanced tutorials
pip install biopython pysam

# Rust CLI (build from source)
cargo install --path .
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
cd rustkmer

# Save the code block you want to run from a tutorial page into a .py file,
# then execute it
python3 basic_workflow.py
```

The tutorial pages present their examples as named scripts (for example `complete_workflow.py` in the [Basic Workflow tutorial](basic-workflow.md)). Copy each block into the named file and run it — the tutorials do not ship separate script files.

### Interactive Jupyter
```bash
# Install Jupyter support
pip install jupyter

# Start notebook server
jupyter notebook
```

The [Integration tutorial](integration.md) includes a notebook-style walkthrough using `# %%` cell markers.

---

## Expected Outcomes

After completing these tutorials, you'll be able to:

### Core Skills
- **Count k-mers** from genomic data efficiently
- **Query databases** with exact and fuzzy searches
- **Process large datasets** with memory optimization
- **Integrate RustKmer** into existing workflows

### Advanced Capabilities
- **Design experiments** with appropriate parameters
- **Optimize performance** for specific use cases
- **Handle errors** and edge cases gracefully
- **Scale solutions** for production use

### Bioinformatics Applications
- **Analyze genomes** for research projects
- **Process sequencing data** from various platforms
- **Compare k-mer content** across samples
- **Build reproducible pipelines** with Snakemake or Nextflow

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

**New to RustKmer?** → [Basic Workflow](basic-workflow.md)

**Bioinformatics researcher?** → [Batch Processing](batch-processing.md)

**Software developer?** → [Integration](integration.md)

**Looking for performance?** → [Large Genomes](large-genomes.md)

---

## Need Help?

- **Documentation**: [Getting Started](../getting-started/) for basics
- **API Reference**: [Python API](../api-reference/python/) for complete reference
- **Community**: [GitHub Discussions](https://github.com/rustkmer/rustkmer/discussions) for questions
- **Issues**: [GitHub Issues](https://github.com/rustkmer/rustkmer/issues) for bugs
