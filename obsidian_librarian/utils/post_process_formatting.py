import re

def remove_markdown_fences(content):
    """Remove markdown code fences if they exist at the start and end of the content"""
    return re.sub(r'^```markdown\n|```\n?$', '', content.strip())

def convert_latex_delimiters(content):
    """Convert LaTeX delimiters from \( \) to $ and \[ \] to $$, handling multi-line cases"""
    # Convert display math (multi-line)
    content = re.sub(r'\\\[\s*(.*?)\s*\\\]', r'$$\1$$', content, flags=re.DOTALL)
    # Convert inline math
    content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
    return content

def adjust_heading_levels(content):
    """Convert all headers to bold text"""
    lines = content.split('\n')
    processed_lines = []
    
    for line in lines:
        if line.startswith('#'):
            # Convert any header level to bold
            line = '**' + line.lstrip('#').strip() + '**'
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def format_latex(content):
    """Format LaTeX expressions by removing spaces and converting display math"""
    # Remove spaces between $ and content for inline math
    content = re.sub(r'\$ (.*?) \$', r'$\1$', content)
    
    # Convert display math blocks to double dollar signs and remove all preceding whitespace
    content = re.sub(r'\s*\\\[(.*?)\\\]', r'$$\1$$', content)
    content = re.sub(r'\s*\$\$(.*?)\$\$', r'$$\1$$', content)
    
    return content

def unindent_content(content):
    """Remove one level of indentation from all content while preserving hierarchy"""
    lines = content.split('\n')
    processed_lines = []
    
    for line in lines:
        # If line starts with spaces and a bullet point, remove 2 spaces but keep remaining indentation
        if re.match(r'\s+[-\*•]', line):
            if line.startswith('    '):  # Remove first level of indentation only
                line = line[2:]
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def remove_extra_newlines(content):
    """Remove extra newlines, keeping appropriate spacing"""
    # First, handle multiple consecutive newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove newline after double dollar signs unless followed by bullet point or bold
    content = re.sub(r'\$\$\n\n(?![-\*•\*\*])', r'$$\n', content)
    
    # Keep double newlines between sections, single newline between bullet points
    content = re.sub(r'(\*\*.*?\*\*)\n\n(?![\*\-])', r'\1\n', content)
    content = re.sub(r'(-.*)\n\n(-)', r'\1\n\2', content)
    
    return content

def format_bullet_points(content):
    """Format bullet points consistently"""
    lines = content.split('\n')
    processed_lines = []
    
    for line in lines:
        # Standardize bullet points to use single dash with space
        if re.match(r'\s*[-\*•]\s', line):
            line = re.sub(r'\s*[-\*•]\s+', '- ', line)
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def clean_raw_llm_output(text: str) -> str:
    """
    Cleans raw text output from LLMs, focusing on common LaTeX-related issues,
    before more structured formatting is applied.
    This aims to prevent "bad escape" errors in subsequent regex processing.
    """
    if not isinstance(text, str):
        return text

    # 1. Normalize double backslashes before commands or symbols: \\command -> \command, \\$ -> \$
    # Handles cases like \\section, \\alpha, \\$, \\{, etc.
    text = re.sub(r'\\\\([a-zA-Z@#$%^&*()\[\]{}<>.?!~\-_+=|:;"\'`])', r'\\\1', text)

    # 2. Fix backslash followed by space then a command/symbol: \ command -> \command or \ symbol -> \symbol
    # Matches '\ ' only if followed by a potential command start (letter) or another backslash (for symbols like '\(')
    text = re.sub(r'\\ (?=([a-zA-Z]|\\))', r'\\', text)

    # 3. Specifically target single erroneous backslashes before specific letters
    #    that were observed to cause "bad escape" errors (e.g., \T, \s, \p, \m, \l, \i).
    #    This converts "\X" to "X" if X is one of these problematic characters and
    #    it's not followed by another letter (which would make it a longer command) or an opening brace.
    problematic_chars = ['T', 's', 'p', 'm', 'l', 'i']
    for char_code in problematic_chars:
        # We need to re.escape(char_code) in case char_code is a regex metacharacter (e.g. if '.' was in the list)
        # For the current list, it's not strictly necessary but good practice.
        escaped_char = re.escape(char_code)
        
        # Pattern: (\\) (problematic_char) (not followed by a letter or '{')
        # Replacement: just the problematic_char (removes the leading backslash)
        # Example: \T -> T, but \Text or \T{...} would be untouched by this specific rule for 'T'.
        # It also avoids affecting valid sequences like `\ ` (escaped space) or `\$`.
        pattern = r'\\(' + escaped_char + r')(?![a-zA-Z{])'
        replacement = r'\1' 
        text = re.sub(pattern, replacement, text)
    
    # 4. Remove backslash before a standalone space if it's not a recognized LaTeX space command.
    # LaTeX uses `\ ` for a normal inter-word space in certain contexts, or `\,`, `\;`, etc.
    # If we find `\ ` followed by a non-alphanumeric character (excluding typical LaTeX ones),
    # it might be an error. This is a bit more heuristic.
    # Example: "word \ and word" -> "word and word"
    # This regex looks for '\ ' NOT followed by typical command/symbol starters or brackets.
    # text = re.sub(r'\\ (?![a-zA-Z\\\[({%])', ' ', text) # This might be too aggressive.

    return text

def post_process_ocr_output(text: str) -> str:
    """
    General post-processing for OCR output after initial LLM cleaning.
    This can include trimming, fixing very basic Markdown, etc.
    """
    if not isinstance(text, str):
        return text
    
    text = text.strip()
    # Add any other general, non-LaTeX specific post-processing here.
    # For example, ensuring consistent line breaks or removing excessive blank lines
    # if not handled by FormatFixer.
    
    # Example: Normalize multiple newlines to a maximum of two
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def post_process_ocr_output(content):
    """Apply all post-processing steps to OCR output"""
    content = remove_markdown_fences(content)
    content = convert_latex_delimiters(content)
    content = adjust_heading_levels(content)
    content = format_latex(content)
    content = format_bullet_points(content)
    content = unindent_content(content)
    content = remove_extra_newlines(content)
    return content
