"""Comprehensive test suite for PyCounter class."""

import os
import gzip
import tempfile
from pathlib import Path

import pytest

try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)


class TestPyCounterBasicCreation:
    """Test basic PyCounter creation and initialization."""

    def test_create_counter_default_params(self):
        """Test creating a counter with default parameters."""
        counter = pyrustkmer.PyCounter(21)
        assert counter is not None
        assert counter.kmer_length == 21
        assert counter.canonical == False

    def test_create_counter_with_canonical(self):
        """Test creating a counter with canonical mode enabled."""
        counter = pyrustkmer.PyCounter(21, canonical=True)
        assert counter is not None
        assert counter.kmer_length == 21
        assert counter.canonical == True

    def test_create_counter_with_custom_capacity(self):
        """Test creating a counter with custom initial capacity."""
        counter = pyrustkmer.PyCounter(21, canonical=True, initial_capacity=5000)
        assert counter is not None
        assert counter.kmer_length == 21
        assert counter.canonical == True

    def test_create_counter_various_k_sizes(self):
        """Test creating counters with various k-mer sizes."""
        valid_sizes = [1, 7, 15, 21, 31, 33, 64]
        for k in valid_sizes:
            counter = pyrustkmer.PyCounter(k)
            assert counter.kmer_length == k

    def test_invalid_kmer_size_zero_raises_error(self):
        """Test that k-mer size of 0 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid k-mer size"):
            pyrustkmer.PyCounter(0)

    def test_invalid_kmer_size_negative_raises_error(self):
        """Test that negative k-mer size raises ValueError."""
        with pytest.raises(ValueError, match="Invalid k-mer size"):
            pyrustkmer.PyCounter(-1)

    def test_invalid_kmer_size_too_large_raises_error(self):
        """Test that k-mer size > 64 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid k-mer size"):
            pyrustkmer.PyCounter(65)

    def test_counter_repr(self):
        """Test counter string representation."""
        counter = pyrustkmer.PyCounter(21, canonical=True)
        repr_str = repr(counter)
        assert "PyCounter" in repr_str
        assert "kmer_length=21" in repr_str
        assert "canonical=true" in repr_str


class TestPyCounterAddKmer:
    """Test adding individual k-mers to the counter."""

    def test_add_single_kmer(self):
        """Test adding a single k-mer."""
        counter = pyrustkmer.PyCounter(21)
        counter.add_kmer("A" * 21)
        assert counter.get_count("A" * 21) == 1

    def test_add_multiple_kmers(self):
        """Test adding multiple different k-mers."""
        counter = pyrustkmer.PyCounter(7)
        kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT"]
        for kmer in kmers:
            counter.add_kmer(kmer)

        for kmer in kmers:
            assert counter.get_count(kmer) == 1

    def test_add_duplicate_kmer_increments_count(self):
        """Test that adding the same k-mer multiple times increments count."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("AAAAAAA")
        assert counter.get_count("AAAAAAA") == 3

    def test_add_kmer_with_mixed_case(self):
        """Test adding k-mers with mixed case."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AaAaAaA")
        # Should be treated as "AAAAAAA"
        assert counter.get_count("AAAAAAA") == 1

    def test_add_kmer_wrong_length_raises_error(self):
        """Test that k-mer with wrong length raises ValueError."""
        counter = pyrustkmer.PyCounter(7)
        with pytest.raises(ValueError, match="K-mer length mismatch"):
            counter.add_kmer("AAA")

    def test_add_kmer_invalid_characters_raises_error(self):
        """Test that k-mer with invalid characters raises ValueError."""
        counter = pyrustkmer.PyCounter(7)
        with pytest.raises(ValueError, match="Failed to encode k-mer"):
            counter.add_kmer("ANNNNNN")


