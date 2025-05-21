#!/usr/bin/env python3
import sys
import os

# Add the project root to the Python path to find the module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from obsidian_librarian.utils.latex_formatting import fix_latex_delimiters

# --- Test Cases ---
test_strings = [
    # Case from your example
    (r"This has \$F_t\$-measurable content.", r"This has $F_t$-measurable content."),
    # Another simple case
    (r"Fix this: \$\alpha\$", r"Fix this: $\alpha$"),
    # Should not change already correct format
    (r"This is correct: $F_t$.", r"This is correct: $F_t$."),
    # Should not change valid LaTeX commands
    (r"This is correct: \alpha.", r"This is correct: \alpha."),
    # Multiple instances
    (r"Fix \$X_t\$ and \$Y_t\$ please.", r"Fix $X_t$ and $Y_t$ please."),
    # Edge case: single escaped dollar
    (r"A single \$ should not change.", r"A single \$ should not change."),
    # Edge case: escaped backslash then dollar
    (r"An escaped \\$ should not change.", r"An escaped \\$ should not change."),
    # Valid command that shouldn't be touched
    (r"Keep \mathbb{R} as is.", r"Keep \mathbb{R} as is."),
    # Mixed content
    (r"Use \$W_t\$ and also $\sigma$-algebra.", r"Use $W_t$ and also $\sigma$-algebra."),
    # No content between dollars (shouldn't match ideally, but good to check)
    (r"What about \$\$?", r"What about \$\$?"),
     # Content with spaces
    (r"Handle \$ spaced content \$ correctly.", r"Handle $ spaced content $ correctly."),
]

print("--- Testing fix_latex_delimiters ---")
all_passed = True
for i, (input_text, expected_output) in enumerate(test_strings):
    print(f"\nTest {i+1}:")
    print(f"  Input:    {input_text!r}")
    actual_output = fix_latex_delimiters(input_text)
    print(f"  Output:   {actual_output!r}")
    print(f"  Expected: {expected_output!r}")
    if actual_output == expected_output:
        print("  Result:   ✅ PASSED")
    else:
        print("  Result:   ❌ FAILED")
        all_passed = False

print("\n--- Testing Summary ---")
if all_passed:
    print("✅ All tests passed!")
else:
    print("❌ Some tests failed.") 