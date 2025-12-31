# PyO3 Fuzzy Query API Contracts

## API Overview

The PyO3 fuzzy query API extends the existing rustkmer Python bindings to provide N-wildcard pattern matching capabilities. The API is designed to integrate seamlessly with existing PyDatabase functionality while providing direct access to Rust's high-performance fuzzy query engine.

## Core Classes

### PyFuzzyQuery

**Purpose**: Main interface for executing fuzzy k-mer queries with N-wildcard support

**Constructor**:
```python
PyFuzzyQuery(database: PyDatabase) -> PyFuzzyQuery
```
- **Parameters**: 
  - `database`: PyDatabase instance (must be loaded)
- **Returns**: PyFuzzyQuery instance
- **Raises**: 
  - `ValueError`: If database is not loaded
  - `DatabaseError`: If database cannot be accessed

**Methods**:

#### `set_position_mutations(position_config: Optional[str] = None) -> None`
Configure position-specific mutation constraints.
- **Parameters**:
  - `position_config`: String in format "positions:limit" or "pos1,pos2:limit;pos3,pos4:limit"
  - Examples: "2,3,4:1" or "4-7:1;10,12:2"
- **Raises**:
  - `ValueError`: If position configuration format is invalid
  - `IndexError`: If positions exceed query pattern length

#### `fuzzy_query(pattern: str, max_mutations: int, max_results: Optional[int] = None) -> PyFuzzyResult`
Execute fuzzy query with N-wildcard support.
- **Parameters**:
  - `pattern`: Query pattern with optional N wildcards (e.g., "GANNNGA")
  - `max_mutations`: Maximum Hamming distance tolerance (0-5)
  - `max_results`: Optional limit on number of results returned
- **Returns**: PyFuzzyResult object containing all matches
- **Raises**:
  - `InvalidKmerError`: If pattern contains invalid characters
  - `InvalidMutationToleranceError`: If max_mutations is out of range
  - `CombinatorialExplosionError`: If wildcard expansion would exceed limits

---

### PyFuzzyResult

**Purpose**: Container for fuzzy query results with metadata and individual matches

**Properties** (read-only):
- `query_kmer: str` - Original query pattern
- `exact_match: Optional[PyFuzzyMatch]` - Exact match if found
- `matches: List[PyFuzzyMatch]` - All fuzzy matches
- `total_matches: int` - Total count of matches
- `mutation_tolerance: int` - Mutation tolerance used

**Methods**:

#### `get_matches_by_distance(distance: int) -> List[PyFuzzyMatch]`
Get matches filtered by specific Hamming distance.
- **Parameters**:
  - `distance`: Target Hamming distance
- **Returns**: List of matches with specified distance
- **Raises**: `ValueError`: If distance is negative

#### `get_top_matches(limit: int = 10) -> List[PyFuzzyMatch]`
Get top matches by count (most frequent k-mers).
- **Parameters**:
  - `limit`: Maximum number of matches to return
- **Returns**: List of matches sorted by count (descending)

---

### PyFuzzyMatch

**Purpose**: Individual fuzzy match result with detailed information

**Properties** (read-only):
- `kmer: str` - Matched k-mer sequence
- `count: int` - Occurrence count in database
- `distance: int` - Hamming distance from query
- `mutations: List[str]` - List of mutations applied (format: "A>T")
- `match_type: str` - Type of match ("exact", "wildcard", "mutation", "length_norm")

**Methods**:

#### `get_mutation_details() -> List[Dict[str, Any]]`
Get detailed mutation information.
- **Returns**: List of dictionaries with keys:
  - `position`: Mutation position (0-based)
  - `original`: Original nucleotide
  - `mutated`: Mutated nucleotide
  - `type`: Type of mutation

---

## Integration with PyDatabase

### Shared Database Usage
The PyFuzzyQuery is designed to work with the same PyDatabase instance used for regular queries:

```python
# Load database once
db = PyDatabase("database.rkdb", LoadMode.Preload)

# Use for regular queries
result = db.query("ATCG")

# Use for fuzzy queries (same database instance)
fuzzy = PyFuzzyQuery(db)
fuzzy_result = fuzzy.fuzzy_query("GANNNGA", max_mutations=1)
```

### Database Lifecycle
- Database must remain loaded during PyFuzzyQuery usage
- Database cleanup automatically cleans up associated fuzzy queries
- No explicit coordination required between query and fuzzy_query operations

## Error Handling Contract