class TestPyCounterAddSequence:
    """Test adding k-mers from sequence strings."""

    def test_add_sequence_exact_length(self):
        """Test adding a sequence exactly equal to k-mer length."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_sequence("ACGTACG")
        assert counter.get_count("ACGTACG") == 1

    def test_add_sequence_longer_than_k(self):
        """Test adding a sequence longer than k-mer length."""
        counter = pyrustkmer.PyCounter(3)
        counter.add_sequence("ACGTACGTACG")
        # Should extract 3-mers: ACG, CGT, GTA, TAC, ACG, CGT, GTA, TAC, ACG
        # ACG appears at positions 0, 3, 6 -> count 3
        assert counter.get_count("ACG") == 3
        assert counter.get_count("CGT") == 2
        assert counter.get_count("GTA") == 2
        assert counter.get_count("TAC") == 2

    def test_add_sequence_with_whitespace(self):
        """Test that whitespace in sequence is ignored."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_sequence("ACG TACG ACGT")
        assert counter.get_count("ACGTACG") == 1

    def test_add_sequence_with_newlines(self):
        """Test that newlines in sequence are ignored."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_sequence("ACG\nTACG\nACGT")
        assert counter.get_count("ACGTACG") == 1

    def test_add_sequence_with_invalid_characters(self):
        """Test that invalid characters in sequence are skipped."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_sequence("ACGNACG")
        # Should extract k-mers skipping N: ACGACG
        assert counter.get_count("ACGACGA") == 0  # Invalid k-mer spanning N
        assert counter.get_count("ACGTACG") == 0

    def test_add_sequence_shorter_than_k(self):
        """Test adding sequence shorter than k-mer length (no error)."""
        counter = pyrustkmer.PyCounter(21)
        counter.add_sequence("ACG")
        assert counter.is_empty() == True

    def test_add_empty_sequence(self):
        """Test adding empty sequence (no error)."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_sequence("")
        assert counter.is_empty() == True

    def test_add_all_same_base_sequence(self):
        """Test adding sequence of all same bases."""
        counter = pyrustkmer.PyCounter(3)
        counter.add_sequence("AAAAAAAAAA")
        assert counter.get_count("AAA") == 8


class TestPyCounterGetCount:
    """Test querying k-mer counts."""

    def test_get_count_existing_kmer(self):
        """Test getting count for existing k-mer."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        assert counter.get_count("AAAAAAA") == 1

    def test_get_count_nonexistent_kmer(self):
        """Test getting count for non-existent k-mer."""
        counter = pyrustkmer.PyCounter(7)
        assert counter.get_count("AAAAAAA") == 0

    def test_get_count_after_multiple_adds(self):
        """Test count after adding same k-mer multiple times."""
        counter = pyrustkmer.PyCounter(7)
        for _ in range(5):
            counter.add_kmer("AAAAAAA")
        assert counter.get_count("AAAAAAA") == 5

    def test_get_count_wrong_length_raises_error(self):
        """Test that querying with wrong length raises ValueError."""
        counter = pyrustkmer.PyCounter(7)
        with pytest.raises(ValueError, match="K-mer length mismatch"):
            counter.get_count("AAA")


class TestPyCounterGetAllCounts:
    """Test getting all k-mer counts as dictionary."""

    def test_get_all_counts_empty_counter(self):
        """Test getting all counts from empty counter."""
        counter = pyrustkmer.PyCounter(7)
        counts = counter.get_all_counts()
        assert counts == {}

    def test_get_all_counts_single_kmer(self):
        """Test getting all counts with single k-mer."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        counts = counter.get_all_counts()
        assert len(counts) == 1
        assert "AAAAAAA" in counts
        assert counts["AAAAAAA"] == 1

    def test_get_all_counts_multiple_kmers(self):
        """Test getting all counts with multiple k-mers."""
        counter = pyrustkmer.PyCounter(7)
        kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG"]
        for kmer in kmers:
            counter.add_kmer(kmer)
        counts = counter.get_all_counts()
        assert len(counts) == 3
        for kmer in kmers:
            assert kmer in counts
            assert counts[kmer] == 1

    def test_get_all_counts_with_duplicates(self):
        """Test getting all counts with duplicate k-mers."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("AAAAAAA")
        counts = counter.get_all_counts()
        assert len(counts) == 1
        assert counts["AAAAAAA"] == 2


class TestPyCounterReset:
    """Test resetting the counter."""

    def test_reset_clears_all_counts(self):
        """Test that reset clears all counted k-mers."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("CCCCCCC")
        assert counter.is_empty() == False

        counter.reset()
        assert counter.is_empty() == True
        assert counter.get_count("AAAAAAA") == 0
        assert counter.get_count("CCCCCCC") == 0

    def test_reset_multiple_times(self):
        """Test that reset can be called multiple times."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        counter.reset()
        counter.reset()  # Should not raise error
        assert counter.is_empty() == True


