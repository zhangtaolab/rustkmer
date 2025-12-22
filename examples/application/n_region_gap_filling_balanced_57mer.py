#!/usr/bin/env python3
"""
FASTA Gap Filling with Balanced 57-mer Patterns

This script implements gap filling for FASTA sequences using PyO3 unified interface,
focusing on balanced 57-mer hybrid pattern construction with N regions centered.

Key Features:
- Balanced allocation of flanking sequences around N regions
- 57-mer pattern construction with strict length constraints
- PyO3 unified interface integration with K57 database
- Intelligent result filtering prioritizing minimal polymers
- Comprehensive boundary constraint handling

Author: RustKmer Team
Date: 2025-12-22
"""

import pyfastx
import argparse
import sys
import os
from pathlib import Path
from tqdm import tqdm
# from collections import defaultdict  # Not currently used

try:
    import rustkmer_pyo3
except ImportError as e:
    print(f"❌ 无法导入 rustkmer_pyo3 模块: {e}")
    print("💡 请确保已正确构建 PyO3 扩展")
    sys.exit(1)


def reduce_N_positions(seq, max_N=43):
    """
    Reduce the number of N's in each consecutive N region to max_N.
    If a region has fewer than max_N N's, it remains unchanged.
    If a region has more than max_N N's, it's truncated to max_N N's.
    """
    N_regions = get_consecutive_N_regions(seq)
    if not N_regions:
        return seq
    
    # Convert sequence to list for easier manipulation
    seq_list = list(seq)
    
    # Process each N region, accounting for index changes due to deletions
    offset = 0  # Track how many characters have been removed so far
    for region in N_regions:
        nstart = region['nstart'] - offset  # Adjust for previous deletions
        nend = region['nend'] - offset
        region_length = nend - nstart + 1
        
        if region_length > max_N:
            # Remove N's beyond max_N
            # This effectively shortens the sequence by removing these N's
            del seq_list[nstart + max_N : nend + 1]
            offset += (region_length - max_N)  # Update offset for next iteration
    
    return ''.join(seq_list)


def get_consecutive_N_regions(seq):
    """
    Identify consecutive N regions in a sequence and return them as dictionaries.
    
    Returns:
        A list of dictionaries, where each dictionary contains 'nstart' and 'nend' keys
        representing start and end positions of a consecutive N region.
        If there are no N's, returns an empty list.
    """
    N_positions = [i for i, c in enumerate(seq) if c == 'N']
    if not N_positions:
        return []
    
    # Group consecutive N positions and create dictionaries for each region
    regions = []
    nstart = N_positions[0]
    nend = N_positions[0]
    
    for i in range(1, len(N_positions)):
        if N_positions[i] == N_positions[i-1] + 1:  # Consecutive N
            nend = N_positions[i]
        else:
            regions.append({'nstart': nstart, 'nend': nend})
            nstart = N_positions[i]
            nend = N_positions[i]
    
    regions.append({'nstart': nstart, 'nend': nend})  # Add the last region
    return regions


def count_polymers(seq):
    """
    Calculate the number of polymers (consecutive identical nucleotides) in a sequence.
    
    Args:
        seq: DNA sequence string
        
    Returns:
        int: Total number of polymers in the sequence
    """
    if not seq:
        return 0
    
    polymers = 0
    i = 0
    while i < len(seq):
        if seq[i] in ['A', 'C', 'G', 'T']:
            current_base = seq[i]
            j = i + 1
            while j < len(seq) and seq[j] == current_base:
                j += 1
            if j - i >= 2:  # Found a polymer of length >= 2
                polymers += 1
            i = j
        else:
            i += 1
    
    return polymers


