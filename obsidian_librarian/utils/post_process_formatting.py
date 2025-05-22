"""
Simple post-processing utilities for OCR and LLM outputs.
"""

import re
from obsidian_librarian.utils.math_processing import (
    process_math_blocks,
    protect_code_blocks
)

def clean_llm_output(text: str) -> str:
    """Clean raw LLM output text."""
    if not isinstance(text, str):
        return text
    
    # Protect code blocks
    text, code_blocks = protect_code_blocks(text)
    
    # Basic cleanup
    text = re.sub(r'^```markdown\n|```\n?$', '', text.strip())
    text = re.sub(r'---\s*\nOCR processing: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*\n+', '', text)
    
    # Process all math using the unified function
    text = process_math_blocks(text)
    
    # Standardize bullet points
    text = re.sub(r'\s*[-\*•]\s+', '- ', text)
    
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Restore code blocks
    for placeholder, original in code_blocks.items():
        text = text.replace(placeholder, original)
    
    return text

def process_ocr_output(text: str) -> str:
    """Process OCR output text."""
    if not isinstance(text, str):
        return text
    
    # Apply basic cleaning
    text = clean_llm_output(text)
    
    # Fix common OCR layout issues
    text = re.sub(r'(\*\*.+?\*\*)\s*\n\s*:\s*', r'\1: ', text)
    
    return text

# Legacy functions for backward compatibility
def format_latex(text: str) -> str:
    """Legacy function for backward compatibility."""
    return clean_llm_output(text)

def convert_latex_delimiters(text: str) -> str:
    """Legacy function for backward compatibility."""
    from obsidian_librarian.utils.math_processing import fix_latex_delimiters
    return fix_latex_delimiters(text)