use std::collections::HashSet;

#[derive(Debug, Clone, Default)]
pub struct PositionMutationGroup {
    pub positions: Vec<usize>,
    pub max_mutations: usize,
}

#[derive(Debug, Clone, Default)]
pub struct PositionMutationConfig {
    pub groups: Vec<PositionMutationGroup>,
}

fn main() {
    // Test ":1" format
    let input = ":1";
    let mut config = PositionMutationConfig::default();

    for (group_idx, group_str) in input.split(';').enumerate() {
        let group_str = group_str.trim();
        if group_str.is_empty() {
            continue;
        }

        let (positions_str, limit_str) = match group_str.split_once(':') {
            Some((pos_str, lim_str)) => (pos_str, lim_str),
            None => {
                println!("Invalid group format '{}'", group_str);
                continue;
            }
        };

        println!("positions_str: '{}', limit_str: '{}'", positions_str, limit_str);

        let positions: Vec<usize> = positions_str
            .split(',')
            .flat_map(|s| {
                let trimmed = s.trim();
                println!("  Processing part: '{}'", trimmed);
                if trimmed.is_empty() {
                    println!("    -> Empty, returning empty vec");
                    return Vec::new();
                }
                vec![1] // Simplified
            })
            .collect();

        let max_mutations: usize = limit_str.trim().parse().unwrap_or(0);

        println!("  Parsed positions: {:?}, max_mutations: {}", positions, max_mutations);

        config.groups.push(PositionMutationGroup {
            positions,
            max_mutations,
        });
    }

    println!("Final config: {:?}", config);
}
