import re
from pathlib import Path
import os

def get_latex_blocks(content):
    """
    Identifies LaTeX blocks in the content.
    Returns the position ranges to avoid linking within these areas.
    """
    # Create a list to store the start and end positions of LaTeX blocks
    latex_blocks = []
    
    # Keep track of temporary replacements to restore later
    replacements = {}
    modified_content = content
    
    # First save code blocks
    code_block_pattern = r'```.*?```'
    code_blocks = re.findall(code_block_pattern, content, re.DOTALL)
    for i, block in enumerate(code_blocks):
        placeholder = f"__CODE_BLOCK_{i}__"
        replacements[placeholder] = block
        modified_content = modified_content.replace(block, placeholder)
    
    # Track display math blocks ($$...$$)
    i = 0
    while i < len(modified_content) - 1:
        if modified_content[i:i+2] == '$$':
            start = i
            i += 2
            # Find closing $$
            while i < len(modified_content) - 1:
                if modified_content[i:i+2] == '$$':
                    latex_blocks.append((start, i+2))
                    i += 2
                    break
                i += 1
        else:
            i += 1
    
    # Track inline math blocks ($...$)
    # Logic: scan through content, when finding a single $, mark it as the start of a block
    # then continue until finding another single $ (not part of $$)
    i = 0
    in_math = False
    math_start = -1
    
    while i < len(modified_content):
        if i < len(modified_content) - 1 and modified_content[i:i+2] == '$$':
            # Skip display math (already handled)
            i += 2
            continue
            
        if modified_content[i] == '$':
            if not in_math:
                # Start of math block
                in_math = True
                math_start = i
            else:
                # End of math block
                latex_blocks.append((math_start, i+1))
                in_math = False
        i += 1
    
    return latex_blocks

def get_note_titles(vault_path):
    """
    Get all note titles in the vault.
    Returns a list of titles (without .md extension).
    """
    if not vault_path or not os.path.exists(vault_path):
        return []
    
    all_files = os.listdir(vault_path)
    return [f[:-3] for f in all_files if f.endswith('.md')]

def title_variations(title):
    """Generate case variations for a title"""
    return [
        title,  # Original
        title.lower(),  # Lowercase
        title.upper(),  # Uppercase
        title.capitalize(),  # First letter capitalized
        ' '.join(word.capitalize() for word in title.split())  # Title Case
    ]

def is_within_range(position, ranges):
    """Check if a position is within any of the given ranges"""
    for start, end in ranges:
        if start <= position < end:
            return True
    return False

def fix_broken_links(content):
    """
    Fix malformed link patterns in content.
    """
    # Fix links with extra brackets like [[[]][Topic]]
    content = re.sub(r'\[\[\[\]\]\[([^\]]+?)\]\]', r'[[\1]]', content)
    
    # Fix links with duplicate brackets like [[[[Topic]]]]
    content = re.sub(r'\[\[\[\[([^\]]+?)\]\]\]\]', r'[[\1]]', content)
    
    # Fix links with mismatched brackets like [[[Topic]]
    content = re.sub(r'\[\[\[([^\]]+?)\]\]', r'[[\1]]', content)
    
    # Fix links with mismatched brackets like [[Topic]]]
    content = re.sub(r'\[\[([^\]]+?)\]\]\]', r'[[\1]]', content)
    
    # Fix nested links like [[Doubling or Duplicating [[Regression]] Points]]
    nested_pattern = r'\[\[(.*?)\[\[(.*?)\]\](.*?)\]\]'
    while re.search(nested_pattern, content):
        content = re.sub(nested_pattern, r'[[\1\2\3]]', content)
    
    return content

