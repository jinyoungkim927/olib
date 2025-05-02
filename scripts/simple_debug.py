#\!/usr/bin/env python3
import os
import shutil
from obsidian_librarian.config import get_config
from obsidian_librarian.commands.format import process_note_formatting

# Get vault path
config = get_config()
vault_path = config.get('vault_path')
print(f"Vault path: {vault_path}")

# Copy test file to vault
test_source = "/tmp/test_format_issues.md"
test_dest = os.path.join(vault_path, "TEST_FORMAT_ISSUES.md")
shutil.copy(test_source, test_dest)
print(f"Created test file: {test_dest}")

# Process the file
print("\nProcessing test file...")
was_modified = process_note_formatting(test_dest, fix_math=True, fix_links=True, dry_run=False, quiet=False)
print(f"Was modified: {was_modified}")

# Read the file to check if it was actually changed
print("\nReading updated file content...")
with open(test_dest, 'r') as f:
    updated_content = f.read()

with open(test_source, 'r') as f:
    original_content = f.read()

is_different = updated_content \!= original_content
print(f"Content actually changed: {is_different}")

if is_different:
    print("\nOriginal content:")
    print("-" * 50)
    print(original_content)
    print("-" * 50)
    
    print("\nUpdated content:")
    print("-" * 50)
    print(updated_content)
    print("-" * 50)

# Clean up
os.remove(test_dest)
print(f"Removed test file: {test_dest}")
