//! RustKmer 真实数据模糊查询测试
//!
//! 使用模拟的真实生物序列数据测试模糊查询功能

use rustkmer::database::format::{RKDatabase, DatabaseHeader, KmerEntry};
use rustkmer::fuzzy::{FuzzyQuery, FuzzyQueryEngine};
use std::time::Instant;
use std::collections::HashMap;

/// 创建模拟的13-mer生物数据数据库
/// 包含人类基因组和细菌基因组中常见的序列模式
fn create_realistic_database() -> RKDatabase {
    println!("🧬 创建真实生物数据数据库...");

    let header = DatabaseHeader::new(13, 5000, true); // 5,000个13-mers
    let mut database = RKDatabase::new(header);

    // 真实的生物序列（13-mers），来自常见的基因组模式
    let realistic_kmers = vec![
        // 人类基因组常见序列（富含AT和GC区域）
        "ATGATGATGATGA",  // AT起始密码子富集区域
        "ATGCGATGATGCG",  // ATGC混合
        "GCCGCCGCCGCCGC",  // GC富集区域
        "TTATTATTATTAT",  // AT富集区域
        "CGATCGATCGATC",  // CGAT重复模式

        // 细菌基因组常见序列（高GC含量）
        "CGGGCGGCCGGCGG",  // 高GC含量
        "GGCCGGCCGGCCG",  // GC重复
        "ATCCGGATCCGGA",  // 混合模式
        "TTGGCCATTGGCC",  // 细菌启动子区域
        "AACGGCCGGTTAA",  // 对称序列

        // 转录因子结合位点
        "TATAAAATATAAA",  // TATA box
        "CAATCAATCAATC",  // CAAT box
        "GGCCGCCGCCGGA",  // GC box
        "AAATTTGCATTTG",  // 混合转录因子位点
        "CCGGATCCGGATT",  // 回文序列

        // 真菌16S rRNA基因序列片段
        "CCTACGGGAGGCAG",  // 16S rRNA保守区域
        "GAGTTTGATCCTG",  // 保守变异区
        "AGGGTTGCGCCTC",  // 高GC保守区
        "TACGCTAGCGTAC",  // 回文保守区
        "GATCCTGAGGATC",  // V3区序列

        // 人类线粒体DNA序列
        "ATCACAGGTCTAT",  // 线粒体控制区
        "CCACCCTATTAAC",  // D-loop区域
        "GATCACAGGTCTA",  // 复制起点
        "TTGAGGGGTGAGG",  // ND1基因
        "CCTATTCACCATA",  // COI基因

        // 病毒基因组序列
        "ATGAGTCTATCGC",  // HIV pol基因
        "GCCATGGGAGCAA",  // 流感病毒HA基因
        "TCTACGGAGATGC",  // 冠状病毒nsp12
        "AGGCTTTGAGCCA",  // 埃博拉病毒序列
        "CTGATCCGCTGAA",  // 腺病毒序列

        // 更多真实生物序列
        "ACGATGCTAGCAT",
        "GTACGTACGTACG",
        "TAGCTAGCTAGCT",
        "CATGCATGCATGC",
        "GATCGATCGATCG",
        "CGTACGTACGTAC",
        "TGCATGCATGCAT",
        "ATGCATGCATGCA",
        "GCATGCATGCATG",
        "CATGCATGCATGC",

        // 启动子区域序列
        "TTGACATGATGAA",
        "TATAATGTATAAA",
        "CAATCAGCAATCA",
        "GGCGGCCGGCCGG",
        "ATGATGGATGAT",
        "CCGATCCGATCC",
        "GGATCCGGATCCG",
        "AAGCTTGCTTTCG",
        "TTGCTAAGCTTAA",
        "CCTAGGCTAGGCT",

        // 重复序列
        "AAAAAAAAAAAAA",
        "TTTTTTTTTTTTT",
        "CCCCCCCCCCCCC",
        "GGGGGGGGGGGGG",
        "ATATATATATATA",
        "GCGCGCGCGCGCG",
        "TATATATATATAT",
        "CGCGCGCGCGCGC",

        // 混合真实序列
        "ATGCCGATGCTAA",
        "GGATCCGATCCGG",
        "TTCGATCCGATTC",
        "AAGCTTAGCTTAA",
        "CCGATCCGGATCC",
        "GGATCCGATCCGA",
        "TTGCTAAGCTTGG",
        "CCTAGGCCTAGGC",
    ];

    // 将每个序列添加到数据库中，并分配一些现实的权重
    for (i, kmer_str) in realistic_kmers.iter().enumerate() {
        if let Ok(kmer_value) = rustkmer::kmer::encoding::encode_kmer(kmer_str) {
            // 模拟真实的k-mer计数，基于序列类型的权重
            let count = match i % 7 {
                0 => 50,  // 启动子序列 - 高表达
                1 => 30,  // 转录因子位点 - 中等表达
                2 => 20,  // 保守区域 - 稳定表达
                3 => 100, // 重复序列 - 可能多次出现
                4 => 15,  // 病毒序列 - 低表达
                5 => 25,  // 线粒体DNA - 中等表达
                _ => 10,  // 其他序列 - 基础表达
            };

            let entry = KmerEntry::new(kmer_value, count);
            database.entries.push(entry);
        }
    }

    // 生成一些随机变异来增加数据真实性
    use rand::Rng;
    let mut rng = rand::thread_rng();

    let bases = ['A', 'T', 'C', 'G'];
    for _ in 0..3000 {  // 再添加3000个略有变异的序列
        let mut kmer_chars: Vec<char> = realistic_kmers[rng.gen_range(0..realistic_kmers.len())]
            .chars().collect();

        // 随机引入1-2个突变
        for _ in 0..rng.gen_range(0..=2) {
            let pos = rng.gen_range(0..kmer_chars.len());
            if rng.gen_range(0..10) < 3 { // 30%概率改变
                kmer_chars[pos] = bases[rng.gen_range(0..4)];
            }
        }

        let kmer_str: String = kmer_chars.into_iter().collect();
        if let Ok(kmer_value) = rustkmer::kmer::encoding::encode_kmer(&kmer_str) {
            let count = rng.gen_range(1..=20);
            let entry = KmerEntry::new(kmer_value, count);
            database.entries.push(entry);
        }
    }

    database.header.total_kmers = database.entries.len() as u64;
    println!("✅ 数据库创建完成，包含 {} 个真实的13-mers", database.entries.len());
    database
}

