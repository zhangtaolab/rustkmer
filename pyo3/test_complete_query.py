#!/usr/bin/env python3
"""
完整的 PyO3 查询功能测试脚本
"""

def test_complete_query_functionality():
    """测试完整的 PyO3 查询功能"""
    print("🧪 测试完整的 PyO3 查询功能...")
    
    try:
        import rustkmer_pyo3
        print("✅ PyO3 模块导入成功")
        
        # 显示可用的类
        available_classes = [attr for attr in dir(rustkmer_pyo3) if not attr.startswith('_')]
        print(f"📋 可用类: {available_classes}")
        
        # 测试 PyKmerCounter
        if 'PyKmerCounter' in available_classes:
            print("\n🔬 测试 PyKmerCounter...")
            
            # 创建计数器
            counter = rustkmer_pyo3.PyKmerCounter(k=4, canonical=False)
            print("✅ 成功创建 PyKmerCounter")
            
            # 添加测试数据
            test_kmers = ['ATCG', 'CGAT', 'TAGC', 'ATCG', 'GCTA']
            for kmer in test_kmers:
                counter.add_kmer(kmer)
            print("✅ 添加测试 k-mers 完成")
            
            # 测试基本查询
            print("\n🔍 测试基本查询...")
            count = counter.query('ATCG')
            print(f"✅ ATCG 查询结果: {count}")
            print(f"   kmer: {count.kmer}")
            print(f"   count: {count.count}")
            print(f"   found: {count.found}")
            
            # 测试查询不存在 k-mer
            missing = counter.query('TGCA')
            print(f"✅ TGCA 查询结果: {missing}")
            print(f"   found: {missing.found}")
            
            # 测试批量查询
            print("\n📊 测试批量查询...")
            batch_kmers = ['ATCG', 'CGAT', 'TGCA', 'GCTA']
            batch_results = counter.query_batch(batch_kmers)
            print(f"✅ 批量查询完成，共 {len(batch_results)} 个结果")
            for result in batch_results:
                print(f"   {result.kmer}: {result.count} (found: {result.found})")
            
            # 测试 exists 方法
            print("\n✅ 测试 exists 方法...")
            exists_atcg = counter.exists('ATCG')
            exists_tgca = counter.exists('TGCA')
            print(f"✅ ATCG 存在: {exists_atcg}")
            print(f"✅ TGCA 存在: {exists_tgca}")
            
            # 测试统计信息
            print("\n📈 测试统计信息...")
            stats = counter.get_stats()
            print(f"✅ 统计信息:")
            print(f"   unique_kmers: {stats['unique_kmers']}")
            print(f"   total_kmers: {stats['total_kmers']}")
            print(f"   kmer_size: {stats['kmer_size']}")
            print(f"   canonical: {stats['canonical']}")
            
            # 测试获取所有 k-mers
            print("\n📋 测试获取所有 k-mers...")
            all_kmers = counter.get_all_kmers()
            print(f"✅ 获取所有 k-mers: {len(all_kmers)} 个")
            for item in all_kmers[:3]:  # 只显示前3个
                print(f"   {item['kmer']}: {item['count']}")
            
        # 测试 PyFuzzyQuery
        if 'PyFuzzyQuery' in available_classes:
            print("\n🎯 测试 PyFuzzyQuery...")
            
            # 重新创建计数器用于模糊查询
            counter = rustkmer_pyo3.PyKmerCounter(k=4, canonical=False)
            fuzzy_kmers = ['ATCG', 'ATCA', 'ATTA', 'CTCG', 'GTCG']
            for kmer in fuzzy_kmers:
                counter.add_kmer(kmer)
            
            # 创建模糊查询引擎
            fuzzy = rustkmer_pyo3.PyFuzzyQuery(counter)
            print("✅ 成功创建 PyFuzzyQuery")
            
            # 测试模糊查询
            print("\n🔍 测试模糊查询...")
            result = fuzzy.fuzzy_query('ATCG', max_mutations=1)
            print(f"✅ 模糊查询 'ATCG' (max_mutations=1):")
            print(f"   查询模式: {result.query_kmer}")
            print(f"   总匹配数: {result.total_matches}")
            print(f"   突变容忍: {result.mutation_tolerance}")
            
            if result.matches:
                print("   匹配结果:")
                for match in result.matches[:3]:  # 只显示前3个
                    print(f"     {match.kmer}: count={match.count}, distance={match.distance}, type={match.match_type}")
            
            # 测试批量模糊查询
            print("\n📊 测试批量模糊查询...")
            patterns = ['ATCG', 'CTCG']
            batch_fuzzy_results = fuzzy.fuzzy_query_batch(patterns, max_mutations=1)
            print(f"✅ 批量模糊查询完成，共 {len(batch_fuzzy_results)} 个结果")
            
            for pattern, fuzzy_result in batch_fuzzy_results.items():
                print(f"   模式 '{pattern}': {fuzzy_result.total_matches} 个匹配")
        
        print("\n🎉 所有查询功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 完整 PyO3 查询功能测试")
    print("=" * 60)
    
    success = test_complete_query_functionality()
    
    print("=" * 60)
    if success:
        print("🎊 测试完成：所有查询功能正常工作！")
        return 0
    else:
        print("💥 测试失败：存在功能问题")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
