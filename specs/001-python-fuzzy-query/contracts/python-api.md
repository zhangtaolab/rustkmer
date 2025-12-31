# Python API Contract: Fuzzy Query

## Database.fuzzy_query()

### Method Signature
```python
def fuzzy_query(
    self,
    kmer: str,
    mutations: int = 1,
    max_variants: Optional[int] = None,
    output_format: str = 'auto'
) -> FuzzyQueryResult
```

### Parameters
- `kmer` (str, required): The k-mer sequence to query
  - Must contain only A, T, C, G characters
  - Length must match database k-mer size
- `mutations` (int, optional, default=1): Maximum number of mutations allowed
  - Range: 0-5
  - 0 behaves like exact query
- `max_variants` (int, optional): Maximum number of variants to check
  - If None, no limit
  - Used for performance control
- `output_format` (str, optional, default='auto'): Output format for CLI
  - Options: 'auto', 'json', 'table', 'tsv'

### Returns
`FuzzyQueryResult` object containing:
- Query metadata (kmer, tolerance, database path)
- List of all matches within tolerance
- Exact match identification
- Helper methods for analysis

### Exceptions
- `InvalidKmerError`: k-mer contains invalid characters or wrong length
- `QueryError`: CLI command execution fails
- `DatabaseError`: Database is closed or inaccessible

### Examples
```python
db = Database("genome.rkdb")
result = db.fuzzy_query("ATCGATCG", mutations=2)

if result.has_exact_match:
    print(f"Exact match found with count: {result.exact_match.count}")

for distance, matches in result.get_matches_by_distance().items():
    print(f"Distance {distance}: {len(matches)} matches")
```

## Database.fuzzy_query_batch()

### Method Signature
```python
def fuzzy_query_batch(
    self,
    kmers: List[str],
    mutations: int = 1,
    max_variants: Optional[int] = None,
    max_workers: int = 4,
    output_format: str = 'auto'
) -> FuzzyBatchResult
```

### Parameters
- `kmers` (List[str], required): List of k-mer sequences to query
  - All k-mers must be valid
- `mutations` (int, optional, default=1): Maximum mutations per query
- `max_variants` (int, optional): Maximum variants per query
- `max_workers` (int, optional, default=4): Parallel subprocess workers
- `output_format` (str, optional): Output format for CLI commands

### Returns
`FuzzyBatchResult` object containing:
- List of FuzzyQueryResult objects
- Aggregate statistics
- Summary reporting methods

### Exceptions
- `InvalidKmerError`: Any k-mer in batch is invalid
- `DatabaseError`: Database is closed
- Query failures for individual k-mers are handled gracefully

### Examples
```python
kmers = ["ATCGATCG", "CGATCGAT", "GATCGATC"]
batch = db.fuzzy_query_batch(kmers, mutations=2, max_workers=8)

print(f"Processed {batch.total_queries} queries")
print(f"{batch.queries_with_exact_matches} had exact matches")

for result in batch.query_results:
    if result.matches:
        print(f"{result.query_kmer}: {len(result.matches)} variants")
```

## FuzzyQueryResult Methods

### to_table()
```python
def to_table(self, max_rows: Optional[int] = None) -> str
```
Format results as readable table.

### get_matches_by_distance()
```python
def get_matches_by_distance(self) -> Dict[int, List[FuzzyMatchResult]]
```
Group matches by Hamming distance.

### get_top_matches()
```python
def get_top_matches(self, n: int = 10) -> List[FuzzyMatchResult]
```
Return top N matches sorted by count.

## Output Formats

### JSON Structure
```json
{
  "query_kmer": "ATCGATCG",
  "exact_match": {
    "kmer": "ATCGATCG",
    "count": 42,
    "distance": 0,
    "mutations": []
  },
  "matches": [
    {
      "kmer": "ATCGATCA",
      "count": 15,
      "distance": 1,
      "mutations": ["G->A at position 6"]
    }
  ],
  "total_matches": 2,
  "mutation_tolerance": 1,
  "database_path": "/path/to/db.rkdb"
}
```