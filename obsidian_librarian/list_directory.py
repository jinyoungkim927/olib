import os
import click
from .config import get_config

@click.command()
def list_directory():
    """Lists all files in the Obsidian vault directory"""
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        print("Vault path not configured. Please reinstall the package.")
        return
    
    if not os.path.exists(vault_path):
        print(f"Configured vault path '{vault_path}' does not exist.")
        return
        
    files = os.listdir(vault_path)
    for file in files:
        print(file)

if __name__ == '__main__':
    list_directory()
