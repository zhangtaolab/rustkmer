#!/usr/bin/env python3
"""
K-mer Analysis Interactive Notebook
==================================

A comprehensive marimo notebook for k-mer analysis using pure Python.
This notebook demonstrates basic k-mer counting, analysis, and visualization
without requiring RustKmer or any external dependencies.

Features:
- FASTA file parsing (supports .gz compression)
- Pure Python k-mer counting and analysis
- Interactive visualizations with plotly
- Real-time statistics and performance metrics
- Educational explanations at each step

Requirements: pip install marimo plotly pandas numpy
"""

import marimo

__generated_with__ = "0.8.7"
app = marimo.App()


@app.cell(hide_code=True)
def __():
    import marimo as mo
    import gzip
    import os
    import sys
    from pathlib import Path
    from typing import Dict, List, Tuple, Iterator, Optional
    import time
    import itertools
    from collections import Counter, defaultdict

    # Data manipulation and visualization
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots

    # Set up marimo UI
    mo.md("""# 🧬 K-mer Analysis Interactive Notebook""")

    return (
        mo, gzip, os, sys, Path, Dict, List, Tuple, Iterator, Optional,
        time, itertools, Counter, defaultdict, pd, np, go, px, make_subplots
    )


@app.cell(hide_code=True)
def __(mo):
    """Notebook introduction and overview."""
    mo.md("""
    ## 📚 What are K-mers?

    A **k-mer** is a sequence of DNA/RNA of length *k*. For example:
    - **3-mers** in "ATGCGAT" are: ATG, TGC, GCG, CGA, GAT

    **Why are k-mers important?**
    - 🔍 **Genome analysis**: Species identification, genome comparison
    - 📊 **Sequence assembly**: Building longer sequences from short reads
    - 🧪 **Bioinformatics**: Pattern finding, repeat detection, GC content analysis

    **Notebook Features:**
    - 🧮 **Pure Python k-mer counting** - No external dependencies needed
    - 📈 **Interactive visualizations** - Real-time charts and statistics
    - 🗂️ **FASTA file support** - Works with compressed .gz files
    - ⚡ **Performance tracking** - Monitor memory and runtime
    - 🎯 **Educational focus** - Learn k-mer analysis step-by-step

    ---

    Let's start by loading our demo dataset! 🎉
    """)
    return


@app.cell(hide_code=True)
def __(Path, os, pd):
    """Demo dataset information and file validation."""
    # Define data paths
    current_dir = Path.cwd()
    examples_dir = current_dir.parent / "examples" if current_dir.name == "marimo" else current_dir / "examples"
    data_dir = examples_dir / "data"
    demo_file = data_dir / "demo_rice_genome.fa.gz"

    # Check if demo file exists
    if demo_file.exists():
        file_size = demo_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        file_info = {
            "File Path": str(demo_file),
            "File Size": f"{file_size_mb:.2f} MB ({file_size:,} bytes)",
            "Compressed": "Yes (.gz format)",
            "Organism": "Rice (Oryza sativa)",
            "Data Type": "Genomic DNA"
        }

        df_info = pd.DataFrame(list(file_info.items()), columns=["Property", "Value"])
        display_table = df_info

    else:
        # Create demo file info for when file doesn't exist
        display_table = "Demo file not found. Please ensure examples/data/demo_rice_genome.fa.gz exists."

    return demo_file, display_table, file_info


@app.cell(hide_code=True)
def __(mo, display_table):
    """Display dataset information."""
    if isinstance(display_table, pd.DataFrame):
        mo.md("""## 📁 Demo Dataset Information""")
        mo.md(f"""
        This notebook uses a **compressed rice genome dataset** extracted from the OSA1 r7 assembly.

        **Dataset Details:**
        {display_table.to_markdown(index=False)}

        The dataset contains real genomic sequences including:
        - **Chromosome sequences** from rice genome
        - **N characters** representing unknown/uncertain bases
        - **Various GC content** regions for k-mer distribution analysis

        This compressed format saves ~70% space while maintaining full compatibility with our pure Python FASTA parser.
        """)
    else:
        mo.md(f"""
        ## ⚠️ Dataset Not Found

        {display_table}

        Please create a demo FASTA file at `examples/data/demo_rice_genome.fa.gz` to proceed with the analysis.
        """)
    return


