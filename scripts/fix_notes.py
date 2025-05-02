#\!/usr/bin/env python3
"""
Standalone script to directly fix notes using the formatter.
This bypasses the CLI command which may have issues.
"""

import os
import sys
import glob
from pathlib import Path
from obsidian_librarian.commands.format import fix_math_formatting
from obsidian_librarian.config import get_config

def fix_note(note_path, dry_run=False):
    """Fix formatting issues in a single note."""
    try:
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply the fixes
        fixed_content = fix_math_formatting(content)
        
        # Check if any changes were made
        if content == fixed_content:
            print(f"No changes needed for {os.path.basename(note_path)}")
            return False
        
        if dry_run:
            print(f"Would fix {os.path.basename(note_path)}")
            # Print a small sample of the changes
            content_lines = content.split('\n')
            fixed_lines = fixed_content.split('\n')
            for i, (old, new) in enumerate(zip(content_lines, fixed_lines)):
                if old != new:
                    print(f"  - Before: {old}")
                    print(f"  + After:  {new}")
                    if i >= 3:  # Show just a few examples
                        print("  ... (more changes)")
                        break
        else:
            # Write the changes
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"Fixed {os.path.basename(note_path)}")
        
        return True
    
    except Exception as e:
        print(f"Error processing {os.path.basename(note_path)}: {e}")
        return False

def fix_all_notes(vault_path, dry_run=False):
    """Fix formatting issues in all .md files in the vault."""
    md_files = glob.glob(os.path.join(vault_path, "**/*.md"), recursive=True)
    
    print(f"Found {len(md_files)} markdown files in {vault_path}")
    
    if not md_files:
        print("No .md files found in the vault.")
        return
    
    fixed_count = 0
    for file_path in md_files:
        print(f"Processing {os.path.basename(file_path)}...", end="")
        sys.stdout.flush()
        
        was_fixed = fix_note(file_path, dry_run=dry_run)
        
        if was_fixed:
            fixed_count += 1
    
    print(f"\nProcessed {len(md_files)} notes. {fixed_count} notes were {'would be' if dry_run else ''} fixed.")

def main():
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        print("Error: Vault path not configured. Please run 'olib config setup' first.")
        sys.exit(1)
    
    import argparse
    parser = argparse.ArgumentParser(description="Fix formatting issues in Obsidian notes")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show changes without applying them")
    parser.add_argument("--note", "-n", help="Fix a specific note (provide the name without .md extension)")
    
    args = parser.parse_args()
    
    if args.note:
        note_path = os.path.join(vault_path, f"{args.note}.md")
        if not os.path.exists(note_path):
            print(f"Error: Note '{args.note}' not found in {vault_path}")
            sys.exit(1)
        
        print(f"Processing note: {args.note}")
        fix_note(note_path, dry_run=args.dry_run)
    else:
        print(f"Processing all notes in {vault_path}")
        if args.dry_run:
            print("Running in dry-run mode (no changes will be made)")
        
        if input("Continue? (y/n): ").lower() != "y":
            print("Operation cancelled")
            sys.exit(0)
        
        fix_all_notes(vault_path, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