def handle_boundary_constraints(seq, nstart, nend, desired_upstream, desired_downstream):
    """
    Handle sequence boundary constraints and return the best feasible allocation.
    
    Args:
        seq: Original sequence
        nstart: N region start position
        nend: N region end position
        desired_upstream: Desired upstream length
        desired_downstream: Desired downstream length
        
    Returns:
        tuple: (feasible_upstream, feasible_downstream, constraint_info)
    """
    max_upstream = nstart
    max_downstream = len(seq) - nend - 1
    
    constraint_info = {
        'upstream_constrained': False,
        'downstream_constrained': False,
        'total_constrained': False,
        'adjustment_made': '',
        'balance_maintained': True
    }
    
    # Check constraints
    if desired_upstream > max_upstream:
        constraint_info['upstream_constrained'] = True
        constraint_info['adjustment_made'] = 'upstream_trimmed'
    
    if desired_downstream > max_downstream:
        constraint_info['downstream_constrained'] = True
        constraint_info['adjustment_made'] = 'downstream_trimmed'
    
    feasible_upstream = min(desired_upstream, max_upstream)
    feasible_downstream = min(desired_downstream, max_downstream)
    
    # Check total length constraint
    total_feasible = feasible_upstream + feasible_downstream
    total_desired = desired_upstream + desired_downstream
    
    if total_feasible < total_desired:
        constraint_info['total_constrained'] = True
        constraint_info['adjustment_made'] = 'total_trimmed'
        
        # Try to maintain balance under constraints
        if constraint_info['upstream_constrained'] and not constraint_info['downstream_constrained']:
            feasible_downstream = total_feasible - feasible_upstream
        elif constraint_info['downstream_constrained'] and not constraint_info['upstream_constrained']:
            feasible_upstream = total_feasible - feasible_downstream
        else:
            # Both sides constrained, use average allocation
            feasible_upstream = total_feasible // 2
            feasible_downstream = total_feasible - feasible_upstream
    
    # Check balance
    balance_diff = abs(feasible_upstream - feasible_downstream)
    constraint_info['balance_maintained'] = balance_diff <= 1
    
    return feasible_upstream, feasible_downstream, constraint_info


def build_progressive_57mer_pattern(seq, nstart, nend, initial_n_length=None, verbose=True):
    """
    Build balanced 57-mer pattern with progressive fallback strategy.
    Start with smaller N lengths and only increase if query fails.
    
    Args:
        seq: Original sequence
        nstart: N region start position
        nend: N region end position
        initial_n_length: Initial N length to try (default: try smaller values first)
        verbose: Whether to print detailed information
        
    Returns:
        tuple: (pattern, upstream_seq, downstream_seq, n_length, balance_info, used_fallback)
    """
    original_n_length = nend - nstart + 1
    
    # Start with smaller N lengths and progressively increase
    if initial_n_length is None:
        # Start with small N lengths and increase
        n_lengths_to_try = []
        # Try lengths from 3 up to min(original_n_length, 43)
        max_n = min(original_n_length, 43)
        for n_len in range(3, max_n + 1, 4):  # Start small, increase by 4
            n_lengths_to_try.append(n_len)
        
        # Also try the capped length if different
        capped_length = min(original_n_length, 43)
        if capped_length not in n_lengths_to_try:
            n_lengths_to_try.append(capped_length)
    else:
        n_lengths_to_try = [initial_n_length]
    
    # Check available flanking sequence
    max_upstream_available = nstart
    max_downstream_available = len(seq) - nend - 1
    available_flanking_total = max_upstream_available + max_downstream_available
    
    if available_flanking_total < 6:  # Need at least 3+3 for flanking sequences
        # Not enough space for flanking sequences, fall back to balanced approach
        return build_balanced_57mer_pattern(seq, nstart, nend, verbose=False)
    
    for current_n_length in n_lengths_to_try:
        # Calculate flanking sequence lengths for balance
        remaining_length = 57 - current_n_length
        target_upstream = remaining_length // 2
        target_downstream = remaining_length - target_upstream
        
        # Use available flanking sequence
        upstream_length = min(target_upstream, max_upstream_available)
        downstream_length = min(target_downstream, max_downstream_available)
        
        # Ensure minimum flanking lengths
        if upstream_length < 3:
            upstream_length = min(3, max_upstream_available)
        if downstream_length < 3:
            downstream_length = min(3, max_downstream_available)
        
        # Calculate total length
        actual_total = upstream_length + current_n_length + downstream_length
        
        if actual_total <= 57:
            # Extract sequences
            upstream_seq = seq[nstart - upstream_length:nstart]
            downstream_seq = seq[nend + 1:nend + 1 + downstream_length]
            
            # Verify we have valid sequences
            if len(upstream_seq) == upstream_length and len(downstream_seq) == downstream_length:
                # Build pattern
                pattern = f"{upstream_seq}{{N{current_n_length}}}{downstream_seq}"
                
                balance_info = {
                    'n_length': current_n_length,
                    'upstream_length': len(upstream_seq),
                    'downstream_length': len(downstream_seq),
                    'balance_score': abs(len(upstream_seq) - len(downstream_seq)),
                    'center_position': (len(upstream_seq) + current_n_length / 2) / 57,
                    'used_fallback': current_n_length > (n_lengths_to_try[0] if n_lengths_to_try else 3)
                }
                
                if verbose:
                    fallback_note = " (使用回退策略)" if balance_info['used_fallback'] else ""
                    print(f"    🔄 渐进式Pattern: {pattern}{fallback_note}")
                    print(f"    📊 分解: 上游({len(upstream_seq)}) + N({current_n_length}) + 下游({len(downstream_seq)}) = {len(upstream_seq) + current_n_length + len(downstream_seq)}")
                    print(f"    ⚖️  平衡性: 分数={balance_info['balance_score']}, 中心位置={balance_info['center_position']:.3f}")
                
                return pattern, upstream_seq, downstream_seq, current_n_length, balance_info
    
    # If no progressive pattern works, try balanced approach
    return build_balanced_57mer_pattern(seq, nstart, nend, verbose=False)


