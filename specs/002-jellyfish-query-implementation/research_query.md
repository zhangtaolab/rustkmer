# Jellyfish Query Implementation Research

## Current Understanding

### Jellyfish Query Interface
Based on testing jellyfish 2.3.0, the query command supports:

```bash
jellyfish query [options] file:path mers:string+

Options:
  -s, --sequence=path     Output counts for all mers in sequence
  -o, --output=path       Output file (stdout)
  -i, --interactive       Interactive, queries from stdin (false)
  -l, --load             Force pre-loading of database file into memory (false)
  -L, --no-load          Disable pre-loading of database file into memory (false)
```

### Key Features Identified:

1. **Multiple Query Types:**
   - Individual k-mer queries: `jellyfish query db.jf ATGCGATGCTAGC`
   - Multiple k-mers: `jellyfish query db.jf ATGCGATGCTAGC GCTAGCTAGATGC`
   - Sequence file: `jellyfish query -s seq.fa db.jf`
   - Interactive mode: `jellyfish query -i db.jf`

2. **Output Format:**
   - Tab-separated: `k-mer\tcount`
   - Handles invalid k-mers gracefully: "Invalid mer 'XYZ'"

3. **Performance Considerations:**
   - Pre-loading option for faster multiple queries
   - Efficient lookup structure

## Implementation Approaches

### Option A: Index-Based Approach (Recommended)
**Concept:** Create an indexed binary format for fast k-mer lookups

**Pros:**
- Very fast query performance (O(1) or O(log n))
- Memory efficient
- Scalable to large databases
- Compatible with existing count output

**Cons:**
- Requires index building step
- More complex implementation

**Structure:**
```
rustkmer_db.rkdb:
├── Header (metadata)
│   ├── Magic number (4 bytes)
│   ├── Version (2 bytes)
│   ├── K-mer size (1 byte)
│   ├── Total k-mers (8 bytes)
│   ├── Index offset (8 bytes)
│   └── Data offset (8 bytes)
├── Index Section
│   ├── Hash table or B-tree structure
│   └── k-mer to data offset mappings
└── Data Section
    ├── Packed k-mer sequences
    └── 32-bit counts
```

### Option B: Sort + Binary Search
**Concept:** Use sorted k-mer list with binary search

**Pros:**
- Simpler implementation
- Uses existing sort functionality
- Good performance for moderate datasets

**Cons:**
- O(log n) lookup time
- Memory usage for large datasets
- Slower than indexed approach

**Structure:**
```
sorted_kmers.bin:
├── Header
│   ├── Magic number
│   ├── K-mer size
│   ├── Total k-mers
│   └── Sorted flag
└── Sorted k-mer list
    ├── [kmer_encoded][count]
    ├── [kmer_encoded][count]
    └── ...
```

### Option C: Hybrid Hash + Index
**Concept:** In-memory hash with disk-based overflow

**Pros:**
- Fast for hot data
- Handles datasets larger than memory
- Flexible memory usage

**Cons:**
- Most complex
- Potential I/O bottlenecks

## Recommended Implementation Strategy

### Phase 1: Basic Query with Sort + Binary Search
1. Extend `count` command to output indexed format with `--index` flag
2. Create basic `query` command with binary search
3. Support single and multiple k-mer queries
4. Add sequence file querying

### Phase 2: Performance Optimization
1. Implement efficient in-memory index
2. Add pre-loading option
3. Optimize for large datasets
4. Performance benchmarking

### Phase 3: Advanced Features
1. Interactive mode
2. Batch querying
3. Integration with jellyfish databases
4. Compression support

## Technical Decisions

### Data Structure Choice
**Recommendation:** Start with Option B (Sort + Binary Search)
- Easiest to implement using existing codebase
- Good performance characteristics
- Clear upgrade path to indexed approach

### File Format
**Recommendation:** Custom binary format with header
```
struct DatabaseHeader {
    magic: [u8; 4],      // "RKDB"
    version: u16,         // 1
    kmer_size: u8,        // k
    total_kmers: u64,     // n
    kmer_data_offset: u64,
    index_data_offset: u64,
}
```

### Error Handling
- Invalid k-mer characters
- Wrong k-mer size
- Database corruption detection
- Graceful fallbacks

## Implementation Plan

### Immediate Tasks (This session):
1. ✅ Research jellyfish query interface
2. ✅ Create implementation research document
3. 🔄 Design query command interface
4. 🔄 Extend count command to support indexed output
5. 🔄 Implement basic binary search query
6. 🔄 Add query command to CLI args
7. 🔄 Test with existing data

### Future Sessions:
1. Performance optimization
2. Interactive mode
3. Index building utilities
4. Jellyfish compatibility layer

## Success Criteria

### Functional:
- ✅ Query single k-mer count
- ✅ Query multiple k-mers
- ✅ Query from sequence file
- ✅ Handle invalid k-mers gracefully
- ⏳ Compatible with jellyfish output format

### Performance:
- ⏳ <1ms per query for <1M k-mer database
- ⏳ <10ms per query for <10M k-mer database
- ⏳ Memory usage <2x database size
- ⏳ Support databases >100M k-mers

### Usability:
- ⏳ Simple CLI interface
- ⏳ Helpful error messages
- ⏳ Progress indicators for large operations
- ⏳ Compatible with existing workflows

## Risk Analysis

### Technical Risks:
- **Low:** Basic query implementation complexity
- **Medium:** Performance with large datasets
- **Low:** Integration with existing codebase

### Timeline Risks:
- **Low:** Basic functionality (1-2 hours)
- **Medium:** Performance optimization (2-4 hours)
- **Low:** Testing and validation (1 hour)

### Dependencies:
- ✅ Existing k-mer encoding functions
- ✅ Binary I/O utilities
- ✅ CLI framework
- ⏳ New query module structure