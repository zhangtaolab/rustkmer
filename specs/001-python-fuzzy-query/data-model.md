# Data Model: Python Fuzzy Query API

## Core Entities

### FuzzyMatchResult
Represents a single k-mer match within mutation tolerance.

**Attributes**:
- `kmer: str` - The matched k-mer sequence
- `count: int` - Number of occurrences in database
- `distance: int` - Hamming distance from query (0 = exact match)
- `mutations: List[str]` - List of mutations from query to this match

**Validation Rules**:
- kmer must contain only A, T, C, G characters
- kmer length must match database k-mer size
- distance must be >= 0 and <= mutation tolerance
- count must be >= 0

**Methods**:
- `is_exact_match: bool` - Property: returns True if distance == 0
- `to_dict() -> Dict` - Convert to dictionary representation
- `to_json() -> str` - Serialize to JSON string

### FuzzyQueryResult
Contains all matches for a single fuzzy query.

**Attributes**:
- `query_kmer: str` - The original query k-mer
- `exact_match: Optional[FuzzyMatchResult]` - Exact match if found
- `matches: List[FuzzyMatchResult]` - All matches within tolerance
- `total_matches: int` - Total number of matches found
- `mutation_tolerance: int` - Maximum distance allowed
- `database_path: str` - Path to queried database

**Methods**:
- `get_matches_by_distance() -> Dict[int, List[FuzzyMatchResult]]` - Group matches by distance
- `get_top_matches(n: int) -> List[FuzzyMatchResult]` - Get N matches by highest count
- `to_table(max_rows: Optional[int]) -> str` - Format as readable table
- `to_json() -> str` - Serialize to JSON

**Properties**:
- `has_exact_match: bool` - Whether exact match exists
- `fuzzy_matches: List[FuzzyMatchResult]` - Matches with distance > 0
- `match_count: int` - Sum of all match counts

### FuzzyBatchResult
Aggregates results from multiple fuzzy queries.

**Attributes**:
- `query_results: List[FuzzyQueryResult]` - Results for each query
- `total_queries: int` - Number of queries processed
- `total_matches: int` - Total matches across all queries
- `database_path: str` - Path to queried database

**Properties**:
- `queries_with_exact_matches: int` - Count of queries with exact matches
- `queries_with_any_matches: int` - Count of queries with any matches

**Methods**:
- `get_summary_table() -> str` - Format batch summary as table
- `to_json() -> str` - Serialize batch to JSON

## State Transitions

### Query Processing Flow
```
Input k-mer → Validation → CLI Execution → Output Parsing → Result Object
```

1. **Validation Phase**:
   - Check k-mer format (DNA characters only)
   - Verify length matches database
   - Validate mutation tolerance range (0-5)
   - Check within configurable limits

2. **Execution Phase**:
   - Construct CLI command with format options
   - Execute with timeout
   - Capture stdout/stderr

3. **Parsing Phase**:
   - Parse CLI output format
   - Apply pagination (default: 10,000 match limit)
   - Create FuzzyMatchResult objects
   - Populate FuzzyQueryResult

## Relationships

```
Database
  ├── fuzzy_query(kmer, mutations, max_workers) → FuzzyQueryResult
  │   └── matches → List[FuzzyMatchResult]
  └── fuzzy_query_batch(kmers, mutations, max_workers) → FuzzyBatchResult
      └── query_results → List[FuzzyQueryResult]
```

## Constraints

### Performance
- Memory usage scales O(n) with number of matches returned
- Batch processing uses parallel execution with configurable worker threads
- Maximum 5 mutations tolerance per requirement
- Default pagination limit: 10,000 matches

### Consistency
- All distances calculated using Hamming distance
- Mutation format standardized (e.g., "A->T at position 5")
- Output formats consistent with existing query API
- Error handling patterns match existing python/rustkmer conventions

### Memory Management
- Result pagination prevents memory overflow
- Linear scaling target: <1GB for 1000 k-mers with 2 mutations
- Lazy loading of mutation details in large result sets