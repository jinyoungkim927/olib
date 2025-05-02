import click
import os
import re
from pathlib import Path
from ..config import get_config
from ..utils.post_process_formatting import format_latex, convert_latex_delimiters
import pyperclip
from .utilities.format_fixer import FormatFixer

# Should be a group command with subcommands for formatting and screenshot conversion
@click.group()
def format_notes():
    """Format notes and convert screenshots to text
    
    Automatically format your notes according to configured style guidelines
    and convert screenshots to searchable text.
    """
    pass

@format_notes.command()
def format():
    click.echo("Formatting...")

@format_notes.command()
def screenshot():
    click.echo("Screenshot...")

@format_notes.command()
@click.argument('note_name', type=click.STRING, required=False)
@click.option('--dry-run', '-d', is_flag=True, help='Show changes without writing to file')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
def fix(note_name=None, dry_run=False, verbose=False):
    """Fix common formatting issues in notes using FormatFixer."""
    config = get_config()
    vault_path = config.get('vault_path')

    if not vault_path:
        click.echo("Error: Vault path not configured. Run 'olib config setup' first.")
        return

    # Instantiate the fixer, passing relevant options
    # We assume backup=True by default unless a --no-backup option is added
    fixer = FormatFixer(dry_run=dry_run, backup=True, verbose=verbose)

    if note_name:
        # Find the specific note
        note_path = None
        # Use a robust way to find the note, e.g., searching the vault
        for root, _, files in os.walk(vault_path):
            if note_name in files and note_name.endswith(".md"):
                 note_path = os.path.join(root, note_name)
                 break
            # Handle cases where note_name might not include .md
            elif f"{note_name}.md" in files:
                 note_path = os.path.join(root, f"{note_name}.md")
                 break

        if note_path and os.path.isfile(note_path):
             click.echo(f"Formatting specific note: {note_path}")
             # Use the fixer's format_file method directly
             fixer.format_file(note_path)
             # Save history if changes were made (format_file doesn't save history itself)
             if fixer.modified_files and not dry_run:
                 fixer.save_history()
        else:
             click.echo(f"Error: Note '{note_name}' not found in vault.")
    else:
        # Process the entire vault
        click.echo(f"Formatting entire vault: {vault_path}")
        # Use the fixer's format_directory or format_vault method
        fixer.format_directory(vault_path) # This method handles finding files and saving history