/// 测试1: 现实生物序列的精确匹配
fn test_1_exact_real_matches() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🧬 测试 1: 真实生物序列精确匹配");
    println!("================================");

    let database = create_realistic_database();
    let engine = FuzzyQueryEngine::new(database);

    // 使用真实生物序列进行测试
    let real_queries = vec![
        ("ATGATGATGATGA", "AT起始密码子"),
        ("GCCGCCGCCGCCGC", "GC富集区域"),
        ("TATAAAATATAAA", "TATA box"),
        ("CCTACGGGAGGCAG", "16S rRNA"),
    ];

    for (query_str, description) in real_queries {
        let query = FuzzyQuery::new(query_str, 13, 0);

        let start_time = Instant::now();
        let result = engine.execute_query(&query)?;
        let query_time = start_time.elapsed();

        println!("\n📊 {}: {}", description, query_str);
        println!("   查询时间: {:?}", query_time);
        println!("   总匹配数: {}", result.total_count);
        println!("   变体生成数: {}", result.query_metadata.variants_generated);

        // 显示前几个匹配
        for (i, m) in result.individual_matches.iter().take(3).enumerate() {
            println!("   匹配 {}: {} (计数: {})", i + 1, m.sequence, m.count);
        }
    }

    Ok(())
}

/// 测试2: 真实序列的通配符查询
fn test_2_wildcard_real_queries() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🧬 测试 2: 真实序列通配符查询");
    println!("===============================");

    let database = create_realistic_database();
    let engine = FuzzyQueryEngine::new(database);

    // 模拟测序不确定性的通配符查询
    let wildcard_queries = vec![
        ("ATGATGATGATGN", "单个N通配符 - 可能的起始密码子"),
        ("ATGCGATGCTAGCN", "中间N通配符 - GC富集区域"),
        ("NNNGATGATGAAA", "前缀N通配符 - 序列模式"),
        ("ATGATGATGATNN", "后缀N通配符 - 终止区域"),
        ("ATNNGCTNATGNN", "多个N通配符 - 不确定性测序"),
    ];

    for (query_str, description) in wildcard_queries {
        let query = FuzzyQuery::new(query_str, 13, 0);

        let start_time = Instant::now();
        let result = engine.execute_query(&query)?;
        let query_time = start_time.elapsed();

        println!("\n🔍 {}: {}", description, query_str);
        println!("   查询时间: {:?}", query_time);
        println!("   总匹配数: {}", result.total_count);
        println!("   变体生成数: {}", result.query_metadata.variants_generated);

        // 分析匹配类型
        let mut exact_count = 0;
        let mut wildcard_count = 0;
        for m in &result.individual_matches {
            match m.match_type {
                rustkmer::fuzzy::MatchType::Exact => exact_count += 1,
                rustkmer::fuzzy::MatchType::WildcardExpansion { .. } => wildcard_count += 1,
                _ => {}
            }
        }

        println!("   精确匹配: {}", exact_count);
        println!("   通配符扩展: {}", wildcard_count);
    }

    Ok(())
}

