use std::collections::HashSet;
use rand::{Rng, SeedableRng};
use rand::rngs::StdRng;
use serde::{Deserialize, Serialize};

/// k-mer 生成器配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KmerGeneratorConfig {
    /// k-mer 长度
    pub kmer_length: usize,
    /// 生成数量
    pub count: usize,
    /// 随机种子（可选）
    pub seed: Option<u64>,
    /// 是否包含重复的 k-mers
    pub allow_duplicates: bool,
    /// GC 含量范围 (0.0 - 1.0)
    pub gc_content_range: (f64, f64),
    /// 包含同聚物的比例 (0.0 - 1.0)
    pub homopolymer_ratio: f64,
}

impl Default for KmerGeneratorConfig {
    fn default() -> Self {
        Self {
            kmer_length: 31,
            count: 100,
            seed: Some(42),
            allow_duplicates: false,
            gc_content_range: (0.4, 0.6),
            homopolymer_ratio: 0.1,
        }
    }
}

/// k-mer 生成器
pub struct KmerGenerator {
    config: KmerGeneratorConfig,
    rng: StdRng,
}

impl KmerGenerator {
    /// 创建新的 k-mer 生成器
    pub fn new(config: KmerGeneratorConfig) -> Self {
        let seed = config.seed.unwrap_or(42);
        let rng = StdRng::seed_from_u64(seed);

        Self { config, rng }
    }

    /// 使用默认配置创建生成器
    pub fn with_defaults(count: usize) -> Self {
        let mut config = KmerGeneratorConfig::default();
        config.count = count;
        Self::new(config)
    }

    /// 生成指定数量的 k-mers
    pub fn generate(&mut self) -> Vec<String> {
        let mut kmers = Vec::new();
        let mut seen = HashSet::new();

        while kmers.len() < self.config.count {
            let kmer = self.generate_single_kmer();

            if !self.config.allow_duplicates {
                if seen.contains(&kmer) {
                    continue;
                }
                seen.insert(kmer.clone());
            }

            kmers.push(kmer);
        }

        kmers
    }

    /// 生成单个 k-mer
    pub fn generate_single_kmer(&mut self) -> String {
        // 决定是否生成同聚物
        if self.rng.gen::<f64>() < self.config.homopolymer_ratio {
            self.generate_homopolymer_kmer()
        } else {
            self.generate_balanced_kmer()
        }
    }

    /// 生成平衡的 k-mer（控制 GC 含量）
    pub fn generate_balanced_kmer(&mut self) -> String {
        let target_gc = self.rng.gen_range(
            self.config.gc_content_range.0..=self.config.gc_content_range.1
        );
        let gc_count = (target_gc * self.config.kmer_length as f64) as usize;

        let mut kmer = Vec::new();
        for _ in 0..gc_count {
            kmer.push(if self.rng.gen() { 'G' } else { 'C' });
        }
        for _ in 0..(self.config.kmer_length - gc_count) {
            kmer.push(if self.rng.gen() { 'A' } else { 'T' });
        }

        // 随机打乱顺序
        for i in (1..kmer.len()).rev() {
            let j = self.rng.gen_range(0..=i);
            kmer.swap(i, j);
        }

        kmer.into_iter().collect()
    }

    /// 生成同聚物 k-mer（连续相同碱基）
    pub fn generate_homopolymer_kmer(&mut self) -> String {
        let base = ['A', 'T', 'C', 'G'][self.rng.gen_range(0..4)];
        base.to_string().repeat(self.config.kmer_length)
    }

    /// 生成特定模式的 k-mers
    pub fn generate_pattern_kmers(&mut self, pattern: &str) -> Vec<String> {
        let mut kmers = Vec::new();
        let base_kmer = pattern.chars().cycle()
            .take(self.config.kmer_length)
            .collect::<String>();

        // 生成变体
        for i in 0..self.config.count {
            let mut kmer = base_kmer.clone();

            // 在随机位置引入变异
            if self.rng.gen::<f64>() < 0.3 {
                let pos = self.rng.gen_range(0..self.config.kmer_length);
                let bases = ['A', 'T', 'C', 'G'];
                kmer.replace_range(pos..=pos, &bases[self.rng.gen_range(0..4)].to_string());
            }

            kmers.push(kmer);
        }

        kmers
    }

