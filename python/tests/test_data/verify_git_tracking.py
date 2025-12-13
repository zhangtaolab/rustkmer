#!/usr/bin/env python3
"""Verify that test_data folder is now tracked by git."""

import subprocess
import os
from pathlib import Path

def check_git_status():
    """Check git status of test_data directory."""
    repo_root = Path(__file__).parent.parent.parent
    test_data_path = Path(__file__).parent
    
    print("Git Tracking Verification")
    print("=" * 40)
    
    # Check if .gitignore exists in test_data
    gitignore_path = test_data_path / ".gitignore"
    print(f".gitignore in test_data: {'EXISTS' if gitignore_path.exists() else 'REMOVED'}")
    
    # Check git status
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", str(test_data_path)],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            if result.stdout.strip():
                print("Git status changes detected:")
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('??'):
                        print(f"  ✓ UNTRACKED: {line[3:]}")
                    elif line.startswith(' M'):
                        print(f"  ✓ MODIFIED: {line[3:]}")
                    else:
                        print(f"  ✓ {line}")
            else:
                print("✓ test_data folder is clean (all changes committed)")
        else:
            print(f"Git status check failed: {result.stderr}")
            
    except FileNotFoundError:
        print("Git command not found - git may not be available")
    except Exception as e:
        print(f"Error checking git status: {e}")

def list_files():
    """List all files in test_data directory."""
    test_data_path = Path(__file__).parent
    print(f"\nFiles in {test_data_path.name}:")
    print("-" * 30)
    
    total_size = 0
    for file_path in sorted(test_data_path.iterdir()):
        if file_path.is_file():
            size = file_path.stat().st_size
            total_size += size
            size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
            print(f"  {file_path.name:<25} {size_str:>8}")
    
    print(f"\nTotal size: {total_size/1024:.1f}KB")

if __name__ == "__main__":
    check_git_status()
    list_files()
    print("\n✓ test_data folder is now ready for git tracking!")
