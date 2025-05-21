"""
Tests for the simplified formatter.
"""

import pytest
import os
import re
from pathlib import Path
import tempfile
import shutil

from obsidian_librarian.commands.utilities.simplified_format_fixer import FormatFixer
from obsidian_librarian.utils.simplified_post_process import clean_llm_output, process_ocr_output


class TestSimplifiedFormatter:
    """Test cases for the simplified FormatFixer class."""
    
    def setup_method(self):
        """Set up a temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.formatter = FormatFixer(verbose=False)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def create_test_file(self, content):
        """Create a test file with the given content."""
        test_file = os.path.join(self.temp_dir, "test.md")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return test_file

    def test_math_content_fixes(self):
        """Test that math content is properly fixed."""
        content = r"This is a test with math: $A\_1 + B\_2$ and $\frac{1}{2}$."
        expected = r"This is a test with math: $A_1 + B_2$ and $\frac{1}{2}$."
        
        file_path = self.create_test_file(content)
        self.formatter.format_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            result = f.read()
        
        assert result == expected

    def test_display_math_formatting(self):
        """Test that display math is properly formatted."""
        content = r"Here's some display math:$$\sum_{i=1}^{n} i = \frac{n(n+1)}{2}$$"
        expected = r"Here's some display math:

$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$"
        
        file_path = self.create_test_file(content)
        self.formatter.format_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            result = f.read()
        
        assert result.strip() == expected.strip()

    def test_latex_delimiter_conversion(self):
        """Test that LaTeX delimiters are properly converted."""
        content = r"Inline math: \(a + b\) and display math: \[\sum_{i=1}^{n} i\]"
        expected = r"Inline math: $a + b$ and display math: 

$$
\sum_{i=1}^{n} i
$$"
        
        file_path = self.create_test_file(content)
        self.formatter.format_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            result = f.read()
        
        assert result.strip() == expected.strip()

    def test_inline_math_spacing(self):
        """Test that spacing around inline math is fixed."""
        content = r"No space$x$here and $  y  $ has spaces."
        expected = r"No space $x$ here and $y$ has spaces."
        
        file_path = self.create_test_file(content)
        self.formatter.format_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            result = f.read()
        
        assert result == expected

    def test_code_block_preservation(self):
        """Test that code blocks are preserved during formatting."""
        content = r"""
        Text with math $a\_1$ and code:
        ```python
        def f(x):
            return x**2
        ```
        More text $b\_2$.
        """
        expected = r"""
        Text with math $a_1$ and code:
        ```python
        def f(x):
            return x**2
        ```
        More text $b_2$.
        """
        
        file_path = self.create_test_file(content)
        self.formatter.format_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            result = f.read()
        
        assert result.strip() == expected.strip()

    def test_ocr_text_cleaning(self):
        """Test OCR text processing."""
        content = r"""
        OCR output with issues:
        - Malformed math: $a\_1 + b \$
        - Missing backslash: ext{testing}
        - Bad spacing:$x$next to word
        """
        
        cleaned = process_ocr_output(content)
        
        # Check that specific issues are fixed
        assert r"$a_1 + b$" in cleaned  # Fixed malformed math
        assert r"\text{testing}" in cleaned  # Fixed missing backslash
        assert "$x$ next" in cleaned  # Fixed spacing


# Add test cases for simplified_post_process.py
class TestPostProcess:
    """Test cases for simplified post-processing utilities."""
    
    def test_clean_llm_output(self):
        """Test cleaning of LLM output."""
        raw_text = r"""
        ```markdown
        Math with errors: $a\_1 + b\_2$
        
        Equation: $$\sum\_{i=1}^{n} i$$
        
        Missing backslash: ext{text}
        ```
        """
        
        cleaned = clean_llm_output(raw_text)
        
        # Check that specific issues are fixed
        assert "_" in cleaned and "\\_" not in cleaned  # Underscores are fixed
        assert "\\text{text}" in cleaned  # Missing backslash is fixed
        assert "```markdown" not in cleaned  # Markdown fences are removed

    def test_process_ocr_output(self):
        """Test comprehensive OCR processing."""
        raw_text = r"""
        ---
        OCR processing: 2023-01-01 12:00:00
        
        # Heading
        
        Math: $a\_1$
        
        $$\[x=\frac{-b \pm \sqrt{b^2-4ac}}{2a}\]$$
        
        **Title**
        : Content
        """
        
        processed = process_ocr_output(raw_text)
        
        # Check OCR-specific fixes
        assert "---\nOCR processing" not in processed  # Header is removed
        assert "**Heading**" in processed  # Heading converted to bold
        assert "$a_1$" in processed  # Math is fixed
        assert "**Title**: Content" in processed  # Layout is fixed