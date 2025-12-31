# Error Recovery and Graceful Degradation

This guide demonstrates how to handle errors gracefully and recover from common issues when using the RustKmer Python API.

## Overview

RustKmer provides comprehensive error handling with structured exception types and recovery mechanisms. This document shows practical examples of error handling patterns.

## Exception Hierarchy

```python
# Base exception
class RustKmerError(Exception):
    """Base exception for all RustKmer errors."""
    pass

# Specific exception types
class SequenceError(RustKmerError):
    """Raised for invalid DNA sequences."""
    pass

class DatabaseError(RustKmerError):
    """Raised for database-related errors."""
    pass

class QueryError(RustKmerError):
    """Raised for query operation errors."""
    pass

class ValidationError(RustKmerError):
    """Raised for parameter validation errors."""
    pass

class MergeError(RustKmerError):
    """Raised for database merge errors."""
    pass

class ExportError(RustKmerError):
    """Raised for export operation errors."""
    pass

class FuzzyQueryError(RustKmerError):
    """Raised for fuzzy query errors."""
    pass

class StatsError(RustKmerError):
    """Raised for statistics calculation errors."""
    pass

class KmerCountingError(RustKmerError):
    """Raised for k-mer counting errors."""
    pass

class EncodingError(RustKmerError):
    """Raised for encoding/decoding errors."""
    pass
```

## Common Error Scenarios and Recovery Strategies

### 1. Invalid k-mer Size

```python
import rustkmer

def safe_create_counter(k):
    """Safely create a k-mer counter with validation."""
    try:
        counter = rustkmer.KmerCounter(k=k)
        return counter
    except (ValueError, OverflowError) as e:
        print(f"Invalid k-mer size {k}: {e}")
        # Fall back to default size
        print("Using default k=31")
        return rustkmer.KmerCounter(k=31)

# Example usage
counter = safe_create_counter(100)  # Invalid size
print(f"Created counter with k={counter.get_k()}")
```

### 2. Sequence Validation

```python
def validate_dna_sequence(sequence):
    """Validate and clean DNA sequence."""
    # Convert to uppercase
    sequence = sequence.upper()

    # Check for invalid characters
    invalid_chars = set(sequence) - set('ATCG')
    if invalid_chars:
        print(f"Warning: Invalid characters found: {invalid_chars}")
        # Remove invalid characters
        sequence = ''.join(c for c in sequence if c in 'ATCG')
        print(f"Cleaned sequence length: {len(sequence)}")

    return sequence

def safe_count_sequence(counter, sequence):
    """Safely count k-mers in a sequence."""
    try:
        # Clean the sequence first
        clean_seq = validate_dna_sequence(sequence)

        if len(clean_seq) < counter.get_k():
            print(f"Warning: Sequence too short for k={counter.get_k()}")
            return None

        counter.count_string(clean_seq)
        return counter.get_total_count()

    except SequenceError as e:
        print(f"Sequence error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

### 3. Database Loading with Fallback

```python
import os
from rustkmer.error_handling import retry_on_io_error, error_context

def safe_load_database(file_path, max_retries=3):
    """Load database with retry and fallback strategies."""

    @error_context("database_load", strategies=[retry_on_io_error(max_retries)])
    def load_with_retry(path):
        db = rustkmer.Database()
        db.load(path)
        return db

    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Database file not found: {file_path}")

    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise DatabaseError(f"Database file is empty: {file_path}")

    try:
        return load_with_retry(file_path)
    except Exception as e:
        print(f"Failed to load database after {max_retries} attempts: {e}")

        # Try to recover with file system check
        if not os.access(file_path, os.R_OK):
            raise DatabaseError(f"No read permission for file: {file_path}")

        raise
```

### 4. Memory Pressure Handling

```python
import psutil
from rustkmer.performance import DatabaseCache

