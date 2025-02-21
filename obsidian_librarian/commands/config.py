import click


@click.group()
def manage_config():
    click.echo("Managing config...")

@manage_config.command()
def show():
    click.echo("Showing config...")

@manage_config.command()
def save():
    click.echo("Saving config...")

@manage_config.command()
def load():
    click.echo("Loading config...")
