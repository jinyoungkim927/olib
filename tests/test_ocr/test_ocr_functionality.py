"""
Tests for the OCR functionality in the Obsidian Librarian.
"""

import os
import pytest
from unittest import mock
from pathlib import Path
import shutil
import tempfile

from obsidian_librarian.commands.ocr import (
    extract_image_paths_from_md,
    process_image_with_gpt4v,
    ocr_note
)


class TestOCRFunctionality:
    """Test OCR functionality with mocked GPT-4V calls."""

    @pytest.fixture
    def setup_test_environment(self):
        """Set up a temporary environment for testing OCR."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Create a mock image file
        mock_image_path = os.path.join(temp_dir, "test_math_image.png")
        with open(mock_image_path, "wb") as f:
            # Create an empty PNG file (content doesn't matter for our tests)
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
        
        # Create a test markdown file
        test_md_path = os.path.join(temp_dir, "test_ocr.md")
        with open(test_md_path, "w") as f:
            f.write("# Math Concepts\n\n"
                    "This note contains mathematical concepts and formulas.\n\n"
                    "![[test_math_image.png]]\n\n"
                    "Some additional text after the image reference.")
        
        yield {
            "temp_dir": temp_dir,
            "test_md_path": test_md_path,
            "mock_image_path": mock_image_path
        }
        
        # Cleanup after tests
        shutil.rmtree(temp_dir)

    def test_extract_image_paths(self, setup_test_environment):
        """Test that image references are correctly extracted from markdown files."""
        env = setup_test_environment
        
        # Test extraction function
        image_paths = extract_image_paths_from_md(Path(env["test_md_path"]))
        
        # Verify the correct image path was extracted
        assert len(image_paths) == 1
        assert image_paths[0].name == "test_math_image.png"

    @mock.patch("obsidian_librarian.commands.ocr.process_image_with_gpt4v")
    def test_ocr_functionality(self, mock_process_image, setup_test_environment, monkeypatch):
        """Test the full OCR functionality with mocked GPT-4V call."""
        env = setup_test_environment
        
        # Set up mock return value for process_image_with_gpt4v
        mock_ocr_result = """
This is a mathematical equation:

$$
E = mc^2
$$

Where:
- $E$ is energy
- $m$ is mass
- $c$ is the speed of light
"""
        mock_process_image.return_value = mock_ocr_result
        
        # Mock the config to use our temp directory as vault path
        def mock_get_config():
            return {"vault_path": os.path.dirname(env["test_md_path"])}
        
        monkeypatch.setattr("obsidian_librarian.commands.ocr.get_config", mock_get_config)
        
        # Run the OCR command
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(ocr_note, ["test_ocr"])
        
        # Verify the OCR command executed successfully
        assert result.exit_code == 0
        
        # Read the updated file
        with open(env["test_md_path"], "r") as f:
            updated_content = f.read()
        
        # Verify the OCR result was inserted after the image reference
        assert "![[test_math_image.png]]" in updated_content
        assert "$$\nE = mc^2\n$$" in updated_content
        assert "Where:" in updated_content
        assert "$E$ is energy" in updated_content
        
        # Verify original content is preserved
        assert "# Math Concepts" in updated_content
        assert "This note contains mathematical concepts and formulas." in updated_content
        assert "Some additional text after the image reference." in updated_content
        
        # Verify mock was called correctly
        mock_process_image.assert_called_once()
        args, _ = mock_process_image.call_args
        assert "test_math_image.png" in str(args[0])
        assert args[1] == "test_ocr"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])