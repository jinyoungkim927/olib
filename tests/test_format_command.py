#\!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

# Test file path
test_file = '/tmp/test_format_issues.md'

# Print the content of the test file
print("Original content of test file:")
print("-" * 50)
with open(test_file, 'r') as f:
    content = f.read()
    print(content)
print("-" * 50)

# Run the format fix command
print("\nRunning the format fix command on the test file...")
cmd = ['olib', 'format', 'fix', '--dry-run', '--verbose', test_file]
try:
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Command: {' '.join(cmd)}")
    print("Exit code:", result.returncode)
    print("Output:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
except Exception as e:
    print(f"Error running command: {e}")

# Verify the formatter works directly
print("\nVerifying formatter directly...")
from obsidian_librarian.commands.format import fix_math_formatting

# Test with the content
fixed_content = fix_math_formatting(content)

# Check if it's different
is_changed = fixed_content \!= content
print(f"Content changed: {is_changed}")

if is_changed:
    print("\nFixed content:")
    print("-" * 50)
    print(fixed_content)
    print("-" * 50)
