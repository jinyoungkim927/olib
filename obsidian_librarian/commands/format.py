"""
Format command for Obsidian notes.

This module provides CLI commands for formatting notes with a focus on
consistent styling and proper LaTeX math formatting.
"""

import click
import os
import re
from pathlib import Path
from ..config import get_config
from ..utils.post_process_formatting import format_latex, convert_latex_delimiters
import pyperclip
from .utilities.format_fixer import FormatFixer
import logging
import time

from obsidian_librarian.config import get_vault_path_from_config
from obsidian_librarian.utils.file_operations import find_note_in_vault, read_note_content, get_markdown_files
from .. import vault_state

logger = logging.getLogger(__name__)

@click.group()
def format_notes():
    """Format notes and convert screenshots to text
    
    Automatically format your notes according to configured style guidelines
    and convert screenshots to searchable text.
    """
    pass

@format_notes.command()
@click.argument('note_name', type=click.STRING, required=False)
@click.option('--dry-run', '-d', is_flag=True, help='Show changes without writing to file')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.option('--no-backup', is_flag=True, default=False, help='Do not create .bak files.')
def fix(note_name=None, dry_run=False, verbose=False, no_backup=False):
    """Fix common formatting issues in notes using FormatFixer."""
    config = get_config()
    vault_path = config.get('vault_path')

    if not vault_path:
        click.echo("Error: Vault path not configured. Run 'olib config setup' first.")
        return

    # Instantiate the fixer, passing relevant options
    fixer = FormatFixer(dry_run=dry_run, backup=not no_backup, verbose=verbose)

    if note_name:
        # Find the specific note
        note_path_obj = find_note_in_vault(vault_path, note_name) 

        if note_path_obj and note_path_obj.is_file():
             click.echo(f"Formatting specific note: {note_path_obj.relative_to(vault_path)}")
             # Use the fixer's format_file method directly
             was_modified = fixer.format_file(str(note_path_obj)) 
             # Save history if changes were made
             if was_modified and not dry_run:
                 fixer.save_history() 
        else:
             click.echo(f"Error: Note '{note_name}' not found in vault.")
    else:
        # Process the entire vault
        click.echo(f"Formatting entire vault: {vault_path}")
        # Use the fixer's format_directory method
        fixer.format_directory(vault_path)