//! Memory Efficiency Module
//!
//! This module provides memory-efficient operations for large genomic datasets,
//! targeting <10% overhead over CLI baseline through memory mapping, pagination,
//! and streaming interfaces.

use std::collections::HashMap;
use std::fs::File;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use parking_lot::RwLock;
use memmap2::{Mmap, MmapOptions, MmapMut};
use crate::error::{ProcessingResult, ProcessingError};

/// Threshold for switching to memory-mapped access (100MB)
pub const MMAP_THRESHOLD: u64 = 100 * 1024 * 1024;

/// Default memory limit for operations (1GB)
pub const DEFAULT_MEMORY_LIMIT: u64 = 1024 * 1024 * 1024;

/// Default pagination size for query results
pub const DEFAULT_PAGE_SIZE: usize = 10000;

/// Memory efficiency configuration
#[derive(Debug, Clone)]
pub struct MemoryConfig {
    /// Maximum memory usage in bytes
    pub memory_limit: u64,
    /// Threshold for memory mapping
    pub mmap_threshold: u64,
    /// Page size for query results
    pub page_size: usize,
    /// Enable adaptive memory management
    pub adaptive: bool,
    /// Force memory mapping regardless of size
    pub force_mmap: bool,
}

impl Default for MemoryConfig {
    fn default() -> Self {
        Self {
            memory_limit: DEFAULT_MEMORY_LIMIT,
            mmap_threshold: MMAP_THRESHOLD,
            page_size: DEFAULT_PAGE_SIZE,
            adaptive: true,
            force_mmap: false,
        }
    }
}

impl MemoryConfig {
    /// Create a new memory configuration
    pub fn new() -> Self {
        Self::default()
    }

    /// Set memory limit
    pub fn with_memory_limit(mut self, limit: u64) -> Self {
        self.memory_limit = limit;
        self
    }

    /// Set memory mapping threshold
    pub fn with_mmap_threshold(mut self, threshold: u64) -> Self {
        self.mmap_threshold = threshold;
        self
    }

    /// Set page size
    pub fn with_page_size(mut self, size: usize) -> Self {
        self.page_size = size;
        self
    }

    /// Enable/disable adaptive memory management
    pub fn with_adaptive(mut self, adaptive: bool) -> Self {
        self.adaptive = adaptive;
        self
    }

    /// Force memory mapping
    pub fn with_force_mmap(mut self, force: bool) -> Self {
        self.force_mmap = force;
        self
    }
}

/// Memory usage statistics
#[derive(Debug, Clone)]
pub struct MemoryStats {
    /// Total memory used in bytes
    pub total_used: u64,
    /// Memory mapped files size
    pub mapped_size: u64,
    /// Number of mapped files
    pub mapped_files: usize,
    /// Number of active pages
    pub active_pages: usize,
    /// Peak memory usage
    pub peak_usage: u64,
}

impl MemoryStats {
    /// Create new memory statistics
    pub fn new() -> Self {
        Self {
            total_used: 0,
            mapped_size: 0,
            mapped_files: 0,
            active_pages: 0,
            peak_usage: 0,
        }
    }

    /// Update peak usage if current usage is higher
    pub fn update_peak(&mut self, current_usage: u64) {
        if current_usage > self.peak_usage {
            self.peak_usage = current_usage;
        }
    }

    /// Get memory efficiency percentage (lower is better)
    pub fn efficiency(&self) -> f64 {
        if self.total_used == 0 {
            return 0.0;
        }
        (self.mapped_size as f64 / self.total_used as f64) * 100.0
    }
}

/// Memory manager for efficient operations
#[derive(Debug)]
pub struct MemoryManager {
    config: MemoryConfig,
    stats: Arc<RwLock<MemoryStats>>,
    mapped_files: Arc<RwLock<HashMap<PathBuf, MmapInfo>>>,
}

#[derive(Debug)]
struct MmapInfo {
    size: u64,
    created_at: std::time::Instant,
}

