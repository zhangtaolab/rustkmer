#!/usr/bin/env python3
"""
PyO3版本的标记脚本 - 使用统一接口优化性能
基于K19数据库查询19mer count，只有被count>0的19mer覆盖的位置才是正确的，
其他位置标记为N

优化特性：
- 使用PyO3统一接口 (PyDatabase)
- 支持LoadMode选择优化内存使用
- 支持批量查询提高性能
- 更好的内存监控和错误处理

Author: RustKmer Team
Date: 2025-12-22
"""

import pyfastx
import argparse
import sys
import os
import time
from pathlib import Path
from tqdm import tqdm

try:
    import rustkmer_pyo3
except ImportError as e:
    print(f"❌ 无法导入 rustkmer_pyo3 模块: {e}")
    print("💡 请确保已正确构建 PyO3 扩展:")
    print("   cd rustkmer/pyo3")
    print("   export RUSTFLAGS='-C link-arg=-undefined -C link-arg=dynamic_lookup'")
    print("   export PYO3_PYTHON=/usr/bin/python3")
    print("   cargo build --release")
    print("   export PYTHONPATH='$PWD/target/release:$PYTHONPATH'")
    sys.exit(1)


class PyO3MarkNProcessor:
    """PyO3版本的N标记处理器"""
    
    def __init__(self, database_path: str, load_mode=rustkmer_pyo3.LoadMode.Preload):
        """
        初始化PyO3标记处理器
        
        Args:
            database_path: 数据库文件路径
            load_mode: 加载模式 (Preload/MemoryMapped/Lazy)
        """
        self.database_path = database_path
        self.load_mode = load_mode
        self.db = None
        self.kmer_size = None
        
        try:
            # 使用PyO3统一接口创建数据库实例
            self.db = rustkmer_pyo3.PyDatabase(database_path, load_mode)
            print(f"✅ 成功加载数据库: {database_path}")
            print(f"   加载模式: {load_mode}")
            
            # 获取数据库信息
            db_info = self.db.database_info()
            self.kmer_size = int(db_info['kmer_size'])
            print(f"   K-mer大小: {self.kmer_size}")
            print(f"   数据库路径: {db_info['database_path']}")
            
            # 显示内存使用情况
            memory_info = self.db.get_memory_usage()
            print(f"   内存使用: {memory_info}")
            
            # 验证k-mer大小是否为19
            if self.kmer_size != 19:
                print(f"⚠️  警告: 数据库k-mer大小为 {self.kmer_size}，脚本期望为19")
                print(f"   将使用实际的k-mer大小: {self.kmer_size}")
                
        except Exception as e:
            print(f"❌ 数据库加载失败: {e}")
            raise
    
    def trim_end_n_bases(self, sequence: str):
        """
        去除序列开头和结尾的'N'，只保留中间的'N'
        
        Args:
            sequence: 输入序列
            
        Returns:
            (trimmed_seq, trimmed_info): 去除头尾N后的序列和修剪信息
        """
        if not sequence:
            return sequence, {'start_trimmed': 0, 'end_trimmed': 0, 'total_trimmed': 0}
        
        # 去除开头的'N'
        start_idx = 0
        while start_idx < len(sequence) and sequence[start_idx] == 'N':
            start_idx += 1
        
        # 去除结尾的'N'
        end_idx = len(sequence) - 1
        while end_idx >= start_idx and sequence[end_idx] == 'N':
            end_idx -= 1
        
        # 提取中间部分
        if start_idx > end_idx:
            # 整个序列都是N，返回空序列
            trimmed_seq = ""
        else:
            trimmed_seq = sequence[start_idx:end_idx + 1]
        
        trimmed_info = {
            'start_trimmed': start_idx,
            'end_trimmed': len(sequence) - 1 - end_idx,
            'total_trimmed': start_idx + (len(sequence) - 1 - end_idx)
        }
        
        return trimmed_seq, trimmed_info
    
    def mark_problem_regions_single(self, sequence: str):
        """
        标记单个序列中的问题区域（单查询版本）
        自动去除开头和结尾的'N'，只保留中间的'N'
        
        Args:
            sequence: 输入序列
            
        Returns:
            (marked_seq, stats): 修剪后的序列和详细统计信息（包含修剪前后的数据）
        """
        seq_len = len(sequence)
        kmer_size = self.kmer_size
        
        # 初始化所有位置为错误（用N标记）
        marked_seq = ['N'] * seq_len
        
        # 用集合记录被正确占位的位置
        correct_positions = set()
        
        # 第一步：用对的kmer去占位
        # 找出所有count>0的kmer，并记录它们覆盖的位置
        for i in range(seq_len - kmer_size + 1):
            kmer = sequence[i:i + kmer_size]
            if 'N' not in kmer:  # 跳过包含N的kmer
                try:
                    # 使用PyO3统一接口进行精确查询
                    result = self.db.query_exact(kmer)
                    if result.found and result.count > 0:
                        # 这个kmer覆盖的kmer_size个位置都是正确的
                        for j in range(i, i + kmer_size):
                            correct_positions.add(j)
                except Exception as e:
                    # 查询失败时视为count=0
                    continue
        
        # 第二步：应用占位结果
        # 只有被count>0的kmer覆盖的位置才是正确的
        for pos in range(seq_len):
            if pos in correct_positions:
                marked_seq[pos] = sequence[pos]  # 用原始序列的大写字母
            else:
                marked_seq[pos] = 'N'  # 问题位置
        
        # 合并所有字符
        final_marked_seq = ''.join(marked_seq)
        
        # 去除开头和结尾的'N'，只保留中间的'N'
        trimmed_seq, trim_info = self.trim_end_n_bases(final_marked_seq)
        
        # 重新计算统计信息（基于修剪后的序列）
        trimmed_len = len(trimmed_seq)
        if trimmed_len > 0:
            # 计算修剪后序列中的正确和问题碱基数
            trimmed_correct = 0
            trimmed_problem = 0
            
            # 找到原始序列中对应的位置
            start_pos = trim_info['start_trimmed']
            for i, base in enumerate(trimmed_seq):
                if base != 'N':
                    trimmed_correct += 1
                else:
                    trimmed_problem += 1
        else:
            trimmed_correct = 0
            trimmed_problem = 0
        
        # 原始统计信息
        original_correct = len(correct_positions)
        original_problem = seq_len - original_correct
        
        stats = {
            'original_total': seq_len,
            'original_correct': original_correct,
            'original_problem': original_problem,
            'original_correct_percentage': (original_correct / seq_len) * 100 if seq_len > 0 else 0,
            'original_problem_percentage': (original_problem / seq_len) * 100 if seq_len > 0 else 0,
            'trimmed_total': trimmed_len,
            'trimmed_correct': trimmed_correct,
            'trimmed_problem': trimmed_problem,
            'trimmed_correct_percentage': (trimmed_correct / trimmed_len) * 100 if trimmed_len > 0 else 0,
            'trimmed_problem_percentage': (trimmed_problem / trimmed_len) * 100 if trimmed_len > 0 else 0,
            'start_trimmed': trim_info['start_trimmed'],
            'end_trimmed': trim_info['end_trimmed'],
            'total_trimmed': trim_info['total_trimmed']
        }
        
        return trimmed_seq, stats
    
    def mark_problem_regions_batch(self, sequence: str, batch_size=1000):
        """
        标记单个序列中的问题区域（批量查询版本）
        自动去除开头和结尾的'N'，只保留中间的'N'
        
        Args:
            sequence: 输入序列
            batch_size: 批量查询的大小
            
        Returns:
            (marked_seq, stats): 修剪后的序列和详细统计信息（包含修剪前后的数据）
        """
        seq_len = len(sequence)
        kmer_size = self.kmer_size
        
        # 初始化所有位置为错误（用N标记）
        marked_seq = ['N'] * seq_len
        
        # 用集合记录被正确占位的位置
        correct_positions = set()
        
        # 收集所有kmer进行批量查询
        kmers = []
        positions = []
        
        for i in range(seq_len - kmer_size + 1):
            kmer = sequence[i:i + kmer_size]
            if 'N' not in kmer:  # 跳过包含N的kmer
                kmers.append(kmer)
                positions.append(i)
        
        # 批量查询
        if kmers:
            try:
                # 使用批量查询
                batch_results = self.db.query_exact_batch(kmers)
                
                # 处理批量结果
                for kmer, result, pos in zip(kmers, batch_results, positions):
                    if result.found and result.count > 0:
                        # 这个kmer覆盖的kmer_size个位置都是正确的
                        for j in range(pos, pos + kmer_size):
                            correct_positions.add(j)
                            
            except Exception as e:
                print(f"⚠️  批量查询失败，回退到单查询模式: {e}")
                # 回退到单查询模式
                return self.mark_problem_regions_single(sequence)
        
        # 应用占位结果
        for pos in range(seq_len):
            if pos in correct_positions:
                marked_seq[pos] = sequence[pos]  # 用原始序列的大写字母
            else:
                marked_seq[pos] = 'N'  # 问题位置
        
        # 合并所有字符
        final_marked_seq = ''.join(marked_seq)
        
        # 去除开头和结尾的'N'，只保留中间的'N'
        trimmed_seq, trim_info = self.trim_end_n_bases(final_marked_seq)
        
        # 重新计算统计信息（基于修剪后的序列）
        trimmed_len = len(trimmed_seq)
        if trimmed_len > 0:
            # 计算修剪后序列中的正确和问题碱基数
            trimmed_correct = 0
            trimmed_problem = 0
            
            # 找到原始序列中对应的位置
            start_pos = trim_info['start_trimmed']
            for i, base in enumerate(trimmed_seq):
                if base != 'N':
                    trimmed_correct += 1
                else:
                    trimmed_problem += 1
        else:
            trimmed_correct = 0
            trimmed_problem = 0
        
        # 原始统计信息
        original_correct = len(correct_positions)
        original_problem = seq_len - original_correct
        
        stats = {
            'original_total': seq_len,
            'original_correct': original_correct,
            'original_problem': original_problem,
            'original_correct_percentage': (original_correct / seq_len) * 100 if seq_len > 0 else 0,
            'original_problem_percentage': (original_problem / seq_len) * 100 if seq_len > 0 else 0,
            'trimmed_total': trimmed_len,
            'trimmed_correct': trimmed_correct,
            'trimmed_problem': trimmed_problem,
            'trimmed_correct_percentage': (trimmed_correct / trimmed_len) * 100 if trimmed_len > 0 else 0,
            'trimmed_problem_percentage': (trimmed_problem / trimmed_len) * 100 if trimmed_len > 0 else 0,
            'start_trimmed': trim_info['start_trimmed'],
            'end_trimmed': trim_info['end_trimmed'],
            'total_trimmed': trim_info['total_trimmed']
        }
        
        return trimmed_seq, stats
    
    def process_fasta_file(self, input_file: str, output_file: str, 
                          use_batch_query=False, batch_size=1000,
                          limit=None, show_progress=True):
        """
        处理FASTA文件
        
        Args:
            input_file: 输入FASTA文件路径
            output_file: 输出文件路径
            use_batch_query: 是否使用批量查询
            batch_size: 批量查询大小
            limit: 限制处理的序列数量
            show_progress: 是否显示进度条
        """
        # 检查文件是否存在
        if not os.path.exists(input_file):
            print(f"❌ 错误：输入文件不存在: {input_file}")
            return False
        
        # 统计序列总数
        try:
            fastx_obj = pyfastx.Fasta(input_file)
            total_seqs_in_file = len(fastx_obj)
            print(f"📊 检测到文件包含 {total_seqs_in_file} 条序列")
        except Exception as e:
            print(f"⚠️  警告：无法统计序列数量: {e}")
            total_seqs_in_file = 0
        
        # 处理参数
        actual_limit = limit if limit else total_seqs_in_file
        print(f"🎯 将处理 {actual_limit} 条序列")
        
        if use_batch_query:
            print(f"📦 使用批量查询模式 (批次大小: {batch_size})")
        else:
            print("🔍 使用单查询模式")
        
        # 开始处理
        total_sequences = 0
        total_problem_bases = 0
        total_bases = 0
        start_time = time.time()
        
        with open(output_file, 'w') as out_f:
            # 创建进度条
            with tqdm(total=actual_limit if actual_limit > 0 else None,
                      desc="处理序列", unit="条", 
                      disable=not show_progress) as pbar:
                
                for seq_idx, fasta_seq in enumerate(pyfastx.Fasta(input_file)):
                    # 检查限制
                    if limit and seq_idx >= limit:
                        break
                    
                    # 选择处理方法
                    if use_batch_query and len(fasta_seq.seq) > batch_size * 2:
                        # 长序列使用批量查询
                        marked_seq, stats = self.mark_problem_regions_batch(fasta_seq.seq, batch_size)
                    else:
                        # 短序列使用单查询
                        marked_seq, stats = self.mark_problem_regions_single(fasta_seq.seq)
                    
                    # 写入结果
                    out_f.write(f">{fasta_seq.name}\n")
                    out_f.write(f"{marked_seq}\n")
                    
                    # 统计（使用修剪后的统计信息）
                    total_sequences += 1
                    total_problem_bases += stats['trimmed_problem']
                    total_bases += stats['trimmed_total']
                    
                    # 更新进度条
                    pbar.update(1)
                    
                    # 添加进度描述
                    if total_sequences > 0:
                        elapsed_time = time.time() - start_time
                        avg_time_per_seq = elapsed_time / total_sequences
                        
                        if actual_limit > 0:
                            percentage = (total_sequences / actual_limit) * 100
                            remaining_seqs = max(0, actual_limit - total_sequences)
                            estimated_remaining = remaining_seqs * avg_time_per_seq
                            
                            if estimated_remaining > 60:
                                eta = f"{estimated_remaining/60:.1f}分钟"
                            else:
                                eta = f"{estimated_remaining:.0f}秒"
                            
                            pbar.set_description(f"处理序列 ({percentage:.1f}%) ETA: {eta}")
                        else:
                            pbar.set_description(f"处理序列 ({total_sequences})")
        
        # 输出总体统计
        print(f"\n✅ 处理完成！")
        print(f"📈 性能统计:")
        print(f"   总序列数: {total_sequences}")
        print(f"   修剪后总碱基数: {total_bases:,}")
        print(f"   修剪后问题碱基数: {total_problem_bases:,}")
        print(f"   修剪后正确碱基数: {total_bases - total_problem_bases:,}")
        
        if total_bases > 0:
            problem_ratio = total_problem_bases/total_bases*100
            correct_ratio = (total_bases - total_problem_bases)/total_bases*100
            print(f"   修剪后问题比例: {problem_ratio:.2f}%")
            print(f"   修剪后正确比例: {correct_ratio:.2f}%")
        
        print(f"   📋 说明: 已自动去除序列开头和结尾的'N'，只保留中间的'N'")
        
        # 显示内存使用情况
        try:
            final_memory = self.db.get_memory_usage()
            print(f"💾 最终内存使用: {final_memory}")
        except Exception:
            pass
        
        print(f"💾 结果已保存到: {output_file}")
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PyO3版本 - 标记序列中的问题区域（基于K19数据库）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PyO3优化特性:
✅ 使用统一PyDatabase接口，内存效率更高
✅ 支持LoadMode选择 (Preload/MemoryMapped/Lazy)
✅ 支持批量查询提高性能
✅ 智能模式选择（长序列批量，短序列单查询）
✅ 更好的内存监控和错误处理

