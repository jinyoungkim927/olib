import pytest
import os
import time
from pathlib import Path
from unittest.mock import patch, call, MagicMock # Import call and MagicMock
from click.testing import CliRunner

# Import the main cli entrypoint and specific functions/modules needed
from obsidian_librarian import cli, config, vault_state
from obsidian_librarian.commands import index as index_commands # To mock _perform_index_build

# Import helper functions from conftest using absolute path from project root
from tests.conftest import modify_file, add_file

# --- Tests ---

# Use function scope for fixtures to ensure clean state for each test
@pytest.mark.usefixtures("temp_config_dir", "temp_vault")
def test_initial_index_build():
    """Test running 'olib index build' for the first time."""
    runner = CliRunner()
    # Mock the actual index building to speed up test and isolate CLI logic
    # Patch build where it's used in commands.index
    with patch('obsidian_librarian.commands.index._perform_index_build', return_value=True) as mock_build:
         # Patch timestamp update where it's used in commands.index
        with patch('obsidian_librarian.commands.index.update_last_embeddings_build_timestamp') as mock_update_ts:
            result = runner.invoke(cli.main, ['index', 'build'])

    assert result.exit_code == 0
    # Add output check for debugging if needed
    # print(result.output)
    # print(result.exception)
    mock_build.assert_called_once() # Check if the core build logic was invoked
    mock_update_ts.assert_called_once() # Check if timestamp update was invoked

@pytest.mark.usefixtures("temp_config_dir", "temp_vault")
def test_auto_update_no_changes():
    """Test running a command when no files changed since last build."""
    runner = CliRunner()

    # 1. Initial build (manual or simulated) - mock to set timestamp
    initial_build_time = time.time()
    with patch('obsidian_librarian.commands.index._perform_index_build', return_value=True), \
         patch('obsidian_librarian.config.update_last_embeddings_build_timestamp'), \
         patch('time.time', return_value=initial_build_time): # Mock time for timestamp update
        runner.invoke(cli.main, ['index', 'build']) # Run initial build

    # Ensure timestamp is set correctly after mocking time.time
    config.update_last_embeddings_build_timestamp() # Manually call with real time now
    time.sleep(0.1) # Ensure time moves forward

    # 2. Run vault state update (simulates auto-update or manual run)
    # We need the db for the check
    vault_path = Path(config.get_vault_path_from_config())
    db_path = vault_state.DB_PATH
    vault_state.initialize_database(db_path)
    vault_state.update_vault_scan(vault_path, db_path) # Populate DB

    # 3. Run a command that triggers checks (e.g., search)
    # Mock the build function again to see if it gets called *this time*
    with patch('obsidian_librarian.commands.index._perform_index_build') as mock_auto_build:
        # Example: Run a search command (replace with an actual command if needed)
        # runner.invoke(cli.main, ['search', 'dummy_query'])
        # Or just run the check function directly if appropriate for the test
        # For now, let's assume running any command triggers the check in cli.main
        runner.invoke(cli.main, ['status']) # Use a simple command like 'status'

    # Assert that the build function was NOT called because no files changed
    mock_auto_build.assert_not_called()


@pytest.mark.usefixtures("temp_config_dir", "temp_vault")
def test_auto_update_after_modification():
    """Test auto-update triggers after a file modification."""
    runner = CliRunner()
    vault_path = Path(config.get_vault_path_from_config())
    db_path = vault_state.DB_PATH

    # 1. Initial build - Run the actual build command to set state correctly
    with patch('obsidian_librarian.commands.index.index_vault', return_value=True) as mock_index_vault_call:
         result_build = runner.invoke(cli.main, ['index', 'build'])
         assert result_build.exit_code == 0
         mock_index_vault_call.assert_called_once()

    initial_ts = config.get_last_embeddings_build_timestamp()
    assert initial_ts > 0.0
    time.sleep(0.1)

    # 2. Modify a file
    note1_path = vault_path / "note1.md"
    modify_file(note1_path)
    mod_time = os.path.getmtime(note1_path)

    # 3. Update vault state DB
    vault_state.initialize_database(db_path)
    scan_success = vault_state.update_vault_scan(vault_path, db_path, quiet=True)
    assert scan_success is True
    max_mtime_db = vault_state.get_max_mtime_from_db(db_path)
    assert max_mtime_db is not None
    assert abs(max_mtime_db - mod_time) < 0.1
    last_build_ts_before_check = config.get_last_embeddings_build_timestamp()
    print(f"DEBUG: Before check: max_mtime={max_mtime_db}, last_build_ts={last_build_ts_before_check}, condition={max_mtime_db > last_build_ts_before_check}")
    assert max_mtime_db > last_build_ts_before_check

    # 4. Run a command that triggers checks
    with patch('obsidian_librarian.cli.get_auto_update_settings', return_value={
            'enabled': True,
            'interval_minutes': 60, # Provide a default interval
            'last_scan_timestamp': 0 # Provide a default timestamp
         }) as mock_get_settings, \
         patch('obsidian_librarian.cli._perform_index_build', return_value=True) as mock_auto_build, \
         patch('obsidian_librarian.cli.update_last_embeddings_build_timestamp') as mock_update_ts:
        with patch('obsidian_librarian.utils.indexing.find_similar_notes', return_value=[]):
            result_search = runner.invoke(cli.main, ['search', 'test query'])
            assert result_search.exit_code == 0, f"CLI command failed with output:\n{result_search.output}\nException:\n{result_search.exception}"
            assert "Vault changes detected since last embeddings build." in result_search.output

    # Assert that the build function WAS called because files changed
    mock_auto_build.assert_called_once()
    # Assert timestamp was updated too
    mock_update_ts.assert_called_once()


