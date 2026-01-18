#!/usr/bin/env python3
"""Check the original import in stage1_fix_backup"""

with open('counter.rs.stage1_fix_backup', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'use rustkmer::hash' in line:
        print(f"Line {i+1}: {line.strip()}")
        break
