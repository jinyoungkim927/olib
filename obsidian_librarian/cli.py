import click
from .commands import (
    format,
    check,
    search,
    notes,
    analytics,
    config,
    history,
    undo
)

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
main.add_command(analytics.analytics, "analytics")
main.add_command(config.manage_config, "config")
main.add_command(history.history, "history")
main.add_command(undo.undo, "undo")

if __name__ == '__main__':
    main()
