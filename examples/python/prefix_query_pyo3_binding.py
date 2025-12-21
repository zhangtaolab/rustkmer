#!/usr/bin/env python3
"""
PyO3 Python Binding for Prefix Query Command
等效于: ./target/release/rustkmer prefix-query ~/Data/data/kmer/K19/R1_001.rkdb AAAAAAAA{N5}AAAAAA

Author: RustKmer Team
Date: 2025-12-21
"""

import sys
import time
import argparse
from typing import Dict, Any, Optional

try:
    import rustkmer_pyo3
except ImportError as e:
    print(f"❌ 无法导入 rustkmer_pyo3 模块: {e}")
    print("💡 请确保已正确构建 PyO3 扩展:")
    print("   cd rustkmer/pyo3")
    print("   export RUSTFLAGS='-C link-arg=-undefined -C link-arg=dynamic_lookup'")
    print("   export PYO3_PYTHON=/usr/bin/python3")
    print("   cargo build")
    print("   export PYTHONPATH='$PWD/target/debug:$PYTHONPATH'")
    sys.exit(1)


class PrefixQueryPyO3Binding:
    """PyO3 Python binding for prefix query functionality"""
    
    def __init__(self, database_path: str):
        """
        Initialize prefix query engine
        
        Args:
            database_path: Path to RKDB file
        """
        self.database_path = database_path
        self.query_engine = None
        self.extended_engine = None
        
        try:
            # Try to create the basic query engine
            self.query_engine = rustkmer_pyo3.PyPrefixQuery(database_path)
            print(f"✅ 成功加载数据库: {database_path}")
            
            # Create extended engine for detailed metrics
            self.extended_engine = rustkmer_pyo3.PyExtendedPrefixQuery(database_path)
            print(f"✅ 成功创建扩展查询引擎")
            
        except Exception as e:
            print(f"❌ 数据库加载失败: {e}")
            raise
    
    def query_prefix(self, prefix: str) -> Dict[str, str]:
        """
        Query k-mers by prefix
        
        Args:
            prefix: DNA sequence prefix
            
        Returns:
            Dictionary of k-mer -> count mappings
        """
        try:
            results = self.query_engine.query_prefix_string(prefix)
            print(f"🔍 前缀查询完成: '{prefix}' - 找到 {len(results)} 个结果")
            return results
        except Exception as e:
            print(f"❌ 前缀查询失败: {e}")
            return {}
    
    def query_hybrid(self, pattern: str) -> Dict[str, str]:
        """
        Query k-mers by hybrid pattern (e.g., ATAC{N5}ACAC)
        
        Args:
            pattern: Hybrid pattern with {N} syntax
            
        Returns:
            Dictionary of k-mer -> count mappings
        """
        try:
            # First, let's parse the pattern to show what we're looking for
            try:
                pattern_info = self.query_engine.parse_pattern(pattern)
                print(f"🔍 混合模式解析:")
                print(f"   前缀: '{pattern_info['prefix']}'")
                print(f"   后缀: '{pattern_info['suffix']}'")
                print(f"   N数量: {pattern_info['n_count']}")
                print(f"   总长度: {pattern_info['total_length']}")
            except:
                # Pattern parsing might not be available, continue anyway
                pass
            
            # Perform the hybrid query
            results = self.query_engine.query_hybrid(pattern)
            print(f"🔍 混合查询完成: '{pattern}' - 找到 {len(results)} 个结果")
            return results
        except Exception as e:
            print(f"❌ 混合查询失败: {e}")
            return {}
    
    def query_with_metrics(self, pattern: str) -> Optional[Dict[str, Any]]:
        """
        Query with detailed performance metrics
        
        Args:
            pattern: Query pattern (prefix or hybrid)
            
        Returns:
            Dictionary containing results and metrics
        """
        try:
            # Check if it's a hybrid pattern
            if '{N' in pattern:
                metrics = self.extended_engine.query_hybrid_with_metrics(pattern)
            else:
                metrics = self.extended_engine.query_with_metrics(pattern)
            
            print(f"📊 查询指标:")
            print(f"   执行时间: {metrics.execution_time_ms} ms")
            print(f"   找到结果: {metrics.total_matches} 个")
            print(f"   内存块起始: {metrics.start_index}")
            print(f"   内存块结束: {metrics.end_index}")
            print(f"   内存块大小: {metrics.block_size}")
            
            return {
                'results': dict(metrics.results),
                'execution_time_ms': metrics.execution_time_ms,
                'total_matches': metrics.total_matches,
                'start_index': metrics.start_index,
                'end_index': metrics.end_index,
                'block_size': metrics.block_size
            }
        except Exception as e:
            print(f"❌ 带指标的查询失败: {e}")
            return None
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        try:
            info = self.query_engine.database_info()
            return dict(info)
        except Exception as e:
            print(f"❌ 获取数据库信息失败: {e}")
            return {}
    
    def batch_query(self, patterns: list) -> Dict[str, Any]:
        """
        Batch query multiple patterns
        
        Args:
            patterns: List of query patterns
            
        Returns:
            Dictionary of pattern -> results mapping
        """
        try:
            results = self.extended_engine.batch_query(patterns)
            
            print(f"🔄 批量查询完成: {len(patterns)} 个模式")
            for pattern, metrics in results.items():
                print(f"   '{pattern}': {metrics.total_matches} 个结果, {metrics.execution_time_ms} ms")
            
            return {pattern: {
                'results': dict(metrics.results),
                'execution_time_ms': metrics.execution_time_ms,
                'total_matches': metrics.total_matches
            } for pattern, metrics in results.items()}
            
        except Exception as e:
            print(f"❌ 批量查询失败: {e}")
            return {}


