//! Configuration Management Module
//!
//! Provides comprehensive configuration management for RustKmer with file-based storage,
//! environment variable integration, and per-operation override mechanisms.

use std::collections::HashMap;
use std::env;
use std::fs::{File};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use serde::{Deserialize, Serialize};
use anyhow::{Context, Result};

/// Default configuration file name
pub const DEFAULT_CONFIG_FILE: &str = ".rustkmerrc";
/// Environment variable prefix
pub const ENV_PREFIX: &str = "RUSTKMER";

/// Thread-safe configuration manager
#[derive(Debug)]
pub struct ConfigManager {
    global_config: Arc<parking_lot::RwLock<GlobalConfig>>,
    config_file: Option<PathBuf>,
}

/// Global configuration loaded from file and environment variables
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalConfig {
    /// Memory configuration
    pub memory: MemoryConfig,
    /// K-mer counting configuration
    pub kmer_counting: KmerCountingConfig,
    /// Database configuration
    pub database: DatabaseConfig,
    /// Output configuration
    pub output: OutputConfig,
    /// Logging configuration
    pub logging: LoggingConfig,
}

/// Memory-related configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryConfig {
    /// Memory limit in bytes
    pub memory_limit: Option<u64>,
    /// Memory mapping threshold in bytes
    pub mmap_threshold: Option<u64>,
    /// Page size for query results
    pub page_size: Option<usize>,
    /// Enable adaptive memory management
    pub adaptive: Option<bool>,
    /// Force memory mapping
    pub force_mmap: Option<bool>,
}

/// K-mer counting configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KmerCountingConfig {
    /// Default k-mer size
    pub default_k: Option<usize>,
    /// Use canonical k-mers
    pub canonical: Option<bool>,
    /// Thread count (0 = auto)
    pub threads: Option<usize>,
    /// Hash table size
    pub hash_size: Option<usize>,
    /// Sort output by k-mer
    pub sort_output: Option<bool>,
    /// Minimum count filter
    pub min_count: Option<u32>,
    /// Maximum count filter
    pub max_count: Option<u32>,
    /// Enable progress reporting
    pub progress: Option<bool>,
}

/// Database configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    /// Default database file extension
    pub extension: Option<String>,
    /// Database format version
    pub format_version: Option<String>,
    /// Enable compression
    pub compression: Option<bool>,
    /// Indexing strategy
    pub indexing: Option<String>,
}

/// Output configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutputConfig {
    /// Default output format
    pub format: Option<String>,
    /// Enable timestamps
    pub timestamps: Option<bool>,
    /// Enable statistics
    pub statistics: Option<bool>,
    /// Verbose output
    pub verbose: Option<bool>,
    /// Quiet mode
    pub quiet: Option<bool>,
}

/// Logging configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    /// Log level
    pub level: Option<String>,
    /// Log file path
    pub file_path: Option<String>,
    /// Enable structured logging
    pub structured: Option<bool>,
}

/// Configuration override for a specific operation
#[derive(Debug, Clone)]
pub struct OperationConfig {
    /// Memory overrides
    pub memory: Option<MemoryConfig>,
    /// K-mer counting overrides
    pub kmer_counting: Option<KmerCountingConfig>,
    /// Output overrides
    pub output: Option<OutputConfig>,
}

impl Default for GlobalConfig {
    fn default() -> Self {
        Self {
            memory: MemoryConfig::default(),
            kmer_counting: KmerCountingConfig::default(),
            database: DatabaseConfig::default(),
            output: OutputConfig::default(),
            logging: LoggingConfig::default(),
        }
    }
}

impl Default for MemoryConfig {
    fn default() -> Self {
        Self {
            memory_limit: Some(1024 * 1024 * 1024), // 1GB
            mmap_threshold: Some(100 * 1024 * 1024), // 100MB
            page_size: Some(10000),
            adaptive: Some(true),
            force_mmap: Some(false),
        }
    }
}

impl Default for KmerCountingConfig {
    fn default() -> Self {
        Self {
            default_k: Some(31),
            canonical: Some(true),
            threads: Some(0), // Auto-detect
            hash_size: Some(1_000_000),
            sort_output: Some(true),
            min_count: None,
            max_count: None,
            progress: Some(true),
        }
    }
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            extension: Some("rkdb".to_string()),
            format_version: Some("2".to_string()),
            compression: Some(true),
            indexing: Some("auto".to_string()),
        }
    }
}

