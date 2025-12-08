# Data Model: u128 Encoding Support

## Core Entities

### KmerEntry (Updated)
```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct KmerEntry {
    pub kmer: u128,        // 16 bytes: encoded k-mer (2 bits per base)
    pub count: u32,        // 4 bytes: occurrence count
    // Total: 20 bytes (was 12 bytes in u64 version)
}
```

### DatabaseHeader (Updated)
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseHeader {
    pub version: u32,           // Database format version (2 for u128)
    pub kmer_size: u32,         // k-mer length (1-64)
    pub entry_count: u64,       // Number of entries
    pub format_id: [u8; 4],     // "RKDB" identifier
    pub created: u64,           // Creation timestamp
}
```

### KmerCounter (Updated)
```rust
pub struct KmerCounter {
    data: ParkingLotRwLock<HashMap<u128, u32>>,
    kmer_size: usize,
}
```

## Canonical K-mer Representation

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct CanonicalKmer(u128);

impl CanonicalKmer {
    pub fn new(kmer: u128, k: usize) -> Self {
        let rc = reverse_complement_u128(kmer, k);
        Self(std::cmp::min(kmer, rc))
    }
}
```

## Database Format Changes

### Version 2 Format Specification
```
Header (42 bytes):
- Format ID: 4 bytes ("RKDB")
- Version: 4 bytes (2)
- K-mer size: 4 bytes
- Entry count: 8 bytes
- Reserved: 16 bytes
- Created: 8 bytes
- Checksum: 2 bytes

Entries (20 bytes each):
- K-mer: 16 bytes (little-endian u128)
- Count: 4 bytes (little-endian u32)
```

## Validation Rules

- kmer_size: 1 ≤ k ≤ 64
- count: non-negative u32
- encoded k-mer: must fit in 2*k bits
- checksum: CRC-16 of header data

## State Transitions

```rust
pub enum DatabaseOperation {
    Create { k: usize, input: PathBuf },
    Open(PathBuf),
    Query { kmer: String },
    Dump { output: Option<PathBuf> },
    Merge { databases: Vec<PathBuf> },
}
```

## Migration Impact

- **Breaking Change**: Old databases incompatible
- **API Impact**: All k-mer related functions update signature
- **Python Bindings**: Need PyO3 updates for u128 support