# CLI API Contract: Stats Command

## Command Definition

```bash
rustkmer stats [OPTIONS] <DATABASE>
```

## Arguments

### Positional Arguments

| Name | Type | Required | Description |
|------|------|----------|-------------|
| DATABASE | String | Yes | Path to the RKDB database file |

### Options

| Flag | Short | Long | Type | Default | Description |
|------|-------|------|------|---------|-------------|
| --format | -f | --format | String | "text" | Output format: text, json, csv, tsv |
| --output | -o | --output | Path | None | Output file (stdout if not specified) |
| --detailed | | --detailed | Flag | false | Include detailed frequency distribution |
| --max-bins | | --max-bins | Number | 1000 | Maximum bins for frequency distribution |
| --approximate | | --approximate | Flag | false | Use approximate median (faster, less memory) |
| --progress | -p | --progress | Flag | false | Show progress bar |

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Statistics calculated and output successfully |
| 1 | File Error | Database file not found or unreadable |
| 2 | Format Error | Invalid or corrupted RKDB database |
| 3 | Empty Database | Database contains no k-mers |
| 4 | Memory Error | Insufficient memory for calculation |
| 5 | Output Error | Unable to write output |

## Output Formats

### Text Format (Default)

```
Database Statistics
===================
Database: /path/to/database.rkdb
K-mer size: 31
Canonical: true
Sorted: false
Total k-mers: 4294967295
Unique k-mers: 1000000
Min count: 1
Max count: 100
Mean count: 42.94
Median count: 35.50
Processing time: 2.34s
Peak memory: 45.2MB

Frequency Distribution:
Count    Frequency
1        100000
2        95000
3        90000
...
100      1000
```

### JSON Format

```json
{
  "database_file": "/path/to/database.rkdb",
  "kmer_size": 31,
  "canonical": true,
  "sorted": false,
  "total_kmers": 4294967295,
  "unique_kmers": 1000000,
  "min_count": 1,
  "max_count": 100,
  "mean_count": 42.94,
  "median_count": 35.50,
  "frequency_distribution": [
    [1, 100000],
    [2, 95000],
    [3, 90000],
    ...
    [100, 1000]
  ],
  "processing_time": "2.34s",
  "memory_peak_bytes": 47392832
}
```

### CSV Format

```csv
database_file,kmer_size,canonical,sorted,total_kmers,unique_kmers,min_count,max_count,mean_count,median_count,processing_time,memory_peak_bytes
/path/to/database.rkdb,31,true,false,4294967295,1000000,1,100,42.94,35.50,2.34,47392832
```

### TSV Format

```tsv
database_file	kmer_size	canonical	sorted	total_kmers	unique_kmers	min_count	max_count	mean_count	median_count	processing_time	memory_peak_bytes
/path/to/database.rkdb	31	true	false	4294967295	1000000	1	100	42.94	35.50	2.34	47392832
```

## Error Messages

### File Not Found
```
Error: Database file not found: /path/to/nonexistent.rkdb
Hint: Check that the file path is correct and the file exists
```

### Invalid Format
```
Error: Invalid database format: Not a valid RKDB file
Hint: Use 'rustkmer check <file>' to validate database format
```

### Empty Database
```
Error: Database empty: no k-mers found in database
Hint: The database file exists but contains no k-mer data
```

### Memory Error
```
Error: Memory limit exceeded: required 2048MB, limit 2000MB
Hint: Try using --approximate or reducing --max-bins
```

## Usage Examples

### Basic statistics
```bash
rustkmer stats genome.rkdb
```

### JSON output to file
```bash
rustkmer stats -f json -o stats.json genome.rkdb
```

### Detailed frequency distribution
```bash
rustkmer stats --detailed --max-bins 10000 genome.rkdb
```

### Approximate median for large database
```bash
rustkmer stats --approximate --progress huge_db.rkdb
```

### CSV output for spreadsheet analysis
```bash
rustkmer stats -f csv -o analysis.csv genome.rkdb
```

## Performance Notes

1. **Memory Usage**: Approximately 10KB base + O(max_bins) for frequency distribution
2. **Processing Time**: O(N) where N is number of k-mers
3. **Parallelization**: Uses multiple cores when available
4. **Progress Bar**: Shown for operations taking >1 second when --progress flag used
5. **Approximation Mode**: Reduces memory usage by ~50% with <1% accuracy loss

## Integration Guidelines

### Piping to Other Commands
```bash
# Extract max count
rustkmer stats -f json genome.rkdb | jq '.max_count'

# Get unique k-mer count
rustkmer stats -f tsv genome.rkdb | cut -f6
```

### Using in Scripts
```bash
#!/bin/bash
DB_PATH=$1
stats=$(rustkmer stats -f json "$DB_PATH")
total=$(echo "$stats" | jq -r '.total_kmers')
unique=$(echo "$stats" | jq -r '.unique_kmers')
echo "Total: $total, Unique: $unique"
```

### Batch Processing
```bash
for db in *.rkdb; do
    rustkmer stats -f csv "$db" > "${db%.rkdb}_stats.csv"
done
```