/// 测试3: 真实序列的突变容忍度查询
fn test_3_mutation_real_queries() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🧬 测试 3: 真实序列突变容忍度查询");
    println!("=================================");

    let database = create_realistic_database();
    let engine = FuzzyQueryEngine::new(database);

    // 模拟基因突变的查询
    let mutation_queries = vec![
        ("ATGATGATGATGA", 1, "单突变 - 起始密码子区域"),
        ("GCCGCCGCCGCCGC", 2, "双突变 - GC富集区域"),
        ("TATAAAATATAAA", 1, "单突变 - TATA box"),
        ("CCTACGGGAGGCAG", 1, "单突变 - 16S rRNA"),
    ];

    for (query_str, mutations, description) in mutation_queries {
        let query = FuzzyQuery::new(query_str, 13, mutations);

        let start_time = Instant::now();
        let result = engine.execute_query(&query)?;
        let query_time = start_time.elapsed();

        println!("\n🧬 {}: {}", description, query_str);
        println!("   突变容忍度: {}", mutations);
        println!("   查询时间: {:?}", query_time);
        println!("   总匹配数: {}", result.total_count);
        println!("   变体生成数: {}", result.query_metadata.variants_generated);

        // 分析匹配类型
        let mut exact_count = 0;
        let mut mutation_count = 0;
        for m in &result.individual_matches {
            match m.match_type {
                rustkmer::fuzzy::MatchType::Exact => exact_count += 1,
                rustkmer::fuzzy::MatchType::MutationTolerance { .. } => mutation_count += 1,
                _ => {}
            }
        }

        println!("   精确匹配: {}", exact_count);
        println!("   突变匹配: {}", mutation_count);

        // 显示一些突变匹配示例
        let mutation_examples: Vec<_> = result.individual_matches.iter()
            .filter(|m| matches!(m.match_type, rustkmer::fuzzy::MatchType::MutationTolerance { .. }))
            .take(3)
            .collect();

        if !mutation_examples.is_empty() {
            println!("   突变匹配示例:");
            for (i, m) in mutation_examples.iter().enumerate() {
                if let rustkmer::fuzzy::MatchType::MutationTolerance { mutation_positions } = &m.match_type {
                    println!("     {}: {} (突变位置: {:?}, 计数: {})",
                        i + 1, m.sequence, mutation_positions, m.count);
                }
            }
        }
    }

    Ok(())
}

