# Quick Start Guide: Stats Command

## Overview

The `rustkmer stats` command calculates comprehensive statistics for RKDB databases, including k-mer counts, frequency distributions, and basic statistical measures.

## Prerequisites

- RustKmer CLI tool installed
- An RKDB database file (created with `rustkmer count`)

## Basic Usage

### Generate statistics for a database
```bash
rustkmer stats mydb.rkdb
```

This will display:
- Total k-mers (including duplicates)
- Number of unique k-mers
- Minimum, maximum, mean, and median counts
- Processing information

### Save statistics to a file
```bash
# Save human-readable report
rustkmer stats mydb.rkdb > stats_report.txt

# Save JSON format
rustkmer stats -f json -o stats.json mydb.rkdb

# Save CSV for spreadsheet analysis
rustkmer stats -f csv -o stats.csv mydb.rkdb
```

### Get detailed frequency distribution
```bash
# Include full frequency distribution (may be large)
rustkmer stats --detailed mydb.rkdb

# Limit frequency distribution to 1000 bins (default)
rustkmer stats --detailed --max-bins 1000 mydb.rkdb
```

### Work with large databases
```bash
# Show progress bar
rustkmer stats --progress large_db.rkdb

# Use approximate median (faster, less memory)
rustkmer stats --approximate huge_db.rkdb
```

## Common Use Cases

### 1. Check database quality
```bash
# Get basic statistics
rustkmer stats genome_assembly.rkdb

# Look for:
# - Total k-mers vs unique k-mers ratio
# - Distribution shape (evenness)
# - Maximum count (potential repeats)
```

### 2. Compare databases
```bash
# Create comparison script
for db in sample1.rkdb sample2.rkdb sample3.rkdb; do
    echo "=== $db ==="
    rustkmer stats -f json "$db" | jq '{total_kmers, unique_kmers, max_count}'
done
```

### 3. Export for analysis
```bash
# Create comprehensive CSV
rustkmer stats -f csv --detailed mydb.rkdb > analysis.csv

# The CSV includes all statistics in a single row,
# or use TSV for better tab separation
rustkmer stats -f tsv --detailed mydb.rkdb > analysis.tsv
```

### 4. Pipeline integration
```bash
# Extract specific statistics
MAX_COUNT=$(rustkmer stats -f json mydb.rkdb | jq -r '.max_count')
echo "Maximum k-mer count: $MAX_COUNT"

# Check if database meets criteria
UNIQUE=$(rustkmer stats -f json mydb.rkdb | jq -r '.unique_kmers')
if [ "$UNIQUE" -gt 1000000 ]; then
    echo "Database has sufficient unique k-mers"
fi
```

## Output Formats

### Text (Human-readable)
Default format, best for quick inspection
```
Database Statistics
===================
Database: mydb.rkdb
K-mer size: 31
Total k-mers: 100000000
Unique k-mers: 50000000
Min count: 1
Max count: 1000
Mean count: 2.00
Median count: 1.50
```

### JSON (Machine-readable)
Best for programmatic use and APIs
```json
{
  "total_kmers": 100000000,
  "unique_kmers": 50000000,
  "min_count": 1,
  "max_count": 1000,
  "mean_count": 2.0,
  "median_count": 1.5
}
```

### CSV/TSV (Data analysis)
Best for spreadsheets and data analysis tools
```csv
database_file,total_kmers,unique_kmers,min_count,max_count,mean_count,median_count
mydb.rkdb,100000000,50000000,1,1000,2.0,1.5
```

## Performance Tips

1. **Memory Usage**: Default uses <100MB regardless of database size
2. **Speed**: Use `--approximate` for faster median calculation
3. **Large Outputs**: Redirect to file instead of stdout for large datasets
4. **Batch Processing**: Process multiple databases in parallel

## Troubleshooting

### Empty database error
```bash
# Error: Database empty: no k-mers found
# Solution: Check if database was created correctly
rustkmer check mydb.rkdb
```

### Memory issues
```bash
# Error: Memory limit exceeded
# Solution: Use approximate mode or reduce bins
rustkmer stats --approximate --max-bins 100 huge_db.rkdb
```

### Slow processing
```bash
# Show progress to see if it's working
rustkmer stats --progress slow_db.rkdb

# Use approximate mode for faster processing
rustkmer stats --approximate slow_db.rkdb
```

## Examples

### Example 1: Analyze sequencing depth
```bash
# Calculate k-mer depth statistics
rustkmer stats -f json reads.rkdb | jq '
{
  "total_kmers": .total_kmers,
  "unique_kmers": .unique_kmers,
  "estimated_coverage": (.total_kmers / .unique_kmers)
}'
```

### Example 2: Check database completeness
```bash
# Verify database was created completely
rustkmer stats mydb.rkdb > stats.log
if grep -q "Error" stats.log; then
    echo "Database has issues"
    cat stats.log
else
    echo "Database is valid"
fi
```

### Example 3: Compare k-mer sizes
```bash
# Compare statistics across different k-mer sizes
for k in 21 31 51; do
    echo "=== k=$k ==="
    rustkmer -k $k count reads.fastq -o reads_k${k}.rkdb
    rustkmer stats reads_k${k}.rkdb | grep -E "(Total|Unique)"
done
```

## Integration Examples

### Python integration
```python
import subprocess
import json

def get_stats(database_path):
    result = subprocess.run(
        ["rustkmer", "stats", "-f", "json", database_path],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)

stats = get_stats("mydb.rkdb")
print(f"Total k-mers: {stats['total_kmers']:,}")
print(f"Unique k-mers: {stats['unique_kmers']:,}")
```

### R integration
```r
# Read stats into R data frame
stats_json <- system("rustkmer stats -f json mydb.rkdb", intern = TRUE)
stats <- jsonlite::fromJSON(stats_json)
print(data.frame(
  Total = stats$total_kmers,
  Unique = stats$unique_kmers,
  MaxCount = stats$max_count
))
```