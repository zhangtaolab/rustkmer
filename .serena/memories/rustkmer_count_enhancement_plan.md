# RustKmer Count Command Enhancement Plan

**Objective**: Enhance the `rustkmer count` command with directory processing and interactive file selection capabilities.

## 1. TUI Library Selection Analysis

### 1.1 Library Comparison

| Library | Pros | Cons | Recommendation |
|---------|------|------|----------------|
| **inquire** | • Modern, intuitive API<br>• Built-in multi-select support<br>• Excellent cross-platform compatibility<br>• Minimal dependencies<br>• Easy integration with clap | • Limited to simple interactions<br>• No complex TUI layouts | ⭐ **Recommended for simple dialogs** |
| **dialoguer** | • Mature, battle-tested<br>• Good integration with existing CLI tools<br>• Various confirmation types<br>• Works well in CI/automation | • Older API style<br>• Limited multi-select capabilities<br>• Less intuitive than inquire | ⚠️ Good fallback option |
| **ratatui** | • Full-featured TUI framework<br>• Complex layouts possible<br>• Rich widget ecosystem<br>• High customizability | • Steep learning curve<br>• Heavy dependency tree<br>• Overkill for simple selection<br>• More maintenance burden | ❌ Not recommended for this use case |

### 1.2 Recommended Approach
Use **inquire** as the primary TUI library with dialoguer as fallback:

```toml
[dependencies]
inquire = "0.7"  # Primary TUI library
dialoguer = "0.11"  # Fallback for complex confirmations
```

**Rationale**: 
- File selection is primarily a simple interaction
- inquire provides excellent multi-select with checkboxes
- Minimal learning curve and maintenance overhead
- Works seamlessly with existing clap-based CLI

## 2. Directory Traversal Strategy

### 2.1 File Discovery Algorithm

```rust
// Proposed file discovery structure
pub struct FileDiscovery {
    extensions: Vec<&'static str>,
    recursive: bool,
    follow_symlinks: bool,
    max_depth: usize,
}

impl FileDiscovery {
    // Core discovery method with performance optimizations
    pub fn discover_files(&self, directory: &Path) -> ProcessingResult<Vec<FileInfo>> {
        // 1. Use WalkDir for efficient directory traversal
        // 2. Parallel processing with rayon for large directories
        // 3. Early filtering by extension to minimize filesystem calls
        // 4. Memory-efficient streaming for very large directories
    }
}
```

### 2.2 Supported File Extensions
- **FASTA**: `.fa`, `.fasta`, `.fna`, `.ffn`
- **FASTQ**: `.fq`, `.fastq`
- **Compressed**: `.fa.gz`, `.fasta.gz`, `.fq.gz`, `.fastq.gz`
- **Archive support**: `.tar.gz`, `.zip` (future enhancement)

### 2.3 Performance Optimizations

1. **Parallel Directory Traversal**
```rust
use rayon::prelude::*;
use walkdir::{WalkDir, DirEntry};

// Parallel processing of directory entries
let files: Vec<DirEntry> = WalkDir::new(directory)
    .parallel_iter()  // Use rayon for parallel processing
    .filter_entry(|e| filter_entry(e))
    .filter_map(|e| e.ok())
    .collect();
```

2. **Memory-Efficient Streaming**
```rust
// Stream results for very large directories
pub fn discover_files_stream(&self, directory: &Path) -> impl Iterator<Item = FileInfo> {
    WalkDir::new(directory)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| self.is_valid_file(e))
        .map(|e| FileInfo::from(e))
}
```

3. **Progress Indication**
```rust
use indicatif::{ProgressBar, ProgressStyle};

// Progress bar for large directory scans
let pb = ProgressBar::new_spinner();
pb.set_style(ProgressStyle::default_bar()
    .template("{spinner:.green} [{elapsed_precise}] Scanning: {msg}")
    .unwrap());
```

## 3. UI/UX Flow Design

### 3.1 Command Line Interface Enhancement

```rust
// Enhanced count command arguments
Count {
    // ... existing arguments ...
    
    /// Process all files in directory
    #[arg(long, conflicts_with = "input")]
    directory: Option<String>,
    
    /// Interactive file selection
    #[arg(long, short = 'i')]
    interactive: bool,
    
    /// Recursive directory search
    #[arg(long, default_value = "true")]
    recursive: bool,
    
    /// Maximum directory depth
    #[arg(long, default_value = "10")]
    max_depth: usize,
    
    /// File extension filter
    #[arg(long, value_delimiter = ',')]
    extensions: Option<Vec<String>>,
    
    /// Skip confirmation for all files
    #[arg(long)]
    auto_confirm: bool,
},
```