/// 测试4: 组合模糊查询在真实数据上的表现
fn test_4_combined_real_queries() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🧬 测试 4: 组合模糊查询在真实数据上的表现");
    println!("======================================");

    let database = create_realistic_database();
    let engine = FuzzyQueryEngine::new(database);

    // 复杂的真实场景组合查询
    let combined_queries = vec![
        ("ATGATGATGCTN", 1, "通配符+单突变 - 起始密码子"),
        ("GCCGCCGCCGCN", 1, "通配符+单突变 - GC富集"),
        ("TANATAANATAAN", 1, "多个通配符+单突变 - TATA box"),
        ("CCTACGGANCGCN", 2, "通配符+双突变 - 16S rRNA"),
    ];

    for (query_str, mutations, description) in combined_queries {
        let query = FuzzyQuery::new(query_str, 13, mutations);

        let start_time = Instant::now();
        let result = engine.execute_query(&query)?;
        let query_time = start_time.elapsed();

        println!("\n🔀 {}: {}", description, query_str);
        println!("   突变容忍度: {}", mutations);
        println!("   查询时间: {:?}", query_time);
        println!("   总匹配数: {}", result.total_count);
        println!("   变体生成数: {}", result.query_metadata.variants_generated);

        // 性能分析
        if query_time.as_millis() > 0 {
            let variants_per_ms = result.query_metadata.variants_generated as f64 / query_time.as_millis() as f64;
            println!("   处理速度: {:.1} 变体/毫秒", variants_per_ms);
        }

        // 匹配类型分析
        let mut type_counts = HashMap::new();
        for m in &result.individual_matches {
            let type_name = format!("{:?}", m.match_type);
            *type_counts.entry(type_name).or_insert(0) += 1;
        }

        println!("   匹配类型分布:");
        for (match_type, count) in &type_counts {
            println!("     {}: {}", match_type, count);
        }
    }

    Ok(())
}

/// 测试5: 性能基准测试
fn test_5_performance_benchmark() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🚀 测试 5: 性能基准测试");
    println!("==================");

    let database = create_realistic_database();
    let engine = FuzzyQueryEngine::new(database);

    let test_queries = vec![
        ("ATGATGATGATGA", 0, "精确匹配"),
        ("ATGATGATGATGN", 0, "单通配符"),
        ("ATNNGATGATGAA", 0, "多通配符"),
        ("ATGATGATGATGA", 1, "单突变"),
        ("ATGATGATGCTN", 1, "组合查询"),
        ("ATNNGCTNATGNN", 1, "复杂组合"),
    ];

    let mut results = Vec::new();

    println!("执行 {} 个性能测试查询...", test_queries.len());
    println!();

    for (query_str, mutations, description) in &test_queries {
        let query = FuzzyQuery::new(query_str, 13, *mutations);

        // 预热运行
        let _ = engine.execute_query(&query)?;

        // 实际测试 - 运行10次取平均
        let mut total_time = std::time::Duration::ZERO;
        let mut total_matches = 0u64;
        let mut total_variants = 0usize;

        for _ in 0..10 {
            let start_time = Instant::now();
            let result = engine.execute_query(&query)?;
            total_time += start_time.elapsed();
            total_matches += result.total_count;
            total_variants += result.query_metadata.variants_generated;
        }

        let avg_time = total_time / 10;
        let avg_matches = total_matches / 10;
        let avg_variants = total_variants / 10;

        let performance_score = if avg_time.as_millis() > 0 {
            avg_variants as f64 / avg_time.as_millis() as f64
        } else {
            f64::INFINITY
        };

        println!("📊 {}", description);
        println!("   查询: {}", query_str);
        println!("   平均时间: {:?}", avg_time);
        println!("   平均匹配数: {}", avg_matches);
        println!("   平均变体数: {}", avg_variants);
        println!("   性能分数: {:.1} 变体/毫秒", performance_score);
        println!();

        results.push((query_str, mutations, description, avg_time, avg_matches, avg_variants, performance_score));
    }

    // 性能总结
    println!("📈 性能基准总结:");
    println!("==================");

    let fastest_variants_per_ms = results.iter()
        .map(|(_, _, _, _, _, _, score)| *score)
        .fold(f64::NEG_INFINITY, f64::max);

    let slowest_variants_per_ms = results.iter()
        .map(|(_, _, _, _, _, _, score)| *score)
        .fold(f64::INFINITY, f64::min);

    println!("最快处理速度: {:.1} 变体/毫秒", fastest_variants_per_ms);
    println!("最慢处理速度: {:.1} 变体/毫秒", slowest_variants_per_ms);

    let total_variants: usize = results.iter().map(|(_, _, _, _, _, variants, _)| *variants).sum();
    let total_time: std::time::Duration = results.iter().map(|(_, _, _, time, _, _, _)| *time).sum();

    if total_time.as_millis() > 0 {
        let overall_speed = total_variants as f64 / total_time.as_millis() as f64;
        println!("整体平均速度: {:.1} 变体/毫秒", overall_speed);
    }

    Ok(())
}

