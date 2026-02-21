# Integration with Bioinformatics Workflows

This tutorial demonstrates how to integrate RustKmer's Python API with popular bioinformatics tools, workflow managers, and cloud platforms for scalable k-mer analysis.

## Tutorial Overview

You'll learn to:
- Integrate with Snakemake workflow management
- Use RustKmer in Jupyter notebooks
- Connect with Nextflow pipelines
- Work with pandas and NumPy for data analysis
- Deploy to cloud platforms (AWS, GCP, Azure)
- Build reproducible analysis pipelines

### Prerequisites
- Python 3.8+ with RustKmer installed
- Basic understanding of bioinformatics workflows
- Familiarity with command-line tools
- 45-60 minutes to complete

---

## Integration 1: Snakemake Workflows

### Snakemake Rule for K-mer Counting

```python
# Snakefile
#!/usr/bin/env python3
"""
Snakemake workflow for k-mer analysis with RustKmer Python API.
"""

import os
from pathlib import Path

configfile: "config.yaml"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

configfile: "config.yaml"

# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

rule all:
    input:
        expand("results/{sample}/kmer_stats.txt", sample=config["samples"]),
        "results/merged_database.rkdb",
        "results/presence_matrix.csv",
        "results/kmer_analysis.html"

rule count_kmers:
    """
    Count k-mers from FASTA files using RustKmer Python API.
    """
    input:
        fasta="data/{sample}.fasta"
    output:
        database="results/{sample}/database.rkdb",
        stats="results/{sample}/kmer_stats.txt"
    params:
        k=config["kmer_size"]
    script:
        "scripts/count_kmers.py"

rule query_database:
    """
    Query k-mer database with specified k-mers.
    """
    input:
        database="results/{sample}/database.rkdb",
        queries="config/queries.txt"
    output:
        results="results/{sample}/query_results.csv"
    script:
        "scripts/query_database.py"

rule merge_databases:
    """
    Merge multiple k-mer databases.
    """
    input:
        databases=expand("results/{sample}/database.rkdb", sample=config["samples"])
    output:
        merged="results/merged_database.rkdb"
    script:
        "scripts/merge_databases.py"

rule create_presence_matrix:
    """
    Create presence-absence matrix across all samples.
    """
    input:
        databases=expand("results/{sample}/database.rkdb", sample=config["samples"]),
        queries="config/queries.txt"
    output:
        matrix="results/presence_matrix.csv"
    script:
        "scripts/create_matrix.py"

rule generate_report:
    """
    Generate HTML report with analysis results.
    """
    input:
        matrix="results/presence_matrix.csv",
        stats=expand("results/{sample}/kmer_stats.txt", sample=config["samples"])
    output:
        report="results/kmer_analysis.html"
    script:
        "scripts/generate_report.py"
```

### Snakemake Script: count_kmers.py

```python
#!/usr/bin/env python3
"""
Snakemake script for k-mer counting with RustKmer.
"""

import sys
import os
import time
from pathlib import Path
from pyrustkmer import KmerCounter, PyFuzzyQuery

def main():
    # Input/output from Snakemake
    fasta_file = snakemake.input.fasta
    output_database = snakemake.output.database
    output_stats = snakemake.output.stats
    kmer_size = snakemake.params.k

    # Create output directory
    Path(output_database).parent.mkdir(parents=True, exist_ok=True)

    print(f"Counting k-mers from {fasta_file}")
    print(f"K-mer size: {kmer_size}")
    print(f"Output database: {output_database}")

    # Initialize k-mer counter
    counter = PyCounter(kmer_size, canonical=True)

    # Count k-mers
    start_time = time.time()
    counter.add_from_fasta(fasta_file)
    processing_time = time.time() - start_time

    # Get statistics
    total_kmers = counter.get_stats().total_kmers)
    unique_kmers = counter.get_unique_count()

    # Save database
    counter.save_database(output_database)

    # Write statistics
    with open(output_stats, 'w') as f:
        f.write(f"Sample: {Path(fasta_file).stem}\n")
        f.write(f"K-mer size: {kmer_size}\n")
        f.write(f"Total k-mers: {total_kmers:,}\n")
        f.write(f"Unique k-mers: {unique_kmers:,}\n")
        f.write(f"Processing time: {processing_time:.1f} seconds\n")
        f.write(f"Database file: {output_database}\n")
        f.write(f"Database size: {os.path.getsize(output_database)/(1024*1024):.1f} MB\n")

    print(f"Completed: {total_kmers:,} total k-mers, {unique_kmers:,} unique k-mers")

if __name__ == "__main__":
    main()
```

### Configuration File: config.yaml

```yaml
# Snakemake configuration for k-mer analysis
samples:
  - sample_01
  - sample_02
  - sample_03
  - sample_04
  - sample_05

kmer_size: 31

queries:
  - "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
  - "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"
  - "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
  - "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"

output_directory: "results"

resources:
  threads: 4
  memory: "16G"
```

### Running the Snakemake Workflow

```bash
# Create conda environment
conda create -n rustkmer-snakemake -c conda-forge -c bioconda python=3.10 snakemake rustkmer

# Activate environment
conda activate rustkmer-snakemake

# Dry run to check workflow
snakemake --dryrun

# Run workflow
snakemake --cores 8 --use-conda

# Run with specific resources
snakemake --cores 8 --resources memory=32000 --use-conda

# Generate workflow diagram
snakemake --dag | dot -Tpng > workflow.png
```

