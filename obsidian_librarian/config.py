import os
import json
from pathlib import Path
from typing import Optional, Dict
import time
import logging
import sys
import platform

# Configure logger
logger = logging.getLogger(__name__)

CONFIG_DIR = Path(os.path.expanduser("~/.config/obsidian-librarian"))
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_AUTO_UPDATE_INTERVAL_SECONDS = 3600 # 1 hour
DEFAULT_CONFIG = {
    "vault_path": None,
    "auto_update_interval_minutes": 60,
    "last_scan_timestamp": 0,
    "embedding_model": "all-MiniLM-L6-v2", # Default model
    "llm_model": "gpt-4o", # Default LLM
    "last_embeddings_build_timestamp": 0 # <-- Add new key with default 0
}

def get_config_dir() -> Path:
    """Gets the platform-specific configuration directory path."""
    if platform.system() == "Windows":
        config_dir = Path(os.environ.get("APPDATA", "")) / "ObsidianLibrarian"
    elif platform.system() == "Darwin": # macOS
        config_dir = Path.home() / ".config" / "obsidian-librarian"
    else: # Linux and other Unix-like
        config_dir = Path.home() / ".config" / "obsidian-librarian"

    # Fallback if standard paths fail (e.g., unusual environment)
    if not config_dir.parent.exists():
         config_dir = Path.home() / ".obsidian_librarian" # Fallback to home dir

    return config_dir

def ensure_config_dir_exists():
    """Creates the configuration directory if it doesn't exist."""
    config_dir = get_config_dir()
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured configuration directory exists: {config_dir}")
    except OSError as e:
        logger.error(f"Could not create configuration directory {config_dir}: {e}")
        # Depending on severity, you might want to raise the error or exit
        # For now, just log the error. Operations requiring the dir will likely fail later.

def get_config_file_path() -> Path:
    """Gets the full path to the configuration file."""
    return get_config_dir() / "config.json"

def get_config() -> Dict:
    """
    Loads configuration from file, adds missing default values,
    and saves the updated configuration back to the file if defaults were added.
    """
    config = {}
    defaults_added = False # Flag to track if we need to save

    try:
        ensure_config_dir_exists() # Ensure dir exists before trying to read
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        else:
            logger.info(f"Config file not found at {CONFIG_FILE}. Creating with defaults.")
            # If file doesn't exist, all defaults will be added below
            defaults_added = True # Mark for saving

    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error loading config file {CONFIG_FILE}: {e}. Using defaults and attempting to overwrite.")
        config = {} # Start fresh if file is corrupt or unreadable
        defaults_added = True # Mark for saving

    # Check for missing keys compared to DEFAULT_CONFIG and add them
    current_keys = set(config.keys())
    default_keys = set(DEFAULT_CONFIG.keys())
    missing_keys = default_keys - current_keys

    if missing_keys:
        logger.info(f"Adding default values for missing keys: {', '.join(missing_keys)}")
        for key in missing_keys:
            config[key] = DEFAULT_CONFIG[key]
        defaults_added = True # Mark that defaults were added

    # --- Save the config ONLY if defaults were added ---
    if defaults_added:
        logger.info("Saving configuration file with added default values.")
        save_config(config) # Call the save function
    # --- End Save ---

    return config

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

def save_config(config_data):
    """Saves the configuration dictionary to the config file."""
    config_path = CONFIG_FILE # Use the globally defined config file path
    try:
        # Ensure the directory exists
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        # print(f"DEBUG: Config saved to {config_path}") # Optional debug print
    except Exception as e:
        # Log or print the error appropriately
        print(f"Error saving config to {config_path}: {e}", file=sys.stderr)
        # Consider raising the exception or handling it based on application needs
        # raise # Re-raise if saving is critical

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

def get_last_embeddings_build_timestamp() -> float:
    """Gets the timestamp of the last successful embeddings build."""
    config = get_config()
    # Return 0.0 if key doesn't exist or is invalid, ensuring rebuild on first run
    return float(config.get("last_embeddings_build_timestamp", 0.0))

def update_last_embeddings_build_timestamp():
    """Updates the timestamp of the last successful embeddings build to the current time."""
    # config_dir = get_config_dir() # Not needed if save_config uses global path
    # config_path = os.path.join(config_dir, CONFIG_FILE) # Not needed
    config_data = get_config() # Load current config
    current_time = time.time()
    config_data["last_embeddings_build_timestamp"] = current_time
    # print(f"DEBUG: Updating timestamp to {current_time}") # Optional debug print
    # --- FIX: Call save_config with only one argument ---
    save_config(config_data)
    # --- End Fix ---
    # print("DEBUG: Timestamp update saved.") # Optional debug print
