//! Core database functionality for RustKmer

pub mod persistence;

// Re-export commonly used types
pub use persistence::{
    load_kmer_database, merge_databases, save_kmer_database, validate_checksums, PersistenceConfig,
    PersistenceError,
};
