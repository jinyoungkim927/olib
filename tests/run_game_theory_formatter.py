#!/usr/bin/env python3
"""
Custom formatter for the game theory text.
"""
import sys
import os
import re

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Read the input file
with open('tests/test_game_theory.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Custom formatting specifically for game theory

# 1. Fix display math formatting - compact one line with no blank lines
def format_display_math(match):
    inner = match.group(1).strip().replace('\n', ' ')
    return f"$${inner}$$"

content = re.sub(r'\$\$(.*?)\$\$', format_display_math, content, flags=re.DOTALL)

# 2. Add line break before display math if not at beginning of line
content = re.sub(r'([^\n])\s*(\$\$)', r'\1\n\n\2', content)

# 3. Fix connectors after display math
content = re.sub(r'(\$\$)\s*\n\s*(Then|So|Hence|Therefore)', r'\1 \2', content)

# 4. Fix inline math spacing
# Remove spaces inside inline math delimiters
content = re.sub(r'\$\s+(.*?)\s+\$', r'$\1$', content)

# 5. Fix spacing between math and text
content = re.sub(r'(\$[^\$\n]+\$)([a-zA-Z0-9])', r'\1 \2', content)
content = re.sub(r'([a-zA-Z0-9])(\$[^\$\n]+\$)', r'\1 \2', content)

# 6. Fix comma spacing 
content = re.sub(r'(\$[^\$]+\$),([^\s])', r'\1, \2', content)
content = re.sub(r',\s*(\$)', r', \1', content)

# 7. Fix spacing between adjacent math expressions
content = re.sub(r'(\$[^\$]+\$)\s*(\$)', r'\1 \2', content)

# 8. Fix spacing after display math
content = re.sub(r'(\$\$)([A-Za-z])', r'\1 \2', content)

# 9. Make sure display math is followed by a blank line if not followed by a connector
content = re.sub(r'(\$\$)(?!\s+(Then|So|Hence|Therefore))', r'\1\n', content)

# Write the output file
with open('tests/test_game_theory_custom.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("Custom formatting complete. Check tests/test_game_theory_custom.md for results.")