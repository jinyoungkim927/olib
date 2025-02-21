import click

@click.command()
def analytics():
    click.echo("Analytics...")

@analytics.command()
def show():
    click.echo("Showing analytics...")

@analytics.command()
def save():
    click.echo("Saving analytics...")

@analytics.command()
def load():
    click.echo("Loading analytics...")
