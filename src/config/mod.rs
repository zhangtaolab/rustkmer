//! Configuration Management Module
//!
//! Provides comprehensive configuration management for rustkmer operations,
//! including file-based configuration, environment variable integration,
//! and per-operation configuration overrides.

pub mod manager;

pub use manager::{
    ConfigManager, GlobalConfig, MemoryConfig, KmerCountingConfig,
    DatabaseConfig, OutputConfig, LoggingConfig, OperationConfig,
};