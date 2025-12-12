#!/usr/bin/env python3
"""
RustKmer Performance Benchmarking

This example demonstrates performance benchmarking of RustKmer:
- K-mer counting performance with different parameters
- Database query performance
- Memory usage analysis
- Thread scaling analysis
- Comparison with different k-mer sizes

Author: RustKmer Team
"""

import os
import sys
import time
import psutil
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor
from rustkmer import KmerCounter, Database, FuzzyQuery

class PerformanceBenchmark:
    """Performance benchmarking suite for RustKmer"""

    def __init__(self, output_dir="benchmark_results"):
        self.output_dir = output_dir
        self.results = {}
        self.process = psutil.Process()

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024

    def benchmark_kmer_counting(self):
        """Benchmark k-mer counting performance"""
        print("\n" + "=" * 60)
        print("K-mer Counting Performance Benchmark")
        print("=" * 60)

        # Test parameters
        sequence_sizes = [1000, 10000, 100000, 1000000]  # bp
        k_sizes = [7, 15, 21, 31, 51]
        thread_counts = [1, 2, 4, 8]

        results = []

        for seq_size in sequence_sizes:
            print(f"\nTesting sequence size: {seq_size:,} bp")

            # Generate test sequence
            test_seq = self.generate_sequence(seq_size)

            for k in k_sizes:
                if k > seq_size:
                    continue

                print(f"  k={k}...", end="", flush=True)

                for threads in thread_counts:
                    # Warm up
                    counter = KmerCounter(k=k, threads=threads)
                    counter.count_string(test_seq[:1000])

                    # Benchmark
                    initial_memory = self.get_memory_usage()
                    start_time = time.time()

                    counter = KmerCounter(k=k, threads=threads)
                    counter.count_string(test_seq)

                    end_time = time.time()
                    final_memory = self.get_memory_usage()

                    # Record results
                    total_kmers = counter.get_total_count()
                    unique_kmers = counter.get_unique_count()
                    processing_time = end_time - start_time
                    memory_used = final_memory - initial_memory
                    throughput = total_kmers / processing_time if processing_time > 0 else 0

                    results.append({
                        'sequence_size': seq_size,
                        'k_size': k,
                        'threads': threads,
                        'processing_time': processing_time,
                        'total_kmers': total_kmers,
                        'unique_kmers': unique_kmers,
                        'memory_used_mb': memory_used,
                        'throughput_kmers_per_sec': throughput,
                        'kmer_rate': (seq_size - k + 1) / processing_time if processing_time > 0 else 0
                    })

                print(" ✓", end="", flush=True)

            print()

        self.results['kmer_counting'] = pd.DataFrame(results)

        # Save results
        output_path = os.path.join(self.output_dir, 'kmer_counting_benchmark.csv')
        self.results['kmer_counting'].to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")

    def benchmark_database_operations(self):
        """Benchmark database operations"""
        print("\n" + "=" * 60)
        print("Database Operations Performance Benchmark")
        print("=" * 60)

        # Create test database
        print("Creating test database...")
        counter = KmerCounter(k=21, canonical=True)

        # Add k-mers to database
        for i in range(10000):
            seq = f"{'ATCG' * 5}{i:04d}{'GCTA' * 5}"
            counter.count_string(seq)

        db_path = os.path.join(self.output_dir, "benchmark_db.rkdb")
        counter.save_to_database(db_path)

        db_size_mb = os.path.getsize(db_path) / 1024 / 1024
        print(f"Test database created: {db_size_mb:.2f} MB")

        # Database loading benchmark
        print("\n--- Database Loading Benchmark ---")
        load_times = []
        memory_usage = []

        for i in range(10):
            initial_memory = self.get_memory_usage()
            start_time = time.time()

            db = Database()
            db.load(db_path)

            end_time = time.time()
            final_memory = self.get_memory_usage()

            load_times.append(end_time - start_time)
            memory_usage.append(final_memory - initial_memory)

        avg_load_time = sum(load_times) / len(load_times)
        avg_memory = sum(memory_usage) / len(memory_usage)

        print(f"Average load time: {avg_load_time:.4f} seconds")
        print(f"Average memory usage: {avg_memory:.2f} MB")

        # Query performance benchmark
        print("\n--- Query Performance Benchmark ---")

        # Generate test queries
        test_queries = []
        for i in range(1000):
            test_queries.append(f"{'ATCG' * 5}{i:03d}{'GCTA' * 5}")

        # Single queries
        print("Testing single queries...")
        single_times = []
        for query in test_queries[:100]:  # Test first 100
            start_time = time.time()
            db.query(query)
            single_times.append(time.time() - start_time)

        avg_single_time = sum(single_times) / len(single_times)
        print(f"Average single query time: {avg_single_time*1000:.3f} ms")
        print(f"Queries per second: {1/avg_single_time:.0f}")

        # Batch queries
        print("\nTesting batch queries...")
        batch_sizes = [10, 50, 100, 500, 1000]

        batch_results = []
        for batch_size in batch_sizes:
            start_time = time.time()
            results = db.query_multiple(test_queries[:batch_size])
            batch_time = time.time() - start_time

            avg_per_query = batch_time / batch_size
            queries_per_sec = batch_size / batch_time

            batch_results.append({
                'batch_size': batch_size,
                'total_time': batch_time,
                'avg_time_per_query': avg_per_query,
                'queries_per_second': queries_per_sec
            })

            print(f"  Batch size {batch_size:4d}: {avg_per_query*1000:6.3f} ms/query, {queries_per_sec:6.0f} queries/sec")

        self.results['database_operations'] = {
            'load_time': avg_load_time,
            'load_memory': avg_memory,
            'db_size_mb': db_size_mb,
            'single_query_time': avg_single_time,
            'batch_results': pd.DataFrame(batch_results)
        }

        # Fuzzy query benchmark
        print("\n--- Fuzzy Query Benchmark ---")
        fq = FuzzyQuery()
        fq.load(db_path)

        fuzzy_patterns = ["ATCGNNNNNNATCG", "GCTANNNNNNGCTA", "NNNNATCGATCNNN"]
        max_mismatches = [0, 1, 2, 3]

        fuzzy_results = []
        for pattern in fuzzy_patterns:
            for mismatches in max_mismatches:
                start_time = time.time()
                results = fq.query(pattern, max_mismatches=mismatches)
                query_time = time.time() - start_time

                fuzzy_results.append({
                    'pattern': pattern,
                    'max_mismatches': mismatches,
                    'query_time': query_time,
                    'results_found': len(results)
                })

                print(f"  Pattern '{pattern}', end=" ")
                print(f"(≤{mismatches} mismatches): {query_time*1000:.2f} ms, {len(results)} results")

        self.results['database_operations']['fuzzy_queries'] = pd.DataFrame(fuzzy_results)

        # Clean up
        os.remove(db_path)

    def benchmark_thread_scaling(self):
        """Benchmark thread scaling performance"""
        print("\n" + "=" * 60)
        print("Thread Scaling Performance Benchmark")
        print("=" * 60)

        # Test parameters
        file_sizes = [10000, 100000, 1000000]  # sequences
        thread_counts = [1, 2, 4, 8, 16]
        k = 21

        scaling_results = []

        for file_size in file_sizes:
            print(f"\nTesting with {file_size:,} sequences")

            # Create test file
            test_file = os.path.join(self.output_dir, f"thread_test_{file_size}.fa")
            self.create_test_fasta(test_file, file_size)

            for threads in thread_counts:
                print(f"  {threads} threads...", end="", flush=True)

                # Benchmark
                start_time = time.time()
                initial_memory = self.get_memory_usage()

                counter = KmerCounter(k=k, canonical=True, threads=threads)
                counter.count_file(test_file)

                end_time = time.time()
                final_memory = self.get_memory_usage()

                processing_time = end_time - start_time
                memory_used = final_memory - initial_memory
                throughput = counter.get_total_count() / processing_time

                scaling_results.append({
                    'file_size': file_size,
                    'threads': threads,
                    'processing_time': processing_time,
                    'throughput': throughput,
                    'memory_used_mb': memory_used,
                    'efficiency': throughput / threads  # Throughput per thread
                })

                print(" ✓", end="", flush=True)

            # Clean up
            os.remove(test_file)
            print()

        self.results['thread_scaling'] = pd.DataFrame(scaling_results)

        # Calculate speedup
        speedup_data = []
        for file_size in file_sizes:
            single_thread_throughput = None
            for result in scaling_results:
                if result['file_size'] == file_size and result['threads'] == 1:
                    single_thread_throughput = result['throughput']
                    break

            if single_thread_throughput:
                for result in scaling_results:
                    if result['file_size'] == file_size:
                        speedup = result['throughput'] / single_thread_throughput
                        efficiency = speedup / result['threads'] * 100
                        result['speedup'] = speedup
                        result['efficiency_percent'] = efficiency

        # Save results
        output_path = os.path.join(self.output_dir, 'thread_scaling_benchmark.csv')
        self.results['thread_scaling'].to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")

    def create_test_fasta(self, filepath, num_sequences):
        """Create a test FASTA file"""
        with open(filepath, 'w') as f:
            for i in range(num_sequences):
                seq = f"{'ATCG' * 5}{i:04d}{'GCTA' * 5}"
                f.write(f">seq_{i}\n")
                f.write(f"{seq}\n")

    def generate_sequence(self, length):
        """Generate a random DNA sequence"""
        import random
        bases = ['A', 'T', 'C', 'G']
        return ''.join(random.choice(bases) for _ in range(length))

    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "=" * 60)
        print("Performance Report Summary")
        print("=" * 60)

        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'platform': sys.platform
            }
        }

        # K-mer counting summary
        if 'kmer_counting' in self.results:
            df = self.results['kmer_counting']

            best_throughput = df['throughput_kmers_per_sec'].max()
            best_config = df.loc[df['throughput_kmers_per_sec'].idxmax()]

            report['kmer_counting'] = {
                'best_throughput_kmers_per_sec': best_throughput,
                'best_config': {
                    'k_size': best_config['k_size'],
                    'threads': best_config['threads'],
                    'sequence_size': best_config['sequence_size']
                },
                'average_throughput': df['throughput_kmers_per_sec'].mean(),
                'peak_memory_mb': df['memory_used_mb'].max()
            }

            print(f"\nK-mer Counting Performance:")
            print(f"  Best throughput: {best_throughput:,.0f} k-mers/sec")
            print(f"  Best config: k={best_config['k_size']}, threads={best_config['threads']}")
            print(f"  Average throughput: {df['throughput_kmers_per_sec'].mean():,.0f} k-mers/sec")
            print(f"  Peak memory usage: {df['memory_used_mb'].max():.2f} MB")

        # Database operations summary
        if 'database_operations' in self.results:
            db_ops = self.results['database_operations']

            report['database_operations'] = {
                'load_time_seconds': db_ops['load_time'],
                'load_memory_mb': db_ops['load_memory'],
                'single_query_time_ms': db_ops['single_query_time'] * 1000,
                'db_size_mb': db_ops['db_size_mb']
            }

            print(f"\nDatabase Operations Performance:")
            print(f"  Load time: {db_ops['load_time']:.4f} seconds")
            print(f"  Load memory: {db_ops['load_memory']:.2f} MB")
            print(f"  Single query: {db_ops['single_query_time']*1000:.3f} ms")
            print(f"  Database size: {db_ops['db_size_mb']:.2f} MB")

            if 'batch_results' in db_ops:
                batch_df = db_ops['batch_results']
                max_batch_qps = batch_df['queries_per_second'].max()
                print(f"  Max batch queries/sec: {max_batch_qps:,.0f}")

        # Thread scaling summary
        if 'thread_scaling' in self.results:
            df = self.results['thread_scaling']

            # Calculate average speedup
            speedups = []
            for file_size in df['file_size'].unique():
                single_thread = df[(df['file_size'] == file_size) & (df['threads'] == 1)]
                multi_thread = df[(df['file_size'] == file_size) & (df['threads'] > 1)]

                if not single_thread.empty and not multi_thread.empty:
                    st_throughput = single_thread['throughput'].iloc[0]
                    for _, row in multi_thread.iterrows():
                        speedup = row['throughput'] / st_throughput
                        speedups.append(speedup)

            avg_speedup = sum(speedups) / len(speedups) if speedups else 0

            report['thread_scaling'] = {
                'average_speedup': avg_speedup,
                'max_threads_tested': df['threads'].max()
            }

            print(f"\nThread Scaling:")
            print(f"  Average speedup: {avg_speedup:.2f}x")
            print(f"  Max threads tested: {df['threads'].max()}")

        # Save report
        report_path = os.path.join(self.output_dir, 'performance_report.json')
        with open(report_path, 'w') as f:
            import json
            json.dump(report, f, indent=2)

        print(f"\nFull report saved to: {report_path}")

    def create_performance_plots(self):
        """Create performance visualization plots"""
        print("\n" + "=" * 60)
        print("Creating Performance Plots")
        print("=" * 60)

        plt.style.use('seaborn-v0_8')

        # 1. K-mer counting throughput
        if 'kmer_counting' in self.results:
            df = self.results['kmer_counting']

            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('K-mer Counting Performance', fontsize=16)

            # Throughput vs k-mer size
            sns.lineplot(data=df, x='k_size', y='throughput_kmers_per_sec',
                         hue='threads', ax=axes[0, 0])
            axes[0, 0].set_title('Throughput vs K-mer Size')
            axes[0, 0].set_ylabel('Throughput (k-mers/sec)')

            # Memory usage
            sns.lineplot(data=df, x='k_size', y='memory_used_mb',
                         hue='threads', ax=axes[0, 1])
            axes[0, 1].set_title('Memory Usage vs K-mer Size')
            axes[0, 1].set_ylabel('Memory (MB)')

            # Throughput vs sequence size
            sns.lineplot(data=df, x='sequence_size', y='throughput_kmers_per_sec',
                         hue='threads', ax=axes[1, 0])
            axes[1, 0].set_title('Throughput vs Sequence Size')
            axes[1, 0].set_xlabel('Sequence Size (bp)')

            # Thread efficiency
            df['efficiency'] = df['throughput_kmers_per_sec'] / df['threads']
            sns.lineplot(data=df, x='threads', y='efficiency',
                         hue='k_size', ax=axes[1, 1])
            axes[1, 1].set_title('Thread Efficiency')
            axes[1, 1].set_xlabel('Number of Threads')

            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, 'kmer_counting_performance.png'),
                       dpi=300, bbox_inches='tight')
            plt.close()

        # 2. Thread scaling
        if 'thread_scaling' in self.results:
            df = self.results['thread_scaling']

            plt.figure(figsize=(12, 8))

            # Speedup plot
            for file_size in df['file_size'].unique():
                subset = df[df['file_size'] == file_size]
                single_thread = subset[subset['threads'] == 1]['throughput'].iloc[0]
                subset['speedup'] = subset['throughput'] / single_thread
                subset['efficiency'] = subset['speedup'] / subset['threads'] * 100

                plt.plot(subset['threads'], subset['speedup'],
                        marker='o', label=f'{file_size:,} sequences')

            plt.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
            plt.axhline(y=8, color='red', linestyle='--', alpha=0.5, label='8 threads (ideal)')

            plt.xlabel('Number of Threads')
            plt.ylabel('Speedup')
            plt.title('Thread Scaling Performance')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, 'thread_scaling.png'),
                       dpi=300, bbox_inches='tight')
            plt.close()

        # 3. Database performance
        if 'database_operations' in self.results:
            db_ops = self.results['database_operations']

            if 'batch_results' in db_ops:
                df = db_ops['batch_results']

                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

                # Batch size vs total time
                sns.lineplot(data=df, x='batch_size', y='total_time',
                             marker='o', ax=ax1)
                ax1.set_title('Batch Query Time vs Batch Size')
                ax1.set_xlabel('Batch Size')
                ax1.set_ylabel('Total Time (seconds)')

                # Batch size vs queries per second
                sns.lineplot(data=df, x='batch_size', y='queries_per_second',
                             marker='o', ax=ax2, color='orange')
                ax2.set_title('Query Rate vs Batch Size')
                ax2.set_xlabel('Batch Size')
                ax2.set_ylabel('Queries per Second')

                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, 'database_performance.png'),
                           dpi=300, bbox_inches='tight')
                plt.close()

        print(f"Plots saved to: {self.output_dir}")

    def run_full_benchmark(self):
        """Run the complete performance benchmark suite"""
        print("RustKmer Performance Benchmark Suite")
        print("=====================================")

        try:
            # Run all benchmarks
            self.benchmark_kmer_counting()
            self.benchmark_database_operations()
            self.benchmark_thread_scaling()

            # Generate report and plots
            self.generate_performance_report()
            self.create_performance_plots()

            print("\n" + "=" * 60)
            print("Benchmarking completed successfully!")
            print("=" * 60)
            print(f"Results directory: {self.output_dir}")

        except Exception as e:
            print(f"\nBenchmarking failed with error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

def main():
    """Main function"""
    # Run benchmarks
    benchmark = PerformanceBenchmark("benchmark_results")
    benchmark.run_full_benchmark()

if __name__ == "__main__":
    main()