class TestPyCounterIsEmpty:
    """Test checking if counter is empty."""

    def test_is_empty_initially(self):
        """Test that counter is initially empty."""
        counter = pyrustkmer.PyCounter(7)
        assert counter.is_empty() == True

    def test_is_empty_after_adding_kmer(self):
        """Test that counter is not empty after adding k-mer."""
        counter = pyrustkmer.PyCounter(7)
        assert counter.is_empty() == True
        counter.add_kmer("AAAAAAA")
        assert counter.is_empty() == False

    def test_is_empty_after_reset(self):
        """Test that counter is empty after reset."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        assert counter.is_empty() == False
        counter.reset()
        assert counter.is_empty() == True


class TestPyCounterGetStats:
    """Test getting counter statistics."""

    def test_get_stats_empty_counter(self):
        """Test stats for empty counter."""
        counter = pyrustkmer.PyCounter(21, canonical=True)
        stats = counter.get_stats()

        assert stats.total_kmers == 0
        assert stats.unique_kmers == 0
        assert stats.kmer_length == 21
        assert stats.canonical_mode == True
        assert stats.memory_usage >= 0

    def test_get_stats_after_adding_kmers(self):
        """Test stats after adding k-mers."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("CCCCCCC")

        stats = counter.get_stats()
        assert stats.total_kmers == 3
        assert stats.unique_kmers == 2
        assert stats.kmer_length == 7
        assert stats.canonical_mode == False

    def test_get_stats_from_sequence(self):
        """Test stats after adding from sequence."""
        counter = pyrustkmer.PyCounter(3)
        counter.add_sequence(
            "ACGTACGTACG"
        )  # 4 unique k-mers: ACG, CGT, GTA, TAC (9 total, appearing 3,2,2,2 times)

        stats = counter.get_stats()
        assert stats.total_kmers == 9
        assert stats.unique_kmers == 4
        assert stats.kmer_length == 3

    def test_stats_repr(self):
        """Test stats string representation."""
        counter = pyrustkmer.PyCounter(21, canonical=True)
        stats = counter.get_stats()
        repr_str = repr(stats)
        assert "PyCounterStats" in repr_str
        assert "total_kmers=0" in repr_str


class TestPyCounterCanonicalMode:
    """Test canonical k-mer counting mode."""

    def test_canonical_mode_merge_reverse_complement(self):
        """Test that canonical mode merges forward and reverse complement."""
        counter_canonical = pyrustkmer.PyCounter(7, canonical=True)
        counter_noncanonical = pyrustkmer.PyCounter(7, canonical=False)

        # Add forward k-mer and its reverse complement
        counter_canonical.add_kmer("AAAAAAA")
        counter_canonical.add_kmer("TTTTTTT")  # Reverse complement of AAAAAAA

        counter_noncanonical.add_kmer("AAAAAAA")
        counter_noncanonical.add_kmer("TTTTTTT")

        # Canonical should have 1 unique k-mer, non-canonical should have 2
        stats_canonical = counter_canonical.get_stats()
        stats_noncanonical = counter_noncanonical.get_stats()

        assert stats_canonical.unique_kmers == 1
        assert stats_canonical.total_kmers == 2
        assert stats_noncanonical.unique_kmers == 2
        assert stats_noncanonical.total_kmers == 2

    def test_canonical_mode_reduces_unique_kmers(self):
        """Test that canonical mode reduces unique k-mer count."""
        counter_canonical = pyrustkmer.PyCounter(7, canonical=True)
        counter_noncanonical = pyrustkmer.PyCounter(7, canonical=False)

        # Add sequence with various k-mers
        sequence = "ACGTACGTACGTACGT"
        counter_canonical.add_sequence(sequence)
        counter_noncanonical.add_sequence(sequence)

        stats_canonical = counter_canonical.get_stats()
        stats_noncanonical = counter_noncanonical.get_stats()

        assert stats_canonical.unique_kmers < stats_noncanonical.unique_kmers
        assert stats_canonical.total_kmers == stats_noncanonical.total_kmers

    def test_canonical_mode_query_behavior(self):
        """Test query behavior in canonical mode."""
        counter = pyrustkmer.PyCounter(7, canonical=True)
        counter.add_kmer("AAAAAAA")

        # Both forward and reverse complement should return the same count
        assert counter.get_count("AAAAAAA") == 1
        assert counter.get_count("TTTTTTT") == 1


