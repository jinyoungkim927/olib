#\!/usr/bin/env python3
"""
Debug script to test the CLI command's file processing.
"""
import os
import sys
from pathlib import Path
from obsidian_librarian.config import get_config
from obsidian_librarian.commands.format import process_note_formatting, fix_math_formatting

def main():
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        print("Error: Vault path not configured. Please run 'olib config setup' first.")
        sys.exit(1)
    
    print(f"Vault path: {vault_path}")
    
    # Create a test file with known issues in the vault
    test_file_name = "TEST_FORMAT_FILE_WITH_ISSUES.md"
    test_file_path = os.path.join(vault_path, test_file_name)
    
    # Sample content with clear formatting issues
    test_content = """# Test Format File
#test #with-[[brackets]]

This is a test file with [[[triple brackets]]] and [[nested [[wiki]] links]].

Math expression: $\hat{\beta} = \arg\min_{\[[Beta]]} (y - X\beta)^2 + \lambda \|\beta\|_2^2$

Also check [[[[quadruple brackets]]]] and __SIMPLE_LINK_42__ placeholders.
"""
    
    print(f"\nCreating test file: {test_file_path}")
    with open(test_file_path, 'w') as f:
        f.write(test_content)
    
    # First, test our direct formatter function
    print("\n--- Testing direct formatter function ---")
    fixed_content = fix_math_formatting(test_content)
    print("Original content:")
    print("-" * 50)
    print(test_content)
    print("-" * 50)
    print("\nFixed content:")
    print("-" * 50)
    print(fixed_content)
    print("-" * 50)
    
    if test_content == fixed_content:
        print("❌ Direct formatter didn't make any changes\!")
    else:
        print("✅ Direct formatter made changes successfully\!")
    
    # Now test the CLI process_note_formatting function
    print("\n--- Testing CLI process_note_formatting function ---")
    was_modified = process_note_formatting(test_file_path, fix_math=True, fix_links=True, dry_run=True, quiet=False)
    
    if was_modified:
        print("✅ CLI formatter detected changes\!")
    else:
        print("❌ CLI formatter didn't detect any changes\!")
    
    # Try the actual format operation
    print("\n--- Testing actual note formatting ---")
    was_modified = process_note_formatting(test_file_path, fix_math=True, fix_links=True, dry_run=False, quiet=False)
    
    if was_modified:
        print("✅ CLI formatter applied changes\!")
        
        # Verify by reading the file
        with open(test_file_path, 'r') as f:
            updated_content = f.read()
        
        if updated_content \!= test_content:
            print("✅ File content was actually modified\!")
        else:
            print("❌ File wasn't actually changed despite process_note_formatting returning True\!")
    else:
        print("❌ CLI formatter didn't apply any changes\!")
    
    # Clean up
    print("\nCleaning up test file...")
    try:
        os.remove(test_file_path)
        print(f"✅ Removed test file: {test_file_path}")
    except Exception as e:
        print(f"❌ Failed to remove test file: {e}")
    
    print("\nDebug complete\!")

if __name__ == "__main__":
    main()
