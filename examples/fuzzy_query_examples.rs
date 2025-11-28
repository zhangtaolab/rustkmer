//! RustKmer 模糊查询示例集
//!
//! 这个示例展示了各种模糊查询的使用场景和最佳实践

use rustkmer::database::format::{RKDatabase, DatabaseHeader, KmerEntry};
use rustkmer::fuzzy::{FuzzyQuery, FuzzyQueryEngine};
use std::time::Instant;

fn create_sample_database() -> RKDatabase {
    println!("📝 创建示例数据库...");

    // 创建数据库头
    let header = DatabaseHeader::new(13, 100, true);
    let mut database = RKDatabase::new(header);

    // 添加一些示例 k-mers
    let sample_kmers = vec![
        // 人类基因组常见序列
        "ATGCGATGCTAGCA",  // 示例序列 1
        "ATGCGATGCTAGCG",  // 示例序列 2 (最后一个不同)
        "ATGCGATGCTAGCC",  // 示例序列 3 (最后一个不同)
        "TTGCGATGCTAGCA",  // 示例序列 4 (第一个不同)
        "GCGATGCTAGCATG",  // 示例序列 5 (移位)
        "ATGCGTTGCTAGCA",  // 示例序列 6 (中间有突变)
        "ATGCGATGTTAGCA",  // 示例序列 7 (中间有突变)
        "ATGCCGATGCTAGCA",  // 示例序列 8 (中间有插入)
        "ATGCGATGCTTGCA",  // 示例序列 9 (中间有删除)
        "ATGAGATGCTAGCA",  // 示例序列 10 (前半部分突变)
    ];

    // 转换为数据库条目
    for (i, kmer_str) in sample_kmers.iter().enumerate() {
        if let Ok(kmer_value) = rustkmer::kmer::encoding::encode_kmer(kmer_str) {
            let entry = KmerEntry::new(kmer_value, (i + 1) as u32);
            database.entries.push(entry);
        }
    }

    database.header.total_kmers = database.entries.len() as u64;
    println!("✅ 数据库创建完成，包含 {} 个 k-mers", database.entries.len());
    database
}

fn example_1_exact_match() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 1: 精确匹配查询");
    println!("====================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 精确匹配查询
    let query = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 0);

    let start_time = Instant::now();
    let result = engine.execute_query(&query)?;
    let query_time = start_time.elapsed();

    println!("查询字符串: {}", query.query_string);
    println!("查询时间: {:?}", query_time);
    println!("总匹配数: {}", result.total_count);
    println!("变体生成数: {}", result.query_metadata.variants_generated);

    for (i, m) in result.individual_matches.iter().enumerate() {
        println!("  匹配 {}: {} (计数: {})", i + 1, m.sequence, m.count);
    }

    Ok(())
}

fn example_2_wildcard_basic() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 2: 基础通配符查询");
    println!("========================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 单个通配符查询
    let query = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);

    let start_time = Instant::now();
    let result = engine.execute_query(&query)?;
    let query_time = start_time.elapsed();

    println!("查询字符串: {}", query.query_string);
    println!("查询时间: {:?}", query_time);
    println!("总匹配数: {}", result.total_count);
    println!("变体生成数: {}", result.query_metadata.variants_generated);

    // 展示不同类型的匹配
    let mut exact_matches = 0;
    let mut wildcard_matches = 0;

    for m in &result.individual_matches {
        match m.match_type {
            rustkmer::fuzzy::MatchType::Exact => exact_matches += 1,
            rustkmer::fuzzy::MatchType::WildcardExpansion { .. } => wildcard_matches += 1,
            _ => {}
        }
    }

    println!("  精确匹配: {}", exact_matches);
    println!("  通配符扩展匹配: {}", wildcard_matches);

    // 显示前几个匹配
    for (i, m) in result.individual_matches.iter().take(5).enumerate() {
        println!("  匹配 {}: {} (计数: {})", i + 1, m.sequence, m.count);
    }

    Ok(())
}

fn example_3_multiple_wildcards() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 3: 多个通配符查询");
    println!("========================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 多个通配符查询
    let query = FuzzyQuery::new("ATNNGATGCTAGC", 13, 0);

    let start_time = Instant::now();
    let result = engine.execute_query(&query)?;
    let query_time = start_time.elapsed();

    println!("查询字符串: {}", query.query_string);
    println!("查询时间: {:?}", query_time);
    println!("总匹配数: {}", result.total_count);
    println!("变体生成数: {}", result.query_metadata.variants_generated);

    // 显示组合爆炸的影响
    let expected_variants = 4_usize.pow(2); // 4^2 = 16
    println!("理论变体数: {}", expected_variants);
    println!("实际变体数: {}", result.query_metadata.variants_generated);

    // 显示前几个匹配
    for (i, m) in result.individual_matches.iter().take(8).enumerate() {
        println!("  匹配 {}: {} (计数: {})", i + 1, m.sequence, m.count);
    }

    Ok(())
}

