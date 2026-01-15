//! Core functionality modules for RustKmer

pub mod database;
pub mod metadata;
pub mod monitoring;

// Re-export commonly used types
pub use monitoring::{
    initialize_monitoring, record_metric, start_timer, MonitoringConfig, OperationMetrics,
    PerformanceTimer,
};

#[cfg(feature = "profiling")]
pub use monitoring::{if_profiling, time_operation, MetricsCollector};

pub use metadata::{
    create_metadata, load_metadata, save_metadata, validate_metadata, DatabaseMetadata,
    MetadataError, MetadataSchema,
};

pub use database::{
    load_kmer_database, merge_databases, save_kmer_database, validate_checksums, PersistenceConfig,
    PersistenceError,
};
