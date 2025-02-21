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
    """Obsidian Librarian CLI tool"""
    pass

# Add all commands to the main group
main.add_command(format.format_notes)
main.add_command(check.check)
main.add_command(search.search)
main.add_command(notes.notes)
main.add_command(analytics.analytics)
main.add_command(config.manage_config)
main.add_command(history.history)
main.add_command(undo.undo)

if __name__ == '__main__':
    main()
