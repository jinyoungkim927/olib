import re

def remove_markdown_fences(content):
    """Remove markdown code fences if they exist at the start and end of the content"""
    return re.sub(r'^```markdown\n|```\n?$', '', content.strip())

def convert_latex_delimiters(content):
    """Convert LaTeX delimiters from \\( \\) to $ and \\[ \\] to $$, handling multi-line cases"""
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
    
    This function is primarily used for OCR output and LLM-generated LaTeX.
    """
    if not isinstance(text, str):
        return text

    # Extract and protect existing code blocks from changes
    code_blocks = {}
    code_placeholder_template = "___CODE_BLOCK_PLACEHOLDER_{}___"
    for i, match in enumerate(re.finditer(r'```.*?```', text, flags=re.DOTALL)):
        placeholder = code_placeholder_template.format(i)
        code_blocks[placeholder] = match.group(0)
        text = text.replace(match.group(0), placeholder, 1)

    # 1. BASIC ESCAPING FIXES

    # Fix double backslashes before commands or symbols
    # \\command -> \command, \\$ -> \$
    text = re.sub(r'\\\\([a-zA-Z@#$%^&*()\[\]{}<>.?!~\-_+=|:;"\'`])', r'\\\1', text)

    # Fix backslash followed by space before a command
    # "\ command" -> "\command"
    text = re.sub(r'\\ (?=([a-zA-Z]|\\))', r'\\', text)

    # 2. SPECIFIC LATEX COMMAND FIXES

    # Fix missing backslash in \text{} - very common in OCR output
    # "ext{text}" -> "\text{text}"
    text = re.sub(r'(^|\s)ext{', r'\1\\text{', text)
    text = re.sub(r'(^|\s)ext\s+{', r'\1\\text{', text)
    
    # Fix common LaTeX command OCR errors
    common_command_fixes = {
        # Greek letters
        r'(^|\s)heta\b': r'\1\\theta',
        r'(^|\s)elta\b': r'\1\\delta', 
        r'(^|\s)mega\b': r'\1\\omega',
        r'(^|\s)alpha\b': r'\1\\alpha',
        r'(^|\s)beta\b': r'\1\\beta',
        r'(^|\s)gamma\b': r'\1\\gamma',
        r'(^|\s)lambda\b': r'\1\\lambda',
        r'(^|\s)sigma\b': r'\1\\sigma',
        r'(^|\s)tau\b': r'\1\\tau',
        r'(^|\s)phi\b': r'\1\\phi',
        r'(^|\s)psi\b': r'\1\\psi',
        
        # Math symbols and operators
        r'(^|\s)ightarrow\b': r'\1\\rightarrow',
        r'(^|\s)leftarrow\b': r'\1\\leftarrow',
        r'(^|\s)infty\b': r'\1\\infty',
        r'(^|\s)sum(?![a-zA-Z])': r'\1\\sum',
        r'(^|\s)prod(?![a-zA-Z])': r'\1\\prod',
        r'(^|\s)cdot\b': r'\1\\cdot',
        r'(^|\s)prime\b': r'\1\\prime',
        r'(^|\s)nabla\b': r'\1\\nabla',
        r'(^|\s)partial\b': r'\1\\partial',
        r'(^|\s)forall\b': r'\1\\forall',
        r'(^|\s)exists\b': r'\1\\exists',
        r'(^|\s)subset\b': r'\1\\subset',
        
        # Math environments and formatting
        r'(^|\s)frac\s': r'\1\\frac ',
        r'(^|\s)mathbb\s': r'\1\\mathbb ',
        r'(^|\s)mathcal\s': r'\1\\mathcal ',
        r'(^|\s)mathrm\s': r'\1\\mathrm ',
        r'(^|\s)mathbf\s': r'\1\\mathbf ',
        r'(^|\s)mathit\s': r'\1\\mathit ',
    }
    
    for pattern, replacement in common_command_fixes.items():
        text = re.sub(pattern, replacement, text)
    
    # Fix spacing in LaTeX commands that take arguments
    # "\command {arg}" -> "\command{arg}"
    text = re.sub(r'(\\[a-zA-Z]+)\s+({)', r'\1\2', text)
    text = re.sub(r'(\\[a-zA-Z]+)\s+(\()', r'\1\2', text)
    text = re.sub(r'(\\[a-zA-Z]+)\s+(\[)', r'\1\2', text)

    # 3. UNDERSCORE AND SUPERSCRIPT FIXES
    
    # Fix escaped underscores in math (not needed in math mode)
    # "a\_i" -> "a_i"
    text = re.sub(r'(\$[^\$]*?)\\_(.*?\$)', r'\1_\2', text)  # for inline math
    text = re.sub(r'(\$\$[^\$]*?)\\_(.*?\$\$)', r'\1_\2', text, flags=re.DOTALL)  # for block math
    
    # Handle multiple underscores in the same math block
    while re.search(r'(\$[^\$]*?)\\_(.*?\$)', text) or re.search(r'(\$\$[^\$]*?)\\_(.*?\$\$)', text, flags=re.DOTALL):
        text = re.sub(r'(\$[^\$]*?)\\_(.*?\$)', r'\1_\2', text)  # for inline math
        text = re.sub(r'(\$\$[^\$]*?)\\_(.*?\$\$)', r'\1_\2', text, flags=re.DOTALL)  # for block math
    
    # Same for carets (superscripts)
    # "a\^i" -> "a^i"
    text = re.sub(r'(\$[^\$]*?)\\\^(.*?\$)', r'\1^\2', text)  # for inline math
    text = re.sub(r'(\$\$[^\$]*?)\\\^(.*?\$\$)', r'\1^\2', text, flags=re.DOTALL)  # for block math

    # 4. SPACING AND DELIMITER FIXES
    
    # Fix the "$F$to$A$" problem (missing spaces between inline math and words)
    text = re.sub(r'(\$[^\$\n]+\$)([a-zA-Z0-9])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z0-9])(\$[^\$\n]+\$)', r'\1 \2', text)
    
    # Fix missing/malformed delimiters in math expressions
    # Fix unclosed math expressions (only if they look like math)
    # Only fix if the content contains math operators or has at least 3 chars
    text = re.sub(r'\$([^$\n]{3,}|[^$\n]*?[+\-*/=<>\^_][^$\n]*)(?!\$)(?=\s|$)', r'$\1$', text)
    
    # Collapse consecutive dollar signs (common OCR error)
    text = re.sub(r'\${3,}', r'$$', text)  # $$$$ -> $$
    text = re.sub(r'(?<!\\)(\$)(\$+)([^$]+)(\$)(\$+)', r'$$\3$$', text)  # $$$x$$$ -> $$x$$
    
    # Fix alternating inline/display math (OCR error)
    text = re.sub(r'\$\$([^$]+)\$(?!\$)', r'$$\1$$', text)  # $$x$ -> $$x$$
    text = re.sub(r'\$([^$]+)\$\$(?!\$)', r'$$\1$$', text)  # $x$$ -> $$x$$
    
    # 5. PROBLEMATIC ESCAPE FIXES
    
    # Fix erroneous backslashes before specific letters known to cause "bad escape" errors
    # "\T", "\s", "\p", etc. that aren't actually LaTeX commands
    problematic_chars = ['T', 's', 'p', 'm', 'l', 'i', 'q', 'z', 'k', 'j', 'h', 'f', 'b', 'g', 'c', 'd', 'e']
    for char in problematic_chars:
        # Only replace if not followed by letters or brace (not a real LaTeX command)
        # Only do this in math blocks
        text = re.sub(r'(\$[^\$]*?)\\(' + char + r')(?![a-zA-Z{])(.*?\$)', r'\1\2\3', text)
        text = re.sub(r'(\$\$[^\$]*?)\\(' + char + r')(?![a-zA-Z{])(.*?\$\$)', r'\1\2\3', text, flags=re.DOTALL)
    
    # 6. LATEX ENVIRONMENT CONVERSION AND CLEANUP
    
    # Convert LaTeX environments to simpler markdown math
    text = re.sub(r'\\begin{equation}(.*?)\\end{equation}', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\begin{equation\*}(.*?)\\end{equation\*}', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\begin{align}(.*?)\\end{align}', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\begin{align\*}(.*?)\\end{align\*}', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\begin{gathered}(.*?)\\end{gathered}', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\begin{cases}(.*?)\\end{cases}', r'$$\\begin{cases}\1\\end{cases}$$', text, flags=re.DOTALL)
    
    # Convert LaTeX delimiters
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    # 7. GENERAL MARKDOWN CLEANUP
    
    # Remove OCR timestamp headers 
    text = re.sub(r'---\s*\nOCR processing: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*\n+', '', text)
    
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up spacing in display math blocks (ensure single newlines around display math)
    text = re.sub(r'([^\n])\$\$', r'\1\n$$', text)  # Ensure newline before display math
    text = re.sub(r'\$\$([^\n])', r'$$\n\1', text)  # Ensure newline after display math
    text = re.sub(r'\n\n\$\$', r'\n$$', text)       # But not excessive newlines
    text = re.sub(r'\$\$\n\n', r'$$\n', text)       # But not excessive newlines
    
    # Restore protected code blocks
    for placeholder, content in code_blocks.items():
        text = text.replace(placeholder, content)

    return text

def post_process_ocr_output(text: str) -> str:
    """
    Comprehensive post-processing for OCR output after initial LLM cleaning.
    Applies multiple formatting steps to clean up and standardize the text.
    
    This is the main entry point for OCR text processing.
    """
    if not isinstance(text, str):
        return text
    
    # 1. Basic cleaning
    text = text.strip()
    text = remove_markdown_fences(text)
    
    # 2. LaTeX and math formatting
    text = clean_raw_llm_output(text)  # First apply general LLM/OCR cleanup
    text = convert_latex_delimiters(text)  # Convert \( \) to $ $ and \[ \] to $$ $$
    text = format_latex(text)  # Format LaTeX expressions
    
    # 3. Markdown structure formatting
    text = format_bullet_points(text)  # Standardize bullet points
    text = adjust_heading_levels(text)  # Convert headers appropriately
    text = unindent_content(text)  # Fix indentation issues
    
    # 4. Final cleanups
    text = remove_extra_newlines(text)  # Clean up excessive newlines
    
    # 5. Specific improvements for OCR
    # Make sure consecutive equations are properly formatted (no extra blank lines)
    text = re.sub(r'\$\$\s*\n\s*\n+\s*\$\$', r'$$\n$$', text)
    
    # Fix common OCR layout issues
    text = re.sub(r'(\*\*.+?\*\*)\s*\n\s*:\s*', r'\1: ', text)  # Fix "**Title**\n: content"
    
    return text