---

## Integration 2: Jupyter Notebooks

### Interactive K-mer Analysis Notebook

```python
#!/usr/bin/env python3
"""
Jupyter notebook for interactive k-mer analysis with RustKmer.
Save as: kmer_analysis.ipynb
"""

# %%
# # K-mer Analysis with RustKmer
#
# This notebook demonstrates interactive k-mer analysis using the RustKmer Python API.

# %%
# ## Setup and Imports

# %%
import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from pyrustkmer import KmerCounter, Database, PyFuzzyQuery
from Bio import SeqIO
import ipywidgets as widgets
from IPython.display import display, Markdown

# Set plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# %%
# ## Configuration

# %%
# Interactive widgets for configuration
kmer_size_widget = widgets.IntSlider(
    value=31,
    min=13,
    max=51,
    step=2,
    description='K-mer size:',
    style={'description_width': 'initial'}
)

input_file_widget = widgets.Text(
    value='data/sample.fasta',
    description='Input file:',
    style={'description_width': 'initial'}
)

display(kmer_size_widget)
display(input_file_widget)

# %%
# ## Load and Analyze FASTA File

# %%
def analyze_fasta_file(file_path):
    """Analyze FASTA file basic statistics."""

    sequences = []
    total_length = 0
    gc_count = 0

    for record in SeqIO.parse(file_path, "fasta"):
        seq = str(record.seq).upper()
        sequences.append(seq)
        total_length += len(seq)
        gc_count += seq.count('G') + seq.count('C')

    if total_length == 0:
        return None

    return {
        'num_sequences': len(sequences),
        'total_length': total_length,
        'average_length': total_length / len(sequences),
        'gc_content': gc_count / total_length,
        'sequences': sequences
    }

# Analyze the input file
file_path = input_file_widget.value
fasta_stats = analyze_fasta_file(file_path)

if fasta_stats:
    display(Markdown(f"""
    ### FASTA File Statistics
    - **Number of sequences**: {fasta_stats['num_sequences']:,}
    - **Total length**: {fasta_stats['total_length']:,} bp
    - **Average length**: {fasta_stats['average_length']:.1f} bp
    - **GC content**: {fasta_stats['gc_content']:.2%}
    """))
else:
    display(Markdown("⚠️ Could not read FASTA file. Please check the file path."))

# %%
# ## K-mer Counting Analysis

# %%
def count_kmers_with_progress(fasta_file, kmer_size):
    """Count k-mers with progress indication."""

    display(Markdown(f"🧬 Counting {kmer_size}-mers from `{fasta_file}`..."))

    # Create progress bar
    progress = widgets.IntProgress(
        value=0,
        min=0,
        max=100,
        description='Processing:',
        bar_style='info'
    )
    display(progress)

    # Count k-mers
    start_time = time.time()
    counter = PyCounter(kmer_size, canonical=True)

    # Update progress
    progress.value = 25

    counter.add_from_fasta(fasta_file)
    progress.value = 75

    # Get statistics
    total_kmers = counter.get_stats().total_kmers)
    unique_kmers = counter.get_unique_count()

    progress.value = 100
    processing_time = time.time() - start_time

    display(Markdown(f"""
    ### K-mer Counting Results
    - **Total k-mers**: {total_kmers:,}
    - **Unique k-mers**: {unique_kmers:,}
    - **Uniqueness ratio**: {unique_kmers/total_kmers:.4f}
    - **Processing time**: {processing_time:.1f} seconds
    - **Speed**: {total_kmers/processing_time:,.0f} k-mers/second
    """))

    return counter, {
        'total_kmers': total_kmers,
        'unique_kmers': unique_kmers,
        'processing_time': processing_time
    }

# Run k-mer counting
kmer_size = kmer_size_widget.value
counter, kmer_stats = count_kmers_with_progress(file_path, kmer_size)

# %%
# ## K-mer Database Creation and Analysis

# %%
def create_and_analyze_database(counter, sample_name="sample"):
    """Create database and analyze its contents."""

    display(Markdown("💾 Creating k-mer database..."))

    # Create database
    db_file = f"{sample_name}_k{kmer_size}.rkdb"
    counter.save_database(db_file)

    db_size = os.path.getsize(db_file) / (1024*1024)  # MB

    display(Markdown(f"""
    ### Database Information
    - **Database file**: `{db_file}`
    - **File size**: {db_size:.1f} MB
    """))

    # Analyze database contents
    display(Markdown("🔍 Analyzing database contents..."))

    db = PyDatabase(db_file)
fuzzy = PyFuzzyQuery(db) as db:
        # Get top k-mers
        top_kmers = []
        for result in db.dump(limit=50, canonical_only=True):
            top_kmers.append({
                'kmer': result.kmer,
                'canonical': result.canonical,
                'count': result.count
            })

    return db_file, pd.DataFrame(top_kmers)

# Create and analyze database
db_file, top_kmers_df = create_and_analyze_database(counter, Path(file_path).stem)

# %%
# ## Visualize K-mer Distribution

# %%
def plot_kmer_distribution(df):
    """Create visualizations of k-mer distribution."""

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('K-mer Distribution Analysis', fontsize=16)

    # Plot 1: Top 20 k-mers by count
    top_20 = df.nlargest(20, 'count')
    axes[0, 0].barh(range(len(top_20)), top_20['count'])
    axes[0, 0].set_yticks(range(len(top_20)))
    axes[0, 0].set_yticklabels([k[:15] + "..." for k in top_20['kmer']], fontsize=8)
    axes[0, 0].set_xlabel('Count')
    axes[0, 0].set_title('Top 20 K-mers by Count')
    axes[0, 0].invert_yaxis()

    # Plot 2: Count distribution histogram
    axes[0, 1].hist(df['count'], bins=30, alpha=0.7, edgecolor='black')
    axes[0, 1].set_xlabel('K-mer Count')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('K-mer Count Distribution')
    axes[0, 1].set_yscale('log')

    # Plot 3: Cumulative distribution
    sorted_counts = sorted(df['count'], reverse=True)
    cumulative = np.cumsum(sorted_counts) / np.sum(sorted_counts)
    axes[1, 0].plot(range(len(cumulative)), cumulative)
    axes[1, 0].set_xlabel('K-mer Rank')
    axes[1, 0].set_ylabel('Cumulative Fraction')
    axes[1, 0].set_title('Cumulative K-mer Distribution')
    axes[1, 0].grid(True, alpha=0.3)

    # Plot 4: Count vs Rank (log-log)
    ranks = np.arange(1, len(sorted_counts) + 1)
    axes[1, 1].loglog(ranks[:100], sorted_counts[:100], 'o-', markersize=4)
    axes[1, 1].set_xlabel('Rank (log scale)')
    axes[1, 1].set_ylabel('Count (log scale)')
    axes[1, 1].set_title('K-mer Rank-Count Relationship (Top 100)')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

# Create visualizations
plot_kmer_distribution(top_kmers_df)

# %%
# ## Interactive K-mer Querying

# %%
# Interactive k-mer query widget
query_widget = widgets.Text(
    value="ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    description='Query k-mer:',
    style={'description_width': 'initial'},
    layout=widgets.Layout(width='500px')
)

mutations_widget = widgets.IntSlider(
    value=2,
    min=0,
    max=5,
    description='Mutations:',
    style={'description_width': 'initial'}
)

query_button = widgets.Button(
    description='Query Database',
    button_style='success'
)

output_area = widgets.Output()

def query_database(b):
    """Handle database query."""
    with output_area:
        output_area.clear_output()

        query = query_widget.value.upper()
        mutations = mutations_widget.value

        if len(query) != kmer_size:
            display(Markdown(f"⚠️ Query length must be {kmer_size} bases"))
            return

        if not all(base in 'ATCG' for base in query):
            display(Markdown("⚠️ Query must contain only A, T, C, G"))
            return

        display(Markdown(f"🔍 Querying: `{query}` with {mutations} mutations allowed..."))

        db = PyDatabase(db_file)
fuzzy = PyFuzzyQuery(db) as db:
            # Exact query
            exact_result = db.query_exact(query)

            display(Markdown(f"""
            ### Exact Query Results
            - **Query**: `{query}`
            - **Found**: {exact_result.found}
            - **Count**: {exact_result.count:,}
            - **Canonical**: `{exact_result.canonical}`
            """))

            # Fuzzy query
            if mutations > 0:
                fuzzy_result = fuzzy.query_fuzzy(query, mutations=mutations)

                display(Markdown(f"""
                ### Fuzzy Query Results ({mutations} mutations)
                - **Total matches**: {fuzzy_result.total_matches}
                - **Query k-mer**: `{fuzzy_result.query_kmer}`
                """))

                if fuzzy_result.total_matches > 0:
                    # Show top matches
                    top_matches = fuzzy_result.get_top_matches(5)
                    match_data = []
                    for match in top_matches:
                        match_data.append({
                            'kmer': match.kmer,
                            'distance': match.distance,
                            'count': match.count
                        })

                    matches_df = pd.DataFrame(match_data)
                    display(Markdown("#### Top 5 Fuzzy Matches:"))
                    display(matches_df)

query_button.on_click(query_database)

# Display query interface
display(widgets.VBox([query_widget, mutations_widget, query_button, output_area]))

# %%
# ## Batch Analysis of Multiple K-mers

# %%
def batch_analyze_kmers(kmers_list):
    """Analyze multiple k-mers in batch."""

    display(Markdown(f"📊 Analyzing {len(kmers_list)} k-mers..."))

    results = []

    db = PyDatabase(db_file)
fuzzy = PyFuzzyQuery(db) as db:
        for i, kmer in enumerate(kmers_list):
            try:
                result = db.query_exact(kmer)
                results.append({
                    'kmer': kmer,
                    'found': result.found,
                    'count': result.count,
                    'canonical': result.canonical
                })
            except Exception as e:
                results.append({
                    'kmer': kmer,
                    'found': False,
                    'count': 0,
                    'canonical': None,
                    'error': str(e)
                })

            # Update progress
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(kmers_list)} k-mers")

    return pd.DataFrame(results)

# Example k-mers to analyze
example_kmers = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
]

# Run batch analysis
batch_results = batch_analyze_kmers(example_kmers)

# Display results
display(Markdown("### Batch Analysis Results"))
display(batch_results)

# %%
# ## Comparative Analysis (Multiple Samples)

# %%
def compare_multiple_samples(sample_files):
    """Compare k-mer content across multiple samples."""

    display(Markdown("🔬 Comparing k-mer content across samples..."))

    all_results = {}

    for sample_file in sample_files:
        sample_name = Path(sample_file).stem
        display(Markdown(f"Processing `{sample_name}`..."))

        # Count k-mers
        counter = PyCounter(kmer_size, canonical=True)
        counter.add_from_fasta(sample_file)

        # Get top k-mers
        sample_results = []
        temp_db = f"temp_{sample_name}.rkdb"
        counter.save_database(temp_db)

        db = PyDatabase(temp_db)
fuzzy = PyFuzzyQuery(db) as db:
            for result in db.dump(limit=20, canonical_only=True):
                sample_results.append({
                    'kmer': result.canonical,
                    'count': result.count
                })

        all_results[sample_name] = pd.DataFrame(sample_results)

        # Clean up
        os.remove(temp_db)

    return all_results

# Example: Compare multiple samples (if available)
sample_files = [file_path]  # Add more files as needed

if len(sample_files) > 1:
    comparison_results = compare_multiple_samples(sample_files)

    # Create comparison visualization
    fig, ax = plt.subplots(figsize=(12, 6))

    for sample_name, df in comparison_results.items():
        ax.plot(range(len(df)), df['count'], label=sample_name, marker='o', markersize=3)

    ax.set_xlabel('K-mer Rank')
    ax.set_ylabel('Count')
    ax.set_title('K-mer Abundance Comparison Across Samples')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.show()
else:
    display(Markdown("📝 Add more sample files to enable comparative analysis"))

# %%
# ## Export Results

# %%
def export_results():
    """Export analysis results to files."""

    display(Markdown("💾 Exporting analysis results..."))

    # Export k-mer statistics
    with open("kmer_statistics.txt", 'w') as f:
        f.write("K-mer Analysis Results\n")
        f.write("=" * 30 + "\n")
        f.write(f"Input file: {file_path}\n")
        f.write(f"K-mer size: {kmer_size}\n")
        f.write(f"Total k-mers: {kmer_stats['total_kmers']:,}\n")
        f.write(f"Unique k-mers: {kmer_stats['unique_kmers']:,}\n")
        f.write(f"Processing time: {kmer_stats['processing_time']:.1f} seconds\n")

    # Export top k-mers
    top_kmers_df.to_csv("top_kmers.csv", index=False)

    # Export batch results
    if 'batch_results' in locals():
        batch_results.to_csv("batch_query_results.csv", index=False)

    display(Markdown("""
    ### Exported Files:
    - `kmer_statistics.txt` - Summary statistics
    - `top_kmers.csv` - Top k-mers with counts
    - `batch_query_results.csv` - Batch query results (if applicable)
    """))

# Export results
export_results()

# %%
# ## Conclusion

# %%
display(Markdown(f"""
## Analysis Summary

- **Processed**: `{Path(file_path).name}` ({kmer_stats['total_kmers']:,} total k-mers)
- **Unique k-mers**: {kmer_stats['unique_kmers']:,}
- **Database created**: `{db_file}`
- **Analysis completed**: 🎉

You can now:
1. Use the database for further queries
2. Compare with other samples
3. Integrate into larger analysis pipelines
4. Export results for downstream analysis

### Next Steps
- Try different k-mer sizes
- Analyze multiple samples
- Use fuzzy queries for pattern matching
- Integrate with Snakemake or Nextflow workflows
"""))
```