impl Default for OutputConfig {
    fn default() -> Self {
        Self {
            format: Some("text".to_string()),
            timestamps: Some(true),
            statistics: Some(true),
            verbose: Some(false),
            quiet: Some(false),
        }
    }
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            level: Some("info".to_string()),
            file_path: None,
            structured: Some(false),
        }
    }
}

impl ConfigManager {
    /// Create a new configuration manager
    pub fn new() -> Self {
        Self {
            global_config: Arc::new(parking_lot::RwLock::new(GlobalConfig::default())),
            config_file: Self::find_config_file(),
        }
    }

    /// Create a configuration manager with a specific config file
    pub fn with_config_file<P: AsRef<Path>>(path: P) -> Self {
        let config_file = Some(path.as_ref().to_path_buf());
        Self {
            global_config: Arc::new(parking_lot::RwLock::new(GlobalConfig::default())),
            config_file,
        }
    }

    /// Find the configuration file in standard locations
    fn find_config_file() -> Option<PathBuf> {
        // Check current directory
        let current_dir = PathBuf::from(DEFAULT_CONFIG_FILE);
        if current_dir.exists() {
            return Some(current_dir);
        }

        // Check user's home directory
        if let Ok(home_dir) = env::var("HOME") {
            let home_config = PathBuf::from(home_dir).join(DEFAULT_CONFIG_FILE);
            if home_config.exists() {
                return Some(home_config);
            }
        }

        // Check system-wide config directory
        if let Ok(config_dir) = env::var("XDG_CONFIG_HOME") {
            let system_config = PathBuf::from(config_dir).join("rustkmer").join(DEFAULT_CONFIG_FILE);
            if system_config.exists() {
                return Some(system_config);
            }
        }

        None
    }

    /// Load configuration from file and environment variables
    pub fn load(&self) -> Result<()> {
        let mut config = GlobalConfig::default();

        // Load from file if it exists
        if let Some(ref config_file) = self.config_file {
            config = Self::load_from_file(config_file)
                .with_context(|| format!("Failed to load config from {}", config_file.display()))?;
        }

        // Override with environment variables
        config = Self::apply_env_overrides(config);

        // Store the merged configuration
        *self.global_config.write() = config;

        Ok(())
    }

    /// Load configuration from a TOML file
    fn load_from_file<P: AsRef<Path>>(path: P) -> Result<GlobalConfig> {
        let mut content = String::new();
        let mut file = File::open(&path)
            .with_context(|| format!("Failed to open config file: {}", path.as_ref().display()))?;

        file.read_to_string(&mut content)
            .with_context(|| "Failed to read config file content")?;

        // Parse TOML
        toml::from_str(&content)
            .with_context(|| "Failed to parse TOML configuration")
    }

    /// Save configuration to file
    pub fn save(&self) -> Result<()> {
        if let Some(ref config_file) = self.config_file {
            let config = self.global_config.read();
            let content = toml::to_string_pretty(&*config)
                .with_context(|| "Failed to serialize configuration to TOML")?;

            let mut file = File::create(config_file)
                .with_context(|| format!("Failed to create config file: {}", config_file.display()))?;

            file.write_all(content.as_bytes())
                .with_context(|| "Failed to write config file")?;

            Ok(())
        } else {
            Err(anyhow::anyhow!("No configuration file specified"))
        }
    }

