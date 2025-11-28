# CLI API Contract: Query Command

**Version**: 1.0
**Date**: 2025-11-28
**Status**: Implemented

## Command Overview

The `query` command provides k-mer lookup functionality compatible with jellyfish query interface.

## Command Signature

```bash
rustkmer query [OPTIONS] <DATABASE> [KMERS]...
```

## Parameters

### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `DATABASE` | String | Path to k-mer database file (.rkdb format) | `/data/genome.rkdb` |
| `KMERS` | String[] | K-mer sequences to query (optional) | `ATGCGATGCTAGCGCTAGCTA` |

### Optional Parameters

| Option | Short | Long | Type | Default | Description |
|--------|-------|------|------|---------|-------------|
| `--sequence` | `-s` | `--sequence` | String | None | Query k-mers from sequence file |
| `--output` | `-o` | `--output` | String | stdout | Output file path |
| `--interactive` | `-i` | `--interactive` | Boolean | false | Interactive query mode |
| `--load` | `-l` | `--load` | Boolean | false | Force pre-loading database |
| `--no-load` | `-L` | `--no-load` | Boolean | false | Disable pre-loading database |

## Usage Patterns

### Individual K-mer Query

```bash
rustkmer query database.rkdb ATGCGATGCTAGCGCTAGCTA
```

**Expected Output**:
```
ATGCGATGCTAGCGCTAGCTA	42
```

### Multiple K-mer Query

```bash
rustkmer query database.rkdb ATGCGATGCTAGC GCTAGCTAGATGC TGCAGCTAGCTGA
```

**Expected Output**:
```
ATGCGATGCTAGC	15
GCTAGCTAGATGC	23
TGCAGCTAGCTGA	0
```

### Sequence File Query

```bash
rustkmer query -s sequences.fa database.rkdb
```

**Expected Output**: All k-mers from `sequences.fa` with their counts.

### Interactive Mode

```bash
rustkmer query -i database.rkdb
```

**Expected Behavior**:
- Prompt for k-mer input
- Process each k-mer as entered
- Continue until EOF (Ctrl+D)

### Output Redirection

```bash
rustkmer query database.rkdb ATGCGATGCTAGC -o results.txt
```

**Expected Behavior**: Results written to `results.txt` instead of stdout.

## Input Validation

### K-mer Validation Rules

| Rule | Description | Error Message |
|------|-------------|--------------|
| Character validation | Only A, T, G, C allowed (case-insensitive) | `Invalid mer 'XYZ'` |
| Length validation | Must match database k-mer size | `Error: Invalid k-mer length` |
| Empty k-mer | K-mer cannot be empty | `Error: Empty k-mer` |

### Database Validation Rules

| Rule | Description | Error Message |
|------|-------------|--------------|
| File existence | Database file must exist | `Error: Database file not found: {path}` |
| File format | Must be valid .rkdb format | `Error: Invalid database format` |
| File permissions | Must be readable | `Error: Permission denied` |
| Version compatibility | Database version must be supported | `Error: Unsupported database version` |

## Output Format

### Success Output

**Format**: Tab-separated values
**Schema**: `{kmer}\t{count}`

**Examples**:
- Found k-mer: `ATGCGATGCTAGC\t42`
- Missing k-mer: `INVALIDMER\t0` (or error message)

### Error Output

**Format**: Error messages to stderr
**Style**: Jellyfish-compatible where applicable

**Examples**:
- Invalid k-mer: `Invalid mer 'ATXCG'`
- File not found: `Error: Database file not found: missing.rkdb`
- Format error: `Error: Invalid database magic number`

## Performance Modes

### Memory Mode (Pre-loading)

**Trigger**: `-l` flag or automatic detection
**Behavior**: Load entire database into memory
**Advantages**: Fastest query performance
**Disadvantages**: Higher memory usage
**Use Case**: Repeated queries on same database

### Disk Mode (Streaming)

**Trigger**: `-L` flag or large databases
**Behavior**: Binary search on disk with minimal memory
**Advantages**: Low memory usage
**Disadvantages**: Slower query performance
**Use Case**: Large databases or memory-constrained environments

### Auto Mode (Default)

**Trigger**: No explicit memory flags
**Behavior**: Intelligent mode selection based on database size and query patterns
**Advantages**: Balanced performance and memory usage
**Disadvantages**: May not be optimal for specific use cases

## Error Handling

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (invalid input, file not found, etc.) |
| 2 | Database format error |
| 3 | I/O error (disk read failure, permissions) |

### Error Recovery

**Individual Query Errors**: Continue processing other k-mers
**Database Errors**: Halt execution immediately
**I/O Errors**: Attempt graceful shutdown with error message

## Integration Examples

### Shell Script Integration

```bash
#!/bin/bash
# Query multiple k-mers and count results
RESULTS=$(rustkmer query database.rkdb ATGC TGCN CGAT 2>/dev/null)
COUNT=$(echo "$RESULTS" | wc -l)
echo "Found $COUNT k-mers"
```

### Pipeline Integration

```bash
# Generate k-mers and query them
echo -e "ATGC\nTGCG\nCGAT" | rustkmer query -i database.rkdb
```

### Makefile Integration

```makefile
query: database.rkdb
	rustkmer query database.rkdb $(KMERS) -o results.txt

%.txt: %.fa database.rkdb
	rustkmer query -s $< database.rkdb -o $@
```

## Compatibility Notes

### Jellyfish Compatibility

**Compatible Features**:
- Command-line argument patterns
- Output format (tab-separated)
- Error messages for invalid k-mers
- Interactive mode behavior

**Differences**:
- Database format (custom .rkdb vs .jf)
- Additional memory management options
- Enhanced error messages

### Version Compatibility

**Minimum Database Version**: 1.0
**Maximum Database Version**: 1.x
**Backward Compatibility**: Supported within major version
**Forward Compatibility**: Not guaranteed