impl MemoryManager {
    /// Create a new memory manager
    pub fn new(config: MemoryConfig) -> Self {
        Self {
            config,
            stats: Arc::new(RwLock::new(MemoryStats::new())),
            mapped_files: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Get current memory statistics
    pub fn stats(&self) -> MemoryStats {
        self.stats.read().clone()
    }

    /// Check if a file should be memory mapped
    pub fn should_mmap(&self, file_size: u64) -> bool {
        self.config.force_mmap || file_size >= self.config.mmap_threshold
    }

    /// Memory map a file for reading
    pub fn mmap_file(&self, path: &Path) -> ProcessingResult<Mmap> {
        let file = File::open(path)?;
        let file_size = file.metadata()?.len();

        // Check if we should memory map
        if !self.should_mmap(file_size) {
            return Err(ProcessingError::new("File too small for memory mapping"));
        }

        // Create memory map
        let mmap = unsafe { MmapOptions::new().map(&file)? };

        // Update statistics
        let total_used_after;
        {
            let mut stats = self.stats.write();
            stats.total_used += file_size;
            stats.mapped_size += file_size;
            stats.mapped_files += 1;
            total_used_after = stats.total_used;
        }

        // Update peak usage
        {
            let mut stats = self.stats.write();
            stats.update_peak(total_used_after);
        }

        // Track mapped file
        {
            let mut mapped = self.mapped_files.write();
            mapped.insert(path.to_path_buf(), MmapInfo {
                size: file_size,
                created_at: std::time::Instant::now(),
            });
        }

        Ok(mmap)
    }

    /// Create a writable memory map
    pub fn mmap_file_mut(&self, path: &Path, size: u64) -> ProcessingResult<MmapMut> {
        // Check memory limit
        {
            let stats = self.stats.read();
            if stats.total_used + size > self.config.memory_limit {
                return Err(ProcessingError::new("Memory limit exceeded"));
            }
        }

        let file = File::create(path)?;
        file.set_len(size)?;

        let mmap = unsafe { MmapOptions::new().map_mut(&file)? };

        // Update statistics
        let total_used_after;
        {
            let mut stats = self.stats.write();
            stats.total_used += size;
            stats.mapped_size += size;
            stats.mapped_files += 1;
            total_used_after = stats.total_used;
        }

        // Update peak usage
        {
            let mut stats = self.stats.write();
            stats.update_peak(total_used_after);
        }

        Ok(mmap)
    }

    /// Unmap a file and free memory
    pub fn unmap_file(&self, path: &Path) -> ProcessingResult<()> {
        let mut mapped = self.mapped_files.write();
        if let Some(info) = mapped.remove(path) {
            let mut stats = self.stats.write();
            stats.total_used = stats.total_used.saturating_sub(info.size);
            stats.mapped_size = stats.mapped_size.saturating_sub(info.size);
            stats.mapped_files = stats.mapped_files.saturating_sub(1);
        }
        Ok(())
    }

    /// Clean up old memory mappings
    pub fn cleanup_old_mappings(&self, max_age: std::time::Duration) -> ProcessingResult<usize> {
        let mut mapped = self.mapped_files.write();
        let now = std::time::Instant::now();
        let mut removed = 0;

        mapped.retain(|_path, info| {
            if now.duration_since(info.created_at) > max_age {
                let mut stats = self.stats.write();
                stats.total_used = stats.total_used.saturating_sub(info.size);
                stats.mapped_size = stats.mapped_size.saturating_sub(info.size);
                stats.mapped_files = stats.mapped_files.saturating_sub(1);
                removed += 1;
                false
            } else {
                true
            }
        });

        Ok(removed)
    }

    /// Get memory efficiency report
    pub fn efficiency_report(&self) -> MemoryEfficiencyReport {
        let stats = self.stats.read();
        let mapped = self.mapped_files.read();

        MemoryEfficiencyReport {
            config: self.config.clone(),
            current_stats: stats.clone(),
            mapped_files_count: mapped.len(),
            efficiency_percentage: stats.efficiency(),
            overhead_percentage: self.calculate_overhead(),
        }
    }

    /// Calculate memory overhead percentage
    fn calculate_overhead(&self) -> f64 {
        let stats = self.stats.read();
        if stats.mapped_size == 0 {
            return 0.0;
        }

        // Estimate overhead from bookkeeping structures
        let estimated_overhead = (stats.mapped_files as u64 * 1024) // ~1KB per mapping
            + (stats.active_pages as u64 * 64); // ~64 bytes per page

        (estimated_overhead as f64 / stats.mapped_size as f64) * 100.0
    }
}

/// Memory efficiency report
#[derive(Debug, Clone)]
pub struct MemoryEfficiencyReport {
    pub config: MemoryConfig,
    pub current_stats: MemoryStats,
    pub mapped_files_count: usize,
    pub efficiency_percentage: f64,
    pub overhead_percentage: f64,
}

impl MemoryEfficiencyReport {
    /// Check if memory efficiency is within target (<10% overhead)
    pub fn is_efficient(&self) -> bool {
        // For empty usage, consider it efficient
        if self.current_stats.total_used == 0 {
            return true;
        }
        self.overhead_percentage < 10.0 && self.efficiency_percentage > 90.0
    }

    /// Print a formatted report
    pub fn print(&self) {
        println!("=== Memory Efficiency Report ===");
        println!("Memory limit: {} MB", self.config.memory_limit / 1024 / 1024);
        println!("Memory map threshold: {} MB", self.config.mmap_threshold / 1024 / 1024);
        println!("Page size: {}", self.config.page_size);
        println!("Adaptive mode: {}", self.config.adaptive);
        println!();

        println!("Current Usage:");
        println!("  Total memory: {} MB", self.current_stats.total_used / 1024 / 1024);
        println!("  Mapped memory: {} MB", self.current_stats.mapped_size / 1024 / 1024);
        println!("  Mapped files: {}", self.current_stats.mapped_files);
        println!("  Active pages: {}", self.current_stats.active_pages);
        println!("  Peak usage: {} MB", self.current_stats.peak_usage / 1024 / 1024);
        println!();

        println!("Efficiency Metrics:");
        println!("  Memory efficiency: {:.2}%", self.efficiency_percentage);
        println!("  Overhead percentage: {:.2}%", self.overhead_percentage);
        println!("  Target met: {}", self.is_efficient());
    }
}

/// Page-based iterator for large result sets
pub struct PageIterator<T: Clone> {
    items: Vec<T>,
    page_size: usize,
    current_page: usize,
    total_pages: usize,
}

impl<T: Clone> PageIterator<T> {
    /// Create a new page iterator
    pub fn new(items: Vec<T>, page_size: usize) -> Self {
        let total_pages = (items.len() + page_size - 1) / page_size;
        Self {
            items,
            page_size,
            current_page: 0,
            total_pages,
        }
    }

    /// Get the next page of items
    pub fn next_page(&mut self) -> Option<Vec<T>> {
        if self.current_page >= self.total_pages {
            return None;
        }

        let start = self.current_page * self.page_size;
        let end = std::cmp::min(start + self.page_size, self.items.len());

        self.current_page += 1;
        Some(self.items[start..end].to_vec())
    }

    /// Get the current page number (0-based)
    pub fn current_page(&self) -> usize {
        self.current_page
    }

    /// Get the total number of pages
    pub fn total_pages(&self) -> usize {
        self.total_pages
    }

    /// Check if there are more pages
    pub fn has_next(&self) -> bool {
        self.current_page < self.total_pages
    }

    /// Get remaining items count
    pub fn remaining_items(&self) -> usize {
        if self.current_page >= self.total_pages {
            return 0;
        }

        let start = self.current_page * self.page_size;
        self.items.len() - start
    }
}

impl<T: Clone> Iterator for PageIterator<T> {
    type Item = Vec<T>;

    fn next(&mut self) -> Option<Self::Item> {
        self.next_page()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_config() {
        let config = MemoryConfig::new()
            .with_memory_limit(512 * 1024 * 1024) // 512MB
            .with_page_size(5000)
            .with_adaptive(false);

        assert_eq!(config.memory_limit, 512 * 1024 * 1024);
        assert_eq!(config.page_size, 5000);
        assert!(!config.adaptive);
    }

    #[test]
    fn test_memory_stats() {
        let mut stats = MemoryStats::new();

        stats.total_used = 1024 * 1024; // 1MB
        stats.mapped_size = 800 * 1024;  // 800KB

        stats.update_peak(2 * 1024 * 1024); // 2MB

        assert_eq!(stats.peak_usage, 2 * 1024 * 1024);
        assert_eq!(stats.efficiency(), 78.125); // 800KB / 1MB * 100
    }

    #[test]
    fn test_page_iterator() {
        let items: Vec<i32> = (0..25).collect();
        let mut iterator = PageIterator::new(items, 10);

        assert_eq!(iterator.total_pages(), 3);
        assert_eq!(iterator.remaining_items(), 25);

        let page1 = iterator.next_page().unwrap();
        assert_eq!(page1.len(), 10);
        assert_eq!(iterator.current_page(), 1);
        assert_eq!(iterator.remaining_items(), 15);

        let page2 = iterator.next_page().unwrap();
        assert_eq!(page2.len(), 10);

        let page3 = iterator.next_page().unwrap();
        assert_eq!(page3.len(), 5);

        assert!(!iterator.has_next());
        assert!(iterator.next_page().is_none());
    }

    #[test]
    fn test_memory_manager_mmap_decision() {
        let config = MemoryConfig::new()
            .with_mmap_threshold(50 * 1024 * 1024); // 50MB

        let manager = MemoryManager::new(config);

        assert!(!manager.should_mmap(10 * 1024 * 1024)); // 10MB - no mmap
        assert!(manager.should_mmap(100 * 1024 * 1024)); // 100MB - mmap
    }

    #[test]
    fn test_efficiency_report() {
        let config = MemoryConfig::default();
        let manager = MemoryManager::new(config);
        let report = manager.efficiency_report();

        assert_eq!(report.mapped_files_count, 0);
        assert!(report.is_efficient()); // Should be efficient with no usage
    }
}