"""
Utility for compacting math expressions in markdown files.
"""

import re

def compact_math_blocks(text):
    """
    Removes newlines from display math blocks and ensures clean formatting.
    Removes spaces between dollar signs and math content.
    
    Args:
        text: Input markdown text with LaTeX math
        
    Returns:
        Text with compacted math blocks
    """
    # Use function-based replacement for the most reliable handling
    def process_all_math(text):
        """Process all math expressions to remove spaces inside delimiters"""
        # Process display math
        def compact_display(match):
            inside = match.group(1).strip().replace('\n', ' ')
            return f"$${inside}$$"
        
        text = re.sub(r'\$\$(.*?)\$\$', compact_display, text, flags=re.DOTALL)
        
        # Process inline math with function for reliable spacing handling
        def compact_inline(match):
            # Get the entire match
            full_match = match.group(0)
            
            # If it doesn't have spaces at the delimiters, return as is
            if not (full_match.startswith('$ ') or full_match.endswith(' $')):
                return full_match
                
            # Extract content and strip spaces
            content = full_match.strip('$').strip()
            return f"${content}$"
        
        # Apply to all inline math - carefully match to avoid capturing display math
        # Match pattern that starts with $ but not preceded by another $
        # and ends with $ but not followed by another $
        text = re.sub(r'(?<!\$)\$(.*?)\$(?!\$)', compact_inline, text, flags=re.DOTALL)
        
        return text
    
    # Process multiple times to handle nested or complex cases
    for _ in range(3):  # Multiple passes to catch all instances
        text = process_all_math(text)
    
    # Add space between math and text if needed (but only where needed)
    text = re.sub(r'(\$[^\$\n]+\$)([a-zA-Z0-9])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z0-9])(\$[^\$\n]+\$)', r'\1 \2', text)
    
    # Fix connecting words after display math
    text = re.sub(r'(\$\$)(Then|So|Hence|Therefore)', r'\1 \2', text)
    
    return text

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else input_file + ".fixed"
        
        with open(input_file, 'r') as f:
            content = f.read()
        
        fixed = compact_math_blocks(content)
        
        with open(output_file, 'w') as f:
            f.write(fixed)
        
        print(f"Compacted math in {input_file}, saved to {output_file}")
    else:
        print("Usage: python compact_math.py input_file [output_file]")