@pytest.mark.usefixtures("temp_config_dir", "temp_vault")
def test_auto_update_after_new_file():
    """Test auto-update triggers after adding a new file."""
    runner = CliRunner()
    vault_path = Path(config.get_vault_path_from_config())
    db_path = vault_state.DB_PATH

    # 1. Initial build
    with patch('obsidian_librarian.commands.index.index_vault', return_value=True) as mock_index_vault_call:
        result_build = runner.invoke(cli.main, ['index', 'build'])
        assert result_build.exit_code == 0
        mock_index_vault_call.assert_called_once()

    initial_ts = config.get_last_embeddings_build_timestamp()
    assert initial_ts > 0.0
    time.sleep(0.1)

    # 2. Add a file
    new_file_path = add_file(vault_path)
    add_time = os.path.getmtime(new_file_path)

    # 3. Update vault state DB
    vault_state.initialize_database(db_path)
    scan_success = vault_state.update_vault_scan(vault_path, db_path, quiet=True)
    assert scan_success is True
    max_mtime_db = vault_state.get_max_mtime_from_db(db_path)
    assert max_mtime_db is not None
    assert abs(max_mtime_db - add_time) < 0.1
    assert max_mtime_db > initial_ts # Check condition

    # 4. Run a command that triggers checks
    with patch('obsidian_librarian.cli.get_auto_update_settings', return_value={
            'enabled': True,
            'interval_minutes': 60, # Provide a default interval
            'last_scan_timestamp': 0 # Provide a default timestamp
         }) as mock_get_settings, \
         patch('obsidian_librarian.cli._perform_index_build', return_value=True) as mock_auto_build, \
         patch('obsidian_librarian.cli.update_last_embeddings_build_timestamp') as mock_update_ts:
        with patch('obsidian_librarian.utils.indexing.find_similar_notes', return_value=[]) as mock_find_similar:
            result_search = runner.invoke(cli.main, ['search', 'new query'])
            assert result_search.exit_code == 0, f"CLI command failed with output:\n{result_search.output}\nException:\n{result_search.exception}"
            assert "Vault changes detected since last embeddings build." in result_search.output

    # Assert that the build function WAS called because a new file was added
    mock_auto_build.assert_called_once()
    mock_update_ts.assert_called_once() # Timestamp should be updated after auto-build
    mock_find_similar.assert_called_once() # Ensure search command logic was reached


@pytest.mark.usefixtures("temp_config_dir", "temp_vault")
def test_commands_skip_update():
    """Test that certain commands skip the auto-update checks."""
    runner = CliRunner()
    vault_path = Path(config.get_vault_path_from_config())

    # 1. Modify a file (to ensure changes exist)
    modify_file(vault_path / "note1.md")

    # 2. Run commands that should skip updates
    commands_to_skip = ['config', 'index', 'init'] # From cli.py
    for cmd_group in commands_to_skip:
        # Mock the check functions to see if they are called
        with patch('obsidian_librarian.cli._check_and_run_auto_update') as mock_hist_check, \
             patch('obsidian_librarian.cli._check_and_run_embedding_update') as mock_embed_check:
            # We need a subcommand for config/index
            subcommand = 'list' if cmd_group == 'config' else 'build' if cmd_group == 'index' else None
            args = [cmd_group]
            if subcommand: args.append(subcommand)

            # Mock underlying logic to prevent errors unrelated to the check skipping
            with patch('obsidian_librarian.config.get_config', return_value={}), \
                 patch('obsidian_librarian.commands.index._perform_index_build', return_value=True):
                 result = runner.invoke(cli.main, args)

            # Assert the check functions were NOT called
            mock_hist_check.assert_not_called()
            mock_embed_check.assert_not_called()
            # Don't assert exit code here as underlying command might fail in isolation 