fn example_4_mutation_tolerance() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 4: 突变容忍度查询");
    println!("========================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 单突变容忍度查询
    let query = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 1);

    let start_time = Instant::now();
    let result = engine.execute_query(&query)?;
    let query_time = start_time.elapsed();

    println!("查询字符串: {}", query.query_string);
    println!("突变容忍度: {}", query.mutation_tolerance);
    println!("查询时间: {:?}", query_time);
    println!("总匹配数: {}", result.total_count);
    println!("变体生成数: {}", result.query_metadata.variants_generated);

    // 分析匹配类型
    let mut mutation_matches = 0;
    for m in &result.individual_matches {
        if let rustkmer::fuzzy::MatchType::MutationTolerance { .. } = m.match_type {
            mutation_matches += 1;
        }
    }

    println!("  精确匹配: {}", result.individual_matches.len() - mutation_matches);
    println!("  突变匹配: {}", mutation_matches);

    // 显示一些突变匹配
    let mutation_examples: Vec<_> = result.individual_matches.iter()
        .filter(|m| matches!(m.match_type, rustkmer::fuzzy::MatchType::MutationTolerance { .. }))
        .take(5)
        .collect();

    println!("  突变匹配示例:");
    for (i, m) in mutation_examples.iter().enumerate() {
        if let rustkmer::fuzzy::MatchType::MutationTolerance { mutation_positions } = &m.match_type {
            println!("    {}: {} (突变位置: {:?})", i + 1, m.sequence, mutation_positions);
        }
    }

    Ok(())
}

fn example_5_combined_fuzzy() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 5: 组合模糊查询");
    println!("==================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 组合通配符和突变容忍度
    let query = FuzzyQuery::new("ATGCGATGCTN", 13, 1);

    let start_time = Instant::now();
    let result = engine.execute_query(&query)?;
    let query_time = start_time.elapsed();

    println!("查询字符串: {}", query.query_string);
    println!("突变容忍度: {}", query.mutation_tolerance);
    println!("查询时间: {:?}", query_time);
    println!("总匹配数: {}", result.total_count);
    println!("变体生成数: {}", result.query_metadata.variants_generated);

    // 分析扩展方法
    println!("查询参数: 突变容忍度={}", query.mutation_tolerance);

    // 显示性能分析
    if query_time.as_millis() > 0 {
        let variants_per_ms = result.query_metadata.variants_generated as f64 / query_time.as_millis() as f64;
        println!("处理速度: {:.1} 变体/毫秒", variants_per_ms);
    }

    // 显示匹配分布
    let mut match_types = std::collections::HashMap::new();
    for m in &result.individual_matches {
        let key = format!("{:?}", m.match_type);
        *match_types.entry(key).or_insert(0) += 1;
    }

    println!("匹配类型分布:");
    for (match_type, count) in &match_types {
        println!("  {}: {}", match_type, count);
    }

    Ok(())
}

fn example_6_length_normalization() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 6: 长度标准化");
    println!("==================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 短查询（需要填充）
    let short_query = FuzzyQuery::new("ATGCG", 13, 0);

    println!("短查询测试:");
    println!("原始查询: {}", short_query.query_string);
    println!("目标长度: {}", short_query.kmer_size);

    match engine.execute_query(&short_query) {
        Ok(result) => {
            println!("✅ 查询成功");
            println!("变体生成数: {}", result.query_metadata.variants_generated);
            println!("总匹配数: {}", result.total_count);
        }
        Err(e) => {
            println!("❌ 查询失败: {}", e);
        }
    }

    // 长查询（需要截断）
    let long_query = FuzzyQuery::new("ATGCGATGCTAGCATGCGATG", 13, 0);

    println!("\n长查询测试:");
    println!("原始查询: {}", long_query.query_string);
    println!("目标长度: {}", long_query.kmer_size);

    match engine.execute_query(&long_query) {
        Ok(result) => {
            println!("✅ 查询成功");
            println!("变体生成数: {}", result.query_metadata.variants_generated);
            println!("总匹配数: {}", result.total_count);
        }
        Err(e) => {
            println!("❌ 查询失败: {}", e);
        }
    }

    Ok(())
}

