#!/usr/bin/env python3
"""Restore counter.rs from backup"""

import shutil

# Copy backup back
shutil.copy('counter.rs.stage1_fix_backup', 'counter.rs')

print("Restored counter.rs from backup")