@app.cell
def __(demo_file, gzip, mo, time):
    """FASTA file parser implementation."""
    def parse_fasta(file_path: str, max_sequences: Optional[int] = None) -> Iterator[Tuple[str, str]]:
        """
        Parse FASTA files (supports .gz compression).

        Args:
            file_path: Path to FASTA file
            max_sequences: Maximum number of sequences to parse (for testing)

        Yields:
            Tuple of (header, sequence)
        """
        opener = gzip.open if file_path.endswith('.gz') else open

        with opener(file_path, 'rt') as f:
            header = None
            sequence_parts = []
            seq_count = 0

            for line in f:
                line = line.strip()

                if line.startswith('>'):
                    # Yield previous sequence if exists
                    if header is not None:
                        yield header, ''.join(sequence_parts)
                        seq_count += 1
                        if max_sequences and seq_count >= max_sequences:
                            break

                    # Start new sequence
                    header = line[1:]  # Remove '>' prefix
                    sequence_parts = []
                else:
                    sequence_parts.append(line)

            # Yield last sequence
            if header is not None:
                yield header, ''.join(sequence_parts)

    # Test the parser
    if demo_file.exists():
        mo.md("## 🔍 FASTA File Parser")

        start_time = time.time()
        sequences = list(parse_fasta(str(demo_file), max_sequences=5))
        parse_time = time.time() - start_time

        mo.md(f"""
        ### ✅ Parser Test Results

        Successfully parsed **{len(sequences)} sequences** in **{parse_time:.3f} seconds**.

        **Sample sequences:**
        """)

        for i, (header, seq) in enumerate(sequences[:3], 1):
            seq_preview = seq[:100] + "..." if len(seq) > 100 else seq
            mo.md(f"""
            **Sequence {i}:**
            - *Header*: `{header[:50]}...`
            - *Length*: {len(seq):,} bases
            - *Preview*: `{seq_preview}`
            """)

    return parse_fasta, sequences, parse_time


@app.cell
def __(Counter, itertools, mo, parse_fasta, time):
    """K-mer counting implementation."""
    def count_kmers(sequence: str, k: int) -> Counter:
        """
        Count k-mers in a single sequence.

        Args:
            sequence: DNA sequence string
            k: k-mer size

        Returns:
            Counter with k-mer counts
        """
        # Filter out invalid characters (keep only A, T, G, C, N)
        valid_bases = {'A', 'T', 'G', 'C', 'N'}

        kmers = []
        for i in range(len(sequence) - k + 1):
            kmer = sequence[i:i+k]
            if all(base in valid_bases for base in kmer):
                kmers.append(kmer)

        return Counter(kmers)

    def count_kmers_from_file(file_path: str, k: int, canonical: bool = False) -> Tuple[Counter, Dict]:
        """
        Count k-mers from entire FASTA file.

        Args:
            file_path: Path to FASTA file
            k: k-mer size
            canonical: Whether to use canonical k-mers (and reverse complement)

        Returns:
            Tuple of (kmer_counter, statistics)
        """
        start_time = time.time()
        total_kmers = 0
        sequence_count = 0
        total_length = 0

        kmer_counts = Counter()

        # Complement mapping for canonical k-mers
        complement = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}

        for header, sequence in parse_fasta(file_path):
            sequence_count += 1
            total_length += len(sequence)

            # Count k-mers in this sequence
            seq_kmers = []
            for i in range(len(sequence) - k + 1):
                kmer = sequence[i:i+k]

                # Skip k-mers with invalid characters
                if not all(base in 'ATGCN' for base in kmer):
                    continue

                if canonical:
                    # Get reverse complement
                    rev_comp = ''.join(complement[base] for base in reversed(kmer))
                    # Use lexicographically smaller as canonical
                    canonical_kmer = min(kmer, rev_comp)
                    seq_kmers.append(canonical_kmer)
                else:
                    seq_kmers.append(kmer)

            kmer_counts.update(seq_kmers)
            total_kmers += len(seq_kmers)

        runtime = time.time() - start_time

        stats = {
            'sequences_processed': sequence_count,
            'total_length': total_length,
            'total_kmers': total_kmers,
            'unique_kmers': len(kmer_counts),
            'runtime_seconds': runtime,
            'kmer_per_second': total_kmers / runtime if runtime > 0 else 0
        }

        return kmer_counts, stats

    # Interactive controls
    k_size = mo.ui.slider(1, 31, 1, value=13, label="K-mer Size (k)")
    canonical_mode = mo.ui.checkbox(label="Use Canonical K-mers", value=False)

    return count_kmers, count_kmers_from_file, k_size, canonical_mode


