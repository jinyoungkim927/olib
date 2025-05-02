#!/usr/bin/env python3
import os
import shutil
from obsidian_librarian.config import get_config
# --- FIX: Import the class ---
from obsidian_librarian.commands.utilities.format_fixer import FormatFixer
# --- End Fix ---

# Create test content
test_content = r"""# Test Format File \h
#test #with-[[brackets]]

This is a test file with [[[triple brackets]]] and [[nested [[wiki]] links]].

Math expression: $\hat{\beta} = \arg\min_{\[[Beta]]} (y - X\beta)^2 + \lambda \|\beta\|_2^2$

Also check [[[[quadruple brackets]]]] and __SIMPLE_LINK_42__ placeholders.
"""

# Get vault path
config_data = get_config() # Renamed variable to avoid conflict
vault_path = config_data.get('vault_path')
print(f"Vault path: {vault_path}")

# Create test file
test_file = os.path.join(vault_path, "TEST_FORMAT_DEBUG.md")
with open(test_file, 'w') as f:
    f.write(test_content)
print(f"Created test file: {test_file}")

# --- FIX: Instantiate the class and call the method ---
fixer_instance = FormatFixer(verbose=True) # Instantiate (verbose might be helpful for debugging)
fixed_content = fixer_instance.apply_all_fixes(test_content) # Call the method
# --- End Fix ---

print("\nDirect formatting test:")
if test_content != fixed_content:
    print("✓ Direct formatter made changes")
else:
    print("✗ Direct formatter made NO changes")

# Test process_note_formatting - This part needs rethinking for automated tests
# print("\nCLI processing test:")
# result = process_note_formatting(test_file, fix_math=True, fix_links=True, dry_run=False) # This function likely doesn't exist for direct import
# print(f"CLI process_note_formatting returned: {result}")

# Read file to check if it was actually modified (only relevant if CLI command was run)
# with open(test_file, 'r') as f:
#     final_content = f.read()
#
# if final_content != test_content:
#     print("✓ File was actually modified")
# else:
#     print("✗ File was NOT modified")

# Cleanup
os.remove(test_file)
print(f"Removed test file: {test_file}")
