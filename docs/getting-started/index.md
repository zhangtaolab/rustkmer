# Getting Started

Welcome to RustKmer! This section will help you get up and running quickly with k-mer counting and genomic analysis.

## Quick Navigation

- **[Installation](installation.md)** - How to install RustKmer on your system
- **[First Steps](first-steps.md)** - Your first k-mer counting and querying operations

## Why RustKmer?

RustKmer delivers world-class performance for genomic analysis:

| Feature | Performance | Benefits |
|---------|-------------|----------|
| **Query Speed** | 3,986,981 queries/sec | Process millions of queries instantly |
| **Memory Usage** | <2MB overhead | Work with massive datasets efficiently |
| **Python Integration** | Native bindings | Seamless bioinformatics workflow integration |
| **Cross-Platform** | Linux, macOS, Windows | Deploy anywhere |

## What You'll Learn

In this section, you'll:

1. **Install** RustKmer using your preferred method
2. **Count** your first k-mers from genomic data
3. **Query** k-mer databases with exact and fuzzy searches
4. **Integrate** RustKmer into your existing workflows

## Before You Begin

- **System Requirements**: Python 3.8+ or Rust 1.80+
- **Data Format**: FASTA/FASTQ files (compressed supported)
- **Memory**: 4GB+ RAM recommended for large genomes
- **Storage**: Additional space for database files

## Choose Your Path

!!! example "New to k-mer counting?"
    Start with the [First Steps](first-steps.md) guide for a complete walkthrough.

!!! example "Integrating into existing workflow?"
    Jump to the [User Guide](../user-guide/) for advanced usage patterns.

!!! example "Need performance optimization?"
    Check the [Performance Tips](../user-guide/performance-tips.md) guide for optimization strategies.

## Ready to Start?

Choose your installation method below and begin your RustKmer journey!

```bash
# Quick test with Python (after installation)
python -c "from pyrustkmer import PyCounter; print('RustKmer ready! 🚀')"
```

Let's get started with [Installation](installation.md)!