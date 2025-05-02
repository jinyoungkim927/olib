import os
from pathlib import Path
import glob
import re
import logging
from typing import Optional, List

# Configure logging if needed for this module
# logging.basicConfig(level=logging.INFO)

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

def sanitize_filename(name: str) -> str:
    """Removes or replaces characters invalid for filenames."""
    if not isinstance(name, str):
        name = str(name) # Ensure input is a string

    # Remove characters invalid in Windows/Linux/MacOS filenames
    # Keep alphanumeric, spaces, hyphens, underscores, periods (for extension)
    # Remove others. Adjust the regex as needed for your preferences.
    name = re.sub(r'[<>:"/\\|?*]', '', name) # Basic invalid chars

    # Replace sequences of whitespace with a single underscore
    name = re.sub(r'\s+', '_', name)

    # Optional: Replace other potentially problematic chars like apostrophes, commas etc.
    # name = re.sub(r"[',;()&]", '', name)

    # Remove leading/trailing underscores/spaces/periods
    name = name.strip('_. ')

    # Prevent names that are just dots or empty
    if not name or name. Lstrip('.') == '':
        return "untitled_note"

    # Limit length (optional, be careful not to cut off extensions if used elsewhere)
    # max_len = 100
    # name = name[:max_len]

    return name

def find_note_in_vault(vault_path: str, note_identifier: str) -> Optional[str]:
    """
    Searches recursively within the vault for a note matching the identifier.

    Args:
        vault_path: The absolute path to the Obsidian vault.
        note_identifier: The filename (e.g., "My Note.md") or base name (e.g., "My Note")
                         or a relative path within the vault (e.g., "Folder/My Note.md").

    Returns:
        The absolute path to the found note, or None if not found or ambiguous.
        Prints a warning if multiple matches are found and returns the first one.
    """
    if not vault_path or not os.path.isdir(vault_path):
        logging.error(f"Invalid vault path provided for searching: {vault_path}")
        return None

    p_vault = Path(vault_path)
    potential_matches = []

    # Case 1: Identifier might be a direct relative path
    potential_path = p_vault / note_identifier
    if potential_path.is_file() and potential_path.suffix.lower() == '.md':
        potential_matches.append(str(potential_path.resolve()))

    # Case 2: Identifier is likely a filename or base name, search recursively
    if not potential_matches:
        search_term = note_identifier
        if not search_term.lower().endswith('.md'):
            search_term += ".md"

        # Use rglob for recursive search
        # Note: This might be slow in very large vaults. Consider index-based search later if needed.
        found_files = list(p_vault.rglob(f"**/{search_term}")) # Search for exact match first

        if not found_files and note_identifier.lower().endswith('.md'):
             # If user provided .md and exact match failed, try without it? Less common.
             pass
        elif not found_files:
             # If user didn't provide .md and exact match failed, maybe try partial?
             # For now, let's stick to exact match (with added .md if needed)
             pass


        potential_matches.extend([str(f.resolve()) for f in found_files])


    if len(potential_matches) == 0:
        logging.info(f"No note found matching identifier '{note_identifier}' in vault '{vault_path}'.")
        return None
    elif len(potential_matches) == 1:
        logging.info(f"Found unique note match: {potential_matches[0]}")
        return potential_matches[0]
    else:
        # Ambiguous match
        logging.warning(f"Multiple notes found matching identifier '{note_identifier}':")
        for match in potential_matches:
            logging.warning(f"  - {match}")
        logging.warning("Using the first match found. Please provide a more specific path if this is incorrect.")
        return potential_matches[0] # Return the first match found
