Tutorials and Examples
=======================

This section provides step-by-step tutorials and examples for using the RustKmer Python API.

.. contents::
   :local:
   :depth: 2

Getting Started
---------------

Installation
~~~~~~~~~~~~

First, ensure you have Rust installed, then build and install the Python bindings:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/your-org/rustkmer.git
   cd rustkmer

   # Build the Python bindings
   cd python
   maturin develop --release

Basic Usage
~~~~~~~~~~~

Here's a simple example of counting k-mers in a DNA sequence:

.. code-block:: python

   from rustkmer import KmerCounter

   # Create a counter for 31-mers
   counter = KmerCounter(k=31)

   # Count k-mers in a DNA string
   sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"
   kmer_counts = counter.count_from_string(sequence)

   print(f"Found {len(kmer_counts)} unique k-mers")

Tutorial 1: K-mer Counting and Analysis
----------------------------------------

This tutorial demonstrates how to count k-mers from a FASTA file and analyze the results.

.. code-block:: python

   from rustkmer import KmerCounter, Database
   from rustkmer.stats import StatisticsCalculator
   import matplotlib.pyplot as plt

   # Step 1: Count k-mers from a FASTA file
   counter = KmerCounter(k=21, threads=4)
   database = counter.count_from_file("genome.fasta")

   # Step 2: Get basic statistics
   stats = database.get_stats()
   print(f"K-mer size: {stats.kmer_size}")
   print(f"Total k-mers: {stats.total_kmers:,}")
   print(f"Unique k-mers: {stats.cardinality:,}")

   # Step 3: Calculate detailed statistics
   calc = StatisticsCalculator()
   detailed_stats = calc.calculate_all_stats(database)

   # Print frequency statistics
   freq_stats = detailed_stats['frequency']
   print(f"Mean abundance: {freq_stats.mean:.2f}")
   print(f"Median abundance: {freq_stats.median:.2f}")
   print(f"Standard deviation: {freq_stats.std_dev:.2f}")

   # Print composition statistics
   comp_stats = detailed_stats['composition']
   print(f"GC content: {comp_stats.gc_content:.2%}")
   print(f"AT content: {comp_stats.at_content:.2%}")

   # Step 4: Visualize k-mer abundance distribution
   distribution = detailed_stats['distribution']
   plt.figure(figsize=(10, 6))
   plt.bar(distribution.bins, distribution.counts)
   plt.xlabel('K-mer Count')
   plt.ylabel('Number of K-mers')
   plt.title('K-mer Abundance Distribution')
   plt.show()

Tutorial 2: Database Querying
------------------------------

Learn how to query k-mers in a database.

.. code-block:: python

   from rustkmer import KmerCounter, Database

   # Create or load a database
   counter = KmerCounter(k=31)
   database = counter.count_from_file("reads.fastq")

   # Save for later use
   database.save("kmer_database.rkdb")

   # Load database
   db = Database()
   db.load("kmer_database.rkdb")

   # Query individual k-mers
   test_kmers = [
       "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
       "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA",
       "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
   ]

   print("Query Results:")
   print("-" * 50)
   for kmer in test_kmers:
       result = db.query(kmer)
       if result.found:
           print(f"{kmer[:10]}...: {result.count:,} occurrences")
       else:
           print(f"{kmer[:10]}...: Not found")

   # Batch query
   results = db.query_multiple(test_kmers)
   print(f"\nBatch query: {len([r for r in results if r.found])} out of {len(results)} k-mers found")

Tutorial 3: Fuzzy K-mer Search
-------------------------------

Search for k-mers with mismatches for variant detection.

.. code-block:: python

   from rustkmer import KmerCounter, FuzzyQueryEngine, FuzzyQueryConfig

   # Create a reference database
   counter = KmerCounter(k=21)
   ref_db = counter.count_from_file("reference.fasta")

   # Configure fuzzy search
   config = FuzzyQueryConfig(
       max_distance=2,      # Allow up to 2 mismatches
       max_results=10,      # Return top 10 matches
       include_counts=True,
       sort_by_distance=True
   )

   # Create fuzzy query engine
   engine = FuzzyQueryEngine(config)
   engine.attach_database(ref_db)

   # Search for k-mers with variations
   query_kmers = [
       "ATCGATCGATCGATCGATCGA",  # Reference k-mer
       "ATCGATCGATCGATCGATCGC",  # 1 mismatch
       "ATCAATCGATCGATCGATCGA",  # 2 mismatches
       "TTTTTTTTTTTTTTTTTTTTT"   # No similarity
   ]

   for kmer in query_kmers:
       results = engine.query(kmer)
       print(f"\nQuery: {kmer}")
       if results:
           for i, result in enumerate(results[:5], 1):
               print(f"  {i}. Match: {result.match}")
               print(f"     Distance: {result.distance}")
               print(f"     Count: {result.count}")
       else:
           print("  No matches found")