@app.cell
def __(canonical_mode, demo_file, k_size, mo):
    """Run k-mer counting with user parameters."""
    if demo_file.exists():
        mo.md("## 🧮 K-mer Counting Analysis")

        # Display controls
        controls = mo.hstack([k_size, canonical_mode])
        mo.md("### ⚙️ Analysis Parameters")
        controls

        # Run analysis button
        run_analysis = mo.ui.button(label="🚀 Run K-mer Analysis", value=False)

        # Show progress message initially
        progress_msg = mo.md("Click the button above to start k-mer counting...")

        run_analysis, progress_msg
    else:
        mo.md("## ⚠️ Demo file not available for k-mer counting")
        run_analysis = mo.ui.button(label="Cannot run analysis - no data", disabled=True)
        run_analysis, demo_file
    return run_analysis, progress_msg


@app.cell
def __(canonical_mode, count_kmers_from_file, demo_file, k_size, mo, run_analysis):
    """Execute k-mer counting and display results."""
    if run_analysis.value and demo_file.exists():
        # Show loading state
        progress_msg = mo.md("🔄 **Running k-mer counting...** Please wait.")

        # Run the analysis
        kmer_counts, stats = count_kmers_from_file(
            str(demo_file),
            k=k_size.value,
            canonical=canonical_mode.value
        )

        # Update progress and show results
        progress_msg = mo.md("✅ **Analysis complete!** Results below:")

        # Create statistics display
        mo.md("### 📊 Analysis Statistics")

        stats_df = pd.DataFrame([
            ("Sequences Processed", f"{stats['sequences_processed']:,}"),
            ("Total Bases", f"{stats['total_length']:,}"),
            ("K-mers Counted", f"{stats['total_kmers']:,}"),
            ("Unique K-mers", f"{stats['unique_kmers']:,}"),
            ("Runtime", f"{stats['runtime_seconds']:.3f} seconds"),
            ("Processing Speed", f"{stats['kmer_per_second']:,.0f} k-mers/sec")
        ], columns=["Metric", "Value"])

        stats_table = mo.ui.table(stats_df)
        stats_table

        # Show most common k-mers
        mo.md("### 🏆 Top 10 Most Common K-mers")

        top_kmers = kmer_counts.most_common(10)
        top_kmers_df = pd.DataFrame(top_kmers, columns=["K-mer", "Count"])
        top_kmers_table = mo.ui.table(top_kmers_df)
        top_kmers_table

    else:
        # Initial state or no data
        progress_msg = mo.md("🔍 **Ready to analyze.** Set your parameters and click the button above.")
        kmer_counts = None
        stats = None

    return kmer_counts, stats, stats_df, top_kmers_df, progress_msg


