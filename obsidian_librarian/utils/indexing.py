import os
import glob
import pickle
import numpy as np
import logging
from tqdm import tqdm  # For progress bar
from typing import Dict, Tuple, Optional, List # Added List
from pathlib import Path # Import Path
import time
from sentence_transformers import SentenceTransformer

# print("DEBUG: Importing obsidian_librarian.utils.indexing...") # Already removed

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
            # Save empty files to indicate indexing ran but found nothing
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
             np.save(embeddings_path, np.array([]))
             with open(file_map_path, 'wb') as f:
                 pickle.dump({}, f)
             return

        logger.info(f"Loading sentence transformer model '{model_name}'...")
        model = SentenceTransformer(model_name)

        logger.info(f"Generating embeddings for {len(documents)} documents...")
        start_time = time.time()
        embeddings = model.encode(documents, show_progress_bar=True)
        end_time = time.time()
        logger.info(f"Embedding generation took {end_time - start_time:.2f} seconds.")


        # --- Save embeddings and map ---
        logger.info(f"Saving embeddings to {embeddings_path}")
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

def load_index_data(embeddings_path: str, map_path: str) -> Tuple[Optional[np.ndarray], Optional[dict]]:
    """
    Loads the embeddings NumPy array and the file map dictionary from disk.

    Args:
        embeddings_path: Path to the embeddings NumPy file.
        map_path: Path to the file map dictionary.

    Returns:
        A tuple containing either a NumPy array or None, and either a dictionary or None.
    """
    embeddings = None
    file_map = None

    if os.path.exists(embeddings_path):
        try:
            embeddings = np.load(embeddings_path) # Use of np
            logging.info(f"Loaded embeddings from {embeddings_path} (Shape: {embeddings.shape})")
        except Exception as e:
            logging.error(f"Failed to load embeddings file {embeddings_path}: {e}")
            return None, None
    else:
        logging.error(f"Embeddings file not found: {embeddings_path}")
        return None, None # Indicate index needs building

    if os.path.exists(map_path):
        try:
            with open(map_path, 'rb') as f:
                file_map = pickle.load(f)
            logging.info(f"Loaded file map from {map_path} ({len(file_map)} entries)")
        except Exception as e:
            logging.error(f"Failed to load file map {map_path}: {e}")
            return embeddings, None # Return embeddings but indicate map error
    else:
        logging.error(f"File map not found: {map_path}")
        return embeddings, None # Return embeddings but indicate map error

    # Sanity check: number of embeddings should match number of files in map
    if embeddings is not None and file_map is not None and embeddings.shape[0] != len(file_map):
        logging.warning(f"Mismatch between number of embeddings ({embeddings.shape[0]}) and file map entries ({len(file_map)}). Index might be inconsistent.")
        # Decide how to handle this? For now, proceed but log warning.

    return embeddings, file_map

def find_similar_notes(prerequisites: list[str], embeddings: np.ndarray, file_map: dict, model) -> dict:
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
    from sklearn.metrics.pairwise import cosine_similarity # <-- Keep this lazy import
    results = {}
    if not prerequisites or embeddings is None or embeddings.shape[0] == 0 or not file_map:
        logging.warning("Cannot find similar notes: Prerequisites list is empty or index data is invalid/empty.")
        return results

    logging.info(f"Generating embeddings for {len(prerequisites)} prerequisites...")
    try:
        from sentence_transformers import SentenceTransformer # Already lazy-loaded
        prereq_embeddings = model.encode(prerequisites, convert_to_numpy=True, normalize_embeddings=True) # Uses np implicitly via model
    except Exception as e:
        logging.error(f"Failed to generate embeddings for prerequisites: {e}")
        return results

    logging.info("Calculating cosine similarities...")
    sim_matrix = cosine_similarity(prereq_embeddings, embeddings) # Use of cosine_similarity

    # For each prerequisite, find the note with the highest similarity
    for i, prereq in enumerate(prerequisites):
        if sim_matrix.shape[1] == 0:
             # Handle case where vault embeddings exist but are empty (e.g., only empty files)
             best_match_index = -1
             max_similarity = 0.0
        else:
            best_match_index = np.argmax(sim_matrix[i]) # Use of np
            max_similarity = sim_matrix[i, best_match_index]

        if best_match_index != -1 and best_match_index in file_map:
            best_match_filepath = file_map[best_match_index]
            results[prereq] = (best_match_filepath, float(max_similarity))
            # logging.debug(f"  '{prereq}' -> '{os.path.basename(best_match_filepath)}' (Score: {max_similarity:.4f})")
        else:
            results[prereq] = (None, 0.0) # Should not happen if index is consistent
            logging.warning(f"Could not find file path for best match index {best_match_index} for prerequisite '{prereq}'")

    return results

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