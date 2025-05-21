#!/usr/bin/env python3
"""
Migration script for transitioning to the simplified formatter.

This script helps migrate from the old formatting system to the new one.
It updates import statements and makes necessary adjustments to any code
that might be using the old formatter directly.
"""

import os
import re
import glob
import argparse
from pathlib import Path

OLD_IMPORTS = [
    "from obsidian_librarian.commands.utilities.simplified_format_fixer import FormatFixer",
    "from obsidian_librarian.utils.post_process_formatting import",
    "from obsidian_librarian.utils.formatting import",
    "from ..utils.post_process_formatting import",
    "from ..utils.formatting import",
]

NEW_IMPORTS = {
    "from obsidian_librarian.commands.utilities.simplified_format_fixer import FormatFixer": 
        "from obsidian_librarian.commands.utilities.simplified_format_fixer import FormatFixer",
    "from obsidian_librarian.utils.simplified_post_process import clean_llm_output": 
        "from obsidian_librarian.utils.simplified_post_process import clean_llm_output",
    "from obsidian_librarian.utils.simplified_post_process import process_ocr_output": 
        "from obsidian_librarian.utils.simplified_post_process import process_ocr_output",
    "from ..utils.simplified_post_process import clean_llm_output": 
        "from ..utils.simplified_post_process import clean_llm_output",
    "from ..utils.simplified_post_process import process_ocr_output": 
        "from ..utils.simplified_post_process import process_ocr_output",
}

FUNCTION_RENAMES = {
    "clean_raw_llm_output": "clean_llm_output",
    "post_process_ocr_output": "process_ocr_output",
}


def update_imports(file_path, dry_run=False):
    """Update import statements in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        # Look for old imports and replace them
        for old_import in OLD_IMPORTS:
            if old_import in content:
                for old, new in NEW_IMPORTS.items():
                    if old in content:
                        content = content.replace(old, new)
                        modified = True
        
        # Update function calls
        for old_name, new_name in FUNCTION_RENAMES.items():
            if re.search(r'\b' + old_name + r'\(', content):
                content = re.sub(r'\b' + old_name + r'\(', new_name + '(', content)
                modified = True
        
        if modified:
            print(f"Updating imports in {file_path}")
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Migrate to simplified formatter")
    parser.add_argument("--path", default=".", help="Path to the project root")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying them")
    args = parser.parse_args()
    
    project_root = os.path.abspath(args.path)
    print(f"Searching for Python files in {project_root}")
    
    # Find all Python files in the project
    py_files = glob.glob(os.path.join(project_root, "**/*.py"), recursive=True)
    
    updated_count = 0
    for py_file in py_files:
        if update_imports(py_file, args.dry_run):
            updated_count += 1
    
    print(f"Updated {updated_count} files")
    
    if args.dry_run:
        print("\nThis was a dry run. No files were modified.")
        print("Run without --dry-run to apply the changes.")


if __name__ == "__main__":
    main()