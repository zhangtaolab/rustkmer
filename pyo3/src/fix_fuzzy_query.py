#!/usr/bin/env python3
"""Fix fuzzy_query.rs formatting strings"""

# Read file
with open('fuzzy_query.rs', 'r') as f:
    content = f.read()

# Fix the first to_csv method (lines 161-174)
# Original format string is missing arguments for the format specifiers
old_pattern1 = '''    fn to_csv(&self) -> PyResult<String> {
        let mut csv = format!("kmer,count,distance,match_type,mutation_positions\\n");

        if let Some(ref exact) = self.exact_match {
            csv = format!(
                "{}{},{},{},\\"{:?}\\"\\n",
                csv,
                exact.kmer,
                exact.count,
                exact.distance.unwrap_or(0),
                exact.match_type,
                exact.mutation_positions
            );
        }

        for match_item in &self.matches {
            if match_item.match_type == "exact" {
                if let Some(ref exact) = self.exact_match {
                    if match_item.kmer == exact.kmer {
                        continue;
                    }
                }
            }

            csv = format!(
                "{}{},{},{},\\"{:?}\\"\\n",
                csv,
                match_item.kmer,
                match_item.count,
                match_item.distance.unwrap_or(0),
                match_item.match_type,
                match_item.mutation_positions
            );
        }

        csv = format!("{}# query_kmer={}\\n", csv, self.query_kmer);
        csv = format!("{}# total_matches={}\\n", csv, self.total_matches);
        csv = format!("{}# mutation_tolerance={}\\n", csv, self.mutation_tolerance);
        csv = format!("{}# query_time_ms={}\\n", csv, self.query_time_ms);
        csv = format!(
            "{}# has_position_mutations={}\\n",
            csv, self.has_position_mutations
        );

        Ok(csv)
    }'''

new_pattern1 = '''    fn to_csv(&self) -> PyResult<String> {
        let mut csv = format!("kmer,count,distance,match_type,mutation_positions\\n");

        if let Some(ref exact) = self.exact_match {
            csv = format!(
                "{}{},{},{},{},\\"{:?}\\"\\n",
                csv,
                exact.kmer,
                exact.count,
                exact.distance.unwrap_or(0),
                exact.match_type,
                exact.mutation_positions
            );
        }

        for match_item in &self.matches {
            if match_item.match_type == "exact" {
                if let Some(ref exact) = self.exact_match {
                    if match_item.kmer == exact.kmer {
                        continue;
                    }
                }
            }

            csv = format!(
                "{}{},{},{},{},\\"{:?}\\"\\n",
                csv,
                match_item.kmer,
                match_item.count,
                match_item.distance.unwrap_or(0),
                match_item.match_type,
                match_item.mutation_positions
            );
        }

        csv = format!("{}# query_kmer={}\\n", csv, self.query_kmer);
        csv = format!("{}# total_matches={}\\n", csv, self.total_matches);
        csv = format!("{}# mutation_tolerance={}\\n", csv, self.mutation_tolerance);
        csv = format!("{}# query_time_ms={}\\n", csv, self.query_time_ms);
        csv = format!(
            "{}# has_position_mutations={}\\n",
            csv, self.has_position_mutations
        );

        Ok(csv)
    }'''

# Fix the first to_tsv method (lines 208-252)
# Original format string is missing arguments for the format specifiers
old_pattern2 = '''    fn to_tsv(&self) -> PyResult<String> {
        let mut tsv = format!("kmer\\tcount\\tdistance\\tmatch_type\\tmutation_positions\\n");

        if let Some(ref exact) = self.exact_match {
            tsv = format!(
                "{}\\t{}\\t{}\\t{}\\t{:?}\\n",
                tsv,
                exact.kmer,
                exact.count,
                exact.distance.unwrap_or(0),
                exact.match_type,
                exact.mutation_positions
            );
        }

        for match_item in &self.matches {
            if match_item.match_type == "exact" {
                if let Some(ref exact) = self.exact_match {
                    if match_item.kmer == exact.kmer {
                        continue;
                    }
                }
            }

            tsv = format!(
                "{}\\t{}\\t{}\\t{}\\t{:?}\\n",
                tsv,
                match_item.kmer,
                match_item.count,
                match_item.distance.unwrap_or(0),
                match_item.match_type,
                match_item.mutation_positions
            );
        }

        tsv = format!("{}# query_kmer={}\\n", tsv, self.query_kmer);
        tsv = format!("{}# total_matches={}\\n", tsv, self.total_matches);
        tsv = format!("{}# mutation_tolerance={}\\n", tsv, self.mutation_tolerance);
        tsv = format!("{}# query_time_ms={}\\n", tsv, self.query_time_ms);
        tsv = format!(
            "{}# has_position_mutations={}\\n",
            tsv, self.has_position_mutations
        );

        Ok(tsv)
    }'''

new_pattern2 = '''    fn to_tsv(&self) -> PyResult<String> {
        let mut tsv = format!("kmer\\tcount\\tdistance\\tmatch_type\\tmutation_positions\\n");

        if let Some(ref exact) = self.exact_match {
            tsv = format!(
                "{}\\t{}\\t{}\\t{}\\t{}\\t{:?}\\n",
                tsv,
                exact.kmer,
                exact.count,
                exact.distance.unwrap_or(0),
                exact.match_type,
                exact.mutation_positions
            );
        }

        for match_item in &self.matches {
            if match_item.match_type == "exact" {
                if let Some(ref exact) = self.exact_match {
                    if match_item.kmer == exact.kmer {
                        continue;
                    }
                }
            }

            tsv = format!(
                "{}\\t{}\\t{}\\t{}\\t{}\\t{:?}\\n",
                tsv,
                match_item.kmer,
                match_item.count,
                match_item.distance.unwrap_or(0),
                match_item.match_type,
                match_item.mutation_positions
            );
        }

        tsv = format!("{}# query_kmer={}\\n", tsv, self.query_kmer);
        tsv = format!("{}# total_matches={}\\n", tsv, self.total_matches);
        tsv = format!("{}# mutation_tolerance={}\\n", tsv, self.mutation_tolerance);
        tsv = format!("{}# query_time_ms={}\\n", tsv, self.query_time_ms);
        tsv = format!(
            "{}# has_position_mutations={}\\n",
            tsv, self.has_position_mutations
        );

        Ok(tsv)
    }'''

# Replace patterns
content = content.replace(old_pattern1, new_pattern1)
content = content.replace(old_pattern2, new_pattern2)

# Write fixed file
with open('fuzzy_query.rs', 'w') as f:
    f.write(content)

print("Fixed fuzzy_query.rs formatting strings")
