import click
from .commands import (
    format,
    check,
    search,
    notes,
    analytics,
    history,
    undo
)
# Import config utility functions if needed elsewhere, but not the command itself
# from .config import get_config # Example if needed

# Import specific command functions/groups
# from .commands.link import link_command # <-- Comment out this line
from .commands.analytics import analytics as analytics_command
# Import the config command from its actual location
from .commands.config import manage_config as config_command

@click.group()
def main():
    """Obsidian Librarian - A tool for enhanced note-taking and knowledge management

    Format notes, analyze content, and discover connections in your Obsidian vault.
    """
    pass

# Add all commands to the main group
main.add_command(format.format_notes, "format")
main.add_command(check.check, "check")
main.add_command(search.search, "search")
main.add_command(notes.notes, "notes")
main.add_command(analytics_command, "analytics")
main.add_command(config_command, name='config')
main.add_command(history.history, "history")
main.add_command(undo.undo, "undo")
# main.add_command(link_command, name='link') # <-- Comment out this line

if __name__ == '__main__':
    main()