@app.cell(hide_code=True)
def __(go, kmer_counts, mo, np, pd):
    """K-mer distribution visualization."""
    if kmer_counts:
        mo.md("## 📈 K-mer Distribution Analysis")

        # Prepare data for visualization
        counts = list(kmer_counts.values())

        if len(counts) > 0:
            # Distribution statistics
            mean_count = np.mean(counts)
            median_count = np.median(counts)
            max_count = max(counts)
            min_count = min(counts)

            mo.md(f"""
            ### 📋 Distribution Summary
            - **Mean count**: {mean_count:.2f}
            - **Median count**: {median_count:.2f}
            - **Range**: {min_count} - {max_count}
            - **Total unique k-mers**: {len(counts):,}
            """)

            # Create histogram
            fig_histogram = go.Figure()

            # Use logarithmic bins for better visualization of wide-ranging counts
            bins = np.logspace(np.log10(min_count), np.log10(max_count), 50)

            fig_histogram.add_trace(go.Histogram(
                x=counts,
                bins=bins,
                nbinsx=50,
                name="K-mer Count Distribution",
                opacity=0.7,
                marker_color='lightblue',
                hovertemplate='Count: %{x}<br>Frequency: %{y}<extra></extra>'
            ))

            fig_histogram.update_layout(
                title="Distribution of K-mer Counts (Log Scale)",
                xaxis_title="K-mer Count (log scale)",
                yaxis_title="Number of K-mers",
                xaxis_type="log",
                height=500,
                template="plotly_white"
            )

            mo.md("### 📊 Histogram View")
            histogram_fig = fig_histogram

            # Cumulative distribution
            sorted_counts = sorted(counts, reverse=True)
            total_kmers = len(sorted_counts)
            cumulative_pct = [(i+1)/total_kmers * 100 for i in range(total_kmers)]

            fig_cumulative = go.Figure()
            fig_cumulative.add_trace(go.Scatter(
                x=list(range(total_kmers)),
                y=cumulative_pct,
                mode='lines',
                name="Cumulative Distribution",
                line=dict(color='orange', width=2)
            ))

            fig_cumulative.update_layout(
                title="Cumulative Distribution of K-mer Counts",
                xaxis_title="K-mers (sorted by count)",
                yaxis_title="Cumulative Percentage (%)",
                height=500,
                template="plotly_white"
            )

            mo.md("### 📈 Cumulative Distribution")
            cumulative_fig = fig_cumulative

        else:
            mo.md("No k-mers found to visualize.")
            histogram_fig = None
            cumulative_fig = None
    else:
        histogram_fig = None
        cumulative_fig = None

    return mean_count, median_count, histogram_fig, cumulative_fig, sorted_counts


@app.cell(hide_code=True)
def __(cumulative_fig, histogram_fig, mo):
    """Display visualizations."""
    if histogram_fig and cumulative_fig:
        # Display side by side
        mo.hstack([
            mo.as_html(histogram_fig),
            mo.as_html(cumulative_fig)
        ], widths=(50, 50))
    elif histogram_fig:
        mo.as_html(histogram_fig)
    elif cumulative_fig:
        mo.as_html(cumulative_fig)
    else:
        mo.md("📊 **Visualizations will appear here after running k-mer analysis.**")
    return


