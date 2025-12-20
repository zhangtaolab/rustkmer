# Data Model: PyO3 Fuzzy Query Implementation

## Core Entities

### PyFuzzyQuery
**Purpose**: Main class for executing fuzzy k-mer queries with N-wildcard support
**Relationships**: 
- Uses: PyDatabase (shared instance)
- Produces: PyFuzzyResult
- Configured by: PositionMutationConfig

**Fields**:
- `database: Option<RKDatabase>` - Shared database instance
- `kmer_size: Option<usize>` - K-mer size from database
- `position_mutations: Option<PositionMutationConfig>` - Position-specific constraints

**State Transitions**:
1. `Created` → `Configured` (via `set_position_mutations`)
2. `Configured` → `QueryExecuted` (via `fuzzy_query`)
3. `QueryExecuted` → `Ready` (result consumed)

**Validation Rules**:
- Database must be loaded before query execution
- K-mer size must match database configuration
- Position mutations must be valid for query pattern

---

### PyFuzzyResult
**Purpose**: Container for fuzzy query results with metadata and individual matches
**Relationships**:
- Produced by: PyFuzzyQuery
- Contains: Vec<PyFuzzyMatch>
- References: Original query pattern

**Fields**:
- `query_kmer: String` - Original query pattern
- `exact_match: Option<PyFuzzyMatch>` - Exact match if found
- `matches: Vec<PyFuzzyMatch>` - All fuzzy matches
- `total_matches: usize` - Total count of matches
- `mutation_tolerance: u32` - Mutation tolerance used

**Validation Rules**:
- Total matches equals length of matches vector
- Exact match (if present) must have distance = 0
- All matches must have consistent mutation tolerance

---

### PyFuzzyMatch
**Purpose**: Individual fuzzy match result with detailed information
**Relationships**:
- Contained in: PyFuzzyResult
- Describes: Single k-mer match with mutations

**Fields**:
- `kmer: String` - Matched k-mer sequence
- `count: u32` - Occurrence count in database
- `distance: u32` - Hamming distance from query
- `mutations: Vec<String>` - List of mutations applied
- `match_type: String` - Type of match (exact, wildcard, mutation, length_norm)

**Validation Rules**:
- K-mer length must match query pattern length
- Distance must be ≥ 0 and ≤ mutation tolerance
- Mutations must be valid nucleotide changes
- Count must be ≥ 0

---

### PositionMutationConfig
**Purpose**: Configuration for position-specific mutation constraints
**Relationships**:
- Configures: PyFuzzyQuery behavior
- Used by: Rust PositionMutationConfig

**Fields**:
- `groups: Vec<PositionMutationGroup>` - Mutation constraint groups
- `global_max_mutations: Option<usize>` - Global mutation limit

**Validation Rules**:
- Position indices must be within query pattern bounds
- Groups must not overlap
- Mutation limits cannot exceed group size

---

### PositionMutationGroup
**Purpose**: Group of positions with shared mutation constraints
**Relationships**:
- Part of: PositionMutationConfig
- Contains: Position indices and limits

**Fields**:
- `positions: Vec<usize>` - Position indices (0-based, sorted)
- `max_mutations: usize` - Maximum mutations in this group
- `group_name: Option<String>` - Optional identifier

**Validation Rules**:
- Positions must be unique and sorted
- Max mutations cannot exceed positions count
- All positions must be valid for query pattern

## Data Flow

### Query Execution Flow
```
User Input (pattern, mutations) 
    ↓
PyFuzzyQuery.fuzzy_query()
    ↓
Validate input parameters
    ↓
Generate query expansion (wildcards + mutations)
    ↓
Execute against shared RKDatabase
    ↓
Collect and filter results
    ↓
Convert to PyFuzzyResult
    ↓
Return to Python caller
```

### Database Sharing Flow
```
PyDatabase("database.rkdb")
    ↓
Load RKDatabase into memory
    ↓
Create PyFuzzyQuery(db)
    ↓
Share database instance
    ↓
Execute both query() and fuzzy_query()
    ↓
Efficient resource utilization
```

## Error Handling Model

### Exception Hierarchy
```
RustKmerError (base)
├── InvalidKmerError
├── InvalidMutationToleranceError  
├── DatabaseError
├── QueryError
├── InvalidPositionMutationError
└── CombinatorialExplosionError
```

### Error Propagation
1. **Rust layer**: FuzzyError enum with specific error types
2. **PyO3 boundary**: Convert to PyErr with appropriate Python exceptions
3. **Python layer**: Standard Python exceptions with descriptive messages

## Memory Management

### Resource Lifecycle
1. **Database loading**: RKDatabase loaded into memory
2. **Query execution**: Temporary resources allocated for expansion
3. **Result conversion**: PyFuzzyMatch objects created
4. **Cleanup**: Automatic memory management via PyO3 and Rust drop traits

### Memory Optimization
- **Database sharing**: Single RKDatabase instance for multiple operations
- **Result streaming**: Large result sets handled efficiently
- **Wildcard limits**: Combinatorial explosion protection
- **Garbage collection**: Automatic cleanup via Python reference counting

## Performance Characteristics

### Time Complexity
- **Wildcard expansion**: O(4^n) where n = number of N wildcards
- **Database query**: O(log N) for binary search per variant
- **Total query time**: O(4^n × log N) for wildcard queries
- **Mutation tolerance**: Additional factor based on mutation combinations

### Space Complexity
- **Database storage**: O(N) where N = number of k-mers in database
- **Wildcard expansion**: O(4^n) for storing all combinations
- **Result storage**: O(M) where M = number of matches found
- **Memory limit**: Combinatorial explosion protection prevents excessive memory usage

## Integration Points

### With Existing PyDatabase
- **Shared database instance**: Same RKDatabase used for both query types
- **Consistent API patterns**: Similar error handling and return types
- **Resource management**: Coordinated database lifecycle

### With Rust Core
- **FuzzyQueryEngine**: Direct integration with Rust fuzzy query logic
- **Wildcard expansion**: Reuse existing Rust wildcard algorithms
- **Performance optimization**: Leverage Rust's memory efficiency

### With Python Ecosystem
- **Type hints**: Full type annotations for IDE support
- **Exception handling**: Standard Python exception patterns
- **Documentation**: Python-friendly docstrings and examples