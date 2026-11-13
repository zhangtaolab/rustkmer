"""Concurrent ``PyCounter.add_from_*`` calls: bounded waits, exact counts.

Each call owns a per-call ``CountEngine`` and merges through the shared
counter's documented concurrent-safe ``merge_local_counts`` path. If a
regression ever deadlocks, the bounded ``future.result(timeout=...)`` calls
fail the suite instead of hanging it.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)

K = 21
TIMEOUT_SECONDS = 120

# Deterministic, ACGT-only reads; each is longer than k so it yields windows.
READS = [
    "ACGT" * 10,
    "TTTT" * 10,
    "GATTACA" * 6,
    "AAAACCCCGGGGTTTT" * 3,
]


def _revcomp(sequence):
    """Return the reverse complement of a pure-ACGT sequence."""
    return sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def _reference_counts(sequence):
    """Pure-Python canonical skip-N reference count map for one read."""
    counts = {}
    for start in range(len(sequence) - K + 1):
        kmer = sequence[start : start + K]
        if any(base not in "ACGT" for base in kmer):
            continue
        counts[min(kmer, _revcomp(kmer))] = (
            counts.get(min(kmer, _revcomp(kmer)), 0) + 1
        )
    return counts


def _sum_counts(maps):
    """Sum several count maps key by key."""
    total = {}
    for counts in maps:
        for kmer, count in counts.items():
            total[kmer] = total.get(kmer, 0) + count
    return total


def _write_fastq(path, sequences):
    """Write four-line FASTQ records for the given sequences."""
    lines = []
    for index, sequence in enumerate(sequences):
        lines.extend([f"@read{index}", sequence, "+", "I" * len(sequence)])
    path.write_text("\n".join(lines) + "\n")


class TestConcurrentCountFile:
    """Several Python threads counting distinct files concurrently."""

    def test_shared_counter_counts_exactly(self, tmp_path):
        """One shared counter must end with the exact summed reference map."""
        files = []
        references = []
        for index, sequence in enumerate(READS):
            path = tmp_path / f"read{index}.fastq"
            _write_fastq(path, [sequence])
            files.append(path)
            references.append(_reference_counts(sequence))

        counter = pyrustkmer.PyCounter(K, canonical=True, threads=1)
        barrier = threading.Barrier(len(files))

        def worker(path):
            """Wait for all workers, then count one file on the shared counter."""
            barrier.wait(timeout=TIMEOUT_SECONDS)
            counter.add_from_fastq(str(path))

        with ThreadPoolExecutor(max_workers=len(files)) as pool:
            futures = [pool.submit(worker, path) for path in files]
            for future in futures:
                future.result(timeout=TIMEOUT_SECONDS)

        expected = _sum_counts(references)
        assert counter.get_all_counts() == expected, (
            "concurrent add_from_fastq calls on one shared counter diverged "
            "from the exact per-file reference sum"
        )
        assert counter.get_stats().total_kmers == sum(expected.values())

    def test_per_thread_counters_merge_to_same_reference(self, tmp_path):
        """Per-thread counters, merged by accumulation, match the reference."""
        files = []
        references = []
        for index, sequence in enumerate(READS):
            path = tmp_path / f"own{index}.fastq"
            _write_fastq(path, [sequence])
            files.append(path)
            references.append(_reference_counts(sequence))

        barrier = threading.Barrier(len(files))

        def worker(path):
            """Count one file on a counter owned by this thread."""
            barrier.wait(timeout=TIMEOUT_SECONDS)
            own = pyrustkmer.PyCounter(K, canonical=True, threads=1)
            own.add_from_fastq(str(path))
            return own.get_all_counts()

        with ThreadPoolExecutor(max_workers=len(files)) as pool:
            futures = [pool.submit(worker, path) for path in files]
            maps = [future.result(timeout=TIMEOUT_SECONDS) for future in futures]

        expected = _sum_counts(references)
        assert _sum_counts(maps) == expected, (
            "per-thread counters merged by accumulation diverged from the "
            "exact per-file reference sum"
        )


class TestCounterAccumulation:
    """Adjacency and empty-input exactness across successive calls."""

    def test_same_file_twice_doubles_every_count(self, tmp_path):
        """Counting the same file twice yields exactly twice every count."""
        path = tmp_path / "twice.fastq"
        _write_fastq(path, READS)
        expected = _sum_counts([_reference_counts(sequence) for sequence in READS])

        counter = pyrustkmer.PyCounter(K, canonical=True, threads=1)
        counter.add_from_fastq(str(path))
        counter.add_from_fastq(str(path))

        doubled = {kmer: 2 * count for kmer, count in expected.items()}
        assert counter.get_all_counts() == doubled
        assert counter.get_stats().total_kmers == 2 * sum(expected.values())

    def test_disjoint_files_equal_byte_concatenation(self, tmp_path):
        """Two sequential calls equal one call on the concatenated file."""
        first = tmp_path / "first.fastq"
        second = tmp_path / "second.fastq"
        _write_fastq(first, READS[:2])
        _write_fastq(second, READS[2:])
        concatenated = tmp_path / "concatenated.fastq"
        concatenated.write_bytes(first.read_bytes() + second.read_bytes())

        sequential = pyrustkmer.PyCounter(K, canonical=True, threads=1)
        sequential.add_from_fastq(str(first))
        sequential.add_from_fastq(str(second))

        one_call = pyrustkmer.PyCounter(K, canonical=True, threads=1)
        one_call.add_from_fastq(str(concatenated))

        assert sequential.get_all_counts() == one_call.get_all_counts()
        assert (
            sequential.get_stats().total_kmers
            == one_call.get_stats().total_kmers
        )

        expected = _sum_counts(
            [_reference_counts(sequence) for sequence in READS]
        )
        assert sequential.get_all_counts() == expected

    def test_record_less_file_adds_zero_kmers(self, tmp_path):
        """A zero-byte FASTQ is valid input: zero k-mers, no exception."""
        empty = tmp_path / "empty.fastq"
        empty.write_bytes(b"")

        counter = pyrustkmer.PyCounter(K, canonical=True, threads=1)
        counter.add_from_fastq(str(empty))

        assert counter.is_empty() is True
        assert counter.get_stats().total_kmers == 0
