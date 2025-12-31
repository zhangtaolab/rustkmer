#!/usr/bin/env python3
"""Check for broken internal links in the generated documentation."""

import re
from pathlib import Path

site_dir = Path('../site')
if not site_dir.exists():
    print('No site directory to check')
    exit(0)

# Find all HTML files and check for internal links
broken_links = []
for html_file in site_dir.rglob('*.html'):
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for broken internal links
        internal_links = re.findall(r'href=\"([^\"#]+)\"', content)
        for link in internal_links:
            if link.startswith('http'):
                continue  # Skip external links
            if link.startswith('#'):
                continue  # Skip anchor links
            if link.startswith('mailto:'):
                continue  # Skip mailto links
            if link.startswith('../'):
                # Check if relative path exists
                target_path = html_file.parent / link
                if not target_path.exists():
                    broken_links.append(f'{html_file}: {link}')
    except Exception as e:
        print(f'Error checking {html_file}: {e}')

if broken_links:
    print(f'Found {len(broken_links)} broken links:')
    for link in broken_links[:10]:  # Show first 10
        print(f'  {link}')
    if len(broken_links) > 10:
        print(f'  ... and {len(broken_links) - 10} more')
    exit(1)
else:
    print('No broken internal links found')

