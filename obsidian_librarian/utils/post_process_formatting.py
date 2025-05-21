"""
Post-processing utilities for OCR and LLM-generated text.

This module provides focused utilities for cleaning up text from OCR and LLM outputs,
with special attention to LaTeX formatting in markdown.
"""

import re
from typing import Dict, List, Tuple, Optional, Pattern, Match

from obsidian_librarian.utils.latex_formatting import (
    protect_code_blocks,
    fix_latex_delimiters,
    fix_math_content,
    format_inline_math_spacing,
    format_display_math_blocks
)


def clean_raw_llm_output(text: str) -> str:
    """
    Clean raw text output from LLMs, focusing on common formatting issues.
    
    Args:
        text: Raw text from LLM or OCR
        
    Returns:
        Cleaned text with fixed LaTeX formatting and other improvements
    """
    if not isinstance(text, str):
        return text
    
    # Protect code blocks from changes
    text, code_blocks = protect_code_blocks(text)
    
    # 1. BASIC CLEANUP
    
    # Fix markdown fences if they exist
    text = re.sub(r'^```markdown\n|```\n?$', '', text.strip())
    
    # Remove OCR timestamp headers 
    text = re.sub(r'---\s*\nOCR processing: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*\n+', '', text)
    
    # 2. LATEX COMMAND FIXES
    
    # Fix double backslashes before commands
    text = re.sub(r'\\\\([a-zA-Z@#$%^&*()\[\]{}<>.?!~\-_+=|:;"\'`])', r'\\\1', text)
    
    # Fix backslash followed by space before command
    text = re.sub(r'\\ (?=([a-zA-Z]|\\))', r'\\', text)
    
    # Fix common LaTeX command OCR errors
    latex_command_fixes = {
        # Missing commands
        r'(^|\s)ext{': r'\1\\text{',
        r'(^|\s)ext\s+{': r'\1\\text{',
        
        # Common Greek letters
        r'(^|\s)heta\b': r'\1\\theta',
        r'(^|\s)elta\b': r'\1\\delta', 
        r'(^|\s)mega\b': r'\1\\omega',
        r'(^|\s)alpha\b': r'\1\\alpha',
        r'(^|\s)beta\b': r'\1\\beta',
        r'(^|\s)gamma\b': r'\1\\gamma',
        
        # Math symbols
        r'(^|\s)ightarrow\b': r'\1\\rightarrow',
        r'(^|\s)leftarrow\b': r'\1\\leftarrow',
        r'(^|\s)infty\b': r'\1\\infty',
        r'(^|\s)sum(?![a-zA-Z])': r'\1\\sum',
        
        # Math environments
        r'(^|\s)frac\s': r'\1\\frac ',
        r'(^|\s)mathbb\s': r'\1\\mathbb ',
    }
    
    for pattern, replacement in latex_command_fixes.items():
        text = re.sub(pattern, replacement, text)
    
    # Fix spacing in LaTeX commands
    text = re.sub(r'(\\[a-zA-Z]+)\s+({)', r'\1\2', text)
    text = re.sub(r'(\\[a-zA-Z]+)\s+(\()', r'\1\2', text)
    text = re.sub(r'(\\[a-zA-Z]+)\s+(\[)', r'\1\2', text)
    
    # 3. MATH DELIMITER FIXES
    
    # Convert LaTeX environments to markdown math
    text = re.sub(r'\\begin{equation}(.*?)\\end{equation}', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\begin{align}(.*?)\\end{align}', r'$$\1$$', text, flags=re.DOTALL)
    
    # Convert LaTeX delimiters
    text = fix_latex_delimiters(text)
    
    # Fix missing/malformed math delimiters
    text = re.sub(r'\$([^$\n]{3,}|[^$\n]*?[+\-*/=<>\^_][^$\n]*)(?!\$)(?=\s|$)', r'$\1$', text)
    
    # Fix consecutive dollar signs
    text = re.sub(r'\${3,}', r'$$', text)
    text = re.sub(r'(?<!\\)(\$)(\$+)([^$]+)(\$)(\$+)', r'$$\3$$', text)
    
    # Fix mixed inline/display delimiters
    text = re.sub(r'\$\$([^$]+)\$(?!\$)', r'$$\1$$', text)
    text = re.sub(r'\$([^$]+)\$\$(?!\$)', r'$$\1$$', text)
    
    # 4. PROCESS MATH CONTENT
    
    # Extract and process math blocks
    math_pattern = r'(\$\$.*?\$\$|\$[^\$\n]+\$)'
    
    matches = list(re.finditer(math_pattern, text, re.DOTALL))
    result_parts = []
    last_end = 0
    
    for match in matches:
        # Add text before this math block
        result_parts.append(text[last_end:match.start()])
        
        # Get the math block
        math_block = match.group(0)
        
        # Check if it's display or inline math
        is_display = math_block.startswith('$$')
        
        if is_display:
            # Extract content between $$ delimiters
            content = re.match(r'\$\$(.*?)\$\$', math_block, re.DOTALL).group(1)
            # Fix the content
            fixed_content = fix_math_content(content, is_display_math=True)
            # Add fixed math block
            result_parts.append(f"$${fixed_content}$$")
        else:
            # Extract content between $ delimiters
            content = re.match(r'\$(.*?)\$', math_block).group(1)
            # Fix the content
            fixed_content = fix_math_content(content, is_display_math=False)
            # Add fixed math block
            result_parts.append(f"${fixed_content}$")
        
        last_end = match.end()
    
    # Add remaining text
    result_parts.append(text[last_end:])
    
    # Join all parts
    text = ''.join(result_parts)
    
    # 5. FORMAT MATH BLOCKS AND SPACING
    
    # Format display math blocks
    text = format_display_math_blocks(text)
    
    # Fix spacing around inline math
    text = format_inline_math_spacing(text)
    
    # 6. MARKDOWN STRUCTURE FORMATTING
    
    # Standardize bullet points
    text = standardize_bullets(text)
    
    # Convert headers to bold if needed
    text = adjust_heading_levels(text)
    
    # Fix indentation
    text = unindent_content(text)
    
    # 7. FINAL CLEANUP
    
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Restore code blocks
    for placeholder, original in code_blocks.items():
        text = text.replace(placeholder, original)
    
    return text


def standardize_bullets(text: str) -> str:
    """Standardize bullet points to use hyphens with consistent spacing"""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if re.match(r'\s*[-\*•]\s', line):
            line = re.sub(r'\s*[-\*•]\s+', '- ', line)
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)


