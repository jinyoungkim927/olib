#\!/usr/bin/env python3
import os
import subprocess
from obsidian_librarian.config import get_config

# Create a test file with known issues
test_content = '''# Test Format Debug File
#tag #with-[[brackets]]

This is a test file with [[[triple brackets]]] and [[nested [[wiki]] links]].

Also check [[[[quadruple brackets]]]] and __SIMPLE_LINK_42__ placeholders.
'''

# Get vault path
config = get_config()
vault_path = config.get('vault_path')
print(f"Vault path: {vault_path}")

# Create test file in vault
test_file = os.path.join(vault_path, 'FORMAT_DEBUG_TEST.md')
with open(test_file, 'w', encoding='utf-8') as f:
    f.write(test_content)
print(f"Created test file: {test_file}")

# Install the package to make sure changes are applied
print("\nInstalling package...")
subprocess.run(["pip", "install", "-e", "."], check=True)

# Now run the CLI command
print("\nRunning CLI command...")
try:
    # Run for a single file
    print("Testing single file command:")
    subprocess.run(["python", "-m", "obsidian_librarian.cli", "format", "fix", "FORMAT_DEBUG_TEST"], check=True)
    
    # Now run for all files
    print("\nTesting command for all files:")
    subprocess.run(["python", "-m", "obsidian_librarian.cli", "format", "fix"], check=True,
                   input=b"all\ny\n")  # Simulates answering "all" then "y" to prompts
                   
except Exception as e:
    print(f"Error running CLI: {e}")

# Check if test file was modified
with open(test_file, 'r', encoding='utf-8') as f:
    current_content = f.read()

print("\nResults:")
if current_content \!= test_content:
    print("✓ Test file was modified\!")
    print("Original:", test_content[:50] + "...")
    print("Modified:", current_content[:50] + "...")
else:
    print("✗ Test file was NOT modified\!")

# Clean up test file
os.remove(test_file)
print(f"Removed test file: {test_file}")
