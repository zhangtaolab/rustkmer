#!/usr/bin/env python3
"""
Test runner script for converted RustKmer Python tests.
Simplified runner for converted tests.
"""

import sys
import os
from pathlib import Path

# Add repository root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

# Add python directory to path
python_dir = repo_root / "python"
if python_dir.exists():
    sys.path.insert(0, str(python_dir))

def main():
    """Run converted tests with pytest."""
    import subprocess

    # Run pytest on the converted tests directory
    cmd = [
        sys.executable, "-m", "pytest",
        str(Path(__file__).parent),
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure for debugging
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=repo_root)

    return result.returncode

if __name__ == "__main__":
    sys.exit(main())