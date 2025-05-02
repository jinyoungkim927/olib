import click
import os
import time
import numpy as np
import pickle
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
import logging
from sklearn.metrics.pairwise import cosine_similarity

from obsidian_librarian.config import get_config_dir, get_vault_path_from_config, get_config
from obsidian_librarian.utils.ai import get_prerequisites_from_llm, generate_note_content_from_topic, DEFAULT_LLM_MODEL
from obsidian_librarian.utils.indexing import (
    get_default_index_paths,
    load_index_data,
    find_similar_notes,
    DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL # Use alias to avoid name clash
)
from obsidian_librarian.utils.file_operations import find_note_in_vault, read_note_content, get_popular_tags
from obsidian_librarian.utils.formatting import apply_standard_formatting
from .. import vault_state # Use relative import from parent package

# Default similarity threshold (needs tuning)
DEFAULT_SIMILARITY_THRESHOLD = 0.70
# --- Add new threshold for title similarity ---
DEFAULT_TITLE_SIMILARITY_THRESHOLD = 0.90 # Higher threshold for title matching
# --- End new threshold ---
# Cache file path
PREREQ_CACHE_FILE = get_config_dir() / "prereq_embeddings_cache.json" # <-- Define cache file path

# Configure logger for this module specifically if needed, or rely on root config
logger = logging.getLogger(__name__) # Use module-specific logger

# --- Helper function for caching ---
def load_prereq_cache() -> dict:
    """Loads the prerequisite embedding cache from a file."""
    if PREREQ_CACHE_FILE.exists():
        try:
            with open(PREREQ_CACHE_FILE, 'r') as f:
                # Load and convert lists back to numpy arrays
                cache_data = json.load(f)
                for key, value in cache_data.items():
                    cache_data[key] = np.array(value)
                return cache_data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load prerequisite cache: {e}. Starting fresh.")
            return {}
    return {}

