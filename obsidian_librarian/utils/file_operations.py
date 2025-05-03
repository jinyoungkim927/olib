import os
from pathlib import Path
import glob
import re
import logging
from typing import Optional, List, Dict, Tuple
from collections import Counter

# Configure logging if needed for this module
# logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# --- Constants ---
# --- Define MAX_FILENAME_LENGTH here ---
MAX_FILENAME_LENGTH = 200 # Example limit, adjust as needed
# --- End Define ---

# --- Define characters invalid in filenames across common OS ---
# We will REMOVE these characters.
# We will specifically ALLOW spaces now.
INVALID_FILENAME_CHARS = r'[\\/:\*\?"<>\|]' # Removed space from this set

# --- Define characters to simply replace with an underscore ---
# This can include characters that might be technically valid but problematic
# (e.g., leading/trailing dots, excessive consecutive spaces/underscores if desired)
# For now, let's just focus on removing the truly invalid ones.
# CHARS_TO_REPLACE_WITH_UNDERSCORE = r'\s+' # Example: Replace whitespace sequences (we are keeping single spaces now)

# --- Helper Functions ---

def get_markdown_files(directory_path: str) -> list[str]:
    """
    Recursively finds all markdown (.md) files in a given directory.

    Args:
        directory_path: The path to the directory to search.

    Returns:
        A list of absolute paths to the markdown files found.
    """
    if not os.path.isdir(directory_path):
        return []

    # Use glob to find all .md files recursively
    pattern = os.path.join(directory_path, "**", "*.md")
    md_files = glob.glob(pattern, recursive=True)

    return md_files

# Add the count_words function here
def count_words(text: str) -> int:
    """Counts words in a string, simple split by whitespace."""
    if not text:
        return 0
    return len(text.split())

# You can add other file-related utility functions here 

def sanitize_filename(name: str, replacement: str = '_') -> str:
    """
    Sanitizes a string to be used as a valid filename.
    Removes invalid characters and optionally replaces whitespace.

    Args:
        name: The original string name.
        replacement: The character to use for replacing invalid sequences (currently not used for spaces).

    Returns:
        A sanitized string suitable for use as a filename.
    """
    if not name:
        return ""

    # 1. Remove truly invalid characters
    #    Characters like / \ : * ? " < > | are problematic on most OS
    sanitized = re.sub(INVALID_FILENAME_CHARS, '', name)

    # 2. Handle leading/trailing whitespace and dots (often problematic)
    sanitized = sanitized.strip().strip('.')

    # 3. Collapse multiple consecutive spaces into one (optional, but good practice)
    sanitized = re.sub(r'\s+', ' ', sanitized)

    # --- Removed: Replacing spaces with underscores ---
    # # 4. Replace remaining whitespace (now just single spaces) with underscore
    # #    Comment this out to allow spaces in filenames
    # # sanitized = re.sub(r'\s', replacement, sanitized)
    # --- End Removed ---

    # 5. Ensure the filename isn't empty after sanitization
    if not sanitized:
        # Maybe return a default name or raise an error?
        # For now, let's return a single underscore.
        logger.warning(f"Filename '{name}' became empty after sanitization.")
        return "_"

    # 6. Limit length (optional, but good practice for some filesystems)
    # max_len = 250 # Example limit
    # if len(sanitized) > max_len:
    #     # Find the last space within the limit to avoid cutting words
    #     ext = ""
    #     base = sanitized
    #     if '.' in sanitized:
    #         parts = sanitized.rsplit('.', 1)
    #         base = parts[0]
    #         ext = '.' + parts[1]
    #
    #     if len(base) > max_len - len(ext):
    #         cutoff_point = base[:max_len - len(ext)].rfind(' ')
    #         if cutoff_point != -1 and cutoff_point > max_len // 2: # Cut at space if reasonable
    #              base = base[:cutoff_point]
    #         else: # Otherwise just truncate
    #              base = base[:max_len - len(ext)]
    #         sanitized = base.strip() + ext
    #     logger.info(f"Truncated sanitized filename to {max_len} chars: {sanitized}")


    return sanitized