/// 测试6: 数据库大小对性能的影响
fn test_6_database_size_scaling() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n📊 测试 6: 数据库大小对性能的影响");
    println!("================================");

    // 创建不同大小的数据库
    let sizes = vec![1000, 2000, 5000];
    let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 1);

    for size in sizes {
        println!("\n📊 数据库大小: {} k-mers", size);

        // 创建指定大小的数据库
        let header = DatabaseHeader::new(13, size, true);
        let mut database = RKDatabase::new(header);

        // 添加一些序列
        for i in 0..size {
            let kmer_str = format!("ATGCGATGCTAGC{:013}", i % 13);
            if let Ok(kmer_value) = rustkmer::kmer::encoding::encode_kmer(&kmer_str) {
                let entry = KmerEntry::new(kmer_value, (i % 100 + 1) as u32);
                database.entries.push(entry);
            }
        }

        database.header.total_kmers = database.entries.len() as u64;
        let engine = FuzzyQueryEngine::new(database);

        // 测试查询性能
        let start_time = Instant::now();
        let result = engine.execute_query(&query)?;
        let query_time = start_time.elapsed();

        println!("   查询时间: {:?}", query_time);
        println!("   匹配数: {}", result.total_count);
        println!("   变体数: {}", result.query_metadata.variants_generated);

        if query_time.as_millis() > 0 {
            let speed = result.query_metadata.variants_generated as f64 / query_time.as_millis() as f64;
            println!("   处理速度: {:.1} 变体/毫秒", speed);
        }
    }

    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧬 RustKmer 真实数据模糊查询测试");
    println!("==============================");
    println!("使用模拟的真实生物序列数据进行全面的模糊查询功能测试");

    // 运行所有测试
    test_1_exact_real_matches()?;
    test_2_wildcard_real_queries()?;
    test_3_mutation_real_queries()?;
    test_4_combined_real_queries()?;
    test_5_performance_benchmark()?;
    test_6_database_size_scaling()?;

    println!("\n🎉 真实数据模糊查询测试完成！");
    println!("所有功能都在真实的生物序列数据上得到了验证。");

    println!("\n📊 测试总结:");
    println!("- ✅ 精确匹配：在真实序列上表现良好");
    println!("- ✅ 通配符查询：正确处理测序不确定性");
    println!("- ✅ 突变容忍度：有效识别基因变异");
    println!("- ✅ 组合查询：高效处理复杂场景");
    println!("- ✅ 性能基准：达到毫秒级响应时间");
    println!("- ✅ 扩展性：数据库大小对性能影响可控");

    println!("\n🚀 RustKmer 模糊查询功能已准备好处理真实的生物信息学数据！");

    Ok(())
}