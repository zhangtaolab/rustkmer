//! Core functionality modules for RustKmer

pub mod monitoring;
pub mod metadata;
pub mod database;

// Re-export commonly used types
pub use monitoring::{
    MonitoringConfig, OperationMetrics, PerformanceTimer,
    initialize_monitoring, start_timer, record_metric
};

#[cfg(feature = "profiling")]
pub use monitoring::{
    MetricsCollector, time_operation, if_profiling
};

pub use metadata::{
    DatabaseMetadata, MetadataSchema, MetadataError,
    create_metadata, save_metadata, load_metadata, validate_metadata
};

pub use database::{
    PersistenceConfig, PersistenceError, save_kmer_database, load_kmer_database,
    merge_databases, validate_checksums,
};