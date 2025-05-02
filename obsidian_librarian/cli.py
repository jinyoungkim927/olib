import click
import os
import sys # Import sys
import platform # Import platform
import shutil # Import shutil
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
from .config import get_vault_path_from_config, get_config # Import necessary config functions

@click.group()
def main():
    """Obsidian Librarian - A tool for enhanced note-taking and knowledge management

    Format notes, analyze content, and discover connections in your Obsidian vault.
    """
    # Check if vault path is configured before running any command except config
    # This can be done within each command or via a context object if needed later
    pass

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
# Remove the vault option, rely on config
# @click.option('--vault', '-v', 'vault_path_override', type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True), help="Override configured vault path.")
def update_index_command():
    """
    Scans the vault and updates the internal file index database.
    Reads vault path from configuration. Run 'olib config setup' first.
    Run this periodically or after significant changes.
    """
    # Get vault path from config
    vault_path = get_vault_path_from_config()
    if not vault_path:
        click.echo("Error: Vault path not configured or not found. Run 'olib config setup' first.", err=True)
        return # Exit if no vault path

    # Get DB path (uses default from vault_state)
    db_path = vault_state.DB_PATH

    try:
        # Ensure DB exists and has the correct schema
        vault_state.initialize_database(db_path)
        click.echo(f"Using database: {db_path}")

        # Scan the vault
        vault_state.update_vault_scan(vault_path, db_path)
        # Output is handled within update_vault_scan now
        # print("Index update complete.")
    except ValueError as e: # Catch specific error from update_vault_scan
         click.echo(f"Error: {e}", err=True)
    except Exception as e:
        click.echo(f"An unexpected error occurred during index update: {e}", err=True)


# --- New Scheduling Helper Command ---
@main.command(name="schedule-update")
def schedule_update_command():
    """
    Provides instructions to schedule hourly vault index updates using the OS scheduler.
    """
    click.echo("This command helps you set up automatic hourly updates for the vault index.")

    # Find the full path to the olib executable
    olib_path = shutil.which("olib")
    if not olib_path:
        # Fallback if shutil.which doesn't work (e.g., unusual PATH setup)
        # This assumes olib is runnable via the python executable's directory
        python_executable_dir = Path(sys.executable).parent
        potential_path = python_executable_dir / "olib"
        if potential_path.is_file():
             olib_path = str(potential_path.resolve())
        else:
             click.echo(click.style("Error: Could not automatically find the 'olib' executable path.", fg="red"))
             click.echo("Please find it manually (e.g., run 'which olib' or 'where olib') and use that path in the instructions below.")
             olib_path = "/path/to/your/olib" # Placeholder

    system = platform.system()
    log_file = Path.home() / "olib_update_index.log" # Suggest log in home dir

    if system == "Linux" or system == "Darwin": # Linux or macOS
        click.echo("\nTo schedule hourly updates using cron (Linux/macOS):")
        click.echo("1. Open your crontab for editing by running:")
        click.echo(click.style("   crontab -e", fg="cyan"))
        click.echo("2. Add the following line at the bottom (adjust log path if desired):")
        click.echo(click.style(f"   0 * * * * {olib_path} update-index > {log_file} 2>&1", fg="green"))
        click.echo("3. Save and close the editor (e.g., Esc -> :wq in vim, Ctrl+X -> Y in nano).")
        click.echo(f"\nOutput and errors will be logged to: {log_file}")

    elif system == "Windows":
        click.echo("\nTo schedule hourly updates using Windows Task Scheduler:")
        click.echo("1. Open Task Scheduler (search for it in the Start Menu).")
        click.echo("2. Click 'Create Basic Task...' in the Actions pane.")
        click.echo("3. Name: 'Obsidian Librarian Index Update', Description: 'Updates olib index hourly'. Click Next.")
        click.echo("4. Trigger: Select 'Daily'. Click Next.")
        click.echo("5. Daily: Set start time. Recur every '1' days. Check 'Repeat task every:' and select '1 hour' for a duration of 'Indefinitely'. Click Next.")
        click.echo("6. Action: Select 'Start a program'. Click Next.")
        click.echo("7. Start a program:")
        click.echo(f"   Program/script: {click.style(olib_path, fg='green')}")
        click.echo(f"   Add arguments (optional): {click.style('update-index', fg='green')}")
        # Note: Redirecting output in Task Scheduler is more complex, often done via cmd /c
        click.echo("   (Logging output might require running via 'cmd /c \"your command > logfile\"')")
        click.echo("8. Click Next, review the settings, and click Finish.")
        click.echo("\nConsider running the task with appropriate user permissions.")

    else:
        click.echo(f"\nUnsupported operating system: {system}. Please consult your OS documentation for scheduling tasks.")

    click.echo("\nEnsure the user running the scheduled task has permissions to access:")
    click.echo(f"- Your vault: {get_vault_path_from_config() or 'Not Configured'}")
    click.echo(f"- The olib database: {vault_state.DB_PATH}")


# --- Example: Integrating record_access into format command ---
# You would modify the relevant command file, e.g., obsidian_librarian/commands/format.py
# Inside the function that processes a file (e.g., FormatFixer.format_file or the command itself):
#
# from .. import vault_state
# from ..config import get_vault_path_from_config
# from pathlib import Path
#
# def some_processing_function(file_path_str: str):
#     file_path = Path(file_path_str)
#     vault_path = get_vault_path_from_config() # Get vault path
#
#     # ... perform formatting or other actions ...
#
#     # After successful processing, record access
#     if vault_path and file_path.is_relative_to(vault_path): # Check if file is within vault
#         try:
#             relative_path = file_path.relative_to(vault_path)
#             vault_state.record_access(str(relative_path))
#             # print(f"Recorded access for {relative_path}") # Optional debug
#         except ValueError:
#              print(f"Warning: Could not determine relative path for {file_path} within {vault_path}")
#         except Exception as e:
#              print(f"Warning: Failed to record access for {file_path}: {e}")
#     elif not vault_path:
#          print("Warning: Vault path not configured, cannot record access.")
#     else:
#          print(f"Warning: File {file_path} is outside the configured vault {vault_path}, access not recorded.")


if __name__ == '__main__':
    main()
