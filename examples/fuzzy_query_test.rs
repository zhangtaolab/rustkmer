//! Test program for fuzzy query functionality

use rustkmer::database::format::RKDatabase;
use rustkmer::fuzzy::{FuzzyQuery, FuzzyQueryEngine};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧬 RustKmer Fuzzy Query Test");
    println!("================================");

    // Create a simple test database
    println!("Creating test database...");
    let header = rustkmer::database::format::DatabaseHeader::new(13, 1000, true);
    let mut database = RKDatabase::new(header);

    // Add some test k-mers
    let test_kmers = vec![
        "ATGCGATGCTAGCA",
        "ATGCGATGCTAGCG",
        "ATGCGATGCTAGCC",
        "TTGCGATGCTAGCA",
        "GCGATGCTAGCATG",
    ];

    // Convert to k-mer entries (simplified)
    for (i, kmer) in test_kmers.iter().enumerate() {
        let kmer_value = rustkmer::kmer::encoding::encode_kmer(kmer)?;
        let entry = rustkmer::database::format::KmerEntry::new(kmer_value, (i + 1) as u32 * 10);
        database.entries.push(entry);
    }

    database.header.total_kmers = database.entries.len() as u64;

    println!("✅ Database created with {} k-mers", database.entries.len());

    // Create fuzzy query engine
    let engine = FuzzyQueryEngine::new(database);

    // Test 1: Exact match
    println!("\n🔍 Test 1: Exact match query");
    let query1 = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 0);
    match engine.execute_query(&query1) {
        Ok(result) => {
            println!("✅ Query executed successfully");
            println!("   Total matches: {}", result.total_count);
            println!("   Individual matches: {}", result.individual_matches.len());
            for (i, m) in result.individual_matches.iter().enumerate() {
                println!("   Match {}: {} (count: {})", i + 1, m.sequence, m.count);
            }
        }
        Err(e) => println!("❌ Query failed: {}", e),
    }

    // Test 2: Single wildcard
    println!("\n🔍 Test 2: Single wildcard query");
    let query2 = FuzzyQuery::new("ATGCGATGCTAGCN", 13, 0);
    match engine.execute_query(&query2) {
        Ok(result) => {
            println!("✅ Query executed successfully");
            println!("   Total matches: {}", result.total_count);
            println!("   Variants generated: {}", result.query_metadata.variants_generated);
            println!("   Individual matches: {}", result.individual_matches.len());
            for (i, m) in result.individual_matches.iter().enumerate() {
                println!("   Match {}: {} (count: {})", i + 1, m.sequence, m.count);
            }
        }
        Err(e) => println!("❌ Query failed: {}", e),
    }

    // Test 3: Mutation tolerance
    println!("\n🔍 Test 3: Mutation tolerance query");
    let query3 = FuzzyQuery::new("ATGCGATGCTAGCA", 13, 1);
    match engine.execute_query(&query3) {
        Ok(result) => {
            println!("✅ Query executed successfully");
            println!("   Total matches: {}", result.total_count);
            println!("   Variants generated: {}", result.query_metadata.variants_generated);
            println!("   Individual matches: {}", result.individual_matches.len());
            for (i, m) in result.individual_matches.iter().enumerate() {
                println!("   Match {}: {} (count: {})", i + 1, m.sequence, m.count);
            }
        }
        Err(e) => println!("❌ Query failed: {}", e),
    }

    // Test 4: Length normalization (shorter query)
    println!("\n🔍 Test 4: Length normalization (shorter query)");
    let query4 = FuzzyQuery::new("ATGCGATG", 13, 0);
    match engine.execute_query(&query4) {
        Ok(result) => {
            println!("✅ Query executed successfully");
            println!("   Total matches: {}", result.total_count);
            println!("   Variants generated: {}", result.query_metadata.variants_generated);
            println!("   Individual matches: {}", result.individual_matches.len());
        }
        Err(e) => println!("❌ Query failed: {}", e),
    }

    // Test 5: Combined wildcards and mutations
    println!("\n🔍 Test 5: Combined wildcards and mutations");
    let query5 = FuzzyQuery::new("ATGCGATGCTN", 13, 1);
    match engine.execute_query(&query5) {
        Ok(result) => {
            println!("✅ Query executed successfully");
            println!("   Total matches: {}", result.total_count);
            println!("   Variants generated: {}", result.query_metadata.variants_generated);
            println!("   Individual matches: {}", result.individual_matches.len());
            println!("   Query time: {}ms", result.query_metadata.query_time_ms);
        }
        Err(e) => println!("❌ Query failed: {}", e),
    }

    println!("\n🎉 Fuzzy query test completed successfully!");
    Ok(())
}