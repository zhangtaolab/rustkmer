Performance Optimization Guide
===============================

This guide provides tips and best practices for optimizing the performance of the RustKmer Python API.

.. contents::
   :local:
   :depth: 2

Performance Overview
--------------------

The RustKmer Python API is built with performance in mind, leveraging Rust's speed while providing Python's ease of use. Key performance characteristics:

- **K-mer counting**: 10-100x faster than pure Python implementations
- **Database queries**: Microsecond-level query times
- **Memory efficiency**: Uses memory mapping and efficient data structures
- **Parallel processing**: Multi-threaded support for CPU-intensive operations

Benchmark Results
~~~~~~~~~~~~~~~~

Typical performance metrics on a modern 8-core system:

.. list-table:: Performance Benchmarks
   :header-rows: 1

   * - Operation
     - Dataset Size
     - Time
     - Memory
     - Notes
   * - Count 31-mers
     - 1 GB FASTA
     - ~5 seconds
     - ~2 GB RAM
     - 4 threads
   * - Count 31-mers
     - 10 GB FASTA
     - ~45 seconds
     - ~8 GB RAM
     - 8 threads
   * - Database query
     - Single k-mer
     - ~10 microseconds
     - Negligible
     - From memory-mapped DB
   * - Batch query
     - 1000 k-mers
     - ~5 milliseconds
     - Negligible
     - All from memory
   * - Fuzzy search
     - 100 queries, dist=2
     - ~50 milliseconds
     - Negligible
     - Depends on database size

Optimization Strategies
----------------------

1. Thread Configuration
~~~~~~~~~~~~~~~~~~~~~~

Use appropriate thread counts based on your CPU and workload:

.. code-block:: python

   import multiprocessing

   # Get optimal thread count (usually number of CPU cores)
   optimal_threads = multiprocessing.cpu_count()

   # For I/O bound operations (reading files)
   io_threads = min(optimal_threads, 4)

   # For CPU bound operations (counting, merging)
   cpu_threads = optimal_threads

   # Configure RustKmer
   counter = KmerCounter(
       k=31,
       threads=cpu_threads,
       canonical=True
   )

2. Memory Management
~~~~~~~~~~~~~~~~~~~

For large datasets, use memory-efficient modes:

.. code-block:: python

   # For very large files (> available RAM)
   counter = KmerCounter(k=31)
   database = counter.count_from_file(
       "huge_dataset.fasta",
       low_memory=True  # Uses streaming processing
   )

   # Configure merge operations to limit memory
   from rustkmer import MergeConfig
   config = MergeConfig(
       max_memory_mb=4096,  # Limit memory usage
       threads=8
   )
   merger = DatabaseMerger(config)

3. Batch Operations
~~~~~~~~~~~~~~~~~~

Batch operations are more efficient than individual calls:

.. code-block:: python

   # Good: Batch queries
   kmer_list = ["ATCGATCG" + str(i).zfill(4) for i in range(1000)]
   results = database.query_multiple(kmer_list)

   # Avoid: Individual queries in loop
   # for kmer in kmer_list:
   #     result = database.query(kmer)  # Slow!

   # Good: Batch file processing
   def process_batch(file_paths):
       databases = []
       counter = KmerCounter(k=31, threads=8)
       for file_path in file_paths:
           db = counter.count_from_file(file_path)
           databases.append(db)
       return databases

4. Database Caching
~~~~~~~~~~~~~~~~~~~

Keep frequently accessed databases in memory:

.. code-block:: python

   class DatabaseCache:
       def __init__(self, max_size=5):
           self.cache = {}
           self.max_size = max_size

       def get_database(self, path):
           if path not in self.cache:
               if len(self.cache) >= self.max_size:
                   # Remove oldest entry
                   oldest = next(iter(self.cache))
                   del self.cache[oldest]
               db = Database()
               db.load(path)
               self.cache[path] = db
           return self.cache[path]

   # Usage
   cache = DatabaseCache()
   db = cache.get_database("frequent_database.rkdb")

5. Lazy Loading
~~~~~~~~~~~~~~~

Load data only when needed:

.. code-block:: python

   class LazyDatabase:
       def __init__(self, path):
           self.path = path
           self._db = None

       @property
       def db(self):
           if self._db is None:
               self._db = Database()
               self._db.load(self.path)
           return self._db

       def query(self, kmer):
           return self.db.query(kmer)

6. Progress Monitoring
~~~~~~~~~~~~~~~~~~~~~~

Use progress callbacks for long operations:

.. code-block:: python

   def progress_callback(processed, total):
       if total > 0:
           percent = (processed / total) * 100
           print(f"\rProgress: {percent:.1f}%", end="")
       if processed % 100 == 0:
           print(f"\nProcessed {processed} sequences")

   database = counter.count_from_file(
       "large_file.fasta",
       progress_callback=progress_callback
   )

Advanced Optimization Techniques
------------------------------

1. Vectorized Operations
~~~~~~~~~~~~~~~~~~~~~~~

When working with k-mer sets, use vectorized approaches:

.. code-block:: python

   import numpy as np

   # Pre-allocate arrays for better performance
   def batch_hash_kmers(kmers):
       hashes = np.zeros(len(kmers), dtype=np.uint64)
       for i, kmer in enumerate(kmers):
           hashes[i] = calculate_kmer_hash(kmer)
       return hashes

2. Memory Mapping
~~~~~~~~~~~~~~~~

For large databases, ensure memory mapping is used:

.. code-block:: python

   # RustKmer automatically uses memory mapping for .rkdb files
   # This allows accessing databases larger than RAM

   # For custom file formats, implement memory mapping
   import mmap

   def read_large_file_mmap(path):
       with open(path, 'rb') as f:
           with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
               # Process memory-mapped file
               yield mm.read()

