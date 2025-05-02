#\!/usr/bin/env python3
import os
import sys
import glob
import json
from datetime import datetime
from pathlib import Path
import re

# from ..format import fix_math_formatting
from ...config import get_config

class FormatFixer:
    """A reliable utility to format markdown files in Obsidian vaults"""
    
    def __init__(self, dry_run=False, backup=True, verbose=False):
        self.dry_run = dry_run
        self.backup = backup
        self.verbose = verbose
        self.modified_files = []
        self.history_file = os.path.join(os.path.expanduser('~'), '.config', 
                                        'obsidian-librarian', 'format_history.json')
        
        # Create history directory if it doesn't exist
        history_dir = os.path.dirname(self.history_file)
        os.makedirs(history_dir, exist_ok=True)
    
    def format_file(self, file_path):
        """Format a single file and return True if changes were made"""
        if self.verbose:
            print(f"Processing {os.path.basename(file_path)}")
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply formatter
            modified_content = self.apply_all_fixes(content)
            
            # Check if changes were made
            is_changed = content != modified_content
            
            if not is_changed:
                if self.verbose:
                    print(f"  No changes needed for {os.path.basename(file_path)}")
                return False
            
            # Create backup if needed
            if self.backup and not self.dry_run:
                backup_path = f"{file_path}.bak"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                if self.verbose:
                    print(f"  Created backup: {backup_path}")
            
            # Apply changes or show diff
            if self.dry_run:
                if self.verbose:
                    print(f"  Would update {os.path.basename(file_path)}")
                    # Show some sample changes
                    for i, (old, new) in enumerate(zip(content.split('\n'), 
                                                       modified_content.split('\n'))):
                        if old != new:
                            print(f"  - {old}")
                            print(f"  + {new}")
                            if i > 3:  # Show just a few examples
                                print("  ...")
                                break
            else:
                # Write changes
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                if self.verbose:
                    print(f"  Updated {os.path.basename(file_path)}")
                    
                # Record in history
                self.modified_files.append({
                    'path': file_path,
                    'backup': f"{file_path}.bak" if self.backup else None,
                    'timestamp': datetime.now().isoformat()
                })
            
            return True
        
        except Exception as e:
            print(f"Error processing {os.path.basename(file_path)}: {e}")
            return False
    
    def format_directory(self, directory_path):
        """Format all markdown files in a directory (recursively)"""
        md_files = glob.glob(os.path.join(directory_path, "**/*.md"), 
                               recursive=True)
        
        print(f"Found {len(md_files)} markdown files in {directory_path}")
        
        modified_count = 0
        for file_path in md_files:
            was_modified = self.format_file(file_path)
            if was_modified and not self.dry_run:
                modified_count += 1
        
        print(f"Processed {len(md_files)} files. {modified_count} files were modified.")
        
        # Save history if changes were made and not in dry-run mode
        if modified_count > 0 and not self.dry_run:
            self.save_history()
        
        return modified_count
    
    def format_vault(self):
        """Format all markdown files in the configured Obsidian vault"""
        config = get_config()
        vault_path = config.get('vault_path')
        
        if not vault_path:
            print("Error: Vault path not configured. Please run 'olib config setup' first.")
            return 0
            
        print(f"Formatting files in vault: {vault_path}")
        return self.format_directory(vault_path)
    
    def save_history(self):
        """Save modification history to a JSON file"""
        if not self.modified_files:
            return
            
        # Read existing history if it exists
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                print(f"Warning: Could not read history file: {e}")
        
        # Add new entry with timestamp
        history.append({
            'command': 'format fix',
            'timestamp': datetime.now().isoformat(),
            'modified_files': self.modified_files
        })
        
        # Save history
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
            if self.verbose:
                print(f"Saved history to {self.history_file}")
        except Exception as e:
            print(f"Warning: Could not save history file: {e}")

    def apply_all_fixes(self, text: str) -> str:
        """
        Applies a sequence of formatting fixes to the input text.

        Args:
            text: The raw text content of a note.

        Returns:
            The text content after applying all registered fixes.
        """
        original_text = text

        # --- Apply fixes in a specific order ---

        # 1. Fix escaped LaTeX delimiters ( \$...\$ -> $...$ )
        text = self._fix_escaped_latex_delimiters(text)

        # 2. Fix content within math blocks (e.g., \_ -> _)
        text = self._fix_math_content(text)

        # 3. Fix bullet point indentation (spaces -> tabs)
        text = self._fix_bullet_indentation(text)

        # 4. Add other fixes here if needed
        # ... etc ...

        # --- End of fixes ---

        if self.verbose and text != original_text:
             print("  Applied formatting fixes.") # General message

        return text

    def _fix_escaped_latex_delimiters(self, text: str) -> str:
        """
        Corrects improperly escaped LaTeX delimiters like \$...\$ to $...$.

        Finds instances of a literal '\$' followed by some content and another
        literal '\$', and replaces them with '$' followed by the content and '$'.
        It avoids changing valid LaTeX commands starting with '\'.

        Args:
            text: The input string potentially containing incorrect LaTeX.

        Returns:
            The string with corrected LaTeX delimiters.
        """
        # Pattern: Finds \$ followed by non-$ characters (non-greedy) followed by \$
        # Replacement: Replaces with $ followed by the captured content followed by $
        corrected_text = re.sub(r'\\\$([^$]+?)\\\$', r'$\1$', text)
        return corrected_text

    def _fix_math_content(self, text: str) -> str:
        """
        Cleans up common issues within $...$ and $$...$$ blocks.
        Currently fixes escaped underscores: \_ -> _
        """
        def replace_content(match):
            # Group 1 captures the delimiter ($ or $$)
            # Group 2 captures the content inside
            delimiter = match.group(1)
            content = match.group(2)

            # Apply fixes to the content
            # Replace escaped underscore with literal underscore
            fixed_content = content.replace(r'\_', '_')

            # Add more content fixes here if needed in the future
            # fixed_content = fixed_content.replace(r'\*', '*') # Example

            # Reconstruct the math block
            return delimiter + fixed_content + delimiter

        # Pattern to find math blocks ($...$ or $$...$$)
        # (\${1,2}): Captures $ or $$ as group 1
        # (.*?): Non-greedily captures content as group 2
        # \1: Matches the same delimiter captured in group 1
        # re.DOTALL allows '.' to match newlines, important for $$...$$ blocks
        pattern = r'(\${1,2})(.*?)\1'
        corrected_text = re.sub(pattern, replace_content, text, flags=re.DOTALL)

        # Optional: Add verbose logging specific to this fix
        # if self.verbose and corrected_text != text:
        #     print("    - Applied math content fixes (e.g., escaped underscores).")

        return corrected_text

    def _fix_bullet_indentation(self, text: str) -> str:
        """
        Converts space-indented second-level bullets to tab-indented.
        Specifically targets lines starting with '  * '.
        """
        # Pattern: Start of line (^), exactly two spaces (  ), literal '* '
        # Replacement: Start of line, a tab (\t), literal '* '
        # re.MULTILINE makes ^ match the start of each line, not just the string
        corrected_text = re.sub(r'^(  )\* ', r'\t* ', text, flags=re.MULTILINE)

        # Optional: Add verbose logging specific to this fix
        # if self.verbose and corrected_text != text:
        #     print("    - Applied bullet indentation fix (spaces to tabs).")

        return corrected_text

    # --- Add other fix methods below if migrating from fix_math_formatting ---
    # def _fix_inline_math_spaces(self, text: str) -> str:
    #     # ... implementation ...
    #     return text
    #
    # def _convert_latex_delimiters(self, text: str) -> str:
    #     # ... implementation ...
    #     return text
    # ... etc ...

def format_command(path=None, dry_run=False, backup=True, verbose=False):
    """Command line entry point for the format fixer"""
    fixer = FormatFixer(dry_run=dry_run, backup=backup, verbose=verbose)
    
    if path:
        # Process a specific file or directory
        path = os.path.abspath(path)
        if os.path.isfile(path):
            print(f"Formatting file: {path}")
            fixer.format_file(path)
        elif os.path.isdir(path):
            print(f"Formatting directory: {path}")
            fixer.format_directory(path)
        else:
            print(f"Error: Path {path} not found")
    else:
        # Process the entire vault
        fixer.format_vault()

if __name__ == "__main__":
    # Simple CLI when called directly
    import argparse
    parser = argparse.ArgumentParser(description="Format Obsidian markdown files")
    parser.add_argument("path", nargs="?", help="Path to file or directory (default: vault)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show changes without applying them")
    parser.add_argument("--no-backup", "-n", action="store_true", help="Skip creating .bak files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    format_command(args.path, args.dry_run, not args.no_backup, args.verbose)