def adjust_heading_levels(text: str) -> str:
    """Convert headers to bold text if needed"""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if line.startswith('#'):
            # Convert header to bold
            line = '**' + line.lstrip('#').strip() + '**'
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)


def unindent_content(text: str) -> str:
    """Remove excessive indentation from content"""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if re.match(r'\s+[-\*•]', line):
            if line.startswith('    '):  # Remove first level of indentation
                line = line[2:]
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)


def post_process_ocr_output(text: str) -> str:
    """
    Comprehensive processing for OCR output.
    This is the main entry point for processing OCR text.
    
    Args:
        text: Raw OCR text from LLM
        
    Returns:
        Cleaned and formatted text suitable for Obsidian notes
    """
    if not isinstance(text, str):
        return text
    
    # Apply all LLM output cleaning
    text = clean_raw_llm_output(text)
    
    # Additional OCR-specific fixes
    
    # Fix common OCR layout issues
    text = re.sub(r'(\*\*.+?\*\*)\s*\n\s*:\s*', r'\1: ', text)  # Fix "**Title**\n: content"
    
    # Ensure consecutive equations are properly formatted
    text = re.sub(r'\$\$\s*\n\s*\n+\s*\$\$', r'$$\n$$', text)
    
    return text


# Legacy functions for backward compatibility
def format_latex(text: str) -> str:
    """
    Legacy function for backward compatibility.
    Formats LaTeX in markdown text.
    
    Args:
        text: Raw markdown text
        
    Returns:
        Text with LaTeX formatting fixed
    """
    return clean_raw_llm_output(text)

def convert_latex_delimiters(text: str) -> str:
    """
    Legacy function for backward compatibility.
    Converts LaTeX delimiters to markdown style.
    
    Args:
        text: Raw markdown text
        
    Returns:
        Text with LaTeX delimiters converted
    """
    return fix_latex_delimiters(text)