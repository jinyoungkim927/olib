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
    index_vault as build_semantic_index,
    get_default_index_paths,
    DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL,
    extract_frontmatter,
)
from obsidian_librarian.utils.formatting import generate_index_content
from .. import config as vault_config

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
    """Internal function to handle the actual semantic index building process."""
    try:
        config_data = get_config()
        model_name = config_data.get('embedding_model', DEFAULT_EMBEDDING_MODEL)
        config_dir = get_config_dir()
        embeddings_path, file_map_path = get_default_index_paths(config_dir)

        build_semantic_index(
            db_path=db_path,
            vault_path=vault_path,
            embeddings_path=embeddings_path,
            file_map_path=file_map_path,
            model_name=model_name
        )
        return True
    except Exception as e:
        click.echo(f"Error during semantic index building: {e}", err=True)
        # Log the full traceback for debugging
        import traceback
        traceback.print_exc()
        return False

def generate_human_readable_index(vault_path: str, output_file: str, use_ai: bool = False):
    """Generates a human-readable index file of the Obsidian vault."""
    from ..vault_state import VaultState
    from ..utils.file_operations import write_file
    from ..utils.ai import generate_summary

    logger.info(f"Starting human-readable index generation for vault: {vault_path}")
    vault_state_instance = VaultState(vault_path)
    index_data = {}

    for file_path, metadata in vault_state_instance.files.items():
        if not metadata:
            logger.warning(f"Skipping file due to missing metadata: {file_path}")
            continue

        relative_path = metadata.relative_path
        logger.debug(f"Processing file for human index: {relative_path}")

        frontmatter = extract_frontmatter(metadata)

        summary = None
        if use_ai and metadata.content:
            logger.debug(f"Generating AI summary for: {relative_path}")
            try:
                summary = generate_summary(metadata.content)
            except Exception as e:
                logger.error(f"Failed to generate AI summary for {relative_path}: {e}")

        index_data[relative_path] = {
            "path": relative_path,
            "title": metadata.title,
            "frontmatter": frontmatter if frontmatter else {},
            "summary": summary,
            "tags": metadata.tags,
            "links": list(metadata.links),
            "backlinks": list(metadata.backlinks),
        }

    index_content = generate_index_content(index_data)

    if write_file(output_file, index_content):
        logger.info(f"Human-readable index file generated successfully: {output_file}")
    else:
        logger.error(f"Failed to write human-readable index file: {output_file}")

@index.command(name="create-md")
@click.option('--vault-path', default=None, help='Path to the Obsidian vault (overrides config).')
@click.option('--output', '-o', default='vault_index.md', help='Output file path for the index.')
@click.option('--ai', is_flag=True, help='Use AI to generate summaries for notes.')
def create_markdown_index(vault_path, output, ai):
    """Generate a human-readable Markdown index file for the vault."""
    if vault_path is None:
        vault_path_config = get_vault_path_from_config()
        if not vault_path_config:
            click.echo("Vault path not configured. Run 'olib config setup' or use --vault-path.", err=True)
            return
        vault_path = vault_path_config

    if not os.path.isdir(vault_path):
        click.echo(f"Error: Vault path '{vault_path}' not found or is not a directory.", err=True)
        return

    try:
        generate_human_readable_index(vault_path, output, ai)
        click.echo(f"Markdown index generated at: {output}")
    except Exception as e:
        click.echo(f"Error generating Markdown index: {e}", err=True)
        import traceback
        traceback.print_exc()

# Add other index commands if needed (e.g., status, clear)
# index.add_command(status) 