RustKmer Python API Reference
=============================

The RustKmer Python API provides high-performance k-mer counting, querying, and analysis capabilities powered by Rust backend.

.. contents::
   :local:
   :depth: 2

Core Classes
------------

KmerCounter
~~~~~~~~~~~

.. autoclass:: rustkmer.KmerCounter
   :members:
   :special-members: __init__

Example::

    from rustkmer import KmerCounter

    # Create counter with 31-mers using 4 threads
    counter = KmerCounter(k=31, threads=4)

    # Count k-mers from a file
    database = counter.count_from_file("sequences.fasta")

    # Count k-mers from a string
    kmer_counts = counter.count_from_string("ATCGATCGATCGATCG", k=8)

Database
~~~~~~~~

.. autoclass:: rustkmer.Database
   :members:
   :special-members: __init__

Example::

    from rustkmer import Database

    # Load existing database
    db = Database()
    db.load("kmer_database.rkdb")

    # Query k-mers
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCG")
    if result.found:
        print(f"Found {result.count} occurrences")

    # Get database statistics
    stats = db.get_stats()
    print(f"Database contains {stats.total_kmers} k-mers")

QueryResult
~~~~~~~~~~~

.. autoclass:: rustkmer.QueryResult
   :members:
   :special-members: __init__

DatabaseStats
~~~~~~~~~~~~~

.. autoclass:: rustkmer.DatabaseStats
   :members:
   :special-members: __init__

Fuzzy Query Classes
-------------------

FuzzyQueryEngine
~~~~~~~~~~~~~~~~

.. autoclass:: rustkmer.FuzzyQueryEngine
   :members:
   :special-members: __init__

Example::

    from rustkmer import FuzzyQueryEngine, FuzzyQueryConfig

    # Create fuzzy query engine
    config = FuzzyQueryConfig(max_distance=2, max_results=10)
    engine = FuzzyQueryEngine(config)
    engine.attach_database(database)

    # Find similar k-mers
    results = engine.query("ATCGATCG")
    for result in results:
        print(f"{result.match}: distance={result.distance}, count={result.count}")

FuzzyQueryConfig
~~~~~~~~~~~~~~~~

.. autoclass:: rustkmer.FuzzyQueryConfig
   :members:
   :special-members: __init__

FuzzyResult
~~~~~~~~~~~

.. autoclass:: rustkmer.FuzzyResult
   :members:
   :special-members: __init__

Database Export Classes
-----------------------

DatabaseExporter
~~~~~~~~~~~~~~~~

.. autoclass:: rustkmer.DatabaseExporter
   :members:
   :special-members: __init__

Example::

    from rustkmer import DatabaseExporter, ExportConfig, ExportFormat

    # Create exporter
    config = ExportConfig(format=ExportFormat.JSON, sort_by_count=True)
    exporter = DatabaseExporter(config)

    # Export database
    exporter.export(database, "output.json")

    # Export to string
    json_output = exporter.export_to_string(database)

ExportConfig
~~~~~~~~~~~~

.. autoclass:: rustkmer.ExportConfig
   :members:
   :special-members: __init__

FilterConfig
~~~~~~~~~~~~

.. autoclass:: rustkmer.FilterConfig
   :members:
   :special-members: __init__

Database Merge Classes
----------------------

DatabaseMerger
~~~~~~~~~~~~~~

.. autoclass:: rustkmer.DatabaseMerger
   :members:
   :special-members: __init__

Example::

    from rustkmer import DatabaseMerger, MergeConfig

    # Create merger
    config = MergeConfig(threads=4, max_memory_mb=1024)
    merger = DatabaseMerger(config)

    # Merge multiple databases
    databases = [db1, db2, db3]
    result = merger.merge_databases(databases, "merged.rkdb")
    print(f"Merged {result.successful_merges} databases")

MergeConfig
~~~~~~~~~~~

.. autoclass:: rustkmer.MergeConfig
   :members:
   :special-members: __init__

MergeResult
~~~~~~~~~~~

.. autoclass:: rustkmer.MergeResult
   :members:
   :special-members: __init__

Statistics Classes
------------------

StatisticsCalculator
~~~~~~~~~~~~~~~~~~~

.. autoclass:: rustkmer.stats.StatisticsCalculator
   :members:
   :special-members: __init__

Example::

    from rustkmer.stats import StatisticsCalculator

    # Calculate database statistics
    calc = StatisticsCalculator()
    stats = calc.calculate_all_stats(database)

    print(f"Mean k-mer abundance: {stats['frequency'].mean:.2f}")
    print(f"GC content: {stats['composition'].gc_content:.2%}")

KmerDistribution
~~~~~~~~~~~~~~~~

.. autoclass:: rustkmer.stats.KmerDistribution
   :members:
   :special-members: __init__

FrequencyStats
~~~~~~~~~~~~~~

.. autoclass:: rustkmer.stats.FrequencyStats
   :members:
   :special-members: __init__

CompositionStats
~~~~~~~~~~~~~~~~

.. autoclass:: rustkmer.stats.CompositionStats
   :members:
   :special-members: __init__

Utility Classes
---------------

SequenceReader
~~~~~~~~~~~~~~

.. autoclass:: rustkmer.utils.SequenceReader
   :members:
   :special-members: __init__

Example::

    from rustkmer.utils import SequenceReader

    # Read FASTA/FASTQ files
    with SequenceReader("sequences.fasta") as reader:
        for seq_id, sequence in reader:
            print(f"{seq_id}: {len(sequence)} bp")

    # Count sequences
    total_seqs = reader.count_sequences()

SequenceWriter
~~~~~~~~~~~~~~

.. autoclass:: rustkmer.utils.SequenceWriter
   :members:
   :special-members: __init__

Exception Classes
-----------------

All exceptions inherit from :class:`rustkmer.RustKmerError`:

.. autoclass:: rustkmer.RustKmerError
   :members:
   :special-members: __init__

.. autoclass:: rustkmer.DatabaseError
   :members:
   :special-members: __init__

.. autoclass:: rustkmer.QueryError
   :members:
   :special-members: __init__

.. autoclass:: rustkmer.ValidationError
   :members:
   :special-members: __init__

.. autoclass:: rustkmer.MergeError
   :members:
   :special-members: __init__

.. autoclass:: rustkmer.ExportError
   :members:
   :special-members: __init__

.. autoclass:: rustkmer.FuzzyQueryError
   :members:
   :special-members: __init__

.. autoclass:: rustkmer.StatsError
   :members:
   :special-members: __init__

.. autoclass:: rustkmer.UtilsError
   :members:
   :special-members: __init__

Module Functions
----------------

.. autofunction:: rustkmer.utils.validate_sequence

.. autofunction:: rustkmer.utils.reverse_complement

.. autofunction:: rustkmer.utils.kmerize_sequence

.. autofunction:: rustkmer.utils.calculate_kmer_hash

.. autofunction:: rustkmer.utils.detect_compression

.. autofunction:: rustkmer.utils.format_memory_size

.. autofunction:: rustkmer.utils.parse_memory_size