    /// 从现有序列生成 k-mers
    pub fn generate_from_sequence(&self, sequence: &str) -> Vec<String> {
        let seq = sequence.to_uppercase();
        let mut kmers = HashSet::new();

        for i in 0..=(seq.len().saturating_sub(self.config.kmer_length)) {
            let kmer = &seq[i..i + self.config.kmer_length];

            // 检查是否包含非 ATCG 字符
            if kmer.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')) {
                kmers.insert(kmer.to_string());
            }
        }

        // 转换为向量并限制数量
        kmers.into_iter().take(self.config.count).collect()
    }

    /// 生成反向互补 k-mers
    pub fn generate_reverse_complements(&self, kmers: &[String]) -> Vec<String> {
        kmers.iter()
            .map(|kmer| self.reverse_complement(kmer))
            .collect()
    }

    /// 计算反向互补序列
    pub fn reverse_complement(&self, kmer: &str) -> String {
        kmer.chars()
            .rev()
            .map(|c| match c {
                'A' => 'T',
                'T' => 'A',
                'C' => 'G',
                'G' => 'C',
                'a' => 'T',
                't' => 'A',
                'c' => 'G',
                'g' => 'C',
                _ => 'N', // 对于未知字符
            })
            .collect()
    }

    /// 生成 Hamming 距离为 1 的变体
    pub fn generate_hamming_variants(&self, kmer: &str, distance: usize) -> Vec<String> {
        let mut variants = HashSet::new();
        let bases = ['A', 'T', 'C', 'G'];

        // 递归生成指定距离的变体
        self.generate_hamming_recursive(
            kmer,
            distance,
            0,
            &mut 0,
            &mut variants,
            &bases
        );

        variants.into_iter().collect()
    }

    /// 递归生成 Hamming 距离变体
    fn generate_hamming_recursive(
        &self,
        kmer: &str,
        remaining_distance: usize,
        position: usize,
        current_distance: &mut usize,
        variants: &mut HashSet<String>,
        bases: &[char],
    ) {
        if *current_distance == remaining_distance {
            variants.insert(kmer.to_string());
            return;
        }

        if position >= kmer.len() {
            return;
        }

        // 保持当前位置
        self.generate_hamming_recursive(
            kmer,
            remaining_distance,
            position + 1,
            current_distance,
            variants,
            bases,
        );

        // 变异当前位置
        let original_char = kmer.chars().nth(position).unwrap();
        for &base in bases {
            if base != original_char {
                let mut modified = kmer.to_string();
                modified.replace_range(position..=position, &base.to_string());

                *current_distance += 1;
                self.generate_hamming_recursive(
                    &modified,
                    remaining_distance,
                    position + 1,
                    current_distance,
                    variants,
                    bases,
                );
                *current_distance -= 1;
            }
        }
    }

    /// 分析 k-mer 集合
    pub fn analyze_kmers(&self, kmers: &[String]) -> KmerAnalysis {
        let mut analysis = KmerAnalysis::default();

        for kmer in kmers {
            analysis.total_kmers += 1;
            analysis.length_distribution
                .entry(kmer.len())
                .and_modify(|e| *e += 1)
                .or_insert(1);

            // 计算 GC 含量
            let gc_count = kmer.chars()
                .filter(|&c| c == 'G' || c == 'C')
                .count();
            let gc_content = gc_count as f64 / kmer.len() as f64;
            analysis.gc_content_sum += gc_content;

            // 检查同聚物
            let has_homopolymer = kmer.chars()
                .collect::<Vec<char>>()
                .windows(4)
                .any(|w| w.iter().all(|&c| c == w[0]));
            if has_homopolymer {
                analysis.homopolymer_count += 1;
            }

            // 检查重复模式
            let half_len = kmer.len() / 2;
            if kmer.len() >= 4 && kmer.len() % 2 == 0 {
                let first_half = &kmer[..half_len];
                let second_half = &kmer[half_len..];
                if first_half == second_half {
                    analysis.repeated_pattern_count += 1;
                }
            }

            // 统计碱基使用
            for c in kmer.chars() {
                *analysis.base_usage.entry(c).or_insert(0) += 1;
            }
        }

        analysis.avg_gc_content = analysis.gc_content_sum / kmers.len() as f64;

        analysis
    }
}