---

## Integration 3: Nextflow Pipeline

### Nextflow Main Script

```groovy
#!/usr/bin/env nextflow

nextflow.enable.dsl=2

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

params.kmer_size = 31
params.input_dir = 'data'
params.output_dir = 'results'
params.query_file = 'queries.txt'
params.container = 'rustkmer/rustkmer:latest'

// ---------------------------------------------------------------------------
// Processes
// ---------------------------------------------------------------------------

process COUNT_KMERS {
    tag "${sample_id}"

    input:
    path fasta_file from params.input_dir.glob("*.fasta")

    output:
    path "${sample_id}.rkdb" into databases
    path "${sample_id}_stats.txt"

    container "${params.container}"

    script:
    """
    #!/usr/bin/env python3
    import os
    import time
    from pyrustkmer import KmerCounter, PyFuzzyQuery

    sample_id = "${sample_id}"
    fasta_file = "${fasta_file}"
    db_file = "${sample_id}.rkdb"
    stats_file = "${sample_id}_stats.txt"
    kmer_size = ${params.kmer_size}

    print(f"Processing {sample_id} with k={kmer_size}")

    # Count k-mers
    counter = PyCounter(kmer_size, canonical=True)
    start_time = time.time()
    counter.add_from_fasta(fasta_file)
    processing_time = time.time() - start_time

    # Get statistics
    total_kmers = counter.get_stats().total_kmers)
    unique_kmers = counter.get_unique_count()

    # Save database
    counter.save_database(db_file)

    # Write statistics
    with open(stats_file, 'w') as f:
        f.write(f"sample_id,{sample_id}\\n")
        f.write(f"total_kmers,{total_kmers}\\n")
        f.write(f"unique_kmers,{unique_kmers}\\n")
        f.write(f"processing_time,{processing_time}\\n")
        f.write(f"database_size,{os.path.getsize(db_file)}\\n")

    print(f"Completed: {total_kmers:,} total, {unique_kmers:,} unique")
    """
}

process QUERY_DATABASES {
    tag "batch_query"

    input:
    path db_files from databases.collect()
    path query_file from params.query_file

    output:
    path "presence_matrix.csv"
    path "count_matrix.csv"

    container "${params.container}"

    script:
    """
    #!/usr/bin/env python3
    import pandas as pd
    from pyrustkmer import Database, PyFuzzyQuery
    from pathlib import Path

    # Load queries
    with open("${query_file}") as f:
        queries = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(queries)} queries")

    # Collect all database files
    db_files = ${db_files}

    # Query all databases
    presence_data = []
    count_data = []

    for db_file in db_files:
        sample_name = Path(db_file).stem

        presence_row = {'Sample': sample_name}
        count_row = {'Sample': sample_name}

        try:
            db = PyDatabase(db_file)
fuzzy = PyFuzzyQuery(db) as db:
                for query in queries:
                    try:
                        result = db.query_exact(query)
                        presence_row[query] = 1 if result.found else 0
                        count_row[query] = result.count
                    except Exception as e:
                        print(f"Query {query} failed for {sample_name}: {e}")
                        presence_row[query] = 0
                        count_row[query] = 0

        except Exception as e:
            print(f"Database {db_file} failed: {e}")
            for query in queries:
                presence_row[query] = 0
                count_row[query] = 0

        presence_data.append(presence_row)
        count_data.append(count_row)

    # Create DataFrames
    presence_df = pd.DataFrame(presence_data)
    count_df = pd.DataFrame(count_data)

    # Save results
    presence_df.to_csv("presence_matrix.csv", index=False)
    count_df.to_csv("count_matrix.csv", index=False)

    print("Query analysis completed")
    """
}

process GENERATE_REPORT {
    tag "report"

    input:
    path presence_matrix from "presence_matrix.csv"
    path count_matrix from "count_matrix.csv"

    output:
    path "kmer_analysis_report.html"

    container "${params.container}"

    script:
    """
    #!/usr/bin/env python3
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    from pathlib import Path

    # Load data
    presence_df = pd.read_csv("${presence_matrix}")
    count_df = pd.read_csv("${count_matrix}")

    # Create HTML report
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>K-mer Analysis Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }
            .stats-table { border-collapse: collapse; width: 100%; }
            .stats-table th, .stats-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .stats-table th { background-color: #4CAF50; color: white; }
        </style>
    </head>
    <body>
        <h1>K-mer Analysis Report</h1>

        <div class="summary">
            <h2>Summary Statistics</h2>
            <table class="stats-table">
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Samples</td><td>{len(presence_df)}</td></tr>
                <tr><td>Total K-mers Queried</td><td>{len(presence_df.columns) - 1}</td></tr>
                <tr><td>Presence Matrix Size</td><td>{presence_df.shape}</td></tr>
            </table>
        </div>
    """.format(len(presence_df), len(presence_df.columns) - 1, presence_df.shape)

    # Add k-mer presence analysis
    html_content += """
        <h2>K-mer Presence Analysis</h2>
        <table class="stats-table">
            <tr><th>K-mer</th><th>Samples Present</th><th>Presence Frequency</th></tr>
    """

    for col in presence_df.columns[1:]:  # Skip Sample column
        present_count = presence_df[col].sum()
        frequency = present_count / len(presence_df)
        html_content += f"<tr><td>{col}</td><td>{present_count}</td><td>{frequency:.2%}</td></tr>"

    html_content += """
        </table>
    </body>
    </html>
    """

    # Save HTML report
    with open("kmer_analysis_report.html", 'w') as f:
        f.write(html_content)

    print("Report generated successfully")
    """
}

// ---------------------------------------------------------------------------
// Workflow
// ---------------------------------------------------------------------------

workflow {
    // Count k-mers for all samples
    COUNT_KMERS

    // Query databases and generate matrices
    QUERY_DATABASES

    // Generate final report
    GENERATE_REPORT
}
```

