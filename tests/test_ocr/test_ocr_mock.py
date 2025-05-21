"""
Test script to manually test OCR functionality with mocked GPT-4V API calls.
"""

import os
import sys
from pathlib import Path
from unittest import mock

# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from obsidian_librarian.commands.ocr import (
    extract_image_paths_from_md,
    process_image_with_gpt4v,
    ocr_note
)
from obsidian_librarian.config import get_config


def setup_mock_environment():
    """Set up a mock environment for testing."""
    # Use the test directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Mock the process_image_with_gpt4v function
    # This prevents actual API calls to OpenAI
    original_func = process_image_with_gpt4v
    
    def mock_process_image_with_gpt4v(image_path, note_name):
        print(f"Mock processing image: {image_path}")
        print(f"Note name: {note_name}")
        
        # Return a predefined result
        return """
This is a mathematical equation:

$$
E = mc^2
$$

Where:
- $E$ is energy
- $m$ is mass
- $c$ is the speed of light in vacuum
"""
    
    # Create a simple patch context manager
    class MockPatch:
        def __enter__(self):
            # Replace the original function with our mock
            sys.modules['obsidian_librarian.commands.ocr'].process_image_with_gpt4v = mock_process_image_with_gpt4v
            return mock_process_image_with_gpt4v
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            # Restore the original function
            sys.modules['obsidian_librarian.commands.ocr'].process_image_with_gpt4v = original_func
    
    # Mock the config function
    original_get_config = get_config
    
    def mock_get_config():
        # Return a mock config pointing to our test directory
        return {
            "vault_path": test_dir,
            "api_key": "mock_api_key"  # Fake API key
        }
    
    class MockConfigPatch:
        def __enter__(self):
            # Replace the original function
            sys.modules['obsidian_librarian.config'].get_config = mock_get_config
            sys.modules['obsidian_librarian.commands.ocr'].get_config = mock_get_config
            return mock_get_config
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            # Restore the original function
            sys.modules['obsidian_librarian.config'].get_config = original_get_config
            sys.modules['obsidian_librarian.commands.ocr'].get_config = original_get_config
    
    return MockPatch(), MockConfigPatch()


def run_ocr_test():
    """Run a test of the OCR functionality with mocked functions."""
    # Get mock patches
    mock_process_patch, mock_config_patch = setup_mock_environment()
    
    try:
        # Apply mocks
        with mock_process_patch, mock_config_patch:
            # Get test file path
            test_dir = os.path.dirname(os.path.abspath(__file__))
            test_file = os.path.join(test_dir, "test_ocr.md")
            
            # Make sure test file exists
            if not os.path.exists(test_file):
                print(f"Test file not found: {test_file}")
                return False
                
            # Get the base name without extension
            test_note_name = Path(test_file).stem
            
            print(f"Starting OCR test on {test_file}")
            print("-" * 50)
            
            # Read original content
            with open(test_file, 'r') as f:
                original_content = f.read()
                
            print("Original content:")
            print(original_content)
            print("-" * 50)
            
            # Create a backup of the test file
            backup_file = test_file + ".bak"
            with open(backup_file, 'w') as f:
                f.write(original_content)
                
            # Run the OCR command
            from click.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(ocr_note, [test_note_name])
            
            print("\nOCR command output:")
            print(result.output)
            print("-" * 50)
            
            # Read the updated content
            with open(test_file, 'r') as f:
                updated_content = f.read()
                
            print("Updated content:")
            print(updated_content)
            print("-" * 50)
            
            # Check if the content was updated
            if original_content == updated_content:
                print("❌ Test failed: File content was not updated")
                return False
                
            # Check if the OCR result was added after the image reference
            if "![[test_math_image.png]]" in updated_content and "$$\nE = mc^2\n$$" in updated_content:
                print("✅ Test passed: OCR result was added correctly")
                return True
            else:
                print("❌ Test failed: OCR result was not added correctly")
                return False
                
    finally:
        # Restore the original file from backup
        if os.path.exists(backup_file):
            with open(backup_file, 'r') as f:
                original_content = f.read()
                
            with open(test_file, 'w') as f:
                f.write(original_content)
                
            print("Restored original file content from backup")
            
            # Delete the backup
            os.remove(backup_file)


if __name__ == "__main__":
    # Run the test
    success = run_ocr_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)