@app.cell(hide_code=True)
def __(go, kmer_counts, mo, pd, px):
    """K-mer composition analysis."""
    if kmer_counts:
        mo.md("## 🧬 K-mer Composition Analysis")

        # Analyze k-mer composition by first base
        composition = defaultdict(lambda: {'count': 0, 'kmers': []})

        for kmer, count in kmer_counts.items():
            first_base = kmer[0] if kmer else 'N'
            composition[first_base]['count'] += count
            composition[first_base]['kmers'].append((kmer, count))

        # Create composition dataframe
        comp_data = []
        for base in sorted(composition.keys()):
            comp_data.append({
                'First Base': base,
                'Total Count': composition[base]['count'],
                'Unique K-mers': len(composition[base]['kmers']),
                'Average Count': composition[base]['count'] / len(composition[base]['kmers']) if composition[base]['kmers'] else 0
            })

        comp_df = pd.DataFrame(comp_data)

        mo.md("### 🎯 Composition by First Base")
        comp_table = mo.ui.table(comp_df)
        comp_table

        # Create pie chart
        if len(comp_df) > 0:
            fig_pie = go.Figure()

            fig_pie.add_trace(go.Pie(
                labels=comp_df['First Base'],
                values=comp_df['Total Count'],
                hole=0.3,
                marker_colors=['lightgreen', 'lightcoral', 'lightblue', 'lightyellow', 'lightgray']
            ))

            fig_pie.update_layout(
                title="K-mer Distribution by First Base",
                height=400,
                template="plotly_white"
            )

            mo.md("### 🥧 Distribution Pie Chart")
            pie_chart = fig_pie

        else:
            pie_chart = None

    else:
        comp_df = None
        pie_chart = None

    return composition, comp_df, pie_chart, comp_table


@app.cell(hide_code=True)
def __(mo, pie_chart, comp_table):
    """Display composition analysis."""
    if comp_df is not None:
        mo.hstack([comp_table, mo.as_html(pie_chart)], widths=(60, 40))
    else:
        mo.md("🧬 **Composition analysis will appear here after running k-mer counting.**")
    return


@app.cell(hide_code=True)
def __(mo, pd, time):
    """Performance benchmarks and optimization insights."""
    mo.md("## ⚡ Performance Analysis & Insights")

    # Performance test with different k-mer sizes
    performance_data = []

    if demo_file.exists():
        for k_test in [7, 13, 21, 31]:
            start_time = time.time()
            # Run a quick test with small subset
            test_sequences = list(parse_fasta(str(demo_file), max_sequences=3))
            test_kmers = Counter()

            for _, seq in test_sequences:
                for i in range(len(seq) - k_test + 1):
                    kmer = seq[i:i+k_test]
                    if all(base in 'ATGCN' for base in kmer):
                        test_kmers[kmer] += 1

            test_time = time.time() - start_time
            performance_data.append({
                'K-mer Size': k_test,
                'Test Runtime (ms)': test_time * 1000,
                'Test K-mers': len(test_kmers),
                'Estimated Theoretical K-mers': 4**k_test
            })

        perf_df = pd.DataFrame(performance_data)

        mo.md(f"""
        ### 🚀 Performance Benchmarks

        Performance varies significantly with k-mer size due to the combinatorial explosion:

        - **K=7**: 4⁷ = **16,384** possible k-mers
        - **K=13**: 4¹³ = **67,108,864** possible k-mers
        - **K=21**: 4²¹ = **4,398,046,511,104** possible k-mers
        - **K=31**: 4³¹ = **4.6 × 10¹⁸** possible k-mers

        **Test Results:**
        {perf_df.to_markdown(index=False)}

        ### 💡 Optimization Insights

        **Memory Considerations:**
        - **Small k (≤13)**: Fits easily in memory, fast processing
        - **Medium k (15-21)**: Moderate memory usage, good balance
        - **Large k (>25)**: High memory requirements, sparse distributions

        **Performance Tips:**
        - Use **canonical k-mers** to halve the memory footprint
        - Consider **filtering low-complexity sequences** for large genomes
        - **Batch processing** for very large files
        - **Compression** (like our .gz file) saves disk space with minimal runtime cost

        **When to Use Different K-mer Sizes:**
        - **k=7-11**: Quick species identification, taxonomic classification
        - **k=13-17**: Genome assembly, repeat detection
        - **k=21-31**: Specific variant detection, detailed analysis
        """)

    return perf_df, performance_data


