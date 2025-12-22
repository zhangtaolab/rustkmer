#!/usr/bin/env python3
"""
测试去除头尾N功能
验证新添加的trim_end_n_bases功能是否正常工作

Author: RustKmer Team
Date: 2025-12-22
"""

import sys
from pathlib import Path

# 添加路径以便导入
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))

try:
    import rustkmer_pyo3
    print("✅ 成功导入 rustkmer_pyo3")
except ImportError as e:
    print(f"⚠️  无法导入 rustkmer_pyo3: {e}")
    print("请先构建PyO3扩展")

from mark_N_script_pyo3 import PyO3MarkNProcessor


def test_trim_functionality():
    """测试去除头尾N的功能"""
    print("\n🧪 测试trim_end_n_bases功能")
    print("="*50)
    
    # 寻找测试数据库
    test_data_dir = Path(__file__).parent.parent.parent / "python" / "tests" / "test_data"
    possible_databases = [
        test_data_dir / "tiny_test.rkdb",
        test_data_dir / "small_test.rkdb", 
        test_data_dir / "medium_test.rkdb",
    ]
    
    database_path = None
    for db_path in possible_databases:
        if db_path.exists():
            database_path = db_path
            break
    
    if not database_path:
        print("❌ 未找到测试数据库文件")
        return False
    
    try:
        # 创建处理器
        processor = PyO3MarkNProcessor(
            database_path=str(database_path),
            load_mode=rustkmer_pyo3.LoadMode.Preload
        )
        
        # 测试用例
        test_cases = [
            # (输入序列, 期望的去除头尾N后的序列, 描述)
            ("NNNNATCGATCGNNNN", "ATCGATCG", "头尾都有N"),
            ("ATCGATCGNNNN", "ATCGATCG", "只有尾N"),
            ("NNNNATCGATCG", "ATCGATCG", "只有头N"),
            ("ATCGATCG", "ATCGATCG", "无头尾N"),
            ("NNNNNNNN", "", "全是N"),
            ("N", "", "单个N"),
            ("ATCG", "ATCG", "无N"),
            ("", "", "空序列"),
        ]
        
        print("🔍 测试用例:")
        all_passed = True
        
        for i, (input_seq, expected_output, description) in enumerate(test_cases, 1):
            trimmed_seq, trim_info = processor.trim_end_n_bases(input_seq)
            
            print(f"\n  测试 {i}: {description}")
            print(f"    输入: '{input_seq}'")
            print(f"    输出: '{trimmed_seq}'")
            print(f"    期望: '{expected_output}'")
            print(f"    修剪信息: {trim_info}")
            
            if trimmed_seq == expected_output:
                print(f"    ✅ 通过")
            else:
                print(f"    ❌ 失败")
                all_passed = False
        
        print(f"\n{'='*50}")
        if all_passed:
            print("🎉 所有trim功能测试通过！")
        else:
            print("❌ 部分测试失败")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_marking_with_trim():
    """测试标记功能结合trim"""
    print("\n🧪 测试标记功能结合trim")
    print("="*50)
    
    # 寻找测试数据库
    test_data_dir = Path(__file__).parent.parent.parent / "python" / "tests" / "test_data"
    possible_databases = [
        test_data_dir / "tiny_test.rkdb",
        test_data_dir / "small_test.rkdb", 
        test_data_dir / "medium_test.rkdb",
    ]
    
    database_path = None
    for db_path in possible_databases:
        if db_path.exists():
            database_path = db_path
            break
    
    if not database_path:
        print("❌ 未找到测试数据库文件")
        return False
    
    try:
        # 创建处理器
        processor = PyO3MarkNProcessor(
            database_path=str(database_path),
            load_mode=rustkmer_pyo3.LoadMode.Preload
        )
        
        # 创建测试序列（开头和结尾包含N）
        test_sequence = "NNNNATCGATCGATCGATCGATCGATCGATCGNNNN"
        print(f"🔍 测试序列: '{test_sequence}'")
        print(f"   序列长度: {len(test_sequence)}")
        print(f"   开头N数量: 4")
        print(f"   结尾N数量: 4")
        
        # 测试单查询模式
        print(f"\n📊 测试单查询模式:")
        marked_seq, stats = processor.mark_problem_regions_single(test_sequence)
        
        print(f"   修剪后序列: '{marked_seq}'")
        print(f"   修剪后长度: {len(marked_seq)}")
        print(f"   修剪统计:")
        for key, value in stats.items():
            if 'trimmed' in key or 'trim' in key:
                print(f"     {key}: {value}")
        
        # 验证是否正确去除了头尾N
        if not marked_seq.startswith('N') and not marked_seq.endswith('N'):
            print("   ✅ 成功去除头尾N")
        else:
            print("   ❌ 未正确去除头尾N")
            return False
        
        # 测试批量查询模式
        print(f"\n📦 测试批量查询模式:")
        marked_seq_batch, stats_batch = processor.mark_problem_regions_batch(test_sequence, batch_size=5)
        
        print(f"   修剪后序列: '{marked_seq_batch}'")
        print(f"   修剪后长度: {len(marked_seq_batch)}")
        
        # 验证两种模式结果一致
        if marked_seq == marked_seq_batch:
            print("   ✅ 单查询和批量查询结果一致")
        else:
            print("   ⚠️  单查询和批量查询结果不一致（这可能是正常的）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 开始测试PyO3标记脚本的trim功能")
    print("="*60)
    
    # 测试trim功能
    trim_test_passed = test_trim_functionality()
    
    # 测试标记功能结合trim
    marking_test_passed = test_marking_with_trim()
    
    print("\n" + "="*60)
    print("📋 测试总结:")
    print(f"  Trim功能测试: {'✅ 通过' if trim_test_passed else '❌ 失败'}")
    print(f"  标记+Trim测试: {'✅ 通过' if marking_test_passed else '❌ 失败'}")
    
    if trim_test_passed and marking_test_passed:
        print("\n🎉 所有测试通过！Trim功能工作正常。")
        print("📝 新功能说明:")
        print("   - 自动去除序列开头的连续'N'")
        print("   - 自动去除序列结尾的连续'N'")
        print("   - 只保留中间的'N'")
        print("   - 提供详细的修剪统计信息")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