def build_balanced_57mer_pattern(seq, nstart, nend, verbose=True):
    """
    Build balanced 57-mer pattern with N region centered.
    
    Args:
        seq: Original sequence
        nstart: N region start position
        nend: N region end position
        verbose: Whether to print detailed information
        
    Returns:
        tuple: (pattern, upstream_seq, downstream_seq, n_length, balance_info)
    """
    # 1. Determine N region length
    n_length = min(nend - nstart + 1, 43)  # Max 43 N's
    
    # 2. Calculate target flanking lengths (prioritize balanced allocation)
    target_total_flanking = 57 - n_length
    target_upstream = target_total_flanking // 2
    target_downstream = target_total_flanking - target_upstream
    
    # 3. Get available sequence lengths
    max_upstream_available = nstart  # Maximum available length on left
    max_downstream_available = len(seq) - nend - 1  # Maximum available length on right
    
    # 4. Balanced allocation strategy
    balance_info = {
        'ideal_upstream': target_upstream,
        'ideal_downstream': target_downstream,
        'actual_upstream': 0,
        'actual_downstream': 0,
        'balance_score': 0,
        'allocation_strategy': '',
        'center_position': 0.0
    }
    
    # Strategy 1: Ideal balanced allocation
    if max_upstream_available >= target_upstream and max_downstream_available >= target_downstream:
        upstream_seq = seq[nstart - target_upstream:nstart]
        downstream_seq = seq[nend + 1:nend + 1 + target_downstream]
        balance_info['allocation_strategy'] = 'perfect_balance'
        balance_info['balance_score'] = 0
        
    # Strategy 2: One side insufficient, extend from the other side (keep N region centered)
    elif max_upstream_available < target_upstream and max_downstream_available >= target_upstream:
        # Left side insufficient, extend right side
        total_available = max_upstream_available + max_downstream_available
        if total_available >= target_total_flanking:
            upstream_seq = seq[0:nstart]  # Use all left sequences
            remaining_for_downstream = target_total_flanking - len(upstream_seq)
            downstream_seq = seq[nend + 1:nend + 1 + remaining_for_downstream]
            balance_info['allocation_strategy'] = 'left_extend_right'
        else:
            upstream_seq = seq[0:nstart]
            downstream_seq = seq[nend + 1:]
            balance_info['allocation_strategy'] = 'use_all_available'
            
    elif max_downstream_available < target_downstream and max_upstream_available >= target_downstream:
        # Right side insufficient, extend left side
        total_available = max_upstream_available + max_downstream_available
        if total_available >= target_total_flanking:
            downstream_seq = seq[nend + 1:]  # Use all right sequences
            remaining_for_upstream = target_total_flanking - len(downstream_seq)
            upstream_seq = seq[nstart - remaining_for_upstream:nstart]
            balance_info['allocation_strategy'] = 'right_extend_left'
        else:
            upstream_seq = seq[nstart - max_upstream_available:nstart]
            downstream_seq = seq[nend + 1:]
            balance_info['allocation_strategy'] = 'use_all_available'
    
    # Strategy 3: Both sides insufficient, use all available sequences
    else:
        total_available = max_upstream_available + max_downstream_available
        if total_available >= target_total_flanking:
            # Try to allocate as balanced as possible
            upstream_seq = seq[nstart - target_upstream:nstart]
            remaining_for_downstream = target_total_flanking - len(upstream_seq)
            downstream_seq = seq[nend + 1:nend + 1 + remaining_for_downstream]
            balance_info['allocation_strategy'] = 'insufficient_both_sides'
        else:
            # Extreme case: total length insufficient for 57-mer
            # Use all available sequences but pad with N's to reach 57
            upstream_seq = seq[0:nstart]
            downstream_seq = seq[nend + 1:]
            balance_info['allocation_strategy'] = 'extreme_shortage'
            
            # Calculate how many N's we need to add to reach 57
            current_total = len(upstream_seq) + n_length + len(downstream_seq)
            if current_total < 57:
                # Add extra N's to the N region to reach exactly 57
                n_length = 57 - len(upstream_seq) - len(downstream_seq)
                balance_info['n_length'] = n_length
    
    # 5. Calculate actual allocation and balance score
    actual_upstream = len(upstream_seq)
    actual_downstream = len(downstream_seq)
    actual_total = actual_upstream + n_length + actual_downstream
    
    # Balance score: absolute difference in upstream/downstream lengths (smaller is better)
    balance_score = abs(actual_upstream - actual_downstream)
    balance_info.update({
        'actual_upstream': actual_upstream,
        'actual_downstream': actual_downstream,
        'actual_total': actual_total,
        'balance_score': balance_score,
        'n_length': n_length,
        'center_position': (actual_upstream + n_length / 2) / 57
    })
    
    # 6. Build pattern with proper {N} syntax for hybrid search
    pattern = f"{upstream_seq}{{N{n_length}}}{downstream_seq}"
    
    # 6.1. Ensure pattern is exactly 57 characters long (accounting for {N} syntax)
    # Calculate actual pattern length without {N} syntax
    pattern_without_syntax = f"{upstream_seq}{'N' * n_length}{downstream_seq}"
    
    if len(pattern_without_syntax) != 57:
        # If pattern is too short, extend the N region
        if len(pattern_without_syntax) < 57:
            needed = 57 - len(pattern_without_syntax)
            n_length += needed
            pattern = f"{upstream_seq}{{N{n_length}}}{downstream_seq}"
        # If pattern is too long, truncate downstream sequence
        elif len(pattern_without_syntax) > 57:
            excess = len(pattern_without_syntax) - 57
            downstream_seq = downstream_seq[:-excess] if len(downstream_seq) > excess else ""
            pattern = f"{upstream_seq}{{N{n_length}}}{downstream_seq}"
    
    # Ensure we have exactly 57 characters
    final_pattern_check = f"{upstream_seq}{'N' * n_length}{downstream_seq}"
    if len(final_pattern_check) != 57:
        # Final fallback: adjust N region to make it exactly 57
        upstream_len = len(upstream_seq)
        downstream_len = len(downstream_seq)
        n_length = 57 - upstream_len - downstream_len
        if n_length < 1:
            n_length = 1  # At least 1 N
        pattern = f"{upstream_seq}{{N{n_length}}}{downstream_seq}"
    
    # 7. Validation and debugging information
    if verbose:
        print(f"  平衡分配信息:")
        print(f"    N区域: 位置{nstart}-{nend}, 长度{n_length}")
        print(f"    理想分配: 上游{target_upstream}, 下游{target_downstream}")
        print(f"    实际分配: 上游{actual_upstream}, 下游{actual_downstream}")
        print(f"    平衡分数: {balance_score} (越小越平衡)")
        print(f"    分配策略: {balance_info['allocation_strategy']}")
        print(f"    中心位置: {balance_info['center_position']:.3f} (0.5为理想中心)")
        
        # Print pattern in both formats for clarity
        actual_pattern = f"{upstream_seq}{'N' * n_length}{downstream_seq}"
        print(f"    查询Pattern: {pattern} (N语法)")
        print(f"    实际序列: {actual_pattern[:20]}...{actual_pattern[-20:]} (长度: {len(actual_pattern)})")
        print(f"    总长度验证: {len(actual_pattern)} = {len(upstream_seq)} + {n_length} + {len(downstream_seq)}")
    
    return pattern, upstream_seq, downstream_seq, n_length, balance_info