### Nextflow Configuration

```groovy
// nextflow.config

process {
    executor = 'local'

    // Container settings
    container = 'rustkmer/rustkmer:latest'

    // Resource settings
    cpus = 4
    memory = '8 GB'
    time = '2h'

    // Error handling
    errorStrategy = 'retry'
    maxRetries = 3

    // Queue settings
    queue = 'normal'

    // Docker settings
    docker.enabled = true
    docker.runOptions = '--rm'

    // Singularity settings
    singularity.enabled = true
    singularity.autoMounts = true
}

// Environment variables
env {
    PYTHONPATH = '/usr/local/lib/python3.10/site-packages'
}

// Executors
aws {
    process {
        executor = 'awsbatch'
        queue = 'rustkmer-queue'
        region = 'us-east-1'
    }
}

slurm {
    process {
        executor = 'slurm'
        queue = 'short'
        clusterOptions = '--partition=short'
    }
}
```

---

## Integration 4: Cloud Platform Deployment

### AWS Lambda Function

```python
#!/usr/bin/env python3
"""
AWS Lambda function for k-mer analysis with RustKmer.
"""

import json
import os
import tempfile
import urllib.request
from pyrustkmer import Database, KmerCounter, PyFuzzyQuery
import boto3

def lambda_handler(event, context):
    """AWS Lambda handler for k-mer queries."""

    try:
        # Parse input
        query_kmer = event.get('kmer')
        database_url = event.get('database_url')
        mutations = event.get('mutations', 0)

        if not query_kmer or not database_url:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters: kmer, database_url'
                })
            }

        # Download database from S3
        s3_client = boto3.client('s3')

        # Parse S3 URL (s3://bucket/path/file.rkdb)
        if database_url.startswith('s3://'):
            parts = database_url[5:].split('/', 1)
            bucket = parts[0]
            key = parts[1]

            # Download to temporary file
            with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp_file:
                s3_client.download_file(bucket, key, tmp_file.name)
                db_path = tmp_file.name
        else:
            # Direct URL download
            with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp_file:
                urllib.request.urlretrieve(database_url, tmp_file.name)
                db_path = tmp_file.name

        # Query database
        db = PyDatabase(db_path, LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
            if mutations > 0:
                # Fuzzy query
                result = fuzzy.query_fuzzy(query_kmer, mutations=mutations)
                response = {
                    'kmer': query_kmer,
                    'mutations_allowed': mutations,
                    'total_matches': result.total_matches,
                    'matches': [
                        {
                            'kmer': match.kmer,
                            'distance': match.distance,
                            'count': match.count
                        } for match in result.get_top_matches(10)
                    ]
                }
            else:
                # Exact query
                result = db.query_exact(query_kmer)
                response = {
                    'kmer': query_kmer,
                    'found': result.found,
                    'count': result.count,
                    'canonical': result.canonical
                }

        # Clean up temporary file
        os.unlink(db_path)

        return {
            'statusCode': 200,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
```

