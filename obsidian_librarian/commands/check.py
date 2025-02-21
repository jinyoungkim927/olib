import click

# Should be a group with 'semantic' and 'prereq' subcommands
@click.group()
def check():
    click.echo("Checking...")

@check.command()
def semantic():
    click.echo("Semantic checking...")

@check.command()
def prereq():
    click.echo("Prerequisite checking...")
