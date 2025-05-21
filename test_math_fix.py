#!/usr/bin/env python3

from obsidian_librarian.utils.compact_math import compact_math_blocks
from obsidian_librarian.utils.latex_formatting import format_inline_math_spacing
from obsidian_librarian.commands.utilities.format_fixer import FormatFixer

# Create sample text with problematic spacing
test_text = """
Here is some text with math: $ u_2(\sigma_1, \sigma_2) \geq v_2 $ in the middle.

And another example with different spacing:
$u_1(\sigma_1, \sigma_2) \geq v_1$

And one with space at the end: $u_3(\sigma_1, \sigma_2) \geq v_3 $

And one with space at the beginning: $ u_4(\sigma_1, \sigma_2) \geq v_4$

Let's also test display math:

$$ 
u_5(\sigma_1, \sigma_2) \geq v_5 
$$

"""

# Define function to print math expressions more clearly
def highlight_math(text):
    import re
    # Replace $ with visible markers to clearly show spacing issues
    marked = re.sub(r'\$', '|$|', text)
    return marked

# Test individual functions
print("Testing format_inline_math_spacing:")
result1 = format_inline_math_spacing(test_text)
print(highlight_math(result1))
print("-" * 50)

print("Testing compact_math_blocks:")
result2 = compact_math_blocks(test_text)
print(highlight_math(result2))
print("-" * 50)

# Test the full formatter
print("Testing full FormatFixer:")
fixer = FormatFixer()
result3 = fixer.apply_math_fixes(test_text)
print(highlight_math(result3))
print("-" * 50)

# Show original and fixed math expressions
print("Example conversions:")
examples = [
    "$ u_2(\sigma_1, \sigma_2) \geq v_2 $",  # Spaces on both sides
    "$u_1(\sigma_1, \sigma_2) \geq v_1 $",   # Space at end
    "$ u_4(\sigma_1, \sigma_2) \geq v_4$"    # Space at beginning
]

for example in examples:
    fixed = format_inline_math_spacing(example)
    print(f"Original: {highlight_math(example)}")
    print(f"Fixed:    {highlight_math(fixed)}")
    print()