def read_note_content(file_path: Path) -> Optional[str]:
    """
    Reads the content of a note file.

    Args:
        file_path: The absolute Path object of the note file.

    Returns:
        The content of the file as a string, or None if an error occurs
        (e.g., file not found, permission error, decoding error).
    """
    try:
        # Ensure we are working with an absolute path
        if not file_path.is_absolute():
             logging.warning(f"Received relative path in read_note_content: {file_path}. Attempting to read anyway.")
             # Depending on context, you might want to resolve it or raise an error

        if not file_path.is_file():
            logging.error(f"File not found or is not a regular file: {file_path}")
            return None

        # Try reading with UTF-8 first, fallback to latin-1 if needed
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            logging.warning(f"UTF-8 decoding failed for {file_path}. Trying latin-1.")
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return content
            except Exception as e:
                logging.error(f"Failed to read file {file_path} even with latin-1: {e}")
                return None
        except Exception as e: # Catch other potential errors like PermissionError
            logging.error(f"Error reading file {file_path}: {e}")
            return None

    except Exception as e: # Catch errors related to path handling itself
        logging.error(f"Unexpected error handling path {file_path} in read_note_content: {e}")
        return None

def find_note_in_vault(vault_path: str, note_identifier: str) -> Optional[Path]:
    """
    Finds a unique markdown note (.md) within the vault based on its name or relative path.

    Args:
        vault_path: The absolute path to the Obsidian vault.
        note_identifier: The name of the note (e.g., "My Note") or its relative
                         path within the vault (e.g., "Folder/My Note.md").
                         The .md extension is optional.

    Returns:
        An absolute Path object to the unique note file if found, otherwise None.
        Returns None if multiple ambiguous matches are found or if no .md file matches.
    """
    vault_path_obj = Path(vault_path)
    if not vault_path_obj.is_dir():
        logging.error(f"Vault path does not exist or is not a directory: {vault_path}")
        return None

    # Normalize the identifier: remove .md extension if present for base name matching
    # Keep the original identifier for direct path checking
    original_identifier = note_identifier
    if note_identifier.lower().endswith(".md"):
        base_name = note_identifier[:-3]
    else:
        base_name = note_identifier

    potential_matches: List[Path] = []

    # 1. Check direct relative paths (both with and without .md)
    # Ensure they are files and end with .md (case-insensitive)
    potential_direct_path_no_ext = vault_path_obj / original_identifier
    potential_direct_path_with_ext = vault_path_obj / f"{original_identifier}.md" # Handles case where identifier has no ext

    if potential_direct_path_no_ext.is_file() and potential_direct_path_no_ext.suffix.lower() == ".md":
         potential_matches.append(potential_direct_path_no_ext.resolve())

    # Check the path with .md added, only if it's different from the first check
    # and avoid adding duplicates if original_identifier already ended with .md
    if potential_direct_path_with_ext != potential_direct_path_no_ext and \
       potential_direct_path_with_ext.is_file() and \
       potential_direct_path_with_ext.suffix.lower() == ".md":
        potential_matches.append(potential_direct_path_with_ext.resolve())


    # 2. Perform recursive search by base name (case-insensitive stem)
    # This helps find notes even if the direct path wasn't exact (e.g., case difference)
    # or if only the base name was provided.
    try:
        for item in vault_path_obj.rglob(f"{base_name}.md"): # More efficient glob
             if item.is_file() and item.stem.lower() == base_name.lower(): # Double check stem match case-insensitively
                 potential_matches.append(item.resolve())
        # Add a second glob for case variations if the first didn't catch everything
        # (less efficient but covers more edge cases like file systems preserving case in glob)
        for item in vault_path_obj.rglob(f"*"):
             if item.is_file() and item.suffix.lower() == ".md" and item.stem.lower() == base_name.lower():
                 potential_matches.append(item.resolve()) # Resolve ensures absolute path

    except Exception as e:
         logging.error(f"Error during recursive search in vault: {e}")
         # Decide if we should return None or continue with only direct matches


    # 3. Deduplicate and check results
    unique_matches = list(set(potential_matches))

    if len(unique_matches) == 0:
        return None
    elif len(unique_matches) == 1:
        found_path = unique_matches[0]
        return found_path
    else: # len > 1
        # --- Refined Ambiguity Check ---
        # Check if all paths point to the same actual file using inode comparison
        try:
            first_inode = os.stat(unique_matches[0]).st_ino
            all_same_inode = True
            for match in unique_matches[1:]:
                # Check if file exists before stating to avoid errors on dangling paths
                if not match.exists() or os.stat(match).st_ino != first_inode:
                    all_same_inode = False
                    break

            if all_same_inode:
                # If all point to the same file, it's not truly ambiguous.
                # Return the first one found (or potentially try to find one with preferred casing).
                found_path = unique_matches[0]
                return found_path
            else:
                # Genuinely ambiguous match (different files)
                logging.warning(f"Multiple different markdown notes found matching identifier '{original_identifier}':")
                relative_matches = sorted([match.relative_to(vault_path_obj) for match in unique_matches if match.exists()]) # Show existing matches
                for rel_match in relative_matches:
                    logging.warning(f"  - {rel_match}")
                logging.error("Ambiguous match. Please provide a more specific path.")
                return None
        except OSError as e:
            logging.error(f"Error checking file status during ambiguity resolution: {e}")
            # Fallback to reporting ambiguity if stat fails
            logging.warning(f"Multiple markdown notes found matching identifier '{original_identifier}' (could not resolve ambiguity):")
            relative_matches = sorted([match.relative_to(vault_path_obj) for match in unique_matches if match.exists()])
            for rel_match in relative_matches:
                 logging.warning(f"  - {rel_match}")
            logging.error("Ambiguous match. Please provide a more specific path.")
            return None
        # --- End Refined Ambiguity Check ---

