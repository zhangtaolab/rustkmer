#!/usr/bin/env python3
"""
Fuzzy Query Examples with RustKmer

This script demonstrates fuzzy k-mer searching capabilities:
- Basic fuzzy queries with mutation tolerance
- Position-specific mutations
- Batch fuzzy queries
- Analysis of fuzzy query results
- Performance optimization
"""

from pyrustkmer import PyDatabase, LoadMode, KmerCounter, PyFuzzyQuery
import tempfile
import os
import sys
import time
from collections import defaultdict, Counter

def example_1_basic_fuzzy_query():
    """Example 1: Basic fuzzy querying."""
    print("=" * 60)
    print("Example 1: Basic Fuzzy Querying")
    print("=" * 60)

    # Ensure database exists
    db_path = "example.rkdb"
    if not os.path.exists(db_path):
        create_sample_database_with_variants(db_path)

    try:
        db = PyDatabase(db_path)
fuzzy = PyFuzzyQuery(db)

        # Reference k-mer (should have exact match)
        reference_kmer = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        print(f"Reference k-mer: {reference_kmer}")

        # Query with different mutation tolerances
        for mutations in range(4):
            print(f"\n--- Mutation tolerance: {mutations} ---")
            result = fuzzy.query_fuzzy(reference_kmer, mutations=mutations)

            print(f"Total matches: {result.total_matches}")
            print(f"Exact matches: {result.exact_matches}")
            print(f"Fuzzy matches: {result.fuzzy_matches}")

            if result.total_matches > 0:
                # Show top matches
                top_matches = result.get_top_matches(5)
                print("Top 5 matches:")
                for i, match in enumerate(top_matches, 1):
                    print(f"  {i}. {match.kmer}: {match.count:,} (distance={match.distance})")


    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_2_position_mutations():
    """Example 2: Position-specific mutations."""
    print("\n" + "=" * 60)
    print("Example 2: Position-Specific Mutations")
    print("=" * 60)

    db_path = "example.rkdb"

    try:
        db = PyDatabase(db_path)
fuzzy = PyFuzzyQuery(db)

        reference_kmer = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        print(f"Reference k-mer: {reference_kmer}")
        print("Positions (1-based):")
        for i, base in enumerate(reference_kmer, 1):
            print(f"  {i:2d}: {base}")

        mutation_scenarios = [
            ("Single position mutation", "15:1"),
            ("Multiple positions, same budget", "10,15:2"),
            ("Range of positions", "20-25:2"),
            ("Multiple groups", "10,15:1;20,25:2"),
            ("Allow mutations anywhere", None)
        ]

        for description, position_mutations in mutation_scenarios:
            print(f"\n--- {description} ---")
            print(f"Position mutations: {position_mutations or 'None'}")

            start_time = time.time()

            if position_mutations:
                result = fuzzy.query_fuzzy(
                    reference_kmer,
                    mutations=3,
                    position_mutations=position_mutations
                )
            else:
                result = fuzzy.query_fuzzy(reference_kmer, mutations=2)

            query_time = time.time() - start_time

            print(f"Query time: {query_time:.4f} seconds")
            print(f"Total matches: {result.total_matches}")
            print(f"Unique variants: {len(result.get_fuzzy_matches())}")

            if result.total_matches > 0:
                # Analyze mutation patterns
                mutations_by_distance = defaultdict(int)
                for match in result.get_fuzzy_matches():
                    mutations_by_distance[match.distance] += 1

                print("Mutation distribution:")
                for distance in sorted(mutations_by_distance):
                    print(f"  Distance {distance}: {mutations_by_distance[distance]} variants")


    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_3_batch_fuzzy_queries():
    """Example 3: Batch fuzzy queries."""
    print("\n" + "=" * 60)
    print("Example 3: Batch Fuzzy Queries")
    print("=" * 60)

    db_path = "example.rkdb"

    # Prepare test k-mers
    test_kmers = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # Should match exactly
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",  # Should match exactly
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",  # Should match exactly
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",  # Should match exactly
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",           # Likely no match
        "ATCGATCGATCGATCGATCGATCGATCGATCGATGG",  # 1 mutation
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAA",  # 1 mutation
        "ATCGATCGATCGATCGATCGATCGATCGATCGAGCG",  # 1 mutation
    ]

    try:
        db = PyDatabase(db_path)