### 3.2 User Interaction Flow

#### Scenario 1: Directory Processing
```
$ rustkmer count -k 21 --directory ./data --interactive

[INFO] Discovered 47 files in ./data and subdirectories:
  • 12 FASTA files (.fa, .fasta)
  • 35 FASTQ files (.fq, .fastq)

? Select files to process (Space to toggle, Enter to confirm):
[✓] chr1.fa
[✓] chr2.fa  
[✓] chr3.fa
[ ] chr4.fa
[✓] sample_1.fq
[✓] sample_2.fq
...
(47 total, 35 selected)

? Process 35 selected files? (y/N) y
```

#### Scenario 2: Non-Interactive Mode
```
$ rustkmer count -k 21 --directory ./data --auto-confirm

[INFO] Discovered 47 files in ./data
[INFO] Processing all files (use --interactive to select specific files)
Processing file 1/47: chr1.fa
Processing file 2/47: chr2.fa
...
```

### 3.3 Error Handling Flow

```rust
// Comprehensive error handling
pub enum FileProcessingError {
    DirectoryNotFound(String),
    PermissionDenied(String),
    InvalidFileType(String),
    EmptyDirectory,
    TooManyFiles(usize),  // Configurable limit
    ProcessingFailed(String, Box<dyn Error>),
}

impl FileProcessingError {
    pub fn user_friendly_message(&self) -> String {
        match self {
            FileProcessingError::TooManyFiles(count) => 
                format!("Found {} files. Consider using --interactive to select specific files or reduce directory scope.", count),
            // ... other cases
        }
    }
}
```

## 4. Implementation Architecture

### 4.1 Module Organization

```
src/
├── cli/
│   ├── commands/
│   │   ├── count.rs          # Enhanced count command
│   │   └── mod.rs
│   ├── args.rs               # Updated CLI arguments
│   └── mod.rs
├── io/
│   ├── discovery.rs          # NEW: File discovery module
│   ├── selection.rs          # NEW: Interactive file selection
│   ├── fasta.rs              # Existing
│   ├── fastq.rs              # Existing
│   └── mod.rs                # Updated exports
└── ...
```

### 4.2 New Module Structure

#### `src/io/discovery.rs` - File Discovery Logic
```rust
pub struct FileDiscovery {
    extensions: Vec<&'static str>,
    recursive: bool,
    max_depth: usize,
    follow_symlinks: bool,
}

#[derive(Debug, Clone)]
pub struct FileInfo {
    pub path: PathBuf,
    pub size: u64,
    pub file_type: FileType,
    pub extension: String,
    pub is_compressed: bool,
}

#[derive(Debug, Clone, Copy)]
pub enum FileType {
    Fasta,
    Fastq,
    Unknown,
}
```

#### `src/io/selection.rs` - Interactive Selection
```rust
use inquire::{MultiSelect, Confirm, Text};

pub struct FileSelector {
    max_display: usize,
    show_file_info: bool,
}

impl FileSelector {
    pub fn select_files_interactive(
        &self, 
        files: Vec<FileInfo>
    ) -> ProcessingResult<Vec<FileInfo>> {
        // Interactive file selection with inquire
    }
    
    pub fn confirm_processing(
        &self, 
        selected_count: usize, 
        total_files: usize
    ) -> ProcessingResult<bool> {
        // Confirmation dialog with file count summary
    }
}
```

### 4.3 Integration Points

#### Modified `execute_count` Function
```rust
pub fn execute_count(args: &Args) -> ProcessingResult<()> {
    match &args.command {
        Commands::Count { 
            directory, 
            interactive, 
            recursive, 
            // ... other args
        } => {
            let input_files = if let Some(dir_path) = directory {
                // New directory processing logic
                let discovery = FileDiscovery::new()
                    .with_recursive(*recursive)
                    .with_extensions(extract_extensions(args));
                
                let files = discovery.discover_files(Path::new(dir_path))?;
                
                let selected_files = if *interactive {
                    let selector = FileSelector::new();
                    selector.select_files_interactive(files)?
                } else {
                    // Auto-confirm mode - use all files
                    if !args.auto_confirm {
                        confirm_large_file_set(&files)?;
                    }
                    files
                };
                
                selected_files.into_iter().map(|f| f.path.to_string_lossy().to_string()).collect()
            } else {
                // Existing file list processing
                input.clone()
            };
            
            // Continue with existing processing logic...
            process_files(&input_files, &counter, ...)?;
        }
        // ... other commands
    }
}
```

