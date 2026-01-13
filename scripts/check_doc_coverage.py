#!/usr/bin/env python3
"""Check documentation coverage for the rustkmer API."""

import sys
sys.path.insert(0, '../python')
from rustkmer import database, fuzzy_query, query, stats, exceptions

# Count classes and methods
import inspect

modules = [database, fuzzy_query, query, stats, exceptions]
total_classes = 0
total_methods = 0
documented_methods = 0

for module in modules:
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            total_classes += 1
            for method_name, method_obj in inspect.getmembers(obj, inspect.ismethod):
                if not method_name.startswith('_'):
                    total_methods += 1
                    if method_obj.__doc__:
                        documented_methods += 1

print(f'Classes: {total_classes}')
print(f'Public methods: {total_methods}')
print(f'Documented methods: {documented_methods}')
if total_methods > 0:
    coverage = (documented_methods / total_methods) * 100
    print(f'Documentation coverage: {coverage:.1f}%')