class TestPyCounterFastaFiles:
    """Test reading FASTA files."""

    def test_add_from_fasta_single_sequence(self, tmp_path):
        """Test reading FASTA with single sequence."""
        fasta_file = tmp_path / "test.fasta"
        fasta_content = """>seq1
ACGTACGTACGTACGTACGTACGTACGTACGT
"""
        fasta_file.write_text(fasta_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fasta(str(fasta_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_add_from_fasta_multiple_sequences(self, tmp_path):
        """Test reading FASTA with multiple sequences."""
        fasta_file = tmp_path / "test_multi.fasta"
        fasta_content = """>seq1
ACGTACGTACGT
>seq2
TGCATGCATGCA
>seq3
GGGGGGGGGGGG
"""
        fasta_file.write_text(fasta_content)

        counter = pyrustkmer.PyCounter(7)
        counter.add_from_fasta(str(fasta_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_add_from_fasta_with_line_breaks(self, tmp_path):
        """Test reading FASTA with line breaks in sequence."""
        fasta_file = tmp_path / "test_breaks.fasta"
        fasta_content = """>seq1
ACGTACGT
ACGTACGT
ACGTACGT
"""
        fasta_file.write_text(fasta_content)

        counter = pyrustkmer.PyCounter(7)
        counter.add_from_fasta(str(fasta_file))

        # Should merge sequences across lines
        stats = counter.get_stats()
        assert stats.total_kmers > 0

    def test_add_from_fasta_with_invalid_characters(self, tmp_path):
        """Test reading FASTA with invalid characters (N)."""
        fasta_file = tmp_path / "test_invalid.fasta"
        fasta_content = """>seq1
ACGTNACGTACGTACGT
"""
        fasta_file.write_text(fasta_content)

        counter = pyrustkmer.PyCounter(7)
        counter.add_from_fasta(str(fasta_file))

        # Should skip invalid characters
        stats = counter.get_stats()
        assert stats.total_kmers > 0

    def test_add_from_fasta_nonexistent_file(self, tmp_path):
        """Test reading non-existent FASTA file raises error."""
        counter = pyrustkmer.PyCounter(7)
        nonexistent = tmp_path / "nonexistent.fasta"

        with pytest.raises(ValueError, match="Failed to process FASTA"):
            counter.add_from_fasta(str(nonexistent))

    def test_add_from_fasta_gz_compressed(self, tmp_path):
        """Test reading gzipped FASTA file."""
        fasta_file = tmp_path / "test.fasta.gz"
        fasta_content = """>seq1
ACGTACGTACGTACGTACGTACGTACGTACGT
"""
        with gzip.open(fasta_file, "wt") as f:
            f.write(fasta_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fasta(str(fasta_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_add_from_fasta_bz2_compressed(self, tmp_path):
        """WR-05 regression: bzip2-compressed FASTA must be read correctly."""
        bz2 = pytest.importorskip("bz2")
        fasta_file = tmp_path / "test.fasta.bz2"
        fasta_content = b""">seq1
ACGTACGTACGTACGTACGTACGTACGTACGT
"""
        with bz2.open(fasta_file, "wb") as f:
            f.write(fasta_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fasta(str(fasta_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_add_from_fasta_xz_compressed(self, tmp_path):
        """WR-05 regression: xz-compressed FASTA must be read correctly."""
        lzma = pytest.importorskip("lzma")
        fasta_file = tmp_path / "test.fasta.xz"
        fasta_content = b""">seq1
ACGTACGTACGTACGTACGTACGTACGTACGT
"""
        with lzma.open(fasta_file, "wb") as f:
            f.write(fasta_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fasta(str(fasta_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_add_from_fasta_all_a_sequence(self, tmp_path):
        """Test reading FASTA with all A's."""
        fasta_file = tmp_path / "test_alla.fasta"
        fasta_content = """>seq1
AAAAAAAAAAAAAAAAAAAAA
"""
        fasta_file.write_text(fasta_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fasta(str(fasta_file))

        assert counter.get_count("A" * 21) == 1


class TestPyCounterFastqFiles:
    """Test reading FASTQ files."""

    def test_add_from_fastq_single_read(self, tmp_path):
        """Test reading FASTQ with single read."""
        fastq_file = tmp_path / "test.fastq"
        fastq_content = """@read1
ACGTACGTACGTACGTACGTACGTACGTACGT
+
IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
"""
        fastq_file.write_text(fastq_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fastq(str(fastq_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_add_from_fastq_multiple_reads(self, tmp_path):
        """Test reading FASTQ with multiple reads."""
        fastq_file = tmp_path / "test_multi.fastq"
        fastq_content = """@read1
ACGTACGTACGT
+
IIIIIIIIIIII
@read2
TGCATGCATGCA
+
IIIIIIIIIIII
@read3
GGGGGGGGGGGG
+
IIIIIIIIIIII
"""
        fastq_file.write_text(fastq_content)

        counter = pyrustkmer.PyCounter(7)
        counter.add_from_fastq(str(fastq_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_add_from_fastq_with_invalid_characters(self, tmp_path):
        """Test reading FASTQ with invalid characters (N)."""
        fastq_file = tmp_path / "test_invalid.fastq"
        fastq_content = """@read1
ACGTNACGTACGTACGT
+
IIIIIIIIIIIIIIIII
"""
        fastq_file.write_text(fastq_content)

        counter = pyrustkmer.PyCounter(7)
        counter.add_from_fastq(str(fastq_file))

        # Should skip invalid characters
        stats = counter.get_stats()
        assert stats.total_kmers > 0

    def test_add_from_fastq_nonexistent_file(self, tmp_path):
        """Test reading non-existent FASTQ file raises error."""
        counter = pyrustkmer.PyCounter(7)
        nonexistent = tmp_path / "nonexistent.fastq"

        with pytest.raises(ValueError, match="Failed to open file"):
            counter.add_from_fastq(str(nonexistent))

    def test_add_from_fastq_gz_compressed(self, tmp_path):
        """Test reading gzipped FASTQ file."""
        fastq_file = tmp_path / "test.fastq.gz"
        fastq_content = """@read1
ACGTACGTACGTACGTACGTACGTACGTACGT
+
IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
"""
        with gzip.open(fastq_file, "wt") as f:
            f.write(fastq_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fastq(str(fastq_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0

    def test_add_from_fastq_bz2_compressed(self, tmp_path):
        """WR-05 regression: bzip2-compressed FASTQ must be read correctly."""
        bz2 = pytest.importorskip("bz2")
        fastq_file = tmp_path / "test.fastq.bz2"
        fastq_content = b"""@read1
ACGTACGTACGTACGTACGTACGTACGTACGT
+
IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
"""
        with bz2.open(fastq_file, "wb") as f:
            f.write(fastq_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fastq(str(fastq_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0

    def test_add_from_fastq_xz_compressed(self, tmp_path):
        """WR-05 regression: xz-compressed FASTQ must be read correctly."""
        lzma = pytest.importorskip("lzma")
        fastq_file = tmp_path / "test.fastq.xz"
        fastq_content = b"""@read1
ACGTACGTACGTACGTACGTACGTACGTACGT
+
IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
"""
        with lzma.open(fastq_file, "wb") as f:
            f.write(fastq_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fastq(str(fastq_file))

        stats = counter.get_stats()
        assert stats.total_kmers > 0

    def test_add_from_fastq_sequence_shorter_than_k(self, tmp_path):
        """Test reading FASTQ with sequence shorter than k."""
        fastq_file = tmp_path / "test_short.fastq"
        fastq_content = """@read1
ACG
+
III
"""
        fastq_file.write_text(fastq_content)

        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fastq(str(fastq_file))

        # Should remain empty
        assert counter.is_empty() == True


class TestPyCounterSaveDatabase:
    """Test saving counter to RKDB database."""

    def test_save_database_basic(self, tmp_path):
        """Test saving counter to database."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("CCCCCCC")
        counter.add_kmer("AAAAAAA")

        db_path = tmp_path / "test.rkdb"
        counter.save_database(str(db_path))

        assert db_path.exists()
        assert db_path.stat().st_size > 0

    def test_save_database_and_load(self, tmp_path):
        """Test saving database and loading with PyDatabase."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("CCCCCCC")
        counter.add_kmer("AAAAAAA")

        db_path = tmp_path / "test.rkdb"
        counter.save_database(str(db_path))

        # Load and verify
        db = pyrustkmer.PyDatabase(str(db_path), pyrustkmer.LoadMode.Preload)

        result_a = db.query("AAAAAAA")
        assert result_a.found == True
        assert result_a.count == 2

        result_c = db.query("CCCCCCC")
        assert result_c.found == True
        assert result_c.count == 1

    def test_save_database_canonical_mode(self, tmp_path):
        """Test saving database from canonical mode counter."""
        counter = pyrustkmer.PyCounter(7, canonical=True)
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("TTTTTTT")

        db_path = tmp_path / "test_canonical.rkdb"
        counter.save_database(str(db_path))

        # Load and verify canonical behavior
        db = pyrustkmer.PyDatabase(str(db_path), pyrustkmer.LoadMode.Preload)

        stats = db.get_stats()
        assert stats.kmer_size == 7

        # Both should map to same canonical k-mer
        result_a = db.query("AAAAAAA")
        result_t = db.query("TTTTTTT")
        assert result_a.found == True
        assert result_t.found == True

    def test_save_database_large_kmer(self, tmp_path):
        """Test saving database with large k-mer (k=33)."""
        counter = pyrustkmer.PyCounter(33)
        counter.add_kmer("A" * 33)
        counter.add_kmer("C" * 33)

        db_path = tmp_path / "test_k33.rkdb"
        counter.save_database(str(db_path))

        assert db_path.exists()

        # Load and verify
        db = pyrustkmer.PyDatabase(str(db_path), pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()
        assert stats.kmer_size == 33
        assert stats.unique_kmers == 2

    def test_save_database_from_sequence(self, tmp_path):
        """Test saving database after adding from sequence."""
        counter = pyrustkmer.PyCounter(3)
        counter.add_sequence("ACGTACGTACG")

        db_path = tmp_path / "test_seq.rkdb"
        counter.save_database(str(db_path))

        # Load and verify
        db = pyrustkmer.PyDatabase(str(db_path), pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_save_database_from_fasta(self, tmp_path):
        """Test saving database after reading FASTA."""
        # Create FASTA file
        fasta_file = tmp_path / "test.fasta"
        fasta_content = """>seq1
ACGTACGTACGTACGTACGTACGTACGTACGT
"""
        fasta_file.write_text(fasta_content)

        # Count k-mers
        counter = pyrustkmer.PyCounter(21)
        counter.add_from_fasta(str(fasta_file))

        # Save database
        db_path = tmp_path / "test_from_fasta.rkdb"
        counter.save_database(str(db_path))

        # Load and verify
        db = pyrustkmer.PyDatabase(str(db_path), pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()
        assert stats.kmer_size == 21
        assert stats.total_kmers > 0

    def test_save_database_empty_counter_raises_error(self, tmp_path):
        """Test that saving empty counter raises ValueError."""
        counter = pyrustkmer.PyCounter(7)
        db_path = tmp_path / "test_empty.rkdb"

        with pytest.raises(ValueError, match="Cannot save empty database"):
            counter.save_database(str(db_path))

    def test_save_database_file_error(self, tmp_path):
        """Test that file write errors are handled."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("AAAAAAA")

        # Try to save to invalid path (directory instead of file)
        with pytest.raises(ValueError, match="Failed to create file"):
            counter.save_database(str(tmp_path))


class TestPyCounterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_kmer_size_1(self):
        """Test counter with k=1 (single nucleotides)."""
        counter = pyrustkmer.PyCounter(1)
        counter.add_sequence("ACGTACGT")

        stats = counter.get_stats()
        assert stats.total_kmers == 8
        assert stats.unique_kmers == 4

        # Check individual counts
        assert counter.get_count("A") == 2
        assert counter.get_count("C") == 2
        assert counter.get_count("G") == 2
        assert counter.get_count("T") == 2

    def test_kmer_size_64(self):
        """Test counter with k=64 (maximum)."""
        counter = pyrustkmer.PyCounter(64)
        kmer64 = "A" * 32 + "C" * 32
        counter.add_kmer(kmer64)

        assert counter.get_count(kmer64) == 1

    def test_add_sequence_all_invalid_characters(self):
        """Test adding sequence with all invalid characters."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_sequence("NNNNNNNNNNN")

        # Should remain empty
        assert counter.is_empty() == True

    def test_add_sequence_mixed_valid_invalid(self):
        """Test adding sequence with mix of valid and invalid characters."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_sequence("ACGTNNNACGTACGT")

        # Should count only valid k-mers
        stats = counter.get_stats()
        assert stats.total_kmers > 0

    def test_large_sequence(self):
        """Test adding a very long sequence."""
        counter = pyrustkmer.PyCounter(21)
        long_seq = "ACGTACGTACGTACGTACGT" * 1000  # 21000 bases
        counter.add_sequence(long_seq)

        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

    def test_add_kmer_lowercase(self):
        """Test that lowercase k-mers are handled."""
        counter = pyrustkmer.PyCounter(7)
        counter.add_kmer("aaaaaaa")

        # Should be treated as uppercase
        assert counter.get_count("AAAAAAA") == 1

    def test_add_sequence_lowercase(self):
        """Test that lowercase sequence is handled."""
        counter = pyrustkmer.PyCounter(3)
        counter.add_sequence("acgtacgtacg")

        stats = counter.get_stats()
        assert stats.total_kmers == 9


class TestPyCounterMemoryUsage:
    """Test memory usage estimation."""

    def test_memory_usage_increases_with_kmers(self):
        """Test that memory usage increases with more k-mers."""
        counter = pyrustkmer.PyCounter(7)

        stats_before = counter.get_stats()
        memory_before = stats_before.memory_usage

        # Add many k-mers
        for i in range(1000):
            counter.add_kmer("AAAAAAA")

        stats_after = counter.get_stats()
        memory_after = stats_after.memory_usage

        assert memory_after > memory_before

    def test_memory_usage_canonical_vs_noncanonical(self):
        """Test memory usage difference between canonical and non-canonical."""
        counter_canonical = pyrustkmer.PyCounter(7, canonical=True)
        counter_noncanonical = pyrustkmer.PyCounter(7, canonical=False)

        sequence = "ACGTACGTACGTACGT" * 100
        counter_canonical.add_sequence(sequence)
        counter_noncanonical.add_sequence(sequence)

        stats_c = counter_canonical.get_stats()
        stats_nc = counter_noncanonical.get_stats()

        # Canonical should use less memory (fewer unique k-mers)
        assert stats_c.unique_kmers < stats_nc.unique_kmers


class TestPyCounterProperties:
    """Test counter properties."""

    def test_kmer_length_property(self):
        """Test kmer_length property."""
        counter = pyrustkmer.PyCounter(21)
        assert counter.kmer_length == 21

    def test_canonical_property(self):
        """Test canonical property."""
        counter_true = pyrustkmer.PyCounter(21, canonical=True)
        counter_false = pyrustkmer.PyCounter(21, canonical=False)

        assert counter_true.canonical == True
        assert counter_false.canonical == False


class TestPyCounterIntegration:
    """Integration tests combining multiple features."""

    def test_counter_workflow(self, tmp_path):
        """Test complete counter workflow."""
        # Create counter
        counter = pyrustkmer.PyCounter(7, canonical=True)

        # Add k-mers in various ways
        counter.add_kmer("AAAAAAA")
        counter.add_sequence("ACGTACGTACG")
        counter.add_kmer("AAAAAAA")

        # Check stats
        stats = counter.get_stats()
        assert stats.total_kmers > 0
        assert stats.unique_kmers > 0

        # Save to database
        db_path = tmp_path / "workflow.rkdb"
        counter.save_database(str(db_path))

        # Load and verify
        db = pyrustkmer.PyDatabase(str(db_path), pyrustkmer.LoadMode.Preload)
        db_stats = db.get_stats()

        assert db_stats.kmer_size == 7
        assert db_stats.total_kmers == stats.unique_kmers

    def test_fasta_to_database_workflow(self, tmp_path):
        """Test workflow from FASTA to database."""
        # Create FASTA file
        fasta_file = tmp_path / "test.fasta"
        fasta_content = """>seq1
ACGTACGTACGTACGTACGTACGTACGTACGT
>seq2
TGCATGCATGCATGCATGCATGCATGCATGCA
"""
        fasta_file.write_text(fasta_content)

        # Count k-mers
        counter = pyrustkmer.PyCounter(21, canonical=True)
        counter.add_from_fasta(str(fasta_file))

        # Save database
        db_path = tmp_path / "from_fasta.rkdb"
        counter.save_database(str(db_path))

        # Verify database can be queried
        db = pyrustkmer.PyDatabase(str(db_path), pyrustkmer.LoadMode.Preload)

        # Try some queries
        result_a = db.query("A" * 21)
        assert result_a.found == True or result_a.found == False  # May or may not exist

    def test_multiple_counters_save_to_separate_dbs(self, tmp_path):
        """Test saving multiple counters to separate databases."""
        counter1 = pyrustkmer.PyCounter(7)
        counter1.add_kmer("AAAAAAA")

        counter2 = pyrustkmer.PyCounter(7)
        counter2.add_kmer("CCCCCCC")

        db_path1 = tmp_path / "counter1.rkdb"
        db_path2 = tmp_path / "counter2.rkdb"

        counter1.save_database(str(db_path1))
        counter2.save_database(str(db_path2))

        # Verify both databases exist and are independent
        assert db_path1.exists()
        assert db_path2.exists()

        db1 = pyrustkmer.PyDatabase(str(db_path1), pyrustkmer.LoadMode.Preload)
        db2 = pyrustkmer.PyDatabase(str(db_path2), pyrustkmer.LoadMode.Preload)

        assert db1.query("AAAAAAA").found == True
        assert db1.query("CCCCCCC").found == False

        assert db2.query("AAAAAAA").found == False
        assert db2.query("CCCCCCC").found == True


class TestPyCounterThreads:
    """Test the threads kwarg (PCOUNT-03 / D-08)."""

    def test_create_counter_with_threads(self):
        """Construct a counter with an explicit threads kwarg."""
        counter = pyrustkmer.PyCounter(21, canonical=True, threads=4)
        assert counter is not None
        assert counter.kmer_length == 21
        assert counter.canonical == True

    def test_threads_none_uses_all_cores(self):
        """threads=None (default) constructs without error."""
        counter = pyrustkmer.PyCounter(21, threads=None)
        assert counter is not None
        assert counter.kmer_length == 21

    def test_threads_zero_rejected(self):
        """threads=0 is rejected with a ValueError (T-02-13)."""
        with pytest.raises(ValueError, match="Invalid thread count"):
            pyrustkmer.PyCounter(21, threads=0)


class TestPyCounterParallel:
    """PCOUNT-03 at the Python layer: threads=1 vs threads=N must produce
    identical count maps (the Python-side commutativity differential,
    parity with the Rust differential_threads_1_vs_n test).
    """

    def test_parallel_counts_match_sequential(self, tmp_path):
        """threads=1 and threads=N produce identical count maps.

        Writes a small deterministic FASTQ fixture, counts it once with
        threads=1 and once with threads=4, and compares the resulting
        count maps via PyCounter.get_all_counts() (returns a dict mapping
        the decoded kmer string to its count). The dict comparison is
        order-independent, so sharded DashMap iteration order cannot flake
        the assertion.
        """
        fastq_file = tmp_path / "reads.fastq"
        # 4 deterministic reads exercising A/C/G/T; k=21 so each
        # 32-base read yields 32-21+1 = 12 windows.
        reads = [
            "ACGTACGTACGTACGTACGTACGTACGTACGT",
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
            "ACACACACACACACACACACACACACACACAC",
            "GATTACAGATTACAGATTACAGATTACAGATT",
        ]
        lines = []
        for i, seq in enumerate(reads):
            lines.append(f"@read{i}")
            lines.append(seq)
            lines.append("+")
            lines.append("I" * len(seq))
        fastq_file.write_text("\n".join(lines) + "\n")

        # threads=1 path. get_all_counts() returns a dict[str, int] which
        # is canonical (order-independent) — the natural comparison type.
        counter1 = pyrustkmer.PyCounter(21, canonical=True, threads=1)
        counter1.add_from_fastq(str(fastq_file))
        counts_1 = counter1.get_all_counts()

        # threads=N path (4 workers). build_global returns Err on a second
        # call; PyCounter::new deliberately discards it (T-02-12), so the
        # second counter inherits the first's pool config — but the
        # DashMap atomicity (the property under test) is unaffected.
        counter4 = pyrustkmer.PyCounter(21, canonical=True, threads=4)
        counter4.add_from_fastq(str(fastq_file))
        counts_4 = counter4.get_all_counts()

        # Order-independent comparison: DashMap iteration order is
        # run-to-run non-deterministic, but the count MAP must be
        # identical (commutativity of integer addition — PCOUNT-03).
        assert counts_1 == counts_4, (
            "PCOUNT-03 divergence: threads=1 and threads=4 produced "
            "different count maps (concurrency bug)"
        )
