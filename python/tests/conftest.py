"""
Shared fixtures for RustKmer Python tests.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Ensure we're using the project's .venv
def pytest_sessionstart(session):
    """Validate that tests are running in .venv environment."""
    venv_python = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"
    if sys.executable != str(venv_python):
        pytest.skip("Tests must be run in .venv environment", allow_module_level=True)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def temp_fasta_file(temp_dir):
    """Create a temporary FASTA file with test sequences."""
    fasta_path = os.path.join(temp_dir, "test.fa")
    with open(fasta_path, "w") as f:
        f.write(">seq1\n")
        f.write("ATCGATCGATCGATCGATCGATCGATCGATCG\n")
        f.write(">seq2\n")
        f.write("GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n")
    return fasta_path

@pytest.fixture
def temp_fastq_file(temp_dir):
    """Create a temporary FASTQ file with test sequences."""
    fastq_path = os.path.join(temp_dir, "test.fq")
    with open(fastq_path, "w") as f:
        f.write("@seq1\n")
        f.write("ATCGATCGATCGATCGATCGATCGATCGATCG\n")
        f.write("+\n")
        f.write("IIIIIIIIIIIIIIIIIIIIIIIIIIII\n")
        f.write("@seq2\n")
        f.write("GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n")
        f.write("+\n")
        f.write("JJJJJJJJJJJJJJJJJJJJJJJJJJ\n")
    return fastq_path

@pytest.fixture(scope="session")
def rustkmer_import():
    """Test that rustkmer can be imported."""
    import rustkmer
    return rustkmer

@pytest.fixture
def kmer_counter_21(rustkmer_import):
    """Create a KmerCounter with k=21 for testing."""
    return rustkmer_import.KmerCounter(k=21, canonical=True)

@pytest.fixture
def small_test_db(temp_dir, kmer_counter_21):
    """Create a small test database."""
    db_path = os.path.join(temp_dir, "test.rkdb")
    # Count sequences and save to database
    kmer_counter_21.count_string("ATCGATCGATCGATCGATCGATCGATCGATCG")
    kmer_counter_21.save_to_database(db_path)
    return db_path