/// k-mer 分析结果
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct KmerAnalysis {
    /// 总 k-mer 数
    pub total_kmers: usize,
    /// 长度分布
    pub length_distribution: std::collections::HashMap<usize, usize>,
    /// 平均 GC 含量
    pub avg_gc_content: f64,
    /// GC 含量总和
    pub gc_content_sum: f64,
    /// 同聚物数量
    pub homopolymer_count: usize,
    /// 重复模式数量
    pub repeated_pattern_count: usize,
    /// 碱基使用统计
    pub base_usage: std::collections::HashMap<char, usize>,
}

/// 预定义的测试 k-mer 集合
pub struct TestKmerSets;

impl TestKmerSets {
    /// 获取常用的测试 k-mers
    pub fn common_kmers() -> Vec<String> {
        vec![
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_string(),
            "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT".to_string(),
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC".to_string(),
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG".to_string(),
            "ATCGATCGATCGATCGATCGATCGATCGATCG".to_string(),
            "CGATCGATCGATCGATCGATCGATCGATCGA".to_string(),
            "GATCGATCGATCGATCGATCGATCGATCGAT".to_string(),
            "TATATATATATATATATATATATATATATAT".to_string(),
            "CGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC".to_string(),
            "ATATATATATATATATATATATATATATATA".to_string(),
        ]
    }

    /// 获取边界测试 k-mers
    pub fn edge_case_kmers() -> Vec<String> {
        vec![
            "A".repeat(31),
            "T".repeat(31),
            "C".repeat(31),
            "G".repeat(31),
            "AT".repeat(15) + "A",
            "CG".repeat(15) + "C",
            "GC".repeat(15) + "G",
            "TA".repeat(15) + "T",
        ]
    }

    /// 获取包含混合模式的 k-mers
    pub fn mixed_pattern_kmers() -> Vec<String> {
        vec![
            "AAAAATTTTTGGGGGCCCCCAAAAATTTTT".to_string(),
            "ATATATATATATATATATATATATATATAT".to_string(),
            "ATCGATCGATCGATCGATCGATCGATCGAT".to_string(),
            "AAAATTTTGGGGCCCCAAAATTTTGGGG".to_string(),
            "ATGCATGCATGCATGCATGCATGCATGCAT".to_string(),
        ]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kmer_generation() {
        let mut generator = KmerGenerator::with_defaults(10);
        let kmers = generator.generate();

        assert_eq!(kmers.len(), 10);

        for kmer in &kmers {
            assert_eq!(kmer.len(), 31);
            assert!(kmer.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')));
        }
    }

    #[test]
    fn test_reverse_complement() {
        let generator = KmerGenerator::new(KmerGeneratorConfig::default());
        let kmer = "ATCGATCGATCGATCGATCGATCGATCGATCG";
        let rc = generator.reverse_complement(kmer);

        assert_eq!(rc, "CGATCGATCGATCGATCGATCGATCGATAT");
    }

    #[test]
    fn test_hamming_variants() {
        let generator = KmerGenerator::new(KmerGeneratorConfig::default());
        let kmer = "AAAAA";
        let variants = generator.generate_hamming_variants(kmer, 1);

        // 应该有 3*5 = 15 个变体（每个位置3种变异）
        assert_eq!(variants.len(), 15);

        // 验证所有变体的 Hamming 距离都是1
        for variant in &variants {
            let distance = kmer.chars()
                .zip(variant.chars())
                .map(|(a, b)| if a != b { 1 } else { 0 })
                .sum::<usize>();
            assert_eq!(distance, 1);
        }
    }

    #[test]
    fn test_kmer_analysis() {
        let kmers = vec![
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_string(),
            "ATCGATCGATCGATCGATCGATCGATCGATCG".to_string(),
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG".to_string(),
        ];

        let generator = KmerGenerator::new(KmerGeneratorConfig::default());
        let analysis = generator.analyze_kmers(&kmers);

        assert_eq!(analysis.total_kmers, 3);
        assert!(analysis.avg_gc_content > 0.0);
        assert!(analysis.homopolymer_count > 0);
    }
}