fn example_7_performance_optimization() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 7: 性能优化");
    println!("================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 测试不同的批处理大小
    let batch_sizes = vec![100, 500, 1000, 2000];

    for batch_size in batch_sizes {
        let query = FuzzyQuery::with_params(
            "ATGCGATGCTAGCN",
            13,
            1,
            None,
            true,
            batch_size,
        );

        let start_time = Instant::now();
        let result = engine.execute_query(&query)?;
        let query_time = start_time.elapsed();

        println!("批处理大小: {}", batch_size);
        println!("  查询时间: {:?}", query_time);
        println!("  变体数: {}", result.query_metadata.variants_generated);
        println!("  匹配数: {}", result.total_count);

        if query_time.as_millis() > 0 {
            let throughput = result.query_metadata.variants_generated as f64 / query_time.as_millis() as f64;
            println!("  吞吐量: {:.1} 变体/毫秒", throughput);
        }
        println!();
    }

    Ok(())
}

fn example_8_error_handling() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 8: 错误处理");
    println!("================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 测试1: 过多通配符
    println!("测试1: 过多通配符");
    let too_many_wildcards = FuzzyQuery::new("NNNNNNNNNNNNN", 13, 0);
    match engine.execute_query(&too_many_wildcards) {
        Ok(_) => println!("❌ 预期应该失败"),
        Err(rustkmer::fuzzy::FuzzyError::TooManyVariants { actual, limit }) => {
            println!("✅ 正确捕获错误: 生成 {} 个变体 (限制: {})", actual, limit);
        }
        Err(e) => println!("❓ 意外错误: {}", e),
    }

    // 测试2: 无效字符
    println!("\n测试2: 无效字符");
    let invalid_chars = FuzzyQuery::new("ATGCGATGCTXAGCA", 13, 0); // 包含 X
    match engine.execute_query(&invalid_chars) {
        Ok(_) => println!("❌ 预期应该失败"),
        Err(rustkmer::fuzzy::FuzzyError::InvalidQuery(msg)) => {
            println!("✅ 正确捕获错误: {}", msg);
        }
        Err(e) => println!("❓ 意外错误: {}", e),
    }

    // 测试3: 长度差过大
    println!("\n测试3: 长度差过大");
    let too_short = FuzzyQuery::new("ATG", 13, 0);
    match engine.execute_query(&too_short) {
        Ok(_) => println!("❌ 预期应该失败"),
        Err(rustkmer::fuzzy::FuzzyError::InvalidParameters(msg)) => {
            println!("✅ 正确捕获错误: {}", msg);
        }
        Err(e) => println!("❓ 意外错误: {}", e),
    }

    Ok(())
}

fn example_9_batch_queries() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n🎯 示例 9: 批量查询");
    println!("================");

    let database = create_sample_database();
    let engine = FuzzyQueryEngine::new(database);

    // 创建多个查询
    let queries = vec![
        FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0),      // 通配符
        FuzzyQuery::new("ATGCGATGCTAGCA", 13, 1),      // 单突变
        FuzzyQuery::new("TTGCGATGCTAGCN", 13, 0),      // 通配符
        FuzzyQuery::new("GCGATGCTAGCATN", 13, 0),      // 通配符
    ];

    println!("执行 {} 个批量查询...", queries.len());

    let start_time = Instant::now();
    let results = engine.execute_batch(&queries)?;
    let total_time = start_time.elapsed();

    println!("批量查询完成:");
    println!("  总时间: {:?}", total_time);
    println!("  平均时间: {:?}", total_time / queries.len() as u32);

    for (i, result) in results.iter().enumerate() {
        println!("  查询 {}: {} ({} 匹配, {} 变体)",
            i + 1,
            queries[i].query_string,
            result.total_count,
            result.query_metadata.variants_generated
        );
    }

    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧬 RustKmer 模糊查询示例集");
    println!("========================");
    println!("这个示例演示了模糊查询的各种使用场景和最佳实践");

    // 运行所有示例
    example_1_exact_match()?;
    example_2_wildcard_basic()?;
    example_3_multiple_wildcards()?;
    example_4_mutation_tolerance()?;
    example_5_combined_fuzzy()?;
    example_6_length_normalization()?;
    example_7_performance_optimization()?;
    example_8_error_handling()?;
    example_9_batch_queries()?;

    println!("\n🎉 所有示例执行完成！");
    println!("您可以根据自己的需求选择合适的查询策略。");

    Ok(())
}