3. Parallel Processing in Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Combine Python's multiprocessing with RustKmer:

.. code-block:: python

   from concurrent.futures import ProcessPoolExecutor
   import multiprocessing

   def process_file(file_path):
       counter = KmerCounter(k=31)
       return counter.count_from_file(file_path)

   def parallel_process(files):
       # Use process pool for CPU-bound work
       with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
           databases = list(executor.map(process_file, files))
       return databases

4. Asynchronous Operations
~~~~~~~~~~~~~~~~~~~~~~~~~

For I/O bound operations, use async:

.. code-block:: python

   import asyncio
   import aiofiles

   async def async_count_file(file_path):
       # Simulate async file reading
       async with aiofiles.open(file_path, 'r') as f:
           content = await f.read()
       # Process with RustKmer (sync operation)
       counter = KmerCounter(k=31)
       return counter.count_from_string(content)

   async def process_files_async(file_paths):
       tasks = [async_count_file(path) for path in file_paths]
       return await asyncio.gather(*tasks)

Performance Profiling
---------------------

1. Built-in Profiling
~~~~~~~~~~~~~~~~~~~~~

Use Python's built-in profiler:

.. code-block:: python

   import cProfile
   import pstats

   def profile_function(func, *args, **kwargs):
       profiler = cProfile.Profile()
       profiler.enable()
       result = func(*args, **kwargs)
       profiler.disable()

       stats = pstats.Stats(profiler)
       stats.sort_stats('cumulative')
       stats.print_stats(10)  # Top 10 functions

       return result

   # Usage
   result = profile_function(
       counter.count_from_file,
       "large_dataset.fasta"
   )

2. Memory Profiling
~~~~~~~~~~~~~~~~~~~

Profile memory usage:

.. code-block:: python

   from memory_profiler import profile

   @profile
   def count_kmers_with_profiling(file_path):
       counter = KmerCounter(k=31)
       return counter.count_from_file(file_path)

   # Run with: python -m memory_profiler script.py

3. Line Profiling
~~~~~~~~~~~~~~~~~

Profile line-by-line execution:

.. code-block:: python

   from line_profiler import LineProfiler

   def count_kmers(file_path):
       counter = KmerCounter(k=31)
       return counter.count_from_file(file_path)

   profiler = LineProfiler()
   profiler.add_function(count_kmers)
   profiler.enable_by_count()

   result = count_kmers("test.fasta")
   profiler.print_stats()

Best Practices
--------------

1. Choose Right K-mer Size
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: K-mer Size Considerations
   :header-rows: 1

   * - K-mer Size
     - Use Case
     - Memory
     - Specificity
   * - 15-21
     - Small genomes, metagenomics
     - Low
     - Low
   * - 31
     - Standard bacterial genomes
     - Medium
     - High
   * - 51-63
     - Eukaryotic genomes
     - High
     - Very High

2. Optimize File I/O
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Use compressed files for storage
   # RustKmer can read gzipped files directly

   # For multiple small files, consider concatenating
   def concatenate_files(input_files, output_file):
       with open(output_file, 'w') as outfile:
           for fname in input_files:
               with open(fname) as infile:
                   outfile.write(infile.read())

3. Database Design
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # For frequent queries, create specialized databases
   # with only the k-mers you need

   from rustkmer import FilterConfig

   # Export only high-abundance k-mers
   filter_config = FilterConfig(min_count=10)
   export_config = ExportConfig(
       filter_config=filter_config,
       format=ExportFormat.BINARY
   )

   exporter = DatabaseExporter(export_config)
   exporter.export(large_db, "filtered_db.rkdb")

4. Error Handling Overhead
~~~~~~~~~~~~~~~~~~~~~~~~~~

Minimize error checking in performance-critical loops:

.. code-block:: python

   # Bad: Checking inside loop
   def slow_query(db, kmer_list):
       results = []
       for kmer in kmer_list:
           if validate_kmer(kmer):  # Validation every time
               results.append(db.query(kmer))
       return results

   # Good: Validate once, then loop
   def fast_query(db, kmer_list):
       # Pre-validate all k-mers
       valid_kmers = [k for k in kmer_list if validate_kmer(k)]
       # Batch query
       return db.query_multiple(valid_kmers)

Common Performance Pitfalls
---------------------------

1. **Excessive Small Operations**: Avoid many small database operations
2. **Memory Leaks**: Close database handles when done
3. **Thread Oversubscription**: Don't use more threads than CPU cores
4. **Unnecessary Copies**: Pass references when possible
5. **Blocking I/O**: Use async for network operations

Example: High-Throughput Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class HighThroughputKmerProcessor:
       def __init__(self, k=31, threads=8):
           self.k = k
           self.threads = threads
           self.cache = {}

       def process_stream(self, file_stream):
           """Process a stream of sequences efficiently."""
           buffer = []
           buffer_size = 10000

           for sequence in file_stream:
               buffer.append(sequence)

               if len(buffer) >= buffer_size:
                   # Process buffer
                   self._process_buffer(buffer)
                   buffer.clear()

           # Process remaining
           if buffer:
               self._process_buffer(buffer)

       def _process_buffer(self, sequences):
           """Process a batch of sequences."""
           # Concatenate for efficient counting
           combined = "\n".join([f">seq{i}\n{seq}"
                               for i, seq in enumerate(sequences)])

           counter = KmerCounter(k=self.k, threads=self.threads)
           return counter.count_from_string(combined)

   # Usage
   processor = HighThroughputKmerProcessor(k=31, threads=8)
   with open("sequences.txt") as f:
       processor.process_stream(f)