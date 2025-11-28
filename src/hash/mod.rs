//! Hash table and counting functionality
//!
//! Provides concurrent hash table implementation for efficient k-mer counting
//! with support for overflow storage and memory optimization.

pub mod table;
pub mod overflow;
pub mod matrix;
pub mod filtering;

pub use table::KmerCounter;
pub use filtering::{CountFilter, CountFilterConfig, FilteringResult};