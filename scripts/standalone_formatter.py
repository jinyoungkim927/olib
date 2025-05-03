#\!/usr/bin/env python3
"""
Standalone formatter for Obsidian notes that fixes common issues
"""
import os
import re
import glob
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# History file location
HISTORY_FILE = os.path.join(os.path.expanduser('~'), '.config', 'obsidian-librarian', 'format_history.json')

def fix_formatting(content):
    """Fix formatting issues in markdown content"""
    # Make a copy of original content
    original_content = content
    
    # Fix hashtags with brackets
    content = re.sub(r'(#[a-zA-Z0-9_-]+)-(\[\[)([a-zA-Z0-9_-]+)(\]\])', r'\1-\3', content)
    content = re.sub(r'(#)(\[+)([a-zA-Z0-9_-]+)(\]+)', r'\1\3', content)
    
    # Fix triple or more brackets
    content = re.sub(r'\[{3,}([^\[\]]+?)\]{3,}', r'[[\1]]', content)
    
    # Fix nested wiki links
    nested_pattern = r'\[\[(.*?)\[\[(.*?)\]\](.*?)\]\]'
    while re.search(nested_pattern, content):
        content = re.sub(nested_pattern, r'[[\1\2\3]]', content)
    
    # Fix __SIMPLE_LINK__ placeholders
    content = re.sub(r'__SIMPLE_LINK_\d+__', r'1', content)
    
    # Return the fixed content
    return content

def format_file(file_path, dry_run=False, backup=True, verbose=False):
    """Format a single file and return True if changes were made"""
    if verbose:
        print(f"Processing {os.path.basename(file_path)}")
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply the formatter
        modified_content = fix_formatting(content)
        
        # Check if content was changed
        if content == modified_content:
            if verbose:
                print(f"No changes needed for {os.path.basename(file_path)}")
            return False, None
        
        # Create backup if needed
        backup_path = None
        if backup and not dry_run:
            backup_path = f"{file_path}.bak"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            if verbose:
                print(f"Created backup: {backup_path}")
        
        # Write the modified content or just report in dry run mode
        if dry_run:
            if verbose:
                print(f"Would modify {os.path.basename(file_path)}")
                
                # Show a simple diff
                orig_lines = content.split('\n')
                mod_lines = modified_content.split('\n')
                
                for i, (old, new) in enumerate(zip(orig_lines, mod_lines)):
                    if old != new:
                        print(f"  - {old}")
                        print(f"  + {new}")
                        if i > 5:  # Just show a few examples
                            print("  ...")
                            break
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            if verbose:
                print(f"Updated {os.path.basename(file_path)}")
        
        return True, backup_path
    
    except Exception as e:
        print(f"Error processing {os.path.basename(file_path)}: {e}")
        return False, None

def process_directory(directory_path, dry_run=False, backup=True, verbose=False):
    """Process all markdown files in a directory (recursively)"""
    md_files = glob.glob(os.path.join(directory_path, "**/*.md"), recursive=True)
    
    print(f"Found {len(md_files)} markdown files in {directory_path}")
    
    modified_files = []
    modified_count = 0
    
    for file_path in md_files:
        was_modified, backup_path = format_file(file_path, dry_run, backup, verbose)
        
        if was_modified:
            modified_count += 1
            if not dry_run:
                modified_files.append({
                    'path': file_path,
                    'backup': backup_path,
                    'timestamp': datetime.now().isoformat()
                })
    
    print(f"Processed {len(md_files)} files. {modified_count} files {'would be' if dry_run else 'were'} modified.")
    
    # Save history if changes were made and not in dry run mode
    if modified_files and not dry_run:
        save_history(modified_files)
    
    return modified_count

def save_history(modified_files):
    """Save modification history to a file"""
    if not modified_files:
        return
    
    # Create the history directory if it doesn't exist
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    
    # Read existing history
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read history file: {e}")
    
    # Add new entry
    history.append({
        'command': 'format fix',
        'timestamp': datetime.now().isoformat(),
        'modified_files': modified_files
    })
    
    # Save the updated history
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save history file: {e}")

def undo_latest():
    """Undo the most recent operation"""
    if not os.path.exists(HISTORY_FILE):
        print("No operation history found.")
        return
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
        
        if not history:
            print("No operation history found.")
            return
        
        # Get the most recent entry
        entry = history[-1]
        cmd = entry.get('command', 'unknown')
        timestamp = entry.get('timestamp', 'unknown')
        modified_files = entry.get('modified_files', [])
        
        print(f"Reverting operation: {cmd} ({timestamp})")
        print(f"This will restore {len(modified_files)} files to their previous state.")
        
        confirm = input("Continue? (y/n): ").lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return
        
        # Perform the undo
        restored_count = 0
        for file_info in modified_files:
            file_path = file_info.get('path')
            backup_path = file_info.get('backup')
            
            if not backup_path or not os.path.exists(backup_path):
                print(f"Skip: No backup found for {os.path.basename(file_path)}")
                continue
                
            if not os.path.exists(file_path):
                print(f"Skip: File no longer exists: {os.path.basename(file_path)}")
                continue
            
            try:
                shutil.copy2(backup_path, file_path)
                restored_count += 1
                print(f"Restored: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Error restoring {os.path.basename(file_path)}: {e}")
        
        # Update history
        history.pop()
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"Reverted {restored_count} files. History updated.")
        
    except Exception as e:
        print(f"Error reverting operation: {e}")

def list_history():
    """List operation history"""
    if not os.path.exists(HISTORY_FILE):
        print("No operation history found.")
        return
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
        
        if not history:
            print("No operation history found.")
            return
        
        print("Operation history (most recent first):")
        print("-" * 80)
        
        for i, entry in enumerate(reversed(history)):
            cmd = entry.get('command', 'unknown')
            timestamp = entry.get('timestamp', 'unknown')
            files_count = len(entry.get('modified_files', []))
            
            print(f"{i}: {cmd} ({timestamp}) - {files_count} files modified")
        
        print("-" * 80)
        print("Use 'python standalone_formatter.py --undo' to revert the most recent operation")
        
    except Exception as e:
        print(f"Error reading history: {e}")

def main():
    parser = argparse.ArgumentParser(description="Format Obsidian markdown files")
    parser.add_argument("path", nargs='?', help="Path to file or directory")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show changes without applying them")
    parser.add_argument("--no-backup", "-n", action="store_true", help="Skip creating backup files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--undo", "-u", action="store_true", help="Undo the most recent operation")
    parser.add_argument("--list", "-l", action="store_true", help="List operation history")
    
    args = parser.parse_args()
    
    if args.undo:
        undo_latest()
        return
    
    if args.list:
        list_history()
        return
    
    if not args.path:
        print("Error: Please provide a path to a file or directory.")
        return
    
    path = os.path.abspath(args.path)
    if os.path.isfile(path):
        print(f"Formatting file: {path}")
        was_modified, _ = format_file(path, args.dry_run, not args.no_backup, args.verbose)
        if not was_modified:
            print("No changes needed.")
    elif os.path.isdir(path):
        print(f"Formatting directory: {path}")
        process_directory(path, args.dry_run, not args.no_backup, args.verbose)
    else:
        print(f"Error: Path {path} not found")

if __name__ == "__main__":
    main()
