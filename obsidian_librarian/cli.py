import click
import os
import sys # Import sys
import platform # Import platform
import shutil # Import shutil
import time # Import time
from .commands import (
    format,
    check,
    search,
    notes,
    history,
    undo,
    config as config_cmd
)
# Import config utility functions if needed elsewhere, but not the command itself
# from .config import get_config # Example if needed

# Import specific command functions/groups
# from .commands.link import link_command # <-- Comment out this line
from .commands.analytics import run_analytics
# Import the config command from its actual location
from .commands.config import manage_config as config_command
from pathlib import Path
from typing import Optional # Keep Optional for type hinting

# Import vault state and config functions
from . import vault_state
from .config import get_vault_path_from_config, get_config, get_auto_update_settings, update_last_scan_timestamp, set_auto_update_setting

# Commands that should NOT trigger an auto-update check
COMMANDS_TO_SKIP_AUTOUPDATE = ['config', 'update-index']

@click.group()
@click.pass_context # Pass context to the group
def main(ctx):
    """Obsidian Librarian - A tool for enhanced note-taking and knowledge management

    Format notes, analyze content, and discover connections in your Obsidian vault.
    """
    # Store context for potential use in subcommands if needed later
    ctx.ensure_object(dict)

    # --- Auto-update Check ---
    # Get command name user invoked (ctx.invoked_subcommand)
    # Check happens *before* the subcommand runs
    command_name = ctx.invoked_subcommand
    if command_name and command_name not in COMMANDS_TO_SKIP_AUTOUPDATE:
        settings = get_auto_update_settings()
        if settings["enabled"]:
            now = time.time()
            time_since_last_scan = now - settings["last_scan_timestamp"]
            interval = settings["interval_seconds"]

            if time_since_last_scan > interval:
                click.echo(f"Index last checked > {interval // 60} minutes ago. Checking for updates...")
                vault_path = get_vault_path_from_config()
                db_path = vault_state.DB_PATH

                if vault_path and db_path.parent.exists(): # Basic check if config/db dir exists
                    # Ensure DB schema is initialized before scan
                    vault_state.initialize_database(db_path)
                    # Run scan quietly
                    success = vault_state.update_vault_scan(vault_path, db_path, quiet=True)
                    if success:
                        update_last_scan_timestamp(now) # Update timestamp only on success
                        click.echo("Auto-update check complete.")
                    else:
                        click.echo(click.style("Auto-update check failed. Run 'olib update-index' manually.", fg="red"))
                elif not vault_path:
                     click.echo(click.style("Skipping auto-update: Vault path not configured.", fg="yellow"))
                # Add separator if output occurred
                click.echo("---")

# Add all commands to the main group
main.add_command(format.format_notes, "format")
main.add_command(check.check, "check")
main.add_command(search.search, "search")
main.add_command(notes.notes, "notes")
main.add_command(run_analytics, "analytics")
main.add_command(config_cmd.manage_config, name='config')
main.add_command(history.history, "history")
main.add_command(undo.undo, "undo")
# main.add_command(link_command, name='link') # <-- Comment out this line

# --- Configuration ---
# Remove this section as it's no longer used by the click command
# # A simple way to find the vault path - assumes it's set in an env var
# # or we could pass it as an option to every command.
# # A more robust solution would use a config file.
# DEFAULT_VAULT_PATH_STR = os.environ.get("OBSIDIAN_VAULT_PATH")
#
# def get_vault_path(vault_path_str: Optional[str] = DEFAULT_VAULT_PATH_STR) -> Path:
#     """Gets the vault path, ensuring it exists."""
#     if not vault_path_str:
#         raise typer.Exit("Error: OBSIDIAN_VAULT_PATH environment variable not set, or vault path not provided.") # typer.Exit is removed
#     vault_path = Path(vault_path_str).resolve()
#     if not vault_path.is_dir():
#         raise typer.Exit(f"Error: Vault path '{vault_path}' not found or is not a directory.") # typer.Exit is removed
#     return vault_path

# --- New Indexing Command (using click) ---
@main.command(name="update-index")
def update_index_command():
    """
    Manually scans the vault and updates the internal file index database.
    """
    vault_path = get_vault_path_from_config()
    if not vault_path:
        click.echo("Error: Vault path not configured. Run 'olib config setup' first.", err=True)
        return

    db_path = vault_state.DB_PATH
    click.echo(f"Using database: {db_path}")

    try:
        vault_state.initialize_database(db_path)
        # Run scan verbosely
        success = vault_state.update_vault_scan(vault_path, db_path, quiet=False)
        if success:
            # Update timestamp after successful manual scan
            update_last_scan_timestamp()
    except Exception as e:
        click.echo(f"An unexpected error occurred during index update: {e}", err=True)


if __name__ == '__main__':
    main()
