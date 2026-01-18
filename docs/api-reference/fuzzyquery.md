# Fuzzy Query

The fuzzy query functionality allows searching for k-mers within a specified Hamming distance, enabling tolerant matching for sequencing errors, natural variations, and related sequences.

## Overview

Fuzzy queries find k-mers that are similar to a query sequence within a specified mutation tolerance. Unlike exact queries, fuzzy queries can handle:

- Sequencing errors in genomic data
- Natural variations and mutations
- Ambiguous positions in k-mers
- Discovery of sequence variants

The implementation uses the Hamming distance metric, which counts the number of positions at which two k-mers differ.

## Classes

### FuzzyMatchResult

Represents a single k-mer match within mutation tolerance.

```python
@dataclass
class FuzzyMatchResult:
    """Represents a single k-mer match within mutation tolerance."""

    kmer: str                          # Matched k-mer sequence
    count: int                         # Number of occurrences in database
    distance: int                      # Hamming distance from query (0 = exact)
    mutations: List[str]               # List of mutation descriptions
```

**Attributes:**
- `kmer` (str): The matched k-mer sequence found in the database
- `count` (int): Number of occurrences of this k-mer in the database
- `distance` (int): Hamming distance from the query k-mer (0 = exact match)
- `mutations` (List[str]): List of mutations formatted as "X>N" (e.g., "A>T")

**Example:**
```python
from rustkmer.fuzzy_query import FuzzyMatchResult

match = FuzzyMatchResult(
    kmer="ATGG",
    count=42,
    distance=1,
    mutations=["A>T"]
)
print(f"Found {match.kmer} with {match.count} occurrences")
print(f"Distance {match.distance} with mutations: {', '.join(match.mutations)}")
```

### FuzzyQueryResult

Contains all matches for a single fuzzy query operation.

```python
@dataclass
class FuzzyQueryResult:
    """Contains all matches for a single fuzzy query operation."""

    query_kmer: str                    # Original query k-mer
    mutations_allowed: int             # Maximum mutations allowed
    total_matches: int                 # Total number of matches found
    exact_matches: int                 # Number of exact matches (distance=0)
    fuzzy_matches: int                 # Number of fuzzy matches (distance>0)
    max_variants: Optional[int]        # Maximum variants that could be generated
    matches: List[FuzzyMatchResult]    # List of all matches
```

**Methods:**

#### `get_exact_matches() -> List[FuzzyMatchResult]`
Get only exact matches (distance=0).

**Returns:**
- `List[FuzzyMatchResult]`: List of exact matches

#### `get_fuzzy_matches() -> List[FuzzyMatchResult]`
Get only fuzzy matches (distance>0).

**Returns:**
- `List[FuzzyMatchResult]`: List of fuzzy matches

#### `get_matches_by_distance(distance: int) -> List[FuzzyMatchResult]`
Get matches at a specific Hamming distance.

**Parameters:**
- `distance` (int): Specific distance to filter by

**Returns:**
- `List[FuzzyMatchResult]`: Matches at the specified distance

#### `get_top_matches(n: int = 10) -> List[FuzzyMatchResult]`
Get top N matches by count (most abundant).

**Parameters:**
- `n` (int): Number of matches to return (default=10)

**Returns:**
- `List[FuzzyMatchResult]`: Top N matches sorted by count

**Example:**
```python
from pyrustkmer import Database, PyFuzzyQuery

db = PyDatabase("example.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)

print(f"Query: {result.query_kmer}")
print(f"Total matches: {result.total_matches}")
print(f"Exact matches: {result.exact_matches}")
print(f"Fuzzy matches: {result.fuzzy_matches}")

# Get exact matches only
exact = result.get_exact_matches()
print(f"Found {len(exact)} exact matches")

# Get matches at distance 2
distance_2 = result.get_matches_by_distance(2)
print(f"Found {len(distance_2)} matches at distance 2")

# Get top 5 most abundant matches
top_5 = result.get_top_matches(5)
for match in top_5:
    print(f"{match.kmer}: {match.count} (distance={match.distance})")
```

### FuzzyBatchResult

Aggregates results from multiple fuzzy query operations.

```python
@dataclass
class FuzzyBatchResult:
    """Aggregates results from multiple fuzzy query operations."""

    total_queries: int                              # Total queries attempted
    successful_queries: int                         # Queries that completed successfully
    failed_queries: int                             # Queries that failed
    successes: Dict[str, FuzzyQueryResult]          # Mapping of query to result
    errors: Dict[str, str]                          # Mapping of query to error message
```

