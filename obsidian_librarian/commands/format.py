import click

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