### Exception Hierarchy
```python
RustKmerError (base exception)
├── InvalidKmerError
├── InvalidMutationToleranceError
├── DatabaseError
├── QueryError
├── InvalidPositionMutationError
└── CombinatorialExplosionError
```

### Error Scenarios and Responses

1. **Invalid Pattern**
   - **Condition**: Pattern contains non-DNA characters or wrong length
   - **Response**: `InvalidKmerError` with descriptive message
   - **Example**: "Pattern 'ATCGX' contains invalid character 'X'"

2. **Excessive Mutations**
   - **Condition**: max_mutations > 5 or > kmer_size/2
   - **Response**: `InvalidMutationToleranceError`
   - **Example**: "Mutation tolerance 10 exceeds maximum allowed (6)"

3. **Combinatorial Explosion**
   - **Condition**: Wildcard expansion would generate >10,000 variants
   - **Response**: `CombinatorialExplosionError`
   - **Example**: "Pattern 'NNNNNNNNNN' would generate 1,048,576 variants (limit: 10,000)"

4. **Invalid Position Configuration**
   - **Condition**: Position indices out of bounds or malformed
   - **Response**: `InvalidPositionMutationError`
   - **Example**: "Position 20 exceeds pattern length 13"

## Performance Contract

### Response Time Guarantees
- **Simple queries** (≤2 wildcards): < 100ms
- **Complex queries** (3-5 wildcards): < 2 seconds
- **Large databases** (millions of k-mers): Linear scaling with database size

### Memory Usage Guarantees
- **Database sharing**: No additional memory for shared database
- **Wildcard expansion**: Memory usage proportional to 4^n where n = number of wildcards
- **Result storage**: Memory proportional to number of matches found

### Throughput Guarantees
- **PyO3 vs Subprocess**: Minimum 5x performance improvement
- **Batch processing**: Linear scaling with number of queries
- **Concurrent usage**: Thread-safe for read-only operations

## Usage Examples

### Basic N-Wildcard Query
```python
from rustkmer_pyo3 import PyDatabase, PyFuzzyQuery, LoadMode

# Load database
db = PyDatabase("genome.rkdb", LoadMode.Preload)

# Create fuzzy query engine
fuzzy = PyFuzzyQuery(db)

# Query with N wildcards
result = fuzzy.fuzzy_query("GANNNGA", max_mutations=0)

print(f"Found {result.total_matches} matches")
for match in result.matches:
    print(f"{match.kmer}: {match.count} (distance={match.distance})")
```

### Advanced Position-Specific Mutations
```python
# Configure position-specific constraints
fuzzy.set_position_mutations("2,3,4:1;8,9:2")

# Query with high tolerance but position constraints
result = fuzzy.fuzzy_query("GATCGATCGATCG", max_mutations=5)

# Filter results by distance
exact_matches = result.get_matches_by_distance(0)
single_mutations = result.get_matches_by_distance(1)

# Get top results
top_5 = result.get_top_matches(5)
```

### Performance Comparison
```python
import time

# PyO3 implementation
start = time.time()
db_pyo3 = PyDatabase("large_genome.rkdb", LoadMode.Preload)
fuzzy_pyo3 = PyFuzzyQuery(db_pyo3)
result_pyo3 = fuzzy_pyo3.fuzzy_query("GANNNNNNNNGA", max_mutations=1)
pyo3_time = time.time() - start

# Subprocess implementation (for comparison)
start = time.time()
from rustkmer import Database
db_subprocess = Database("large_genome.rkdb")
result_subprocess = db_subprocess.fuzzy_query("GANNNNNNNNGA", mutations=1)
subprocess_time = time.time() - start

speedup = subprocess_time / pyo3_time
print(f"PyO3: {pyo3_time:.3f}s, Subprocess: {subprocess_time:.3f}s, Speedup: {speedup:.1f}x")
```

## Testing Contract

### Required Test Coverage
- **Unit tests**: >90% coverage for PyO3 wrapper logic
- **Integration tests**: Database sharing, error propagation, API consistency
- **Performance tests**: Benchmarking against subprocess implementation
- **Edge case tests**: Large wildcards, memory constraints, error conditions

### Test Data Requirements
- **Small databases**: For basic functionality testing
- **Large databases**: For performance and scalability testing
- **Known patterns**: Expected results for validation testing
- **Edge cases**: Invalid inputs, boundary conditions

### Validation Criteria
- **Functional correctness**: Results match CLI implementation exactly
- **Performance targets**: Meet specified response time and memory usage goals
- **API consistency**: Error handling and behavior match PyDatabase patterns
- **Reliability**: No crashes or memory leaks under stress testing