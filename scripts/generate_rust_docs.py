#!/usr/bin/env python3
"""
Generate Rust API documentation from source code.

This script extracts Rust doc comments and generates Markdown documentation
files compatible with MkDocs. It processes all Rust source files and creates
structured API documentation.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class RustDocGenerator:
    """Generate Markdown documentation from Rust source code."""

    def __init__(self, src_dir: Path = Path("src"), output_dir: Path = Path("docs/api-reference/rust")):
        self.src_dir = src_dir
        self.output_dir = output_dir
        self.rust_files: List[Path] = []
        self.processed_modules: set = set()

    def find_rust_files(self) -> None:
        """Find all Rust source files to process."""
        if not self.src_dir.exists():
            print(f"Warning: Source directory {self.src_dir} does not exist")
            return

        # Find all .rs files except mod.rs and main.rs
        for rust_file in self.src_dir.rglob("*.rs"):
            if rust_file.name not in ["mod.rs", "main.rs"]:
                self.rust_files.append(rust_file)

        print(f"Found {len(self.rust_files)} Rust files to process")

    def extract_docs_from_file(self, file_path: Path) -> Dict:
        """Extract documentation and code structure from a Rust file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return {}

        # Extract module-level documentation
        module_doc = self._extract_module_docs(content)

        # Extract items (structs, enums, functions, etc.)
        items = self._extract_items(content)

        return {
            'module_doc': module_doc,
            'items': items,
            'file_path': file_path
        }

    def _extract_module_docs(self, content: str) -> str:
        """Extract module-level documentation."""
        # Look for module-level doc comments (//!)
        doc_lines = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('//!'):
                doc_line = line[3:].strip()
                if doc_line:
                    doc_lines.append(doc_line)
            elif doc_lines and not line.startswith('//!') and not line.startswith('//') and line:
                break

        return '\n'.join(doc_lines)

    def _extract_items(self, content: str) -> List[Dict]:
        """Extract documented items from the content."""
        items = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Look for doc comments followed by items
            if line.startswith('///'):
                doc_lines, item_info, new_i = self._parse_doc_comment(lines, i)
                if item_info:
                    items.append({
                        'doc': '\n'.join(doc_lines),
                        **item_info
                    })
                i = new_i
            else:
                i += 1

        return items

    def _parse_doc_comment(self, lines: List[str], start_idx: int) -> Tuple[List[str], Optional[Dict], int]:
        """Parse a doc comment and the following item."""
        doc_lines = []
        i = start_idx

        # Extract doc comment
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('///'):
                doc_line = line[3:].strip()
                doc_lines.append(doc_line)
                i += 1
            elif line.startswith('//') or not line:
                i += 1
            else:
                break

        # Parse the following item
        item_info = None
        if i < len(lines):
            item_line = lines[i].strip()
            item_info = self._parse_item_line(item_line)

        return doc_lines, item_info, i

    def _parse_item_line(self, line: str) -> Optional[Dict]:
        """Parse a Rust item definition line."""
        # Simple regex patterns for common Rust items
        patterns = {
            'pub struct': r'pub\s+struct\s+(\w+)(?:<[^>]+>)?(?:\s*\{[^}]*})?',
            'struct': r'struct\s+(\w+)(?:<[^>]+>)?(?:\s*\{[^}]*})?',
            'pub enum': r'pub\s+enum\s+(\w+)(?:\s*\{[^}]*})?',
            'enum': r'enum\s+(\w+)(?:\s*\{[^}]*})?',
            'pub fn': r'pub\s+fn\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[^{]+)?',
            'fn': r'fn\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[^{]+)?',
            'pub const': r'pub\s+const\s+(\w+)(?::\s*[^=]+)?\s*=',
            'const': r'const\s+(\w+)(?::\s*[^=]+)?\s*=',
            'impl': r'impl\s+(?:<[^>]+>\s+)?(\w+)(?:\s+for\s+(\w+))?',
            'pub trait': r'pub\s+trait\s+(\w+)',
            'trait': r'trait\s+(\w+)',
            'pub type': r'pub\s+type\s+(\w+)\s*=',
            'type': r'type\s+(\w+)\s*=',
        }

        for pattern_type, pattern in patterns.items():
            match = re.search(pattern, line)
            if match:
                if pattern_type == 'impl' and match.group(2):
                    return {
                        'type': 'impl',
                        'trait': match.group(1),
                        'for': match.group(2),
                        'signature': line
                    }
                else:
                    return {
                        'type': pattern_type.split()[-1],  # Get the item type
                        'name': match.group(1),
                        'signature': line
                    }

        return None

    def generate_docs_for_file(self, rust_file: Path) -> None:
        """Generate documentation for a single Rust file."""
        print(f"Processing {rust_file}")

        # Determine relative path and output file name
        rel_path = rust_file.relative_to(self.src_dir)
        output_name = rel_path.stem

        # Skip if already processed this module
        if output_name in self.processed_modules:
            return

        self.processed_modules.add(output_name)

        # Extract documentation
        docs = self.extract_docs_from_file(rust_file)

        if not docs or not docs['module_doc'] and not docs['items']:
            print(f"  No documentation found in {rust_file}")
            return

        # Generate markdown content
        markdown_content = self._generate_markdown(docs, output_name, rel_path)

        # Write output file
        output_file = self.output_dir / f"{output_name}.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"  Generated: {output_file}")
        except Exception as e:
            print(f"  Error writing {output_file}: {e}")

    def _generate_markdown(self, docs: Dict, module_name: str, rel_path: Path) -> str:
        """Generate Markdown content from extracted documentation."""
        lines = []

        # Title
        title = module_name.replace('_', ' ').replace('-', ' ').title()
        lines.append(f"# {title}")
        lines.append("")

        # Module path
        module_path = str(rel_path.with_suffix('')).replace('/', '::')
        lines.append(f"**Module**: `rustkmer::{module_path}`")
        lines.append("")

        # Module documentation
        if docs['module_doc']:
            lines.append("## Overview")
            lines.append("")
            lines.append(docs['module_doc'])
            lines.append("")

        # Items documentation
        if docs['items']:
            lines.append("## API Reference")
            lines.append("")

            current_section = None
            for item in docs['items']:
                item_type = item['type']
                item_name = item['name']

                # Section headers by type
                if item_type != current_section:
                    current_section = item_type
                    section_title = item_type.title() + 's'
                    lines.append(f"### {section_title}")
                    lines.append("")

                # Item documentation
                lines.append(f"#### {item_name}")
                lines.append("")

                if item['signature']:
                    lines.append("```rust")
                    lines.append(item['signature'])
                    lines.append("```")
                    lines.append("")

                if item['doc']:
                    lines.append(item['doc'])
                    lines.append("")

        # Source reference
        lines.append("---")
        lines.append("")
        lines.append(f"*Source: [`{rel_path.name}`](../../../{rel_path})*")

        return '\n'.join(lines)

    def generate_index(self) -> None:
        """Generate the main Rust API index file."""
        index_content = """# Rust API Reference

This section provides comprehensive documentation for all Rust APIs in RustKmer.

## Core Components

### KmerCounter
The main k-mer counting interface with support for:
- Exact k-mer counting
- Canonical k-mer processing
- Memory-efficient counting algorithms
- Large file processing capabilities

### Database Operations
Efficient database functionality for:
- Binary database storage (.rkdb format)
- High-speed querying operations
- Memory-mapped file access
- Fuzzy search capabilities

### Fuzzy Query
Advanced query functionality supporting:
- Pattern matching with wildcards
- Hamming distance calculations
- Substitution queries
- Performance-optimized search algorithms

### Command Line Interface
Complete CLI tool supporting all library features:
- Batch processing operations
- Multiple output formats
- Progress reporting and logging
- Cross-platform compatibility

## Performance Characteristics

RustKmer delivers world-class performance:

| Feature | Performance | Memory Usage |
|---------|-------------|--------------|
| Counting | ~1M k-mers/sec | <100MB for 1GB files |
| Querying | ~4M queries/sec | <2MB additional overhead |
| Database creation | Stream processing | Linear memory usage |

## Usage Examples

```rust
use rustkmer::KmerCounter;

// Create a new counter
let mut counter = KmerCounter::new(21, true);

// Count k-mers from a file
counter.count_file("genome.fa.gz")?;

// Get statistics
let total = counter.get_total_count();
let unique = counter.get_unique_count();

println!("Total k-mers: {}, Unique k-mers: {}", total, unique);
```

For detailed API documentation, see the specific modules listed in the navigation.
"""

        index_file = self.output_dir / "index.md"
        index_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(index_content)
            print(f"Generated Rust API index: {index_file}")
        except Exception as e:
            print(f"Error writing index file: {e}")

    def generate_all_docs(self) -> None:
        """Generate documentation for all Rust files."""
        print("Generating Rust API documentation...")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Find all Rust files
        self.find_rust_files()

        if not self.rust_files:
            print("No Rust files found to process")
            return

        # Generate documentation for each file
        for rust_file in self.rust_files:
            self.generate_docs_for_file(rust_file)

        # Generate index
        self.generate_index()

        print(f"\nDocumentation generation complete!")
        print(f"Processed {len(self.processed_modules)} modules")


def main():
    """Main function."""
    if len(sys.argv) > 1:
        src_dir = Path(sys.argv[1])
    else:
        src_dir = Path("src")

    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])
    else:
        output_dir = Path("docs/api-reference/rust")

    generator = RustDocGenerator(src_dir, output_dir)
    generator.generate_all_docs()


if __name__ == "__main__":
    main()