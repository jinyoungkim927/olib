import unittest
import os
import tempfile
import numpy as np
from pathlib import Path
import json
from unittest.mock import MagicMock

# --- REMOVE FileMetadata import ---
# from obsidian_librarian.utils.file_operations import FileMetadata # <-- REMOVE THIS LINE
# --- End removal ---
from obsidian_librarian.utils import indexing
from obsidian_librarian.commands import index as index_commands
from obsidian_librarian import config, vault_state

class TestIndexingUtils(unittest.TestCase):

    def test_extract_frontmatter_with_data(self):
        """Test extracting frontmatter when it exists in metadata."""
        # --- Use MagicMock instead of FileMetadata ---
        mock_metadata = MagicMock()
        mock_metadata.frontmatter = {"key": "value", "tags": ["a", "b"]}
        # Add other attributes if the mock needs them for other reasons, but not needed for this test
        # mock_metadata.file_path = Path("dummy.md")
        # mock_metadata.rel_path = "dummy.md"
        # ... etc
        # --- End mock setup ---

        fm = indexing.extract_frontmatter(mock_metadata) # Call the function from the imported module
        self.assertIsNotNone(fm)
        self.assertEqual(fm, {"key": "value", "tags": ["a", "b"]})

    def test_extract_frontmatter_empty(self):
        """Test extracting frontmatter when it's empty in metadata."""
        # --- Use MagicMock ---
        mock_metadata = MagicMock()
        mock_metadata.frontmatter = {}
        # --- End mock setup ---

        fm = indexing.extract_frontmatter(mock_metadata)
        self.assertIsNotNone(fm) # frontmatter library returns {} for empty frontmatter
        self.assertEqual(fm, {})

    def test_extract_frontmatter_none(self):
        """Test extracting frontmatter when there is no frontmatter section."""
        # --- Use MagicMock ---
        mock_metadata = MagicMock()
        mock_metadata.frontmatter = None # Simulate VaultState storing None
        # --- End mock setup ---

        fm = indexing.extract_frontmatter(mock_metadata)
        self.assertIsNone(fm)

    def test_extract_frontmatter_parsing_error_handled_by_vaultstate(self):
        """Test case where VaultState might have failed parsing (represented by None)."""
        # --- Use MagicMock ---
        mock_metadata = MagicMock()
        mock_metadata.frontmatter = None # Assume VaultState sets frontmatter to None on error
        # --- End mock setup ---

        fm = indexing.extract_frontmatter(mock_metadata)
        self.assertIsNone(fm)

    # --- Add a test for when the attribute is missing entirely ---
    def test_extract_frontmatter_attribute_missing(self):
        """Test extracting frontmatter when the attribute doesn't exist."""
        mock_metadata = MagicMock()
        # Remove the attribute if it exists by default on MagicMock (it shouldn't)
        # Or configure the mock specifically:
        mock_metadata.configure_mock(**{'frontmatter': MagicMock(side_effect=AttributeError)})
        # A simpler way for this specific case might be to use a basic object:
        # mock_metadata = object() # A plain object won't have .frontmatter

        # Let's stick with MagicMock but ensure the attribute isn't there.
        # We can actually just *not* set it. hasattr will handle it.
        mock_without_attribute = MagicMock(spec=object) # spec=object prevents arbitrary attributes

        fm = indexing.extract_frontmatter(mock_without_attribute)
        self.assertIsNone(fm)
    # --- End new test ---


if __name__ == '__main__':
    unittest.main() 