fuzzy = PyFuzzyQuery(db)

        print(f"Querying {len(test_kmers)} k-mers in batch...")
        print("K-mers to query:")
        for i, kmer in enumerate(test_kmers, 1):
            print(f"  {i:2d}. {kmer}")

        # Perform batch fuzzy query
        start_time = time.time()
        batch_result = db.fuzzy_query_batch(
            test_kmers,
            mutations=2,
            max_workers=4
        )
        batch_time = time.time() - start_time

        print(f"\nBatch query completed in {batch_time:.3f} seconds")
        print(f"Queries per second: {len(test_kmers) / batch_time:.1f}")

        # Results summary
        print(f"\nResults Summary:")
        print(f"  Total queries: {batch_result.total_queries}")
        print(f"  Successful: {batch_result.successful_queries}")
        print(f"  Failed: {batch_result.failed_queries}")

        # Detailed results
        print(f"\nDetailed Results:")
        for kmer, result in batch_result.successes.items():
            print(f"  {kmer[:20]:20} | "
                  f"Total: {result.total_matches:4d} | "
                  f"Exact: {result.exact_matches:4d} | "
                  f"Fuzzy: {result.fuzzy_matches:4d}")

        # Errors (if any)
        if batch_result.errors:
            print(f"\nErrors encountered:")
            for kmer, error in batch_result.errors.items():
                print(f"  {kmer[:20]:20} | {error}")


    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_4_performance_comparison():
    """Example 4: Performance comparison of different approaches."""
    print("\n" + "=" * 60)
    print("Example 4: Performance Comparison")
    print("=" * 60)

    db_path = "example.rkdb"

    # Test k-mers
    test_kmers = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
    ] * 100  # Repeat for more queries

    print(f"Performance test with {len(test_kmers)} queries")

    try:
        db = PyDatabase(db_path)
fuzzy = PyFuzzyQuery(db)

        # Method 1: Individual exact queries
        print("\n--- Method 1: Individual Exact Queries ---")
        start_time = time.time()

        exact_results = []
        for kmer in test_kmers:
            result = db.query_exact(kmer)
            exact_results.append(result.count)

        exact_time = time.time() - start_time
        exact_rate = len(test_kmers) / exact_time

        print(f"Time: {exact_time:.3f} seconds")
        print(f"Queries per second: {exact_rate:.1f}")
        print(f"Total exact matches found: {sum(exact_results)}")

        # Method 2: Individual fuzzy queries
        print("\n--- Method 2: Individual Fuzzy Queries ---")
        start_time = time.time()

        fuzzy_results = []
        for kmer in test_kmers:
            result = fuzzy.query_fuzzy(kmer, mutations=1)
            fuzzy_results.append(result.total_matches)

        fuzzy_time = time.time() - start_time
        fuzzy_rate = len(test_kmers) / fuzzy_time

        print(f"Time: {fuzzy_time:.3f} seconds")
        print(f"Queries per second: {fuzzy_rate:.1f}")
        print(f"Total fuzzy matches found: {sum(fuzzy_results)}")

        # Method 3: Batch fuzzy queries
        print("\n--- Method 3: Batch Fuzzy Queries ---")
        start_time = time.time()

        batch_result = db.fuzzy_query_batch(
            test_kmers[:100],  # Use subset to avoid timeout
            mutations=1,
            max_workers=4
        )

        batch_time = time.time() - start_time
        batch_rate = len(test_kmers[:100]) / batch_time

        print(f"Time: {batch_time:.3f} seconds")
        print(f"Queries per second: {batch_rate:.1f}")
        print(f"Successful queries: {batch_result.successful_queries}")

        # Performance summary
        print(f"\n--- Performance Summary ---")
        print(f"{'Method':<25} {'Time (s)':<10} {'Rate (q/s)':<12} {'Matches':<10}")
        print(f"{'Exact queries':<25} {exact_time:<10.3f} {exact_rate:<12.1f} {sum(exact_results):<10}")
        print(f"{'Fuzzy queries':<25} {fuzzy_time:<10.3f} {fuzzy_rate:<12.1f} {sum(fuzzy_results):<10}")
        print(f"{'Batch queries':<25} {batch_time:<10.3f} {batch_rate:<12.1f} "
              f"{sum(r.total_matches for r in batch_result.successes.values()):<10}")


    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_5_mutation_analysis():
    """Example 5: Analyze mutation patterns."""
    print("\n" + "=" * 60)
    print("Example 5: Mutation Pattern Analysis")
    print("=" * 60)

    db_path = "example.rkdb"

    try:
        db = PyDatabase(db_path)
