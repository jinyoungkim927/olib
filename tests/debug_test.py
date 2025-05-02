#\!/usr/bin/env python3
import os
import shutil
from obsidian_librarian.config import get_config
from obsidian_librarian.commands.format import process_note_formatting, fix_math_formatting

# Create test content
test_content = """# Test Format File
#test #with-[[brackets]]

This is a test file with [[[triple brackets]]] and [[nested [[wiki]] links]].

Math expression: $\hat{\beta} = \arg\min_{\[[Beta]]} (y - X\beta)^2 + \lambda \|\beta\|_2^2$

Also check [[[[quadruple brackets]]]] and __SIMPLE_LINK_42__ placeholders.
"""

# Get vault path
config = get_config()
vault_path = config.get('vault_path')
print(f"Vault path: {vault_path}")

# Create test file
test_file = os.path.join(vault_path, "TEST_FORMAT_DEBUG.md")
with open(test_file, 'w') as f:
    f.write(test_content)
print(f"Created test file: {test_file}")

# Test direct formatting
fixed_content = fix_math_formatting(test_content)
print("\nDirect formatting test:")
if test_content \!= fixed_content:
    print("✓ Direct formatter made changes")
else:
    print("✗ Direct formatter made NO changes")

# Test process_note_formatting
print("\nCLI processing test:")
result = process_note_formatting(test_file, fix_math=True, fix_links=True, dry_run=False)
print(f"CLI process_note_formatting returned: {result}")

# Read file to check if it was actually modified
with open(test_file, 'r') as f:
    final_content = f.read()

if final_content \!= test_content:
    print("✓ File was actually modified")
else:
    print("✗ File was NOT modified")

# Cleanup
os.remove(test_file)
print(f"Removed test file: {test_file}")
