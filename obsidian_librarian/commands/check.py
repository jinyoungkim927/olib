import click
import os
import time
import json
from pathlib import Path
import logging
from collections import deque # For the queue

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
from obsidian_librarian.utils.file_operations import find_note_in_vault, read_note_content, get_popular_tags, get_all_tag_counts # Import the new function
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
@click.option('--min-tag-count', type=int, default=5, help='Minimum occurrences for a tag to be considered popular for suggestions.')
@click.option('--recursive', '-r', is_flag=True, default=False, help='Recursively check prerequisites for generated notes.')
@click.option('--min-tag-count', type=int, default=10, help='Minimum occurrences for a suggested tag to be kept (0 keeps all).') # Default 10
def prerequisites(note, content_threshold, title_threshold, llm_model, embedding_model, min_tag_count, recursive): # Added recursive, updated min_tag_count help
    """Analyzes a note to find prerequisite concepts and checks if they exist in the vault."""
    import numpy as np
    from sentence_transformers import SentenceTransformer
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

    # --- Data structures for recursion and diagram ---
    prereq_queue = deque()
    processed_topics = set() # Topics whose prerequisites have been checked
    dependency_graph = {} # key: parent topic, value: list of child prerequisite topics
    topic_status = {} # key: topic name, value: 'found', 'generated', 'missing', 'failed', 'skipped', 'original'
    initial_prerequisites = [] # Store the first level prerequisites

    # Set status for the original note
    original_note_topic = full_note_path.stem
    topic_status[original_note_topic] = 'original'
    dependency_graph[original_note_topic] = [] # Initialize children list

    # --- Get Initial Prerequisites from LLM ---
    click.echo("Requesting prerequisites from LLM...")
    prerequisites_list = get_prerequisites_from_llm(note_content, model_name=llm_model_to_use)

    if prerequisites_list is None:
        click.secho("Error: Failed to get prerequisites from the LLM.", fg="red")
        return
    if not prerequisites_list:
        click.echo("LLM did not identify any prerequisites for this note.")
        # Still print the (empty) tree at the end
    else:
        # Filter out the note's own name
        original_count = len(prerequisites_list)
        prerequisites_list = [
            prereq for prereq in prerequisites_list
            if prereq.lower() != note_basename_lower
        ]
        if len(prerequisites_list) < original_count:
             click.echo(f"Filtered out the note's own name ('{original_note_topic}') from prerequisites.")

        if not prerequisites_list:
            click.echo("No external prerequisites identified after filtering.")
            # Still print the (empty) tree at the end
        else:
            click.echo(f"Identified initial prerequisite concepts: {prerequisites_list}")
            initial_prerequisites = list(prerequisites_list) # Copy the list
            dependency_graph[original_note_topic] = initial_prerequisites # Add initial prereqs to graph
            prereq_queue.extend(initial_prerequisites) # Add initial prereqs to the queue

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
    if vault_stems:
        try:
            stem_embeddings = model.encode(vault_stems, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
            stem_embeddings_map = {stem_lower: emb for stem_lower, emb in zip(vault_stems_lower, stem_embeddings)}
        except Exception as e:
            click.secho(f"Error generating note title embeddings: {e}", fg="red")
            logger.exception("Stem embedding generation failed")
            # stem_embeddings_map remains empty, title check will be skipped
    else:
        click.echo("No note titles found in index to generate embeddings for.")

    # --- Get All Tag Counts (for filtering generated note tags) ---
    click.echo("Counting all tags in the vault...")
    all_vault_tag_counts = get_all_tag_counts(vault_path)
    click.echo(f"Found {len(all_vault_tag_counts)} unique tags.")

    # --- Get Popular Tags (for LLM suggestion context - optional but potentially helpful) ---
    # This uses the *old* min_tag_count logic, maybe rename the option or adjust
    popular_tags_for_llm = get_popular_tags(vault_path, min_count=5) # Use a fixed or separate threshold here if desired
    if popular_tags_for_llm:
        click.echo(f"Providing {len(popular_tags_for_llm)} popular tags to LLM for context.")
    else:
        click.echo("No popular tags found to provide context to LLM.")

    # --- Process Queue ---
    click.echo("\n--- Processing Prerequisites ---")
    # Instantiate FormatFixer outside the loop
    formatter = FormatFixer(verbose=False) # Don't need verbose output from formatter itself

    while prereq_queue:
        current_topic = prereq_queue.popleft()

        if current_topic in processed_topics:
            continue # Already processed this topic's prerequisites

        if current_topic in topic_status and topic_status[current_topic] != 'missing':
             # Already found or generated in a previous step, ensure it's processed
             processed_topics.add(current_topic)
             continue

        click.echo(f"\nChecking prerequisite: '{current_topic}'")
        topic_status[current_topic] = 'processing' # Mark as processing

        # --- Compare Prerequisite to Vault Notes ---
        prereq_lower = current_topic.lower()
        found = False
        match_details = {"type": "None", "score": 0.0, "path": ""}
        prereq_embedding = prereq_embeddings_map.get(current_topic) # Get embedding calculated earlier

        # 1. Check Exact Title Match
        try:
            exact_match_index = vault_stems_lower.index(prereq_lower)
            match_path_rel = vault_file_map[exact_match_index]
            match_path_abs = vault_path_obj / match_path_rel
            match_details = {"type": "Exact Title", "score": 1.0, "path": str(match_path_abs.relative_to(vault_path_obj))}
            found = True
            click.echo(f"  -> Found existing note (Exact Title): {match_details['path']}")
            topic_status[current_topic] = 'found'
        except ValueError:
            pass # Not found by exact title
        except Exception as e:
             logger.warning(f"Error during exact title check for '{current_topic}': {e}")


        # 2. Check Similar Title Match (if not found and embedding exists)
        if not found and prereq_embedding is not None and stem_embeddings_map:
            # Find the index corresponding to current_topic in the stem_embeddings_map
            # This is complex because the map was built only on initial prereqs.
            # Let's re-calculate similarity just for this one topic if needed.
            # OR: A better approach is to generate embeddings for ALL potential topics upfront.
            # For now, let's skip complex title similarity for recursive steps if embedding wasn't pre-calculated.
            # We rely on content similarity or exact match for recursive steps primarily.
            # TODO: Refactor embedding generation to handle dynamic topics if high-accuracy title match is needed recursively.
            pass # Simplified for now

        # 3. Check Similar Content Match (if not found and embedding exists)
        if not found and prereq_embedding is not None and vault_embeddings is not None and vault_embeddings.shape[0] > 0:
             # Similar issue: content_similarity_matrix was based on initial prereqs.
             # Let's calculate similarity for the current topic against all vault embeddings.
             try:
                 similarities = cosine_similarity(prereq_embedding.reshape(1, -1), vault_embeddings)[0]
                 best_content_match_idx = np.argmax(similarities)
                 content_similarity_score = similarities[best_content_match_idx]

                 if content_similarity_score >= content_threshold:
                     match_path_rel = vault_file_map[best_content_match_idx]
                     match_path_abs = vault_path_obj / match_path_rel
                     # Avoid matching the original note itself
                     if match_path_abs != full_note_path:
                         match_details = {"type": "Similar Content", "score": float(content_similarity_score), "path": str(match_path_abs.relative_to(vault_path_obj))}
                         found = True
                         click.echo(f"  -> Found existing note (Similar Content): {match_details['path']} (Score: {match_details['score']:.2f})")
                         topic_status[current_topic] = 'found'
             except Exception as e:
                 logger.warning(f"Error during content similarity check for '{current_topic}': {e}")


        # --- Handle Found or Missing ---
        if found:
            processed_topics.add(current_topic) # Mark as processed if found
            # Optionally, ask if user wants to check prerequisites for the *found* note
            # if recursive and click.confirm(f"Note for '{current_topic}' found. Check its prerequisites recursively?"):
            #    # Add logic here to read the found note and get its prerequisites
            #    pass
            continue # Move to the next item in the queue

        # --- Prerequisite is Missing: Offer to Generate ---
        click.echo(f"  -> No existing note found for '{current_topic}'.")
        topic_status[current_topic] = 'missing' # Mark as missing initially

        # --- Generate Note Logic ---
        if click.confirm(f"  -> Attempt to AI-generate placeholder note for '{current_topic}'?"):
            safe_filename = "".join(c for c in current_topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_filename:
                click.secho(f"  -> Skipping invalid topic name: '{current_topic}'", fg="yellow")
                topic_status[current_topic] = 'skipped'
                processed_topics.add(current_topic)
                continue

            note_path = vault_path_obj / f"{safe_filename}.md"

            if note_path.exists():
                click.echo(f"  -> Note already exists: '{note_path.relative_to(vault_path_obj)}'. Skipping generation.")
                # Update status if it was marked missing
                if topic_status.get(current_topic) == 'missing':
                     topic_status[current_topic] = 'found' # Treat as found if file exists
                processed_topics.add(current_topic)
                continue

            click.echo(f"    -> Requesting AI generation for '{current_topic}'...")
            generation_result = generate_note_content_from_topic(
                current_topic,
                llm_model_to_use,
                popular_tags=popular_tags_for_llm # Provide popular tags for context
            )

            generated_content = None
            suggested_tags = []
            if generation_result:
                generated_content, suggested_tags = generation_result

            if generated_content:
                click.echo(f"    -> Formatting generated content...")
                # Pass filename_base for potential title deduplication by fixer
                formatted_content = formatter.apply_all_fixes(generated_content, filename_base=safe_filename)

                # --- New Formatting Logic ---
                # 1. Remove duplicate title if fixer didn't catch it or if it's the specific `# Topic` format
                title_pattern = re.compile(r"^\s*#\s+" + re.escape(current_topic) + r"\s*\n(\n?)", re.IGNORECASE)
                match = title_pattern.match(formatted_content)
                if match:
                    # Remove the matched title line and the following blank line if present
                    formatted_content = formatted_content[match.end():]
                    click.echo("      -> Removed duplicate H1 title from generated content.")

                # 2. Filter suggested tags based on vault counts
                filtered_suggested_tags = []
                if min_tag_count > 0:
                    for tag in suggested_tags:
                        clean_tag = tag.strip('#')
                        if all_vault_tag_counts.get(clean_tag, 0) >= min_tag_count:
                            filtered_suggested_tags.append(clean_tag)
                        else:
                            click.echo(f"      -> Filtering out less common tag: #{clean_tag} (Count: {all_vault_tag_counts.get(clean_tag, 0)})")
                else:
                    filtered_suggested_tags = [tag.strip('#') for tag in suggested_tags] # Keep all if min_count is 0

                # 3. Combine tags (default + filtered suggested)
                final_tags = ["prerequisite", "generated"] + filtered_suggested_tags
                unique_tags = sorted(list(set(final_tags)))
                tags_line = " ".join([f"#{tag}" for tag in unique_tags])
                # --- End New Formatting Logic ---

                try:
                    with open(note_path, 'w', encoding='utf-8') as f:
                        # Write tags line (no "tags:" prefix)
                        f.write(tags_line + "\n")
                        # Write single newline separator
                        f.write("\n")
                        # Write the formatted (and potentially title-removed) content
                        f.write(formatted_content.strip() + "\n\n") # Ensure trailing newlines before footer
                        f.write("---\n*Note generated by Obsidian Librarian.*")

                    click.echo(f"    -> Successfully generated, formatted, and saved: '{note_path.relative_to(vault_path_obj)}'")
                    topic_status[current_topic] = 'generated'

                    # --- Recursive Step ---
                    if recursive:
                        if click.confirm(f"  -> Check prerequisites for the newly generated note '{current_topic}'?"):
                            click.echo(f"    -> Requesting prerequisites for '{current_topic}' from LLM...")
                            # Read the content we just wrote (excluding tags/footer for LLM)
                            new_note_content_for_llm = formatted_content.strip()
                            new_prereqs_list = get_prerequisites_from_llm(new_note_content_for_llm, model_name=llm_model_to_use)

                            if new_prereqs_list:
                                # Filter out self-reference
                                new_prereqs_list = [p for p in new_prereqs_list if p.lower() != current_topic.lower()]
                                click.echo(f"      -> Identified new prerequisites for '{current_topic}': {new_prereqs_list}")

                                if new_prereqs_list:
                                     # Add to graph
                                     dependency_graph[current_topic] = new_prereqs_list
                                     # Add to queue if not already processed or in queue
                                     newly_added_to_queue = 0
                                     for new_prereq in new_prereqs_list:
                                         if new_prereq not in processed_topics and new_prereq not in prereq_queue:
                                             # Check if embedding exists, if not, generate it?
                                             # For now, add to queue; comparison will handle missing embedding later.
                                             if new_prereq not in prereq_embeddings_map:
                                                  # TODO: Handle dynamic embedding generation if needed
                                                  logger.warning(f"Embedding for new prerequisite '{new_prereq}' not pre-calculated. Comparison might be limited.")
                                             prereq_queue.append(new_prereq)
                                             topic_status[new_prereq] = 'missing' # Assume missing until checked
                                             newly_added_to_queue += 1
                                     if newly_added_to_queue > 0:
                                         click.echo(f"      -> Added {newly_added_to_queue} new prerequisite(s) to the processing queue.")
                                else:
                                     click.echo(f"      -> No further external prerequisites identified for '{current_topic}'.")
                                     dependency_graph.setdefault(current_topic, []) # Ensure it has an entry even if empty
                            else:
                                click.echo(f"    -> LLM did not identify prerequisites for '{current_topic}'.")
                                dependency_graph.setdefault(current_topic, []) # Ensure it has an entry even if empty
                        else:
                             dependency_graph.setdefault(current_topic, []) # Ensure it has an entry even if empty

                    else: # Not recursive, ensure graph entry exists
                        dependency_graph.setdefault(current_topic, [])

                except Exception as e:
                    click.secho(f"    -> Error writing generated note '{note_path.name}': {e}", fg="red")
                    topic_status[current_topic] = 'failed'
                    # Clean up potentially partially written file
                    if note_path.exists():
                        try: os.remove(note_path)
                        except OSError: pass
            else:
                # Generation failed or returned empty
                click.secho(f"    -> AI generation failed for '{current_topic}'. Cannot create note.", fg="yellow")
                topic_status[current_topic] = 'failed' # Mark as failed if generation itself failed

        else: # User chose not to generate
             click.echo(f"  -> Skipping generation for '{current_topic}'.")
             topic_status[current_topic] = 'missing' # Remains missing
             dependency_graph.setdefault(current_topic, []) # Ensure it has an entry in the graph

        processed_topics.add(current_topic) # Mark as processed after handling

    # --- End Queue Processing ---

    # --- Report Results / ASCII Diagram ---
    click.echo("\n--- Prerequisite Analysis Complete ---")
    click.echo("Diagram Key: [✓] Found, [+] Generated, [?] Missing, [✗] Failed, [»] Skipped, [●] Original Note")

    # Build the final graph structure (ensure all topics have entries)
    all_topics_in_graph = set(dependency_graph.keys())
    for children in dependency_graph.values():
        all_topics_in_graph.update(children)
    for topic in all_topics_in_graph:
        dependency_graph.setdefault(topic, []) # Ensure all nodes exist as keys

    # Print the tree starting from the original note
    print_tree(dependency_graph, original_note_topic, topic_status)

    end_time = time.time()
    click.echo(f"\nAnalysis finished in {end_time - start_time:.2f} seconds.")

# Add other check subcommands if needed
# check.add_command(semantic)
# check.add_command(prereq) # Already decorated

# --- Helper function for ASCII tree ---
def print_tree(graph, topic, status, indent="", is_last=True, processed=None):
    """Prints an ASCII representation of the prerequisite tree."""
    if processed is None:
        processed = set()
    # Basic cycle detection/repeated node printing
    if topic in processed:
        connector = "└─>" if is_last else "├─>"
        click.echo(f"{indent}{connector} {topic} (*recursive link*)")
        return
    processed.add(topic)

    marker = "└─ " if is_last else "├─ "
    status_marker = {
        'found': '✓',      # Note exists in vault
        'generated': '+',  # Note was generated in this run
        'missing': '?',    # Note is missing and was not generated
        'processing': '…', # Currently being processed (shouldn't appear in final tree)
        'failed': '✗',     # Generation/saving failed
        'skipped': '»',    # Skipped (e.g., already exists)
        'original': '●'    # The starting note
    }.get(status.get(topic, 'missing'), '?') # Default to missing

    click.echo(f"{indent}{marker}[{status_marker}] {topic}")
    child_indent = indent + ("    " if is_last else "│   ")

    children = graph.get(topic, [])
    for i, child in enumerate(children):
        # Pass a copy of the processed set for each branch
        print_tree(graph, child, status, child_indent, i == len(children) - 1, processed.copy())
# --- End ASCII tree helper ---
