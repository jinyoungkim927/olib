#!/usr/bin/env python3
"""
Final manual formatter focusing on LaTeX spacing.
"""
import sys
import os
import re

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from obsidian_librarian.utils.compact_math import compact_math_blocks

# Input original game theory example
with open('tests/test_game_theory.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Apply our compact math formatter
result = compact_math_blocks(content)

# Write the result
with open('tests/game_theory_manual.md', 'w', encoding='utf-8') as f:
    f.write(result)

print("Manual formatting complete. Result saved to tests/game_theory_manual.md")