### 4.4 Backward Compatibility

1. **Existing CLI Interface**: All current command-line options remain unchanged
2. **File Input Handling**: Existing single file processing logic preserved
3. **Output Format**: No changes to output format or database structure
4. **Configuration**: New features are opt-in via new flags

### 4.5 Testing Strategy

#### Unit Tests
```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_file_discovery_basic() {
        // Test basic directory scanning
    }
    
    #[test]
    fn test_extension_filtering() {
        // Test file extension filtering
    }
    
    #[test]
    fn test_recursive_discovery() {
        // Test recursive directory traversal
    }
    
    #[test]
    fn test_large_directory_handling() {
        // Test performance with large directories
    }
}
```

#### Integration Tests
```rust
// tests/integration_count_directory.rs
use std::process::Command;

#[test]
fn test_count_directory_basic() {
    // Test end-to-end directory processing
}

#[test]
fn test_count_interactive_mode() {
    // Test interactive file selection (mocked)
}
```

#### Performance Tests
```rust
// benches/directory_discovery.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn benchmark_directory_discovery(c: &mut Criterion) {
    c.bench_function("discover_1000_files", |b| {
        b.iter(|| {
            // Benchmark directory discovery performance
        })
    });
}
```

## 5. Implementation Dependencies

### 5.1 New Dependencies
```toml
[dependencies]
# TUI libraries
inquire = "0.7"
dialoguer = "0.11"  # Fallback

# Directory traversal
walkdir = "2.4"      # Efficient directory walking

# Enhanced progress reporting
indicatif = "0.17"   # Already present, may need feature flags

# Configuration validation
clap = { version = "4.5", features = ["derive", "env"] }
```

### 5.2 Optional Dependencies for Future Enhancements
```toml
[dependencies]
# Archive support (future)
zip = "0.6"
tar = "0.4"
compress-tools = "0.15"

# Advanced TUI (if needed later)
crossterm = "0.27"
ratatui = "0.24"
```

## 6. Migration Path

### Phase 1: Core File Discovery
1. Implement `src/io/discovery.rs`
2. Add basic directory processing to CLI args
3. Test with existing file processing logic

### Phase 2: Interactive Selection
1. Add inquire dependency
2. Implement `src/io/selection.rs`
3. Integrate with count command

### Phase 3: Advanced Features
1. Add progress bars for large directories
2. Implement file count limits and confirmations
3. Add comprehensive error handling

### Phase 4: Performance Optimization
1. Parallel directory processing
2. Memory-efficient streaming for huge directories
3. Benchmark and optimize hot paths

## 7. Configuration and Defaults

### 7.1 Default Behavior
- **Non-interactive**: Auto-confirm directories with ≤ 50 files
- **Interactive**: Prompt for selection if > 50 files
- **Recursive**: Enabled by default with max depth of 10
- **Extensions**: Auto-detect based on file patterns

### 7.2 Configuration Options
```rust
// Environment variable overrides
const RUSTKMER_MAX_FILES: usize = 1000;      // Max files before requiring interactive
const RUSTKMER_MAX_DEPTH: usize = 20;        // Maximum directory depth
const RUSTKMER_AUTO_CONFIRM: bool = false;   // Default to confirmation
```

## 8. Critical Files for Implementation

1. **`/Users/forrest/GitHub/rustkmer/src/cli/commands/count.rs`** - Core logic to modify for directory processing
2. **`/Users/forrest/GitHub/rustkmer/src/cli/args.rs`** - CLI argument definitions for new flags
3. **`/Users/forrest/GitHub/rustkmer/src/io/discovery.rs`** - New module for file discovery logic
4. **`/Users/forrest/GitHub/rustkmer/src/io/selection.rs`** - New module for interactive file selection
5. **`/Users/forrest/GitHub/rustkmer/Cargo.toml`** - Add new dependencies (inquire, walkdir)

This plan provides a comprehensive, backward-compatible enhancement to the rustkmer count command with excellent user experience and robust error handling.