# --- Add function to find popular tags ---
def get_popular_tags(vault_path: str, min_count: int = 5) -> List[str]:
    """
    Finds tags that appear frequently across notes in the vault.

    Args:
        vault_path: The absolute path to the Obsidian vault.
        min_count: The minimum number of times a tag must appear to be considered popular.

    Returns:
        A list of popular tag names (without the '#').
    """
    tag_counts = get_all_tag_counts(vault_path) # Use the new function
    popular_tags = [tag for tag, count in tag_counts.items() if count >= min_count]
    return popular_tags

def get_all_tag_counts(vault_path: str) -> Dict[str, int]:
    """
    Counts occurrences of all tags across all markdown notes in the vault.
    Looks for tags within the first ~5 lines or ~100 characters.

    Args:
        vault_path: The absolute path to the Obsidian vault.

    Returns:
        A dictionary mapping tag names (without '#') to their counts.
    """
    tag_counts = {}
    vault_path_obj = Path(vault_path)
    md_files = list(vault_path_obj.rglob("*.md"))
    # Regex to find hashtags: starts with #, followed by one or more alphanumeric, /, -, _
    # It avoids matching things like #123 or #---
    tag_regex = re.compile(r'#([a-zA-Z0-9][a-zA-Z0-9\/_-]*)')

    for file_path in md_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read the first few lines or characters to optimize
                content_start = ""
                for i, line in enumerate(f):
                    content_start += line
                    if i >= 4 or len(content_start) > 150: # Check first 5 lines or ~150 chars
                        break

                # Find all tags in the beginning part
                found_tags = tag_regex.findall(content_start)
                for tag in found_tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        except Exception as e:
            logger.warning(f"Could not read or parse tags from {file_path.name}: {e}")

    return tag_counts

# --- End function ---