def select_best_filling_for_n_region(query_results, upstream_seq, n_length, downstream_seq):
    """
    Select the best filling result for a specific N region.
    
    Args:
        query_results: Results from query_hybrid
        upstream_seq: Upstream sequence
        n_length: N region length
        downstream_seq: Downstream sequence
        
    Returns:
        tuple: (best_fill_sequence, best_kmer, best_count, best_polymers)
    """
    if not query_results:
        return None, None, 0, float('inf')
    
    candidates = []
    
    for kmer, count_str in query_results.items():
        try:
            count = int(count_str)
            
            # Verify kmer matches the pattern
            if kmer.startswith(upstream_seq) and kmer.endswith(downstream_seq):
                # Extract filling sequence (remove upstream/downstream sequences)
                fill_sequence = kmer[len(upstream_seq):len(upstream_seq) + n_length]
                
                # Calculate polymers
                polymers = count_polymers(fill_sequence)
                
                candidates.append({
                    'kmer': kmer,
                    'fill_sequence': fill_sequence,
                    'count': count,
                    'polymers': polymers
                })
        except (ValueError, IndexError) as e:
            print(f"    ⚠️  处理kmer时出错: {e}")
            continue
    
    if not candidates:
        return None, None, 0, float('inf')
    
    # Sort by count (descending) then by polymers (ascending)
    candidates.sort(key=lambda x: (-x['count'], x['polymers']))
    best_candidate = candidates[0]
    
    return (best_candidate['fill_sequence'], 
            best_candidate['kmer'], 
            best_candidate['count'], 
            best_candidate['polymers'])


