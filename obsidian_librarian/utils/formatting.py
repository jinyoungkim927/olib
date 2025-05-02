import re
import logging

logger = logging.getLogger(__name__)

# --- Formatting Functions (Adapted from commands/notes.py logic) ---

def format_math_blocks(content: str) -> str:
    """Ensures $$ math blocks are on their own lines."""
    # Ensure $$ blocks are surrounded by newlines
    content = re.sub(r'(?<!\n)\s*(\$\$)\s*', r'\n\n\1\n', content) # Before $$
    content = re.sub(r'\s*(\$\$)\s*(?!\n)', r'\n\1\n\n', content) # After $$
    # Remove redundant blank lines around $$ blocks
    content = re.sub(r'\n{3,}(\$\$)', r'\n\n\1', content)
    content = re.sub(r'(\$\$)\n{3,}', r'\1\n\n', content)
    return content

def format_code_blocks(content: str) -> str:
    """Ensures ``` code blocks are on their own lines."""
    # Find all code blocks first to avoid formatting inside them
    code_blocks = re.findall(r'(```.*?```)', content, re.DOTALL)
    # Temporarily replace code blocks with placeholders
    placeholder_template = "___CODE_BLOCK_PLACEHOLDER_{}___"
    temp_content = content
    for i, block in enumerate(code_blocks):
        temp_content = temp_content.replace(block, placeholder_template.format(i), 1)

    # Format outside code blocks: Ensure ``` are surrounded by newlines
    temp_content = re.sub(r'(?<!\n)\s*(```)\s*', r'\n\n\1\n', temp_content) # Before ```
    temp_content = re.sub(r'\s*(```)\s*(?!\n)', r'\n\1\n\n', temp_content) # After ```
    # Remove redundant blank lines around ``` blocks
    temp_content = re.sub(r'\n{3,}(```)', r'\n\n\1', temp_content)
    temp_content = re.sub(r'(```)\n{3,}', r'\1\n\n', temp_content)

    # Put code blocks back
    final_content = temp_content
    for i, block in enumerate(code_blocks):
        # Ensure the placeholder itself is surrounded by newlines before replacement
        final_content = re.sub(r'\n*'+placeholder_template.format(i)+r'\n*', '\n\n'+placeholder_template.format(i)+'\n\n', final_content)
        final_content = final_content.replace(placeholder_template.format(i), block, 1)
        # Clean up extra newlines potentially introduced around the block
        final_content = re.sub(r'\n{3,}', '\n\n', final_content)


    return final_content.strip() # Strip leading/trailing whitespace from final result

# Add other formatting functions like format_tables if needed

def apply_standard_formatting(content: str) -> str:
    """Applies a standard set of formatting rules to note content."""
    logger.debug("Applying standard formatting...")
    original_content = content
    try:
        content = format_math_blocks(content)
        content = format_code_blocks(content)
        # Add calls to other formatters (e.g., tables) here if desired
        logger.debug("Formatting applied successfully.")
        return content
    except Exception as e:
        logger.error(f"Error during standard formatting: {e}", exc_info=True)
        # Return original content if formatting fails
        return original_content 