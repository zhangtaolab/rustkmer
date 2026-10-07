//! Hash table and counting functionality
//!
//! Provides concurrent hash table implementation for efficient k-mer counting
//! with support for overflow storage and memory optimization.

pub mod filtering;
pub mod key;
pub mod matrix;
pub mod overflow;
pub mod table;

pub use filtering::{CountFilter, CountFilterConfig, FilteringResult};
pub use key::KmerKey;
pub use table::KmerCounter;