    /// Apply environment variable overrides to configuration
    fn apply_env_overrides(mut config: GlobalConfig) -> GlobalConfig {
        // Memory configuration
        if let Ok(val) = env::var(format!("{}_MEMORY_LIMIT", ENV_PREFIX)) {
            if let Ok(limit) = val.parse::<u64>() {
                config.memory.memory_limit = Some(limit);
            }
        }

        if let Ok(val) = env::var(format!("{}_MMAP_THRESHOLD", ENV_PREFIX)) {
            if let Ok(threshold) = val.parse::<u64>() {
                config.memory.mmap_threshold = Some(threshold);
            }
        }

        if let Ok(val) = env::var(format!("{}_PAGE_SIZE", ENV_PREFIX)) {
            if let Ok(page_size) = val.parse::<usize>() {
                config.memory.page_size = Some(page_size);
            }
        }

        if let Ok(val) = env::var(format!("{}_ADAPTIVE", ENV_PREFIX)) {
            config.memory.adaptive = Some(val.parse().unwrap_or(true));
        }

        if let Ok(val) = env::var(format!("{}_FORCE_MMAP", ENV_PREFIX)) {
            config.memory.force_mmap = Some(val.parse().unwrap_or(false));
        }

        // K-mer counting configuration
        if let Ok(val) = env::var(format!("{}_DEFAULT_K", ENV_PREFIX)) {
            if let Ok(k) = val.parse::<usize>() {
                config.kmer_counting.default_k = Some(k);
            }
        }

        if let Ok(val) = env::var(format!("{}_CANONICAL", ENV_PREFIX)) {
            config.kmer_counting.canonical = Some(val.parse().unwrap_or(true));
        }

        if let Ok(val) = env::var(format!("{}_THREADS", ENV_PREFIX)) {
            if let Ok(threads) = val.parse::<usize>() {
                config.kmer_counting.threads = Some(threads);
            }
        }

        if let Ok(val) = env::var(format!("{}_HASH_SIZE", ENV_PREFIX)) {
            if let Ok(size) = val.parse::<usize>() {
                config.kmer_counting.hash_size = Some(size);
            }
        }

        if let Ok(val) = env::var(format!("{}_SORT_OUTPUT", ENV_PREFIX)) {
            config.kmer_counting.sort_output = Some(val.parse().unwrap_or(true));
        }

        if let Ok(val) = env::var(format!("{}_MIN_COUNT", ENV_PREFIX)) {
            if let Ok(count) = val.parse::<u32>() {
                config.kmer_counting.min_count = Some(count);
            }
        }

        if let Ok(val) = env::var(format!("{}_MAX_COUNT", ENV_PREFIX)) {
            if let Ok(count) = val.parse::<u32>() {
                config.kmer_counting.max_count = Some(count);
            }
        }

        if let Ok(val) = env::var(format!("{}_PROGRESS", ENV_PREFIX)) {
            config.kmer_counting.progress = Some(val.parse().unwrap_or(true));
        }

        // Output configuration
        if let Ok(val) = env::var(format!("{}_FORMAT", ENV_PREFIX)) {
            config.output.format = Some(val);
        }

        if let Ok(val) = env::var(format!("{}_TIMESTAMPS", ENV_PREFIX)) {
            config.output.timestamps = Some(val.parse().unwrap_or(true));
        }

        if let Ok(val) = env::var(format!("{}_STATISTICS", ENV_PREFIX)) {
            config.output.statistics = Some(val.parse().unwrap_or(true));
        }

        if let Ok(val) = env::var(format!("{}_VERBOSE", ENV_PREFIX)) {
            config.output.verbose = Some(val.parse().unwrap_or(false));
        }

        if let Ok(val) = env::var(format!("{}_QUIET", ENV_PREFIX)) {
            config.output.quiet = Some(val.parse().unwrap_or(false));
        }

        // Logging configuration
        if let Ok(val) = env::var(format!("{}_LOG_LEVEL", ENV_PREFIX)) {
            config.logging.level = Some(val);
        }

        if let Ok(val) = env::var(format!("{}_LOG_FILE", ENV_PREFIX)) {
            config.logging.file_path = Some(val);
        }

        if let Ok(val) = env::var(format!("{}_STRUCTURED", ENV_PREFIX)) {
            config.logging.structured = Some(val.parse().unwrap_or(false));
        }

        config
    }

    /// Get the current global configuration
    pub fn get_config(&self) -> GlobalConfig {
        self.global_config.read().clone()
    }

    /// Create an operation-specific configuration with overrides
    pub fn create_operation_config(&self, overrides: OperationConfig) -> OperationConfig {
        let global_config = self.global_config.read();

        OperationConfig {
            memory: overrides.memory.or(Some(global_config.memory.clone())),
            kmer_counting: overrides.kmer_counting.or(Some(global_config.kmer_counting.clone())),
            output: overrides.output.or(Some(global_config.output.clone())),
        }
    }

    /// Apply environment variable overrides to an existing configuration
    pub fn apply_env_overrides_to_config(&self, config: &mut GlobalConfig) {
        *config = Self::apply_env_overrides(config.clone());
    }

