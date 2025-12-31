//! Error types for rustkmer
//!
//! Provides comprehensive error handling for k-mer counting operations.

use std::fmt;

/// Library-specific errors with thiserror for type safety
#[derive(Debug, thiserror::Error)]
pub enum KmerError {
    #[error("Invalid k-mer size: {0}. Must be between 1 and 127")]
    InvalidKmerSize(u32),

    #[error("Invalid character at position {pos}: '{char}' in sequence")]
    InvalidCharacter { pos: usize, char: char },

    #[error("Sequence too short: {length} bases (minimum {min_required} for k-mer size {kmer_size})")]
    SequenceTooShort { length: usize, min_required: usize, kmer_size: usize },

    #[error("File format error in '{file}': {reason}")]
    FileFormatError { file: String, reason: String },

    #[error("Memory error: {0}")]
    MemoryError(String),

    #[error("Hash table overflow: {0}")]
    HashTableOverflow(String),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("UTF-8 error: {0}")]
    Utf8Error(#[from] std::string::FromUtf8Error),

    #[error("Parse error: {0}")]
    ParseError(String),

    #[error("Processing error: {0}")]
    ProcessingError(String),

    #[error("File not found: {0}")]
    FileNotFound(String),

    #[error("File write error: {0}")]
    FileWriteError(String),

    #[error("Invalid argument: {0}")]
    InvalidArgument(String),

    #[error("Invalid parameters: {0}")]
    InvalidParameters(String),

    #[error("Too many variants: {actual} (limit: {limit})")]
    TooManyVariants { actual: usize, limit: usize },
}

/// Application-level errors with anyhow for context
pub type ProcessingResult<T> = Result<T, ProcessingError>;

/// Processing errors with context and chaining
#[derive(Debug)]
pub struct ProcessingError {
    message: String,
    source: Option<anyhow::Error>,
}

impl ProcessingError {
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            source: None,
        }
    }

    pub fn with_context<E: Into<anyhow::Error>>(message: impl Into<String>, error: E) -> Self {
        Self {
            message: message.into(),
            source: Some(error.into()),
        }
    }
}

impl fmt::Display for ProcessingError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)?;
        if let Some(ref source) = self.source {
            write!(f, ": {}", source)?;
        }
        Ok(())
    }
}

impl std::error::Error for ProcessingError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        self.source.as_ref().map(|e| e.as_ref())
    }
}

impl From<KmerError> for ProcessingError {
    fn from(err: KmerError) -> Self {
        Self::with_context("K-mer processing error", err)
    }
}

impl From<std::io::Error> for ProcessingError {
    fn from(err: std::io::Error) -> Self {
        Self::with_context("I/O error", err)
    }
}

/// Additional error types for queryx functionality
#[derive(Debug, thiserror::Error)]
pub enum RustKmerError {
    #[error("Invalid k-mer sequence: {0}")]
    InvalidKmer(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Query error: {0}")]
    QueryError(String),

    #[error("Database error: {0}")]
    DatabaseError(String),

    #[error("Thread creation failed: {0}")]
    ThreadCreationError(String),

    #[error("Processing error: {0}")]
    ProcessingError(String),

    #[error("I/O error: {0}")]
    IoError(String),

    #[error("Insufficient memory: {0}")]
    InsufficientMemory(String),

    #[error("Database not found: {0}")]
    DatabaseNotFound(String),

    #[error("Invalid database format: {0}")]
    InvalidDatabaseFormat(String),
}

/// Additional processing error constructors for convenience
impl ProcessingError {
    pub fn io_error(message: impl Into<String>) -> Self {
        Self::new(message)
    }

    pub fn database_error(message: impl Into<String>) -> Self {
        Self::new(format!("Database error: {}", message.into()))
    }

    pub fn query_error(message: impl Into<String>) -> Self {
        Self::new(format!("Query error: {}", message.into()))
    }
}