def main():
    """Main function demonstrating the PyO3 binding usage"""
    
    # Command line argument parsing
    parser = argparse.ArgumentParser(
        description='PyO3 Python Binding for Prefix Query',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s ~/Data/data/kmer/K19/R1_001.rkdb "AAAAAAAA{N5}AAAAAA"
  %(prog)s ~/Data/data/kmer/K19/R1_001.rkdb "AAAAAAAA" --prefix-only
  %(prog)s ~/Data/data/kmer/K19/R1_001.rkdb "AAAAAAAA{N5}AAAAAA" --with-metrics
  %(prog)s ~/Data/data/kmer/K19/R1_001.rkdb "AAAAAAAA" --batch "AAAAAAAA{N5}AAAAAA" "AAAAAAA"
        """
    )
    
    parser.add_argument('database', help='RKDB database file path')
    parser.add_argument('pattern', nargs='?', help='Query pattern (prefix or hybrid)')
    parser.add_argument('--prefix-only', action='store_true', 
                       help='Treat pattern as pure prefix (no hybrid parsing)')
    parser.add_argument('--with-metrics', action='store_true',
                       help='Show detailed performance metrics')
    parser.add_argument('--batch', nargs='+', metavar='PATTERN',
                       help='Batch query multiple patterns')
    parser.add_argument('--max-results', type=int, default=20,
                       help='Maximum number of results to display')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    try:
        # Initialize the query engine
        print("🚀 初始化 PyO3 前缀查询引擎...")
        binding = PrefixQueryPyO3Binding(args.database)
        
        # Display database information
        print("\n📋 数据库信息:")
        db_info = binding.get_database_info()
        for key, value in db_info.items():
            print(f"   {key}: {value}")
        
        # Determine which query to run
        if args.batch:
            # Batch query mode
            print(f"\n🔄 执行批量查询...")
            results = binding.batch_query(args.batch)
            
            for pattern, data in results.items():
                print(f"\n📊 模式 '{pattern}' 的结果:")
                print(f"   找到: {data['total_matches']} 个k-mer")
                print(f"   时间: {data['execution_time_ms']} ms")
                
                # Show sample results
                sample_results = list(data['results'].items())[:args.max_results]
                for kmer, count in sample_results:
                    print(f"   {kmer}: {count}")
                if data['total_matches'] > args.max_results:
                    print(f"   ... 还有 {data['total_matches'] - args.max_results} 个结果")
        
        elif args.pattern:
            # Single query mode
            pattern = args.pattern
            print(f"\n🔍 执行查询: '{pattern}'")
            
            if args.with_metrics:
                # Query with detailed metrics
                result_data = binding.query_with_metrics(pattern)
                if result_data:
                    results = result_data['results']
                    print(f"\n📊 查询结果 (前 {min(len(results), args.max_results)} 个):")
                    for kmer, count in list(results.items())[:args.max_results]:
                        print(f"   {kmer}: {count}")
                    if len(results) > args.max_results:
                        print(f"   ... 还有 {len(results) - args.max_results} 个结果")
            else:
                # Regular query
                if args.prefix_only or '{N' not in pattern:
                    results = binding.query_prefix(pattern)
                    print(f"\n📊 前缀查询结果 (前 {min(len(results), args.max_results)} 个):")
                else:
                    results = binding.query_hybrid(pattern)
                    print(f"\n📊 混合查询结果 (前 {min(len(results), args.max_results)} 个):")
                
                for kmer, count in list(results.items())[:args.max_results]:
                    print(f"   {kmer}: {count}")
                if len(results) > args.max_results:
                    print(f"   ... 还有 {len(results) - args.max_results} 个结果")
        
        else:
            # No pattern provided, show help
            parser.print_help()
            print("\n💡 示例查询模式:")
            print("   AAAAAAAA{N5}AAAAAA  # 混合搜索 (前缀+后缀+中间N个wildcards)")
            print("   AAAAAAAA            # 纯前缀搜索")
            print("   ATCG{N3}GCTA         # 混合搜索，不同长度")
        
        print("\n✅ PyO3 Python Binding 执行完成!")
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        print("💡 请检查数据库文件路径是否正确")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
