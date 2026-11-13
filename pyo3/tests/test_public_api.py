"""Freeze the public ``PyCounter`` surface and constructor keyword contract.

The Phase 9 Python parity work must not add, remove, or rename any public
``PyCounter`` member: the surface is exactly the twelve documented names, and
the constructor keeps the documented keyword-only contract.
"""

import pytest

try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)

PUBLIC_PYCOUNTER_NAMES = {
    "add_from_fasta",
    "add_from_fastq",
    "add_kmer",
    "add_sequence",
    "canonical",
    "get_all_counts",
    "get_count",
    "get_stats",
    "is_empty",
    "kmer_length",
    "reset",
    "save_database",
}


def test_public_pycounter_surface_is_exactly_the_frozen_twelve():
    """Compare by equality so both an added and a removed name fail."""
    observed = {
        name for name in dir(pyrustkmer.PyCounter) if not name.startswith("_")
    }
    assert observed == PUBLIC_PYCOUNTER_NAMES, (
        "PyCounter public surface changed: added=%r removed=%r"
        % (
            sorted(observed - PUBLIC_PYCOUNTER_NAMES),
            sorted(PUBLIC_PYCOUNTER_NAMES - observed),
        )
    )


def test_constructor_keyword_contract():
    """``kmer_length`` is the first parameter; the rest stay optional."""
    assert pyrustkmer.PyCounter(kmer_length=21).kmer_length == 21
    assert pyrustkmer.PyCounter(21, canonical=True).canonical is True
    assert pyrustkmer.PyCounter(21, initial_capacity=5000).kmer_length == 21
    assert pyrustkmer.PyCounter(21, threads=1).kmer_length == 21
    with pytest.raises(ValueError, match="Invalid thread count"):
        pyrustkmer.PyCounter(21, threads=0)
