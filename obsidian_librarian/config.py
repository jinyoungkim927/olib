import os
import json
from pathlib import Path
from typing import Optional, Dict
import time

CONFIG_DIR = Path(os.path.expanduser("~/.config/obsidian-librarian"))
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_AUTO_UPDATE_INTERVAL_SECONDS = 3600 # 1 hour

def get_config_dir() -> Path:
    """Returns the application's configuration directory path."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR

def get_config() -> Dict:
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

# --- New Config Functions for Auto-Update ---

def get_auto_update_settings() -> Dict:
    """Gets auto-update settings from config, providing defaults."""
    config = get_config()
    return {
        "enabled": config.get("auto_update_enabled", True), # Default to enabled
        "interval_seconds": config.get("auto_update_interval_seconds", DEFAULT_AUTO_UPDATE_INTERVAL_SECONDS),
        "last_scan_timestamp": config.get("last_scan_timestamp", 0.0) # Default to 0 (long ago)
    }

def update_last_scan_timestamp(timestamp: Optional[float] = None):
    """Updates the last scan timestamp in the config file."""
    config = get_config()
    config["last_scan_timestamp"] = timestamp if timestamp is not None else time.time()
    save_config(config)

def set_auto_update_setting(key: str, value):
    """Sets a specific auto-update setting."""
    # Basic validation could be added here
    valid_keys = ["auto_update_enabled", "auto_update_interval_seconds"]
    if key not in valid_keys:
        print(f"Warning: Invalid auto-update setting key: {key}")
        return
    if key == "auto_update_enabled" and not isinstance(value, bool):
         print(f"Warning: 'auto_update_enabled' must be true or false.")
         return
    if key == "auto_update_interval_seconds" and (not isinstance(value, int) or value < 60):
         print(f"Warning: 'auto_update_interval_seconds' must be an integer >= 60.")
         return

    config = get_config()
    config[key] = value
    # Also update last_scan_timestamp to 0 when enabling/disabling or changing interval
    # to ensure a scan runs soon if needed after the change.
    config["last_scan_timestamp"] = 0.0
    save_config(config)
    print(f"Set {key} = {value}")
