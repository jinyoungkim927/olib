#\!/usr/bin/env python3
"""
Direct formatter script that bypasses the CLI interface.
"""
import os
import glob
import argparse
from pathlib import Path

# Import the formatting functions directly
from obsidian_librarian.commands.format import fix_math_formatting

def format_file(file_path, dry_run=False):
    """Format a single file and return True if changes were made."""
    print(f"Processing {os.path.basename(file_path)}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply fix_math_formatting directly
        modified_content = fix_math_formatting(content)
        
        # Check if any changes were made
        if content == modified_content:
            print(f"No changes needed for {os.path.basename(file_path)}")
            return False
            
        # Show changes or write them
        if dry_run:
            print(f"Would modify {os.path.basename(file_path)}:")
            
            # Show a sample of changes
            content_lines = content.split('\n')
            modified_lines = modified_content.split('\n')
            print("-" * 40)
            for i in range(min(len(content_lines), len(modified_lines))):
                old = content_lines[i]
                new = modified_lines[i]
                if old \!= new:
                    print(f"- {old}")
                    print(f"+ {new}")
                    # Only show a few examples
                    if i > 5:
                        print("...")
                        break
            print("-" * 40)
        else:
            # Write changes
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"Updated {os.path.basename(file_path)}")
        
        return True
    except Exception as e:
        print(f"Error processing {os.path.basename(file_path)}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Format Obsidian markdown files")
    parser.add_argument("path", help="Path to a file or directory to format")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview changes without applying them")
    args = parser.parse_args()
    
    path = os.path.abspath(args.path)
    
    if os.path.isfile(path):
        # Process a single file
        format_file(path, args.dry_run)
    elif os.path.isdir(path):
        # Process all .md files in directory
        md_files = glob.glob(os.path.join(path, "**/*.md"), recursive=True)
        print(f"Found {len(md_files)} markdown files")
        
        modified_count = 0
        for file_path in md_files:
            was_modified = format_file(file_path, args.dry_run)
            if was_modified and not args.dry_run:
                modified_count += 1
        
        print(f"Processed {len(md_files)} files. {modified_count} files were modified.")
    else:
        print(f"Error: Path {path} not found")

if __name__ == "__main__":
    main()
