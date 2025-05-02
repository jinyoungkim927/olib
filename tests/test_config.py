import pytest
import time
import os
from pathlib import Path

from obsidian_librarian import config

def test_get_set_last_embeddings_build_timestamp(temp_config_dir):
    """Test getting and setting the embeddings build timestamp."""
    # Ensure config dir exists (handled by fixture)
    config_file = temp_config_dir / "config.json"

    # 1. Test default value (config file might not exist yet)
    assert config.get_last_embeddings_build_timestamp() == 0.0

    # 2. Test setting the timestamp
    start_time = time.time()
    config.update_last_embeddings_build_timestamp()
    end_time = time.time()

    # Check config file was created and written to
    assert config_file.exists()
    cfg_data = config.get_config() # Use get_config to load
    assert "last_embeddings_build_timestamp" in cfg_data
    timestamp_in_file = cfg_data["last_embeddings_build_timestamp"]
    assert start_time <= timestamp_in_file <= end_time

    # 3. Test getting the timestamp after setting
    retrieved_timestamp = config.get_last_embeddings_build_timestamp()
    assert retrieved_timestamp == timestamp_in_file

    # 4. Test updating the timestamp again
    time.sleep(0.1) # Ensure time progresses
    start_time_2 = time.time()
    config.update_last_embeddings_build_timestamp()
    end_time_2 = time.time()

    retrieved_timestamp_2 = config.get_last_embeddings_build_timestamp()
    assert retrieved_timestamp_2 > retrieved_timestamp
    assert start_time_2 <= retrieved_timestamp_2 <= end_time_2 