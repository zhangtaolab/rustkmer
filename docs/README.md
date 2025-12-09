# RustKmer Documentation

This directory contains the documentation for the RustKmer Python API, built with MkDocs.

## Structure

```
docs/
├── mkdocs.yml                 # MkDocs configuration file
├── index.md                   # Homepage
├── installation.md            # Installation guide
├── user-guide/                # User documentation
│   ├── quickstart.md         # Quick start guide
│   ├── concepts.md           # Core concepts
│   ├── examples.md           # Code examples
│   └── tutorials/            # Step-by-step tutorials
│       ├── basic-workflow.md # Basic workflow tutorial
│       └── large-datasets.md # Large datasets tutorial
├── api-reference/             # API documentation
│   └── overview.md           # API overview
├── examples/                  # Example documentation
├── dev-guide/                 # Developer documentation
├── stylesheets/               # Custom CSS
├── javascripts/               # Custom JavaScript
└── assets/                    # Static assets
```

## Building the Documentation

### Prerequisites

```bash
pip install mkdocs-material mkdocstrings[python]
```

### Build Commands

```bash
# Build the documentation
mkdocs build --config-file docs/mkdocs.yml

# Serve locally (for development)
mkdocs serve --config-file docs/mkdocs.yml

# Deploy to GitHub Pages (requires mike)
mike deploy --push --update-aliases 0.1 latest
```

## Features

- **Material Design**: Clean, modern interface with mkdocs-material
- **API Documentation**: Automatic API docs with mkdocstrings
- **Code Examples**: Illustrated examples from the test suite
- **Tutorials**: Step-by-step guides for common tasks
- **Search**: Full-text search capability
- **Responsive**: Mobile-friendly design
- **Dark Mode**: Automatic light/dark theme switching

## Adding New Documentation

1. Create markdown files in the appropriate directory
2. Update the navigation in `mkdocs.yml`
3. Run `mkdocs build` to verify
4. Commit the changes

## Python Examples

Example scripts are located in `/python/examples/`:
- `01_basic_usage.py` - Basic k-mer counting and database operations
- `02_advanced_features.py` - Fuzzy queries, database merging, parallel processing
- `03_real_world_pipeline.py` - Complete genomics analysis pipeline
- `04_benchmarking.py` - Performance benchmarking utilities

These examples are tested and serve both as documentation and as usage tests.