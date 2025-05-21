#!/usr/bin/env python3
import pytest
# Import from the utility module
from obsidian_librarian.commands.utilities.simplified_format_fixer import FormatFixer

test_content = '''# Test Format File
#tag #with-[[brackets]]

This is a test file with [[[triple brackets]]] and [[nested [[wiki]] links]].

Also check [[[[quadruple brackets]]]] and __SIMPLE_LINK_42__ placeholders.
'''

# Instantiate the class and call the method
fixer_instance = FormatFixer()
fixed_content = fixer_instance.apply_all_fixes(test_content)

print("Original content:")
print("-" * 50)
print(test_content[:100])
print("-" * 50)

print("\nFixed content:")
print("-" * 50)
print(fixed_content[:100])
print("-" * 50)

# Compare the content
if fixed_content == test_content:
    print("\nNo changes were made")
else:
    print("\nChanges were made successfully!")