    /// Validate configuration values
    pub fn validate_config(config: &GlobalConfig) -> Result<Vec<String>> {
        let mut errors = Vec::new();

        // Validate memory configuration
        if let Some(limit) = config.memory.memory_limit {
            if limit == 0 {
                errors.push("Memory limit cannot be zero".to_string());
            }
        }

        if let Some(threshold) = config.memory.mmap_threshold {
            if threshold == 0 {
                errors.push("Memory mapping threshold cannot be zero".to_string());
            }
        }

        if let Some(page_size) = config.memory.page_size {
            if page_size == 0 {
                errors.push("Page size cannot be zero".to_string());
            }
        }

        // Validate k-mer counting configuration
        if let Some(k) = config.kmer_counting.default_k {
            if k == 0 || k > 64 {
                errors.push("Default k-mer size must be between 1 and 64".to_string());
            }
        }

        if let Some(threads) = config.kmer_counting.threads {
            if threads > 256 {
                errors.push("Thread count should not exceed 256".to_string());
            }
        }

        if let Some(hash_size) = config.kmer_counting.hash_size {
            if hash_size == 0 {
                errors.push("Hash table size cannot be zero".to_string());
            }
        }

        // Validate database configuration
        if let Some(extension) = &config.database.extension {
            if extension.is_empty() {
                errors.push("Database extension cannot be empty".to_string());
            }
        }

        Ok(errors)
    }

    /// Get a configuration value with fallback to environment variable
    pub fn get_config_with_fallback<T>(&self, key: &str, fallback: T) -> T
    where
        T: std::str::FromStr,
    {
        let env_key = format!("{}_{}", ENV_PREFIX, key.to_uppercase());

        env::var(&env_key)
            .ok()
            .and_then(|val| val.parse().ok())
            .unwrap_or(fallback)
    }

    /// Set a temporary environment variable for the current process
    pub fn set_env_var(&self, key: &str, value: &str) -> Result<()> {
        unsafe { env::set_var(format!("{}_{}", ENV_PREFIX, key.to_uppercase()), value) };
        Ok(())
    }

    /// Remove a temporary environment variable
    pub fn remove_env_var(&self, key: &str) -> Result<()> {
        unsafe { env::remove_var(format!("{}_{}", ENV_PREFIX, key.to_uppercase())) };
        Ok(())
    }

    /// Generate a configuration report
    pub fn generate_report(&self) -> ConfigReport {
        let config = self.global_config.read();
        ConfigReport {
            config_file: self.config_file.clone(),
            config: config.clone(),
            environment_overrides: Self::get_all_env_overrides(),
            validation_errors: Self::validate_config(&config).unwrap_or_default(),
        }
    }

    /// Get all environment variable overrides currently active
    fn get_all_env_overrides() -> HashMap<String, String> {
        let mut overrides = HashMap::new();

        for (key, value) in env::vars() {
            if key.starts_with(ENV_PREFIX) {
                let clean_key = key.strip_prefix(ENV_PREFIX).unwrap().to_string();
                overrides.insert(clean_key, value);
            }
        }

        overrides
    }
}

/// Configuration report for debugging and validation
#[derive(Debug, Clone)]
pub struct ConfigReport {
    pub config_file: Option<PathBuf>,
    pub config: GlobalConfig,
    pub environment_overrides: HashMap<String, String>,
    pub validation_errors: Vec<String>,
}

impl ConfigReport {
    /// Print a formatted configuration report
    pub fn print(&self) {
        println!("=== RustKmer Configuration Report ===");

        if let Some(ref file) = self.config_file {
            println!("Config file: {}", file.display());
        } else {
            println!("No configuration file found");
        }

        println!("\nEnvironment overrides:");
        if self.environment_overrides.is_empty() {
            println!("  None");
        } else {
            for (key, value) in &self.environment_overrides {
                println!("  {}: {}", key, value);
            }
        }

        println!("\nCurrent configuration:");
        println!("  Memory limit: {:?} MB",
                 self.config.memory.memory_limit.map(|x| x / 1024 / 1024));
        println!("  Memory mapping threshold: {:?} MB",
                 self.config.memory.mmap_threshold.map(|x| x / 1024 / 1024));
        println!("  Default k: {:?}", self.config.kmer_counting.default_k);
        println!("  Canonical: {:?}", self.config.kmer_counting.canonical);
        println!("  Threads: {:?}", self.config.kmer_counting.threads);
        println!("  Output format: {:?}", self.config.output.format);

        if !self.validation_errors.is_empty() {
            println!("\nValidation errors:");
            for error in &self.validation_errors {
                println!("  - {}", error);
            }
        } else {
            println!("\n✅ Configuration is valid");
        }
    }

