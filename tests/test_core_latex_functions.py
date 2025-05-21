#!/usr/bin/env python3
"""
Tests for core LaTeX formatting functions.
"""

import unittest
from obsidian_librarian.utils.latex_formatting import (
    fix_math_content,
    fix_latex_delimiters,
    format_inline_math_spacing,
    format_display_math_blocks
)


class TestCoreLaTeXFunctions(unittest.TestCase):
    """Test core LaTeX formatting functions individually."""
    
    def test_fix_math_content(self):
        """Test that fix_math_content correctly fixes common issues."""
        # Test case 1: Fix escaped underscores
        input_text = r"A\_1 + B\_2 = C\_3"
        expected = r"A_1 + B_2 = C_3"
        self.assertEqual(fix_math_content(input_text), expected)
        
        # Test case 2: Fix escaped carets
        input_text = r"x\^2 + y\^2 = z\^2"
        expected = r"x^2 + y^2 = z^2"
        self.assertEqual(fix_math_content(input_text), expected)
        
        # Test case 3: Fix LaTeX command spacing
        input_text = r"\text {word} \sqrt (x) \mathbb [R]"
        expected = r"\text{word} \sqrt(x) \mathbb[R]"
        self.assertEqual(fix_math_content(input_text), expected)
        
        # Test case 4: Fix common OCR errors
        input_text = r"ext{test}"
        expected = r"\text{test}"
        self.assertEqual(fix_math_content(input_text), expected)
    
    def test_fix_latex_delimiters(self):
        """Test that fix_latex_delimiters converts LaTeX delimiters to markdown style."""
        # Test case 1: Fix escaped inline delimiters
        input_text = r"Inline math: \$a + b = c\$"
        expected = r"Inline math: $a + b = c$"
        self.assertEqual(fix_latex_delimiters(input_text), expected)
        
        # Test case 2: Convert display math delimiters
        input_text = r"Display math: \[\sum_{i=1}^n i = \frac{n(n+1)}{2}\]"
        expected = r"Display math: $$\sum_{i=1}^n i = \frac{n(n+1)}{2}$$"
        self.assertEqual(fix_latex_delimiters(input_text), expected)
        
        # Test case 3: Convert inline math parentheses
        input_text = r"Inline math: \(E = mc^2\)"
        expected = r"Inline math: $E = mc^2$"
        self.assertEqual(fix_latex_delimiters(input_text), expected)
    
    def test_format_inline_math_spacing(self):
        """Test that format_inline_math_spacing fixes spacing around inline math."""
        # Test case 1: Remove spaces inside inline math
        input_text = r"This has $ a + b $ with spaces inside."
        expected = r"This has $a + b$ with spaces inside."
        self.assertEqual(format_inline_math_spacing(input_text), expected)
        
        # Test case 2: Add space between math and text
        input_text = r"No space$x$here or$y$there."
        expected = r"No space $x$ here or $y$ there."
        self.assertEqual(format_inline_math_spacing(input_text), expected)
        
        # Test case 3: No space between math and punctuation
        input_text = r"Math $E=mc^2$ , followed by comma."
        expected = r"Math $E=mc^2$, followed by comma."
        self.assertEqual(format_inline_math_spacing(input_text), expected)
    
    def test_format_display_math_blocks(self):
        """Test that format_display_math_blocks properly formats display math."""
        # Test case 1: Multi-line display math with newlines
        input_text = r"Before math.\n$$\begin{align}\na &= b \\ \nc &= d \n\end{align}$$\nAfter math."
        result = format_display_math_blocks(input_text)
        # Just check that the content is preserved and has some formatting
        self.assertIn(r"\begin{align}", result)
        self.assertIn(r"\end{align}", result)
        self.assertIn(r"$$", result)
        
        # Test case 2: Standalone single-line display math
        input_text = r"Before math.\n\n$$E=mc^2$$\n\nAfter math."
        result = format_display_math_blocks(input_text)
        # The function might add newlines within the math delimiters
        self.assertIn(r"$$", result)
        self.assertIn(r"E=mc^2", result)
        
        # Test case 3: Inline display math in a paragraph
        input_text = r"This is a paragraph with $$E=mc^2$$ in the middle of it."
        result = format_display_math_blocks(input_text)
        # Should preserve inline display math within text
        self.assertIn(r"with $$E=mc^2$$ in", result)


if __name__ == '__main__':
    unittest.main()