Tutorial 4: Database Merging
----------------------------

Combine multiple k-mer databases.

.. code-block:: python

   from rustkmer import KmerCounter, DatabaseMerger, MergeConfig

   # Create multiple databases
   samples = ["sample1.fasta", "sample2.fasta", "sample3.fasta"]
   databases = []

   for sample_file in samples:
       counter = KmerCounter(k=31, threads=4)
       db = counter.count_from_file(sample_file)
       databases.append(db)
       print(f"{sample_file}: {db.total_kmers:,} k-mers")

   # Configure merge operation
   config = MergeConfig(
       threads=8,                # Use 8 threads for merging
       max_memory_mb=2048,      # Limit memory usage
       validate_checksums=True,
       preserve_metadata=True
   )

   # Merge databases
   merger = DatabaseMerger(config)
   output_path = "merged_database.rkdb"

   print("\nMerging databases...")
   result = merger.merge_databases(databases, output_path)

   print(f"Merge completed!")
   print(f"Databases processed: {result.total_databases}")
   print(f"Successful merges: {result.successful_merges}")
   print(f"Total k-mers before merge: {result.total_kmers:,}")
   print(f"Unique k-mers after merge: {result.total_unique_kmers:,}")
   print(f"Duplicate rate: {result.duplicate_rate:.2%}")
   print(f"Processing time: {result.merge_time_seconds:.2f} seconds")

Tutorial 5: Export and Visualization
-----------------------------------

Export k-mer data for external analysis.

.. code-block:: python

   from rustkmer import KmerCounter, DatabaseExporter, ExportConfig, ExportFormat
   from rustkmer import FilterConfig
   import pandas as pd

   # Create database
   counter = KmerCounter(k=21)
   database = counter.count_from_file("metagenome.fasta")

   # Export to JSON with filters
   filter_config = FilterConfig(min_count=5, max_count=1000)
   export_config = ExportConfig(
       format=ExportFormat.JSON,
       include_header=True,
       include_stats=True,
       sort_by_count=True,
       filter_config=filter_config
   )

   exporter = DatabaseExporter(export_config)
   exporter.export(database, "filtered_kmers.json")

   # Export to CSV for analysis
   csv_config = ExportConfig(
       format=ExportFormat.CSV,
       include_header=True,
       sort_by_count=True,
       filter_config=filter_config
   )
   exporter.config = csv_config
   exporter.export(database, "kmers.csv")

   # Load CSV into pandas for analysis
   df = pd.read_csv("kmers.csv")
   print(f"Exported {len(df)} k-mers to CSV")
   print("\nTop 10 most abundant k-mers:")
   print(df.head(10))

   # Basic analysis
   print(f"\nStatistics:")
   print(f"Mean count: {df['count'].mean():.2f}")
   print(f"Median count: {df['count'].median():.2f}")
   print(f"Max count: {df['count'].max()}")

Tutorial 6: Working with Large Datasets
---------------------------------------

Handle large genomic datasets efficiently.

.. code-block:: python

   from rustkmer import KmerCounter, Database
   import psutil
   import time
   import os

   # Monitor memory usage
   process = psutil.Process(os.getpid())

   def get_memory_mb():
       return process.memory_info().rss / 1024 / 1024

   # Step 1: Process large file with memory monitoring
   print("Processing large FASTA file...")
   initial_memory = get_memory_mb()
   print(f"Initial memory: {initial_memory:.1f} MB")

   # Use low memory mode for very large files
   counter = KmerCounter(k=31, threads=8)

   start_time = time.time()
   database = counter.count_from_file(
       "large_genome.fasta",
       low_memory=True,
       progress_callback=lambda p, t: print(f"\rProgress: {p}/{t} sequences", end="")
   )
   elapsed = time.time() - start_time

   final_memory = get_memory_mb()
   print(f"\n\nProcessing completed!")
   print(f"Time: {elapsed:.2f} seconds")
   print(f"Memory used: {final_memory - initial_memory:.1f} MB")
   print(f"Total k-mers: {database.total_kmers:,}")

   # Step 2: Batch processing for multiple files
   def process_file_batch(file_paths, output_dir):
       """Process multiple files in batches to manage memory."""
       batch_size = 5
       all_databases = []

       for i in range(0, len(file_paths), batch_size):
           batch = file_paths[i:i + batch_size]
           batch_databases = []

           print(f"\nProcessing batch {i//batch_size + 1}/{(len(file_paths)-1)//batch_size + 1}")

           for file_path in batch:
               print(f"  Processing {file_path}...")
               counter = KmerCounter(k=31)
               db = counter.count_from_file(file_path)
               batch_databases.append(db)

           # Merge batch databases
           if len(batch_databases) > 1:
               from rustkmer import DatabaseMerger
               merger = DatabaseMerger()
               batch_output = f"{output_dir}/batch_{i//batch_size + 1}.rkdb"
               merger.merge_databases(batch_databases, batch_output)
               all_databases.append(batch_output)
           else:
               all_databases.append(batch_databases[0])

       return all_databases

   # Example usage
   # large_files = ["file1.fasta", "file2.fasta", "file3.fasta", ...]
   # processed_dbs = process_file_batch(large_files, "output_dir")

