//! Core database functionality for RustKmer

pub mod persistence;

// Re-export commonly used types
pub use persistence::{
    PersistenceConfig, PersistenceError, save_kmer_database, load_kmer_database,
    merge_databases, validate_checksums,
};