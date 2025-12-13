# Test FASTA Data

This directory contains randomly generated FASTA files for testing rustkmer.

## FASTA Files:
- `tiny_test.fasta`: Very small file (10 sequences, 20-100bp each)
- `small_test.fasta`: Small file (50 sequences, 50-200bp each)
- `medium_test.fasta`: Medium file (100 sequences, 100-500bp each)
- `large_test.fasta`: Large file (200 sequences, 200-1000bp each)

All files contain randomly generated DNA sequences (A, T, C, G only).

## Generated RKDB Databases:
- `tiny_test.rkdb`: Database from tiny_test.fasta (k=7, 8KB)
- `small_test.rkdb`: Database from small_test.fasta (k=7, 88KB)
- `medium_test.rkdb`: Database from medium_test.fasta (k=7, 160KB)
- `large_test.rkdb`: Database from large_test.fasta (k=7, 164KB)

**Database Details:**
- K-mer size: 7 (optimal for short sequences)
- Canonical k-mers: Yes (forward/reverse complement considered)
- Format: Binary RKDB format
- Total size: ~420KB for all databases

## Usage:

### Using FASTA files:
```python
from rustkmer import Database

# Load a test database
db = Database("tiny_test.rkdb")
count = db.query("GCCGCGG")  # Query a 7-mer
```

### Using rustkmer CLI:
```bash
# Query databases
rustkmer query tiny_test.rkdb GCCGCGG ATCCTGA

# Generate new databases
rustkmer count -k 7 -i large_test.fasta -o new_database.rkdb --canonical
```

### Database Contents:
All databases contain 7-mer counts from their respective FASTA files, with canonical k-mer counting (forward and reverse complement sequences are considered the same).

Generated on: 1765625051.6467962
