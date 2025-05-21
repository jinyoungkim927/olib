#!/usr/bin/env python3
import re
from typing import List, Tuple, Dict, Set, Optional

class MathFixer:
    """A utility class for fixing LaTeX formatting issues in Markdown"""
    
    @staticmethod
    def fix_math(text: str) -> str:
        """
        Main method to fix all math-related formatting issues in the given text.
        This uses a systematic approach rather than relying on complex regex patterns.
        """
        # First, let's extract all inline and display math blocks to process them separately
        # This avoids problems with nested regexes
        display_math_blocks = MathFixer._extract_math_blocks(text, is_display=True)
        inline_math_blocks = MathFixer._extract_math_blocks(text, is_display=False)
        
        # Create a clean version of the text with math blocks replaced by placeholders
        processed_text = text
        all_blocks = {}
        
        # Replace display math blocks with placeholders
        for i, (start, end, content) in enumerate(display_math_blocks):
            placeholder = f"___DISPLAY_MATH_{i}___"
            all_blocks[placeholder] = (start, end, content, True)  # True indicates display math
            processed_text = processed_text[:start] + placeholder + processed_text[end:]
            
            # Adjust positions of subsequent blocks
            offset = len(placeholder) - (end - start)
            for j in range(i + 1, len(display_math_blocks)):
                display_math_blocks[j] = (
                    display_math_blocks[j][0] + offset,
                    display_math_blocks[j][1] + offset,
                    display_math_blocks[j][2]
                )
            for j in range(len(inline_math_blocks)):
                if inline_math_blocks[j][0] > end:
                    inline_math_blocks[j] = (
                        inline_math_blocks[j][0] + offset,
                        inline_math_blocks[j][1] + offset,
                        inline_math_blocks[j][2]
                    )
        
        # Replace inline math blocks with placeholders
        for i, (start, end, content) in enumerate(inline_math_blocks):
            placeholder = f"___INLINE_MATH_{i}___"
            all_blocks[placeholder] = (start, end, content, False)  # False indicates inline math
            processed_text = processed_text[:start] + placeholder + processed_text[end:]
            
            # Adjust positions of subsequent blocks
            offset = len(placeholder) - (end - start)
            for j in range(i + 1, len(inline_math_blocks)):
                inline_math_blocks[j] = (
                    inline_math_blocks[j][0] + offset,
                    inline_math_blocks[j][1] + offset,
                    inline_math_blocks[j][2]
                )
        
        # Process each math block individually
        fixed_blocks = {}
        for placeholder, (_, _, content, is_display) in all_blocks.items():
            if is_display:
                # Fix display math
                fixed_content = MathFixer._fix_display_math(content)
                fixed_blocks[placeholder] = f"$$\n{fixed_content}\n$$"
            else:
                # Fix inline math
                fixed_content = MathFixer._fix_inline_math(content)
                fixed_blocks[placeholder] = f"${fixed_content}$"
        
        # Now restore all math blocks with their fixed versions
        for placeholder, fixed_content in fixed_blocks.items():
            processed_text = processed_text.replace(placeholder, fixed_content)
        
        # Fix spacing around inline math
        processed_text = MathFixer._fix_spacing_around_math(processed_text)
        
        return processed_text
    
    @staticmethod
    def _extract_math_blocks(text: str, is_display: bool = False) -> List[Tuple[int, int, str]]:
        """
        Extract math blocks (either display or inline) from the text.
        Returns a list of tuples: (start_index, end_index, content)
        """
        if is_display:
            # Extract display math blocks ($$...$$)
            pattern = r'\$\$(.*?)\$\$'
            delim_length = 2
        else:
            # Extract inline math blocks ($...$)
            pattern = r'(?<!\$)\$((?!\$).*?)(?<!\$)\$(?!\$)'
            delim_length = 1
        
        blocks = []
        for match in re.finditer(pattern, text, re.DOTALL):
            start = match.start()
            end = match.end()
            content = match.group(1)
            blocks.append((start, end, content))
        
        return blocks
    
    @staticmethod
    def _fix_inline_math(content: str) -> str:
        """Fix common issues in inline math content"""
        # Remove spaces at the beginning and end
        content = content.strip()
        
        # Fix escaped underscores (\_1 -> _1)
        content = re.sub(r'\\_', '_', content)
        
        # Fix spacing in LaTeX commands
        content = re.sub(r'\\([a-zA-Z]+)\s+{', r'\\\1{', content)
        
        return content
    
    @staticmethod
    def _fix_display_math(content: str) -> str:
        """Fix common issues in display math content"""
        # Remove spaces at the beginning and end
        content = content.strip()
        
        # Fix escaped underscores (\_1 -> _1)
        content = re.sub(r'\\_', '_', content)
        
        # Fix spacing in LaTeX commands
        content = re.sub(r'\\([a-zA-Z]+)\s+{', r'\\\1{', content)
        
        return content
    
    @staticmethod
    def _fix_spacing_around_math(text: str) -> str:
        """Fix spacing issues around math blocks"""
        # Ensure there's a space between text and inline math
        text = re.sub(r'([a-zA-Z])(\$[^\$]+\$)', r'\1 \2', text)  # word$ math$ -> word $math$
        text = re.sub(r'(\$[^\$]+\$)([a-zA-Z])', r'\1 \2', text)  # $math$word -> $math$ word
        
        # No space between math and punctuation
        text = re.sub(r'(\$[^\$]+\$)\s+([.,;:!?)])', r'\1\2', text)  # $math$ . -> $math$.
        
        # No space between opening punctuation and math
        text = re.sub(r'([(])\s+(\$[^\$]+\$)', r'\1\2', text)  # ( $math$ -> ($math$
        
        return text
    
if __name__ == "__main__":
    # Simple test case
    test_text = """
    This is a test with inline math $a_1 + b\_2 = c$ and display math:
    $$
    E = mc^2\\
    F = ma
    $$
    
    And mixed math: $a$ and $a_i$ should be fixed.
    Some more display math:
    $$\\frac{1}{2} = 0.5$$
    """
    
    fixed_text = MathFixer.fix_math(test_text)
    print("Original:")
    print(test_text)
    print("\nFixed:")
    print(fixed_text)