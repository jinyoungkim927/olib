import click
import os
import logging
import numpy as np
from pathlib import Path

from obsidian_librarian.config import get_config_dir, get_vault_path_from_config
from obsidian_librarian.utils.ai import get_prerequisites_from_llm
from obsidian_librarian.utils.indexing import (
    get_default_index_paths,
    load_index_data,
    find_similar_notes,
    DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL # Use alias to avoid name clash
)
from obsidian_librarian.utils.file_operations import find_note_in_vault

# Default similarity threshold (needs tuning)
DEFAULT_SIMILARITY_THRESHOLD = 0.70

@click.group()
def check():
    """Run various checks on notes.

    Check notes for accuracy, conceptual prerequisites, and detect private content.
    """
    pass # Group command doesn't do anything by itself

@check.command()
def accuracy(): # Placeholder for future accuracy check
    """Check note accuracy and completeness (Not Implemented)."""
    click.echo("Accuracy checking... (Not Implemented)")

@check.command()
def private(): # Placeholder for future private content check
    """Detect private/sensitive content (Not Implemented)."""
    click.echo("Private content detection... (Not Implemented)")

@check.command()
@click.option('--note', '-n', required=True,
              help='Name or relative path of the markdown note to analyze (e.g., "My Note" or "Folder/My Note.md").')
@click.option('--threshold', '-t', type=click.FloatRange(0.0, 1.0), default=DEFAULT_SIMILARITY_THRESHOLD,
              help=f'Similarity threshold to flag a gap (0.0-1.0). Default: {DEFAULT_SIMILARITY_THRESHOLD}')
@click.option('--llm-model', default=None, help='Specify the LLM model to use (e.g., gpt-4o-mini). Uses default if not set.')
@click.option('--embedding-model', default=DEFAULT_EMBEDDING_MODEL, help=f'Specify the embedding model used for indexing. Default: {DEFAULT_EMBEDDING_MODEL}')
def prerequisites(note, threshold, llm_model, embedding_model):
    """Check for potential conceptual prerequisite gaps for a given note."""

    # --- Find the note path ---
    vault_path = get_vault_path_from_config()
    if not vault_path:
        click.secho("Error: Vault path not configured. Run 'olib config setup' first.", fg="red")
        return

    click.echo(f"Searching for note '{note}' in vault: {vault_path}")
    full_note_path = find_note_in_vault(vault_path, note)

    if not full_note_path:
        click.secho(f"Error: Could not find a unique note matching '{note}' in the vault.", fg="red")
        click.echo("Please check the name/path or provide a more specific identifier.")
        return
    # --- End find note path ---

    # Get the base name of the note without extension for filtering
    note_basename = Path(full_note_path).stem

    # Use full_note_path from now on
    click.echo(f"Analyzing prerequisites for note: {full_note_path}") # Use the resolved path
    click.echo(f"Using similarity threshold: {threshold}")

    # --- 1. Load Note Content ---
    try:
        # Use full_note_path here
        with open(full_note_path, 'r', encoding='utf-8') as f:
            note_content = f.read()
        if not note_content.strip():
            # Use full_note_path in error message
            click.secho(f"Error: Note file '{full_note_path}' is empty.", fg="red")
            return
    except Exception as e:
        # Use full_note_path in error message
        click.secho(f"Error reading note file '{full_note_path}': {e}", fg="red")
        return

    # --- 2. Get Prerequisites from LLM ---
    llm_model_to_use = llm_model if llm_model else None # Pass None to use default in function
    click.echo(f"Requesting prerequisites from LLM ({llm_model_to_use or 'default'})...")
    raw_prereqs = get_prerequisites_from_llm(note_content, model_name=llm_model_to_use) if llm_model_to_use else get_prerequisites_from_llm(note_content)

    if raw_prereqs is None:
        click.secho("Failed to get prerequisites from LLM. Check logs and OPENAI_API_KEY.", fg="red")
        return

    # --- Filter out the note's own name (case-insensitive) ---
    prereqs = [p for p in raw_prereqs if p.lower() != note_basename.lower()]
    # --- End filtering ---

    if not prereqs: # Check if the list is empty *after* filtering
        click.secho("LLM did not identify any prerequisites for this note (or only identified the note itself).", fg="yellow")
        return

    # Use the filtered list 'prereqs' from now on
    click.echo(f"Identified prerequisite concepts (filtered): {prereqs}") # Show filtered list

    # --- 3. Load Index Data ---
    config_dir = get_config_dir()
    embeddings_path, map_path = get_default_index_paths(config_dir)
    click.echo("Loading vault index data...")
    embeddings, file_map = load_index_data(embeddings_path, map_path)

    if embeddings is None or file_map is None:
        click.secho(f"Failed to load index data. Please run 'olib index build' first.", fg="red")
        click.echo(f"Looked for: {embeddings_path} and {map_path}")
        return

    # --- 4. Load Embedding Model ---
    click.echo(f"Loading embedding model '{embedding_model}'... (This may take a moment on first run)")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(embedding_model)
    except Exception as e:
        click.secho(f"Failed to load sentence transformer model '{embedding_model}': {e}", fg="red")
        return

    # --- 5. Find Similar Notes ---    
    click.echo("Comparing prerequisites against vault notes...")
    similarity_results = find_similar_notes(prereqs, embeddings, file_map, model)

    if not similarity_results:
        click.secho("Failed to perform similarity analysis. Check logs.", fg="red")
        return

    # --- 6. Report Results ---    
    click.echo("\n--- Prerequisite Analysis Results ---")
    gaps_found = 0
    for prereq, (match_path, score) in similarity_results.items():
        if score < threshold:
            gaps_found += 1
            # Use os.path.basename for cleaner output even if match_path is None
            match_filename = os.path.basename(match_path) if match_path else 'N/A'
            click.secho(f"[GAP?] - '{prereq}': No note found above threshold {threshold:.2f}. (Highest similarity: {score:.2f} with '{match_filename}')", fg="yellow")
        else:
            # Use os.path.basename for cleaner output
            match_filename = os.path.basename(match_path) if match_path else 'N/A' # Should have match_path here
            click.secho(f"[OK]   - '{prereq}': Likely covered by '{match_filename}' (Similarity: {score:.2f})", fg="green")

    click.echo("--- End of Report ---")
    if gaps_found == 0:
        click.echo("No significant prerequisite gaps identified based on the current index and threshold.")
    else:
        click.echo(f"{gaps_found} potential prerequisite gap(s) identified. Consider creating or expanding notes on these topics.")

# Add other check subcommands if needed
# check.add_command(semantic)
# check.add_command(prereq) # Already decorated
