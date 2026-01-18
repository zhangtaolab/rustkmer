# Fuzzy Search Examples

Practical examples demonstrating RustKmer's fuzzy search functionality, from basic usage to advanced applications.

## Table of Contents

- [Basic Examples](#basic-examples)
- [Wildcards](#wildcards)
- [Mutation Tolerance](#mutation-tolerance)
- [Batch Processing](#batch-processing)
- [Export and Integration](#export-and-integration)
- [Real-world Applications](#real-world-applications)
- [Performance Examples](#performance-examples)

## Basic Examples

### Getting Started

```python
from pyrustkmer import Database, PyFuzzyQuery

# Load your database
db = PyDatabase("database.rkdb", LoadMode.Preload)
db.load("genome_k21.rkdb")

# Basic wildcard search
results = fuzzy.query_fuzzy("ATNNGTA")
print(f"Found {len(results)} matches for 'ATNNGTA'")

# Show first few results
for i, result in enumerate(results[:5]):
    print(f"  {i+1}. {result.kmer}: {result.count} (distance: {result.distance})")
```

### Simple Pattern Matching

```python
# Single wildcard - expands to 4 possibilities
results = fuzzy.query_fuzzy("ATN")
print(f"Single wildcard matches: {len(results)}")

# Double wildcard - expands to 16 possibilities
results = fuzzy.query_fuzzy("ATNN")
print(f"Double wildcard matches: {len(results)}")

# Triple wildcard - expands to 64 possibilities
results = fuzzy.query_fuzzy("ATNNN")
print(f"Triple wildcard matches: {len(results)}")
```

## Wildcards

### Progressive Wildcard Examples

```python
def analyze_wildcard_complexity(db, base_pattern):
    """Analyze results with increasing wildcard complexity."""

    wildcard_positions = [5, 10, 15]  # Add wildcards at different positions
    pattern_list = [base_pattern]

    for pos in wildcard_positions:
        # Add wildcard at specified position
        new_pattern = base_pattern[:pos] + 'N' + base_pattern[pos+1:]
        pattern_list.append(new_pattern)

    print("Wildcard Complexity Analysis:")
    print("=" * 50)

    for pattern in pattern_list:
        wildcard_count = pattern.count('N')
        theoretical_combinations = 4 ** wildcard_count

        print(f"\nPattern: {pattern}")
        print(f"Wildcards: {wildcard_count}")
        print(f"Theoretical combinations: {theoretical_combinations:,}")

        try:
            start_time = time.time()
            results = fuzzy.query_fuzzy(pattern)
            end_time = time.time()

            print(f"Actual matches: {len(results)}")
            print(f"Query time: {end_time - start_time:.3f}s")

            # Show top matches
            if results:
                results.sort(key=lambda x: x.count, reverse=True)
                print("Top 3 matches:")
                for i, result in enumerate(results[:3], 1):
                    print(f"  {i}. {result.kmer}: {result.count:,}")

        except Exception as e:
            print(f"Error: {e}")

# Usage
analyze_wildcard_complexity(db, "ATCGATCGATCGATCGATCGA")
```

### Biological Motif Search

```python
def find_promoter_elements(db, promoter_consensus="TATAAAW"):
    """
    Find promoter elements using consensus sequences.
    W = A or T (converted to ATN pattern)
    """

    # Convert IUPAC ambiguity codes to wildcards
    def convert_iupac_to_wildcard(sequence):
        iupac_map = {
            'W': 'AT',  # A or T
            'R': 'AG',  # A or G
            'Y': 'CT',  # C or T
            'S': 'GC',  # G or C
            'K': 'GT',  # G or T
            'M': 'AC',  # A or C
            'B': 'CGT', # C or G or T
            'D': 'AGT', # A or G or T
            'H': 'ACT', # A or C or T
            'V': 'ACG', # A or C or G
            'N': 'ATCG' # Any base
        }

        converted = sequence
        for code, bases in iupac_map.items():
            if len(bases) == 2:
                converted = converted.replace(code, 'N')  # Use wildcard
            else:
                converted = converted.replace(code, 'N')  # Complex patterns use N

        return converted

    # Convert consensus to wildcard pattern
    pattern = convert_iupac_to_wildcard(promoter_consensus)
    print(f"Searching for promoter consensus: {promoter_consensus}")
    print(f"Using pattern: {pattern}")

    results = fuzzy.query_fuzzy(pattern)

    # Filter by biological relevance
    significant_results = [r for r in results if r.count >= 50]
    significant_results.sort(key=lambda x: x.count, reverse=True)

    print(f"\nFound {len(significant_results)} significant promoter-like elements:")
    for i, result in enumerate(significant_results[:10], 1):
        gc_content = (result.kmer.count('G') + result.kmer.count('C')) / len(result.kmer)
        print(f"  {i:2d}. {result.kmer}: {result.count:,} (GC={gc_content:.2f})")

    return significant_results

# Usage
promoter_hits = find_promoter_elements(db, "TATAAAW")
```

## Mutation Tolerance

### Hamming Distance Search

```python
def analyze_mutation_spectrum(db, reference_kmer):
    """Analyze all mutations around a reference sequence."""

    print(f"Mutation Spectrum Analysis for: {reference_kmer}")
    print("=" * 60)

    # Search with increasing mutation distance
    for distance in range(4):  # 0, 1, 2, 3
        results = fuzzy.query_fuzzy(reference_kmer, max_distance=distance)

        # Filter by exact distance
        exact_distance_results = [r for r in results if r.distance == distance]

        total_count = sum(r.count for r in exact_distance_results)

        print(f"\nDistance {distance}: {len(exact_distance_results)} variants")
        print(f"Total occurrences: {total_count:,}")

        if exact_distance_results:
            # Sort by frequency
            exact_distance_results.sort(key=lambda x: x.count, reverse=True)

            print("Top 10 variants:")
            for i, result in enumerate(exact_distance_results[:10], 1):
                if result.distance > 0:
                    mutation = identify_mutation(reference_kmer, result.kmer)
                    print(f"  {i:2d}. {result.kmer}: {result.count:,} ({mutation})")
                else:
                    print(f"  {i:2d}. {result.kmer}: {result.count:,} (reference)")

def identify_mutation(ref, var):
    """Identify specific mutations between reference and variant."""
    mutations = []
    for i, (ref_base, var_base) in enumerate(zip(ref, var)):
        if ref_base != var_base:
            mutations.append(f"{ref_base}{i+1}{var_base}")
    return ", ".join(mutations)

# Usage
analyze_mutation_spectrum(db, "ATCGATCGATCGATCGATCGA")
```

### SNP Detection

```python
def detect_snp_variants(db, reference_kmer, min_frequency=0.01, min_count=10):
    """Detect SNP variants around a reference sequence."""

    print(f"SNP Detection for: {reference_kmer}")
    print(f"Minimum frequency: {min_frequency*100:.1f}%")
    print(f"Minimum count: {min_count}")
    print("-" * 50)

    # Find all single-mutation variants
    results = fuzzy.query_fuzzy(reference_kmer, max_distance=1)

    # Get reference count
    ref_result = db.query_exact(reference_kmer)
    ref_count = ref_result.count if ref_result.found else 0

    # Calculate total with variants
    variant_results = [r for r in results if r.distance == 1]
    total_count = ref_count + sum(r.count for r in variant_results)

    if total_count == 0:
        print("No occurrences found")
        return []

    print(f"Reference count: {ref_count:,}")
    print(f"Total with variants: {total_count:,}")

    # Analyze variants
    significant_variants = []

    for variant in variant_results:
        frequency = variant.count / total_count

        if variant.count >= min_count and frequency >= min_frequency:
            mutation = identify_mutation(reference_kmer, variant.kmer)

            significant_variants.append({
                'variant': variant.kmer,
                'count': variant.count,
                'frequency': frequency,
                'mutation': mutation,
                'effect': classify_mutation_effect(mutation)
            })

    # Sort by frequency
    significant_variants.sort(key=lambda x: x['frequency'], reverse=True)

    print(f"\nSignificant SNP variants ({len(significant_variants)}):")
    for i, variant in enumerate(significant_variants, 1):
        print(f"  {i:2d}. {variant['variant']}: {variant['count']:,} "
              f"({variant['frequency']*100:.2f}%)")
        print(f"      Mutation: {variant['mutation']}")
        print(f"      Effect: {variant['effect']}")

    return significant_variants

def classify_mutation_effect(mutation):
    """Classify the likely effect of a mutation."""
    # Simple classification based on mutation type
    if 'A>G' in mutation or 'G>A' in mutation:
        return "Transition (A↔G)"
    elif 'C>T' in mutation or 'T>C' in mutation:
        return "Transition (C↔T)"
    else:
        return "Transversion"

# Usage
snp_variants = detect_snp_variants(db, "ATCGATCGATCGATCGATCGA")
```

## Batch Processing

### Efficient Query Batch Processing

```python
import time
import json
from typing import List, Dict

def process_query_batch_optimized(db, queries: List[str],
                                 max_distance: int = 2,
                                 output_file: str = None):
    """
    Efficiently process a batch of fuzzy queries with optimization.

    Args:
        db: Database object
        queries: List of query patterns
        max_distance: Maximum mutation distance
        output_file: Optional JSON output file
    """

    print(f"Processing {len(queries)} queries...")
    print(f"Max distance: {max_distance}")

    # Group queries by complexity
    simple_queries = []   # ≤1 wildcard
    medium_queries = []   # 2-3 wildcards
    complex_queries = []  # >3 wildcards

    for query in queries:
        wildcard_count = query.count('N')
        if wildcard_count <= 1:
            simple_queries.append(query)
        elif wildcard_count <= 3:
            medium_queries.append(query)
        else:
            complex_queries.append(query)

    print(f"Query complexity distribution:")
    print(f"  Simple (≤1 wildcard): {len(simple_queries)}")
    print(f"  Medium (2-3 wildcards): {len(medium_queries)}")
    print(f"  Complex (>3 wildcards): {len(complex_queries)}")

    all_results = {}
    total_start_time = time.time()

    # Process simple queries with higher tolerance
    if simple_queries:
        print(f"\nProcessing {len(simple_queries)} simple queries...")
        for query in simple_queries:
            try:
                results = fuzzy.query_fuzzy(
                    query,
                    max_distance=max_distance,
                    parallel=len(simple_queries) > 10
                )
                all_results[query] = process_results(query, results)
            except Exception as e:
                all_results[query] = {"error": str(e)}
                print(f"  Error with '{query}': {e}")

    # Process medium queries with moderate limits
    if medium_queries:
        print(f"\nProcessing {len(medium_queries)} medium queries...")
        for query in medium_queries:
            try:
                results = fuzzy.query_fuzzy(
                    query,
                    max_distance=max_distance,
                    max_variants=5000,
                    parallel=True,
                    batch_size=500
                )
                all_results[query] = process_results(query, results)
            except Exception as e:
                all_results[query] = {"error": str(e)}
                print(f"  Error with '{query}': {e}")

    # Process complex queries with conservative limits
    if complex_queries:
        print(f"\nProcessing {len(complex_queries)} complex queries...")
        for query in complex_queries:
            try:
                results = fuzzy.query_fuzzy(
                    query,
                    max_distance=min(max_distance, 1),  # Reduce distance for complex
                    max_variants=1000,
                    batch_size=100
                )
                all_results[query] = process_results(query, results)
            except Exception as e:
                all_results[query] = {"error": str(e)}
                print(f"  Error with '{query}': {e}")

    total_time = time.time() - total_start_time

    # Generate summary
    successful_queries = sum(1 for r in all_results.values() if 'error' not in r)
    total_matches = sum(r.get('matches', 0) for r in all_results.values() if 'matches' in r)

    print(f"\nBatch Processing Summary:")
    print(f"  Total queries: {len(queries)}")
    print(f"  Successful: {successful_queries}")
    print(f"  Failed: {len(queries) - successful_queries}")
    print(f"  Total matches: {total_matches:,}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Average time per query: {total_time/len(queries):.3f}s")

    # Save results if requested
    if output_file:
        summary = {
            'metadata': {
                'total_queries': len(queries),
                'successful_queries': successful_queries,
                'total_matches': total_matches,
                'processing_time_seconds': total_time,
                'max_distance': max_distance
            },
            'results': all_results
        }

        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Results saved to: {output_file}")

    return all_results

def process_results(query, results):
    """Process and summarize query results."""
    return {
        'matches': len(results),
        'total_count': sum(r.count for r in results),
        'top_matches': [
            {
                'kmer': r.kmer,
                'count': r.count,
                'distance': r.distance,
                'match_type': r.match_type
            }
            for r in sorted(results, key=lambda x: x.count, reverse=True)[:10]
        ]
    }

# Usage
queries = [
    "ATNNGTA",
    "ANNNNNNGT",
    "GTCGATCNN",
    "ATCGATCGATCGATCGATCGA",
    "TTAGGCNNTAACGA"
]

results = process_query_batch_optimized(
    db,
    queries,
    max_distance=2,
    output_file="batch_fuzzy_results.json"
)
```

### Parallel Batch Processing

```python
def parallel_batch_processing(db, query_groups: Dict[str, List[str]],
                            max_distance: int = 2):
    """
    Process multiple query groups in parallel for maximum efficiency.

    Args:
        db: Database object
        query_groups: Dictionary of group_name -> list of queries
        max_distance: Maximum mutation distance
    """

    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    print(f"Processing {len(query_groups)} query groups in parallel...")

    def process_group(group_name, queries):
        """Process a single group of queries."""
        thread_id = threading.get_ident()
        print(f"[Thread-{thread_id}] Processing group '{group_name}' ({len(queries)} queries)")

        group_results = {}
        group_start_time = time.time()

        for query in queries:
            try:
                results = fuzzy.query_fuzzy(query, max_distance=max_distance)
                group_results[query] = {
                    'matches': len(results),
                    'total_count': sum(r.count for r in results),
                    'results': results[:5]  # Keep top 5 for summary
                }
            except Exception as e:
                group_results[query] = {'error': str(e)}

        group_time = time.time() - group_start_time
        print(f"[Thread-{thread_id}] Completed group '{group_name}' in {group_time:.2f}s")

        return group_name, group_results, group_time

    # Process groups in parallel
    all_results = {}
    total_start_time = time.time()

    with ThreadPoolExecutor(max_workers=min(4, len(query_groups))) as executor:
        # Submit all group processing tasks
        future_to_group = {
            executor.submit(process_group, group_name, queries): group_name
            for group_name, queries in query_groups.items()
        }

        # Collect results as they complete
        for future in as_completed(future_to_group):
            group_name, group_results, group_time = future.result()
            all_results[group_name] = group_results

    total_time = time.time() - total_start_time

    # Generate summary
    total_queries = sum(len(queries) for queries in query_groups.values())
    total_matches = sum(
        sum(result.get('matches', 0) for result in group.values())
        for group in all_results.values()
    )

    print(f"\nParallel Processing Summary:")
    print(f"  Groups processed: {len(query_groups)}")
    print(f"  Total queries: {total_queries}")
    print(f"  Total matches: {total_matches:,}")
    print(f"  Total time: {total_time:.2f}s")

    return all_results

# Usage
query_groups = {
    'promoters': ["TATAAA", "CAAT", "GGCCGG"],
    'restriction_sites': ["GAATTC", "GGATCC", "CTGCAG"],
    'random_patterns': ["ATNNGTA", "ANNNNNNGT", "GTCGATCNN"]
}

parallel_results = parallel_batch_processing(db, query_groups, max_distance=1)
```

## Export and Integration

### Export to Multiple Formats

```python
def export_fuzzy_results(results, base_filename, query_pattern):
    """Export fuzzy query results to multiple formats."""

    import pandas as pd
    import csv
    import json

    # Prepare data
    data = []
    for result in results:
        data.append({
            'query_pattern': query_pattern,
            'matched_kmer': result.kmer,
            'count': result.count,
            'distance': result.distance,
            'match_type': result.match_type,
            'gc_content': (result.kmer.count('G') + result.kmer.count('C')) / len(result.kmer)
        })

    df = pd.DataFrame(data)

    # Export to CSV
    csv_file = f"{base_filename}.csv"
    df.to_csv(csv_file, index=False)
    print(f"Exported {len(data)} results to {csv_file}")

    # Export to TSV
    tsv_file = f"{base_filename}.tsv"
    df.to_csv(tsv_file, sep='\t', index=False)
    print(f"Exported to {tsv_file}")

    # Export to JSON with metadata
    json_file = f"{base_filename}.json"
    json_data = {
        'query_metadata': {
            'pattern': query_pattern,
            'total_matches': len(results),
            'total_count': sum(r.count for r in results),
            'export_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'results': [
            {
                'kmer': r.kmer,
                'count': r.count,
                'distance': r.distance,
                'match_type': r.match_type,
                'gc_content': (r.kmer.count('G') + r.kmer.count('C')) / len(r.kmer)
            }
            for r in results
        ]
    }

    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"Exported to {json_file}")

    # Export to Excel (if openpyxl is available)
    try:
        excel_file = f"{base_filename}.xlsx"
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Results', index=False)

            # Create summary sheet
            summary_data = {
                'Metric': [
                    'Query Pattern',
                    'Total Matches',
                    'Total Count',
                    'Average Count',
                    'Max Count',
                    'Average Distance'
                ],
                'Value': [
                    query_pattern,
                    len(results),
                    sum(r.count for r in results),
                    sum(r.count for r in results) / len(results) if results else 0,
                    max(r.count for r in results) if results else 0,
                    sum(r.distance for r in results) / len(results) if results else 0
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

        print(f"Exported to {excel_file}")
    except ImportError:
        print("Excel export skipped (openpyxl not available)")

    return {
        'csv': csv_file,
        'tsv': tsv_file,
        'json': json_file,
        'excel': excel_file if 'excel_file' in locals() else None
    }

# Usage
results = fuzzy.query_fuzzy("ATNNGTA", max_distance=2)
exported_files = export_fuzzy_results(results, "fuzzy_query_results", "ATNNGTA")
```

### Database Integration Examples

```python
def integrate_with_sqlite(db, query_pattern, sqlite_db_path):
    """Integrate fuzzy query results with SQLite database."""

    import sqlite3
    import json

    # Perform fuzzy query
    results = fuzzy.query_fuzzy(query_pattern, max_distance=2)

    # Connect to SQLite database
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fuzzy_query_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_pattern TEXT,
            matched_kmer TEXT,
            count INTEGER,
            distance INTEGER,
            match_type TEXT,
            gc_content REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert results
    for result in results:
        gc_content = (result.kmer.count('G') + result.kmer.count('C')) / len(result.kmer)

        cursor.execute('''
            INSERT INTO fuzzy_query_results
            (query_pattern, matched_kmer, count, distance, match_type, gc_content)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            query_pattern,
            result.kmer,
            result.count,
            result.distance,
            result.match_type,
            gc_content
        ))

    # Create query summary table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS query_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_pattern TEXT UNIQUE,
            total_matches INTEGER,
            total_count INTEGER,
            average_count REAL,
            max_count INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert or update summary
    total_matches = len(results)
    total_count = sum(r.count for r in results)
    avg_count = total_count / total_matches if total_matches > 0 else 0
    max_count = max(r.count for r in results) if results else 0

    cursor.execute('''
        INSERT OR REPLACE INTO query_summaries
        (query_pattern, total_matches, total_count, average_count, max_count)
        VALUES (?, ?, ?, ?, ?)
    ''', (query_pattern, total_matches, total_count, avg_count, max_count))

    conn.commit()
    conn.close()

    print(f"Integrated {len(results)} results into SQLite database: {sqlite_db_path}")

    # Query example
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    print("\nTop 5 results from database:")
    cursor.execute('''
        SELECT matched_kmer, count, distance, match_type
        FROM fuzzy_query_results
        WHERE query_pattern = ?
        ORDER BY count DESC
        LIMIT 5
    ''', (query_pattern,))

    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} (distance: {row[2]}, type: {row[3]})")

    conn.close()

# Usage
integrate_with_sqlite(db, "ATNNGTA", "fuzzy_results.sqlite")
```

## Real-world Applications

### Primer Design with Fuzzy Matching

```python
class PrimerDesigner:
    """Design PCR primers with fuzzy matching capabilities."""

    def __init__(self, database):
        self.db = database

    def find_primer_candidates(self, target_sequence, primer_length=20,
                             max_mismatches=2, min_gc=0.4, max_gc=0.6):
        """
        Find optimal primer candidates in target sequence.

        Args:
            target_sequence: DNA sequence to search for primers
            primer_length: Length of primers to design
            max_mismatches: Maximum mismatches tolerated
            min_gc, max_gc: Acceptable GC content range
        """

        print(f"Designing {primer_length}-mer primers from target sequence...")
        print(f"Target length: {len(target_sequence)}")

        candidates = []

        # Slide window to extract potential primers
        for i in range(len(target_sequence) - primer_length + 1):
            primer = target_sequence[i:i+primer_length]

            # Calculate basic properties
            gc_content = (primer.count('G') + primer.count('C')) / primer_length

            if not (min_gc <= gc_content <= max_gc):
                continue  # Skip if GC content not in range

            # Search for matches in database
            try:
                results = self.fuzzy.query_fuzzy(primer, max_distance=max_mismatches)

                if results:
                    # Calculate binding strength metrics
                    exact_matches = sum(1 for r in results if r.distance == 0)
                    total_binding = sum(r.count for r in results if r.distance <= 1)

                    # Calculate specificity (fewer off-targets is better)
                    off_target_penalty = sum(r.count for r in results if r.distance > 1)

                    # Quality score (higher is better)
                    quality_score = (exact_matches * 10 +
                                   total_binding * 2 -
                                   off_target_penalty * 0.1)

                    candidates.append({
                        'sequence': primer,
                        'position': i,
                        'gc_content': gc_content,
                        'exact_matches': exact_matches,
                        'total_binding': total_binding,
                        'off_target_penalty': off_target_penalty,
                        'quality_score': quality_score,
                        'top_matches': results[:5]
                    })

            except Exception as e:
                print(f"Error processing primer at position {i}: {e}")
                continue

        # Sort by quality score
        candidates.sort(key=lambda x: x['quality_score'], reverse=True)

        print(f"\nFound {len(candidates)} primer candidates")
        print("\nTop 10 candidates:")

        for i, primer in enumerate(candidates[:10], 1):
            print(f"\n{i:2d}. {primer['sequence']}")
            print(f"    Position: {primer['position']}")
            print(f"    GC content: {primer['gc_content']:.2f}")
            print(f"    Exact matches: {primer['exact_matches']}")
            print(f"    Binding strength: {primer['total_binding']:,}")
            print(f"    Quality score: {primer['quality_score']:.1f}")

            if primer['top_matches']:
                print(f"    Top database matches:")
                for j, match in enumerate(primer['top_matches'][:3], 1):
                    print(f"      {j}. {match.kmer}: {match.count} (dist: {match.distance})")

        return candidates

    def design_primer_pair(self, target_sequence, product_size_range=(100, 1000)):
        """
        Design forward and reverse primer pair.

        Args:
            target_sequence: Target DNA sequence
            product_size_range: Desired PCR product size range (min, max)
        """

        min_size, max_size = product_size_range
        print(f"Designing primer pair for {min_size}-{max_size}bp product")

        # Find forward primers (first half of sequence)
        forward_candidates = self.find_primer_candidates(
            target_sequence[:len(target_sequence)//2],
            primer_length=20,
            max_mismatches=1
        )

        # Find reverse primers (second half, reverse complement)
        reverse_sequence = self.reverse_complement(target_sequence[len(target_sequence)//2:])
        reverse_candidates = self.find_primer_candidates(
            reverse_sequence,
            primer_length=20,
            max_mismatches=1
        )

        # Find best pairs
        best_pairs = []
        for forward in forward_candidates[:20]:  # Check top forward primers
            for reverse in reverse_candidates[:20]:  # Against top reverse primers

                # Calculate product size
                product_size = (len(target_sequence) - reverse['position'] -
                               forward['position'] - 20)  # Approximate

                if min_size <= product_size <= max_size:
                    pair_score = (forward['quality_score'] +
                                reverse['quality_score']) / 2

                    best_pairs.append({
                        'forward_primer': forward['sequence'],
                        'reverse_primer': self.reverse_complement(reverse['sequence']),
                        'product_size': product_size,
                        'pair_score': pair_score,
                        'forward_position': forward['position'],
                        'reverse_position': len(target_sequence) - reverse['position'] - 20
                    })

        # Sort by pair score
        best_pairs.sort(key=lambda x: x['pair_score'], reverse=True)

        print(f"\nFound {len(best_pairs)} suitable primer pairs")
        print("\nTop 5 pairs:")

        for i, pair in enumerate(best_pairs[:5], 1):
            print(f"\n{i:2d}. Forward:  {pair['forward_primer']}")
            print(f"    Reverse:  {pair['reverse_primer']}")
            print(f"    Product:  {pair['product_size']}bp")
            print(f"    Score:    {pair['pair_score']:.1f}")
            print(f"    Positions: {pair['forward_position']}-{pair['reverse_position']}")

        return best_pairs

    def reverse_complement(self, sequence):
        """Generate reverse complement of DNA sequence."""
        complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
        return ''.join(complement[base] for base in reversed(sequence))

# Usage
designer = PrimerDesigner(db)

# Example target sequence (could be from a gene of interest)
target_seq = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG" * 10

# Find single primers
primer_candidates = designer.find_primer_candidates(target_seq, primer_length=21)

# Find primer pairs
primer_pairs = designer.design_primer_pair(target_seq, product_size_range=(200, 500))
```

### K-mer Based Phylogenetic Analysis

```python
def phylogenetic_distance_analysis(db, sequences, labels=None):
    """
    Calculate phylogenetic distances between sequences using k-mer fuzzy matching.

    Args:
        db: Database with reference k-mers
        sequences: List of query sequences
        labels: Optional labels for sequences
    """

    if labels is None:
        labels = [f"Seq_{i+1}" for i in range(len(sequences))]

    print(f"Analyzing phylogenetic relationships between {len(sequences)} sequences")

    # Extract k-mers from each sequence (assuming k=21)
    kmer_size = 21
    sequence_kmers = {}

    for i, sequence in enumerate(sequences):
        # Extract non-overlapping k-mers
        kmers = [sequence[j:j+kmer_size]
                for j in range(0, len(sequence) - kmer_size + 1, kmer_size)]
        sequence_kmers[labels[i]] = kmers
        print(f"  {labels[i]}: {len(kmers)} k-mers extracted")

    # Calculate distance matrix
    print("\nCalculating pairwise distances...")
    distance_matrix = {}

    for seq1_label, seq1_kmers in sequence_kmers.items():
        distance_matrix[seq1_label] = {}

        for seq2_label, seq2_kmers in sequence_kmers.items():
            if seq1_label == seq2_label:
                distance_matrix[seq1_label][seq2_label] = 0.0
                continue

            # Calculate shared and unique k-mers
            shared_count = 0
            total_query_count = 0

            for kmer in seq1_kmers:
                try:
                    # Find close matches in database
                    results = fuzzy.query_fuzzy(kmer, max_distance=1)
                    matches = [r.kmer for r in results if r.distance <= 1]

                    # Check if any matches are in seq2
                    for seq2_kmer in seq2_kmers:
                        if seq2_kmer in matches:
                            shared_count += 1
                            break

                    total_query_count += 1

                except Exception:
                    total_query_count += 1

            # Calculate distance (Jaccard-like distance)
            if total_query_count > 0:
                similarity = shared_count / total_query_count
                distance = 1.0 - similarity
            else:
                distance = 1.0

            distance_matrix[seq1_label][seq2_label] = distance

    # Display distance matrix
    print("\nDistance Matrix:")
    print("-" * 60)

    # Header
    header = " " * 15 + "  ".join(f"{label:10}" for label in labels)
    print(header)

    # Rows
    for seq1_label in labels:
        row = f"{seq1_label:15}"
        for seq2_label in labels:
            distance = distance_matrix[seq1_label][seq2_label]
            row += f"  {distance:10.3f}"
        print(row)

    # Find most similar pairs
    print("\nMost similar sequence pairs:")
    similarities = []

    for i in range(len(labels)):
        for j in range(i+1, len(labels)):
            seq1_label = labels[i]
            seq2_label = labels[j]
            distance = distance_matrix[seq1_label][seq2_label]
            similarity = 1.0 - distance

            similarities.append((similarity, seq1_label, seq2_label))

    similarities.sort(reverse=True)

    for similarity, seq1, seq2 in similarities[:5]:
        print(f"  {seq1} - {seq2}: {similarity:.3f}")

    return distance_matrix

# Usage with example sequences
sequences = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG" * 10,  # Sequence 1
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATTT" * 10,  # Sequence 2 (1 mutation)
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCC" * 10,  # Sequence 3 (1 mutation)
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT" * 10,  # Sequence 4 (different)
]

labels = ["Human", "Chimpanzee", "Gorilla", "Mouse"]

distance_matrix = phylogenetic_distance_analysis(db, sequences, labels)
```

## Performance Examples

### Performance Benchmarking

```python
import time
import psutil
import matplotlib.pyplot as plt

class FuzzyQueryBenchmark:
    """Benchmark fuzzy query performance under various conditions."""

    def __init__(self, database):
        self.db = database
        self.results = []

    def benchmark_wildcard_complexity(self, base_patterns):
        """Benchmark performance with increasing wildcard complexity."""

        print("Benchmarking Wildcard Complexity")
        print("=" * 50)

        complexity_levels = []
        query_times = []
        variant_counts = []
        memory_usage = []

        for pattern in base_patterns:
            wildcard_count = pattern.count('N')
            theoretical_variants = 4 ** wildcard_count

            print(f"\nPattern: {pattern}")
            print(f"Wildcards: {wildcard_count}")
            print(f"Theoretical variants: {theoretical_variants:,}")

            try:
                # Measure memory before query
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024  # MB

                # Time the query
                start_time = time.time()
                results = self.fuzzy.query_fuzzy(pattern, max_variants=theoretical_variants)
                end_time = time.time()

                # Measure memory after query
                memory_after = process.memory_info().rss / 1024 / 1024  # MB

                query_time = end_time - start_time
                memory_used = memory_after - memory_before

                print(f"  Results: {len(results)}")
                print(f"  Query time: {query_time:.3f}s")
                print(f"  Memory used: {memory_used:.1f}MB")

                complexity_levels.append(wildcard_count)
                query_times.append(query_time)
                variant_counts.append(len(results))
                memory_usage.append(memory_used)

                # Store detailed results
                self.results.append({
                    'pattern': pattern,
                    'wildcards': wildcard_count,
                    'theoretical_variants': theoretical_variants,
                    'actual_results': len(results),
                    'query_time': query_time,
                    'memory_mb': memory_used
                })

            except Exception as e:
                print(f"  Error: {e}")

        # Plot results
        self.plot_complexity_results(complexity_levels, query_times, variant_counts, memory_usage)

    def benchmark_mutation_distance(self, reference_sequence):
        """Benchmark performance with increasing mutation distance."""

        print("\nBenchmarking Mutation Distance")
        print("=" * 50)

        distances = []
        query_times = []
        result_counts = []

        for distance in range(6):  # 0 to 5
            print(f"\nTesting distance {distance}...")

            try:
                start_time = time.time()
                results = self.fuzzy.query_fuzzy(reference_sequence, max_distance=distance)
                end_time = time.time()

                query_time = end_time - start_time

                # Filter by exact distance
                exact_distance_results = [r for r in results if r.distance == distance]

                print(f"  Distance {distance}: {len(exact_distance_results)} results")
                print(f"  Query time: {query_time:.3f}s")

                distances.append(distance)
                query_times.append(query_time)
                result_counts.append(len(exact_distance_results))

            except Exception as e:
                print(f"  Error: {e}")

        # Plot mutation distance results
        self.plot_distance_results(distances, query_times, result_counts)

    def benchmark_batch_processing(self, query_sets):
        """Benchmark batch processing performance."""

        print("\nBenchmarking Batch Processing")
        print("=" * 50)

        batch_sizes = []
        individual_times = []
        batch_times = []
        speedups = []

        for batch_size in query_sets:
            queries = batch_size['queries']
            batch_label = batch_size['label']

            print(f"\nBatch: {batch_label} ({len(queries)} queries)")

            # Individual processing
            print("  Individual processing...")
            start_time = time.time()
            individual_results = []
            for query in queries:
                try:
                    results = self.fuzzy.query_fuzzy(query, max_distance=1)
                    individual_results.append(results)
                except:
                    individual_results.append([])
            individual_time = time.time() - start_time

            # Batch processing
            print("  Batch processing...")
            start_time = time.time()
            try:
                batch_results = self.db.fuzzy_query_batch(queries, max_distance=1)
                batch_time = time.time() - start_time
            except:
                # Fallback to individual processing if batch not available
                batch_time = individual_time

            speedup = individual_time / batch_time if batch_time > 0 else 1.0

            print(f"  Individual time: {individual_time:.3f}s")
            print(f"  Batch time: {batch_time:.3f}s")
            print(f"  Speedup: {speedup:.2f}x")

            batch_sizes.append(len(queries))
            individual_times.append(individual_time)
            batch_times.append(batch_time)
            speedups.append(speedup)

        # Plot batch processing results
        self.plot_batch_results(batch_sizes, individual_times, batch_times, speedups)

    def plot_complexity_results(self, complexity, times, variants, memory):
        """Plot wildcard complexity benchmark results."""

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

        # Query time vs complexity
        ax1.plot(complexity, times, 'bo-')
        ax1.set_xlabel('Number of Wildcards')
        ax1.set_ylabel('Query Time (seconds)')
        ax1.set_title('Query Time vs Wildcard Complexity')
        ax1.grid(True)

        # Results vs complexity
        ax2.plot(complexity, variants, 'go-')
        ax2.set_xlabel('Number of Wildcards')
        ax2.set_ylabel('Number of Results')
        ax2.set_title('Results vs Wildcard Complexity')
        ax2.grid(True)

        # Memory usage vs complexity
        ax3.plot(complexity, memory, 'ro-')
        ax3.set_xlabel('Number of Wildcards')
        ax3.set_ylabel('Memory Usage (MB)')
        ax3.set_title('Memory Usage vs Wildcard Complexity')
        ax3.grid(True)

        # Theoretical vs actual variants
        theoretical = [4**c for c in complexity]
        ax4.loglog(complexity, theoretical, 'b-', label='Theoretical', alpha=0.7)
        ax4.loglog(complexity, variants, 'ro-', label='Actual')
        ax4.set_xlabel('Number of Wildcards')
        ax4.set_ylabel('Number of Variants')
        ax4.set_title('Theoretical vs Actual Variants')
        ax4.legend()
        ax4.grid(True)

        plt.tight_layout()
        plt.savefig('wildcard_complexity_benchmark.png', dpi=300, bbox_inches='tight')
        plt.show()

    def plot_distance_results(self, distances, times, counts):
        """Plot mutation distance benchmark results."""

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Query time vs distance
        ax1.plot(distances, times, 'bo-')
        ax1.set_xlabel('Mutation Distance')
        ax1.set_ylabel('Query Time (seconds)')
        ax1.set_title('Query Time vs Mutation Distance')
        ax1.grid(True)

        # Results vs distance
        ax2.plot(distances, counts, 'go-')
        ax2.set_xlabel('Mutation Distance')
        ax2.set_ylabel('Number of Results')
        ax2.set_title('Results vs Mutation Distance')
        ax2.grid(True)

        plt.tight_layout()
        plt.savefig('mutation_distance_benchmark.png', dpi=300, bbox_inches='tight')
        plt.show()

    def plot_batch_results(self, sizes, individual_times, batch_times, speedups):
        """Plot batch processing benchmark results."""

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Time comparison
        ax1.plot(sizes, individual_times, 'bo-', label='Individual Processing')
        ax1.plot(sizes, batch_times, 'go-', label='Batch Processing')
        ax1.set_xlabel('Batch Size')
        ax1.set_ylabel('Processing Time (seconds)')
        ax1.set_title('Processing Time Comparison')
        ax1.legend()
        ax1.grid(True)

        # Speedup
        ax2.plot(sizes, speedups, 'ro-')
        ax2.set_xlabel('Batch Size')
        ax2.set_ylabel('Speedup Factor')
        ax2.set_title('Batch Processing Speedup')
        ax2.grid(True)
        ax2.axhline(y=1, color='k', linestyle='--', alpha=0.5)

        plt.tight_layout()
        plt.savefig('batch_processing_benchmark.png', dpi=300, bbox_inches='tight')
        plt.show()

# Usage
benchmark = FuzzyQueryBenchmark(db)

# Test wildcard complexity
base_patterns = [
    "ATCGATCGATCGATCGATCGA",      # 0 wildcards
    "ATCGATCGATCGATCGATCNG",      # 1 wildcard
    "ATCGATCGATCGATCGATCNN",      # 2 wildcards
    "ATCGATCGATCGATCNNNTCNN",      # 4 wildcards
    "ATCGATCNNNNNNCNNNTCNN",      # 6 wildcards
]

benchmark.benchmark_wildcard_complexity(base_patterns)

# Test mutation distance
reference_seq = "ATCGATCGATCGATCGATCGA"
benchmark.benchmark_mutation_distance(reference_seq)

# Test batch processing
query_sets = [
    {
        'label': 'Small',
        'queries': ["ATNNGTA", "ANNNNNNGT", "GTCGATCNN"]
    },
    {
        'label': 'Medium',
        'queries': ["ATNNGTA", "ANNNNNNGT", "GTCGATCNN"] * 5
    },
    {
        'label': 'Large',
        'queries': ["ATNNGTA", "ANNNNNNGT", "GTCGATCNN"] * 20
    }
]

benchmark.benchmark_batch_processing(query_sets)
```

This comprehensive examples file demonstrates practical applications of RustKmer's fuzzy search functionality, from basic usage to advanced real-world scenarios like primer design, phylogenetic analysis, and performance benchmarking.