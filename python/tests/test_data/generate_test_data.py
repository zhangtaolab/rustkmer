#!/usr/bin/env python3
"""Generate random FASTA test data for rustkmer testing."""

import random
import os
from pathlib import Path

def generate_random_dna_sequence(length):
    """Generate a random DNA sequence of specified length."""
    bases = ['A', 'T', 'C', 'G']
    return ''.join(random.choice(bases) for _ in range(length))

def generate_fasta_file(filename, num_sequences, seq_length_range=(100, 1000)):
    """Generate a FASTA file with random sequences.
    
    Args:
        filename: Output filename
        num_sequences: Number of sequences to generate
        seq_length_range: Tuple of (min_length, max_length) for sequences
    """
    with open(filename, 'w') as f:
        for i in range(num_sequences):
            # Generate header
            header = f">sequence_{i+1:04d}_length_{random.randint(*seq_length_range)}\n"
            f.write(header)
            
            # Generate random sequence
            seq_length = random.randint(*seq_length_range)
            sequence = generate_random_dna_sequence(seq_length)
            
            # Write sequence with line wrapping at 80 characters
            for j in range(0, len(sequence), 80):
                f.write(sequence[j:j+80] + '\n')
            
            f.write('\n')  # Empty line between sequences

def main():
    """Generate test FASTA files."""
    test_data_dir = Path(__file__).parent
    print(f"Generating test data in: {test_data_dir}")
    
    # Generate different sized test files
    files_to_generate = [
        ("small_test.fasta", 50, (50, 200)),      # Small file with short sequences
        ("medium_test.fasta", 100, (100, 500)),   # Medium file with medium sequences  
        ("large_test.fasta", 200, (200, 1000)),   # Larger file with longer sequences
        ("tiny_test.fasta", 10, (20, 100)),       # Very small file for quick tests
    ]
    
    for filename, num_seqs, length_range in files_to_generate:
        filepath = test_data_dir / filename
        print(f"Generating {filename}...")
        generate_fasta_file(filepath, num_seqs, length_range)
        
        # Check file size
        size_kb = filepath.stat().st_size / 1024
        print(f"  Created: {filename} ({size_kb:.1f} KB)")
        
        if size_kb > 500:
            print(f"  Warning: {filename} exceeds 500KB limit!")
    
    # Generate a README file
    readme_content = """# Test FASTA Data

This directory contains randomly generated FASTA files for testing rustkmer.

## Files:
- `tiny_test.fasta`: Very small file (10 sequences, 20-100bp each)
- `small_test.fasta`: Small file (50 sequences, 50-200bp each)
- `medium_test.fasta`: Medium file (100 sequences, 100-500bp each)
- `large_test.fasta`: Large file (200 sequences, 200-1000bp each)

All files contain randomly generated DNA sequences (A, T, C, G only).

## Usage:
```python
from rustkmer import Database

# Load a test database
db = Database("path/to/test_data.large_test.fasta")
```

Generated on: """ + str(Path(__file__).stat().st_mtime) + """
"""
    
    readme_path = test_data_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"\nTest data generation complete!")
    print(f"Total files generated: {len(files_to_generate) + 1}")

if __name__ == "__main__":
    main()




