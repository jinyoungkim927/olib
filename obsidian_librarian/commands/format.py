import click

# Should be a group command with subcommands for formatting and screenshot conversion
@click.group()
def format_notes():
    click.echo("Formatting...")

@format_notes.command()
def format():
    click.echo("Formatting...")

@format_notes.command()
def screenshot():
    click.echo("Screenshot...")
