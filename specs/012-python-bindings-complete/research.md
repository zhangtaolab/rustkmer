# Research: Documentation Generation for RustKmer Python API

**Date**: 2025-12-09
**Purpose**: Research findings for generating examples and user documentation using MkDocs with mkdocstrings

## MkDocs and mkdocstrings Configuration Research

### Decision: Use mkdocs-material theme with mkdocstrings[python]

**Rationale**:
- mkdocs-material provides a modern, responsive theme with excellent navigation
- mkdocstrings automatically generates API documentation from Python docstrings
- Supports bilingual documentation (English primary, Chinese secondary)
- Excellent search functionality
- Built-in support for code highlighting and Admonitions

**Configuration Findings**:
```yaml
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [python]
          options:
            show_source: true
            show_root_heading: true
            show_root_members_full_path: false
            members_order: source
            docstring_style: google
            show_inheritance_diagram: true
            merge_init_into_class: true

theme:
  name: material
  language: en  # English primary
  palette:
    primary: blue
    accent: orange
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - search.suggest
    - search.highlight
    - content.tabs.link
    - content.code.annotate
    - content.code.copy
```

**Language Support**:
- Primary: English (per user request)
- Secondary: Chinese for user-facing content
- Bilingual structure with separate sections or language switcher

**Alternatives Considered**:
- Sphinx + autodoc: More powerful but complex setup
- GitBook: Good UI but limited customization
- Docusaurus: React-based, excellent but overkill

## Documentation Structure Research

### Decision: Follow Bioinformatics Library Patterns

**Rationale**:
- Familiar to Python bioinformatics community
- Clear separation of user guide and API reference
- Standardized docstring format that works well with mkdocstrings
- Examples included in documentation

**Structure Findings**:
```
docs/
├── index.md                   # Homepage with overview
├── installation.md            # Installation instructions
├── user-guide/               # User-focused documentation
│   ├── quickstart.md         # 5-minute quick start
│   ├── concepts.md           # Key concepts and terminology
│   ├── examples/             # Practical examples gallery
│   └── tutorials/            # Step-by-step tutorials
├── api-reference/            # Auto-generated API docs
│   ├── overview.md           # API overview
│   ├── kmercounter.md        # KmerCounter class docs
│   ├── database.md           # Database class docs
│   ├── fuzzyquery.md         # FuzzyQuery class docs
│   └── exceptions.md         # Exception classes docs
└── dev-guide/                # Developer documentation
    └── examples/             # Code examples
```

**Docstring Format**:
- Google style with mkdocstrings compatibility
- Include Args, Returns, Raises, Examples sections
- Use `>>>` for doctest examples
- Add Note sections for important details

## Example Selection from Completed Test Suite

Based on the completed 30 compatibility test tasks, identified key examples:

### 1. Basic K-mer Counting
```python
from rustkmer import KmerCounter

# Count k-mers in FASTA file
counter = KmerCounter(k=31)
counter.count_file("sample.fa")
print(f"Total k-mers: {counter.get_total_count()}")
print(f"Unique k-mers: {counter.get_unique_count()}")
```

### 2. Database Operations
```python
from rustkmer import Database, KmerCounter

# Create and save database
counter = KmerCounter(k=31)
counter.count_file("sample.fa")
counter.save_to_database("sample.rkdb")

# Load and query
db = Database()
db.load("sample.rkdb")
count = db.query("ATCGATCGATCGATCGATCGATC")
```

### 3. Fuzzy Search
```python
from rustkmer import FuzzyQuery

fq = FuzzyQuery()
fq.load("database.rkdb")
results = fq.query("ATCGATCGATCGATCGATCGATC", max_mismatches=2)
```

### 4. Batch Operations
```python
from rustkmer import Database

db = Database()
db.load("database.rkdb")
sequences = ["ATCGATCG", "GCTAGCTA", "CCCCCCCC"]
results = db.query_multiple(sequences)
```

### 5. Statistics
```python
from rustkmer import Database

db = Database()
db.load("database.rkdb")
stats = db.get_stats()
print(f"Total: {stats['total_kmers']}")
print(f"Unique: {stats['unique_kmers']}")
```

### 6. Merging
```python
from rustkmer import Database

db = Database()
db.load("db1.rkdb")
db.merge_with("db2.rkdb")
```

### 7. Data Export
```python
from rustkmer import Database

db = Database()
db.load("database.rkdb")
db.dump("export.txt", format="text")
```

### 8. Advanced Features
```python
# Memory-mapped database access
db = Database()
db.load("large_db.rkdb", memory_mapped=True)

# Progress reporting
def progress_callback(progress):
    print(f"Progress: {progress*100:.1f}%")

counter = KmerCounter(k=31)
counter.count_file("large_file.fa", progress_callback=progress_callback)
```

## Integration with Existing Documentation

### Current Documentation Status
- Existing `/docs/` directory with comprehensive CLI documentation
- API.md covers basic Python API
- Getting started guides exist
- Performance documentation available
- Well-established structure and style

