import click
from ..setup_command import run_setup
from ..config import get_config

@click.group()
def manage_config():
    """Managing configuration settings"""
    pass

@manage_config.command()
def show():
    """Show the current configuration"""
    config = get_config()
    click.echo(f"Vault path: {config.get('vault_path')}")
    click.echo(f"API key: {config.get('api_key')}")

@manage_config.command()
def save():
    click.echo("Saving config...")

@manage_config.command()
def load():
    click.echo("Loading config...")

@manage_config.command()
def setup():
    """Run the initial setup process"""
    run_setup()
