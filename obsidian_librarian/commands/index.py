import click
import os
import logging
import time
from pathlib import Path
import numpy as np
import json

from obsidian_librarian.config import (
    get_config_dir,
    get_vault_path_from_config,
    get_config,
    update_last_embeddings_build_timestamp
)
from obsidian_librarian.utils.indexing import (
    index_vault,
    get_default_index_paths,
    DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL
)
from .. import config as vault_config, vault_state

# Configure logging for the command
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

@click.group()
def index():
    """Commands for managing the semantic index."""
    pass

@index.command()
@click.option('--force', is_flag=True, help="Force rebuild even if index seems up-to-date.")
def build(force):
    """Build or update the semantic index for the vault."""
    vault_path_config = get_vault_path_from_config()
    if not vault_path_config:
        click.echo("Vault path not configured. Run 'olib config setup'", err=True)
        return

    vault_path = Path(vault_path_config)
    db_path = vault_state.DB_PATH

    vault_state.initialize_database(db_path)
    scan_successful = vault_state.update_vault_scan(vault_path, db_path, quiet=True)
    if not scan_successful:
        click.echo("Vault scan failed. Aborting index build.", err=True)
        return

    last_build_time = vault_config.get_last_embeddings_build_timestamp()
    max_mtime = vault_state.get_max_mtime_from_db(db_path)

    needs_rebuild = False
    if force:
        click.echo("Forcing index rebuild.")
        needs_rebuild = True
    elif last_build_time == 0.0:
        click.echo("No previous build timestamp found (or first run). Building index.")
        needs_rebuild = True
    elif max_mtime is not None and max_mtime > last_build_time:
        click.echo("Vault changes detected since last build. Updating index.")
        needs_rebuild = True
    else:
        click.echo("Index appears up-to-date. Use --force to rebuild.")

    if needs_rebuild:
        click.echo("Building semantic index...")
        start_time = time.time()
        success = _perform_index_build(vault_path, db_path)
        end_time = time.time()

        if success:
            update_last_embeddings_build_timestamp()
            click.echo(f"Index build completed successfully in {end_time - start_time:.2f} seconds.")
        else:
            click.echo("Index build failed.", err=True)
    else:
        if last_build_time == 0.0:
            click.echo("Updating build timestamp as it was missing or zero.")
            update_last_embeddings_build_timestamp()

def _perform_index_build(vault_path: Path, db_path: Path) -> bool:
    """Internal function to handle the actual index building process."""
    try:
        config_data = get_config()
        model_name = config_data.get('embedding_model', DEFAULT_EMBEDDING_MODEL)
        config_dir = get_config_dir()
        embeddings_path, file_map_path = get_default_index_paths(config_dir)

        index_vault(
            db_path=db_path,
            vault_path=vault_path,
            embeddings_path=embeddings_path,
            file_map_path=file_map_path,
            model_name=model_name
        )
        return True
    except Exception as e:
        click.echo(f"Error during index building: {e}", err=True)
        # Log the full traceback for debugging
        import traceback
        traceback.print_exc()
        return False

# Add other index commands if needed (e.g., status, clear)
# index.add_command(status) 