Tutorial 7: Sequence Utilities
------------------------------

Use the utility functions for sequence manipulation.

.. code-block:: python

   from rustkmer.utils import (
       SequenceReader, SequenceWriter,
       validate_sequence, reverse_complement,
       kmerize_sequence, calculate_kmer_hash
   )

   # Read sequences efficiently
   with SequenceReader("sequences.fasta") as reader:
       total_sequences = reader.count_sequences()
       print(f"File contains {total_sequences} sequences")

       # Read first 10 sequences
       for i, (seq_id, sequence) in enumerate(reader):
           if i >= 10:
               break
           print(f"{seq_id}: {len(sequence)} bp")

   # Validate sequences
   sequences = [
       "ATCGATCGATCGATCG",
       "GCTAGCTAGCTAGCTAGC",
       "ATCGX",  # Invalid character
       "atcgatcg",  # Lowercase
   ]

   for seq in sequences:
       if validate_sequence(seq):
           print(f"✓ {seq}: Valid DNA sequence")
       else:
           print(f"✗ {seq}: Invalid DNA sequence")

   # Generate reverse complement
   dna_seq = "ATCGATCGATCGATCG"
   rc_seq = reverse_complement(dna_seq)
   print(f"\nOriginal:    {dna_seq}")
   print(f"Rev. Compl.: {rc_seq}")

   # Generate k-mers
   kmers = kmerize_sequence(dna_seq, k=8)
   print(f"\n8-mers from {dna_seq[:20]}...")
   for kmer in kmers[:5]:
       print(f"  {kmer}")

   # Calculate k-mer hashes
   for kmer in kmers[:3]:
       hash_val = calculate_kmer_hash(kmer)
       print(f"  {kmer} -> {hash_val}")

   # Write sequences
   sequences_to_write = [
       ("seq1", "ATCGATCGATCGATCGATCGATCGATCGATCG"),
       ("seq2", "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC"),
       ("seq3", "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT")
   ]

   with SequenceWriter("output.fasta", format="fasta") as writer:
       for seq_id, sequence in sequences_to_write:
           writer.write_sequence(seq_id, sequence)

Tutorial 8: Error Handling
--------------------------

Proper error handling for robust applications.

.. code-block:: python

   from rustkmer import KmerCounter, Database
   from rustkmer.exceptions import (
       RustKmerError, DatabaseError, QueryError,
       ValidationError, KmerCountingError
   )
   import logging

   # Setup logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   def safe_count_kmers(file_path, k=31, threads=4):
       """Safely count k-mers with error handling."""
       try:
           # Validate inputs
           if not isinstance(k, int) or k < 1 or k > 128:
               raise ValidationError(f"Invalid k-mer size: {k}")

           # Create counter
           counter = KmerCounter(k=k, threads=threads)

           # Count k-mers
           logger.info(f"Counting {k}-mers from {file_path}")
           database = counter.count_from_file(file_path)

           logger.info(f"Successfully counted {database.total_kmers:,} k-mers")
           return database

       except FileNotFoundError:
           logger.error(f"File not found: {file_path}")
           raise
       except KmerCountingError as e:
           logger.error(f"K-mer counting failed: {e}")
           raise
       except RustKmerError as e:
           logger.error(f"RustKmer error: {e}")
           raise
       except Exception as e:
           logger.error(f"Unexpected error: {e}")
           raise

   def safe_query_database(database, kmer):
       """Safely query k-mer with error handling."""
       try:
           # Validate k-mer
           if not isinstance(kmer, str):
               raise ValidationError("K-mer must be a string")

           if not validate_sequence(kmer):
               raise ValidationError(f"Invalid k-mer: {kmer}")

           if len(kmer) != database.kmer_size:
               raise ValidationError(
                   f"K-mer length mismatch: expected {database.kmer_size}, got {len(kmer)}"
               )

           # Query database
           result = database.query(kmer)
           return result

       except ValidationError as e:
           logger.warning(f"Validation error: {e}")
           return None
       except QueryError as e:
           logger.error(f"Query error: {e}")
           return None

   # Example usage
   try:
       db = safe_count_kmers("genome.fasta", k=31)
       result = safe_query_database(db, "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
       if result:
           print(f"Found k-mer {result.count} times")
   except Exception as e:
       logger.error(f"Failed to process file: {e}")