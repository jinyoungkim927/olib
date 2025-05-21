#!/usr/bin/env python3

from obsidian_librarian.commands.utilities.format_fixer import FormatFixer

# Create a test string with the specific example
test_text = "This example has a math expression: $ u_2(\sigma_1, \sigma_2) \geq v_2 $ with spaces."

# Create the formatter
formatter = FormatFixer(verbose=True)

# Test the apply_math_fixes method specifically
result = formatter.apply_math_fixes(test_text)

# Show the results clearly
print("Original text:")
print(test_text.replace('$', '|$|'))
print("\nFormatted text:")
print(result.replace('$', '|$|'))

# Test additional examples
print("\nAdditional examples:")
examples = [
    "$ u_2(\sigma_1, \sigma_2) \geq v_2 $",  # Spaces on both sides
    "$u_1(\sigma_1, \sigma_2) \geq v_1 $",   # Space at end
    "$ u_4(\sigma_1, \sigma_2) \geq v_4$",   # Space at beginning
    "Some text $ with math $ and more text" # Inline with context
]

for example in examples:
    fixed = formatter.apply_math_fixes(example)
    print(f"\nOriginal: {example.replace('$', '|$|')}")
    print(f"Fixed:    {fixed.replace('$', '|$|')}")