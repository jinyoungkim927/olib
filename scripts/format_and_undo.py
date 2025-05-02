#\!/usr/bin/env python3
"""
Standalone formatter and undo utility for Obsidian notes.
This script provides the functionality without relying on the package structure.
"""
import os
import re
import glob
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Constants
HISTORY_FILE = os.path.join(os.path.expanduser('~'), '.config', 'obsidian-librarian', 'format_history.json')

def fix_math_formatting(content):
    """Fix formatting issues in markdown content"""
    # First, preserve front matter and hashtags at beginning of document
    lines = content.split('\n')
    front_matter_lines = []
    hashtag_lines = []
    
    # Identify and preserve hashtag lines at the start
    for i, line in enumerate(lines):
        if i == 0 and line.strip().startswith('#') and not line.strip().startswith('##'):
            hashtag_lines.append(line)
        elif hashtag_lines and line.strip().startswith('#') and not line.strip().startswith('##'):
            hashtag_lines.append(line)
        else:
            break
    
    # Remove preserved lines from content for processing
    if hashtag_lines:
        lines = lines[len(hashtag_lines):]
        content = '\n'.join(lines)
    
    # Preserve code blocks to avoid modifying code
    code_blocks = {}
    for i, match in enumerate(re.finditer(r'```.*?```', content, re.DOTALL)):
        placeholder = f"__CODE_BLOCK_{i}__"
        code_blocks[placeholder] = match.group(0)
        content = content.replace(match.group(0), placeholder)

    # Fix math expressions
    # Remove spaces between $ and content for inline math
    content = re.sub(r'\$ (.*?) \$', r'$\1$', content)
    content = re.sub(r'\$([ ]+)(.*?)([ ]+)\$', r'$\2$', content)
    
    # Fix missing spaces after/before inline math
    content = re.sub(r'(\$[^\$\n]+\$)([a-zA-Z0-9])', r'\1 \2', content)
    content = re.sub(r'([a-zA-Z0-9])(\$[^\$\n]+\$)', r'\1 \2', content)
    
    # Fix math OCR issues in __SIMPLE_LINK__ placeholders
    content = re.sub(r'__SIMPLE_LINK_\d+__', r'1', content)
    
    # Fix wiki links in math expressions
    def fix_math_links(match):
        math_content = match.group(1)
        if '[[' in math_content and ']]' in math_content:
            return '$$' + re.sub(r'\[\[([^\]]+)\]\]', r'\1', math_content) + '$$'
        return match.group(0)
    
    content = re.sub(r'\$\$(.*?)\$\$', fix_math_links, content, flags=re.DOTALL)
    
    # Fix hashtags with unnecessary brackets
    # Careful to exclude file references like \![[file.png]]
    # First, handle hashtags that look like #[tag] or #[[[tag]]]
    content = re.sub(r'(#)(\[+)([a-zA-Z0-9_-]+)(\]+)', r'\1\3', content)
    # More aggressive tag fixing for cases like "#data-science #linear-[[Algebra]]"
    content = re.sub(r'(#[a-zA-Z0-9_-]+)-(\[\[)([a-zA-Z0-9_-]+)(\]\])', r'\1-\3', content)
    
    # Handle malformed wiki-style links
    content = fix_wiki_links(content)
    
    # Fix triple or more brackets (e.g., [[[Topic]]] -> [[Topic]])
    triple_bracket_pattern = r'\[{3,}([^\[\]]+?)\]{3,}'
    content = re.sub(triple_bracket_pattern, r'[[\1]]', content)
    
    # Restore code blocks
    for placeholder, original in code_blocks.items():
        content = content.replace(placeholder, original)
    
    # Add back hashtag lines to the beginning
    if hashtag_lines:
        # Clean up hashtag lines (remove excess brackets in hashtags)
        for i, line in enumerate(hashtag_lines):
            # Fix hashtags with brackets in them - more thorough cleanup
            hashtag_lines[i] = re.sub(r'(#[a-zA-Z0-9_-]*)\[+([a-zA-Z0-9_-]+)\]+', r'\1\2', line)
            # More aggressive tag fixing for cases like "#data-science #linear-[[Algebra]]"
            hashtag_lines[i] = re.sub(r'(#[a-zA-Z0-9_-]+)-(\[\[)([a-zA-Z0-9_-]+)(\]\])', r'\1-\3', hashtag_lines[i])
        
        content = '\n'.join(hashtag_lines) + '\n\n' + content
    
    return content

def fix_wiki_links(content):
    """Fix malformed wiki-style links"""
    # Fix nested broken links by removing the inner brackets
    nested_pattern = r'\[\[(.*?)\[\[(.*?)\]\](.*?)\]\]'
    while re.search(nested_pattern, content):
        content = re.sub(nested_pattern, r'[[\1\2\3]]', content)
    
    # Fix triple brackets
    content = re.sub(r'\[{3}([^\[\]]+?)\]{3}', r'[[\1]]', content)
    
    # Fix quadruple brackets
    content = re.sub(r'\[{4}([^\[\]]+?)\]{4}', r'[[\1]]', content)
    
    return content

def format_file(file_path, dry_run=False, backup=True, verbose=False):
    """Format a single file and return True if changes were made"""
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply the formatter
        modified_content = fix_math_formatting(content)
        
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
                
                for i in range(min(len(orig_lines), len(mod_lines))):
                    if i >= len(orig_lines) or i >= len(mod_lines):
                        break
                    if orig_lines[i] \!= mod_lines[i]:
                        print(f"  - {orig_lines[i]}")
                        print(f"  + {mod_lines[i]}")
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
        return True
    except Exception as e:
        print(f"Warning: Could not save history file: {e}")
        return False

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
        if confirm \!= 'y':
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
        print("Use 'python format_and_undo.py --undo' to revert the most recent operation")
        
    except Exception as e:
        print(f"Error reading history: {e}")

def get_vault_path():
    """Get the configured Obsidian vault path"""
    # Try to read the config file
    config_file = os.path.join(os.path.expanduser('~'), '.config', 'obsidian-librarian', 'config.json')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('vault_path')
        except Exception:
            pass
    
    # If not found, ask the user
    vault_path = input("Enter the path to your Obsidian vault: ")
    
    # Validate the path
    if not os.path.exists(vault_path):
        print(f"Error: Path {vault_path} does not exist.")
        return None
        
    # Save the config
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as f:
        json.dump({"vault_path": vault_path}, f)
    
    return vault_path

def main():
    parser = argparse.ArgumentParser(description="Format Obsidian markdown files")
    parser.add_argument("path", nargs='?', help="Path to file or directory (default: vault)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show changes without applying them")
    parser.add_argument("--no-backup", "-n", action="store_true", help="Skip creating backup files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--undo", "-u", action="store_true", help="Undo the most recent operation")
    parser.add_argument("--list", "-l", action="store_true", help="List operation history")
    parser.add_argument("--all", "-a", action="store_true", help="Process all notes in the vault")
    
    args = parser.parse_args()
    
    if args.undo:
        undo_latest()
        return
    
    if args.list:
        list_history()
        return
    
    if args.all:
        vault_path = get_vault_path()
        if not vault_path:
            return
        print(f"Processing all notes in vault: {vault_path}")
        process_directory(vault_path, args.dry_run, not args.no_backup, args.verbose)
        return
    
    if args.path:
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
    else:
        print("Error: Please provide a path to a file or directory, or use --all to process the vault")
        print("Usage: python format_and_undo.py [path] [options]")
        print("       python format_and_undo.py --all")
        print("       python format_and_undo.py --undo")
        print("       python format_and_undo.py --list")

if __name__ == "__main__":
    main()