def apply_gap_filling(seq, nstart, nend, fill_sequence):
    """
    Apply filling sequence to the original sequence.
    
    Args:
        seq: Original sequence
        nstart: N region start position
        nend: N region end position
        fill_sequence: Filling sequence
        
    Returns:
        str: Sequence after gap filling
    """
    seq_list = list(seq)
    
    # Replace N region
    for i, nucleotide in enumerate(fill_sequence):
        pos = nstart + i
        if pos <= nend and pos < len(seq_list):
            seq_list[pos] = nucleotide
    
    return ''.join(seq_list)


class FastaGapFilling57merProcessor:
    """
    57-mer gap filling processor with balanced pattern allocation.
    """
    
    def __init__(self, database_path, load_mode=rustkmer_pyo3.LoadMode.Preload):
        """
        Initialize the gap filling processor.
        
        Args:
            database_path: Path to k-mer database file
            load_mode: PyO3 LoadMode (default: Preload)
        """
        self.database_path = database_path
        self.load_mode = load_mode
        self.db = None
        
        try:
            self.db = rustkmer_pyo3.PyDatabase(database_path, load_mode)
            print(f"✅ PyO3统一接口数据库初始化成功: {database_path}")
            print(f"   加载模式: {load_mode}")
            
            # Get database information
            db_info = self.db.database_info()
            kmer_size = int(db_info['kmer_size'])
            print(f"   K-mer大小: {kmer_size}")
            
            if kmer_size != 57:
                print(f"⚠️  警告: 数据库k-mer大小为 {kmer_size}，期望为57")
            
        except Exception as e:
            print(f"❌ PyO3统一接口数据库初始化失败: {e}")
            raise
    
    def process_sequence(self, header, sequence, verbose=True):
        """
        Process a single sequence for gap filling following the correct logic:
        1. Reduce N regions to max_N length
        2. Perform gap filling on reduced sequence
        3. Return filled reduced sequence
        
        Args:
            header: FASTA header
            sequence: DNA sequence
            verbose: Whether to print detailed information
            
        Returns:
            tuple: (processed_header, processed_sequence, processing_info)
        """
        if verbose:
            print(f"\n🔍 处理序列: {header}")
            print(f"   原始序列长度: {len(sequence)}")
        
        # Find original N regions for reporting
        original_n_regions = get_consecutive_N_regions(sequence)
        
        if not original_n_regions:
            if verbose:
                print(f"   ✅ 序列中未发现N区域，跳过处理")
            return header, sequence, {'n_regions_found': 0, 'gaps_filled': 0}
        
        if verbose:
            print(f"   📍 发现 {len(original_n_regions)} 个N区域")
            for i, region in enumerate(original_n_regions):
                n_length = region['nend'] - region['nstart'] + 1
                print(f"     区域{i+1}: 位置{region['nstart']}-{region['nend']}, 长度{n_length}")
        
        # Step 1: Reduce N positions (limit gaps to 43 N's)
        reduced_sequence = reduce_N_positions(sequence, max_N=43)
        
        if verbose:
            print(f"   ✂️  N区域缩减后序列长度: {len(reduced_sequence)}")
            if len(reduced_sequence) != len(sequence):
                print(f"   📉 序列缩短了 {len(sequence) - len(reduced_sequence)} 个字符")
        
        # Find N regions in reduced sequence
        reduced_n_regions = get_consecutive_N_regions(reduced_sequence)
        
        if not reduced_n_regions:
            if verbose:
                print(f"   ✅ 缩减后无N区域，无需gap filling")
            return header, reduced_sequence, {'n_regions_found': 0, 'gaps_filled': 0}
        
        if verbose:
            print(f"   📍 缩减后发现 {len(reduced_n_regions)} 个N区域")
            for i, region in enumerate(reduced_n_regions):
                n_length = region['nend'] - region['nstart'] + 1
                print(f"     区域{i+1}: 位置{region['nstart']}-{region['nend']}, 长度{n_length}")
        
        # Step 2: Process each N region in reduced sequence
        processing_info = {
            'n_regions_found': len(original_n_regions),
            'n_regions_reduced': len(reduced_n_regions),
            'gaps_filled': 0,
            'total_patterns': 0,
            'successful_queries': 0,
            'balance_stats': []
        }
        
        for i, n_region in enumerate(reduced_n_regions):
            nstart = n_region['nstart']
            nend = n_region['nend']
            
            if verbose:
                print(f"\n   🛠️  处理第{i+1}个缩减N区域 (位置{nstart}-{nend})")
            
            # Try progressive pattern building with fallback
            pattern, upstream, downstream, n_length, balance_info = build_progressive_57mer_pattern(
                reduced_sequence, nstart, nend, verbose=True
            )
            
            processing_info['total_patterns'] += 1
            processing_info['balance_stats'].append(balance_info)
            
            # Query database with retry mechanism
            query_results = None
            max_retries = 5  # Maximum number of fallback attempts
            
            for attempt in range(max_retries):
                try:
                    query_results = self.db.query_hybrid(pattern)
                    processing_info['successful_queries'] += 1
                    
                    if verbose:
                        print(f"    🔍 查询结果 (尝试{attempt + 1}): 找到 {len(query_results)} 个匹配")
                    
                    # If we found results, break out of retry loop
                    if query_results:
                        break
                        
                except Exception as e:
                    if verbose:
                        print(f"    ⚠️  查询失败 (尝试{attempt + 1}): {e}")
                    
                    # If this isn't the last attempt, try with more N's
                    if attempt < max_retries - 1:
                        original_n_length = nend - nstart + 1
                        initial_n_length = min(original_n_length, 43)
                        next_n_length = initial_n_length + (attempt + 1) * 4
                        
                        if next_n_length <= min(original_n_length, 53):  # Don't exceed reasonable limits
                            if verbose:
                                print(f"    🔄 回退策略: 尝试增加N数量到{next_n_length}")
                            
                            # Try building new pattern with more N's
                            pattern, upstream, downstream, n_length, balance_info = build_progressive_57mer_pattern(
                                reduced_sequence, nstart, nend, initial_n_length=next_n_length, verbose=False
                            )
                            
                            if verbose:
                                fallback_note = " (回退策略)" if balance_info.get('used_fallback', False) else ""
                                print(f"    🔄 新Pattern: {pattern}{fallback_note}")
                            
                            processing_info['total_patterns'] += 1
                            processing_info['balance_stats'].append(balance_info)
                        else:
                            if verbose:
                                print(f"    ❌ 已达到最大重试次数，放弃此N区域")
                            break
                    else:
                        if verbose:
                            print(f"    ❌ 已达到最大重试次数，放弃此N区域")
            
            # Select best filling if we have results
            if query_results and query_results:
                fill_seq, best_kmer, best_count, best_polymers = select_best_filling_for_n_region(
                    query_results, upstream, n_length, downstream
                )
                
                # Apply filling to reduced sequence
                if fill_seq:
                    # Fill the N region in reduced sequence
                    reduced_sequence = apply_gap_filling(
                        reduced_sequence, nstart, nstart + n_length - 1, fill_seq
                    )
                    processing_info['gaps_filled'] += 1
                    
                    if verbose:
                        print(f"    ✅ 成功填充: {fill_seq}")
                        print(f"       填充位置: {nstart}-{nstart + n_length - 1} (长度: {len(fill_seq)})")
                        print(f"       最佳匹配: {best_kmer}")
                        print(f"       计数: {best_count}, 多聚体: {best_polymers}")
                else:
                    if verbose:
                        print(f"    ❌ 未找到合适的填充序列")
            elif verbose:
                print(f"    ❌ 所有查询尝试都失败，无法填充此N区域")
        
        # Step 3: Return filled reduced sequence
        return header, reduced_sequence, processing_info
    
    def process_fasta_file(self, input_file, output_file, limit=None, verbose=True):
        """
        Process FASTA file for gap filling.
        
        Args:
            input_file: Input FASTA file path
            output_file: Output FASTA file path
            limit: Limit number of sequences to process
            verbose: Whether to print detailed information
        """
        if verbose:
            print(f"\n📝 开始处理FASTA文件: {input_file}")
        
        # Check input file
        if not os.path.exists(input_file):
            print(f"❌ 错误: 输入文件不存在 {input_file}")
            return False
        
        # Count sequences
        try:
            fasta = pyfastx.Fasta(input_file)
            total_sequences = len(fasta)
            actual_limit = limit if limit else total_sequences
            if verbose:
                print(f"📊 文件包含 {total_sequences} 个序列，将处理 {actual_limit} 个")
        except Exception as e:
            print(f"❌ 读取FASTA文件失败: {e}")
            return False
        
        # Process sequences
        processed_sequences = []
        all_processing_info = []
        error_count = 0
        
        with tqdm(total=actual_limit, desc="处理序列", unit="个", disable=not verbose) as pbar:
            for i, fasta_seq in enumerate(pyfastx.Fasta(input_file)):
                if limit and i >= limit:
                    break
                
                try:
                    # Process sequence
                    header, filled_seq, proc_info = self.process_sequence(
                        fasta_seq.name, str(fasta_seq.seq), verbose=False
                    )
                    
                    processed_sequences.append((header, filled_seq))
                    all_processing_info.append(proc_info)
                    
                    # Update progress
                    pbar.update(1)
                    if verbose and i < 5:  # Show details for first few sequences
                        pbar.set_description(f"处理序列 {i+1}/{actual_limit}")
                    
                except Exception as e:
                    error_count += 1
                    if verbose:
                        print(f"⚠️  处理序列 {i+1} 时出错: {e}")
                    # Add original sequence on error
                    processed_sequences.append((fasta_seq.name, str(fasta_seq.seq)))
                    all_processing_info.append({'error': str(e)})
        
        # Write output
        if verbose:
            print(f"\n💾 写入 {len(processed_sequences)} 个处理后的序列到 {output_file}")
        
        try:
            with open(output_file, 'w') as f:
                for header, sequence in processed_sequences:
                    f.write(f">{header}\n")
                    # Write sequence in lines of 80 characters
                    for j in range(0, len(sequence), 80):
                        f.write(f"{sequence[j:j+80]}\n")
                    f.write("\n")
            
            if verbose:
                print(f"✅ 成功写入输出文件")
                
        except Exception as e:
            print(f"❌ 写入输出文件失败: {e}")
            return False
        
        # Print summary statistics
        if verbose:
            self.print_processing_summary(all_processing_info, error_count)
        
        return True
    
    def print_processing_summary(self, all_processing_info, error_count):
        """Print comprehensive processing summary."""
        print(f"\n📈 处理总结:")
        print(f"   总序列数: {len(all_processing_info)}")
        print(f"   错误数: {error_count}")
        
        # Calculate statistics
        total_n_regions = sum(info.get('n_regions_found', 0) for info in all_processing_info)
        total_n_regions_reduced = sum(info.get('n_regions_reduced', 0) for info in all_processing_info)
        total_gaps_filled = sum(info.get('gaps_filled', 0) for info in all_processing_info)
        total_patterns = sum(info.get('total_patterns', 0) for info in all_processing_info)
        successful_queries = sum(info.get('successful_queries', 0) for info in all_processing_info)
        
        print(f"   发现N区域总数: {total_n_regions}")
        print(f"   缩减后N区域数: {total_n_regions_reduced}")
        print(f"   成功填充数: {total_gaps_filled}")
        print(f"   生成patterns数: {total_patterns}")
        print(f"   成功查询数: {successful_queries}")
        
        if total_n_regions > 0:
            success_rate = (total_gaps_filled / total_n_regions) * 100
            query_success_rate = (successful_queries / total_patterns) * 100 if total_patterns > 0 else 0
            print(f"   填充成功率: {success_rate:.1f}%")
            print(f"   查询成功率: {query_success_rate:.1f}%")
        
        # Balance statistics
        all_balance_scores = []
        all_center_positions = []
        for info in all_processing_info:
            if 'balance_stats' in info:
                for stat in info['balance_stats']:
                    all_balance_scores.append(stat['balance_score'])
                    all_center_positions.append(stat['center_position'])
        
        if all_balance_scores:
            avg_balance = sum(all_balance_scores) / len(all_balance_scores)
            avg_center = sum(all_center_positions) / len(all_center_positions)
            well_balanced = sum(1 for score in all_balance_scores if score <= 1)
            well_centered = sum(1 for pos in all_center_positions if 0.4 <= pos <= 0.6)
            
            print(f"\n⚖️  平衡性统计:")
            print(f"   平均平衡分数: {avg_balance:.2f} (越小越平衡)")
            print(f"   平均中心位置: {avg_center:.3f} (0.5为理想)")
            print(f"   良好平衡分配: {well_balanced}/{len(all_balance_scores)} ({100*well_balanced/len(all_balance_scores):.1f}%)")
            print(f"   良好居中位置: {well_centered}/{len(all_center_positions)} ({100*well_centered/len(all_center_positions):.1f}%)")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="FASTA Gap Filling with Balanced 57-mer Patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --input input.fa --output output.fa --database database.rkdb
  %(prog)s -i input.fa -o output.fa -d database.rkdb --load-mode MemoryMapped

