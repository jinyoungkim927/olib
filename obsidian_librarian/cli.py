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
from .config import (
    get_vault_path_from_config, get_config, get_auto_update_settings,
    update_last_scan_timestamp, set_auto_update_setting, get_config_dir,
    get_last_embeddings_build_timestamp, update_last_embeddings_build_timestamp,
    ensure_config_dir_exists # setup_config removed
)
from .vault_state import get_max_mtime_from_db, VaultStateManager # <-- Import
# --- Remove the problematic import from utils.indexing ---
# from .utils.indexing import DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL, build_embeddings_index # <-- REMOVE THIS LINE
# --- Keep the import for the default model name if needed elsewhere, or remove if unused ---
from .utils.indexing import DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL # <-- Keep only this part if DEFAULT_MODEL is needed
# --- Import the build function from commands.index ---
from .commands.index import _perform_index_build
# --- End import ---

# Define the threshold for triggering embedding updates
MIN_CHANGES_FOR_EMBEDDING = 1 # e.g., 1 means any added or modified file triggers check

# Commands that should NOT trigger *any* auto-updates (history or embeddings)
# Keep 'index' here so 'olib index build' uses the full scan logic within its own command
COMMANDS_TO_SKIP_AUTO_SCAN = ['config', 'index', 'init', 'analytics', 'history', 'undo'] # Fine-tune as needed

# --- Configure Logging ---
# Determine log level based on verbosity flags
def configure_logging(verbose: int, quiet: bool):
    """Configures logging level."""
    log_level = logging.WARNING # Default level
    if quiet:
        log_level = logging.ERROR
    elif verbose == 1:
        log_level = logging.INFO
    elif verbose >= 2:
        log_level = logging.DEBUG

    # Basic configuration
    logging.basicConfig(
        level=log_level,
        format='%(levelname)-8s %(name)s:%(filename)s:%(lineno)d %(message)s',
        # Use stream handler to output to stderr by default
        stream=sys.stderr,
    )

    # --- Silence Third-Party Loggers ---
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING) # httpx dependency
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING) # sentence_transformers dependency
    logging.getLogger("PIL").setLevel(logging.WARNING) # Often noisy dependency
    # Add any other noisy libraries here
    # --- End Silencing ---

    # You could add file logging here if desired
    # log_file = get_config_dir() / "obsidian_librarian.log"
    # file_handler = logging.FileHandler(log_file)
    # file_handler.setLevel(logging.DEBUG) # Log everything to file
    # file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # file_handler.setFormatter(file_formatter)
    # logging.getLogger().addHandler(file_handler)

    logger = logging.getLogger(__name__) # Get logger for this module
    logger.debug(f"Logging configured to level: {logging.getLevelName(log_level)}")

# --- End Logging Configuration ---

# --- CLI Setup ---
@click.group()
@click.version_option(package_name='obsidian-librarian')
@click.option('-v', '--verbose', count=True, help='Increase verbosity (use -vv for debug).')
@click.option('-q', '--quiet', is_flag=True, help='Suppress all output except errors.')
@click.pass_context
def cli(ctx, verbose, quiet):
    """Obsidian Librarian: Manage and enhance your Obsidian vault."""
    ensure_config_dir_exists() # Ensure config dir exists early
    configure_logging(verbose, quiet) # Configure logging based on flags
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose
    ctx.obj['QUIET'] = quiet
    logger = logging.getLogger(__name__) # Get logger early

    # --- Check if the invoked command should skip the auto-scan ---
    # ctx.invoked_subcommand gives the name of the command being run (e.g., 'config', 'index', 'format')
    if ctx.invoked_subcommand in COMMANDS_TO_SKIP_AUTO_SCAN:
        logger.debug(f"Command '{ctx.invoked_subcommand}' is in skip list, skipping auto-scan.")
    else:
        logger.debug(f"Command '{ctx.invoked_subcommand}' not in skip list, proceeding with auto-scan check.")
        # --- Auto-scan and Indexing Logic ---
        # --- Indent the entire auto-scan block ---
        config = get_config()
        vault_path = get_vault_path_from_config()
        auto_scan_interval = config.get('auto_scan_interval_minutes', 60) * 60 # Default 60 mins
        last_scan_time = config.get('last_scan_time', 0)
        # --- Add check for vault_path before calculating run_scan ---
        run_scan = False
        if vault_path:
             run_scan = (time.time() - last_scan_time > auto_scan_interval)
        else:
             logger.debug("Vault path not set, skipping auto-scan interval check.")
        # --- End Add check ---


        if vault_path and run_scan and not quiet:
            logger.info("Auto-update interval elapsed, running incremental scan...")
            try:
                state_manager = VaultStateManager(vault_path)
                added_count, modified_count, deleted_count = state_manager.incremental_scan()
                logger.info(f"Incremental vault scan complete (Added: {added_count}, Modified: {modified_count}, Deleted: {deleted_count}).")
                state_manager.close()

                # Update last scan time in config
                # --- We need a way to save the updated config ---
                # This requires importing or defining a save_config function
                # For now, let's assume update_last_scan_timestamp handles saving
                update_last_scan_timestamp(time.time())
                logger.debug(f"Updated last_scan_time to {time.time()}")
                # --- End config saving assumption ---


                # Check if significant changes warrant embedding update
                # Define "significant" - e.g., more than 5 changes total
                significant_change_threshold = 5 # Make this configurable?
                total_changes = added_count + modified_count # Ignore deletes for now?
                if total_changes >= significant_change_threshold:
                     logger.info(f"Significant changes detected (added: {added_count}, modified: {modified_count}). Checking if embedding update is needed.")
                     # TODO: Implement logic to check if embeddings *actually* need updating
                     # This might involve comparing last_embeddings_build_time with max mtime of changed files
                     # Or just triggering a build if changes > threshold (simpler but less efficient)
                     # click.echo("Significant changes detected. Consider running 'olib index build'.") # Placeholder message
                elif total_changes > 0:
                     logger.info("Minor changes detected, skipping automatic embedding rebuild check.")


            except Exception as e:
                logger.error(f"Auto-scan failed: {e}", exc_info=True) # Log traceback on error
                if verbose > 0: # Show error to user if verbose
                     click.secho(f"Auto-scan failed: {e}", fg="red")
        elif not quiet:
             if not vault_path:
                 logger.debug("Auto-scan skipped: Vault path not configured.")
             elif not run_scan:
                 logger.debug(f"Auto-scan skipped: Interval not elapsed (Last scan: {datetime.fromtimestamp(last_scan_time).strftime('%Y-%m-%d %H:%M:%S') if last_scan_time else 'Never'}, Interval: {auto_scan_interval/60} mins).")
        # --- End Indentation for Auto-scan block ---
    # --- End Auto-scan ---


# Add command groups to the main CLI
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
