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
from obsidian_librarian.utils.formatting import apply_standard_formatting # <-- Import the shared formatter
from .. import vault_state # Assuming vault_state might be used for backup/undo

logger = logging.getLogger(__name__)

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

@click.command()
@click.option('--path', '-p', default=None,
              help='Specific note path (relative to vault) or directory path to format. If omitted, formats the entire vault.')
@click.option('--dry-run', '-d', is_flag=True, help="Show which files would be formatted without making changes.")
# Add other options as needed (e.g., --backup)
def format(path, dry_run):
    """Applies standard formatting rules to markdown notes."""
    start_time = time.time()
    vault_path = get_vault_path_from_config()
    if not vault_path:
        click.secho("Vault path not configured. Please run 'olib config setup'.", fg="red")
        return
    vault_path_obj = Path(vault_path)

    files_to_process = []
    target_desc = "entire vault"

    if path:
        target_path = (vault_path_obj / path).resolve()
        target_desc = f"path '{path}'"
        if target_path.is_dir():
            files_to_process = [p for p in target_path.rglob('*.md') if p.is_file()]
        elif target_path.is_file() and target_path.suffix.lower() == '.md':
            # Check if it's within the vault path for safety
            if vault_path_obj in target_path.parents:
                 files_to_process = [target_path]
            else:
                 click.secho(f"Error: Specified file '{path}' is outside the configured vault.", fg="red")
                 return
        else:
            # Try finding as a note identifier if not a direct path
            found_note = find_note_in_vault(vault_path, path)
            if found_note:
                files_to_process = [found_note]
                target_desc = f"note '{path}'"
            else:
                click.secho(f"Error: Path '{path}' is not a valid directory, markdown file, or known note identifier within the vault.", fg="red")
                return
    else:
        # Format entire vault
        files_to_process = [p for p in vault_path_obj.rglob('*.md') if p.is_file()]

    if not files_to_process:
        click.echo(f"No markdown files found to format in {target_desc}.")
        return

    click.echo(f"Scanning {len(files_to_process)} markdown files in {target_desc} for formatting...")

    formatted_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in files_to_process:
        relative_path = file_path.relative_to(vault_path_obj)
        logger.debug(f"Processing: {relative_path}")
        try:
            original_content = read_note_content(file_path)
            if original_content is None:
                logger.warning(f"Could not read content from {relative_path}. Skipping.")
                skipped_count += 1
                continue

            # --- Use the shared formatting function ---
            formatted_content = apply_standard_formatting(original_content)
            # --- End usage ---

            if formatted_content == original_content:
                logger.debug(f"No formatting changes needed for {relative_path}.")
                continue # No changes needed

            formatted_count += 1
            click.echo(f"Formatting changes identified for: {relative_path}")

            if not dry_run:
                # --- Add backup logic here if desired ---
                # vault_state.add_change(file_path, original_content) # Example undo integration
                # --- End backup logic ---
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(formatted_content)
                    logger.info(f"Formatted {relative_path}")
                except Exception as write_err:
                    click.secho(f"Error writing changes to {relative_path}: {write_err}", fg="red")
                    logger.error(f"Failed to write formatted file {relative_path}: {write_err}", exc_info=True)
                    error_count += 1
                    # --- Add undo rollback logic here if backup was made ---
                    # vault_state.revert_last_change() # Example
                    # --- End rollback ---
            else:
                 # Dry run: just report
                 logger.info(f"[Dry Run] Would format {relative_path}")


        except Exception as e:
            click.secho(f"Error processing file {relative_path}: {e}", fg="red")
            logger.error(f"Failed to process {relative_path}: {e}", exc_info=True)
            error_count += 1

    end_time = time.time()
    duration = end_time - start_time

    click.echo("\n--- Formatting Summary ---")
    if dry_run:
        click.echo(f"[Dry Run] Would format {formatted_count} files.")
    else:
        click.echo(f"Formatted {formatted_count} files.")
    if skipped_count > 0: click.echo(f"Skipped {skipped_count} files (read errors).")
    if error_count > 0: click.echo(click.style(f"Encountered errors on {error_count} files.", fg="red"))
    click.echo(f"Operation completed in {duration:.2f} seconds.")
