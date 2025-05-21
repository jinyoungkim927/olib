"""
Core LaTeX formatting utilities for markdown files.

This module provides essential functions for handling LaTeX formatting in markdown,
particularly focusing on math expressions. These functions are used by both the
main formatter and the OCR processing functionality.
"""

import re
from typing import Dict, Tuple, List, Pattern, Match


def protect_code_blocks(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Extracts and protects code blocks from changes during formatting.
    
    Args:
        text: The input text that may contain code blocks.
        
    Returns:
        A tuple containing:
        - The modified text with code blocks replaced by placeholders
        - A dictionary mapping placeholders to original code blocks
    """
    code_blocks = {}
    placeholder_template = "___CODE_BLOCK_PLACEHOLDER_{}___"
    
    # Process code blocks in order to avoid nesting issues
    code_matches = list(re.finditer(r'```.*?```', text, flags=re.DOTALL))
    
    # Create a list of text parts and placeholders
    parts = []
    last_end = 0
    
    for i, match in enumerate(code_matches):
        placeholder = placeholder_template.format(i)
        code_blocks[placeholder] = match.group(0)
        
        # Add text before the code block and the placeholder
        parts.append(text[last_end:match.start()])
        parts.append(placeholder)
        last_end = match.end()
    
    # Add remaining text
    parts.append(text[last_end:])
    
    return "".join(parts), code_blocks


def protect_and_extract_math(text: str) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    """
    Extracts both inline and display math blocks, protecting them for separate processing.
    
    Args:
        text: The input text containing math expressions.
        
    Returns:
        A tuple containing:
        - The modified text with math blocks replaced by placeholders
        - A dictionary mapping display math placeholders to original blocks
        - A dictionary mapping inline math placeholders to original blocks
    """
    # Protect display math ($$...$$) first
    display_math_blocks = {}
    display_placeholder_template = "___DISPLAY_MATH_PLACEHOLDER_{}___"
    
    # Use non-greedy matching and ensure we don't match nested $$ patterns wrongly
    display_pattern = r'(?<!\$)\$\$(.*?)\$\$(?!\$)'
    
    # Find and store all display math blocks
    for i, match in enumerate(re.finditer(display_pattern, text, flags=re.DOTALL)):
        placeholder = display_placeholder_template.format(i)
        display_math_blocks[placeholder] = match.group(0)
        text = text.replace(match.group(0), placeholder, 1)
    
    # Now protect inline math ($...$)
    inline_math_blocks = {}
    inline_placeholder_template = "___INLINE_MATH_PLACEHOLDER_{}___"
    
    # Find all inline math, being careful not to match $ used for other purposes
    # Look for $ that doesn't have another $ before it, followed by content without newlines, 
    # followed by $ that doesn't have another $ after it
    inline_pattern = r'(?<!\$)\$([^\$\n]+?)\$(?!\$)'
    
    for i, match in enumerate(re.finditer(inline_pattern, text)):
        placeholder = inline_placeholder_template.format(i)
        inline_math_blocks[placeholder] = match.group(0)
        text = text.replace(match.group(0), placeholder, 1)
    
    return text, display_math_blocks, inline_math_blocks


def fix_math_content(content: str, is_display_math: bool = False) -> str:
    """
    Cleans up and fixes common issues within math content.
    
    Args:
        content: The math content (without the delimiters)
        is_display_math: Whether this is display math (True) or inline math (False)
        
    Returns:
        The fixed math content
    """
    # 1. Fix escaped underscores in math (e.g., A\_1 -> A_1)
    content = re.sub(r'\\_', r'_', content)
    
    # 2. Fix escaped carets in math (e.g., A\^2 -> A^2)
    content = re.sub(r'\\\^', r'^', content)
    
    # 3. Fix LaTeX command spacing
    content = re.sub(r'(\\[a-zA-Z]+)\s+({)', r'\1\2', content)  # \text {word} -> \text{word}
    content = re.sub(r'(\\[a-zA-Z]+)\s+(\()', r'\1\2', content) # \sqrt (x) -> \sqrt(x)
    content = re.sub(r'(\\[a-zA-Z]+)\s+(\[)', r'\1\2', content) # \mathbb [R] -> \mathbb[R]
    
    # 4. Fix common OCR errors
    content = re.sub(r'(^|\s)ext{', r'\1\\text{', content)
    content = re.sub(r'(\\text)\s+({)', r'\1\2', content)
    
    # 5. Fix problematic backslashes
    problematic_chars = ['T', 's', 'p', 'm', 'l', 'i', 'q', 'z', 'k', 'j', 'h', 'f', 'b', 'g', 'c', 'd', 'e']
    for char in problematic_chars:
        # Only fix if not followed by a letter or brace (not a real command)
        content = re.sub(r'\\' + char + r'(?![a-zA-Z{])', char, content)
    
    # 6. Only for display math, fix additional issues
    if is_display_math:
        # Fix spacing in math operators
        content = re.sub(r'\\(quad|qquad|,)\s+', r'\\\1 ', content)
        content = re.sub(r'\s+\\(quad|qquad|,)', r' \\\1', content)
        
        # Fix escaped brackets
        content = re.sub(r'\\ ({)', r'\\{\1', content) # \ { -> \{
        content = re.sub(r'\\ (\[)', r'\\[\1', content) # \ [ -> \[
        content = re.sub(r'\\ (\()', r'\\(\1', content) # \ ( -> \(
    
    return content


def fix_latex_delimiters(text: str) -> str:
    """Converts LaTeX style delimiters to Markdown style."""
    # Fix improperly escaped inline delimiters \$...\$ -> $...$
    text = re.sub(r'\\\$([^$]+?)\\\$', r'$\1$', text)
    
    # Convert display math \[ ... \] to $$ ... $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    
    # Convert inline math \( ... \) to $ ... $
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    return text


def format_inline_math_spacing(text: str) -> str:
    """Fixes spacing issues around inline math."""
    # 1. Remove spaces inside inline math delimiters
    text = re.sub(r'\$\s+(.*?)\s+\$', r'$\1$', text)
    
    # 2. Ensure space between math and text
    text = re.sub(r'(\$[^\$]+\$)([a-zA-Z0-9])', r'\1 \2', text)  # $x$word -> $x$ word
    text = re.sub(r'([a-zA-Z0-9])(\$[^\$]+\$)', r'\1 \2', text)  # word$x$ -> word $x$
    
    # 3. No space between math and punctuation
    text = re.sub(r'(\$[^\$]+\$)\s+([.,;:!?)])', r'\1\2', text)
    
    # 4. No space between opening punctuation and math
    text = re.sub(r'([(])\s+(\$[^\$]+\$)', r'\1\2', text)
    
    return text


def format_display_math_blocks(text: str) -> str:
    """
    Ensures proper formatting of display math blocks in markdown.
    
    Args:
        text: The input text with display math blocks.
        
    Returns:
        Text with properly formatted display math blocks.
    """
    # Identify all display math blocks
    display_math_blocks = list(re.finditer(r'\$\$(.*?)\$\$', text, flags=re.DOTALL))
    
    # Process in reverse to avoid index shifts
    for match in reversed(display_math_blocks):
        start, end = match.span()
        content = match.group(1)
        
        # Determine context: Should this be inline or standalone?
        # Default to standalone for multi-line math
        if '\n' in content:
            # Multi-line display math should be on its own lines
            equation_block = f"\n$$\n{content.strip()}\n$$\n"
            text = text[:start] + equation_block + text[end:]
        else:
            # Check if this is in a paragraph
            previous_char = text[start-1] if start > 0 else '\n'
            next_char = text[end] if end < len(text) else '\n'
            
            # If it's surrounded by text (not newlines), keep it inline
            if previous_char != '\n' and next_char != '\n':
                # Keep it inline - no changes needed
                pass
            else:
                # Standalone single-line math should be on its own lines
                equation_block = f"\n$$\n{content.strip()}\n$$\n"
                text = text[:start] + equation_block + text[end:]
    
    # Cleanup: ensure exactly one newline before and after display math
    text = re.sub(r'\n{3,}(\$\$)', r'\n\1', text)
    text = re.sub(r'(\$\$)\n{3,}', r'\1\n', text)
    
    # Handle consecutive equations - no blank line between them
    text = re.sub(r'\$\$\s*\n\n+\s*\$\$', r'$$\n$$', text)
    
    return text