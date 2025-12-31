# Querying Databases

Complete guide to querying k-mer databases with RustKmer, from basic exact matches to complex multi-database operations.

## Table of Contents

- [Understanding K-mer Databases](#understanding-k-mer-databases)
- [Database Operations](#database-operations)
- [Exact Querying](#exact-querying)
- [Batch Querying](#batch-querying)
- [Performance Optimization](#performance-optimization)
- [Database Management](#database-management)
- [Advanced Querying](#advanced-querying)
- [Best Practices](#best-practices)

## Understanding K-mer Databases

### What are K-mer Databases?

A **k-mer database** is an optimized binary storage format that contains k-mer sequences and their occurrence counts. RustKmer uses the `.rkdb` (RustKmer Database) format for maximum performance.

```python
# Database contents:
# {
#     "ATCGATCGATCGATCGATCG": 156,
#     "GCTAGCTAGCTAGCTAGCTA": 98,
#     "TTTTTTTTTTTTTTTTTTTT": 3,
#     ...
# }
```

### Database Features

- **Fast Access**: ~4 million queries per second
- **Memory Efficient**: Memory-mapped files with minimal overhead
- **Portable**: Cross-platform compatible binary format
- **Compressed**: Efficient storage of large k-mer sets
- **Indexed**: Optimized for rapid lookups

---

## Database Operations

### Creating Databases

```python
from rustkmer import KmerCounter

# Method 1: Direct creation from counting
counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa.gz")
counter.save_to_database("genome_k21.rkdb")

print(f"Database created with {counter.get_unique_count():,} unique k-mers")
```

```bash
# Command line creation
rustkmer count -k 21 -i genome.fa.gz -o genome_k21.rkdb --canonical
```

### Loading Databases

```python
from rustkmer import Database

# Load database (memory-mapped by default)
db = Database()
db.load("genome_k21.rkdb")

# Get database information
stats = db.get_stats()
print(f"Database Statistics:")
print(f"  K-mer size: {stats.kmer_size}")
print(f"  Total k-mers: {stats.total_kmers:,}")
print(f"  Unique k-mers: {stats.unique_kmers:,}")
print(f"  Database file: {stats.filename}")

# Close when done (optional, with context managers preferred)
db.close()
```

```python
# Using context manager (recommended)
with Database() as db:
    db.load("genome_k21.rkdb")
    result = db.query("ATCGATCGATCGATCGATCG")
    # Database automatically closed
```

### Database Validation

```python
def validate_database(db_path):
    """Validate database integrity and contents."""

    try:
        db = Database()
        db.load(db_path)

        # Get statistics
        stats = db.get_stats()

        # Basic validation
        if stats.total_kmers == 0:
            print("⚠️  Warning: Database appears to be empty")
            return False

        if stats.kmer_size <= 0:
            print("❌ Error: Invalid k-mer size in database")
            return False

        print(f"✅ Database validation successful:")
        print(f"   K-mer size: {stats.kmer_size}")
        print(f"   Total k-mers: {stats.total_kmers:,}")
        print(f"   Unique k-mers: {stats.unique_kmers:,}")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        return False

# Usage
if validate_database("genome_k21.rkdb"):
    print("Database is ready for querying")
```

---

## Exact Querying

### Single K-mer Queries

```python
from rustkmer import Database

with Database() as db:
    db.load("genome_k21.rkdb")

    # Query a specific k-mer
    result = db.query("ATCGATCGATCGATCGATCG")

    if result.exists:
        print(f"✅ Found {result.kmer}: {result.count:,} occurrences")
        print(f"   Database count: {result.database_count}")
    else:
        print(f"❌ {result.kmer}: not found in database")
```

### Query Result Object

```python
result = db.query("ATCGATCGATCGATCGATCG")

# Available attributes
print(f"K-mer: {result.kmer}")          # The queried k-mer string
print(f"Found: {result.exists}")         # Boolean: exists in database
print(f"Count: {result.count}")          # Occurrence count (0 if not found)
print(f"Database: {result.database_count}") # Total k-mers in database

# Convenient boolean check
if result.exists:
    print(f"Found with count {result.count}")
else:
    print("Not found")
```

### Multiple Single Queries

```python
def query_multiple_kmers(db_path, kmer_list):
    """Query multiple individual k-mers."""

    with Database() as db:
        db.load(db_path)

        results = {}

        for kmer in kmer_list:
            result = db.query(kmer)
            results[kmer] = {
                'exists': result.exists,
                'count': result.count
            }

            if result.exists:
                print(f"✅ {kmer}: {result.count:,}")
            else:
                print(f"❌ {kmer}: not found")

        return results

# Usage
test_kmers = [
    "ATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTA",
    "CCCCCCCCCCCCCCCCCCCCCC",  # Likely not found
    "AAAAAAAAAAAAAAAAAAAAA"
]

results = query_multiple_kmers("genome_k21.rkdb", test_kmers)
```

### Querying with Error Handling

```python
def safe_query(db_path, kmer):
    """Safe query with comprehensive error handling."""

    try:
        # Validate k-mer
        if len(kmer) != 21:  # Assuming k=21
            raise ValueError(f"Invalid k-mer length: {len(kmer)} (expected 21)")

        if not all(base in 'ATCG' for base in kmer):
            raise ValueError(f"Invalid characters in k-mer: {kmer}")

        # Load database and query
        with Database() as db:
            db.load(db_path)
            result = db.query(kmer)

            return {
                'success': True,
                'exists': result.exists,
                'count': result.count,
                'kmer': result.kmer
            }

    except ValueError as e:
        return {'success': False, 'error': str(e)}
    except FileNotFoundError:
        return {'success': False, 'error': f'Database file not found: {db_path}'}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {e}'}

# Usage
result = safe_query("genome_k21.rkdb", "ATCGATCGATCGATCGATCG")
if result['success']:
    if result['exists']:
        print(f"Found: {result['count']:,} occurrences")
    else:
        print("Not found")
else:
    print(f"Error: {result['error']}")
```

---

## Batch Querying

### Querying from Files

```python
def batch_query_from_file(db_path, query_file, output_file=None):
    """Query multiple k-mers from a file."""

    with Database() as db:
        db.load(db_path)

        results = []
        found_count = 0

        # Read queries from file (one k-mer per line)
        with open(query_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                kmer = line.strip()

                if not kmer or kmer.startswith('#'):  # Skip empty lines and comments
                    continue

                try:
                    result = db.query(kmer)

                    results.append({
                        'kmer': kmer,
                        'exists': result.exists,
                        'count': result.count
                    })

                    if result.exists:
                        found_count += 1

                except Exception as e:
                    results.append({
                        'kmer': kmer,
                        'exists': False,
                        'count': 0,
                        'error': str(e)
                    })

        print(f"Processed {len(results)} queries")
        print(f"Found {found_count} matches ({found_count/len(results)*100:.1f}%)")

        # Save results if output file specified
        if output_file:
            save_query_results(results, output_file)

def save_query_results(results, output_file):
    """Save query results to CSV file."""

    import csv

    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['kmer', 'exists', 'count', 'error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow(result)

    print(f"Results saved to {output_file}")

# Usage
queries_file = "queries.txt"  # One k-mer per line
results = batch_query_from_file("genome_k21.rkdb", queries_file, "query_results.csv")
```

### CLI Batch Querying

```bash
# Batch query from text file (one k-mer per line)
rustkmer query database.rkdb --batch kmer_list.txt

# Batch query with output to file
rustkmer query database.rkdb --batch kmer_list.txt -o results.txt

# Batch query file format example
cat > kmer_list.txt << EOF
# This is a comment line and will be ignored
ATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAG

# Empty lines are also ignored
TTTTTTTTTTTTTTTTTTTTT
CCCCCCCCCCCCCCCCCCCCCC
EOF
```

### Batch Query Features

- **File Format**: One k-mer per line, supports comments (lines starting with #)
- **Output Format**: Tab-separated values (kmer<TAB>count)
- **Zero Counts**: Non-existent k-mers are output with count 0
- **Performance**: Processes k-mers in batches for optimal performance
- **Error Handling**: Invalid k-mers are skipped with warnings

### High-Performance Batch Querying

```python
import time
from rustkmer import Database

def benchmark_batch_queries(db_path, queries):
    """Benchmark batch query performance."""

    print(f"🚀 Benchmarking {len(queries)} queries...")

    with Database() as db:
        db.load(db_path, preload=True)  # Preload for maximum speed

        start_time = time.time()

        found_count = 0
        total_count = 0

        for kmer in queries:
            result = db.query(kmer)
            if result.exists:
                found_count += 1
                total_count += result.count

        duration = time.time() - start_time
        queries_per_second = len(queries) / duration

        print(f"📊 Performance Results:")
        print(f"   Total queries: {len(queries):,}")
        print(f"   Queries found: {found_count:,}")
        print(f"   Duration: {duration:.3f} seconds")
        print(f"   Queries per second: {queries_per_second:,.0f}")
        print(f"   Average query time: {duration/len(queries)*1000:.3f} ms")
        print(f"   Total matches found: {total_count:,}")

        return queries_per_second

# Usage with test data
test_queries = ["ATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTA"] * 1000
performance = benchmark_batch_queries("genome_k21.rkdb", test_queries)
```

---

## Performance Optimization

### Database Loading Strategies

```python
from rustkmer import Database

# Strategy 1: Memory-mapped (default, good for large databases)
with Database() as db:
    db.load("large_database.rkdb")  # Memory-mapped
    # Database loaded on-demand as needed

# Strategy 2: Preloaded (good for many queries)
with Database() as db:
    db.load("database.rkdb", preload=True)  # Load entire database into memory
    # Maximum query speed, higher memory usage

# Strategy 3: Context manager (recommended)
with Database() as db:
    db.load("database.rkdb")
    # Automatic resource cleanup
```

### Query Optimization Tips

```python
def optimize_query_performance(db_path, query_count):
    """Optimize query performance based on query count."""

    print(f"Optimizing for {query_count} queries...")

    if query_count > 100000:
        # For many queries, preload the database
        print("   Strategy: Preload database into memory")
        db = Database()
        db.load(db_path, preload=True)
        loading_strategy = "preload"
    else:
        # For fewer queries, use memory-mapping
        print("   Strategy: Use memory-mapped access")
        db = Database()
        db.load(db_path)  # Memory-mapped by default
        loading_strategy = "memory_mapped"

    return db, loading_strategy
```

### Batch Size Optimization

```python
def optimal_batch_size(total_queries, available_memory_mb):
    """Determine optimal batch size based on available memory."""

    # Estimate memory per query (rough approximation)
    memory_per_query_mb = 0.001  # 1KB per query result

    max_queries_in_memory = available_memory_mb / memory_per_query_mb
    optimal_batch = min(10000, max_queries_in_memory)  # Cap at 10k queries

    print(f"Recommended batch size: {optimal_batch:,} queries")
    return int(optimal_batch)

# Usage
batch_size = optimal_batch_size(1000000, 1024)  # 1M queries, 1GB memory
```

---

## Database Management

### Database Information

```python
def get_database_info(db_path):
    """Get comprehensive database information."""

    import os

    with Database() as db:
        db.load(db_path)
        stats = db.get_stats()

        # File size
        file_size = os.path.getsize(db_path)
        file_size_mb = file_size / 1024 / 1024

        # Calculate statistics
        avg_count = stats.total_kmers / stats.unique_kmers
        bytes_per_kmer = file_size / stats.unique_kmers

        info = {
            'file_path': db_path,
            'file_size_mb': file_size_mb,
            'kmer_size': stats.kmer_size,
            'unique_kmers': stats.unique_kmers,
            'total_kmers': stats.total_kmers,
            'average_count': avg_count,
            'bytes_per_kmer': bytes_per_kmer,
            'compression_ratio': bytes_per_kmer / (stats.kmer_size * 2)  # Rough estimate
        }

        return info

def print_database_info(db_path):
    """Print database information in a readable format."""

    info = get_database_info(db_path)

    print(f"📊 Database Information: {info['file_path']}")
    print(f"   File size: {info['file_size_mb']:.1f} MB")
    print(f"   K-mer size: {info['kmer_size']}")
    print(f"   Unique k-mers: {info['unique_kmers']:,}")
    print(f"   Total k-mers: {info['total_kmers']:,}")
    print(f"   Average count per k-mer: {info['average_count']:.2f}")
    print(f"   Storage per k-mer: {info['bytes_per_kmer']:.2f} bytes")
    print(f"   Compression efficiency: {info['compression_ratio']:.2f}x")

# Usage
print_database_info("genome_k21.rkdb")
```

### Database Merging

```python
def merge_databases(db_files, output_file):
    """Merge multiple k-mer databases (conceptual example)."""

    # Note: This would require implementing a merge function
    # For now, showing the conceptual approach

    print(f"Merging {len(db_files)} databases...")

    # Load all databases
    databases = []
    for db_file in db_files:
        db = Database()
        db.load(db_file)
        databases.append(db)

    # Count total unique k-mers
    total_unique = sum(db.get_stats().unique_kmers for db in databases)
    print(f"Total unique k-mers across all databases: {total_unique:,}")

    # Merge logic would go here
    # This is a placeholder for the actual implementation
    print("🔄 Database merging feature coming soon!")

    # Clean up
    for db in databases:
        db.close()

# Usage
# merge_databases(["chr1_k21.rkdb", "chr2_k21.rkdb"], "merged_k21.rkdb")
```

### Database Validation and Repair

```python
def validate_database_integrity(db_path):
    """Comprehensive database validation."""

    issues = []

    try:
        # Check file existence
        import os
        if not os.path.exists(db_path):
            issues.append(f"Database file does not exist: {db_path}")
            return issues

        # Check file size
        file_size = os.path.getsize(db_path)
        if file_size == 0:
            issues.append("Database file is empty")
            return issues

        # Try to load database
        with Database() as db:
            try:
                db.load(db_path)
                stats = db.get_stats()

                # Validate statistics
                if stats.kmer_size <= 0:
                    issues.append(f"Invalid k-mer size: {stats.kmer_size}")

                if stats.unique_kmers <= 0:
                    issues.append(f"Invalid unique k-mer count: {stats.unique_kmers}")

                if stats.total_kmers <= 0:
                    issues.append(f"Invalid total k-mer count: {stats.total_kmers}")

                if stats.total_kmers < stats.unique_kmers:
                    issues.append("Total k-mers less than unique k-mers")

                # Test a few queries
                test_queries = ["A" * stats.kmer_size, "T" * stats.kmer_size]
                for query in test_queries:
                    try:
                        result = db.query(query)
                        # Should not crash
                    except Exception as e:
                        issues.append(f"Query failed for '{query}': {e}")

            except Exception as e:
                issues.append(f"Failed to load database: {e}")

    except Exception as e:
        issues.append(f"Validation error: {e}")

    return issues

def check_database_health(db_path):
    """Check overall database health."""

    issues = validate_database_integrity(db_path)

    if not issues:
        print("✅ Database is healthy")
        return True
    else:
        print("❌ Database issues detected:")
        for issue in issues:
            print(f"   - {issue}")
        return False

# Usage
check_database_health("genome_k21.rkdb")
```

---

## Advanced Querying

### Conditional Querying

```python
def conditional_queries(db_path, conditions):
    """Perform queries with conditions."""

    with Database() as db:
        db.load(db_path)

        results = []

        for condition in conditions:
            kmer = condition['kmer']
            min_count = condition.get('min_count', 1)
            max_count = condition.get('max_count', float('inf'))

            result = db.query(kmer)

            # Apply conditions
            matches = result.exists and min_count <= result.count <= max_count

            results.append({
                'kmer': kmer,
                'count': result.count if result.exists else 0,
                'matches': matches,
                'condition': f"{min_count} <= count <= {max_count}"
            })

        return results

# Usage
conditions = [
    {'kmer': 'ATCGATCGATCGATCGATCG', 'min_count': 100},
    {'kmer': 'GCTAGCTAGCTAGCTAGCTA', 'min_count': 50, 'max_count': 200},
    {'kmer': 'TTTTTTTTTTTTTTTTTTTT', 'min_count': 1}
]

results = conditional_queries("genome_k21.rkdb", conditions)
for result in results:
    if result['matches']:
        print(f"✅ {result['kmer']}: {result['count']} (matches condition)")
    else:
        print(f"❌ {result['kmer']}: {result['count']} (doesn't match condition)")
```

### Query Patterns

```python
def query_sequence_regions(db_path, sequence, k=21):
    """Query all k-mers from a sequence."""

    if len(sequence) < k:
        print(f"Sequence too short for k={k}")
        return []

    with Database() as db:
        db.load(db_path)

        results = []
        found_count = 0

        # Extract all k-mers from sequence
        for i in range(len(sequence) - k + 1):
            kmer = sequence[i:i+k]
            result = db.query(kmer)

            results.append({
                'position': i,
                'kmer': kmer,
                'count': result.count,
                'exists': result.exists
            })

            if result.exists:
                found_count += 1

        print(f"Queried {len(results)} k-mers from sequence")
        print(f"Found {found_count} matches ({found_count/len(results)*100:.1f}%)")

        return results

# Usage
sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"
results = query_sequence_regions("genome_k21.rkdb", sequence)

# Show found k-mers
found_results = [r for r in results if r['exists']]
for result in found_results[:10]:  # Show first 10
    print(f"Position {result['position']}: {result['kmer']} ({result['count']} occurrences)")
```

### Comparative Querying

```python
def compare_databases(db1_path, db2_path, test_kmers):
    """Compare k-mer counts between two databases."""

    with Database() as db1, Database() as db2:
        db1.load(db1_path)
        db2.load(db2_path)

        comparison = []

        for kmer in test_kmers:
            result1 = db1.query(kmer)
            result2 = db2.query(kmer)

            comparison.append({
                'kmer': kmer,
                'db1_count': result1.count if result1.exists else 0,
                'db2_count': result2.count if result2.exists else 0,
                'db1_exists': result1.exists,
                'db2_exists': result2.exists,
                'ratio': result2.count / result1.count if result1.exists and result1.count > 0 else float('inf')
            })

        return comparison

def print_comparison(comparison, db1_name, db2_name):
    """Print database comparison results."""

    print(f"📊 Database Comparison: {db1_name} vs {db2_name}")
    print(f"{'K-mer':<25} {db1_name:<12} {db2_name:<12} {'Ratio':<8}")
    print("-" * 60)

    for comp in comparison:
        ratio_str = f"{comp['ratio']:.2f}" if comp['ratio'] != float('inf') else "∞"
        print(f"{comp['kmer']:<25} {comp['db1_count']:<12,} {comp['db2_count']:<12,} {ratio_str:<8}")

# Usage
test_kmers = ["ATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTA"]
comparison = compare_databases("genome1_k21.rkdb", "genome2_k21.rkdb", test_kmers)
print_comparison(comparison, "Genome1", "Genome2")
```

---

## Best Practices

### Query Performance Guidelines

1. **Use appropriate database loading**:
   - Memory-mapped for large databases, few queries
   - Preloaded for many queries, smaller databases

2. **Batch queries when possible**:
   - Group multiple queries together
   - Use file-based querying for large query sets

3. **Validate k-mers before querying**:
   - Check length matches database k-mer size
   - Ensure valid nucleotide characters

4. **Handle errors gracefully**:
   - Check for database existence
   - Handle invalid k-mer formats

### Memory Management

```python
def memory_efficient_querying(db_path, queries, batch_size=1000):
    """Query large number of k-mers efficiently."""

    results = []

    with Database() as db:
        db.load(db_path)  # Memory-mapped, efficient

        for i in range(0, len(queries), batch_size):
            batch = queries[i:i+batch_size]
            batch_results = []

            for kmer in batch:
                result = db.query(kmer)
                batch_results.append({
                    'kmer': kmer,
                    'count': result.count,
                    'exists': result.exists
                })

            results.extend(batch_results)
            print(f"Processed batch {i//batch_size + 1}/{(len(queries)-1)//batch_size + 1}")

    return results
```

### Error Handling Patterns

```python
class QueryManager:
    """Robust query manager with error handling."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.db = None
        self.stats = None

    def __enter__(self):
        self.db = Database()
        self.db.load(self.db_path)
        self.stats = self.db.get_stats()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()

    def validate_kmer(self, kmer):
        """Validate k-mer format."""
        if len(kmer) != self.stats.kmer_size:
            raise ValueError(f"K-mer length mismatch: expected {self.stats.kmer_size}, got {len(kmer)}")

        if not all(base.upper() in 'ATCG' for base in kmer):
            raise ValueError(f"Invalid characters in k-mer: {kmer}")

        return kmer.upper()

    def safe_query(self, kmer):
        """Safe query with validation."""
        try:
            validated_kmer = self.validate_kmer(kmer)
            result = self.db.query(validated_kmer)
            return {
                'success': True,
                'kmer': validated_kmer,
                'exists': result.exists,
                'count': result.count
            }
        except Exception as e:
            return {
                'success': False,
                'kmer': kmer,
                'error': str(e)
            }

# Usage
with QueryManager("genome_k21.rkdb") as qm:
    result = qm.safe_query("ATCGATCGATCGATCGATCG")
    if result['success']:
        print(f"Found: {result['count']}" if result['exists'] else "Not found")
    else:
        print(f"Error: {result['error']}")
```

---

## Quick Reference

### Python API
```python
from rustkmer import Database

# Load database
with Database() as db:
    db.load("database.rkdb")

    # Single query
    result = db.query("ATCGATCGATCGATCGATCG")

    # Get statistics
    stats = db.get_stats()

    # Batch queries
    # (see examples above)
```

### Command Line
```bash
# Single query
echo "ATCGATCGATCGATCGATCG" | rustkmer query -d database.rkdb --file -

# Batch query from file
rustkmer query -d database.rkdb -f queries.txt -o results.csv

# Database information
rustkmer info -d database.rkdb
```

---

## Need Help?

- **Documentation**: [Fuzzy Search](fuzzy-search.md) for pattern matching
- **API Reference**: [Python API](../api-reference/python/) for complete reference
- **Performance Tips**: [Performance Guide](performance-tips.md) for optimization
- **Troubleshooting**: [FAQ](../appendix/faq.md) for common issues