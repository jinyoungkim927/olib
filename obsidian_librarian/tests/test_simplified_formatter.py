"""
Tests for the consolidated formatter.
"""

import pytest
import os
import re
from pathlib import Path
import tempfile
import shutil

from obsidian_librarian.commands.utilities.format_fixer import FormatFixer
from obsidian_librarian.utils.post_process_formatting import clean_raw_llm_output as clean_llm_output, post_process_ocr_output as process_ocr_output
from obsidian_librarian.utils.latex_formatting import fix_math_content


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
        """Test that underscores in math content are properly fixed."""
        # Direct test of the math fix function to avoid display formatting differences
        content = r"A\_1 + B\_2"
        expected = r"A_1 + B_2"
        
        result = fix_math_content(content)
        assert "_" in result and "\\_" not in result
        
    def test_inline_math_spacing(self):
        """Test that spacing around inline math is fixed."""
        content = r"No space$x$here"
        
        file_path = self.create_test_file(content)
        self.formatter.format_file(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            result = f.read()
        
        # Should have spaces around inline math
        assert " $x$ " in result
        

class TestPostProcess:
    """Test cases for post-processing utilities."""
    
    def test_backslash_fix(self):
        """Test that missing backslash commands are fixed."""
        raw_text = "Missing backslash: ext{text}"
        
        cleaned = process_ocr_output(raw_text)
        
        # Check that specific issues are fixed
        assert "\\text{text}" in cleaned  # Fixed missing backslash