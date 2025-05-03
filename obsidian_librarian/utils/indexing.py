import os
import glob
import pickle
import logging
from tqdm import tqdm  # For progress bar
from typing import Dict, Tuple, Optional, List, Any # <-- Ensure Any is imported
from pathlib import Path # Import Path
import time
import numpy as np

# Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default model for embeddings
DEFAULT_MODEL = 'all-MiniLM-L6-v2'
DEFAULT_EMBEDDINGS_FILENAME = "vault_embeddings.npy" # Changed from .faiss
DEFAULT_MAP_FILENAME = "vault_file_map.pkl"

# --- Import vault_state functions ---
from .. import vault_state
# --- End import ---

logger = logging.getLogger(__name__)

def get_default_index_paths(config_dir):
    """Gets the default paths for the embeddings numpy file and map file within the config directory."""
    embeddings_path = os.path.join(config_dir, DEFAULT_EMBEDDINGS_FILENAME)
    map_path = os.path.join(config_dir, DEFAULT_MAP_FILENAME)
    return embeddings_path, map_path

def index_vault(
    db_path: Path,
    vault_path: Path, # Keep vault_path to read file content
    embeddings_path: Path,
    file_map_path: Path,
    model_name: str = DEFAULT_MODEL
):
    """
    Generates embeddings for all current markdown files found in the vault state DB
    and saves them along with a mapping file.

    Args:
        db_path: Path to the vault state SQLite database.
        vault_path: Path to the root of the Obsidian vault (for reading files).
        embeddings_path: Path to save the .npy embeddings file.
        file_map_path: Path to save the .pkl file map.
        model_name: Name of the Sentence Transformer model to use.
    """
    # --- Import heavy libraries here ---
    from sentence_transformers import SentenceTransformer
    # --- End import ---

    logger.info(f"Starting vault indexing using DB: {db_path}")
    logger.info(f"Reading files from vault: {vault_path}")
    logger.info(f"Using embedding model: {model_name}")

    try:
        # --- Get files from DB ---
        logger.debug(f"Querying database for files: {db_path}")
        files_to_index = vault_state.get_all_files_from_db(db_path) # Returns list of (rel_path, mtime, size)
        logger.info(f"Found {len(files_to_index)} markdown files in DB to index.")
        # --- End getting files from DB ---

        if not files_to_index:
            logger.info("No files found in DB to index. Saving empty index files.")
            # np is used here
            np.save(embeddings_path, np.array([]))
            with open(file_map_path, 'wb') as f:
                pickle.dump({}, f)
            return # Exit early

        # --- Prepare documents and paths ---
        documents = []
        relative_paths = []
        absolute_paths = [] # Store absolute paths for reading content

        for rel_path_str, _, _ in files_to_index:
            abs_path = vault_path / rel_path_str
            if abs_path.is_file():
                try:
                    # Read file content
                    content = abs_path.read_text(encoding='utf-8')
                    documents.append(content)
                    relative_paths.append(rel_path_str)
                    absolute_paths.append(abs_path) # Keep track if needed later
                except Exception as e:
                    logger.warning(f"Could not read or process file {abs_path}: {e}")
            else:
                 logger.warning(f"File listed in DB not found at {abs_path}. Skipping.")
        # --- End preparing documents ---


        if not documents:
             logger.warning("No documents could be read successfully. Saving empty index.")
             # np is used here
             np.save(embeddings_path, np.array([]))
             with open(file_map_path, 'wb') as f:
                 pickle.dump({}, f)
             return

        logger.info(f"Loading sentence transformer model '{model_name}'...")
        # SentenceTransformer is used here
        model = SentenceTransformer(model_name)

        logger.info(f"Generating embeddings for {len(documents)} documents...")
        start_time = time.time()
        # model.encode uses numpy implicitly
        embeddings = model.encode(documents, show_progress_bar=True)
        end_time = time.time()
        logger.info(f"Embedding generation took {end_time - start_time:.2f} seconds.")


        # --- Save embeddings and map ---
        logger.info(f"Saving embeddings to {embeddings_path}")
        # np is used here
        np.save(embeddings_path, embeddings)

        # Create mapping from index to relative file path
        file_map = {i: path for i, path in enumerate(relative_paths)}
        logger.info(f"Saving file map to {file_map_path}")
        with open(file_map_path, 'wb') as f:
            pickle.dump(file_map, f)
        # --- End saving ---

    except Exception as e:
        logger.error(f"Error during vault indexing: {e}", exc_info=True)
        # Re-raise the exception so the caller knows it failed
        raise

