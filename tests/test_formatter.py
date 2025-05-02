#!/usr/bin/env python3
import pytest
# Import from the utility module
from obsidian_librarian.commands.utilities.format_fixer import FormatFixer

# Test content
test_content = """# Test Format File
#tag #with-[[brackets]]

This is a test file with [[[triple brackets]]] and [[nested [[wiki]] links]].

Also check [[[[quadruple brackets]]]] and __SIMPLE_LINK_42__ placeholders."""

# Apply the formatter
fixer_instance = FormatFixer()
fixed_content = fixer_instance.apply_all_fixes(test_content)

# Print results
print("Original content:")
print("-" * 50)
print(test_content)
print("-" * 50)

print("\nFixed content:")
print("-" * 50)
print(fixed_content)
print("-" * 50)

# Check for specific fixes
changes = []
if "#with-[[brackets]]" in test_content and "#with-[[brackets]]" not in fixed_content:
    changes.append("✓ Fixed hashtags with brackets")
if "[[[triple brackets]]]" in test_content and "[[[triple brackets]]]" not in fixed_content:
    changes.append("✓ Fixed triple brackets")
if "[[nested [[wiki]] links]]" in test_content and "[[nested [[wiki]] links]]" not in fixed_content:
    changes.append("✓ Fixed nested wiki links")
if "[[[[quadruple brackets]]]]" in test_content and "[[[[quadruple brackets]]]]" not in fixed_content:
    changes.append("✓ Fixed quadruple brackets")
if "__SIMPLE_LINK_42__" in test_content and "__SIMPLE_LINK_42__" not in fixed_content:
    changes.append("✓ Fixed SIMPLE_LINK placeholders")

if changes:
    print("\nImproved formatting:")
    for change in changes:
        print(change)
else:
    print("\nNo formatting improvements detected")
