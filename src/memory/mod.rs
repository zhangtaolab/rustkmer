//! Memory Management Module
//!
//! Provides memory-efficient operations for large genomic datasets,
//! including memory mapping, pagination, and streaming interfaces.

pub mod efficiency;

pub use efficiency::{
    MemoryConfig, MemoryManager, MemoryStats, MemoryEfficiencyReport,
    PageIterator, MMAP_THRESHOLD, DEFAULT_MEMORY_LIMIT, DEFAULT_PAGE_SIZE,
};