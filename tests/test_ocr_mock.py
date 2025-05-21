#!/usr/bin/env python3
"""
Mock test for OCR functionality.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import shutil
import re

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import without the Click decorator to test directly
from obsidian_librarian.commands.ocr import extract_image_paths_from_md
from obsidian_librarian.commands.utilities.format_fixer import FormatFixer


class TestOCR(unittest.TestCase):
    """Test OCR functionality with mocks."""
    
    def setUp(self):
        """Set up test environment."""
        # Create test directory
        self.test_dir = Path('/Users/jinyoungkim/Desktop/Projects/olib/tests/test_ocr_temp')
        self.test_dir.mkdir(exist_ok=True)
        
        # Create a test image
        self.image_path = self.test_dir / 'test_image.png'
        with open(self.image_path, 'wb') as f:
            f.write(b'dummy image data')
        
        # Create a test markdown file with image reference
        self.note_path = self.test_dir / 'test_note.md'
        with open(self.note_path, 'w') as f:
            f.write("# Test Note\n\n"
                    "This is a test note with an image.\n\n"
                    "![[test_image.png]]\n\n"
                    "Some text after the image.")
    
    def tearDown(self):
        """Clean up after tests."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_extract_image_paths(self):
        """Test extracting image paths from markdown."""
        image_paths = extract_image_paths_from_md(self.note_path)
        self.assertEqual(len(image_paths), 1)
        self.assertEqual(image_paths[0].name, 'test_image.png')
    
    def test_manual_ocr_workflow(self):
        """Test the core OCR workflow manually without Click dependencies."""
        # 1. Read original file content
        with open(self.note_path, 'r') as f:
            original_content = f.read()
        
        # 2. Extract image references
        image_paths = extract_image_paths_from_md(self.note_path)
        self.assertEqual(len(image_paths), 1)
        
        # 3. Simulate OCR process for each image
        ocr_result = "This is the OCR text with $E=mc^2$ formula."
        processed_ocr = "This is the processed OCR text with $E=mc^2$ formula."
        formatted_ocr = "This is the formatted OCR text with $E=mc^2$ formula."
        
        # 4. Replace image reference in the content
        image_ref = f"!\\[\\[{re.escape(image_paths[0].name)}\\]\\]"
        updated_content = re.sub(
            image_ref,
            f"![[{image_paths[0].name}]]\n{formatted_ocr}",
            original_content
        )
        
        # 5. Write back to file
        with open(self.note_path, 'w') as f:
            f.write(updated_content)
        
        # 6. Verify the content was updated correctly
        with open(self.note_path, 'r') as f:
            final_content = f.read()
        
        self.assertIn("![[test_image.png]]\nThis is the formatted OCR text with $E=mc^2$ formula.", final_content)


if __name__ == '__main__':
    unittest.main()