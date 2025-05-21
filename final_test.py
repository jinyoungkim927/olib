#!/usr/bin/env python3

from obsidian_librarian.commands.utilities.format_fixer import FormatFixer

# Create formatter
formatter = FormatFixer()

# Define several test cases that represent common math expressions
test_cases = [
    # Basic inline math with spaces
    "$ u_2(\sigma_1, \sigma_2) \geq v_2 $",
    
    # Inline math with space only at beginning
    "$ x^2 + y^2 = z^2$",
    
    # Inline math with space only at end
    "$x^2 + y^2 = z^2 $",
    
    # Math expression in a sentence
    "The equation $ E = mc^2 $ is famous.",
    
    # Multiple math expressions in a paragraph
    "If $ x > 0 $ and $ y < 0 $, then $ xy < 0 $.",
    
    # Display math with newlines
    """
    The formula is:
    $$ 
    f(x) = \int_{a}^{b} g(x) dx 
    $$
    """,
    
    # Mixed inline and display math
    """
    We can see that $ a^2 + b^2 = c^2 $ holds when:
    $$ 
    a = 3, b = 4, c = 5 
    $$
    because $ 3^2 + 4^2 = 9 + 16 = 25 = 5^2 $.
    """
]

# Test each case
print("Testing math formatting...\n")
for i, test_case in enumerate(test_cases, 1):
    result = formatter.apply_math_fixes(test_case)
    
    print(f"Test Case {i}:")
    print(f"Original: {test_case.replace('$', '|$|')}")
    print(f"Fixed:    {result.replace('$', '|$|')}")
    
    # Verify no spaces between $ and math content in the result
    if "|$| " not in result.replace('$', '|$|') and " |$|" not in result.replace('$', '|$|'):
        print("✓ PASS: No spaces between $ and math content")
    else:
        print("✗ FAIL: Spaces still exist between $ and math content")
    print()

# Final verification
print("Final verification with a complex example:")
complex_example = """
In game theory, if $ u_2(\sigma_1, \sigma_2) \geq v_2 $ and $ u_1(\sigma_1, \sigma_2) \geq v_1 $, then the strategy profile $(\sigma_1, \sigma_2)$ is a Nash equilibrium.

The payoff function is defined as:
$$ 
u_i(s) = \sum_{j=1}^{n} p_j \cdot v_{ij}
$$

where $ p_j $ is the probability and $ v_{ij} $ is the value.
"""

complex_result = formatter.apply_math_fixes(complex_example)
print(complex_result)