fuzzy = PyFuzzyQuery(db)

        # Reference sequence
        reference_kmer = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        print(f"Analyzing mutations from: {reference_kmer}")

        # Query with higher mutation tolerance
        result = fuzzy.query_fuzzy(reference_kmer, mutations=3)

        print(f"\nFound {result.total_matches} total matches")
        print(f"Exact matches: {result.exact_matches}")
        print(f"Fuzzy matches: {result.fuzzy_matches}")

        if result.fuzzy_matches > 0:
            # Analyze mutation distribution
            mutation_counts = Counter()
            position_mutations = defaultdict(list)

            for match in result.get_fuzzy_matches():
                mutation_counts[match.distance] += 1

                for mutation in match.mutations:
                    # Parse mutation format like "15:A>T"
                    if '>' in mutation:
                        try:
                            parts = mutation.split(':')
                            pos_info = parts[0]  # e.g., "15:A>T"
                            if len(pos_info) > 1 and pos_info[0].isdigit():
                                position = int(pos_info.split(':')[0])  # Extract position
                                position_mutations[position].append(mutation)
                        except:
                            pass  # Skip malformed mutations

            print("\n--- Mutation Distance Distribution ---")
            for distance in sorted(mutation_counts.keys()):
                print(f"  Distance {distance}: {mutation_counts[distance]} variants")

            print("\n--- Most Common Mutation Positions ---")
            sorted_positions = sorted(position_mutations.items(),
                                    key=lambda x: len(x[1]), reverse=True)
            for pos, mutations in sorted_positions[:10]:
                print(f"  Position {pos}: {len(mutations)} mutations")
                for mut in mutations[:3]:  # Show first 3
                    print(f"    {mut}")

            # Calculate mutation hotspots (consecutive positions with many mutations)
            print("\n--- Mutation Hotspots ---")
            positions_with_mutations = sorted(position_mutations.keys())
            hotspot_threshold = 2  # Positions with at least 2 mutations

            hotspots = []
            i = 0
            while i < len(positions_with_mutations):
                start_pos = positions_with_mutations[i]
                end_pos = start_pos
                j = i + 1

                while j < len(positions_with_mutations):
                    if positions_with_mutations[j] == end_pos + 1:
                        end_pos = positions_with_mutations[j]
                        j += 1
                    else:
                        break

                if end_pos - start_pos + 1 >= 2:  # At least 2 consecutive positions
                    total_mutations = sum(len(position_mutations[pos])
                                            for pos in range(start_pos, end_pos + 1))
                    hotspots.append((start_pos, end_pos, total_mutations))

                i = j

            for start, end, count in sorted(hotspots, key=lambda x: x[2], reverse=True)[:5]:
                print(f"  Positions {start}-{end}: {count} total mutations")


    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def create_sample_database_with_variants(db_path):
    """Create a sample database with known variants."""
    print(f"Creating sample database with variants: {db_path}")

    # Create sequences with intentional variations
    sequences = [
        # Original sequences
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",

        # Single mutation variants
        "ATCGATCGATCGATCGATCGATCGATCGATCGATGG",  # C->G at position 31
        "ATCGATCGATCGATCGATCGATCGATCGATCGACCG",  # T->C at position 29
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCAA",  # G->A at position 32

        # Two mutation variants
        "ATCGATCGATCGATCGATCGATCGATCGATCGAGGG",  # Last 2 mutations
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTACTAG",  # Multiple mutations

        # Repeated sequences
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",

        # Low complexity
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        for i, seq in enumerate(sequences):
            f.write(f">sequence_{i+1}\n{seq}\n")
        fasta_file = f.name

    try:
        counter = PyCounter(k=31, canonical=True)
        counter.count_file(fasta_file)
        counter.save_to_database(db_path)

    finally:
        os.unlink(fasta_file)


def main():
    """Run all fuzzy query examples."""
    print("RustKmer Python API - Fuzzy Query Examples")
    print("============================================")

    examples = [
        ("Basic Fuzzy Querying", example_1_basic_fuzzy_query),
        ("Position-Specific Mutations", example_2_position_mutations),
        ("Batch Fuzzy Queries", example_3_batch_fuzzy_queries),
        ("Performance Comparison", example_4_performance_comparison),
        ("Mutation Analysis", example_5_mutation_analysis)
    ]

    results = []
    for name, example_func in examples:
        print(f"\nRunning: {name}")
        try:
            success = example_func()
            results.append((name, success))
        except Exception as e:
            print(f"Example '{name}' failed with error: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("EXAMPLES SUMMARY")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{name:25} {status}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nTotal: {passed}/{total} examples completed successfully")

    if passed == total:
        print("🎉 All examples completed successfully!")
        return 0
    else:
        print("⚠️  Some examples failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())