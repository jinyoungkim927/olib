import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# --- Remove Formatting Functions ---
# The logic from format_math_blocks, format_code_blocks, and apply_standard_formatting
# has been moved into the FormatFixer class in obsidian_librarian/commands/utilities/format_fixer.py

# --- Keep Index Generation Function ---
def generate_index_content(index_data: Dict[str, Dict[str, Any]]) -> str:
    """
    Generates a Markdown formatted string from the index data.

    Args:
        index_data: A dictionary where keys are relative file paths and values
                    are dictionaries containing metadata like title, summary, etc.

    Returns:
        A Markdown formatted string representing the vault index.
    """
    lines = ["# Index of Vault\n"]
    if not index_data:
        lines.append("No markdown files found or processed.")
        return "\n".join(lines)

    # Sort by relative path for consistent output
    sorted_paths = sorted(index_data.keys())

    for rel_path in sorted_paths:
        data = index_data[rel_path]
        title = data.get("title", rel_path) # Use path as fallback title
        lines.append(f"## [[{title}]]") # Link using title
        lines.append(f"*Path: `{rel_path}`*")

        # Add frontmatter if present
        frontmatter = data.get("frontmatter")
        if frontmatter:
            lines.append("\n**Frontmatter:**")
            fm_lines = []
            for key, value in frontmatter.items():
                fm_lines.append(f"  - `{key}`: `{value}`")
            lines.append("\n".join(fm_lines))


        # Add AI summary if present
        summary = data.get("summary")
        if summary:
            lines.append("\n**AI Summary:**")
            lines.append(f"> {summary.replace(chr(10), chr(10) + '> ')}") # Blockquote format

        # Add Tags
        tags = data.get("tags")
        if tags:
            tag_links = [f"`#{tag}`" for tag in sorted(list(tags))]
            lines.append(f"\n**Tags:** {', '.join(tag_links)}")

        # Add Links
        links = data.get("links")
        if links:
            link_wikilinks = [f"[[{link}]]" for link in sorted(list(links))]
            lines.append(f"\n**Links:** {', '.join(link_wikilinks)}")

        # Add Backlinks
        backlinks = data.get("backlinks")
        if backlinks:
             # Assuming backlinks are stored as relative paths
             backlink_wikilinks = []
             for bl_path in sorted(list(backlinks)):
                 # Try to get the title from index_data if the backlink is also indexed
                 bl_title = index_data.get(bl_path, {}).get("title", bl_path)
                 backlink_wikilinks.append(f"[[{bl_title}]]")
             lines.append(f"\n**Backlinks:** {', '.join(backlink_wikilinks)}")


        lines.append("\n---") # Separator

    return "\n".join(lines) 