主要特性:
- 优先将N区域放置在57-mer pattern中央
- 平衡分配上下游序列长度
- PyO3统一接口集成
- 智能结果筛选（优先多聚体最少）
- 全面的边界约束处理

平衡分配策略:
- 理想情况: 上游长度 ≈ 下游长度
- 边界限制: 从可用侧补充
- 严格验证: 确保57-mer长度约束
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='输入FASTA文件路径'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='输出FASTA文件路径'
    )
    
    parser.add_argument(
        '--database', '-d',
        required=True,
        help='K57数据库文件路径 (.rkdb文件)'
    )
    
    parser.add_argument(
        '--load-mode',
        choices=['Preload', 'MemoryMapped', 'Lazy'],
        default='Preload',
        help='PyO3加载模式 (默认: Preload)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='限制处理的序列数量（用于测试）'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式，减少输出'
    )
    
    args = parser.parse_args()
    
    # Check files
    if not os.path.exists(args.input):
        print(f"❌ 错误: 输入文件不存在 {args.input}")
        return 1
    
    if not os.path.exists(args.database):
        print(f"❌ 错误: 数据库文件不存在 {args.database}")
        return 1
    
    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert load mode
    load_mode = getattr(rustkmer_pyo3.LoadMode, args.load_mode)
    
    try:
        # Initialize processor
        processor = FastaGapFilling57merProcessor(
            database_path=args.database,
            load_mode=load_mode
        )
        
        # Process file
        success = processor.process_fasta_file(
            input_file=args.input,
            output_file=args.output,
            limit=args.limit,
            verbose=not args.quiet
        )
        
        if success:
            print(f"\n🎉 Gap filling处理完成！")
            print(f"📁 输出文件: {args.output}")
            return 0
        else:
            print(f"\n❌ 处理失败")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断处理")
        return 1
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