### Docker Container for Cloud Deployment

```dockerfile
# Dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install RustKmer
RUN pip install rustkmer

# Create app directory
WORKDIR /app

# Copy application code
COPY app.py .
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "app.py"]
```

### Flask Web Service

```python
#!/usr/bin/env python3
"""
Flask web service for k-mer analysis.
"""

from flask import Flask, request, jsonify
from pyrustkmer import Database, KmerCounter, PyFuzzyQuery
import os
import tempfile
import urllib.request
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration
DATABASE_DIR = os.environ.get('DATABASE_DIR', '/app/databases')
MAX_DATABASE_SIZE = int(os.environ.get('MAX_DATABASE_SIZE', '1000000000'))  # 1GB

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'rustkmer-api'})

@app.route('/query', methods=['POST'])
def query_kmer():
    """Query k-mer in database."""

    try:
        data = request.get_json()

        # Validate input
        required_fields = ['kmer', 'database']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        query_kmer = data['kmer']
        database_path = data['database']
        mutations = data.get('mutations', 0)

        # Validate k-mer
        if not all(base in 'ATCG' for base in query_kmer.upper()):
            return jsonify({'error': 'Invalid k-mer sequence'}), 400

        # Get database path
        if database_path.startswith('http'):
            # Download from URL
            with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp_file:
                urllib.request.urlretrieve(database_path, tmp_file.name)
                db_path = tmp_file.name
        else:
            # Local file path
            db_path = os.path.join(DATABASE_DIR, database_path)

            if not os.path.exists(db_path):
                return jsonify({'error': 'Database not found'}), 404

        # Query database
        db = PyDatabase(db_path, LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
            if mutations > 0:
                result = fuzzy.query_fuzzy(query_kmer, mutations=mutations)
                response = {
                    'kmer': query_kmer,
                    'mutations_allowed': mutations,
                    'total_matches': result.total_matches,
                    'matches': [
                        {
                            'kmer': match.kmer,
                            'distance': match.distance,
                            'count': match.count
                        } for match in result.get_top_matches(10)
                    ]
                }
            else:
                result = db.query_exact(query_kmer)
                response = {
                    'kmer': query_kmer,
                    'found': result.found,
                    'count': result.count,
                    'canonical': result.canonical
                }

        # Clean up temporary file
        if database_path.startswith('http'):
            os.unlink(db_path)

        return jsonify(response)

    except Exception as e:
        app.logger.error(f"Query error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/count', methods=['POST'])
def count_kmers():
    """Count k-mers from FASTA sequence."""

    try:
        data = request.get_json()

        if 'sequence' not in data and 'file_url' not in data:
            return jsonify({'error': 'Missing sequence or file_url'}), 400

        kmer_size = data.get('kmer_size', 31)
        canonical = data.get('canonical', True)

        # Create temporary FASTA file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as tmp_file:
            if 'sequence' in data:
                tmp_file.write(f">input_sequence\n{data['sequence']}\n")
            else:
                # Download sequence from URL
                seq_content = urllib.request.urlopen(data['file_url']).read().decode()
                tmp_file.write(seq_content)

            fasta_path = tmp_file.name

        # Count k-mers
        counter = PyCounter(kmer_size, canonical=canonical)
        counter.add_from_fasta(fasta_path)

        # Get statistics
        total_kmers = counter.get_stats().total_kmers)
        unique_kmers = counter.get_unique_count()

        # Get top k-mers
        temp_db = tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False)
        counter.save_database(temp_db.name)

        top_kmers = []
        db = PyDatabase(temp_db.name)
fuzzy = PyFuzzyQuery(db) as db:
            for result in db.dump(limit=20, canonical_only=True):
                top_kmers.append({
                    'kmer': result.kmer,
                    'count': result.count,
                    'canonical': result.canonical
                })

        # Clean up
        os.unlink(fasta_path)
        os.unlink(temp_db.name)

        response = {
            'kmer_size': kmer_size,
            'canonical': canonical,
            'total_kmers': total_kmers,
            'unique_kmers': unique_kmers,
            'top_kmers': top_kmers
        }

        return jsonify(response)

    except Exception as e:
        app.logger.error(f"Count error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
```