标记规则:
1. 查询序列中所有k-mer在数据库中的count
2. count=0的k-mer覆盖的位置被视为问题
3. 问题区域用N标记
4. 正确区域用原始碱基表示

示例用法:
    python mark_N_script_pyo3.py
    python mark_N_script_pyo3.py -i Chr10_.fasta -o Chr10_marked.fa
    python mark_N_script_pyo3.py -d /path/to/database.rkdb --batch-query
    python mark_N_script_pyo3.py --load-mode MemoryMapped --batch-size 2000
        """
    )

    parser.add_argument('-i', '--input', default='Chr10_.fasta',
                      help='输入FASTA文件（默认: Chr10_demo.fasta）')
    parser.add_argument('-o', '--output', default='Chr10_demo_marked_pyo3.fa',
                      help='输出文件（标记后的序列，默认: Chr10_marked_pyo3.fa）')
    parser.add_argument('-d', '--database', 
                      help='数据库路径 (.rkdb文件，优先使用环境变量或默认路径)')
    
    # 添加数据库路径搜索
    default_db_paths = [
        '/Users/forrest/Data/data/kmer/K19/R1_001.rkdb',
        '/Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb',
        'python/tests/test_data/tiny_test.rkdb',
    ]
    
    # PyO3相关参数
    parser.add_argument('--load-mode', 
                      choices=['Preload', 'MemoryMapped', 'Lazy'],
                      default='Preload',
                      help='数据库加载模式 (默认: Preload)')
    parser.add_argument('--batch-query', action='store_true',
                      help='启用批量查询模式（提高长序列性能）')
    parser.add_argument('--batch-size', type=int, default=1000,
                      help='批量查询大小 (默认: 1000)')
    
    # 通用参数
    parser.add_argument('--show-progress', action='store_true', default=True,
                      help='显示处理进度（默认开启）')
    parser.add_argument('--no-progress', action='store_true',
                      help='关闭进度显示')
    parser.add_argument('--limit', type=int,
                      help='限制处理的序列数量（用于测试）')

    args = parser.parse_args()

    # 寻找数据库文件
    database_path = args.database
    if not database_path:
        # 尝试环境变量
        database_path = os.environ.get('RUSTKMER_DB_PATH')
        
        if not database_path:
            # 尝试默认路径
            for db_path in default_db_paths:
                if os.path.exists(db_path):
                    database_path = db_path
                    break
    
    if not database_path:
        print("❌ 未找到数据库文件")
        print("请指定数据库路径:")
        print("  python mark_N_script_pyo3.py -d /path/to/database.rkdb")
        print("  或设置环境变量: export RUSTKMER_DB_PATH=/path/to/database.rkdb")
        print("\n可用的默认路径:")
        for db_path in default_db_paths:
            print(f"  - {db_path}")
        return 1

    if not os.path.exists(database_path):
        print(f"❌ 错误：数据库文件不存在: {database_path}")
        return 1

    print(f"🚀 启动PyO3版本标记脚本")
    print(f"📂 数据库: {database_path}")
    print(f"📝 输入文件: {args.input}")
    print(f"💾 输出文件: {args.output}")
    print(f"⚙️  加载模式: {args.load_mode}")
    
    try:
        # 创建PyO3处理器
        processor = PyO3MarkNProcessor(
            database_path=database_path,
            load_mode=getattr(rustkmer_pyo3.LoadMode, args.load_mode)
        )
        
        # 处理文件
        success = processor.process_fasta_file(
            input_file=args.input,
            output_file=args.output,
            use_batch_query=args.batch_query,
            batch_size=args.batch_size,
            limit=args.limit,
            show_progress=not args.no_progress
        )
        
        if success:
            print(f"\n🎉 PyO3标记脚本执行成功！")
            print(f"📊 使用了统一PyDatabase接口，内存效率更高")
            if args.batch_query:
                print(f"📦 启用了批量查询，性能更优")
        else:
            print(f"\n❌ 处理失败")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了处理")
        return 1
    except Exception as e:
        print(f"\n❌ 处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
