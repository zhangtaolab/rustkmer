#!/usr/bin/env python3
"""
FASTA Gap Filling Batch Processor - Single Thread Version (FIXED)

This script processes FASTA files containing DNA sequences with N-gaps,
using the k-mer based gap filling algorithm (SINGLE THREAD VERSION - FIXED).

PROCESSING RULES:
- Sequences with internal gaps: Fill gaps using k-mer algorithm
- Sequences with >3 N's at start/end: Print original sequence (no processing)
- Sequences with no N's: Print original sequence (no processing)
- Sequences with only small end N's (≤3): Print original sequence (no processing)

FIXES:
- Fixed list index out of range error
- Enhanced boundary checking
- Improved sequence mapping logic
- Added intelligent sequence filtering

Usage:
    python process_fasta_gaps_single_thread_FIXED.py --input input.fa --output output.fa --db /path/to/database.rkdb
"""

import argparse
import sys
from pathlib import Path
import pyfastx
from tqdm import tqdm
from rustkmer import Database

# Import functions from existing gap_filling module
from gap_filling import (
    get_consecutive_N_regions,
    reduce_N_positions,
    polish_all_gap_regions,
    apply_all_polish_results,
    get_kmer_count_zero,
    get_kmer_list
)


class FastaGapProcessor:
    """Process FASTA files to fill gaps in DNA sequences using k-mer based algorithm"""
    
    def __init__(self, database_path, kmer_size=19, max_n_per_region=11, top_n=1000):
        """
        Initialize the gap processor
        
        Args:
            database_path: Path to k-mer database file
            kmer_size: Size of k-mers to use (default: 19)
            max_n_per_region: Maximum N's to process per region (default: 11)
            top_n: Number of top matches to consider (default: 1000)
        """
        # Initialize database
        try:
            self.db = Database(database_path, validate=False)
        except Exception as e:
            print(f"Error loading database {database_path}: {e}")
            sys.exit(1)
        
        self.kmer_size = kmer_size
        self.max_n_per_region = max_n_per_region
        self.top_n = top_n
        
        # Statistics tracking
        self.stats = {
            'total_sequences': 0,
            'processed_sequences': 0,  # 进行填充处理的序列
            'skipped_no_gaps': 0,      # 跳过的序列（无内部gap）
            'too_many_end_n': 0,       # 开头或结尾超过3个N的序列
            'no_n_sequences': 0,       # 没有N的序列
            'total_gaps_filled': 0,
            'successful_fills': 0
        }
    
    def classify_sequence(self, sequence):
        """
        Classify sequence for processing decision
        
        Rules:
        - Sequences with >3 N's at start or end: "too_many_end_n"
        - Sequences with no N's: "no_n"  
        - Sequences with internal gaps: "process"
        - Sequences with only small end N's (<=3): "skip"
        
        Args:
            sequence: DNA sequence string
            
        Returns:
            str: Classification category
        """
        # Count leading and trailing N's
        leading_n_count = 0
        for char in sequence:
            if char == 'N':
                leading_n_count += 1
            else:
                break
        
        trailing_n_count = 0
        for char in reversed(sequence):
            if char == 'N':
                trailing_n_count += 1
            else:
                break
        
        # Check if sequence has no N's at all
        if 'N' not in sequence:
            return "no_n"
        
        # Check if too many leading or trailing N's (>3)
        if leading_n_count > 3 or trailing_n_count > 3:
            return "too_many_end_n"
        
        # Get N regions for internal gap check
        n_regions = get_consecutive_N_regions(sequence)
        
        if not n_regions:
            return "no_n"
        
        # Check if any N region is internal (not at sequence ends)
        sequence_length = len(sequence)
        
        for region in n_regions:
            # If region is not at start or end, it's an internal gap
            if region['nstart'] > 0 and region['nend'] < sequence_length - 1:
                return "process"
        
        # All N regions are at ends (but <=3 each)
        return "skip"

    def should_process_sequence(self, sequence):
        """
        Determine if a sequence should be processed (has internal gaps)
        
        Args:
            sequence: DNA sequence string
            
        Returns:
            bool: True if sequence should be processed
        """
        return self.classify_sequence(sequence) == "process"
    
    def fill_gaps_in_sequence(self, sequence):
        """
        Fill gaps in a single sequence using the gap filling algorithm (FIXED VERSION).

        Args:
            sequence: Input DNA sequence with N's

        Returns:
            tuple: (filled_sequence, metadata)
        """
        try:
            # Get original N regions for reporting
            original_regions = get_consecutive_N_regions(sequence)
            original_gaps = len(original_regions)

            # Reduce N positions (limit gaps to max_n_per_region)
            reduced_sequence = reduce_N_positions(sequence, max_N=self.max_n_per_region)

            # Get reduced N regions
            reduced_regions = get_consecutive_N_regions(reduced_sequence)

            if not reduced_regions:
                # No gaps to fill after reduction
                return sequence, {
                    'gaps_processed': 0,
                    'gaps_filled': 0,
                    'zero_count_kmers': get_kmer_count_zero(sequence, self.kmer_size, self.db)
                }

            # Process all gap regions
            all_results = polish_all_gap_regions(
                reduced_sequence,
                reduced_regions,
                self.kmer_size,
                self.db,
                self.top_n
            )

            # Apply all polish results to get filled sequence
            filled_sequence = apply_all_polish_results(reduced_sequence, all_results)

            # Count successful fills
            successful_fills = sum(1 for result in all_results.values()
                                 if result['best_result'] is not None)

            # Calculate zero-count k-mers in final sequence
            zero_count = get_kmer_count_zero(filled_sequence, self.kmer_size, self.db)

            # ========================================
            # ✅ 正确的逻辑：直接返回填充后的缩减序列
            # ========================================
            # reduce_N_positions 删除了超过max_N的N字符
            # gap filling 在这条缩减后的序列上进行
            # 最终结果就是这条缩减后的序列（更短）
            filled_sequence_final = filled_sequence

            return filled_sequence_final, {
                'gaps_processed': original_gaps,
                'gaps_filled': successful_fills,
                'zero_count_kmers': zero_count
            }
            
        except Exception as e:
            print(f"⚠️ 处理序列时出错: {e}")
            # 如果处理失败，返回原始序列
            return sequence, {
                'gaps_processed': 0,
                'gaps_filled': 0,
                'zero_count_kmers': 0
            }

    def process_fasta_file(self, input_path, output_path):
        """
        Process a FASTA file and fill gaps in eligible sequences (SINGLE THREAD VERSION - FIXED).

        Args:
            input_path: Path to input FASTA file
            output_path: Path to output FASTA file
        """
        print(f"\n📝 单线程版本处理 FASTA 文件: {input_path}")
        print(f"输出将写入: {output_path}")

        # Initialize FASTA reader
        try:
            fasta = pyfastx.Fasta(input_path)
            total_sequences = len(fasta)
            self.stats['total_sequences'] = total_sequences
            print(f"📊 在输入文件中找到 {total_sequences} 个序列")
        except Exception as e:
            print(f"❌ 读取 FASTA 文件 {input_path} 时出错: {e}")
            sys.exit(1)

        # ========================================
        # 📝 单线程版本处理序列
        # ========================================
        processed_sequences = []
        error_count = 0

        with tqdm(total=total_sequences, desc="单线程处理序列", unit="seq") as pbar:
            for i in range(total_sequences):
                try:
                    # Get sequence name and sequence
                    name = fasta[i].name
                    sequence = str(fasta[i].seq)
                    print(f"Processing sequence: {name}")
                    # Update progress bar description with current sequence
                    current_name = name.split()[0][:20]
                    pbar.set_postfix({'current': current_name})

                    # Classify sequence for processing
                    seq_type = self.classify_sequence(sequence)
                    
                    if seq_type == "process":
                        # Process the sequence (has internal gaps)
                        filled_sequence, metadata = self.fill_gaps_in_sequence(sequence)
                        
                        # Update statistics
                        self.stats['processed_sequences'] += 1
                        self.stats['total_gaps_filled'] += metadata['gaps_processed']
                        self.stats['successful_fills'] += metadata['gaps_filled']
                        
                        # Create new header with processing info
                        new_header = f"{name} gaps_filled={metadata['gaps_filled']}/{metadata['gaps_processed']} zero_count={metadata['zero_count_kmers']}"
                        
                        # Store processed sequence
                        processed_sequences.append((new_header, filled_sequence))
                        
                    elif seq_type == "too_many_end_n":
                        # Sequence with >3 N's at start or end - print original
                        self.stats['too_many_end_n'] += 1
                        processed_sequences.append((name, sequence))
                        
                    elif seq_type == "no_n":
                        # Sequence with no N's - print original
                        self.stats['no_n_sequences'] += 1
                        processed_sequences.append((name, sequence))
                        
                    elif seq_type == "skip":
                        # Sequence with only small end N's (<=3) - skip processing
                        self.stats['skipped_no_gaps'] += 1
                        processed_sequences.append((name, sequence))

                except Exception as e:
                    error_count += 1
                    print(f"⚠️ 处理序列 {i+1}/{total_sequences} 时出错: {e}")
                    # 继续处理下一个序列
                
                finally:
                    pbar.update(1)

        # 报告错误统计
        if error_count > 0:
            print(f"⚠️ 总共处理了 {error_count} 个序列时出现错误，但程序继续执行")

        # Write output FASTA file
        print(f"\n💾 写入 {len(processed_sequences)} 个处理过的序列到 {output_path}")
        try:
            with open(output_path, 'w') as f:
                for header, sequence in processed_sequences:
                    f.write(f">{header}\n")
                    # Write sequence in lines of 80 characters
                    for i in range(0, len(sequence), 80):
                        f.write(f"{sequence[i:i+80]}\n")
                    f.write("\n")
            print(f"✅ 成功写入输出文件")
        except Exception as e:
            print(f"❌ 写入输出文件时出错: {e}")
            sys.exit(1)

        # Print final statistics
        self.print_statistics()

    def print_statistics(self):
        """Print processing statistics"""
        print("\n📊 处理统计:")
        print(f"  总序列数: {self.stats['total_sequences']}")
        print(f"  进行填充处理的序列: {self.stats['processed_sequences']}")
        print(f"  跳过的序列 (仅末端N≤3): {self.stats['skipped_no_gaps']}")
        print(f"  跳过序列 (开头/结尾>3个N): {self.stats['too_many_end_n']}")
        print(f"  跳过序列 (无N): {self.stats['no_n_sequences']}")
        print(f"  总gap数: {self.stats['total_gaps_filled']}")
        print(f"  成功填充的gap数: {self.stats['successful_fills']}")
        
        if self.stats['processed_sequences'] > 0:
            success_rate = (self.stats['successful_fills'] / self.stats['processed_sequences']) * 100
            print(f"  成功率: {success_rate:.1f}%")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="FASTA Gap Filling Batch Processor (Single Thread Version - FIXED)",
        epilog="""
使用示例:
  %(prog)s --input input.fa --output output.fa --db database.rkdb
  %(prog)s -i input.fa -o output.fa -d database.rkdb --max-n 15 --top-n 2000

处理规则:
- 有内部gap的序列: 使用k-mer算法填充gap
- 开头/结尾>3个N的序列: 直接输出原始序列
- 没有N的序列: 直接输出原始序列  
- 仅末端N≤3的序列: 直接输出原始序列

修复内容:
- 修复列表索引越界错误
- 增强边界检查逻辑
- 改进序列映射算法
- 添加智能序列过滤机制
- 统一输出所有序列

特性:
- 单线程处理，简单可靠
- 智能序列分类处理
- 适合小文件或调试使用
- 清晰的进度显示
- 完整的统计信息
- 强化的错误处理
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='输入 FASTA 文件路径'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='输出 FASTA 文件路径'
    )
    
    parser.add_argument(
        '--database', '-d',
        required=True,
        help='k-mer 数据库文件路径'
    )
    
    parser.add_argument(
        '--kmer-size',
        type=int,
        default=19,
        help='k-mer 大小 (默认: 19)'
    )
    
    parser.add_argument(
        '--max-n',
        type=int,
        default=11,
        help='每个区域最大 N 数量 (默认: 11)'
    )
    
    parser.add_argument(
        '--top-n',
        type=int,
        default=1000,
        help='考虑的前 N 个匹配 (默认: 1000)'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not Path(args.input).exists():
        print(f"❌ 输入文件不存在: {args.input}")
        sys.exit(1)
    
    # Check if database file exists
    if not Path(args.database).exists():
        print(f"❌ 数据库文件不存在: {args.database}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize processor
    processor = FastaGapProcessor(
        database_path=args.database,
        kmer_size=args.kmer_size,
        max_n_per_region=args.max_n,
        top_n=args.top_n
    )
    
    # Process the FASTA file
    try:
        processor.process_fasta_file(args.input, args.output)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断处理")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
