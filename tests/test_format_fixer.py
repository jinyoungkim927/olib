#!/usr/bin/env python3
"""
Test script to verify the format fixer
"""
import os
import sys
# Import from the utility module
from obsidian_librarian.commands.utilities.simplified_format_fixer import FormatFixer

# Test content with formatting issues
test_content = r"""# Test Format File \h
#tag #with-[[brackets]]

This is a test file with [[[triple brackets]]] and [[nested [[wiki]] links]].

Also check [[[[quadruple brackets]]]] and __SIMPLE_LINK_42__ placeholders.

Math expression: $\hat{\beta} = \arg\min_{\[[Beta]]} (y - X\beta)^2 + \lambda \|\beta\|_2^2$
"""

# Run formatting directly
fixer_instance = FormatFixer()
fixed_content = fixer_instance.apply_all_fixes(test_content)

# Compare results
print("Original content:")
print("-" * 50)
print(test_content)
print("-" * 50)

print("\nFixed content:")
print("-" * 50)
print(fixed_content)
print("-" * 50)

# Check if any changes were made
is_different = fixed_content != test_content
print(f"\nChanges made: {'Yes' if is_different else 'No'}")

# Check specific fixes
if '[[[' in test_content and '[[[' not in fixed_content:
    print("✓ Triple brackets were fixed")
if '[[[[' in test_content and '[[[[' not in fixed_content:
    print("✓ Quadruple brackets were fixed")
if '#with-[[' in test_content and '#with-[[' not in fixed_content:
    print("✓ Hashtags with brackets were fixed")
if '__SIMPLE_LINK_42__' in test_content and '__SIMPLE_LINK_42__' not in fixed_content:
    print("✓ Simple link placeholders were fixed")