---

## Integration 5: Advanced Data Analysis

### Pandas Integration for Large-Scale Analysis

```python
#!/usr/bin/env python3
"""
Advanced data analysis with pandas integration.
"""

import pandas as pd
import numpy as np
from pyrustkmer import Database, PyFuzzyQuery
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances

class KmerDataFrame:
    """Enhanced DataFrame for k-mer analysis with pandas integration."""

    def __init__(self, presence_matrix=None, count_matrix=None):
        """
        Initialize with presence and/or count matrices.

        Args:
            presence_matrix: DataFrame of binary presence/absence
            count_matrix: DataFrame of k-mer counts
        """
        self.presence_df = presence_matrix
        self.count_df = count_matrix

    @classmethod
    def from_databases(cls, database_files, queries):
        """Create KmerDataFrame from multiple databases."""

        presence_data = []
        count_data = []

        for db_file in database_files:
            sample_name = Path(db_file).stem

            presence_row = {'Sample': sample_name}
            count_row = {'Sample': sample_name}

            db = PyDatabase(db_file)
fuzzy = PyFuzzyQuery(db) as db:
                for query in queries:
                    try:
                        result = db.query_exact(query)
                        presence_row[query] = 1 if result.found else 0
                        count_row[query] = result.count
                    except:
                        presence_row[query] = 0
                        count_row[query] = 0

            presence_data.append(presence_row)
            count_data.append(count_row)

        presence_df = pd.DataFrame(presence_data)
        count_df = pd.DataFrame(count_data)

        return cls(presence_df, count_df)

    def compute_similarity_matrix(self, metric='jaccard'):
        """Compute pairwise similarity between samples."""

        if self.presence_df is None:
            raise ValueError("Presence matrix required for similarity computation")

        # Extract presence data (exclude Sample column)
        presence_data = self.presence_df.iloc[:, 1:].values

        if metric == 'jaccard':
            # Jaccard similarity
            intersection = np.dot(presence_data, presence_data.T)
            union = np.add.outer(presence_data.sum(axis=1), presence_data.sum(axis=1)) - intersection
            similarity = intersection / union

        elif metric == 'cosine':
            # Cosine similarity
            similarity = np.dot(presence_data, presence_data.T) / (
                np.linalg.norm(presence_data, axis=1)[:, np.newaxis] *
                np.linalg.norm(presence_data, axis=1)
            )

        else:
            # Other metrics
            similarity = pairwise_distances(presence_data, metric=metric)
            similarity = 1 - similarity  # Convert distance to similarity

        # Create DataFrame
        sample_names = self.presence_df['Sample'].values
        similarity_df = pd.DataFrame(
            similarity,
            index=sample_names,
            columns=sample_names
        )

        return similarity_df

    def perform_clustering(self, n_clusters=3, method='kmeans'):
        """Perform clustering analysis on samples."""

        if self.presence_df is None:
            raise ValueError("Presence matrix required for clustering")

        # Extract presence data
        presence_data = self.presence_df.iloc[:, 1:].values

        if method == 'kmeans':
            # K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(presence_data)

        elif method == 'hierarchical':
            # Hierarchical clustering
            from sklearn.cluster import AgglomerativeClustering
            clustering = AgglomerativeClustering(n_clusters=n_clusters)
            cluster_labels = clustering.fit_predict(presence_data)

        # Add cluster labels to presence DataFrame
        self.presence_df = self.presence_df.copy()
        self.presence_df['Cluster'] = cluster_labels

        return cluster_labels

    def perform_pca(self, n_components=2):
        """Perform Principal Component Analysis."""

        if self.presence_df is None:
            raise ValueError("Presence matrix required for PCA")

        # Extract presence data
        presence_data = self.presence_df.iloc[:, 1:].values

        # Perform PCA
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(presence_data)

        # Create DataFrame with results
        sample_names = self.presence_df['Sample'].values
        pca_df = pd.DataFrame(
            pca_result,
            index=sample_names,
            columns=[f'PC{i+1}' for i in range(n_components)]
        )

        # Store explained variance
        self.pca_explained_variance = pca.explained_variance_ratio_

        return pca_df

    def plot_similarity_heatmap(self, figsize=(10, 8)):
        """Plot similarity heatmap."""

        similarity_df = self.compute_similarity_matrix()

        plt.figure(figsize=figsize)
        sns.heatmap(similarity_df, annot=True, cmap='coolwarm', center=0,
                   square=True, fmt='.2f')
        plt.title('Sample Similarity Heatmap')
        plt.tight_layout()
        plt.show()

    def plot_pca(self, figsize=(10, 8)):
        """Plot PCA results."""

        pca_df = self.perform_pca()

        plt.figure(figsize=figsize)

        if len(pca_df.columns) >= 2:
            plt.scatter(pca_df['PC1'], pca_df['PC2'],
                       c=range(len(pca_df)), cmap='viridis', s=100, alpha=0.7)

            # Add sample labels
            for i, sample in enumerate(pca_df.index):
                plt.annotate(sample, (pca_df.iloc[i]['PC1'], pca_df.iloc[i]['PC2']),
                           xytext=(5, 5), textcoords='offset points', fontsize=8)

            plt.xlabel(f'PC1 ({self.pca_explained_variance[0]:.1%} variance)')
            plt.ylabel(f'PC2 ({self.pca_explained_variance[1]:.1%} variance)')
            plt.title('Principal Component Analysis of Samples')
            plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    def find_discriminative_kmers(self, top_n=10):
        """Find k-mers that discriminate between sample groups."""

        if self.presence_df is None:
            raise ValueError("Presence matrix required")

        # If no clusters, perform clustering first
        if 'Cluster' not in self.presence_df.columns:
            self.perform_clustering()

        discriminative_kmers = []

        for kmer in self.presence_df.columns[1:-1]:  # Exclude Sample and Cluster
            # Calculate presence frequency in each cluster
            cluster_frequencies = []
            for cluster_id in sorted(self.presence_df['Cluster'].unique()):
                cluster_data = self.presence_df[self.presence_df['Cluster'] == cluster_id]
                frequency = cluster_data[kmer].mean()
                cluster_frequencies.append(frequency)

            # Calculate discriminative score (max difference)
            max_freq = max(cluster_frequencies)
            min_freq = min(cluster_frequencies)
            discriminative_score = max_freq - min_freq

            discriminative_kmers.append({
                'kmer': kmer,
                'score': discriminative_score,
                'cluster_frequencies': cluster_frequencies
            })

        # Sort by discriminative score
        discriminative_kmers.sort(key=lambda x: x['score'], reverse=True)

        return discriminative_kmers[:top_n]

# Example usage
def main():
    """Example of advanced k-mer analysis."""

    # Database files and queries
    database_files = list(Path("results/databases/").glob("*.rkdb"))
    queries = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
    ]

    # Create KmerDataFrame
    kmer_df = KmerDataFrame.from_databases(database_files, queries)

    print("=== K-mer Analysis Summary ===")
    print(f"Samples: {len(kmer_df.presence_df)}")
    print(f"K-mers: {len(kmer_df.presence_df.columns) - 1}")

    # Compute similarity matrix
    similarity_df = kmer_df.compute_similarity_matrix()
    print(f"\nSample similarity matrix:")
    print(similarity_df.round(3))

    # Perform clustering
    cluster_labels = kmer_df.perform_clustering(n_clusters=3)
    print(f"\nCluster assignments:")
    for sample, cluster in zip(kmer_df.presence_df['Sample'], cluster_labels):
        print(f"  {sample}: Cluster {cluster}")

    # Find discriminative k-mers
    discriminative = kmer_df.find_discriminative_kmers(top_n=5)
    print(f"\nTop 5 discriminative k-mers:")
    for kmer_info in discriminative:
        print(f"  {kmer_info['kmer']}: score = {kmer_info['score']:.3f}")

    # Create visualizations
    kmer_df.plot_similarity_heatmap()
    kmer_df.plot_pca()

if __name__ == "__main__":
    main()
```

