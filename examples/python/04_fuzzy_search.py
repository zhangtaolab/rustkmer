#!/usr/bin/env python3

"""
RustKmer Pattern Search Example

This script demonstrates pattern search functionality using the RustKmer Python API:
- Pattern-based k-mer generation (wildcards, variations)
- Multi-sequence querying strategies
- K-mer variant analysis and statistics
- Pattern search performance analysis

NOTE: This demonstrates how to implement pattern-based search using the existing
query functionality. True fuzzy search with built-in wildcards is not yet
implemented in the current RustKmer version.

Data: ../data/demo_rice_genome.fa.gz
K-mer size: 5-7 for optimal pattern search demonstration
Output: Pattern search results and performance metrics
"""

import os
import sys
import time
import itertools
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import rustkmer classes correctly
from rustkmer import KmerCounter, Database


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color


def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{Colors.BLUE}=== {title} ==={Colors.NC}")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_info(message: str):
    """Print an info message"""
    print(f"{Colors.YELLOW}→ {message}{Colors.NC}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_pattern(message: str):
    """Print a pattern search related message"""
    print(f"{Colors.MAGENTA}◈ {message}{Colors.NC}")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def get_data_path() -> Path:
    """Get the path to the demo data"""
    script_dir = Path(__file__).parent
    data_path = script_dir.parent / "data" / "demo_rice_genome.fa.gz"

    if not data_path.exists():
        # Use the actual test data that exists
        data_path = script_dir.parent.parent / "tests" / "007-api-compatibility" / "test_data" / "small_dataset.fa"
        if not data_path.exists():
            print_error(f"Demo data not found: {data_path}")
            print_info("Please ensure test data is available")
            sys.exit(1)

    return data_path


def get_output_dir() -> Path:
    """Get the output directory"""
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


def create_pattern_database(data_path: Path, output_dir: Path, kmer_size: int = 5):
    """Create a database for pattern search demonstrations"""
    print_header("Creating Pattern Search Database")

    db_file = output_dir / f"pattern_k{kmer_size}.rkdb"

    if db_file.exists():
        print_info(f"Using existing database: {db_file.name}")
        return str(db_file)

    print_pattern(f"Creating k={kmer_size} database for pattern search...")
    start_time = time.time()

    try:
        counter = KmerCounter(k=kmer_size, canonical=False, threads=4)
        counter.count_file(str(data_path))
        counter.save_to_database(str(db_file), False)

        end_time = time.time()

        if db_file.exists():
            file_size = db_file.stat().st_size
            print_success(f"Created pattern database: {db_file.name} ({format_file_size(file_size)})")
            print_info(f"Creation time: {end_time - start_time:.2f} seconds")

            # Get statistics from counter
            unique_kmers = counter.get_unique_count()
            total_kmers = counter.get_total_count()
            print_info(f"Total k-mers: {total_kmers:,}")
            print_info(f"Unique k-mers: {unique_kmers:,}")

            return str(db_file)
        else:
            print_error("Failed to create pattern database")
            return None

    except Exception as e:
        print_error(f"Error creating pattern database: {e}")
        return None


def expand_wildcard_pattern(pattern: str) -> List[str]:
    """Expand wildcard patterns (N → A,T,C,G)"""
    bases = ['A', 'T', 'C', 'G']
    positions = []

    for char in pattern:
        if char.upper() == 'N':
            positions.append(bases)
        else:
            positions.append([char.upper()])

    # Generate all combinations
    combinations = list(itertools.product(*positions))
    return [''.join(combo) for combo in combinations]


def generate_mutation_variants(sequence: str, max_mutations: int) -> List[str]:
    """Generate all variants with up to max_mutations"""
    bases = ['A', 'T', 'C', 'G']
    variants = set([sequence])

    for mutation_count in range(1, max_mutations + 1):
        new_variants = set()
        for variant in variants:
            for i in range(len(variant)):
                for base in bases:
                    if base != variant[i]:
                        mutated = list(variant)
                        mutated[i] = base
                        new_variants.add(''.join(mutated))
        variants.update(new_variants)

    return list(variants)


def wildcard_pattern_demo(db_path: str, kmer_size: int = 5):
    """Demonstrate wildcard pattern search using expansion"""
    print_header("Wildcard Pattern Search Demo")

    try:
        db = Database()
        db.load(db_path)

        # Test wildcard patterns
        wildcard_patterns = [
            "ACGT"[:kmer_size],      # Exact match (no wildcards)
            "ACGN"[:kmer_size],       # Single wildcard
            "ACGNA"[:kmer_size],      # Single wildcard at end
            "ANCN"[:kmer_size],       # Single wildcard in middle
            "ANAN"[:kmer_size],       # Two wildcards
        ]

        print_pattern("Testing wildcard pattern expansions:")
        print(f"{'Pattern':<10} {'Expansions':<12} {'Found':<8} {'Total Count':<12} {'Time (ms)'}")
        print("-" * 70)

        for pattern in wildcard_patterns:
            if len(pattern) == 0:
                continue

            # Expand pattern
            start_time = time.time()
            expansions = expand_wildcard_pattern(pattern)

            # Limit expansions to prevent explosion
            if len(expansions) > 1000:
                expansions = expansions[:1000]
                print_info(f"Limited expansions to 1000 for pattern '{pattern}'")

            # Query all expanded k-mers
            matches = []
            total_count = 0
            for expanded in expansions:
                result = db.query(expanded)
                if result and result.found:
                    matches.append((expanded, result.count))
                    total_count += result.count

            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000

            print(f"{pattern:<10} {len(expansions):<12} {len(matches):<8} "
                  f"{total_count:<12} {query_time_ms:.3f}")

            # Show expansion details for interesting cases
            if 'N' in pattern and len(pattern) <= 6 and len(expansions) <= 20:
                print_pattern(f"  Expansion of '{pattern}': {', '.join(expansions[:8])}"
                      f"{'...' if len(expansions) > 8 else ''}")

    except Exception as e:
        print_error(f"Error in wildcard pattern demo: {e}")


def mutation_tolerance_demo(db_path: str, kmer_size: int = 5):
    """Demonstrate mutation tolerance using variant generation"""
    print_header("Mutation Tolerance Search Demo")

    try:
        db = Database()
        db.load(db_path)

        # Test sequences
        test_sequences = [
            "ACGTACGT"[:kmer_size],
            "TGCATGCA"[:kmer_size],
            "ATGCATGC"[:kmer_size],
        ]

        mutation_levels = [0, 1, 2]  # Limit to prevent explosion

        print_pattern("Testing mutation tolerance:")
        print(f"{'Sequence':<10} {'Mutations':<12} {'Variants':<10} {'Matches':<10} {'Time (ms)':<12}")
        print("-" * 65)

        for sequence in test_sequences:
            for mutations in mutation_levels:
                start_time = time.time()

                # Generate variants
                if mutations == 0:
                    variants = [sequence]
                else:
                    variants = generate_mutation_variants(sequence, mutations)
                    # Limit variants to prevent explosion
                    if len(variants) > 500:
                        variants = variants[:500]

                # Query variants
                matches = []
                for variant in variants:
                    result = db.query(variant)
                    if result and result.found:
                        matches.append((variant, result.count))

                end_time = time.time()
                query_time_ms = (end_time - start_time) * 1000

                total_count = sum(count for _, count in matches)

                print(f"{sequence:<10} {mutations:<12} {len(variants):<10} {len(matches):<10} {query_time_ms:<12.3f}")

    except Exception as e:
        print_error(f"Error in mutation tolerance demo: {e}")


def advanced_pattern_demo(db_path: str, kmer_size: int = 5):
    """Demonstrate advanced pattern search strategies"""
    print_header("Advanced Pattern Search Strategies")

    try:
        db = Database()
        db.load(db_path)

        # Advanced pattern search strategies
        strategies = [
            {
                'name': 'High-Confidence Core',
                'pattern': 'ACGT',
                'description': 'Exact match with high confidence'
            },
            {
                'name': 'Single Degenerate',
                'pattern': 'ACN',
                'description': 'Single position uncertainty'
            },
            {
                'name': 'Double Degenerate',
                'pattern': 'ANN',
                'description': 'Two positions with uncertainty'
            },
            {
                'name': 'Primer Binding',
                'pattern': 'ACGTN',
                'description': 'Simulated primer binding site'
            }
        ]

        print_pattern("Advanced pattern search analysis:")

        for strategy in strategies:
            pattern = strategy['pattern'][:kmer_size]
            if len(pattern) == 0:
                continue

            print(f"\n{Colors.CYAN}Strategy: {strategy['name']}{Colors.NC}")
            print(f"Description: {strategy['description']}")
            print(f"Pattern: {pattern}")

            # Search strategy
            start_time = time.time()

            if 'N' in pattern:
                # Expand wildcards
                expansions = expand_wildcard_pattern(pattern)
                if len(expansions) > 200:
                    expansions = expansions[:200]
                    print_info(f"Limited expansions to 200 for performance")

                matches = []
                for expanded in expansions:
                    result = db.query(expanded)
                    if result and result.found:
                        matches.append((expanded, result.count))
            else:
                # Direct query
                result = db.query(pattern)
                matches = [(pattern, result.count)] if result and result.found else []

            end_time = time.time()

            total_count = sum(count for _, count in matches)
            query_time_ms = (end_time - start_time) * 1000

            print_pattern(f"  Matches found: {len(matches)}")
            print_pattern(f"  Total count: {total_count:,}")
            print_pattern(f"  Query time: {query_time_ms:.3f} ms")

            # Show top matches
            if matches:
                matches.sort(key=lambda x: x[1], reverse=True)
                print_pattern(f"  Top matches: {', '.join([f'{m[0]}({m[1]})' for m in matches[:5]])}")

    except Exception as e:
        print_error(f"Error in advanced pattern demo: {e}")


def pattern_search_performance(db_path: str, kmer_size: int = 5):
    """Analyze pattern search performance"""
    print_header("Pattern Search Performance Analysis")

    try:
        db = Database()
        db.load(db_path)

        # Performance test scenarios
        test_scenarios = [
            {
                'name': 'Exact Match',
                'patterns': ['ACGT', 'TGCA', 'ATGC'],
                'expansion_limit': None
            },
            {
                'name': 'Single Wildcard',
                'patterns': ['ACN', 'TGN', 'ATN'],
                'expansion_limit': 100
            },
            {
                'name': 'Double Wildcard',
                'patterns': ['ANN', 'TNN', 'ATN'],
                'expansion_limit': 50
            },
            {
                'name': 'Mixed Pattern',
                'patterns': ['ACN', 'TGN', 'AN'],
                'expansion_limit': 200
            }
        ]

        print_pattern("Performance test scenarios:")
        print(f"{'Scenario':<20} {'Patterns':<10} {'Time (ms)':<12} {'Matches':<10} {'Avg/Pattern (ms)':<18}")
        print("-" * 80)

        results = []

        for scenario in test_scenarios:
            total_matches = 0
            total_expansions = 0
            start_time = time.time()

            for pattern in scenario['patterns']:
                pattern = pattern[:kmer_size]
                if len(pattern) == 0:
                    continue

                if 'N' in pattern:
                    # Expand wildcards
                    expansions = expand_wildcard_pattern(pattern)
                    if scenario['expansion_limit'] and len(expansions) > scenario['expansion_limit']:
                        expansions = expansions[:scenario['expansion_limit']]

                    total_expansions += len(expansions)
                    for expanded in expansions:
                        result = db.query(expanded)
                        if result and result.found:
                            total_matches += result.count
                else:
                    # Direct query
                    result = db.query(pattern)
                    if result and result.found:
                        total_matches += result.count
                    total_expansions += 1

            end_time = time.time()
            total_time_ms = (end_time - start_time) * 1000
            valid_patterns = len([p for p in scenario['patterns'] if len(p[:kmer_size]) > 0])
            avg_time_per_pattern = total_time_ms / max(1, valid_patterns)

            print(f"{scenario['name']:<20} {valid_patterns:<10} "
                  f"{total_time_ms:<12.3f} {total_matches:<10} {avg_time_per_pattern:<18.3f}")

            results.append({
                'name': scenario['name'],
                'time_ms': total_time_ms,
                'matches': total_matches,
                'patterns': valid_patterns,
                'expansions': total_expansions
            })

        # Find most efficient scenario
        if results:
            most_efficient = min(results, key=lambda x: x['time_ms'] / max(1, x['patterns']))
            print(f"\n{Colors.GREEN}Most efficient: {most_efficient['name']} "
                  f"({most_efficient['time_ms']:.3f} ms total){Colors.NC}")

    except Exception as e:
        print_error(f"Error in pattern search performance analysis: {e}")


def export_pattern_results(db_path: str, output_dir: Path, kmer_size: int = 5):
    """Export comprehensive pattern search results"""
    print_header("Export Pattern Search Results")

    try:
        db = Database()
        db.load(db_path)

        # Comprehensive pattern test
        test_patterns = [
            # Exact patterns
            "ACGT", "TGCA", "ATGC", "CGAT",
            # Single wildcards
            "ACN", "TGN", "ATN", "CGN",
            # Double wildcards
            "ANN", "TNN", "ATN", "CNN",
            # Mixed patterns
            "ACN", "TGN", "AN", "CN"
        ]

        # Filter patterns by kmer_size
        test_patterns = [p[:kmer_size] for p in test_patterns if len(p[:kmer_size]) > 0]
        test_patterns = list(set(test_patterns))  # Remove duplicates

        export_file = output_dir / f"pattern_search_results_k{kmer_size}.txt"

        print_pattern(f"Performing comprehensive pattern search...")
        start_time = time.time()

        all_results = []
        pattern_stats = {}

        for pattern in test_patterns:
            if 'N' in pattern:
                # Expand wildcards
                expansions = expand_wildcard_pattern(pattern)
                if len(expansions) > 500:
                    expansions = expansions[:500]

                pattern_matches = []
                for expanded in expansions:
                    result = db.query(expanded)
                    if result and result.found:
                        pattern_matches.append((expanded, result.count))
            else:
                # Direct query
                result = db.query(pattern)
                pattern_matches = [(pattern, result.count)] if result and result.found else []
                expansions = [pattern]

            all_results.extend(pattern_matches)
            pattern_stats[pattern] = {
                'expansions': len(expansions),
                'matches': len(pattern_matches),
                'total_count': sum(m[1] for m in pattern_matches)
            }

        end_time = time.time()

        # Write export file
        with open(export_file, 'w') as f:
            f.write(f"# RustKmer Pattern Search Results Export\n")
            f.write(f"# Database: {db_path}\n")
            f.write(f"# K-mer size: {kmer_size}\n")
            f.write(f"# Patterns tested: {len(test_patterns)}\n")
            f.write(f"# Total expansions: {sum(stats['expansions'] for stats in pattern_stats.values())}\n")
            f.write(f"# Total matches: {len(all_results)}\n")
            f.write(f"# Total count: {sum(m[1] for m in all_results):,}\n")
            f.write(f"# Search time: {end_time - start_time:.3f}s\n")
            f.write(f"# Export timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("#\n")
            f.write("# Pattern Statistics:\n")
            f.write("# Pattern\tExpansions\tMatches\tTotal_Count\n")
            f.write("# " + "=" * 50 + "\n")

            for pattern, stats in pattern_stats.items():
                f.write(f"{pattern}\t{stats['expansions']}\t{stats['matches']}\t{stats['total_count']}\n")

            f.write("#\n")
            f.write("# All Matched K-mers (sorted by count descending):\n")
            f.write("# Format: KMER\tCOUNT\tPATTERN\n")
            f.write("# " + "=" * 50 + "\n")

            # Sort all results by count descending
            all_results.sort(key=lambda x: x[1], reverse=True)

            for kmer, count in all_results:
                f.write(f"{kmer}\t{count}\tGenerated\n")

        if export_file.exists():
            export_size = export_file.stat().st_size
            print_success(f"Exported pattern results to: {export_file.name}")
            print_info(f"Export size: {format_file_size(export_size)}")
            print_info(f"Total k-mers matched: {len(all_results)}")

            # Show top results
            print_pattern("Top 10 most frequent pattern matches:")
            for kmer, count in all_results[:10]:
                print(f"  {kmer}: {count:,}")

    except Exception as e:
        print_error(f"Error exporting pattern results: {e}")


def main():
    """Main execution function"""
    print_header("RustKmer Pattern Search Examples")

    # Configuration
    kmer_size = 5  # Smaller k-mer size better for pattern search demonstration
    data_path = get_data_path()
    output_dir = get_output_dir()

    print(f"Data: {data_path}")
    if data_path.exists():
        print(f"Data size: {format_file_size(data_path.stat().st_size)}")
    print(f"K-mer size: {kmer_size} (optimized for pattern search)")
    print(f"Output: {output_dir}")

    print_info("NOTE: This demonstrates pattern-based search using existing query functionality.")
    print_info("True fuzzy search with built-in wildcards is not yet implemented.")

    # Create pattern search database
    print()
    db_path = create_pattern_database(data_path, output_dir, kmer_size)

    if not db_path:
        print_error("Failed to create pattern search database")
        return False

    # Execute pattern search demonstrations
    print()
    wildcard_pattern_demo(db_path, kmer_size)

    print()
    mutation_tolerance_demo(db_path, kmer_size)

    print()
    advanced_pattern_demo(db_path, kmer_size)

    print()
    pattern_search_performance(db_path, kmer_size)

    print()
    export_pattern_results(db_path, output_dir, kmer_size)

    print_header("Pattern Search Examples Completed Successfully!")
    print_success(f"All pattern search examples completed with k={kmer_size}")
    print_info("Pattern search results exported to output directory")
    print_info("You can now perform pattern searches using:")
    print(f"  python -c \"from rustkmer import Database; db=Database(); db.load('{db_path}'); print(db.query('ACGT').count)\"")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_info("\nScript interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)