    /// Check if configuration is valid
    pub fn is_valid(&self) -> bool {
        self.validation_errors.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    use std::io::Write;

    #[test]
    fn test_default_config() {
        let manager = ConfigManager::new();
        let config = manager.get_config();

        assert_eq!(config.kmer_counting.default_k, Some(31));
        assert_eq!(config.memory.memory_limit, Some(1024 * 1024 * 1024));
        assert_eq!(config.output.format, Some("text".to_string()));
    }

    #[test]
    fn test_env_overrides() {
        // Set temporary environment variables
        unsafe {
            env::set_var("RUSTKMER_DEFAULT_K", "21");
            env::set_var("RUSTKMER_THREADS", "4");
            env::set_var("RUSTKMER_VERBOSE", "true");
        }

        let manager = ConfigManager::new();
        manager.load().unwrap();
        let config = manager.get_config();

        assert_eq!(config.kmer_counting.default_k, Some(21));
        assert_eq!(config.kmer_counting.threads, Some(4));
        assert_eq!(config.output.verbose, Some(true));

        // Clean up
        unsafe { env::remove_var("RUSTKMER_DEFAULT_K") };
        unsafe { env::remove_var("RUSTKMER_THREADS") };
        unsafe { env::remove_var("RUSTKMER_VERBOSE") };
    }

    #[test]
    fn test_config_file_operations() -> Result<()> {
        // Create a temporary config file
        let mut temp_file = NamedTempFile::new()?;
        let config_content = r#"
[database]
format = "binary"
compression = false

[memory]
memory_limit = 512000000  # 512MB
mmap_threshold = 50000000  # 50MB

[kmer_counting]
default_k = 25
canonical = true
threads = 2

[output]
format = "json"
verbose = true

[logging]
level = "info"
"#;

        temp_file.write_all(config_content.as_bytes())?;

        let manager = ConfigManager::with_config_file(temp_file.path());
        manager.load()?;

        let config = manager.get_config();
        assert_eq!(config.memory.memory_limit, Some(512000000));
        assert_eq!(config.memory.mmap_threshold, Some(50000000));
        assert_eq!(config.kmer_counting.default_k, Some(25));
        assert_eq!(config.kmer_counting.canonical, Some(true));
        assert_eq!(config.kmer_counting.threads, Some(2));
        assert_eq!(config.output.format, Some("json".to_string()));
        assert_eq!(config.output.verbose, Some(true));

        // Test saving (should work without errors)
        manager.save()?;

        Ok(())
    }

    #[test]
    fn test_operation_config() {
        let manager = ConfigManager::new();
        manager.load().unwrap();

        let overrides = OperationConfig {
            memory: Some(MemoryConfig {
                memory_limit: Some(2048 * 1024 * 1024), // 2GB
                ..Default::default()
            }),
            kmer_counting: Some(KmerCountingConfig {
                default_k: Some(33),
                ..Default::default()
            }),
            output: Some(OutputConfig {
                format: Some("csv".to_string()),
                ..Default::default()
            }),
        };

        let op_config = manager.create_operation_config(overrides);

        assert_eq!(op_config.memory.unwrap().memory_limit, Some(2048 * 1024 * 1024));
        assert_eq!(op_config.kmer_counting.unwrap().default_k, Some(33));
        assert_eq!(op_config.output.unwrap().format, Some("csv".to_string()));
    }

    #[test]
    fn test_config_validation() -> Result<()> {
        let mut config = GlobalConfig::default();

        // Test invalid configurations
        config.memory.memory_limit = Some(0); // Invalid
        config.kmer_counting.default_k = Some(0); // Invalid
        config.memory.page_size = Some(0); // Invalid

        let errors = ConfigManager::validate_config(&config).unwrap();
        assert!(!errors.is_empty());
        assert!(errors.contains(&"Memory limit cannot be zero".to_string()));

        // Test valid configuration
        config = GlobalConfig::default();
        let errors = ConfigManager::validate_config(&config).unwrap();
        assert!(errors.is_empty());

        Ok(())
    }
}