def load_index_data(embeddings_path: Path, file_map_path: Path) -> tuple[Optional[np.ndarray], Optional[dict]]:
    """Loads embeddings and file map from specified paths."""
    embeddings = None
    file_map = None

    if embeddings_path.exists():
        try:
            embeddings = np.load(embeddings_path)
        except Exception as e:
            logger.error(f"Error loading embeddings from {embeddings_path}: {e}")

    if file_map_path.exists():
        try:
            with open(file_map_path, 'rb') as f:
                file_map = pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading file map from {file_map_path}: {e}")

    return embeddings, file_map

def find_similar_notes(prerequisites: list[str], embeddings: Any, file_map: dict, model) -> dict: # Changed type hint for numpy
    """
    Finds the most similar notes in the vault for a given list of prerequisite concepts.

    Args:
        prerequisites: A list of prerequisite concept strings.
        embeddings: The NumPy array of vault note embeddings.
        file_map: The dictionary mapping embedding index to file path.
        model: The loaded SentenceTransformer model.

    Returns:
        A dictionary mapping each prerequisite concept to a tuple containing:
        (best_matching_filepath, similarity_score).
        Returns an empty dict if prerequisites list is empty or embeddings are invalid.
    """
    results = {}
    # np shape access is used here
    if not prerequisites or embeddings is None or embeddings.shape[0] == 0 or not file_map:
        logging.warning("Cannot find similar notes: Prerequisites list is empty or index data is invalid/empty.")
        return results

    logging.info(f"Generating embeddings for {len(prerequisites)} prerequisites...")
    try:
        # model.encode uses numpy implicitly
        prereq_embeddings = model.encode(prerequisites, convert_to_numpy=True, normalize_embeddings=True)
    except Exception as e:
        logging.error(f"Failed to generate embeddings for prerequisites: {e}")
        return results

    logging.info("Calculating cosine similarities...")
    # cosine_similarity uses numpy
    sim_matrix = cosine_similarity(prereq_embeddings, embeddings)

    # For each prerequisite, find the note with the highest similarity
    for i, prereq in enumerate(prerequisites):
        if sim_matrix.shape[1] == 0:
             # Handle case where vault embeddings exist but are empty (e.g., only empty files)
             best_match_index = -1
             max_similarity = 0.0
        else:
            # np is used here
            best_match_index = np.argmax(sim_matrix[i])
            max_similarity = sim_matrix[i, best_match_index]

        if best_match_index != -1 and best_match_index in file_map:
            best_match_filepath = file_map[best_match_index]
            results[prereq] = (best_match_filepath, float(max_similarity))
            # logging.debug(f"  '{prereq}' -> '{os.path.basename(best_match_filepath)}' (Score: {max_similarity:.4f})")
        else:
            results[prereq] = (None, 0.0) # Should not happen if index is consistent
            logging.warning(f"Could not find file path for best match index {best_match_index} for prerequisite '{prereq}'")

    return results

def extract_frontmatter(metadata: Any) -> Optional[Dict[str, Any]]:
    """
    Extracts frontmatter from a metadata object (duck typing).

    Args:
        metadata: An object expected to have a 'frontmatter' attribute.

    Returns:
        A dictionary containing the frontmatter, or None if no frontmatter exists
        or an error occurred (e.g., attribute missing).
    """
    # Use hasattr for safer access if the object might not have the attribute
    if hasattr(metadata, 'frontmatter') and metadata.frontmatter is not None:
        # Ensure it's a dictionary before returning, or handle other types if necessary
        if isinstance(metadata.frontmatter, dict):
             return metadata.frontmatter
        else:
             # Log a warning if frontmatter exists but isn't a dict (unexpected)
             logger.warning(f"Non-dictionary frontmatter found for object: {type(metadata.frontmatter)}")
             return None # Or return {} or handle as appropriate
    else:
        # logger.debug(f"No frontmatter attribute found or it is None for object.")
        return None

# Example usage (for testing purposes, can be removed later)
if __name__ == '__main__':
    # This part will only run when the script is executed directly
    # Replace with your actual vault path and desired save location
    test_vault_path = '/path/to/your/vault'
    test_config_dir = '/path/to/your/config/dir' # e.g., ~/.config/olib
    test_embeddings_path, test_map_path = get_default_index_paths(test_config_dir)

    if os.path.exists(test_vault_path) and os.path.exists(test_config_dir):
        print(f"Running test indexing for vault: {test_vault_path}")
        print(f"Saving embeddings to: {test_embeddings_path}")
        print(f"Saving map to: {test_map_path}")
        index_vault(test_vault_path, test_embeddings_path, test_map_path)
    else:
        print("Please update 'test_vault_path' and 'test_config_dir' in indexing.py for testing.") 