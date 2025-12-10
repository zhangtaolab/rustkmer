"""
Pytest configuration for converted RustKmer tests.
Import fixtures from parent directory.
"""

import sys
import os
from pathlib import Path

# Add repository root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

# Add python directory to path for RustKmer module
python_dir = repo_root / "python"
if python_dir.exists():
    sys.path.insert(0, str(python_dir))

# Import all fixtures from parent conftest
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))
from conftest import *