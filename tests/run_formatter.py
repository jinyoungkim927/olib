#!/usr/bin/env python3
"""
Test the formatter on the game theory example.
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from obsidian_librarian.commands.utilities.format_fixer import FormatFixer

# Read the input file
with open('tests/test_game_theory.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Apply formatting
fixer = FormatFixer(verbose=True)
fixed_content = fixer.apply_all_fixes(content)

# Write the output file
with open('tests/test_game_theory_fixed.md', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("Formatting complete. Check tests/test_game_theory_fixed.md for results.")