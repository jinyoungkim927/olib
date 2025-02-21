import click

# Should be a group with 'semantic' and 'prereq' subcommands
@click.group()
def search():
    click.echo("Searching...")

@search.command()
def semantic():
    click.echo("Semantic search...")

@search.command()
def prereq():
    click.echo("Prerequisite search...")

@search.command()
def accuracy():
    click.echo("Accuracy search...")
