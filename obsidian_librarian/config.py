import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/obsidian-librarian")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def setup_vault_path():
    vault_path = input("Please enter your Obsidian vault path (e.g., /Users/username/Documents/Obsidian Vault): ").strip()
    
    while not os.path.exists(vault_path):
        print("The specified path does not exist. Please enter a valid path.")
        vault_path = input("Obsidian vault path: ").strip()
    
    config = get_config()
    config['vault_path'] = vault_path
    save_config(config)
    return vault_path