def save_prereq_cache(cache: dict):
    """Saves the prerequisite embedding cache to a file."""
    try:
        with open(PREREQ_CACHE_FILE, 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            serializable_cache = {k: v.tolist() for k, v in cache.items()}
            json.dump(serializable_cache, f)
    except IOError as e:
        logger.warning(f"Could not save prerequisite cache: {e}")
# --- End Helper function ---

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
@click.option('--content-threshold', '-ct', type=click.FloatRange(0.0, 1.0), default=DEFAULT_SIMILARITY_THRESHOLD,
              help=f'Similarity threshold for content matching (0.0-1.0). Default: {DEFAULT_SIMILARITY_THRESHOLD}')
@click.option('--title-threshold', '-tt', type=click.FloatRange(0.0, 1.0), default=DEFAULT_TITLE_SIMILARITY_THRESHOLD,
              help=f'Similarity threshold for title matching (0.0-1.0). Default: {DEFAULT_TITLE_SIMILARITY_THRESHOLD}')
@click.option('--llm-model', default=None, help='Specify the LLM model to use (e.g., gpt-4o-mini). Uses default if not set.')
@click.option('--embedding-model', default=None, help='Embedding model for similarity checks. Uses config default.')
@click.option('--min-tag-count', type=int, default=5, help='Minimum occurrences for a tag to be considered popular for suggestions.')
def prerequisites(note, content_threshold, title_threshold, llm_model, embedding_model, min_tag_count):
    """Analyzes a note to find prerequisite concepts and checks if they exist in the vault."""
    start_time = time.time()
    config = get_config()

    # --- Determine models ---
    llm_model_to_use = llm_model or config.get('llm_model') or DEFAULT_LLM_MODEL # Use constant from ai.py
    embedding_model_name = embedding_model or config.get('embedding_model') or DEFAULT_EMBEDDING_MODEL # Use constant from indexing.py
    click.echo(f"Using LLM: {llm_model_to_use}, Embedding Model: {embedding_model_name}")

    # --- Get Vault Path ---
    vault_path = get_vault_path_from_config()
    if not vault_path:
        click.secho("Vault path not configured. Run 'olib config set vault_path /path/to/your/vault'", fg="red")
        return
    vault_path_obj = Path(vault_path)

    # --- Find Note ---
    click.echo(f"Searching for note '{note}' in vault: {vault_path}")
    full_note_path = find_note_in_vault(vault_path, note)
    if full_note_path is None:
        # find_note_in_vault logs errors/warnings
        click.secho(f"Could not find a unique note matching '{note}'.", fg="red")
        return

    note_basename_lower = full_note_path.stem.lower()

    # --- Use thresholds passed as arguments ---
    click.echo(f"Analyzing prerequisites for note: {full_note_path.relative_to(vault_path_obj)}")
    click.echo(f"Using Content Similarity Threshold: {content_threshold}")
    click.echo(f"Using Title Similarity Threshold: {title_threshold}")
    # --- End threshold usage ---

    # --- Read Note Content ---
    note_content = read_note_content(full_note_path)
    if note_content is None:
        click.secho(f"Error: Could not read content from note: {full_note_path}", fg="red")
        return
    if not note_content.strip():
        click.secho(f"Warning: Note '{full_note_path.name}' is empty. Prerequisite analysis may be inaccurate.", fg="yellow")
        # Decide if you want to proceed or exit for empty notes
        # return

    # --- Get Prerequisites from LLM ---
    click.echo("Requesting prerequisites from LLM...")
    prerequisites_list = get_prerequisites_from_llm(note_content, model_name=llm_model_to_use)

    if prerequisites_list is None:
        click.secho("Error: Failed to get prerequisites from the LLM.", fg="red")
        return
    if not prerequisites_list:
        click.echo("LLM did not identify any prerequisites for this note.")
        return

    # Filter out the note's own name from prerequisites (case-insensitive)
    original_count = len(prerequisites_list)
    prerequisites_list = [
        prereq for prereq in prerequisites_list
        if prereq.lower() != note_basename_lower
    ]
    if len(prerequisites_list) < original_count:
         click.echo(f"Filtered out the note's own name ('{Path(full_note_path).stem}') from prerequisites.")

    if not prerequisites_list:
        click.echo("No external prerequisites identified after filtering.")
        return

    click.echo(f"Identified prerequisite concepts: {prerequisites_list}")

    # --- Load Vault Index ---
    click.echo("Loading vault index data...")
    index_paths = get_default_index_paths(get_config_dir())
    try:
        # --- Access tuple elements by index ---
        embeddings_path = index_paths[0]
        file_map_path = index_paths[1]
        vault_embeddings, vault_file_map = load_index_data(
            embeddings_path,
            file_map_path
        )
        # --- End tuple access fix ---
        if vault_embeddings is None or vault_file_map is None or len(vault_file_map) == 0:
            click.secho("Vault index is empty or invalid. Please run 'olib index build'.", fg="red")
            return
        # Create reverse map: path -> index
        vault_path_to_index = {v: k for k, v in vault_file_map.items()}
        # --- Get note stems for title matching ---
        vault_stems = [Path(p).stem for p in vault_file_map.values()]
        vault_stems_lower = [s.lower() for s in vault_stems]
        # --- End get note stems ---

    except FileNotFoundError:
        click.secho(f"Vault index files not found. Please run 'olib index build'.", fg="red")
        return
    except Exception as e:
        click.secho(f"Error loading vault index: {e}", fg="red")
        logger.exception("Vault index loading failed")
        return

    # --- Load Embedding Model ---
    click.echo(f"Loading embedding model '{embedding_model_name}'...")
    try:
        # Ensure SentenceTransformer is imported here if not globally
        # from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(embedding_model_name)
    except Exception as e:
        click.secho(f"Error loading embedding model '{embedding_model_name}': {e}", fg="red")
        logger.exception("Embedding model loading failed")
        return

    # --- Load or Generate Prerequisite Embeddings (Cache) ---
    prereq_cache = load_prereq_cache()
    prereqs_to_encode = [p for p in prerequisites_list if p not in prereq_cache]
    prereq_embeddings_map = {p: prereq_cache[p] for p in prerequisites_list if p in prereq_cache}

    if prereqs_to_encode:
        click.echo(f"Generating embeddings for {len(prereqs_to_encode)} new prerequisite(s)...")
        try:
            new_embeddings = model.encode(prereqs_to_encode, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
            for prereq, embedding in zip(prereqs_to_encode, new_embeddings):
                prereq_embeddings_map[prereq] = embedding
                prereq_cache[prereq] = embedding # Update cache
            save_prereq_cache(prereq_cache) # Save updated cache
        except Exception as e:
            click.secho(f"Error generating prerequisite embeddings: {e}", fg="red")
            # Continue with cached embeddings if possible, or handle error appropriately
            # For now, we'll just log and potentially miss some comparisons
            logger.exception("Prerequisite embedding generation failed")

    # --- Generate Embeddings for Note Stems ---
    click.echo("Generating embeddings for note titles...")
    stem_embeddings_map = {} # Initialize as empty
    # --- Add check for empty stems ---
    if vault_stems:
        try:
            # Use original stems for encoding, map results back to lowercase stems if needed
            stem_embeddings = model.encode(vault_stems, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
            # Create a map from lowercase stem to its embedding
            stem_embeddings_map = {stem_lower: emb for stem_lower, emb in zip(vault_stems_lower, stem_embeddings)}
        except Exception as e:
            click.secho(f"Error generating note title embeddings: {e}", fg="red")
            logger.exception("Stem embedding generation failed")
            # stem_embeddings_map remains empty, title check will be skipped
    else:
        click.echo("No note titles found in index to generate embeddings for.")
    # --- End check ---

    # --- Get Popular Tags (before generation loop) ---
    popular_tags_for_llm = get_popular_tags(vault_path, min_count=min_tag_count)
    if popular_tags_for_llm:
        click.echo(f"Found {len(popular_tags_for_llm)} popular tags for potential suggestion.")
    else:
        click.echo("No popular tags found meeting the criteria for suggestions.")
    # --- End Get Popular Tags ---

    # --- Compare Prerequisites ---
    click.echo("Comparing prerequisites against vault notes...")
    results_details = []
    gaps_found = []

    for prereq in prerequisites_list:
        prereq_lower = prereq.lower()
        prereq_embedding = prereq_embeddings_map.get(prereq)

        if prereq_embedding is None:
            results_details.append({"prereq": prereq, "status": "NO_EMBEDDING"})
            gaps_found.append(prereq)
            continue

        # 1. Check for Exact Title Match (Case-Insensitive Stem)
        exact_match_paths = [
            vault_file_map[idx] for idx, stem_lower in enumerate(vault_stems_lower)
            if stem_lower == prereq_lower
        ]

        if exact_match_paths:
            results_details.append({
                "prereq": prereq,
                "status": "TITLE_MATCH",
                "matched_paths": exact_match_paths
            })
            continue # Found exact match, move to next prerequisite

        # 2. Check for Semantic Title Match (if embeddings available)
        if stem_embeddings_map:
            try:
                # Calculate similarities between prereq embedding and all stem embeddings
                similarities = cosine_similarity(
                    prereq_embedding.reshape(1, -1), # Reshape for single comparison
                    np.array(list(stem_embeddings_map.values())) # Convert map values to array
                )[0] # Get the first (only) row of similarities

                best_stem_match_idx = np.argmax(similarities)
                best_stem_score = similarities[best_stem_match_idx]
                best_matching_stem_lower = list(stem_embeddings_map.keys())[best_stem_match_idx]

                if best_stem_score >= title_threshold:
                    # Find original paths corresponding to this best matching lowercase stem
                    title_match_paths = [
                        vault_file_map[idx] for idx, stem_lower in enumerate(vault_stems_lower)
                        if stem_lower == best_matching_stem_lower
                    ]
                    results_details.append({
                        "prereq": prereq,
                        "status": "SEMANTIC_TITLE_MATCH",
                        "matched_paths": title_match_paths,
                        "score": best_stem_score
                    })
                    continue # Found close title match, move to next prerequisite

            except Exception as e:
                 click.secho(f"Error during semantic title check for '{prereq}': {e}", fg="yellow")
                 logger.warning(f"Semantic title check failed for {prereq}", exc_info=True)
                 # Proceed to content check

        # 3. Fallback: Semantic Content Match
        try:
            similarities = cosine_similarity(prereq_embedding.reshape(1, -1), vault_embeddings)[0]
            best_match_idx = np.argmax(similarities)
            best_score = similarities[best_match_idx]
            best_match_path = vault_file_map[best_match_idx]

            above_threshold = best_score >= content_threshold
            results_details.append({
                "prereq": prereq,
                "status": "SEMANTIC_CONTENT_CHECK",
                "top_score": best_score,
                "top_note": Path(best_match_path).name, # Show only filename
                "above_threshold": above_threshold
            })
            if not above_threshold:
                gaps_found.append(prereq)

        except Exception as e:
            click.secho(f"Error calculating content similarity for prerequisite '{prereq}': {e}", fg="red")
            logger.exception(f"Content similarity calculation failed for {prereq}")
            results_details.append({
                "prereq": prereq,
                "status": "ERROR",
                "error": str(e)
            })
            gaps_found.append(prereq)


    # --- Report Results ---
    click.echo("\n--- Prerequisite Analysis Results ---")
    if not results_details:
        click.echo("No prerequisites were processed.")
    else:
        for detail in results_details:
            prereq = detail['prereq']
            status = detail['status']

            if status == "TITLE_MATCH":
                paths_str = ", ".join([f"'{Path(p).name}'" for p in detail['matched_paths']]) # Show names only
                click.echo(click.style(f"[COVERED] - '{prereq}': Found direct title match in {paths_str}", fg="green"))
            # --- Add reporting for semantic title match ---
            elif status == "SEMANTIC_TITLE_MATCH":
                 paths_str = ", ".join([f"'{Path(p).name}'" for p in detail['matched_paths']])
                 score = detail['score']
                 click.echo(click.style(f"[COVERED] - '{prereq}': Found semantically similar title in {paths_str} (Score: {score:.2f} >= {title_threshold:.2f})", fg="cyan")) # Use cyan for distinction
            # --- End semantic title match reporting ---
            elif status == "SEMANTIC_CONTENT_CHECK":
                top_score = detail['top_score']
                top_note = detail['top_note']
                if detail['above_threshold']:
                    click.echo(click.style(f"[COVERED] - '{prereq}': Found semantically similar content in '{top_note}' (Score: {top_score:.2f} >= {content_threshold:.2f})", fg="green"))
                else:
                    # This is now the final GAP indicator
                    click.echo(click.style(f"[GAP?]    - '{prereq}': No exact/similar title or content match above thresholds. (Highest content similarity: {top_score:.2f} with '{top_note}')", fg="yellow"))
            elif status == "NO_EMBEDDING":
                 click.echo(click.style(f"[ERROR]   - '{prereq}': Could not generate embedding for prerequisite.", fg="red"))
            elif status == "ERROR":
                 click.echo(click.style(f"[ERROR]   - '{prereq}': Error during similarity check: {detail['error']}", fg="red"))

    click.echo("--- End of Report ---")

    if gaps_found:
        click.echo(f"{len(gaps_found)} potential prerequisite gap(s) identified (marked [GAP?] or [ERROR]).")

        # --- Modify prompt and note creation logic ---
        if click.confirm(f"\nDo you want to attempt to AI-generate placeholder notes for the {len(gaps_found)} identified gap(s)?"):
            vault_path_obj = Path(vault_path)
            created_count = 0
            stub_count = 0
            skipped_count = 0
            failed_count = 0

            for gap in gaps_found:
                safe_filename = "".join(c for c in gap if c.isalnum() or c in (' ', '-', '_')).rstrip()
                if not safe_filename:
                    click.secho(f"Skipping invalid prerequisite name: '{gap}'", fg="yellow")
                    skipped_count += 1
                    continue

                note_path = vault_path_obj / f"{safe_filename}.md"

                if note_path.exists():
                    click.echo(f"Note already exists: '{note_path.relative_to(vault_path_obj)}'. Skipping.")
                    skipped_count += 1
                    continue

                # --- Add specific feedback before API call ---
                click.echo(f" -> Requesting AI generation for '{gap}'...")
                # --- End feedback ---

                # --- Call the generation function ---
                # --- Pass popular tags to generation function ---
                generation_result = generate_note_content_from_topic(gap, llm_model_to_use, popular_tags=popular_tags_for_llm)
                # --- End pass popular tags ---
                generated_content = None
                suggested_tags = []
                if generation_result:
                    generated_content, suggested_tags = generation_result
                # --- End modification ---

                # --- Add feedback after API call (or failure) ---
                if generated_content is None:
                     # Error/Timeout message is handled within generate_note_content_from_topic now
                     # We just proceed to create the stub or handle file error
                     pass # Continue to the try/except block below
                else:
                    # --- Apply formatting ---
                    click.echo(f"    -> Formatting generated content for '{gap}'...")
                    formatted_content = apply_standard_formatting(generated_content)
                    # --- End formatting ---

                try:
                    with open(note_path, 'w') as f:
                        f.write(f"# {gap}\n\n") # Add title
                        # --- Combine default and suggested tags ---
                        all_tags = ["#prerequisite", "#generated"] + [f"#{tag.strip('#')}" for tag in suggested_tags if tag] # Ensure tags start with #
                        unique_tags = sorted(list(set(all_tags))) # Remove duplicates and sort
                        f.write(f"tags: {' '.join(unique_tags)}\n\n")
                        # --- End tag combination ---

                        if generated_content: # Check original content presence before writing formatted
                            # --- Write formatted content ---
                            f.write(formatted_content)
                            # --- End write formatted content ---
                            f.write("\n\n---\n*Note generated by Obsidian Librarian.*") # Add footer
                            # --- Modify success message slightly ---
                            click.echo(f"    -> Successfully generated, formatted, and saved: '{note_path.relative_to(vault_path_obj)}'")
                            # --- End modification ---
                            created_count += 1
                        else:
                            # Fallback to stub if generation failed or returned empty
                            click.secho(f"    -> AI generation failed for '{gap}'. Creating stub.", fg="yellow")
                            f.write(f"This note was automatically created as a placeholder for the prerequisite concept '{gap}'.\n")
                            f.write("*(Content generation failed)*\n")
                            stub_count += 1
                except Exception as e: # Catch unexpected errors during file writing
                     click.secho(f"Unexpected error writing note '{note_path.name}': {e}", fg="red")
                     failed_count += 1
                     # Attempt to remove partially created file if error occurred during write
                     if note_path.exists():
                         try:
                             os.remove(note_path)
                         except OSError:
                             pass # Ignore error during cleanup

            click.echo(f"\nFinished processing gaps:")
            if created_count > 0: click.echo(f"  - {created_count} notes generated successfully.")
            if stub_count > 0: click.echo(f"  - {stub_count} stub notes created (generation failed).")
            if skipped_count > 0: click.echo(f"  - {skipped_count} skipped (invalid name or already exists).")
            if failed_count > 0: click.echo(f"  - {failed_count} failed due to file writing errors.")

        else:
            click.echo("Okay, not generating any notes.")
        # --- End modification ---

    else:
        click.echo("All identified prerequisites appear to be covered by existing notes (by exact title, similar title, or similar content).")

    end_time = time.time()
    click.echo(f"Analysis completed in {end_time - start_time:.2f} seconds.")

# Add other check subcommands if needed
# check.add_command(semantic)
# check.add_command(prereq) # Already decorated
