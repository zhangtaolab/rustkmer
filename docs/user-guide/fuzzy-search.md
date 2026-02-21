# Fuzzy Search

Complete guide to fuzzy searching with RustKmer, including wildcard patterns, Hamming distance searches, and advanced pattern matching techniques.

## Table of Contents

- [Understanding Fuzzy Search](#understanding-fuzzy-search)
- [Wildcard Searching](#wildcard-searching)
- [Hamming Distance Search](#hamming-distance-search)
- [Advanced Pattern Matching](#advanced-pattern-matching)
- [Performance Optimization](#performance-optimization)
- [Use Cases](#use-cases)
- [Best Practices](#best-practices)

## Understanding Fuzzy Search

### What is Fuzzy Search?

**Fuzzy search** allows you to find k-mers that match a pattern with some degree of flexibility. Unlike exact matching, fuzzy search can handle:

- **Wildcards**: Position-specific flexible matching (e.g., `ATN` where `N` can be any base)
- **Distance-based**: Matches within a certain number of mutations (e.g., find k-mers within 2 mutations of a query)
- **Pattern completion**: Fill missing positions to match database k-mers

### Types of Fuzzy Search

| Type | Description | Use Case | Example |
|------|-------------|----------|---------|
| **Wildcard Search** | Replace `N` with any base (A, T, C, G) | Ambiguous positions, incomplete sequences | `ATN` → `ATA`, `ATT`, `ATC`, `ATG` |
| **Hamming Distance** | Find k-mers within X mutations | Error tolerance, variant detection | `ATCG` + distance=1 → `TTCG`, `AACG`, `ATAG`, `ATCC` |
| **K-mer Completion** | Extend shorter k-mers to database k-mer size | Partial matches, primer design | `ATCG` (k=4) → `ATCGATCGATCG` (k=12) |

---

## Wildcard Searching

### Basic Wildcard Queries

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Load database
db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
db.load("genome_k21.rkdb")

# Single wildcard (N = any base)
print("🔍 Single wildcard examples:")
wildcard_patterns = ["ATN", "CGTN", "TTN"]

for pattern in wildcard_patterns:
    results = fuzzy.query_fuzzy(pattern)
    print(f"   Pattern '{pattern}': {len(results)} matches")

    # Show first few matches
    for i, result in enumerate(results[:3]):
        print(f"     {i+1}. {result.kmer}: {result.count}")

# Multiple wildcards
print("\n🔍 Multiple wildcard examples:")
multi_patterns = ["ATNNT", "CGNNG", "ANNNNNN"]

for pattern in multi_patterns:
    results = fuzzy.query_fuzzy(pattern)
    print(f"   Pattern '{pattern}': {len(results)} matches")
```

### Wildcard Expansion

```python
def expand_wildcard_pattern(pattern):
    """Expand a wildcard pattern to all possible k-mers."""

    def expand_char(char):
        if char == 'N':
            return ['A', 'T', 'C', 'G']
        else:
            return [char]

    import itertools

    # Expand each position
    position_options = [expand_char(char) for char in pattern]

    # Generate all combinations
    all_combinations = itertools.product(*position_options)

    # Join to form k-mers
    expanded_kmers = [''.join(combo) for combo in all_combinations]

    return expanded_kmers

def analyze_wildcard_complexity(pattern):
    """Analyze the complexity of a wildcard pattern."""

    wildcard_count = pattern.count('N')
    total_combinations = 4 ** wildcard_count

    print(f"Pattern Analysis: '{pattern}'")
    print(f"  Length: {len(pattern)}")
    print(f"  Wildcards: {wildcard_count}")
    print(f"  Total combinations: {total_combinations:,}")

    if total_combinations > 1000000:
        print("  ⚠️  Large number of combinations - may be slow")

    return total_combinations

# Usage examples
patterns = ["ATN", "ATNN", "ATNNN", "ANNNNNN"]

for pattern in patterns:
    combinations = analyze_wildcard_complexity(pattern)

    if combinations <= 16:  # Show small examples
        expanded = expand_wildcard_pattern(pattern)
        print(f"  Expanded: {', '.join(expanded)}")
    print()
```

### Practical Wildcard Applications

```python
def find_conserved_motifs(db_path, motif_with_wildcards):
    """Find conserved motifs with flexible positions."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    results = fuzzy.query_fuzzy(motif_with_wildcards)

    # Sort by count (most frequent first)
    results.sort(key=lambda x: x.count, reverse=True)

    print(f"🧬 Conserved motif analysis for: {motif_with_wildcards}")
    print(f"Found {len(results)} total matches")

    # Show top matches
    print("\nTop 10 most frequent matches:")
    for i, result in enumerate(results[:10], 1):
        print(f"  {i:2d}. {result.kmer}: {result.count:,}")

    # Calculate conservation score
    total_count = sum(result.count for result in results)
    top_match_ratio = results[0].count / total_count if results else 0

    print(f"\nConservation Analysis:")
    print(f"  Total occurrences: {total_count:,}")
    print(f"  Most frequent: {results[0].kmer if results else 'None'} ({results[0].count if results else 0})")
    print(f"  Conservation ratio: {top_match_ratio:.3f}")

    return results

def primer_compatibility_check(db_path, primer_sequence):
    """Check primer compatibility with 3' end flexibility."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    # Create pattern with flexible 3' end
    if len(primer_sequence) < 3:
        print("Primer too short")
        return []

    # Make last 3 positions flexible (common in PCR)
    flexible_primer = primer_sequence[:-3] + 'NNN'

    print(f"🧪 Checking primer compatibility for: {primer_sequence}")
    print(f"Using flexible pattern: {flexible_primer}")

    results = fuzzy.query_fuzzy(flexible_primer)

    # Analyze 3' end compatibility
    three_prime_bases = {}

    for result in results:
        three_prime = result.kmer[-3:]
        if three_prime not in three_prime_bases:
            three_prime_bases[three_prime] = 0
        three_prime_bases[three_prime] += result.count

    print(f"\n3' end compatibility:")
    for bases, count in sorted(three_prime_bases.items(), key=lambda x: x[1], reverse=True):
        print(f"  {bases}: {count:,} occurrences")

    return results

# Usage
db_path = "genome_k21.rkdb"

# Find conserved motifs
motif_results = find_conserved_motifs(db_path, "ATGNNNGTA")

# Check primer compatibility
primer_results = primer_compatibility_check(db_path, "ATGCCGATCG")
```

---

## Hamming Distance Search

### Understanding Hamming Distance

**Hamming distance** is the number of positions at which two strings of equal length differ. For DNA sequences, it represents the number of mutations required to transform one sequence into another.

```python
def hamming_distance(seq1, seq2):
    """Calculate Hamming distance between two sequences."""
    if len(seq1) != len(seq2):
        raise ValueError("Sequences must be equal length")

    return sum(1 for a, b in zip(seq1, seq2) if a != b)

def generate_hamming_neighbors(kmer, max_distance):
    """Generate all neighbors within Hamming distance."""

    if max_distance == 0:
        return [kmer]

    bases = ['A', 'T', 'C', 'G']
    neighbors = set()

    def generate_mutations(sequence, pos, distance):
        if distance > max_distance:
            return

        if pos >= len(sequence):
            if sequence != kmer:
                neighbors.add(sequence)
            return

        # Keep original base
        generate_mutations(sequence, pos + 1, distance)

        # Try all other bases
        for base in bases:
            if base != sequence[pos]:
                new_sequence = sequence[:pos] + base + sequence[pos+1:]
                generate_mutations(new_sequence, pos + 1, distance + 1)

    generate_mutations(kmer, 0, 0)
    return list(neighbors)

# Example usage
original = "ATCGATCG"
neighbors = generate_hamming_neighbors(original, 2)

print(f"Original sequence: {original}")
print(f"Neighbors within distance 2: {len(neighbors)}")
print("Example neighbors:", neighbors[:10])
```

### Distance-Based Fuzzy Queries

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

def distance_based_search(db_path, query_kmer, max_distance=3):
    """Search for k-mers within specified Hamming distance."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🎯 Distance-based search for: {query_kmer}")
    print(f"Maximum distance: {max_distance}")

    # Perform fuzzy search with distance constraint
    results = fuzzy.query_fuzzy(query_kmer, max_distance=max_distance)

    # Group results by distance
    distance_groups = {}
    for result in results:
        dist = result.distance
        if dist not in distance_groups:
            distance_groups[dist] = []
        distance_groups[dist].append(result)

    # Display results
    for distance in range(max_distance + 1):
        if distance in distance_groups:
            group = distance_groups[distance]
            print(f"\nDistance {distance}: {len(group)} matches")

            # Sort by count
            group.sort(key=lambda x: x.count, reverse=True)

            for result in group[:5]:  # Show top 5
                print(f"  {result.kmer}: {result.count:,}")

    return results

def variant_analysis(db_path, reference_kmer):
    """Analyze variants around a reference sequence."""

    print(f"🧬 Variant analysis for: {reference_kmer}")

    # Test different distance thresholds
    for distance in [1, 2, 3]:
        results = fuzzy.query_fuzzy(reference_kmer, max_distance=distance)

        # Calculate statistics
        exact_match = any(r.distance == 0 for r in results)
        total_variants = len([r for r in results if r.distance > 0])
        total_variant_count = sum(r.count for r in results if r.distance > 0)

        print(f"\nDistance ≤ {distance}:")
        print(f"  Exact match found: {'Yes' if exact_match else 'No'}")
        print(f"  Variant sequences: {total_variants}")
        print(f"  Total variant occurrences: {total_variant_count:,}")

        if total_variants > 0:
            avg_variant_count = total_variant_count / total_variants
            print(f"  Average variant count: {avg_variant_count:.1f}")

# Usage
db_path = "genome_k21.rkdb"
query_kmer = "ATCGATCGATCGATCGATCGA"  # 21-mer

# Perform distance search
distance_results = distance_based_search(db_path, query_kmer, max_distance=3)

# Analyze variants
variant_analysis(db_path, query_kmer)
```

### Error-Tolerant Search

```python
def error_tolerant_search(db_path, queries, max_error_rate=0.1):
    """Perform error-tolerant search with adaptive distance."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🔍 Error-tolerant search (max error rate: {max_error_rate})")

    all_results = []

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Searching: {query}")

        # Calculate adaptive max distance based on query length
        kmer_size = len(query)
        max_distance = max(1, int(kmer_size * max_error_rate))

        print(f"  Query length: {kmer_size}")
        print(f"  Max distance: {max_distance}")

        # Perform search
        results = fuzzy.query_fuzzy(query, max_distance=max_distance)

        # Analyze results
        if results:
            # Find best match (highest count)
            best_match = max(results, key=lambda x: x.count)

            print(f"  Results: {len(results)} matches")
            print(f"  Best match: {best_match.kmer} (distance={best_match.distance}, count={best_match.count:,})")

            # Group by distance
            distance_counts = {}
            for result in results:
                if result.distance not in distance_counts:
                    distance_counts[result.distance] = 0
                distance_counts[result.distance] += result.count

            print("  Distance distribution:")
            for dist, count in sorted(distance_counts.items()):
                print(f"    Distance {dist}: {count:,} total occurrences")

        else:
            print("  No matches found")

        all_results.extend(results)

    return all_results

# Usage
test_queries = [
    "ATCGATCGATCGATCGATCGA",  # Exact match likely
    "TTCGATCGATCGATCGATCGA",  # Single mutation
    "ATCGATCCATCGATCGATCGA",  # Single mutation
    "TTCGATCCATCGATCGATCGA",  # Double mutation
]

error_results = error_tolerant_search(db_path, test_queries, max_error_rate=0.15)
```

---

## Advanced Pattern Matching

### Complex Pattern Searches

```python
def complex_pattern_search(db_path, patterns):
    """Search for complex patterns with multiple constraints."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🔍 Complex pattern search")

    for pattern_config in patterns:
        pattern = pattern_config['pattern']
        constraints = pattern_config.get('constraints', {})

        print(f"\nPattern: {pattern}")
        print(f"Constraints: {constraints}")

        # Perform fuzzy search
        results = fuzzy.query_fuzzy(pattern)

        # Apply additional constraints
        filtered_results = []

        for result in results:
            # Apply count constraints
            min_count = constraints.get('min_count', 1)
            max_count = constraints.get('max_count', float('inf'))

            if min_count <= result.count <= max_count:
                # Apply GC content constraints
                if 'min_gc' in constraints or 'max_gc' in constraints:
                    gc_content = (result.kmer.count('G') + result.kmer.count('C')) / len(result.kmer)

                    if 'min_gc' in constraints and gc_content < constraints['min_gc']:
                        continue
                    if 'max_gc' in constraints and gc_content > constraints['max_gc']:
                        continue

                filtered_results.append(result)

        print(f"Results: {len(filtered_results)}/{len(results)} match constraints")

        if filtered_results:
            # Show top matches
            filtered_results.sort(key=lambda x: x.count, reverse=True)
            for result in filtered_results[:5]:
                gc_content = (result.kmer.count('G') + result.kmer.count('C')) / len(result.kmer)
                print(f"  {result.kmer}: {result.count:,} (GC={gc_content:.2f})")

# Usage
complex_patterns = [
    {
        'pattern': 'ATNNGTA',
        'constraints': {
            'min_count': 100,
            'max_count': 10000,
            'min_gc': 0.3,
            'max_gc': 0.7
        }
    },
    {
        'pattern': 'CGNNNAT',
        'constraints': {
            'min_count': 50,
        }
    }
]

complex_pattern_search(db_path, complex_patterns)
```

### Motif Discovery with Fuzzy Search

```python
def discover_motifs(db_path, seed_pattern, min_frequency=100):
    """Discover related motifs using fuzzy search."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🧬 Motif discovery from seed: {seed_pattern}")

    # Start with fuzzy search
    initial_results = fuzzy.query_fuzzy(seed_pattern, max_distance=3)

    # Filter by frequency
    significant_results = [r for r in initial_results if r.count >= min_frequency]

    print(f"Found {len(significant_results)} significant motifs (≥{min_frequency} occurrences)")

    # Group by Hamming distance
    distance_groups = {}
    for result in significant_results:
        dist = result.distance
        if dist not in distance_groups:
            distance_groups[dist] = []
        distance_groups[dist].append(result)

    # Analyze each distance group
    for distance, group in sorted(distance_groups.items()):
        group.sort(key=lambda x: x.count, reverse=True)

        print(f"\nDistance {distance} ({len(group)} motifs):")
        for result in group[:10]:  # Show top 10
            print(f"  {result.kmer}: {result.count:,}")

        # Find consensus motif
        if len(group) >= 3:
            consensus = find_consensus([r.kmer for r in group])
            print(f"  Consensus: {consensus}")

def find_consensus(kmers):
    """Find consensus sequence from list of k-mers."""
    if not kmers:
        return ""

    consensus = []
    for pos in range(len(kmers[0])):
        bases = [kmer[pos] for kmer in kmers]

        # Count occurrences of each base
        base_counts = {'A': 0, 'T': 0, 'C': 0, 'G': 0}
        for base in bases:
            base_counts[base] += 1

        # Most common base
        most_common = max(base_counts, key=base_counts.get)
        consensus.append(most_common)

    return ''.join(consensus)

# Usage
discover_motifs(db_path, "ATGCGTA", min_frequency=50)
```

### Position-Specific Scoring

```python
def position_specific_search(db_path, pattern, position_scores):
    """Search with position-specific scoring."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🎯 Position-specific search: {pattern}")
    print("Position scores:")
    for pos, score in position_scores.items():
        print(f"  Position {pos}: {score}")

    results = fuzzy.query_fuzzy(pattern)

    # Calculate scores for each result
    scored_results = []

    for result in results:
        score = 0

        # Add position-specific scores
        for i, (base1, base2) in enumerate(zip(pattern, result.kmer)):
            if i in position_scores:
                if base1 == base2:
                    score += position_scores[i]
                elif base1 != 'N' and base2 != 'N':  # Both are specific bases
                    score -= position_scores[i] // 2  # Penalty for mismatch

        # Add count bonus
        score += result.count // 100  # Scale down count impact

        scored_results.append((result, score))

    # Sort by score
    scored_results.sort(key=lambda x: x[1], reverse=True)

    print(f"\nTop 20 scored results:")
    for i, (result, score) in enumerate(scored_results[:20], 1):
        print(f"  {i:2d}. {result.kmer} (dist={result.distance}, count={result.count:,}, score={score})")

    return [result for result, score in scored_results]

# Usage
# Higher scores for more important positions
position_scores = {
    0: 10,  # First position is very important
    1: 8,   # Second position important
    10: 5,  # Middle position moderately important
    20: 10  # Last position very important
}

scored_results = position_specific_search(db_path, "ATCGATCGATCGATCGATCGA", position_scores)
```

---

## Performance Optimization

### Efficient Wildcard Queries

```python
import time

def optimize_wildcard_queries(db_path, patterns):
    """Optimize wildcard queries for better performance."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🚀 Optimizing {len(patterns)} wildcard patterns")

    # Group patterns by complexity (number of wildcards)
    complexity_groups = {}

    for pattern in patterns:
        complexity = pattern.count('N')
        if complexity not in complexity_groups:
            complexity_groups[complexity] = []
        complexity_groups[complexity].append(pattern)

    print(f"Pattern complexity distribution:")
    for complexity, group_patterns in sorted(complexity_groups.items()):
        print(f"  {complexity} wildcards: {len(group_patterns)} patterns")

    # Process in order of complexity (simplest first)
    total_results = 0
    total_time = 0

    for complexity, group_patterns in sorted(complexity_groups.items()):
        print(f"\nProcessing {complexity}-wildcard patterns...")

        start_time = time.time()
        group_results = 0

        for pattern in group_patterns:
            results = fuzzy.query_fuzzy(pattern)
            group_results += len(results)

        pattern_time = time.time() - start_time
        total_time += pattern_time
        total_results += group_results

        print(f"  Completed in {pattern_time:.2f}s")
        print(f"  Average results per pattern: {group_results/len(group_patterns):.1f}")

    print(f"\nTotal performance:")
    print(f"  Total results: {total_results:,}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Results per second: {total_results/total_time:.0f}")

    return total_results
```

### Distance Search Optimization

```python
def adaptive_distance_search(db_path, query_kmer, target_result_count=1000):
    """Adaptive distance search to find target number of results."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🎯 Adaptive distance search for: {query_kmer}")
    print(f"Target result count: {target_result_count}")

    # Start with distance 1 and increase until we have enough results
    current_distance = 0
    all_results = []

    while current_distance <= 5 and len(all_results) < target_result_count:
        print(f"\nTrying distance {current_distance}...")

        start_time = time.time()
        distance_results = fuzzy.query_fuzzy(query_kmer, max_distance=current_distance)
        search_time = time.time() - start_time

        # Filter to only results at exactly this distance
        exact_distance_results = [r for r in distance_results if r.distance == current_distance]

        all_results.extend(exact_distance_results)

        print(f"  Found {len(exact_distance_results)} results at distance {current_distance}")
        print(f"  Search time: {search_time:.3f}s")
        print(f"  Total results so far: {len(all_results)}")

        current_distance += 1

        # Safety check to avoid infinite loops
        if len(exact_distance_results) == 0 and current_distance > 2:
            print("  No new results found, stopping search")
            break

    # Sort all results by count
    all_results.sort(key=lambda x: x.count, reverse=True)

    # Limit to target count
    final_results = all_results[:target_result_count]

    print(f"\nFinal Results:")
    print(f"  Total matches: {len(final_results)}")
    print(f"  Max distance searched: {current_distance - 1}")

    if final_results:
        print(f"  Distance distribution:")
        distance_counts = {}
        for result in final_results:
            if result.distance not in distance_counts:
                distance_counts[result.distance] = 0
            distance_counts[result.distance] += 1

        for dist, count in sorted(distance_counts.items()):
            print(f"    Distance {dist}: {count} results")

    return final_results
```

---

## Use Cases

### Biological Applications

```python
def snp_detection(db_path, reference_kmer, frequency_threshold=0.01):
    """Detect SNPs in the population using frequency analysis."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🧬 SNP detection for: {reference_kmer}")
    print(f"Frequency threshold: {frequency_threshold}")

    # Find all variants within distance 1 (single mutations)
    variants = db.fuzzy_query(reference_kmer, max_distance=1)

    # Calculate total count including reference
    reference_result = db.query_exact(reference_kmer)
    total_count = reference_result.count + sum(v.count for v in variants if v.distance == 1)

    if total_count == 0:
        print("No occurrences found")
        return []

    print(f"\nTotal occurrences: {total_count:,}")
    print(f"Reference count: {reference_result.count:,}")

    # Analyze variants
    significant_variants = []

    for variant in variants:
        if variant.distance == 1:  # Only single mutations
            frequency = variant.count / total_count

            if frequency >= frequency_threshold:
                significant_variants.append({
                    'kmer': variant.kmer,
                    'count': variant.count,
                    'frequency': frequency,
                    'mutation': identify_mutation(reference_kmer, variant.kmer)
                })

    # Sort by frequency
    significant_variants.sort(key=lambda x: x['frequency'], reverse=True)

    print(f"\nSignificant variants (≥{frequency_threshold*100:.1f}% frequency):")
    for i, variant in enumerate(significant_variants, 1):
        print(f"  {i}. {variant['kmer']}: {variant['count']:,} ({variant['frequency']*100:.2f}%)")
        print(f"     Mutation: {variant['mutation']}")

    return significant_variants

def identify_mutation(ref, var):
    """Identify the specific mutation."""
    for i, (ref_base, var_base) in enumerate(zip(ref, var)):
        if ref_base != var_base:
            return f"{ref_base}{i+1}{var_base}"  # Standard mutation notation
    return "unknown"

# Usage
snp_results = snp_detection(db_path, "ATCGATCGATCGATCGATCGA", frequency_threshold=0.005)
```

### Primer Design with Tolerance

```python
def tolerant_primer_design(db_path, target_region, primer_length=20):
    """Design primers with flexibility for mismatches."""

    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    db.load(db_path)

    print(f"🧪 Tolerant primer design for region: {target_region}")

    if len(target_region) < primer_length:
        print("Target region too short")
        return []

    # Extract potential primer binding sites
    primers = []
    for i in range(len(target_region) - primer_length + 1):
        primer = target_region[i:i+primer_length]

        # Allow up to 2 mismatches in the last 5 positions (3' end is most important)
        results = fuzzy.query_fuzzy(primer, max_distance=2)

        if results:
            # Calculate binding strength
            total_binding = sum(r.count for r in results if r.distance <= 1)

            primers.append({
                'sequence': primer,
                'position': i,
                'total_binding': total_binding,
                'exact_matches': sum(1 for r in results if r.distance == 0),
                'near_matches': sum(1 for r in results if r.distance == 1),
                'best_match': max(results, key=lambda x: x.count) if results else None
            })

    # Sort by binding strength
    primers.sort(key=lambda x: x['total_binding'], reverse=True)

    print(f"\nTop 10 primer candidates:")
    for i, primer in enumerate(primers[:10], 1):
        print(f"  {i:2d}. {primer['sequence']} (pos {primer['position']})")
        print(f"      Binding strength: {primer['total_binding']:,}")
        print(f"      Exact matches: {primer['exact_matches']}")
        print(f"      Near matches: {primer['near_matches']}")
        if primer['best_match']:
            print(f"      Best match: {primer['best_match'].kmer} (count: {primer['best_match'].count:,})")

    return primers[:10]

# Usage
target_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"
primer_candidates = tolerant_primer_design(db_path, target_sequence, primer_length=21)
```

---

## Best Practices

### Choosing the Right Search Strategy

```python
def choose_search_strategy(pattern, database_size_mb):
    """Recommend optimal search strategy based on pattern and database size."""

    pattern_complexity = pattern.count('N')
    pattern_length = len(pattern)

    print(f"📋 Search Strategy Recommendation")
    print(f"Pattern: {pattern}")
    print(f"Pattern complexity: {pattern_complexity} wildcards")
    print(f"Pattern length: {pattern_length}")
    print(f"Database size: {database_size_mb:.1f} MB")

    recommendations = []

    # Wildcard recommendations
    if pattern_complexity == 0:
        recommendations.append("Use exact query (query method) - fastest")
    elif pattern_complexity == 1:
        recommendations.append("Use fuzzy query with wildcards - efficient")
    elif pattern_complexity <= 3:
        recommendations.append("Use fuzzy query - moderate complexity")
    else:
        recommendations.append("⚠️  High complexity - consider reducing wildcards")

    # Distance-based recommendations
    if pattern_complexity == 0:
        recommendations.append("Consider Hamming distance search for variants")

    # Performance recommendations
    if database_size_mb > 1000 and pattern_complexity > 2:
        recommendations.append("⚠️  Large database with complex pattern - may be slow")

    if database_size_mb > 100:
        recommendations.append("Consider preloading database for multiple queries")

    print("\nRecommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

    return recommendations

# Usage
choose_search_strategy("ATNNGTANN", 500)  # Complex pattern, medium database
```

### Memory and Performance Tips

1. **Database Loading**:
   - Use `preload=True` for many queries
   - Use memory-mapped (default) for few queries
   - Close databases when done

2. **Pattern Complexity**:
   - Limit wildcards to ≤3 for optimal performance
   - Consider breaking complex patterns into simpler ones
   - Use distance-based search for variants instead of many wildcards

3. **Result Filtering**:
   - Filter results early to reduce memory usage
   - Use count thresholds to focus on significant matches
   - Sort results only when necessary

### Error Handling

```python
def safe_fuzzy_search(db_path, pattern, max_distance=None):
    """Safe fuzzy search with comprehensive error handling."""

    try:
        # Validate pattern
        if not pattern:
            raise ValueError("Pattern cannot be empty")

        if len(pattern) < 3:
            raise ValueError("Pattern too short (minimum 3 characters)")

        # Check for valid characters
        valid_chars = set('ATCGN')
        if not all(char in valid_chars for char in pattern.upper()):
            raise ValueError("Pattern contains invalid characters")

        # Load database and search
        # PyDatabase doesn't use context manager
            db.load(db_path)

            if max_distance is None:
                results = fuzzy.query_fuzzy(pattern)
            else:
                results = fuzzy.query_fuzzy(pattern, max_distance=max_distance)

            return {
                'success': True,
                'results': results,
                'pattern': pattern,
                'max_distance': max_distance
            }

    except FileNotFoundError:
        return {'success': False, 'error': f'Database file not found: {db_path}'}
    except ValueError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {e}'}

# Usage
result = safe_fuzzy_search("genome_k21.rkdb", "ATNNGTA", max_distance=2)
if result['success']:
    print(f"Found {len(result['results'])} matches")
else:
    print(f"Error: {result['error']}")
```

---

## Quick Reference

### Python API
```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Load database
# PyDatabase doesn't use context manager
    db.load("database.rkdb")

    # Wildcard search
    results = fuzzy.query_fuzzy("ATNNGTA")

    # Distance-based search
    results = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_distance=2)

    # Complex patterns
    results = fuzzy.query_fuzzy("ANNNNNNGT")
```

### Command Line
```bash
# Wildcard search
rustkmer fuzzy-query -d database.rkdb -p "ATNNGTA"

# Distance-based search
rustkmer fuzzy-query -d database.rkdb -p "ATCGATCGATCGATCGATCG" -m 2

# Multiple patterns
rustkmer fuzzy-query -d database.rkdb -f patterns.txt -o results.csv
```

---

## Need Help?

- **Documentation**: [Counting K-mers](counting-kmers.md) for database creation
- **API Reference**: [Python API](../api-reference/python/) for complete reference
- **Performance Tips**: [Performance Guide](performance-tips.md) for optimization
- **Troubleshooting**: [FAQ](../appendix/faq.md) for common issues