# RustKmer Python API Examples

This directory contains comprehensive examples demonstrating the RustKmer Python API for various bioinformatics applications and use cases.

## Overview

The examples cover:
- Basic k-mer database operations
- Fuzzy querying and mutation analysis
- Database management and statistics
- Integration with popular bioinformatics libraries
- Real-world bioinformatics workflows

## Example Files

### 1. **basic_usage.py** - Fundamental Operations
Demonstrates core RustKmer functionality:
- Database creation and loading
- Basic k-mer queries
- Error handling best practices
- Context manager usage

```bash
python basic_usage.py
```

**Key Features:**
- Simple database querying
- Multiple k-mer queries
- Error handling patterns
- Database statistics retrieval

### 2. **fuzzy_search.py** - Advanced Fuzzy Queries
Comprehensive fuzzy querying examples:
- Basic fuzzy queries with mutation tolerance
- Position-specific mutations
- Batch fuzzy queries
- Performance optimization
- Mutation pattern analysis

```bash
python fuzzy_search.py
```

**Key Features:**
- Mutation tolerance levels
- Position-specific mutation control
- Batch processing for multiple queries
- Performance benchmarking
- Mutation hot-spot analysis

### 3. **database_operations.py** - Database Management
Complete database operations guide:
- Database statistics and metadata
- Database dumping and exporting
- Database backup and validation
- Database comparison and analysis
- Large database handling

```bash
python database_operations.py
```

**Key Features:**
- Comprehensive statistics analysis
- Export to various formats (TSV, CSV)
- Backup with integrity validation
- Database comparison and overlap analysis
- Memory-efficient processing

### 4. **integration_pandas.py** - Data Analysis Integration
Integration with pandas for data analysis:
- Database content analysis with pandas
- K-mer abundance analysis
- Similarity and clustering
- Performance benchmarking
- Visualization examples

```bash
python integration_pandas.py
```

**Key Features:**
- Pandas DataFrame integration
- Statistical analysis of k-mer data
- Clustering and similarity analysis
- Visualization with matplotlib/seaborn
- Performance optimization

### 5. **integration_biopython.py** - BioPython Workflows
Integration with BioPython for bioinformatics:
- Working with Bio.Seq objects
- FASTA/FASTQ file processing
- Sequence similarity analysis
- Transcriptome analysis
- Metagenomics profiling
- Protein domain analysis

```bash
python integration_biopython.py
```

**Key Features:**
- BioPython SeqRecord integration
- Feature annotation handling
- Transcript expression analysis
- Metagenome composition analysis
- Protein domain detection

## Requirements

Install the required packages:

```bash
# Core requirements
pip install rustkmer

# For integration examples
pip install pandas matplotlib seaborn biopython
```

## Common Usage Patterns

### Context Manager (Recommended)
```python
from rustkmer import Database

# Automatically handles opening/closing
with Database("your_database.rkdb") as db:
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
    print(f"Count: {result.count}")
```

### Fuzzy Queries with Position Mutations
```python
with Database("database.rkdb") as db:
    # Allow mutations at specific positions
    result = db.fuzzy_query(
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        mutations=2,
        position_mutations="10,15:1;20,25:2"  # Format: position:budget
    )
```

### Batch Processing
```python
kmer_list = ["ATCGATCG...", "GCTAGCTA...", "TTTTTTTT..."]
batch_result = db.fuzzy_query_batch(
    kmer_list,
    mutations=1,
    max_workers=4
)
```

### Database Statistics
```python
stats = db.stats()
print(f"Unique k-mers: {stats.unique_kmers:,}")
print(f"Total counts: {stats.total_counts:,}")
print(f"File size: {stats.file_size:,} bytes")
```

## Performance Tips

1. **Use Context Managers**: Automatically handles resource cleanup
2. **Batch Queries**: More efficient than individual queries
3. **Canonical K-mers**: Reduces database size and improves query speed
4. **Appropriate K-mer Size**: Balance between specificity and database size
5. **Memory-Efficient Processing**: Use generators for large datasets

## Example Workflows

### Simple K-mer Counting
```python
from rustkmer import KmerCounter

# Create counter
counter = KmerCounter(k=31, canonical=True)

# Count from FASTA file
counter.count_file("sequences.fasta")

# Save to database
counter.save_to_database("output.rkdb")
```

### Fuzzy Search Pipeline
```python
with Database("database.rkdb") as db:
    # Query with mutations
    result = db.fuzzy_query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)

    # Get top matches
    top_matches = result.get_top_matches(10)

    for match in top_matches:
        print(f"{match.kmer}: {match.count} (distance={match.distance})")
```

### Integration with Pandas
```python
import pandas as pd
from rustkmer import Database

# Extract database content to DataFrame
with Database("database.rkdb") as db:
    data = []
    for result in db.dump(limit=10000):
        data.append({
            'kmer': result.kmer,
            'count': result.count,
            'canonical': result.canonical
        })

    df = pd.DataFrame(data)

    # Analyze
    print(f"Database contains {len(df)} k-mers")
    print(f"Mean count: {df['count'].mean():.1f}")
    print(f"Max count: {df['count'].max()}")
```

## Troubleshooting

### Common Issues

1. **Database Not Found**: Ensure database file exists and is readable
2. **Invalid K-mers**: Check that k-mers contain only A,T,C,G characters
3. **Memory Issues**: Use smaller k-mer sizes or process in chunks
4. **Performance**: Use batch queries and appropriate k-mer sizes

### Error Handling
```python
from rustkmer import Database, DatabaseNotFoundError, InvalidKmerError

try:
    with Database("database.rkdb") as db:
        result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
except DatabaseNotFoundError:
    print("Database file not found")
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e}")
```

## Advanced Examples

### Custom Analysis Pipeline
```python
def analyze_transcriptome(transcripts_fasta, output_dir):
    """Analyze transcriptome with RustKmer."""

    # Create database
    counter = KmerCounter(k=25, canonical=True)
    counter.count_file(transcripts_fasta)
    db_path = os.path.join(output_dir, "transcriptome.rkdb")
    counter.save_to_database(db_path)

    # Analyze with pandas
    with Database(db_path) as db:
        stats = db.stats()

        # Export top k-mers
        data = []
        for result in db.dump(limit=1000, canonical_only=True):
            data.append({'kmer': result.kmer, 'count': result.count})

        df = pd.DataFrame(data)
        df.to_csv(os.path.join(output_dir, "top_kmers.csv"), index=False)

    return stats
```

## Contributing

To add new examples:

1. Create a new Python file in this directory
2. Follow the existing code style and documentation
3. Include comprehensive error handling
4. Add the example to this README
5. Test with sample data

## Support

For questions or issues:
- Check the [main documentation](../../../docs/)
- Review the API reference
- Open an issue on the GitHub repository