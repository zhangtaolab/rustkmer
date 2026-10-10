//! Common utilities for testing RKDB functionality
//!
//! These modules are a shared test-helper library: each `tests/*.rs` binary
//! pulls in `mod common;` and uses whichever factories it needs. Not every
//! helper is referenced by every binary, so `dead_code` would fire per-binary
//! for the unused subset. The idiomatic fix for shared test utility modules
//! is to allow dead code crate-wide here (matches the localized-allow
//! precedent set in plan 01-01).
//!
//! The factories live in `factories.rs` and are re-exported below. Binaries
//! that need ONLY the factories include `factories.rs` directly via
//! `#[path = "common/factories.rs"] mod common;` — that variant compiles no
//! shared-helper self-tests into the binary, while this full module keeps
//! them (they still run once per full-`common` binary: golden_tests,
//! round_trip_tests).

#![allow(dead_code)]

pub mod memory;
pub mod performance;
pub mod temp_files;

mod factories;
pub use factories::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_test_database() {
        let db = create_test_database(1000, 21, true, true).unwrap();
        assert_eq!(db.kmer_size(), 21);
        assert!(db.is_canonical());
        assert!(db.header().sorted);
    }

    #[test]
    fn test_encode_test_kmer() {
        let kmer1 = encode_test_kmer(0, 8); // Should encode to all A's
        let kmer2 = encode_test_kmer(1, 8); // Should encode to C followed by A's

        // All A's should be 0x0000000000000000
        assert_eq!(kmer1, 0x0000000000000000);
        // C followed by A's should be 0x01
        assert_eq!(kmer2, 0x0000000000000001);
    }

    #[test]
    fn test_databases_have_same_kmers() {
        let kmers = vec![(0x1234, 10), (0x5678, 20), (0x9ABC, 15)];
        let db1 = create_database_from_kmers(kmers.clone(), 21, true, true).unwrap();
        let db2 = create_database_from_kmers(kmers, 21, true, true).unwrap();

        assert!(databases_have_same_kmers(&db1, &db2).unwrap());
    }
}