def process_large_sequence(sequence, k=31, memory_limit_gb=4):
    """Process large sequence with memory management."""

    # Check available memory
    available_memory = psutil.virtual_memory().available / (1024**3)
    if available_memory < memory_limit_gb:
        print(f"Warning: Low memory ({available_memory:.1f}GB available)")

    # Use caching for efficiency
    cache = DatabaseCache(max_memory_mb=memory_limit_gb * 1024 // 2)

    try:
        # Process in chunks if sequence is very large
        chunk_size = 1000000  # 1MB chunks
        if len(sequence) > chunk_size:
            print(f"Processing {len(sequence)} bp in chunks...")

            counter = rustkmer.KmerCounter(k=k)
            for i in range(0, len(sequence), chunk_size):
                chunk = sequence[i:i+chunk_size]
                counter.count_string(chunk)

                # Check memory usage periodically
                if i % (chunk_size * 10) == 0:
                    memory_usage = psutil.Process().memory_info().rss / (1024**2)
                    if memory_usage > memory_limit_gb * 1024 * 0.8:
                        print(f"Memory usage high ({memory_usage:.1f}MB), optimizing...")
                        cache.optimize()

            return counter
        else:
            # For smaller sequences, process normally
            counter = rustkmer.KmerCounter(k=k)
            counter.count_string(sequence)
            return counter

    except MemoryError:
        print("Out of memory! Try reducing k-mer size or sequence length.")
        raise
    except Exception as e:
        print(f"Error processing sequence: {e}")
        raise
```

### 5. Concurrent Access Error Handling

```python
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def safe_concurrent_query(database_path, queries, max_workers=4):
    """Perform concurrent queries with error isolation."""

    def query_worker(query):
        """Worker function for querying."""
        try:
            db = rustkmer.Database()
            db.load(database_path)
            result = db.query(query)
            return query, result, None
        except Exception as e:
            return query, None, str(e)

    results = []
    errors = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all queries
        future_to_query = {
            executor.submit(query_worker, q): q
            for q in queries
        }

        # Collect results as they complete
        for future in as_completed(future_to_query):
            query, result, error = future.result()

            if error:
                print(f"Query '{query[:20]}...' failed: {error}")
                errors.append((query, error))
            else:
                results.append((query, result))

    return results, errors

# Example usage
queries = ["ATCGATCGATCGATCGATCGATC", "GCTAGCTAGCTAGCTAGCTAGCT"] * 100
results, errors = safe_concurrent_query("database.rkdb", queries)

print(f"Successfully processed {len(results)} queries")
if errors:
    print(f"Failed queries: {len(errors)}")
```

### 6. Batch Processing with Error Recovery

```python
from rustkmer.performance import BatchProcessor

def process_file_batch(file_paths, output_dir, batch_size=10):
    """Process multiple files in batches with error recovery."""

    processor = BatchProcessor(batch_size=batch_size)

    for batch_start in range(0, len(file_paths), batch_size):
        batch_end = min(batch_start + batch_size, len(file_paths))
        batch_files = file_paths[batch_start:batch_end]

        print(f"Processing batch {batch_start//batch_size + 1}: {len(batch_files)} files")

        batch_results = []
        batch_errors = []

        for file_path in batch_files:
            try:
                # Process individual file
                counter = rustkmer.KmerCounter(k=31)
                counter.count_file(file_path)

                # Save result
                output_path = os.path.join(
                    output_dir,
                    f"{os.path.basename(file_path)}_k31.rkdb"
                )
                counter.save_to_database(output_path)

                batch_results.append(output_path)

            except Exception as e:
                print(f"  Error processing {file_path}: {e}")
                batch_errors.append((file_path, str(e)))
                continue

        # Report batch status
        print(f"  Batch complete: {len(batch_results)} successful, {len(batch_errors)} errors")

        # Save error report for this batch
        if batch_errors:
            error_report_path = os.path.join(
                output_dir,
                f"batch_errors_{batch_start//batch_size + 1}.txt"
            )
            with open(error_report_path, 'w') as f:
                for file_path, error in batch_errors:
                    f.write(f"{file_path}: {error}\n")
```

### 7. Fuzzy Query with Graceful Degradation

```python
def adaptive_fuzzy_query(database, query, max_distance=5):
    """Perform fuzzy query with adaptive parameters."""

    try:
        db = rustkmer.Database()
        db.load(database)
        fuzzy = rustkmer.FuzzyQuery(db)

        # Start with strict distance
        results = fuzzy.query(query, max_distance=1)

        # If no results, gradually increase distance
        if not results and max_distance > 1:
            print("No matches with distance=1, trying looser parameters...")

            for distance in range(2, max_distance + 1):
                results = fuzzy.query(query, max_distance=distance)
                if results:
                    print(f"Found {len(results)} matches with distance={distance}")
                    break

        return results

    except FuzzyQueryError as e:
        print(f"Fuzzy query error: {e}")

        # Fallback to exact query
        try:
            db = rustkmer.Database()
            db.load(database)
            exact_result = db.query(query)
            if exact_result > 0:
                print(f"Fuzzy query failed, but exact match found: {exact_result}")
                return [(query, exact_result)]
        except Exception:
            pass

        return []
```

### 8. Statistics Calculation with Validation

```python
def get_validated_stats(counter_or_db):
    """Get statistics with validation and error handling."""

    try:
        stats = counter_or_db.get_stats()

        # Validate stats structure
        required_keys = ['k', 'total_kmers', 'unique_kmers']
        for key in required_keys:
            if key not in stats:
                raise StatsError(f"Missing required statistic: {key}")

        # Validate values are reasonable
        if stats['k'] <= 0 or stats['k'] > 31:
            raise StatsError(f"Invalid k-mer size: {stats['k']}")

        if stats['total_kmers'] < 0 or stats['unique_kmers'] < 0:
            raise StatsError("Negative k-mer counts detected")

        if stats['unique_kmers'] > stats['total_kmers']:
            raise StatsError("More unique than total k-mers")

        return stats

    except StatsError as e:
        print(f"Statistics validation failed: {e}")
        return None
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return None
```

## Best Practices

1. **Always validate inputs** before processing
2. **Use try-except blocks** around all database operations
3. **Check file existence and permissions** before loading
4. **Monitor memory usage** for large operations
5. **Implement retry logic** for transient errors
6. **Log errors** for debugging
7. **Provide fallback options** when possible
8. **Clean up resources** in finally blocks

## Complete Example

```python
import rustkmer
import os
from rustkmer.error_handling import error_context, safe_execute

def robust_kmer_analysis(sequence_file, output_dir, k=31):
    """Complete example of robust k-mer analysis."""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Step 1: Validate input
        if not os.path.exists(sequence_file):
            raise FileNotFoundError(f"Input file not found: {sequence_file}")

        file_size = os.path.getsize(sequence_file)
        if file_size == 0:
            raise ValueError(f"Input file is empty: {sequence_file}")

        print(f"Processing {sequence_file} ({file_size} bytes)...")

        # Step 2: Create counter with error handling
        with error_context("create_counter"):
            counter = rustkmer.KmerCounter(k=k)

        # Step 3: Process file with monitoring
        with error_context("count_kmers"):
            counter.count_file(sequence_file)

        # Step 4: Get statistics with validation
        stats = safe_execute(
            counter.get_stats,
            default_value=None,
            log_errors=True
        )

        if stats is None:
            raise RuntimeError("Failed to get statistics")

        print(f"Counted {stats['total_kmers']} k-mers")

        # Step 5: Save database with error handling
        output_path = os.path.join(output_dir, f"output_k{k}.rkdb")

        with error_context("save_database"):
            counter.save_to_database(output_path)

        print(f"Results saved to: {output_path}")

        # Step 6: Verify output
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print("Analysis completed successfully!")
            return output_path
        else:
            raise RuntimeError("Output file was not created properly")

    except Exception as e:
        print(f"Analysis failed: {e}")

        # Log error for debugging
        error_log_path = os.path.join(output_dir, "error.log")
        with open(error_log_path, 'w') as f:
            f.write(f"Error: {e}\n")
            f.write(f"Input: {sequence_file}\n")
            f.write(f"K-mer size: {k}\n")

        return None

# Usage example
result = robust_kmer_analysis(
    sequence_file="input.fasta",
    output_dir="analysis_output",
    k=21
)

if result:
    print("Success!")
else:
    print("Check error log for details")
```

This guide demonstrates comprehensive error handling patterns to make your RustKmer applications robust and reliable.