import click
import os
import sys # Import sys
import platform # Import platform
import shutil # Import shutil
import time # Import time
import logging
from .commands import (
    format,
    check,
    search,
    notes,
    history,
    undo,
    config as config_cmd,
    index as index_cmd,
    analytics as analytics_cmd # Import the analytics module
)
# Import config utility functions if needed elsewhere, but not the command itself
# from .config import get_config # Example if needed

# Import specific command functions/groups
# from .commands.link import link_command # <-- Comment out this line
# from .commands.analytics import run_analytics
# Import the config command from its actual location
from .commands.config import manage_config as config_command
from pathlib import Path
from typing import Optional, Tuple # Keep Optional for type hinting

# Import vault state and config functions
from . import vault_state
from .config import get_vault_path_from_config, get_config, get_auto_update_settings, update_last_scan_timestamp, set_auto_update_setting, get_config_dir, get_last_embeddings_build_timestamp, update_last_embeddings_build_timestamp
from .vault_state import get_max_mtime_from_db # <-- Import
from .utils.indexing import DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL # <-- Import default model name
# --- Import the build function from commands.index ---
from .commands.index import _perform_index_build
# --- End import ---

# Commands that should NOT trigger *any* auto-updates (history or embeddings)
COMMANDS_TO_SKIP_UPDATES = ['config', 'index', 'init', 'analytics'] # Add 'analytics'

# --- Configure Root Logger Early ---
# Set the root logger level to WARNING to suppress INFO messages from libraries like NumExpr
# You can adjust the level (e.g., ERROR) or format as needed.
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
# Optional: Set NumExpr threads to potentially silence its specific info message
# os.environ['NUMEXPR_MAX_THREADS'] = '8' # Or another number based on your cores

# --- Define Context Settings ---
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

# --- Main CLI Group ---
@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name='obsidian-librarian')
@click.pass_context
def cli(ctx, **kwargs):
    """Obsidian Librarian: Manage and enhance your Obsidian vault."""
    # Basic context setup if needed
    ctx.ensure_object(dict)

    # Check if config needs setup before running any command (except init/config)
    ctx = click.get_current_context()
    if ctx.invoked_subcommand not in ['init', 'config']:
        config_dir = get_config_dir()
        if not os.path.exists(os.path.join(config_dir, "config.json")):
             click.echo("Configuration not found.")
             # Optionally run setup automatically or prompt user
             # For now, just inform and exit or let subsequent commands fail
             # if not setup_initial_config(): # Example auto-setup
             #     return # Exit if setup fails/is cancelled

    # --- Auto-update checks moved here, before command execution ---
    if ctx.invoked_subcommand not in COMMANDS_TO_SKIP_UPDATES:
        # 1. Check and update file history DB (vault_state)
        db_updated, db_path = _check_and_run_auto_update() # Modified to return db_path

        # 2. Check and update embeddings index if necessary
        if db_path: # Only proceed if vault path and db path are valid
            # --- Pass db_path correctly ---
            _check_and_run_embedding_update(db_path)
            # --- End passing db_path ---
    # --- End auto-update checks ---

# --- Modify this function to return db_path ---
def _check_and_run_auto_update() -> Tuple[bool, Optional[str]]:
    """Checks if auto-update is due and runs the vault scan."""
    settings = get_auto_update_settings()
    vault_path = get_vault_path_from_config()
    db_path = vault_state.DB_PATH # Use the constant

    if not vault_path:
        # Vault path not set, cannot auto-update
        # click.echo("Auto-update skipped: Vault path not configured.", err=True) # Optional message
        return False, None

    if not settings['enabled']:
        # click.echo("Auto-update disabled.") # Optional message
        # Still return db_path as it might be needed for embedding check later
        return False, db_path

    last_scan = settings['last_scan_timestamp']
    interval = settings['interval_seconds']
    now = time.time()

    if now - last_scan > interval:
        click.echo("Auto-update interval elapsed, checking for vault changes...")
        try:
            vault_state.initialize_database(db_path)
            # Run scan quietly
            success = vault_state.update_vault_scan(vault_path, db_path, quiet=True)
            if success:
                update_last_scan_timestamp() # Update timestamp only on success
                click.echo("Vault scan complete.")
                return True, db_path
            else:
                click.secho("Auto-update vault scan failed.", fg="red")
                return False, db_path # Return db_path even on failure
        except Exception as e:
            click.secho(f"An error occurred during auto-update scan: {e}", fg="red", err=True)
            return False, db_path # Return db_path even on failure
    else:
        # Interval not elapsed
        return False, db_path # Return db_path

# --- Add this new function ---
def _check_and_run_embedding_update(db_path: str): # <-- Accept db_path as string
    """Checks if embeddings index needs rebuilding and triggers it."""
    config_dir = get_config_dir()
    vault_path_config = get_vault_path_from_config() # Assume vault_path is valid if db_path is

    # Double check paths needed for build function
    if not vault_path_config or not config_dir:
        logging.warning("Skipping embedding update check: Vault or Config path missing.")
        return

    # --- Convert paths to Path objects ---
    vault_path = Path(vault_path_config)
    db_path_obj = Path(db_path)
    # --- End path conversion ---


    try:
        last_build_ts = get_last_embeddings_build_timestamp()
        # Query the DB for the most recent modification time recorded
        # --- Pass Path object to DB function ---
        max_mtime = get_max_mtime_from_db(db_path_obj)
        # --- End passing Path object ---

        # If max_mtime exists and is more recent than the last build, rebuild.
        # The check `last_build_ts == 0.0` handles the very first run.
        if max_mtime is not None and (max_mtime > last_build_ts or last_build_ts == 0.0):
            click.echo("Vault changes detected since last embeddings build. Rebuilding index...")
            # Get model from config or use default (handled within _perform_index_build now)
            # config = get_config()
            # model_name = config.get('embedding_model', DEFAULT_EMBEDDING_MODEL)

            # Call the refactored build function from commands.index
            # --- Pass vault_path and db_path_obj ---
            success = _perform_index_build(vault_path, db_path_obj)
            # --- End passing paths ---
            if success:
                # Update timestamp only on successful rebuild
                update_last_embeddings_build_timestamp() # <-- Call timestamp update here too
                click.echo("Embeddings index rebuilt successfully.")
            else:
                click.secho("Automatic embeddings index rebuild failed. Run 'olib index build' manually.", fg="red")
        # else: # Optional: Log that no rebuild is needed
            # logging.info("Embeddings index is up-to-date.")

    except Exception as e:
        # Catch broad exceptions to prevent crashing the main command
        click.secho(f"Error during automatic embedding index check/update: {e}", fg="red", err=True)
        logging.exception("Embedding update check failed")
# --- End of new function ---

# Add command groups
cli.add_command(format.format_notes, name="format")
cli.add_command(check.check)
cli.add_command(search.search)
cli.add_command(notes.notes)
cli.add_command(history.history)
cli.add_command(undo.undo)
cli.add_command(config_cmd.manage_config, name="config")
cli.add_command(index_cmd.index, name="index")
cli.add_command(analytics_cmd.analytics, name="analytics")
# main.add_command(update_index_command) # Remove old standalone update-index if it exists

# --- Entry Point ---
def main():
    # Check for required dependencies early? (Optional)
    # try:
    #     import pandas
    #     import numpy
    # except ImportError as e:
    #     click.echo(f"Missing dependency: {e}. Some commands might not work.", err=True)
    #     click.echo("Consider running: pip install pandas numpy", err=True)

    cli(obj={}) # Pass an empty object for context if needed

if __name__ == '__main__':
    main()
