import pytest
import tempfile
import shutil
import os
from pathlib import Path
import time
import json

from obsidian_librarian import config, vault_state

# --- Fixtures ---

@pytest.fixture(scope="function") # Run for each test function
def temp_config_dir(monkeypatch):
    """Creates a temporary directory for config files and mocks config functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_file_path = tmp_path / "config.json" # Define path first

        # Mock config functions to use this temp dir
        monkeypatch.setattr(config, 'CONFIG_DIR', tmp_path)
        monkeypatch.setattr(config, 'CONFIG_FILE', config_file_path)
        # Mock vault_state DB path to be inside temp config
        monkeypatch.setattr(vault_state, 'DB_PATH', tmp_path / "vault_state.db")

        # Ensure the mocked directory exists
        tmp_path.mkdir(parents=True, exist_ok=True)

        # --- FIX: Create a default config file with necessary keys ---
        default_data = config.DEFAULT_CONFIG.copy()
        # Ensure auto_update_settings exists with default values
        if "auto_update_settings" not in default_data:
             default_data["auto_update_settings"] = {
                 "enable_auto_update": False,
                 "interval_minutes": 60 # Add the missing key
             }
        elif "interval_minutes" not in default_data["auto_update_settings"]:
             default_data["auto_update_settings"]["interval_minutes"] = 60 # Add if section exists but key missing

        with open(config_file_path, 'w') as f:
            json.dump(default_data, f)
        # --- End Fix ---


        yield tmp_path # Provide the path to the test
        # Cleanup happens automatically when exiting the 'with' block

@pytest.fixture(scope="function")
def temp_vault(temp_config_dir):
    """Creates a temporary vault directory and sets it in the temp config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)

        # Load the temp config, update vault path, save back
        config_file_path = temp_config_dir / "config.json"
        if config_file_path.exists():
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
        else:
            # If temp_config_dir didn't create it (it should now), start fresh
            config_data = config.DEFAULT_CONFIG.copy()
            # Ensure auto_update_settings exists here too if starting fresh
            if "auto_update_settings" not in config_data:
                 config_data["auto_update_settings"] = {
                     "enable_auto_update": False,
                     "interval_minutes": 60
                 }
            elif "interval_minutes" not in config_data["auto_update_settings"]:
                 config_data["auto_update_settings"]["interval_minutes"] = 60


        config_data["vault_path"] = str(vault_path)
        with open(config_file_path, 'w') as f:
            json.dump(config_data, f)

        # Create some dummy files
        (vault_path / "note1.md").write_text("Content of note 1.")
        time.sleep(0.01) # Ensure slightly different mtimes
        (vault_path / "note2.md").write_text("Content of note 2, slightly different.")
        (vault_path / "subdir").mkdir()
        (vault_path / "subdir" / "note3.md").write_text("Content of note 3 in subdir.")

        yield vault_path # Provide the path to the test

# --- Helper Functions ---

def modify_file(filepath: Path, append_text=" modified"):
    """Appends text to a file and updates its mtime."""
    current_time = time.time()
    with open(filepath, "a") as f:
        f.write(append_text)
    # Explicitly set mtime to ensure it's updated reliably across systems
    os.utime(filepath, (current_time, current_time))
    time.sleep(0.01) # Small delay

def add_file(dirpath: Path, filename="new_note.md", content="New content."):
    """Adds a new file to the directory."""
    filepath = dirpath / filename
    filepath.write_text(content)
    time.sleep(0.01) # Small delay
    return filepath 
