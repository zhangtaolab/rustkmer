"""
Test Data Generators for Python API Validation
=============================================

This module provides comprehensive test data generators for validating
Python API functionality across all user stories and edge cases.

Generated test data includes:
- K-mer sequences with various patterns and edge cases
- Fuzzy query patterns with wildcards and variant limits
- Large-scale genomic sequences for performance testing
- Invalid/corrupted data for error handling validation
"""

import random
import string
from typing import List, Dict, Tuple, Generator, Optional
from pathlib import Path
import gzip
import json


class KmerDataGenerator:
    """Generates k-mer test sequences for validation testing."""

    def __init__(self, random_seed: int = 42):
        random.seed(random_seed)
        self.nucleotides = ['A', 'T', 'C', 'G']

    def generate_basic_kmers(self, k: int, count: int = 1000) -> List[str]:
        """Generate basic random k-mers."""
        kmers = []
        for _ in range(count):
            kmer = ''.join(random.choices(self.nucleotides, k=k))
            kmers.append(kmer)
        return kmers

    def generate_palindromic_kmers(self, k: int, count: int = 100) -> List[str]:
        """Generate palindromic k-mers for edge case testing."""
        kmers = []
        for _ in range(count):
            half_len = k // 2
            if k % 2 == 0:
                half = ''.join(random.choices(self.nucleotides, k=half_len))
                kmer = half + half[::-1]
            else:
                half = ''.join(random.choices(self.nucleotides, k=half_len))
                middle = random.choice(self.nucleotides)
                kmer = half + middle + half[::-1]
            kmers.append(kmer)
        return kmers

    def generate_low_complexity_kmers(self, k: int, count: int = 50) -> List[str]:
        """Generate low complexity k-mers (repetitive patterns)."""
        kmers = []
        patterns = [
            'A' * k,
            'T' * k,
            'C' * k,
            'G' * k,
            'AT' * (k // 2) + ('A' if k % 2 else ''),
            'GC' * (k // 2) + ('G' if k % 2 else ''),
            'ATCG' * (k // 4) + ('ATC'[:k % 4] if k % 4 else ''),
        ]

        for _ in range(count):
            kmer = random.choice(patterns)
            kmers.append(kmer)
        return kmers

    def generate_gc_extreme_kmers(self, k: int, count: int = 50) -> List[str]:
        """Generate k-mers with extreme GC content."""
        kmers = []

        # Very high GC content (>80%)
        high_gc = ['G', 'G', 'G', 'C', 'C', 'A', 'T']  # 71% GC
        for _ in range(count // 2):
            kmer = ''.join(random.choices(high_gc, k=k))
            kmers.append(kmer)

        # Very low GC content (<20%)
        low_gc = ['A', 'A', 'A', 'T', 'T', 'G', 'C']  # 29% GC
        for _ in range(count // 2):
            kmer = ''.join(random.choices(low_gc, k=k))
            kmers.append(kmer)

        return kmers

    def generate_repetitive_motif_kmers(self, k: int, motif: str, count: int = 20) -> List[str]:
        """Generate k-mers containing repetitive motifs."""
        kmers = []
        motif_len = len(motif)

        for _ in range(count):
            # Place motif at random position
            if motif_len > k:
                continue

            start_pos = random.randint(0, k - motif_len)
            kmer_list = list('N' * k)

            # Insert motif
            for i, base in enumerate(motif):
                if start_pos + i < k:
                    kmer_list[start_pos + i] = base

            # Fill remaining positions randomly
            for i in range(k):
                if kmer_list[i] == 'N':
                    kmer_list[i] = random.choice(self.nucleotides)

            kmers.append(''.join(kmer_list))

        return kmers


class FuzzyQueryDataGenerator:
    """Generates fuzzy query patterns for validation testing."""

    def __init__(self, random_seed: int = 42):
        random.seed(random_seed)
        self.nucleotides = ['A', 'T', 'C', 'G']

    def generate_wildcard_patterns(self, k: int, wildcard_counts: List[int]) -> Dict[str, List[str]]:
        """Generate patterns with specified numbers of wildcards."""
        patterns = {}

        for count in wildcard_counts:
            if count > k:
                continue

            patterns[f"{count}_wildcards"] = []

            for _ in range(100):  # Generate 100 patterns per count
                kmer_list = list('N' * k)

                # Place wildcards
                wildcard_positions = random.sample(range(k), count)
                for pos in wildcard_positions:
                    kmer_list[pos] = 'N'

                # Fill remaining with nucleotides
                for i in range(k):
                    if kmer_list[i] == 'N' and i not in wildcard_positions:
                        kmer_list[i] = random.choice(self.nucleotides)

                patterns[f"{count}_wildcards"].append(''.join(kmer_list))

        return patterns

    def generate_high_variant_patterns(self, k: int, max_variants_threshold: int = 50000) -> List[str]:
        """Generate patterns that would exceed variant limits."""
        patterns = []

        # Generate patterns with many Ns
        for n_count in range(10, min(k, 25)):  # Start from 10 Ns
            if 4**n_count > max_variants_threshold:
                base_pattern = 'A' * (k - n_count) + 'N' * n_count
                patterns.append(base_pattern)

        return patterns

    def generate_mutation_patterns(self, k: int, mutation_distance: int = 1) -> List[Tuple[str, List[str]]]:
        """Generate patterns for mutation testing."""
        patterns = []

        # Start with a base sequence
        base_sequence = ''.join(random.choices(self.nucleotides, k=k))
        mutated_sequences = []

        # Generate all possible single mutations
        for i in range(k):
            for nucleotide in self.nucleotides:
                if nucleotide != base_sequence[i]:
                    mutated = base_sequence[:i] + nucleotide + base_sequence[i+1:]
                    mutated_sequences.append(mutated)

        patterns.append((base_sequence, mutated_sequences))
        return patterns


class LargeScaleDataGenerator:
    """Generates large-scale genomic data for performance testing."""

    def __init__(self, random_seed: int = 42):
        random.seed(random_seed)
        self.nucleotides = ['A', 'T', 'C', 'G']

    def generate_genomic_sequence(self, length: int, gc_content: float = 0.5) -> str:
        """Generate a genomic sequence with specified GC content."""
        # Adjust nucleotide probabilities for GC content
        gc_prob = gc_content / 2
        at_prob = (1 - gc_content) / 2

        nucleotides_weighted = [
            ('A', at_prob),
            ('T', at_prob),
            ('G', gc_prob),
            ('C', gc_prob)
        ]

        sequence = []
        cumulative_probs = [0.0]
        for _, prob in nucleotides_weighted:
            cumulative_probs.append(cumulative_probs[-1] + prob)

        for _ in range(length):
            r = random.random()
            for i in range(1, len(cumulative_probs)):
                if r <= cumulative_probs[i]:
                    sequence.append(nucleotides_weighted[i-1][0])
                    break

        return ''.join(sequence)

    def generate_rnaseq_reads(self, read_length: int = 100, read_count: int = 10000) -> List[str]:
        """Generate RNA-seq like reads."""
        reads = []

        # Generate some reference transcripts
        transcript_length = read_length * 5
        reference = self.generate_genomic_sequence(transcript_length)

        for _ in range(read_count):
            # Random start position
            if len(reference) >= read_length:
                start_pos = random.randint(0, len(reference) - read_length)
                read = reference[start_pos:start_pos + read_length]

                # Add some errors
                read_list = list(read)
                for i in range(len(read_list)):
                    if random.random() < 0.01:  # 1% error rate
                        read_list[i] = random.choice(self.nucleotides)

                reads.append(''.join(read_list))

        return reads

    def generate_fasta_file(self, sequences: List[str], output_path: Path,
                           headers: Optional[List[str]] = None) -> None:
        """Generate FASTA file from sequences."""
        if headers is None:
            headers = [f">seq_{i}" for i in range(len(sequences))]

        with open(output_path, 'w') as f:
            for header, seq in zip(headers, sequences):
                f.write(f"{header}\n")
                # Write sequence in 80-character lines
                for i in range(0, len(seq), 80):
                    f.write(seq[i:i+80] + "\n")

    def generate_fastq_file(self, reads: List[str], output_path: Path,
                           headers: Optional[List[str]] = None) -> None:
        """Generate FASTQ file from reads."""
        if headers is None:
            headers = [f"@read_{i}" for i in range(len(reads))]

        with open(output_path, 'w') as f:
            for header, read in zip(headers, reads):
                # Generate quality scores (Phred+33)
                qual_scores = ''.join(chr(random.randint(30, 40)) for _ in range(len(read)))

                f.write(f"{header}\n")
                f.write(f"{read}\n")
                f.write(f"+\n")
                f.write(f"{qual_scores}\n")


class ErrorCaseGenerator:
    """Generates error cases for robustness testing."""

    def __init__(self):
        self.invalid_chars = ['B', 'D', 'E', 'F', 'H', 'I', 'J', 'K', 'L', 'M',
                             'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X',
                             'Y', 'Z', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

    def generate_invalid_kmers(self, k: int, count: int = 50) -> List[str]:
        """Generate k-mers with invalid characters."""
        invalid_kmers = []

        for _ in range(count):
            kmer = []
            for _ in range(k):
                if random.random() < 0.2:  # 20% chance of invalid character
                    kmer.append(random.choice(self.invalid_chars))
                else:
                    kmer.append(random.choice(['A', 'T', 'C', 'G']))
            invalid_kmers.append(''.join(kmer))

        return invalid_kmers

    def generate_empty_and_invalid_inputs(self) -> Dict[str, str]:
        """Generate various invalid input cases."""
        return {
            "empty_string": "",
            "only_whitespace": "   \t\n   ",
            "only_newlines": "\n\n\n",
            "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
            "mixed_case": "aTcGatCGATcG",
            "unicode": "ÅTCGÄÖÜß",
            "too_short": "ATCG",  # For k=21 testing
            "numbers": "123456789012345678901",
        }

    def generate_extreme_inputs(self) -> Dict[str, str]:
        """Generate extreme input cases."""
        return {
            "very_long_sequence": "ATCG" * 100000,  # 400k characters
            "all_wildcards": "N" * 1000,
            "all_same_base": "A" * 1000,
            "alternating": "ATATATATATATATATATATATATATATATATATATATATAT",
            "random_noise": ''.join(random.choice(['A', 'T', 'C', 'G', 'N']) for _ in range(10000))
        }


class TestDataSuite:
    """Main class for generating comprehensive test data suite."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.kmer_gen = KmerDataGenerator()
        self.fuzzy_gen = FuzzyQueryDataGenerator()
        self.large_gen = LargeScaleDataGenerator()
        self.error_gen = ErrorCaseGenerator()

    def generate_all_test_data(self):
        """Generate complete test data suite."""
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate k-mer test data
        self._generate_kmer_data()

        # Generate fuzzy query data
        self._generate_fuzzy_query_data()

        # Generate large-scale data
        self._generate_large_scale_data()

        # Generate error cases
        self._generate_error_cases()

        # Generate metadata
        self._generate_metadata()

    def _generate_kmer_data(self):
        """Generate k-mer test datasets."""
        kmer_dir = self.output_dir / "kmers"
        kmer_dir.mkdir(exist_ok=True)

        # Test different k values
        k_values = [13, 21, 31]

        for k in k_values:
            kmer_data = {
                "basic": self.kmer_gen.generate_basic_kmers(k, 1000),
                "palindromic": self.kmer_gen.generate_palindromic_kmers(k, 100),
                "low_complexity": self.kmer_gen.generate_low_complexity_kmers(k, 50),
                "gc_extreme": self.kmer_gen.generate_gc_extreme_kmers(k, 50),
                "repetitive_motif": self.kmer_gen.generate_repetitive_motif_kmers(k, "ATCG", 20)
            }

            # Save to JSON
            output_file = kmer_dir / f"k{k}_test_data.json"
            with open(output_file, 'w') as f:
                json.dump(kmer_data, f, indent=2)

    def _generate_fuzzy_query_data(self):
        """Generate fuzzy query test datasets."""
        fuzzy_dir = self.output_dir / "fuzzy_queries"
        fuzzy_dir.mkdir(exist_ok=True)

        # Test different k values
        k_values = [13, 21, 31]

        for k in k_values:
            fuzzy_data = {
                "wildcard_patterns": self.fuzzy_gen.generate_wildcard_patterns(
                    k, [1, 2, 3, 5, 10, 15]
                ),
                "high_variant_patterns": self.fuzzy_gen.generate_high_variant_patterns(k),
                "mutation_patterns": self.fuzzy_gen.generate_mutation_patterns(k, 1)
            }

            # Save to JSON
            output_file = fuzzy_dir / f"k{k}_fuzzy_data.json"
            with open(output_file, 'w') as f:
                json.dump(fuzzy_data, f, indent=2)

    def _generate_large_scale_data(self):
        """Generate large-scale test datasets."""
        large_dir = self.output_dir / "large_scale"
        large_dir.mkdir(exist_ok=True)

        # Generate genomic sequences of different sizes
        sizes = {
            "small": 1000,
            "medium": 10000,
            "large": 100000,
            "xlarge": 1000000
        }

        sequences = {}
        for size_name, length in sizes.items():
            seq = self.large_gen.generate_genomic_sequence(length, gc_content=0.45)
            sequences[size_name] = seq

        # Save sequences
        for size_name, seq in sequences.items():
            output_file = large_dir / f"sequence_{size_name}.fa"
            self.large_gen.generate_fasta_file([seq], output_file, [f">{size_name}_sequence"])

        # Generate RNA-seq reads
        reads = self.large_gen.generate_rnaseq_reads(100, 10000)
        reads_file = large_dir / "rnaseq_reads.fq"
        self.large_gen.generate_fastq_file(reads, reads_file)

    def _generate_error_cases(self):
        """Generate error case datasets."""
        error_dir = self.output_dir / "error_cases"
        error_dir.mkdir(exist_ok=True)

        error_data = {
            "invalid_kmers": {
                str(k): self.error_gen.generate_invalid_kmers(k, 50)
                for k in [13, 21, 31]
            },
            "invalid_inputs": self.error_gen.generate_empty_and_invalid_inputs(),
            "extreme_inputs": self.error_gen.generate_extreme_inputs()
        }

        # Save to JSON
        output_file = error_dir / "error_cases.json"
        with open(output_file, 'w') as f:
            json.dump(error_data, f, indent=2)

    def _generate_metadata(self):
        """Generate metadata for the test data suite."""
        metadata = {
            "generation_timestamp": "2025-12-01T22:45:00Z",
            "generator_version": "1.0.0",
            "random_seed": 42,
            "test_data_structure": {
                "kmers": {
                    "description": "K-mer sequences for various test scenarios",
                    "k_values": [13, 21, 31],
                    "categories": ["basic", "palindromic", "low_complexity", "gc_extreme", "repetitive_motif"]
                },
                "fuzzy_queries": {
                    "description": "Fuzzy query patterns with wildcards and mutations",
                    "k_values": [13, 21, 31],
                    "categories": ["wildcard_patterns", "high_variant_patterns", "mutation_patterns"]
                },
                "large_scale": {
                    "description": "Large-scale genomic data for performance testing",
                    "categories": ["genomic_sequences", "rnaseq_reads"],
                    "sizes": ["small", "medium", "large", "xlarge"]
                },
                "error_cases": {
                    "description": "Invalid and extreme input cases for robustness testing",
                    "categories": ["invalid_kmers", "invalid_inputs", "extreme_inputs"]
                }
            },
            "validation_purposes": [
                "FuzzyQuery API Enhancement validation",
                "Database persistence testing",
                "Performance monitoring validation",
                "Error handling robustness testing",
                "Edge case coverage"
            ]
        }

        # Save metadata
        output_file = self.output_dir / "metadata.json"
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    # Generate test data suite when run directly
    import sys

    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    else:
        output_dir = Path(__file__).parent

    print(f"Generating test data suite in {output_dir}")
    suite = TestDataSuite(output_dir)
    suite.generate_all_test_data()
    print("Test data suite generated successfully!")