---

## Performance Optimization Tips

### 1. Memory Management
```python
# Use generators for large datasets
def query_generator(db_file, queries):
    db = PyDatabase(db_file)
fuzzy = PyFuzzyQuery(db) as db:
        for query in queries:
            yield db.query_exact(query)

# Process in chunks
def process_in_chunks(data, chunk_size=1000):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]
```

### 2. Caching Strategies
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_query(db_path, kmer):
    db = PyDatabase(db_path, LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
        return db.query_exact(kmer)
```

### 3. Parallel Processing
```python
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

def parallel_query_batch(databases, queries):
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = [executor.submit(query_database, db, queries) for db in databases]
        results = [future.result() for future in futures]
    return results
```

---

## Troubleshooting Integration Issues

### Common Problems and Solutions

1. **Import Errors**:
   ```python
   # Check installation
   import rustkmer
   print(rustkmer.__version__)
   ```

2. **Database Access Issues**:
   ```python
   # Verify database file
   from pathlib import Path
   db_path = Path("database.rkdb")
   if not db_path.exists():
       print("Database file not found")
   ```

3. **Memory Issues in Notebooks**:
   ```python
   # Clear memory
   import gc
   del large_variable
   gc.collect()
   ```

4. **Container Issues**:
   ```bash
   # Check container logs
   docker logs rustkmer-container

   # Debug container
   docker run -it --entrypoint /bin/bash rustkmer/rustkmer:latest
   ```

---

## Next Steps

- **Scale to cloud**: Deploy on AWS Lambda, Google Cloud Functions
- **Build web APIs**: Create RESTful services for k-mer analysis
- **Integrate ML**: Use k-mer features for machine learning
- **Real-time processing**: Stream processing of sequence data

## Related Documentation

- [Python API Reference](../api-reference/python/)
- [Batch Processing Tutorial](batch-processing.md)
- [Large Genomes Tutorial](large-genomes.md)
- [Performance Tips](../user-guide/performance-tips.md)