import click
import os
import time
import json
from pathlib import Path
import logging
from collections import deque # For the queue
import re # <-- Add this import
# --- Add datetime for timestamp ---
from datetime import datetime
# --- End Add ---
# --- Add torch import for device detection ---
try:
    import torch
except ImportError:
    torch = None
# --- End Add ---

# For Git history (optional)
try:
    import git
except ImportError:
    git = None

from obsidian_librarian.config import get_config_dir, get_vault_path_from_config, get_config
from obsidian_librarian.utils.ai import get_prerequisites_from_llm, generate_note_content_from_topic, DEFAULT_LLM_MODEL
from obsidian_librarian.utils.indexing import (
    get_default_index_paths,
    load_index_data,
    find_similar_notes,
    DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL # Use alias to avoid name clash
)
from obsidian_librarian.utils.file_operations import find_note_in_vault, read_note_content, get_popular_tags, get_all_tag_counts, sanitize_filename # Import sanitize_filename
from .. import vault_state # Use relative import from parent package
# --- Import FormatFixer ---
from ..commands.utilities.format_fixer import FormatFixer
# --- End import ---

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
    import numpy as np
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
    import numpy as np
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
@click.option('--recursive', '-r', is_flag=True, default=False, help='Recursively check prerequisites for generated notes.')
@click.option('--min-tag-count', type=int, default=10, help='Minimum occurrences for a suggested tag to be kept (0 keeps all).') # Default 10
def prerequisites(note, content_threshold, title_threshold, llm_model, embedding_model, min_tag_count, recursive):
    """Analyzes a note to find prerequisite concepts and checks if they exist in the vault."""
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity # <-- Moved import here
    start_time = time.time()
    config = get_config()
    formatter = FormatFixer(verbose=False) # Initialize formatter early

    # --- Determine models ---
    llm_model_to_use = llm_model or config.get('llm_model') or DEFAULT_LLM_MODEL
    embedding_model_name = embedding_model or config.get('embedding_model') or DEFAULT_EMBEDDING_MODEL
    # --- Remove LLM/Embedding model echo ---
    # click.echo(f"Using LLM: {llm_model_to_use}, Embedding Model: {embedding_model_name}")
    # --- End Remove ---
    if "mini" in llm_model_to_use:
        click.secho("Warning: Using a 'mini' LLM model...", fg="yellow") # Keep warning

    # --- Get Vault Path ---
    vault_path = get_vault_path_from_config()
    if not vault_path:
        click.secho("Vault path not configured. Run 'olib config set vault_path /path/to/your/vault'", fg="red")
        return
    vault_path_obj = Path(vault_path)

    # --- Find Note or Offer to Generate ---
    # --- Remove Searching echo ---
    # click.echo(f"Searching for note '{note}' in vault: {vault_path}")
    # --- End Remove ---
    full_note_path = find_note_in_vault(vault_path, note)
    note_content = None
    original_note_topic = note # Use the input name initially

    if full_note_path is None:
        click.secho(f"Could not find a unique note matching '{note}'.", fg="red")
        if click.confirm(f"Attempt to AI-generate a foundational note for '{note}' to start the analysis?"):
            original_note_topic = note # Keep the original name for context
            safe_filename = sanitize_filename(original_note_topic)
            if not safe_filename:
                 click.secho(f"Cannot generate note for invalid topic name: '{original_note_topic}'", fg="red")
                 return

            full_note_path = vault_path_obj / f"{safe_filename}.md"

            if full_note_path.exists():
                 click.echo(f"Note '{full_note_path.relative_to(vault_path_obj)}' already exists. Using existing note.")
                 note_content = read_note_content(full_note_path)
                 if note_content is None:
                     click.secho(f"Error: Could not read content from existing note: {full_note_path}", fg="red")
                     return
            else:
                click.echo(f"Requesting AI generation for foundational note '{original_note_topic}'...")
                generation_result = generate_note_content_from_topic(
                    original_note_topic,
                    llm_model_to_use,
                    # popular_tags=popular_tags_for_llm # Maybe skip tags for foundational?
                )
                generated_content = None
                if generation_result:
                    generated_content, _ = generation_result # Ignore tags for foundational

                if generated_content:
                    formatted_content = formatter.apply_all_fixes(generated_content, filename_base=safe_filename)

                    # --- Modify Regex for Title Removal ---
                    # Use \s* after # to handle cases with zero or more spaces
                    title_pattern = re.compile(r"^\s*#\s*" + re.escape(original_note_topic) + r"\s*\n(\n?)", re.IGNORECASE)
                    # --- End Regex Modification ---

                    match = title_pattern.match(formatted_content)
                    if match:
                        logger.debug(f"Removing LLM-generated title from content for '{original_note_topic}'")
                        formatted_content = formatted_content[match.end():]
                    else:
                        logger.debug(f"Did not find LLM-generated title pattern to remove for '{original_note_topic}'")

                    try:
                        with open(full_note_path, 'w', encoding='utf-8') as f:
                            f.write(f"# {original_note_topic}\n\n") # Add title explicitly
                            f.write(f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write("Tags: #generated #prerequisite\n\n") # Changed #foundational to #prerequisite
                            f.write(formatted_content.strip() + "\n\n")
                            f.write("---\n*Note generated by Obsidian Librarian.*")
                        click.secho(f"Successfully generated foundational note: '{full_note_path.relative_to(vault_path_obj)}'", fg="green")
                        note_content = formatted_content # Use the generated content for analysis
                    except Exception as e:
                        click.secho(f"Error writing generated foundational note '{full_note_path.name}': {e}", fg="red")
                        return # Exit if foundational note fails
                else:
                    click.secho(f"Failed to generate foundational note for '{original_note_topic}'. Exiting.", fg="red")
                    return
        else:
            click.echo("Cannot proceed without the starting note.") # Keep info
            return
    else:
        # Note was found, read its content
        original_note_topic = full_note_path.stem # Use the actual stem if found
        note_content = read_note_content(full_note_path)
        if note_content is None:
            click.secho(f"Error: Could not read content from note: {full_note_path}", fg="red")
            return

    # --- Content Check ---
    if not note_content or not note_content.strip():
        click.secho(f"Warning: Note '{full_note_path.name}' is empty or could not be read. Prerequisite analysis may be inaccurate.", fg="yellow")
        # Decide if you want to proceed or exit for empty notes

    # --- Data structures ---
    # Queue now stores tuples: (topic_to_process, parent_topic_name)
    prereq_queue = deque()
    # Set stores topics already processed *in this run* to avoid redundant LLM calls/loops
    processed_topics_this_run = set()
    dependency_graph = {original_note_topic: []} # Initialize graph with original topic
    topic_status = {original_note_topic: 'original'} # Status map

    # --- Get Initial Prerequisites ---
    # --- Remove Requesting echo ---
    # click.echo(f"Requesting initial prerequisites from LLM...")
    # --- End Remove ---
    prerequisites_list = get_prerequisites_from_llm(
        note_content,
        model_name=llm_model_to_use,
        original_topic=original_note_topic # Pass original topic context
    )

    if prerequisites_list is None:
        click.secho("Error: Failed to get prerequisites from the LLM.", fg="red")
        return

    # Filter out the note's own name (case-insensitive)
    original_count = len(prerequisites_list)
    prerequisites_list = [
        prereq for prereq in prerequisites_list
        if prereq.lower() != original_note_topic.lower() # Case-insensitive compare
    ]
    if len(prerequisites_list) < original_count:
         click.echo(f"Filtered out the note's own name ('{original_note_topic}') from prerequisites.")

    if not prerequisites_list:
        click.echo("LLM did not identify any external prerequisites for this note.")
    else:
        click.echo(f"Identified initial prerequisite concepts: {prerequisites_list}")
        dependency_graph[original_note_topic] = list(prerequisites_list) # Add to graph
        # Add initial prerequisites to queue with the original note as parent
        for prereq in prerequisites_list:
            prereq_queue.append((prereq, original_note_topic))
            topic_status[prereq] = 'missing' # Assume missing initially

    # --- Load Vault Index ---
    # --- Remove Loading echo ---
    # click.echo("Loading vault index data...")
    # --- End Remove ---
    index_paths = get_default_index_paths(get_config_dir())
    try:
        embeddings_path = index_paths[0]
        file_map_path = index_paths[1]
        # --- Add Debug Logging ---
        logger.debug(f"Type of embeddings_path before load: {type(embeddings_path)}, Value: {embeddings_path}")
        logger.debug(f"Type of file_map_path before load: {type(file_map_path)}, Value: {file_map_path}")
        # --- End Debug Logging ---
        vault_embeddings, vault_file_map = load_index_data(Path(embeddings_path), Path(file_map_path))
        if vault_embeddings is None or vault_file_map is None or len(vault_file_map) == 0:
            click.secho("Vault index is empty or invalid. Please run 'olib index build'.", fg="red")
            return
        vault_path_to_index = {v: k for k, v in vault_file_map.items()}
        # --- Ensure stems are correctly generated ---
        vault_stems = [Path(p).stem for p in vault_file_map.values()]
        vault_stems_lower = [s.lower() for s in vault_stems]
        logger.debug(f"Loaded {len(vault_stems_lower)} note stems for title matching.")
        # --- End Ensure ---
    except FileNotFoundError:
        click.secho(f"Vault index files not found. Please run 'olib index build'.", fg="red")
        return
    except Exception as e:
        click.secho(f"Error loading vault index: {e}", fg="red"); logger.exception("..."); return

    # --- Load Embedding Model with Device Detection ---
    # --- Remove Loading echo ---
    # click.echo(f"Loading embedding model '{embedding_model_name}'...")
    # --- End Remove ---
    device = 'cpu' # Default
    if torch:
        if torch.cuda.is_available():
            device = 'cuda'
        # Check for MPS (Apple Silicon GPU) availability and support
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
             # Potentially add version checks or specific model compatibility checks if needed
             # For now, assume if available, we try to use it.
             device = 'mps'
        # Add other accelerators like 'xpu' if relevant in the future
    else:
        click.secho("Warning: PyTorch not found. Cannot detect GPU/MPS. Using CPU for embeddings.", fg="yellow")

    try:
        model = SentenceTransformer(embedding_model_name, device=device)
        # --- Remove Using device echo ---
        # click.echo(f"Using device: {model.device}")
        # --- End Remove ---
    except Exception as e:
        click.secho(f"Error loading embedding model '{embedding_model_name}' (tried device: {device}): {e}", fg="red") # Keep error
        logger.exception("Embedding model loading failed")
        return
    # --- End Model Loading ---

    # --- Load/Generate Prerequisite Embeddings (Cache) ---
    # ... (cache loading logic remains the same) ...
    prereq_cache = load_prereq_cache()
    prereq_embeddings_map = {p: prereq_cache[p] for p in prerequisites_list if p in prereq_cache}
    initial_prereqs_to_encode = [p for p in prerequisites_list if p not in prereq_cache]
    if initial_prereqs_to_encode:
        # ... (encode initial missing, update cache, save cache) ...
        click.echo(f"Generating embeddings for {len(initial_prereqs_to_encode)} initial prerequisite(s)...") # Keep this
        try:
            new_embeddings = model.encode(initial_prereqs_to_encode, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
            for prereq, embedding in zip(initial_prereqs_to_encode, new_embeddings):
                prereq_embeddings_map[prereq] = embedding
                prereq_cache[prereq] = embedding
            save_prereq_cache(prereq_cache)
        except Exception as e: click.secho(f"Error generating initial prerequisite embeddings: {e}", fg="red"); logger.exception("...")


    # --- Generate Embeddings for Note Stems ---
    click.echo("Generating embeddings for note titles...") # Keep this
    stem_embeddings_map = {}
    stem_embeddings = None
    if vault_stems:
        try:
            stem_embeddings = model.encode(vault_stems, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
            stem_embeddings_map = {stem_lower: emb for stem_lower, emb in zip(vault_stems_lower, stem_embeddings)}
        except Exception as e: click.secho(f"Error generating note title embeddings: {e}", fg="red"); logger.exception("...")
    else: click.echo("No note titles found in index to generate embeddings for.")


    # --- Get All Tag Counts & Popular Tags ---
    # --- Remove Counting echo ---
    # click.echo("Counting all tags in the vault...")
    # --- End Remove ---
    all_vault_tag_counts = get_all_tag_counts(vault_path)
    # --- Remove Found echo ---
    # click.echo(f"Found {len(all_vault_tag_counts)} unique tags.")
    # --- End Remove ---
    popular_tags_for_llm = get_popular_tags(vault_path, min_count=5)
    # --- Remove Providing echo ---
    # if popular_tags_for_llm:
    #     click.echo(f"Providing {len(popular_tags_for_llm)} popular tags to LLM for context.")
    # else:
    #     click.echo("No popular tags found to provide context to LLM.")
    # --- End Remove ---


    # --- Process Queue ---
    click.echo("\n--- Processing Prerequisites ---") # Keep section header
    processed_topics_this_run = set() # Topics processed in this specific run
    dependency_graph = {}
    topic_status = {}
    # Add original note to graph and status
    dependency_graph[original_note_topic] = prerequisites_list
    topic_status[original_note_topic] = 'original'
    # Queue stores tuples: (topic_to_check, parent_topic_name)
    prereq_queue = deque([(prereq, original_note_topic) for prereq in prerequisites_list])

    while prereq_queue:
        current_topic, parent_topic = prereq_queue.popleft()

        # --- Skip if already processed in this run ---
        if current_topic in processed_topics_this_run:
            # Ensure graph link still exists if skipped here
            if parent_topic:
                 parent_children = dependency_graph.setdefault(parent_topic, [])
                 if current_topic not in parent_children:
                     parent_children.append(current_topic)
            dependency_graph.setdefault(current_topic, []) # Ensure node exists
            logger.debug(f"Skipping '{current_topic}' as it was already processed in this run.")
            continue
        # --- End Skip ---

        click.echo(f"\nChecking prerequisite: '{current_topic}' (for '{parent_topic}')")
        topic_status[current_topic] = 'processing' # Mark as processing

        prereq_lower = current_topic.lower()
        found = False
        match_details = {"type": "None", "score": 0.0, "path": ""}

        # --- Get prerequisite embedding (ensure it exists) ---
        prereq_embedding = prereq_embeddings_map.get(current_topic)
        if prereq_embedding is None and current_topic in prereq_cache:
             prereq_embedding = prereq_cache[current_topic]
             prereq_embeddings_map[current_topic] = prereq_embedding

        # --- Start Similarity Checks ---

        # 1. Check Exact Title Match (Case-Insensitive)
        try:
            # Ensure vault_stems_lower is populated
            if vault_stems_lower:
                exact_match_index = vault_stems_lower.index(prereq_lower)
                match_path_rel = vault_file_map[exact_match_index]
                match_path_abs = vault_path_obj / match_path_rel
                match_details = {"type": "Exact Title", "score": 1.0, "path": str(match_path_abs.relative_to(vault_path_obj))}
                found = True
                click.secho(f"  -> Found existing note (Exact Title): {match_details['path']}", fg="green")
                topic_status[current_topic] = 'found'
            else:
                 logger.debug("Vault stems list is empty, cannot perform exact title match.")
        except ValueError:
            logger.debug(f"No exact title match found for '{prereq_lower}'.")
            pass # Not found by exact title
        except Exception as e:
             logger.warning(f"Error during exact title check for '{current_topic}': {e}")

        # 2. Check Similar Title Match (Only if not found by exact title and embeddings exist)
        if not found and prereq_embedding is not None and stem_embeddings is not None and stem_embeddings.shape[0] > 0:
            try:
                title_similarities = cosine_similarity(prereq_embedding.reshape(1, -1), stem_embeddings)[0]
                best_title_match_idx = np.argmax(title_similarities)
                title_similarity_score = title_similarities[best_title_match_idx]
                logger.debug(f"Highest title similarity score for '{current_topic}': {title_similarity_score:.4f}") # Log score

                if title_similarity_score >= title_threshold:
                    match_path_rel = vault_file_map[best_title_match_idx]
                    match_path_abs = vault_path_obj / match_path_rel
                    # Avoid matching the original note itself by path (important!)
                    if full_note_path and match_path_abs != full_note_path:
                        match_details = {"type": "Similar Title", "score": float(title_similarity_score), "path": str(match_path_abs.relative_to(vault_path_obj))}
                        found = True
                        click.secho(f"  -> Found existing note (Similar Title): {match_details['path']} (Score: {match_details['score']:.2f})", fg="yellow")
                        topic_status[current_topic] = 'found'
                    else:
                         logger.debug(f"Similar title match for '{current_topic}' pointed to the original note '{full_note_path.name if full_note_path else 'N/A'}', skipping.")
                else:
                     logger.debug(f"Title similarity score {title_similarity_score:.4f} below threshold {title_threshold}")

            except Exception as e:
                logger.warning(f"Error during title similarity check for '{current_topic}': {e}")

        # 3. Check Similar Content Match (Only if not found by previous methods and embeddings exist)
        if not found and prereq_embedding is not None and vault_embeddings is not None and vault_embeddings.shape[0] > 0:
             try:
                 content_similarities = cosine_similarity(prereq_embedding.reshape(1, -1), vault_embeddings)[0]
                 best_content_match_idx = np.argmax(content_similarities)
                 content_similarity_score = content_similarities[best_content_match_idx]
                 logger.debug(f"Highest content similarity score for '{current_topic}': {content_similarity_score:.4f}") # Log score

                 if content_similarity_score >= content_threshold:
                     match_path_rel = vault_file_map[best_content_match_idx]
                     match_path_abs = vault_path_obj / match_path_rel
                     # Avoid matching the original note itself
                     if full_note_path and match_path_abs != full_note_path:
                         match_details = {"type": "Similar Content", "score": float(content_similarity_score), "path": str(match_path_abs.relative_to(vault_path_obj))}
                         found = True
                         click.secho(f"  -> Found existing note (Similar Content): {match_details['path']} (Score: {match_details['score']:.2f})", fg="yellow")
                         topic_status[current_topic] = 'found'
                     else:
                         logger.debug(f"Similar content match for '{current_topic}' pointed to the original note '{full_note_path.name if full_note_path else 'N/A'}', skipping.")
                 else:
                      logger.debug(f"Content similarity score {content_similarity_score:.4f} below threshold {content_threshold}")

             except Exception as e:
                 logger.warning(f"Error during content similarity check for '{current_topic}': {e}")

        # --- End Similarity Checks ---

        # --- Handle Found or Missing ---
        if found:
            processed_topics_this_run.add(current_topic) # Mark as processed
            # Ensure graph links are correct
            if parent_topic:
                 parent_children = dependency_graph.setdefault(parent_topic, [])
                 if current_topic not in parent_children:
                     parent_children.append(current_topic)
            dependency_graph.setdefault(current_topic, []) # Ensure node exists
            continue # Move to the next item in the queue

        # --- Prerequisite is Missing: Offer to Generate ---
        click.echo(f"  -> No existing note found matching '{current_topic}'.")
        topic_status[current_topic] = 'missing'

        if click.confirm(f"  -> Attempt to AI-generate placeholder note for '{current_topic}'?"):
            safe_filename = sanitize_filename(current_topic)
            if not safe_filename:
                click.secho(f"  -> Skipping invalid topic name: '{current_topic}'", fg="yellow")
                topic_status[current_topic] = 'skipped'
                processed_topics_this_run.add(current_topic)
                if parent_topic: dependency_graph.setdefault(parent_topic, []).append(current_topic)
                dependency_graph.setdefault(current_topic, [])
                continue

            note_path = vault_path_obj / f"{safe_filename}.md"

            if note_path.exists():
                click.echo(f"  -> Note already exists: '{note_path.relative_to(vault_path_obj)}'. Skipping generation.")
                topic_status[current_topic] = 'found' # Treat as found
                processed_topics_this_run.add(current_topic)
                if parent_topic: dependency_graph.setdefault(parent_topic, []).append(current_topic)
                dependency_graph.setdefault(current_topic, [])
                continue

            click.echo(f"    -> Requesting AI generation for '{current_topic}'...")
            generation_result = generate_note_content_from_topic(
                current_topic,
                llm_model_to_use,
                popular_tags=popular_tags_for_llm,
                original_topic=original_note_topic
            )
            generated_content, suggested_tags = (None, []) if generation_result is None else generation_result

            if generated_content:
                formatted_content = formatter.apply_all_fixes(generated_content, filename_base=safe_filename)
                title_pattern = re.compile(r"^\s*#\s*" + re.escape(current_topic) + r"\s*\n(\n?)", re.IGNORECASE)
                match = title_pattern.match(formatted_content)
                if match: formatted_content = formatted_content[match.end():]

                # --- Re-apply tag filtering logic ---
                filtered_suggested_tags = []
                if min_tag_count > 0:
                    for tag in suggested_tags:
                        clean_tag = tag.strip('#')
                        if all_vault_tag_counts.get(clean_tag, 0) >= min_tag_count:
                            filtered_suggested_tags.append(clean_tag)
                        else:
                            logger.debug(f"Filtering out less common tag: #{clean_tag} (Count: {all_vault_tag_counts.get(clean_tag, 0)})")
                else:
                    filtered_suggested_tags = [tag.strip('#') for tag in suggested_tags]

                final_tags = ["prerequisite", "generated"] + filtered_suggested_tags
                tags_line = " ".join([f"#{tag}" for tag in sorted(list(set(final_tags)))])
                # --- End tag filtering ---

                try:
                    with open(note_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {current_topic}\n\n")
                        f.write(f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        if parent_topic: f.write(f"Generated from: [[{parent_topic}]]\n")
                        f.write(f"Tags: {tags_line}\n\n")
                        f.write(formatted_content.strip() + "\n\n")
                        f.write("---\n*Note generated by Obsidian Librarian.*")

                    click.echo(f"    -> Successfully generated, formatted, and saved: '{note_path.relative_to(vault_path_obj)}'") # Keep success
                    topic_status[current_topic] = 'generated'
                    if parent_topic: dependency_graph.setdefault(parent_topic, []).append(current_topic)
                    dependency_graph.setdefault(current_topic, [])

                    # --- Recursive Step ---
                    if recursive:
                        if click.confirm(f"  -> Recursively check prerequisites for the newly generated note '{current_topic}'?"):
                             click.echo(f"    -> Requesting prerequisites for '{current_topic}' from LLM...")
                             new_prereqs_list = get_prerequisites_from_llm(
                                 formatted_content.strip(),
                                 model_name=llm_model_to_use,
                                 original_topic=original_note_topic
                             )
                             if new_prereqs_list:
                                 new_prereqs_list = [p for p in new_prereqs_list if p.lower() != current_topic.lower()]
                                 click.echo(f"      -> Identified new prerequisites for '{current_topic}': {new_prereqs_list}")
                                 if new_prereqs_list:
                                     dependency_graph[current_topic] = new_prereqs_list # Set children
                                     newly_added_to_queue = 0
                                     prereqs_needing_new_embeddings = []
                                     for new_prereq in new_prereqs_list:
                                         if new_prereq not in processed_topics_this_run and new_prereq not in [item[0] for item in prereq_queue]:
                                             prereq_queue.append((new_prereq, current_topic))
                                             topic_status[new_prereq] = 'missing'
                                             newly_added_to_queue += 1
                                             if new_prereq not in prereq_embeddings_map and new_prereq not in prereq_cache:
                                                 prereqs_needing_new_embeddings.append(new_prereq)
                                             elif new_prereq in prereq_cache and new_prereq not in prereq_embeddings_map:
                                                  prereq_embeddings_map[new_prereq] = prereq_cache[new_prereq]
                                     if prereqs_needing_new_embeddings:
                                         click.echo(f"      -> Added {newly_added_to_queue} new prerequisite(s) to the processing queue.")
                                 else: click.echo(f"      -> No further external prerequisites identified for '{current_topic}'.")
                             else: click.echo(f"    -> LLM did not identify prerequisites for '{current_topic}'.")
                        else: click.echo(f"    -> Skipping recursive check for '{current_topic}'.")
                    # Ensure node exists even if not recursive or no children found
                    dependency_graph.setdefault(current_topic, [])

                except Exception as e:
                    click.secho(f"    -> Error writing generated note '{note_path.name}': {e}", fg="red")
                    topic_status[current_topic] = 'failed'
                    # --- Fix Syntax Error: Properly structured try-except for cleanup ---
                    if note_path.exists():
                        try:
                            os.remove(note_path)
                        except OSError:
                            pass # Ignore errors during cleanup removal
                    # --- End Fix ---
                    if parent_topic: dependency_graph.setdefault(parent_topic, []).append(current_topic)
                    dependency_graph.setdefault(current_topic, [])
            else:
                click.secho(f"    -> AI generation failed for '{current_topic}'. Cannot create note.", fg="yellow")
                topic_status[current_topic] = 'failed'
                if parent_topic: dependency_graph.setdefault(parent_topic, []).append(current_topic)
                dependency_graph.setdefault(current_topic, [])

        else: # User chose not to generate
             click.echo(f"  -> Skipping generation for '{current_topic}'.")
             topic_status[current_topic] = 'missing'
             if parent_topic: dependency_graph.setdefault(parent_topic, []).append(current_topic)
             dependency_graph.setdefault(current_topic, [])

        # --- Mark as processed for this run ---
        processed_topics_this_run.add(current_topic)

    # --- End Queue Processing ---

    # --- Report Results / ASCII Diagram ---
    click.echo("\n--- Prerequisite Analysis Complete ---") # Keep section header
    click.echo("Diagram Key: [✓] Found (Green), [+] Generated (Yellow), [?] Missing (Red), [✗] Failed (Red), [»] Skipped (Grey), [●] Original (Blue)") # Keep key
    print_tree_top_down_colored(dependency_graph, original_note_topic, topic_status, prefix="") # Keep diagram

    end_time = time.time()
    click.echo(f"\nAnalysis finished in {end_time - start_time:.2f} seconds.") # Keep summary

# Add other check subcommands if needed
# check.add_command(semantic)
# check.add_command(prereq) # Already decorated

# --- Helper function for ASCII tree (Modified to use run-specific visited set) ---
def print_tree_top_down_colored(graph, topic, status, prefix="", is_last=True, visited_for_print=None):
    """Prints a top-down, colored ASCII representation of the prerequisite tree."""
    if visited_for_print is None:
        visited_for_print = set() # Use a set specific to this print call

    # Check if this node is already being printed higher up in this specific branch
    if topic in visited_for_print:
        connector = "└─>" if is_last else "├─>"
        # Indicate cycle in printout
        click.secho(f"{prefix}{connector} [{status.get(topic, '?')[0]}] {topic} (*Cycle Detected*)", fg="magenta")
        return

    # Add to visited set for this print branch *before* processing children
    visited_for_print.add(topic)

    current_status_code = status.get(topic, 'missing')
    status_marker_map = {
        'found': ('✓', "green"), 'generated': ('+', "yellow"), 'missing': ('?', "red"),
        'failed': ('✗', "red"), 'skipped': ('»', "bright_black"), 'original': ('●', "blue"),
        'processing': ('…', "magenta") # Should ideally not appear in final print
    }
    marker, color = status_marker_map.get(current_status_code, ('?', "red"))

    # Determine connectors
    if prefix == "": connector_str, node_prefix = "", ""
    else: connector_str, node_prefix = ("└─ " if is_last else "├─ "), prefix

    click.secho(f"{node_prefix}{connector_str}[{marker}] {topic}", fg=color)

    child_prefix = prefix + ("    " if is_last else "│   ")
    children = graph.get(topic, [])

    # --- Ensure children are unique before printing to avoid visual clutter from graph structure ---
    unique_children = []
    seen_children = set()
    for child in children:
        if child not in seen_children:
            unique_children.append(child)
            seen_children.add(child)
    # --- End Ensure Unique ---


    for i, child in enumerate(unique_children): # Iterate unique children
        is_last_child = (i == len(unique_children) - 1)
        # Pass a copy of the visited set for each branch to correctly detect cycles within that branch
        print_tree_top_down_colored(graph, child, status, child_prefix, is_last_child, visited_for_print.copy())

    # Remove from visited set *after* processing children (backtracking) - though copy prevents issues
    # visited_for_print.remove(topic) # Not strictly needed if using copy() in recursive call

# --- End ASCII tree helper ---