**Methods:**

#### `get_all_matches() -> List[FuzzyMatchResult]`
Get all matches from all successful queries.

**Returns:**
- `List[FuzzyMatchResult]`: Combined list of all matches

#### `get_query_summary() -> Dict[str, Any]`
Get summary statistics for the batch query.

**Returns:**
- `Dict[str, Any]`: Summary statistics including total matches, success rate, etc.

**Example:**
```python
from pyrustkmer import Database, PyFuzzyQuery

db = PyDatabase("example.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
kmers = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
]

# Perform batch query
batch_result = db.fuzzy_query_batch(kmers, mutations=2)

print(f"Total queries: {batch_result.total_queries}")
print(f"Successful: {batch_result.successful_queries}")
print(f"Failed: {batch_result.failed_queries}")

# Process results
for kmer, result in batch_result.successes.items():
    print(f"{kmer}: {result.total_matches} matches")

# Process errors
for kmer, error in batch_result.errors.items():
    print(f"{kmer} failed: {error}")

# Get summary
summary = batch_result.get_query_summary()
print(f"Success rate: {summary['success_rate']:.1%}")
```

## Database Methods

### Database.fuzzy_query()

Perform a fuzzy search with mutation tolerance.

```python
def fuzzy_query(
    self,
    kmer: str,
    mutations: int = 1,
    max_variants: Optional[int] = None,
    output_format: str = 'auto',
    position_mutations: Optional[str] = None
) -> FuzzyQueryResult:
```