def safe_autolink(content, note_titles):
    """
    Safely add wiki-style links to content without affecting LaTeX or existing links.
    """
    # Save original content in case we need to revert
    original_content = content
    
    # 1. First, identify all areas we need to preserve
    
    # Save code blocks to restore later
    code_blocks = {}
    for i, match in enumerate(re.finditer(r'```.*?```', content, re.DOTALL)):
        placeholder = f"__CODE_BLOCK_{i}__"
        code_blocks[placeholder] = match.group(0)
        content = content.replace(match.group(0), placeholder)
    
    # Save pipe-style links ([[Title|Display Text]])
    pipe_links = {}
    for i, match in enumerate(re.finditer(r'\[\[([^|]+?)\|([^\]]+?)\]\]', content)):
        placeholder = f"__PIPE_LINK_{i}__"
        pipe_links[placeholder] = match.group(0)
        content = content.replace(match.group(0), placeholder)
    
    # Save all existing links
    simple_links = {}
    for i, match in enumerate(re.finditer(r'\[\[([^|]+?)\]\]', content)):
        if not any(ph in match.group(0) for ph in pipe_links.keys()):
            placeholder = f"__SIMPLE_LINK_{i}__"
            simple_links[placeholder] = match.group(0)
            content = content.replace(match.group(0), placeholder)
    
    # Save inline math blocks ($...$)
    inline_math = {}
    for i, match in enumerate(re.finditer(r'\$([^\$]+?)\$', content)):
        placeholder = f"__INLINE_MATH_{i}__"
        inline_math[placeholder] = match.group(0)
        content = content.replace(match.group(0), placeholder)
    
    # Save display math blocks ($$...$$)
    display_math = {}
    for i, match in enumerate(re.finditer(r'\$\$(.*?)\$\$', content, re.DOTALL)):
        placeholder = f"__DISPLAY_MATH_{i}__"
        display_math[placeholder] = match.group(0)
        content = content.replace(match.group(0), placeholder)
    
    # 2. Fix any broken link formatting
    content = fix_broken_links(content)
    
    # 3. Get links that should be added (sorted by length to prevent partial matches)
    sorted_titles = sorted(note_titles, key=len, reverse=True)
    
    # 4. Find and replace instances of titles with links
    for title in sorted_titles:
        # Generate case variations
        variants = title_variations(title)
        
        for variant in variants:
            # Look for standalone instances of the title
            pattern = r'\b' + re.escape(variant) + r'\b'
            
            # Replace with link
            content = re.sub(pattern, f"[[{title}]]", content)
    
    # 5. Restore preserved content
    
    # Restore simple links
    for placeholder, original in simple_links.items():
        content = content.replace(placeholder, original)
    
    # Restore pipe links
    for placeholder, original in pipe_links.items():
        content = content.replace(placeholder, original)
    
    # Restore math blocks
    for placeholder, original in inline_math.items():
        content = content.replace(placeholder, original)
    
    for placeholder, original in display_math.items():
        content = content.replace(placeholder, original)
    
    # Restore code blocks
    for placeholder, original in code_blocks.items():
        content = content.replace(placeholder, original)
    
    # 6. Do final validation
    
    # Check if we have unbalanced delimiters
    dollar_count = content.count('$') - content.count('$$') * 2
    if dollar_count % 2 != 0:
        # Math formatting is broken, revert to original
        return original_content
    
    # Ensure all pipe links are properly formatted
    pipe_link_pattern = r'\[\[([^|]+?)\|([^\]]+?)\]\]'
    if len(re.findall(pipe_link_pattern, original_content)) != len(re.findall(pipe_link_pattern, content)):
        # Pipe links were broken, revert to original
        return original_content
    
    return content

def process_note(note_path, note_titles, verbose=False, dry_run=False):
    """
    Process a single note, adding links where appropriate.
    Returns (was_modified, info_dict)
    """
    try:
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for issues that need fixing
        has_broken_links = re.search(r'\[\[\[.*?\]\]|\[\[.*?\]\]\]|\[\[\[\]\]\[.*?\]\]|\[\[\[\[.*?\]\]\]\]', content) is not None
        has_nested_links = re.search(r'\[\[.*?\[\[.*?\]\].*?\]\]', content) is not None
        
        # Count original links
        orig_link_count = len(re.findall(r'\[\[.*?\]\]', content))
        
        # Process content
        modified_content = safe_autolink(content, note_titles)
        
        # Count new links
        new_link_count = len(re.findall(r'\[\[.*?\]\]', modified_content))
        links_added = max(0, new_link_count - orig_link_count)  # Ensure non-negative
        
        # Prepare info about modifications
        info = {
            'fixed_broken_links': has_broken_links and content != modified_content,
            'fixed_nested_links': has_nested_links and content != modified_content,
            'links_added': links_added
        }
        
        # Write changes if needed and not in dry run mode
        if content != modified_content:
            if not dry_run:
                with open(note_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
            return True, info
        
        return False, info
        
    except Exception as e:
        return False, {'error': str(e)}

def process_vault(vault_path, verbose=False, dry_run=False):
    """
    Process all notes in the vault, adding links where appropriate.
    Returns statistics about the operation.
    """
    if not os.path.exists(vault_path):
        return {'error': f"Vault path {vault_path} does not exist"}
    
    note_titles = get_note_titles(vault_path)
    
    stats = {
        'files_processed': 0,
        'files_modified': 0,
        'broken_links_fixed': 0,
        'nested_links_fixed': 0,
        'total_links_added': 0,
        'errors': []
    }
    
    for file_name in os.listdir(vault_path):
        if not file_name.endswith('.md'):
            continue
        
        note_path = os.path.join(vault_path, file_name)
        stats['files_processed'] += 1
        
        try:
            modified, info = process_note(note_path, note_titles, verbose, dry_run)
            
            if 'error' in info:
                stats['errors'].append(f"{file_name}: {info['error']}")
                continue
            
            if modified:
                stats['files_modified'] += 1
                if info['fixed_broken_links']:
                    stats['broken_links_fixed'] += 1
                if info['fixed_nested_links']:
                    stats['nested_links_fixed'] += 1
                stats['total_links_added'] += info['links_added']
                
                if verbose:
                    note_name = file_name[:-3]  # Remove .md extension
                    if info['fixed_broken_links']:
                        print(f"Fixed broken links in {note_name}")
                    if info['fixed_nested_links']:
                        print(f"Fixed nested links in {note_name}")
                    if info['links_added'] > 0:
                        print(f"Added {info['links_added']} links to {note_name}")
        except Exception as e:
            stats['errors'].append(f"{file_name}: {str(e)}")
    
    return stats
