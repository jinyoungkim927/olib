#!/usr/bin/env python3

from obsidian_librarian.commands.utilities.format_fixer import FormatFixer

# The specific example that was causing issues
example = "$ u_2(\sigma_1, \sigma_2) \geq v_2 $"

# Create formatter
formatter = FormatFixer()

# Process the example
result = formatter.apply_math_fixes(example)

# Show results
print(f"Original: {example}")
print(f"Fixed:    {result}")

# Verify no spaces between $ and math content
if result.startswith("$u") and result.endswith("$") and " $" not in result and "$ " not in result:
    print("\nSUCCESS: Spaces have been removed between $ and math content.")
else:
    print("\nFAILURE: Spaces are still present between $ and math content.")
    print(f"Detailed result: '{result}'")
    
# Verify with a more complex example
complex_example = """
Here is a discussion of the equation $ u_2(\sigma_1, \sigma_2) \geq v_2 $ which shows a key result.
Some more text with inline math $ x^2 + y^2 = z^2 $ and then some display math:
$$ 
\begin{align}
f(x) &= x^2 + 2x + 1\\
&= (x+1)^2
\end{align}
$$
"""

complex_result = formatter.apply_math_fixes(complex_example)
print("\nComplex example (fixed):")
print(complex_result)