**Parameters:**
- `kmer` (str): The k-mer sequence to query (A, T, C, G only)
- `mutations` (int): Maximum mutations allowed (0-5, default=1)  
  **Important Note on N's**: When querying k-mers containing 'N' characters, be aware that the default mutation tolerance differs between CLI and Python API:
  - CLI uses `mutations=0` (exact match only)
  - Python API uses `mutations=1` (allows 1 mutation by default)  
  This means that the same query will return different results depending on which interface you use. See [Fuzzy Query with N's: Behavior and Best Practices](../../../fuzzy_query_n_behavior.md) for detailed information.
- `max_variants` (Optional[int]): Maximum variants to generate to prevent combinatorial explosion
- `output_format` (str): CLI output format ('auto', 'json', 'table', 'tsv')
- `position_mutations` (Optional[str]): Position-specific mutation constraints

**Position Mutations Format:**
- `"4:1"` - Position 4 with max 1 mutation
- `"3,4,5:2"` - Positions 3,4,5 with max 2 mutations total
- `"4-7:1"` - Positions 4,5,6,7 with max 1 mutation (range notation)
- `"3,4:1;6,7:2"` - Multiple independent groups

**Returns:**
- `FuzzyQueryResult`: All matches within mutation tolerance

**Raises:**
- `InvalidKmerError`: If k-mer contains invalid characters
- `InvalidMutationToleranceError`: If mutations not in range 0-5
- `InvalidPositionMutationError`: If position_mutations format is invalid
- `DatabaseError`: If database is closed
- `QueryError`: If CLI command fails

**Examples:**
```python
from pyrustkmer import Database, PyFuzzyQuery

db = PyDatabase("example.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

# Basic fuzzy query
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)
print(f"Found {result.total_matches} matches")

# Position-specific mutations
result = fuzzy.query_fuzzy(
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    position_mutations="10,15:2"  # Allow 2 mutations at positions 10 and 15
)

# Limit variants to prevent combinatorial explosion
result = fuzzy.query_fuzzy(
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    mutations=3,
    max_variants=1000
)
```

### Database.fuzzy_query_batch()

Perform multiple fuzzy queries efficiently in parallel.

```python
def fuzzy_query_batch(
    self,
    kmers: List[str],
    mutations: int = 1,
    max_variants: Optional[int] = None,
    max_workers: int = 4,
    output_format: str = 'auto',
    position_mutations: Optional[str] = None
) -> FuzzyBatchResult:
```

**Parameters:**
- `kmers` (List[str]): List of k-mer sequences to query
- `mutations` (int): Maximum mutations allowed (0-5, default=1)  
  **Important Note on N's**: When querying k-mers containing 'N' characters, be aware that the default mutation tolerance differs between CLI and Python API:
  - CLI uses `mutations=0` (exact match only)
  - Python API uses `mutations=1` (allows 1 mutation by default)  
  This means that the same query will return different results depending on which interface you use. See [Fuzzy Query with N's: Behavior and Best Practices](../../../fuzzy_query_n_behavior.md) for detailed information.
- `max_variants` (Optional[int]): Maximum variants per query
- `max_workers` (int): Maximum parallel workers (default=4)
- `output_format` (str): CLI output format ('auto', 'json', 'table', 'tsv')
- `position_mutations` (Optional[str]): Position-specific mutation constraints

**Returns:**
- `FuzzyBatchResult`: Results for all queries including successes and failures

**Example:**
```python
from pyrustkmer import Database, PyFuzzyQuery

db = PyDatabase("example.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
kmers = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
]

# Batch query with parallel processing
batch_result = db.fuzzy_query_batch(
    kmers,
    mutations=2,
    max_workers=8
)

# Check results
for kmer, result in batch_result.successes.items():
    print(f"{kmer}: {result.total_matches} matches")
```

## Performance Considerations

### Combinatorial Explosion

The number of possible variants grows combinatorially with mutation tolerance. For a k-mer of length k:
- Distance 1: k × 3 variants
- Distance 2: k² × 3² variants
- Distance 3: k³ × 3³ variants

Use `max_variants` to limit computational cost:

```python
# Safe: Low mutation tolerance
result = fuzzy.query_fuzzy(kmer, mutations=1)

# Use limit: Higher mutation tolerance
result = fuzzy.query_fuzzy(kmer, mutations=3, max_variants=1000)
```

### Position Mutations

Position mutations can dramatically reduce search space by restricting mutations to specific positions:

```python
# Allow mutations only at specific positions
result = fuzzy.query_fuzzy(
    kmer,
    mutations=2,
    position_mutations="10,15:2"  # Much faster than allowing mutations anywhere
)

# Range notation for consecutive positions
result = fuzzy.query_fuzzy(
    kmer,
    position_mutations="5-8:1"  # Positions 5,6,7,8 with 1 mutation total
)
```

### Batch Processing

For multiple queries, use `fuzzy_query_batch()` for better performance:

```python
# Less efficient: Individual queries
for kmer in kmers:
    result = fuzzy.query_fuzzy(kmer, mutations=2)
    process_result(result)

# More efficient: Batch processing
batch_result = db.fuzzy_query_batch(kmers, mutations=2, max_workers=8)
for result in batch_result.successes.values():
    process_result(result)
```

## Use Cases

### Error Correction

Find potential correct versions of erroneous k-mers:

```python
def find_corrections(db, erroneous_kmer, max_distance=2):
    """Find potential corrections for an erroneous k-mer."""
    result = fuzzy.query_fuzzy(erroneous_kmer, mutations=max_distance)

    # Sort by abundance (most likely to be correct)
    candidates = result.get_top_matches(5)

    corrections = []
    for match in candidates:
        if match.distance > 0:  # Not exact match
            corrections.append({
                'corrected': match.kmer,
                'distance': match.distance,
                'confidence': match.count,
                'mutations': match.mutations
            })

    return corrections
```

### Variant Discovery

Find variants of a known sequence:

```python
def discover_variants(db, reference_kmer, max_distance=3):
    """Discover variants of a reference sequence."""
    result = fuzzy.query_fuzzy(reference_kmer, mutations=max_distance)

    variants = {}
    for distance in range(1, max_distance + 1):
        variants[distance] = result.get_matches_by_distance(distance)

    return variants

# Example
reference = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
variants = discover_variants(db, reference)

for distance, matches in variants.items():
    print(f"Distance {distance}: {len(matches)} variants")
    for match in matches[:3]:  # Show top 3
        print(f"  {match.kmer}: {match.count}")
```

### Quality Control

Assess sequencing quality by checking error rates:

```python
def assess_sequencing_quality(db, high_confidence_kmers):
    """Assess sequencing quality using high-confidence k-mers."""

    quality_metrics = {}

    for kmer in high_confidence_kmers:
        # Query with mutation tolerance
        result = fuzzy.query_fuzzy(kmer, mutations=2)

        # Calculate error indicators
        exact_count = result.exact_matches
        fuzzy_count = result.fuzzy_matches
        total_abundance = sum(m.count for m in result.matches)

        # Error rate estimation
        if total_abundance > 0:
            error_rate = fuzzy_count / total_abundance
        else:
            error_rate = 0

        quality_metrics[kmer] = {
            'exact_matches': exact_count,
            'fuzzy_matches': fuzzy_count,
            'error_rate': error_rate,
            'total_abundance': total_abundance
        }

    return quality_metrics
```

## Integration Examples

### Pandas Integration

```python
import pandas as pd
from pyrustkmer import Database, PyFuzzyQuery

def fuzzy_query_to_dataframe(result, query_kmer):
    """Convert FuzzyQueryResult to pandas DataFrame."""

    data = []
    for match in result.matches:
        data.append({
            'query_kmer': query_kmer,
            'matched_kmer': match.kmer,
            'count': match.count,
            'distance': match.distance,
            'mutations': ';'.join(match.mutations) if match.mutations else 'none'
        })

    return pd.DataFrame(data)

# Usage
db = PyDatabase("example.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)
df = fuzzy_query_to_dataframe(result, "ATCGATCGATCGATCGATCGATCGATCGATCGATCG")

# Analyze results
print(f"Distance distribution:\n{df['distance'].value_counts().sort_index()}")
print(f"\nTop matches:\n{df.nlargest(10, 'count')[['matched_kmer', 'count', 'distance']]}")
```

### NumPy Integration

```python
import numpy as np
from pyrustkmer import Database, PyFuzzyQuery

def analyze_mutation_spectrum(db, reference_kmer, max_distance=3):
    """Analyze mutation spectrum using NumPy."""

    result = fuzzy.query_fuzzy(reference_kmer, mutations=max_distance)

    # Extract data as arrays
    distances = np.array([match.distance for match in result.matches])
    counts = np.array([match.count for match in result.matches])

    # Calculate statistics
    total_matches = np.sum(counts)
    weighted_distance = np.average(distances, weights=counts)

    # Distance breakdown
    unique_distances = np.unique(distances)
    distance_stats = {}

    for dist in unique_distances:
        mask = distances == dist
        distance_stats[dist] = {
            'count': np.sum(mask),
            'abundance': np.sum(counts[mask]),
            'frequency': np.sum(counts[mask]) / total_matches
        }

    return {
        'reference': reference_kmer,
        'total_matches': total_matches,
        'weighted_distance': weighted_distance,
        'distance_breakdown': distance_stats
    }
```

## Advanced Use Cases

### SNP and Indel Detection

```python
from pyrustkmer import Database, PyFuzzyQuery
from collections import defaultdict

def detect_variants(db, reference_kmer, min_abundance=10):
    """Detect potential SNPs and variants around a reference sequence."""

    # Search for variants with 1-2 mutations
    result = fuzzy.query_fuzzy(reference_kmer, mutations=2)

    variants = defaultdict(list)

    for match in result.matches:
        if match.count >= min_abundance:
            # Analyze mutation pattern
            for mutation in match.mutations:
                # Parse mutation format "A>T" or "A>-"
                if '>' in mutation:
                    ref, alt = mutation.split('>')
                    if alt == '-':  # Deletion
                        variant_type = 'deletion'
                    elif ref == '-':  # Insertion
                        variant_type = 'insertion'
                    else:  # SNP
                        variant_type = 'snp'

                    variants[variant_type].append({
                        'reference': reference_kmer,
                        'variant': match.kmer,
                        'mutation': mutation,
                        'distance': match.distance,
                        'abundance': match.count,
                        'positions': [i for i, (r, v) in enumerate(zip(reference_kmer, match.kmer)) if r != v]
                    })

    return dict(variants)

# Example usage
db = PyDatabase("genome.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
reference = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
variants = detect_variants(db, reference)

print(f"SNPs found: {len(variants.get('snp', []))}")
print(f"Deletions found: {len(variants.get('deletion', []))}")
print(f"Insertions found: {len(variants.get('insertion', []))}")

# Display variants
for variant_type, variant_list in variants.items():
    print(f"\n{variant_type.upper()} Variants:")
    for variant in variant_list[:5]:  # Show top 5
        print(f"  {variant['mutation']}: abundance={variant['abundance']}")
```

### Consensus Sequence Building

```python
def build_consensus_sequence(db, kmer_region, max_distance=2, min_abundance=5):
    """Build a consensus sequence from variants in a k-mer region."""

    # Get all variants in the region
    result = fuzzy.query_fuzzy(kmer_region, mutations=max_distance)

    # Filter by abundance
    abundant_matches = [m for m in result.matches if m.count >= min_abundance]

    if not abundant_matches:
        return kmer_region, 0

    # Calculate consensus
    kmer_length = len(kmer_region)
    position_counts = [defaultdict(int) for _ in range(kmer_length)]
    total_abundance = 0

    # Count nucleotides at each position
    for match in abundant_matches:
        for i, nucleotide in enumerate(match.kmer):
            weight = match.count  # Weight by abundance
            position_counts[i][nucleotide] += weight
        total_abundance += match.count

    # Build consensus sequence
    consensus = []
    for i in range(kmer_length):
        # Choose most abundant nucleotide at each position
        if position_counts[i]:
            consensus_nucleotide = max(position_counts[i].items(), key=lambda x: x[1])[0]
            consensus.append(consensus_nucleotide)
        else:
            consensus.append(kmer_region[i])

    consensus_sequence = ''.join(consensus)

    # Calculate consensus confidence
    confidence_scores = []
    for i in range(kmer_length):
        if total_abundance > 0:
            max_count = max(position_counts[i].values())
            confidence = max_count / total_abundance
            confidence_scores.append(confidence)
        else:
            confidence_scores.append(0)

    average_confidence = sum(confidence_scores) / len(confidence_scores)

    return consensus_sequence, average_confidence

# Example usage
consensus, confidence = build_consensus_sequence(db, "ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
print(f"Consensus: {consensus}")
print(f"Average confidence: {confidence:.2%}")
```

### Metagenome Analysis

```python
def analyze_metagenomic_samples(db_files, query_kmers, mutations=2):
    """Analyze k-mer variants across multiple metagenomic samples."""

    sample_results = {}

    for db_file in db_files:
        sample_name = db_file.stem
        sample_results[sample_name] = {}

        db = PyDatabase(db_file, LoadMode.Preload)
            for kmer in query_kmers:
                result = fuzzy.query_fuzzy(kmer, mutations=mutations)

                # Summarize variant diversity
                variants_by_distance = defaultdict(int)
                total_abundance = 0

                for match in result.matches:
                    variants_by_distance[match.distance] += match.count
                    total_abundance += match.count

                # Calculate diversity metrics
                shannon_diversity = 0
                if total_abundance > 0:
                    for count in variants_by_distance.values():
                        p = count / total_abundance
                        shannon_diversity -= p * np.log(p)

                sample_results[sample_name][kmer] = {
                    'total_matches': result.total_matches,
                    'exact_matches': result.exact_matches,
                    'variant_richness': len(variants_by_distance) - 1,  # Exclude exact matches
                    'shannon_diversity': shannon_diversity,
                    'variants_by_distance': dict(variants_by_distance)
                }

    return sample_results

# Example usage
import glob
db_files = glob.glob("metagenome_samples/*.rkdb")
query_kmers = ["ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
               "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"]

results = analyze_metagenomic_samples(db_files, query_kmers)

# Compare diversity across samples
for kmer in query_kmers:
    print(f"\nK-mer: {kmer[:20]}...")
    print("Sample\t\tRichness\tDiversity")
    for sample, data in results.items():
        if kmer in data:
            print(f"{sample[:15]}\t{data[kmer]['variant_richness']}\t{data[kmer]['shannon_diversity']:.3f}")
```

### Antibiotic Resistance Gene Detection

```python
def detect_resistance_variants(db, resistance_kmers, mutation_tolerance=3):
    """Detect variants in known antibiotic resistance genes."""

    resistance_variants = {}

    for gene_name, reference_kmer in resistance_kmers.items():
        result = fuzzy.query_fuzzy(reference_kmer, mutations=mutation_tolerance)

        # Classify variants by potential impact
        high_impact = []  # Multiple mutations, low abundance
        moderate_impact = []  # Single mutation, moderate abundance
        low_impact = []  # Single mutation, high abundance

        for match in result.matches:
            if match.distance == 0:
                continue  # Skip exact matches

            # Classify based on distance and abundance
            if match.distance >= 3 or match.count < 10:
                high_impact.append(match)
            elif match.distance == 2 or match.count < 100:
                moderate_impact.append(match)
            else:
                low_impact.append(match)

        resistance_variants[gene_name] = {
            'reference': reference_kmer,
            'total_variants': len(result.matches) - result.exact_matches,
            'high_impact': len(high_impact),
            'moderate_impact': len(moderate_impact),
            'low_impact': len(low_impact),
            'all_variants': result.matches
        }

    return resistance_variants

# Example usage
resistance_genes = {
    'bla_TEM': "ATGAGTATTCAACATTTCCGTGTCGCCCTTATT",
    'mecA': "ATGTCGATCTACAAATGTTGCTGCTATGGCATC",
    'vanA': "ATGAACAAATTGAAAGTTATAGAAAGGTGGAA"
}

variants = detect_resistance_variants(db, resistance_genes)

for gene, data in variants.items():
    print(f"\n{gene}:")
    print(f"  Total variants: {data['total_variants']}")
    print(f"  High impact: {data['high_impact']}")
    print(f"  Moderate impact: {data['moderate_impact']}")
    print(f"  Low impact: {data['low_impact']}")
```

### Error-Prone Region Identification

```python
def identify_error_prone_regions(db, genome_kmers, threshold_distance=2, min_variants=5):
    """Identify genomic regions with high variant rates (potential error-prone regions)."""

    error_prone_regions = []

    for kmer in genome_kmers:
        result = fuzzy.query_fuzzy(kmer, mutations=threshold_distance)

        # Calculate variant rate
        total_matches = sum(match.count for match in result.matches)
        variant_matches = sum(match.count for match in result.matches if match.distance > 0)

        if total_matches > 0:
            variant_rate = variant_matches / total_matches

            # Check if it meets error-prone criteria
            if variant_rate > 0.1 and len(result.get_fuzzy_matches()) >= min_variants:
                error_prone_regions.append({
                    'kmer': kmer,
                    'variant_rate': variant_rate,
                    'total_matches': total_matches,
                    'variant_matches': variant_matches,
                    'unique_variants': len(result.get_fuzzy_matches()),
                    'variants': result.get_fuzzy_matches()
                })

    # Sort by variant rate (descending)
    error_prone_regions.sort(key=lambda x: x['variant_rate'], reverse=True)

    return error_prone_regions

# Example usage
# Get a subset of k-mers from the database to analyze
db = PyDatabase("genome.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    genome_kmers = []
    for result in db.dump(limit=1000):
        genome_kmers.append(result.kmer)
        if len(genome_kmers) >= 100:  # Analyze first 100 k-mers
            break

error_regions = identify_error_prone_regions(db, genome_kmers)

print("Top error-prone regions:")
for region in error_regions[:10]:
    print(f"K-mer: {region['kmer'][:20]}...")
    print(f"  Variant rate: {region['variant_rate']:.2%}")
    print(f"  Unique variants: {region['unique_variants']}")
```

### Population Genetics Analysis

```python
def analyze_population_structure(db_files, query_kmers, mutations=2):
    """Analyze population structure using k-mer variant frequencies."""

    population_data = {}

    for db_file in db_files:
        population_name = db_file.stem
        population_variants = {}

        db = PyDatabase(db_file, LoadMode.Preload)
            for kmer in query_kmers:
                result = fuzzy.query_fuzzy(kmer, mutations=mutations)

                # Create allele frequency matrix
                alleles = defaultdict(int)
                total_abundance = 0

                for match in result.matches:
                    alleles[match.kmer] += match.count
                    total_abundance += match.count

                # Calculate allele frequencies
                allele_freqs = {}
                if total_abundance > 0:
                    for allele, count in alleles.items():
                        allele_freqs[allele] = count / total_abundance

                population_variants[kmer] = {
                    'alleles': allele_freqs,
                    'total_abundance': total_abundance,
                    'diversity': len(alleles)
                }

        population_data[population_name] = population_variants

    return population_data

def calculate_fst(population_data, kmer):
    """Calculate Fst statistic for population differentiation."""

    populations = list(population_data.keys())

    # Calculate allele frequencies across populations
    global_alleles = defaultdict(float)
    total_global_abundance = 0

    for pop_data in population_data.values():
        if kmer in pop_data:
            for allele, freq in pop_data[kmer]['alleles'].items():
                abundance = freq * pop_data[kmer]['total_abundance']
                global_alleles[allele] += abundance
                total_global_abundance += abundance

    # Calculate global frequencies
    global_freqs = {}
    if total_global_abundance > 0:
        for allele, abundance in global_alleles.items():
            global_freqs[allele] = abundance / total_global_abundance

    # Calculate Fst
    ht = 0  # Total heterozygosity
    hs = 0  # Average within-population heterozygosity

    # Total heterozygosity
    for freq in global_freqs.values():
        ht += 2 * freq * (1 - freq)

    # Within-population heterozygosity
    pop_heterozygosities = []
    for pop_name, pop_data in population_data.items():
        if kmer in pop_data:
            pop_ht = 0
            for freq in pop_data[kmer]['alleles'].values():
                pop_ht += 2 * freq * (1 - freq)
            pop_heterozygosities.append(pop_ht)

    hs = sum(pop_heterozygosities) / len(pop_heterozygosities) if pop_heterozygosities else 0

    # Fst calculation
    fst = (ht - hs) / ht if ht > 0 else 0

    return fst, ht, hs

# Example usage
pop_db_files = glob.glob("populations/*.rkdb")
query_kmers = ["ATCGATCGATCGATCGATCGATCGATCGATCGATCG"]

pop_data = analyze_population_structure(pop_db_files, query_kmers)

print("Population differentiation analysis:")
for kmer in query_kmers:
    fst, ht, hs = calculate_fst(pop_data, kmer)
    print(f"K-mer {kmer[:20]}...")
    print(f"  Fst: {fst:.4f}")
    print(f"  Total heterozygosity: {ht:.4f}")
    print(f"  Within-pop heterozygosity: {hs:.4f}")
```

## Integration Examples

### Advanced Pandas Integration

```python
import pandas as pd
import numpy as np
from pyrustkmer import Database, PyFuzzyQuery

def create_variant_analysis_dataframe(db_path, query_kmers, mutations=3):
    """Create comprehensive variant analysis DataFrame."""

    db = PyDatabase(db_path)
fuzzy = PyFuzzyQuery(db)
    all_data = []

    for kmer in query_kmers:
        result = fuzzy.query_fuzzy(kmer, mutations=mutations)

        for match in result.matches:
            all_data.append({
                'query_kmer': kmer,
                'matched_kmer': match.kmer,
                'count': match.count,
                'distance': match.distance,
                'mutations': ';'.join(match.mutations),
                'is_exact': match.distance == 0,
                'log_count': np.log10(match.count + 1),
                'relative_abundance': match.count / result.total_matches
            })

    df = pd.DataFrame(all_data)

    # Add derived columns
    df['mutation_count'] = df['mutations'].apply(lambda x: len(x.split(';')) if x != 'none' else 0)
    df['gc_content'] = df['matched_kmer'].apply(lambda x: (x.count('G') + x.count('C')) / len(x))

    return df

# Usage
df = create_variant_analysis_dataframe("genome.rkdb", query_kmers)

# Advanced analysis
print("Variant Analysis Summary:")
print(f"Total variants: {len(df)}")
print(f"Unique k-mers: {df['matched_kmer'].nunique()}")
print(f"Average distance: {df['distance'].mean():.2f}")
print(f"Distance distribution:\n{df['distance'].value_counts().sort_index()}")

# Find most abundant variants by distance
print("\nMost abundant variants by distance:")
for distance in sorted(df['distance'].unique()):
    top_variants = df[df['distance'] == distance].nlargest(3, 'count')
    print(f"Distance {distance}:")
    for _, row in top_variants.iterrows():
        print(f"  {row['matched_kmer']}: {row['count']}")
```

### Machine Learning Feature Extraction

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import numpy as np

def extract_fuzzy_features(db_files, labels, query_kmers, mutations=2):
    """Extract features from fuzzy queries for machine learning."""

    features = []

    for db_file, label in zip(db_files, labels):
        sample_features = []

        db = PyDatabase(db_file, LoadMode.Preload)
            for kmer in query_kmers:
                result = fuzzy.query_fuzzy(kmer, mutations=mutations)

                # Extract numerical features
                feature_vector = [
                    result.total_matches,
                    result.exact_matches,
                    result.fuzzy_matches,
                    result.total_matches / (result.exact_matches + 1),  # Variance ratio
                    np.mean([m.count for m in result.matches]) if result.matches else 0,
                    np.std([m.count for m in result.matches]) if result.matches else 0,
                    len(result.matches),
                    max([m.distance for m in result.matches]) if result.matches else 0
                ]

                sample_features.extend(feature_vector)

        features.append(sample_features)

    return np.array(features), np.array(labels)

def classify_genomic_features(db_files, categories):
    """Classify genomic samples based on fuzzy query features."""

    # Prepare query k-mers
    query_kmers = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
    ]

    # Extract features
    X, y = extract_fuzzy_features(db_files, categories, query_kmers)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Train classifier
    classifier = RandomForestClassifier(n_estimators=100, random_state=42)
    classifier.fit(X_train, y_train)

    # Evaluate
    train_score = classifier.score(X_train, y_train)
    test_score = classifier.score(X_test, y_test)

    print(f"Training accuracy: {train_score:.3f}")
    print(f"Test accuracy: {test_score:.3f}")

    # Feature importance
    feature_names = []
    for i, kmer in enumerate(query_kmers):
        feature_names.extend([
            f'{kmer[:10]}_total',
            f'{kmer[:10]}_exact',
            f'{kmer[:10]}_fuzzy',
            f'{kmer[:10]}_variance',
            f'{kmer[:10]}_mean_count',
            f'{kmer[:10]}_std_count',
            f'{kmer[:10]}_num_matches',
            f'{kmer[:10]}_max_distance'
        ])

    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': classifier.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nTop 10 most important features:")
    print(importance_df.head(10))

    return classifier, importance_df

# Example usage
db_files = ["sample1.rkdb", "sample2.rkdb", "sample3.rkdb", "sample4.rkdb"]
categories = ["type_A", "type_A", "type_B", "type_B"]

classifier, importance = classify_genomic_features(db_files, categories)
```

### Visualization Integration

```python
import matplotlib.pyplot as plt
import seaborn as sns

def visualize_fuzzy_query_results(db_path, query_kmers, mutations=2):
    """Create comprehensive visualizations of fuzzy query results."""

    db = PyDatabase(db_path)
fuzzy = PyFuzzyQuery(db)

    # Create subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f'Fuzzy Query Analysis - {Path(db_path).name}', fontsize=16)

    # Collect data for all k-mers
    all_distances = []
    all_counts = []
    distance_counts = []

    for i, kmer in enumerate(query_kmers):
        if i >= 6:  # Limit to 6 k-mers for visualization
            break

        result = fuzzy.query_fuzzy(kmer, mutations=mutations)

        distances = [match.distance for match in result.matches]
        counts = [match.count for match in result.matches]

        all_distances.extend(distances)
        all_counts.extend(counts)

        # Distance distribution for this k-mer
        ax = axes[i // 3, i % 3]
        distance_dist = pd.Series(distances).value_counts().sort_index()
        ax.bar(distance_dist.index, distance_dist.values, alpha=0.7)
        ax.set_xlabel('Distance')
        ax.set_ylabel('Count')
        ax.set_title(f'{kmer[:15]}... Distance Distribution')
        ax.grid(True, alpha=0.3)

    # Overall distance distribution
    if all_distances:
        ax = axes[1, 2]
        pd.Series(all_distances).value_counts().sort_index().plot(kind='bar', ax=ax)
        ax.set_xlabel('Distance')
        ax.set_ylabel('Frequency')
        ax.set_title('Overall Distance Distribution')
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    # Create heatmap of k-mer vs distance matrix
    if len(query_kmers) <= 10:
        fig, ax = plt.subplots(figsize=(12, 8))

        matrix_data = []
        for kmer in query_kmers:
            result = fuzzy.query_fuzzy(kmer, mutations=mutations)
            distance_counts = [0] * (mutations + 1)

            for match in result.matches:
                if match.distance <= mutations:
                    distance_counts[match.distance] += match.count

            matrix_data.append(distance_counts)

        matrix_df = pd.DataFrame(
            matrix_data,
            index=[k[:15] + "..." for k in query_kmers],
            columns=[f'Distance {i}' for i in range(mutations + 1)]
        )

        sns.heatmap(matrix_df, annot=True, fmt='g', cmap='YlOrRd', ax=ax)
        ax.set_title('K-mer vs Distance Heatmap')
        ax.set_xlabel('Distance')
        ax.set_ylabel('Query K-mers')

        plt.tight_layout()
        plt.show()

# Usage
visualize_fuzzy_query_results("genome.rkdb", query_kmers[:6])
```

This API reference provides comprehensive documentation for rustkmer's fuzzy query functionality, including all classes, methods, and practical usage examples for advanced bioinformatics applications.