import os
import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(os.path.expanduser("~/.config/obsidian-librarian"))
CONFIG_FILE = CONFIG_DIR / "config.json"

def get_config_dir() -> Path:
    """Returns the application's configuration directory path."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR

def get_config():
    """Loads the configuration file."""
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Configuration file at {config_file} is corrupted. Please run setup again.")
            return {}
    return {}

def get_vault_path_from_config() -> Optional[Path]:
    """Gets the vault path from the config file."""
    config = get_config()
    vault_path_str = config.get('vault_path')
    if not vault_path_str:
        return None
    vault_path = Path(vault_path_str)
    if not vault_path.is_dir():
        print(f"Warning: Configured vault path '{vault_path}' not found or is not a directory.")
        return None
    return vault_path.resolve()

def save_config(config: dict):
    """Saves the configuration dictionary to the config file."""
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        print(f"Error saving configuration to {config_file}: {e}")

def setup_vault_path():
    """Prompts the user for the vault path and saves it."""
    vault_path_str = input("Please enter your Obsidian vault path (e.g., /Users/username/Documents/Obsidian Vault): ").strip()
    vault_path = Path(vault_path_str)

    while not vault_path.is_dir():
        print("The specified path does not exist or is not a directory. Please enter a valid path.")
        vault_path_str = input("Obsidian vault path: ").strip()
        vault_path = Path(vault_path_str)

    config = get_config()
    config['vault_path'] = str(vault_path.resolve())
    save_config(config)
    print(f"✅ Vault path saved: {vault_path.resolve()}")
    return str(vault_path.resolve())
