import os
from pathlib import Path
import glob

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
