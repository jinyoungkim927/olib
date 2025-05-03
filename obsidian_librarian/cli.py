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

# Define the threshold for triggering embedding updates
MIN_CHANGES_FOR_EMBEDDING = 1 # e.g., 1 means any added or modified file triggers check

# Commands that should NOT trigger *any* auto-updates (history or embeddings)
# Keep 'index' here so 'olib index build' uses the full scan logic within its own command
COMMANDS_TO_SKIP_AUTO_SCAN = ['config', 'index', 'init', 'analytics', 'history', 'undo'] # Fine-tune as needed

# --- Configure Root Logger Early ---
# Set the root logger level to WARNING to suppress INFO messages from libraries like NumExpr
# You can adjust the level (e.g., ERROR) or format as needed.
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__) # Get the logger for this module
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
    ctx.ensure_object(dict)
    db_path_str = str(vault_state.DB_PATH) # Get DB path string once

    # Config check
    if ctx.invoked_subcommand not in ['init', 'config']:
        config_dir = get_config_dir()
        if not os.path.exists(os.path.join(config_dir, "config.json")):
             click.echo("Configuration not found. Run 'olib config setup' or 'olib init'.")
             # Decide if you want to exit or let commands fail
             # return # Example: exit if config is missing

    # --- Automatic INCREMENTAL Scan Check ---
    scan_success = False
    added_count = 0
    modified_count = 0
    if ctx.invoked_subcommand not in COMMANDS_TO_SKIP_AUTO_SCAN:
        scan_success, added_count, modified_count = _check_and_run_auto_update()

    # --- Conditionally Check for Embedding Update ---
    # Only proceed if the scan was successful and changes meet the threshold
    if scan_success and (added_count + modified_count >= MIN_CHANGES_FOR_EMBEDDING):
        logger.info(f"Significant changes detected (added: {added_count}, modified: {modified_count}). Checking if embedding update is needed.")
        # This function now only checks timestamps and runs the build if needed
        _check_and_run_embedding_update(db_path_str)
    elif ctx.invoked_subcommand not in COMMANDS_TO_SKIP_AUTO_SCAN:
         # Log if scan ran but didn't meet threshold (optional)
         logger.debug(f"Scan complete (added: {added_count}, modified: {modified_count}). Change threshold ({MIN_CHANGES_FOR_EMBEDDING}) not met for embedding update check.")

# --- Modify this function to return scan results ---
def _check_and_run_auto_update() -> Tuple[bool, int, int]:
    """
    Checks if auto-update is due and runs an INCREMENTAL vault scan.
    Returns:
        Tuple[bool, int, int]: (scan_success, added_count, modified_count)
    """
    settings = get_auto_update_settings()
    vault_path_config = get_vault_path_from_config()
    db_path = vault_state.DB_PATH
    vault_path = Path(vault_path_config) if vault_path_config else None

    # Default return values
    scan_success, added_count, modified_count = False, 0, 0

    if not vault_path:
        logger.debug("Auto-update skipped: Vault path not configured.")
        return scan_success, added_count, modified_count

    if not settings['enabled']:
        logger.debug("Auto-update disabled.")
        # Return success=True here, as disabling isn't a failure, but counts are 0
        return True, added_count, modified_count

    last_scan = settings['last_scan_timestamp']
    interval = settings['interval_seconds']
    now = time.time()

    if now - last_scan > interval:
        logger.info("Auto-update interval elapsed, running incremental scan...")
        try:
            vault_state.initialize_database(db_path)
            # Run INCREMENTAL scan quietly and get results
            scan_success, added_count, modified_count = vault_state.update_vault_scan(
                vault_path, db_path, quiet=True, full_scan=False
            )
            if scan_success:
                update_last_scan_timestamp()
                logger.info(f"Incremental vault scan complete (Added: {added_count}, Modified: {modified_count}).")
            else:
                logger.error("Auto-update incremental vault scan failed.")
        except Exception as e:
            logger.error(f"An error occurred during auto-update incremental scan: {e}", exc_info=True)
            scan_success = False # Ensure failure is marked
            added_count = 0 # Reset counts on error
            modified_count = 0
    else:
        logger.debug("Auto-update interval not elapsed.")
        scan_success = True # No scan needed is not a failure

    return scan_success, added_count, modified_count

# --- This function now checks timestamps and runs build if needed ---
# It's called conditionally by the main cli function based on scan results.
def _check_and_run_embedding_update(db_path: str):
    """Checks vault mtime vs last build time and triggers index build if needed."""
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
