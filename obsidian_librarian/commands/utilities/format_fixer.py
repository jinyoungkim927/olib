#\!/usr/bin/env python3
import os
import sys
import glob
import json
from datetime import datetime
from pathlib import Path
import re
import shutil
from typing import Optional

# from ..format import fix_math_formatting
from obsidian_librarian.config import get_config
# Import formatting functions that were in utils
# from ...utils.formatting import format_math_blocks, format_code_blocks # We'll integrate these

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
            
            # Extract filename without extension for title check
            filename_base = Path(file_path).stem

            # Apply formatter, passing filename
            modified_content = self.apply_all_fixes(content, filename_base)
            
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

    def apply_all_fixes(self, text: str, filename_base: Optional[str] = None) -> str:
        """
        Applies a sequence of formatting fixes to the input text.

        Args:
            text: The raw text content of a note.
            filename_base: The base name of the file (without extension), used for title check.

        Returns:
            The text content after applying all registered fixes.
        """
        original_text = text

        # --- Preserve code blocks ---
        code_blocks = {}
        placeholder_template = "___CODE_BLOCK_PLACEHOLDER_{}___"
        for i, match in enumerate(re.finditer(r'```.*?```', text, re.DOTALL)):
            placeholder = placeholder_template.format(i)
            code_blocks[placeholder] = match.group(0)
            text = text.replace(match.group(0), placeholder, 1)

        # --- Apply fixes in a specific order ---

        # 0. Remove duplicate H1 title if it matches filename
        if filename_base:
            text = self._remove_duplicate_title(text, filename_base)

        # 1. Fix escaped LaTeX delimiters ( \$...\$ -> $...$ )
        text = self._fix_escaped_latex_delimiters(text)

        # 2. Convert LaTeX delimiters (\( -> $, \[ -> $$)
        text = self._convert_latex_delimiters(text)

        # 3. Fix content within math blocks (e.g., \_ -> _, [[Link]] -> Link)
        text = self._fix_math_content(text)

        # 4. Fix spacing around inline math ($ ... $ -> $...$, word$ -> word $, $word -> $ word)
        text = self._fix_inline_math_spacing(text)

        # 5. Fix bullet point indentation (spaces -> tabs)
        text = self._fix_bullet_indentation(text)

        # 6. Fix hashtag brackets (#[[tag]] -> #tag, #[tag]-[[subtag]] -> #tag-subtag)
        text = self._fix_hashtag_brackets(text)

        # 7. Fix malformed wiki links (nested, multiple brackets)
        text = self._fix_wiki_links(text)

        # 8. Remove __SIMPLE_LINK__ placeholders
        text = self._remove_simple_link_placeholders(text)

        # 9. Ensure block math ($$) are on their own lines
        text = self._format_math_blocks(text)

        # --- Restore code blocks ---
        # Must happen before formatting code blocks to avoid adding newlines inside them
        for placeholder, original in code_blocks.items():
            text = text.replace(placeholder, original, 1)

        # 10. Ensure code blocks (```) are on their own lines
        # Apply this *after* restoring placeholders
        text = self._format_code_blocks(text)

        # --- End of fixes ---

        if self.verbose and text != original_text:
             print("  Applied formatting fixes.") # General message

        # Final cleanup of potentially excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        return text

    def _remove_duplicate_title(self, text: str, filename_base: str) -> str:
        """Removes the first H1 header if it matches the filename."""
        # Simple case: H1 is the very first line
        pattern = re.compile(r"^\s*#\s+" + re.escape(filename_base) + r"\s*\n")
        if pattern.match(text):
            # Find the end of the first line
            first_line_end = text.find('\n')
            if first_line_end != -1:
                # Check if the next line is blank, remove it too if so
                if text[first_line_end+1:].startswith('\n'):
                    return text[first_line_end+2:] # Skip title and blank line
                else:
                    return text[first_line_end+1:] # Skip just title line
            else:
                return "" # File only contained the title
        return text

    def _fix_escaped_latex_delimiters(self, text: str) -> str:
        """Corrects improperly escaped LaTeX delimiters like \$...\$ to $...$."""
        # Pattern: Finds \$ followed by non-$ characters (non-greedy) followed by \$
        # Replacement: Replaces with $ followed by the captured content followed by $
        corrected_text = re.sub(r'\\\$([^$]+?)\\\$', r'$\1$', text)
        return corrected_text

    def _convert_latex_delimiters(self, text: str) -> str:
        """Converts LaTeX style delimiters to Markdown style.
        \(...\) to $...$
        \[...\] to $$...$$
        Ensures correct pairing and handles content spanning multiple lines.
        """
        # Convert display math \[ ... \] to $$ ... $$
        # Non-greedy match .*? for content, re.DOTALL for multiline content
        text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
        
        # Convert inline math \( ... \) to $ ... $
        # Non-greedy match .*? for content, re.DOTALL for multiline content (though less common for inline)
        text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
        
        return text

    def _fix_math_content(self, text: str) -> str:
        """Cleans up common issues within $...$ and $$...$$ math blocks."""
        # Correct \operatorname {abc} to \operatorname{abc}
        text = re.sub(r'(\\operatorname)\s+({.*?})', r'\1\2', text)
        
        # Correct common cases of \command {arg} to \command{arg}
        # This targets a command (letters) followed by space(s) and then an opening brace/paren/bracket
        text = re.sub(r'(\\[a-zA-Z]+)\s+({)', r'\1\2', text)  # e.g., \textbf {word} -> \textbf{word}
        text = re.sub(r'(\\[a-zA-Z]+)\s+(\()', r'\1\2', text) # e.g., \sqrt (x) -> \sqrt(x) (though \sqrt{x} is more common)
        text = re.sub(r'(\\[a-zA-Z]+)\s+(\[)', r'\1\2', text) # e.g., \mathbb [R] -> \mathbb[R] (though \mathbb{R} is more common)

        # If LLM produces `\ {`, it's often meant to be `\{`.
        text = re.sub(r'\\ ({)', r'\\{\1', text) # \ { -> \{
        # Similarly for other brackets if this pattern is observed:
        text = re.sub(r'\\ (\[)', r'\\[\1', text) # \ [ -> \[
        text = re.sub(r'\\ (\()', r'\\(\1', text) # \ ( -> \(

        # Fix escaped underscores in LaTeX (e.g., A\_1 -> A_1)
        # This pattern looks for escaped underscores inside math blocks
        text = re.sub(r'(\$[^\$]*?)\\_(.*?\$)', r'\1_\2', text)  # for inline math
        text = re.sub(r'(\$\$[^\$]*?)\\_(.*?\$\$)', r'\1_\2', text, flags=re.DOTALL)  # for block math
        
        # Handle multiple underscores in the same math block
        while re.search(r'(\$[^\$]*?)\\_(.*?\$)', text) or re.search(r'(\$\$[^\$]*?)\\_(.*?\$\$)', text, flags=re.DOTALL):
            text = re.sub(r'(\$[^\$]*?)\\_(.*?\$)', r'\1_\2', text)  # for inline math
            text = re.sub(r'(\$\$[^\$]*?)\\_(.*?\$\$)', r'\1_\2', text, flags=re.DOTALL)  # for block math

        # Fix \text{} formatting - remove space after command
        text = re.sub(r'(\\text)\s+({)', r'\1\2', text)

        # Correct common mis-escaped delimiters if not caught by earlier specific delimiter fixes
        # e.g. \$ text \$ -> $ text $ (if \$ wasn't meant to be literal)
        # This is risky if user actually wants literal \$ inside math.
        # The _fix_escaped_latex_delimiters should handle most of these at a higher level.
        # text = re.sub(r'\\\$([^$]*?)\\\$', r'$\1$', text) # Already handled better elsewhere

        return text

    def _fix_inline_math_spacing(self, text: str) -> str:
        """Fixes spacing issues around inline $...$ math."""
        # Remove spaces immediately inside $...$
        # Handles one or more spaces: $  content  $ -> $content$
        text = re.sub(r'\$\s*(.*?)\s*\$', r'$\1$', text)

        return text

    def _fix_bullet_indentation(self, text: str) -> str:
        """Converts space-indented second-level bullets to tab-indented."""
        # Pattern: Start of line (^), exactly two spaces (  ), literal '* '
        # Replacement: Start of line, a tab (\t), literal '* '
        # re.MULTILINE makes ^ match the start of each line, not just the string
        corrected_text = re.sub(r'^(  )\* ', r'\t* ', text, flags=re.MULTILINE)
        return corrected_text

    def _fix_hashtag_brackets(self, text: str) -> str:
        """Fixes hashtags like #[[tag]], #[tag], #tag-[[subtag]]."""
        # Handle #[[tag]] or #[tag] -> #tag
        text = re.sub(r'(#)(\[+)([a-zA-Z0-9\/_-]+)(\]+)', r'\1\3', text)
        # Handle #tag-[[subtag]] -> #tag-subtag
        text = re.sub(r'(#[a-zA-Z0-9\/_-]+)-(\[\[)([a-zA-Z0-9\/_-]+)(\]\])', r'\1-\3', text)
        return text

    def _fix_wiki_links(self, text: str) -> str:
        """Fixes nested or multiple brackets in wiki links."""
        # Fix nested links like [[ Link [[Nested]] ]] -> [[ Link Nested ]]
        nested_pattern = r'\[\[(.*?)\[\[(.*?)\]\](.*?)\]\]'
        while re.search(nested_pattern, text):
            text = re.sub(nested_pattern, r'[[\1\2\3]]', text)

        # Fix multiple brackets like [[[Topic]]] -> [[Topic]]
        # Use {2,} for brackets to catch [[Topic]], {3,} for content inside
        text = re.sub(r'\[{3,}([^\[\]]+?)\]{3,}', r'[[\1]]', text)
        return text

    def _remove_simple_link_placeholders(self, text: str) -> str:
        """Removes __SIMPLE_LINK_<digits>__ placeholders, replacing with '1'."""
        return re.sub(r'__SIMPLE_LINK_\d+__', r'1', text)

    def _format_math_blocks(self, text: str) -> str:
        """Formats $$ math blocks to fit the desired style (compact formatting)."""
        # First, ensure all $$ blocks are properly placed
        
        # Pattern 1: Ensure that math blocks start at the beginning of a line
        # If a $$ is not at the start of a line, add a newline before it
        text = re.sub(r'([^\n])\$\$', r'\1\n$$', text)
        
        # Pattern 2: Ensure that math blocks end with a newline
        # If a $$ is not followed by a newline, add one
        text = re.sub(r'\$\$([^\n])', r'$$\n\1', text)

        # Pattern 3: Compact consecutive equations
        # Looking for a pattern like "something$$\nequation\n$$next line" 
        # and turning it into "something$$equation$$next line"
        text = re.sub(r'([^\n])\$\$\s*\n(.*?)\n\s*\$\$\s*\n', r'\1$$\2$$\n', text, flags=re.DOTALL)
        
        # Pattern 4: For equations that remain on their own lines,
        # remove any excess blank lines around them (ideal format doesn't have these)
        text = re.sub(r'\n\n\$\$', r'\n$$', text)  # Remove extra line before $$
        text = re.sub(r'\$\$\n\n', r'$$\n', text)   # Remove extra line after $$
        
        return text

    def _format_code_blocks(self, text: str) -> str:
        """Ensures ``` code blocks are on their own lines with blank lines around."""
        # --- Refined Regex for Code Blocks ---
        # Ensure ``` starts on a new line, preceded by exactly one blank line
        text = re.sub(r'(?<!\n)\n(?!\n)(```)', r'\n\n\1', text) # Add leading blank line if only one newline exists
        text = re.sub(r'(?<!\n)(```)', r'\n\n\1', text)      # Add leading blank line if no newline exists

        # Ensure ``` ends a line, followed by exactly one blank line
        text = re.sub(r'(```)\n(?!\n)', r'\1\n\n', text) # Add trailing blank line if only one newline exists
        text = re.sub(r'(```)(?!\n)', r'\1\n\n', text)   # Add trailing blank line if no newline exists
        # --- End Refined Regex ---
        return text

    def apply_math_fixes(self, text: str) -> str:
        """
        Applies a sequence of math-specific formatting fixes to the input text.
        Preserves code blocks during the process.
        """
        original_text = text

        # --- Preserve code blocks (Robust Strategy) ---
        code_blocks = {}
        placeholder_template = "___CODE_BLOCK_PLACEHOLDER_{}___"
        
        # Sort matches by start position to process them in order
        sorted_matches = sorted(list(re.finditer(r'```.*?```', text, re.DOTALL)), key=lambda m: m.start())

        text_with_placeholders_parts = []
        last_end = 0
        for i, match in enumerate(sorted_matches):
            placeholder = placeholder_template.format(i)
            code_blocks[placeholder] = match.group(0)
            
            text_with_placeholders_parts.append(text[last_end:match.start()])
            text_with_placeholders_parts.append(placeholder)
            last_end = match.end()
        text_with_placeholders_parts.append(text[last_end:])
        processed_text = "".join(text_with_placeholders_parts)

        # --- Apply math fixes to text with placeholders ---
        processed_text = self._fix_escaped_latex_delimiters(processed_text)
        processed_text = self._convert_latex_delimiters(processed_text)
        processed_text = self._fix_math_content(processed_text)       # Cleans up common issues within $...$ and $$...$$
        processed_text = self._fix_inline_math_spacing(processed_text) # Fixes spacing issues around inline $...$ math
        processed_text = self._format_math_blocks(processed_text)     # Ensures $$ math blocks are on their own lines

        # --- Restore code blocks ---
        final_text = processed_text
        for i in range(len(sorted_matches)): # Iterate in the order of placeholder creation
            placeholder = placeholder_template.format(i)
            if placeholder in code_blocks:
                final_text = final_text.replace(placeholder, code_blocks[placeholder], 1)

        if self.verbose and final_text != original_text:
            # This message is part of FormatFixer's own verbosity
            print("  Applied math formatting fixes.")

        return final_text

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