### Integration Strategy
1. **Extend existing structure**: Add Python API sections alongside CLI docs
2. **Maintain consistency**: Use same style and navigation patterns
3. **Link between CLI and Python**: Cross-reference where relevant
4. **Unified search**: Ensure both CLI and Python docs are searchable

### Key Integration Points
- Primary: `/docs/api-reference/python/` (already exists)
- Secondary: Update `/docs/index.md` with Python highlights
- Cross-references: Link CLI commands to Python equivalents
- Examples: Add Python examples to existing tutorials

## Bilingual Documentation Requirements

### Language Requirements
- **Primary**: English (per user request clarification)
- **Secondary**: Chinese for user-facing content
- Technical terms remain in English where standard

### Implementation Strategy
1. **Separate language sections**:
   ```yaml
   nav:
     - English:
         - Home: index.md
         - API: api/
         - Examples: examples/
     - 中文:
         - 首页: zh/index.md
         - API: zh/api/
         - 示例: zh/examples/
   ```
2. **Alternative approach**: Single docs with language toggle
3. **Code comments**: Python where helpful, bilingual where beneficial

## Performance Documentation Strategy

### Performance Benchmarks
From the test suite, identified key metrics to document:
- K-mer counting throughput (k-mers/second)
- Database query latency (ms)
- Memory usage patterns
- Scalability with data size
- Thread scaling efficiency

### Documentation Approach
- Include performance characteristics in API docs
- Add dedicated performance guide
- Provide optimization tips
- Show benchmark methodology

## Docstring Guidelines for mkdocstrings

### Recommended Format
```python
class KmerCounter:
    """k-mer counter class for counting k-mers in sequences.

    This class provides high-performance k-mer counting functionality,
    supporting FASTA and FASTQ format files.

    Args:
        k (int): k-mer size, range 7-64
        canonical (bool): Whether to use canonical mode, default True
        threads (int): Number of threads, default CPU core count

    Example:
        >>> from rustkmer import KmerCounter
        >>> counter = KmerCounter(k=31)
        >>> counter.count_file("sample.fa")
        >>> print(counter.get_total_count())
        12345

    Note:
        - k must be >= 7 and <= 64
        - canonical mode treats reverse complement as identical
    """

    def count_file(self, filepath: str) -> None:
        """Count k-mers from a file.

        Args:
            filepath (str): Input file path (FASTA or FASTQ format)

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file format is invalid

        Example:
            >>> counter.count_file("sample.fa")
            >>> counter.get_total_count()
            1000
        """
```

## MkDocs Configuration Specifics

### Complete Recommended Configuration
```yaml
site_name: RustKmer Python API Documentation
site_description: High-performance k-mer analysis library for Python
repo_url: https://github.com/rustkmer/rustkmer
edit_uri: edit/main/docs/

theme:
  name: material
  language: en
  palette:
    - scheme: default
      primary: blue
      accent: orange
      toggle:
        icon: material/weather-sunny
        name: Switch to dark mode
    - scheme: slate
      primary: blue
      accent: orange
      toggle:
        icon: material/weather-night
        name: Switch to light mode
  font:
    text: Roboto
    code: Roboto Mono
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.tabs.link

plugins:
  - mkdocstrings:
      handlers:
        python:
          paths: [python]
          options:
            docstring_style: google
            show_source: true
            show_signature: true
            show_signature_annotations: true
            group_by_category: true
            members_order: alphabetical
            filters: ["!^_"]
            show_inheritance_diagram: true
            merge_init_into_class: true
  - search:
      lang: en

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.highlight
  - pymdownx.inlinehilite
  - pymdownx.tabbed
  - attr_list
  - md_in_html

nav:
  - Home: index.md
  - Installation: installation.md
  - User Guide:
      - Quick Start: user-guide/quickstart.md
      - Concepts: user-guide/concepts.md
      - Examples: user-guide/examples.md
      - Tutorials: user-guide/tutorials.md
  - API Reference:
      - Overview: api-reference/overview.md
      - KmerCounter: api-reference/kmercounter.md
      - Database: api-reference/database.md
      - FuzzyQuery: api-reference/fuzzyquery.md
      - Exceptions: api-reference/exceptions.md
  - Developer Guide: dev-guide/
```

## Next Steps

Based on research findings:

1. **Phase 1**: Create MkDocs configuration with above settings
2. **Phase 2**: Update Python docstrings to follow Google style with examples
3. **Phase 3**: Create user guide content based on extracted examples
4. **Phase 4**: Generate example scripts from test suite
5. **Phase 5**: Create step-by-step tutorials
6. **Phase 6**: Build and test documentation

## Key Decisions Made

1. **Documentation Framework**: MkDocs with mkdocstrings
2. **Theme**: mkdocs-material for modern UI and features
3. **Language**: English primary, Chinese secondary
4. **Structure**: Follow bioinformatics library patterns
5. **Integration**: Extend existing `/docs/` structure
6. **Docstrings**: Google style with comprehensive examples
7. **Examples**: Extracted from 30 completed compatibility tests