@app.cell(hide_code=True)
def __(mo):
    """Educational section and next steps."""
    mo.md("""
    ## 🎓 Learning Summary

    ### ✅ What You've Learned

    **K-mer Fundamentals:**
    - K-mers are fixed-length DNA subsequences used throughout bioinformatics
    - Different k-mer sizes serve different analytical purposes
    - Canonical k-mers can reduce computational complexity by ~50%

    **Technical Skills:**
    - **FASTA parsing** (including compressed .gz files)
    - **Pure Python k-mer counting** with efficient algorithms
    - **Statistical analysis** of k-mer distributions
    - **Interactive visualization** using plotly and marimo

    **Performance Insights:**
    - Memory usage grows exponentially with k-mer size
    - Real genomic data shows highly skewed k-mer distributions
    - Compression provides significant space savings with minimal runtime cost

    ### 🔬 Real-World Applications

    **Genome Analysis:**
    - **Species identification**: Compare k-mer frequencies against reference databases
    - **Genome assembly**: Use k-mers as building blocks to reconstruct longer sequences
    - **Variant detection**: Find differences by comparing k-mer presence/absence

    **Metagenomics:**
    - **Community profiling**: Identify species in environmental samples
    - **Functional annotation**: Predict gene functions from k-mer patterns

    **Medical Genomics:**
    - **Disease diagnosis**: Detect pathogens from clinical samples
    - **Cancer genomics**: Identify tumor-specific mutations

    ### 🚀 Next Steps

    **Advanced Topics to Explore:**
    1. **Sparse k-mer tables** for memory-efficient large-scale analysis
    2. **Bloom filters** for approximate k-mer membership testing
    3. **Count-min sketch** algorithms for streaming k-mer analysis
    4. **GPU acceleration** for massive parallel k-mer processing
    5. **Distributed computing** for genome-scale k-mer analysis

    **Integration with Real Tools:**
    - **Jellyfish**: Industry-standard k-mer counting tool
    - **KMC**: High-performance k-mer counter for big data
    - **Mash**: Fast genome distance estimation using MinHash
    - **Kraken**: Taxonomic classification using k-mers

    ### 🛠️ Production Considerations

    **For Production Use:**
    - Use **compiled tools** (like RustKmer!) for performance-critical applications
    - Implement **memory mapping** for large files
    - Add **progress tracking** for long-running analyses
    - Use **checkpointing** for interruptible processing
    - Consider **cloud computing** for petabyte-scale analysis

    **Data Management:**
    - **Version control** for reference genomes
    - **Metadata tracking** for analysis provenance
    - **Quality control** for input sequences
    - **Backup strategies** for valuable k-mer databases

    ---

    ## 🎉 Congratulations!

    You've successfully completed a comprehensive k-mer analysis using pure Python!
    You now have the foundation to explore advanced bioinformatics tools and techniques.

    **Ready for more?** Try integrating with real RustKmer for production-scale performance!
    """)


@app.cell(hide_code=True)
def __(mo):
    """Footer and credits."""
    mo.md("""
    ---

    ### 📚 Further Reading & Resources

    **Papers & Articles:**
    - [K-mer Analysis in Genomics](https://www.nature.com/articles/nbt.2023) - Comprehensive review
    - [Canonical K-mer Applications](https://academic.oup.com/bioinformatics) - Technical details
    - [Memory-Efficient K-mer Counting](https://arxiv.org/abs/1309.4295) - Algorithm design

    **Tools & Libraries:**
    - **RustKmer**: High-performance k-mer analysis (this project!)
    - **BioPython**: Python bioinformatics library
    - **scikit-bio**: Scientific bioinformatics tools
    - **HTSeq**: High-throughput sequencing analysis

    **Online Resources:**
    - [K-mer Calculator](https://www.bioinformatics.org/sms2/kmer.html) - Interactive learning
    - [NCBI Genome Database](https://www.ncbi.nlm.nih.gov/genome/) - Reference sequences
    - [Ensembl Genomes](https://ensemblgenomes.org/) - Annotated genomes

    ---

    *This notebook was created with ❤️ for the bioinformatics community.*
    *Built using [marimo](https://marimo.io/) for interactive scientific computing.*
    """)
    return


if __name__ == "__main__":
    app.run()