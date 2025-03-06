import re
from pathlib import Path
import os

def get_latex_blocks(content):
    """
    Find all LaTeX blocks in the content.
    Returns a list of (start, end) tuples marking LaTeX regions.
    """
    latex_blocks = []
    
    # First, find all display math blocks ($$...$$)
    display_pattern = r'\$\$(.*?)\$\$'
    for match in re.finditer(display_pattern, content, re.DOTALL):
        latex_blocks.append((match.start(), match.end()))
    
    # Now find all inline math blocks ($...$)
    # We need to be careful here as $ is used as both start and end marker
    i = 0
    while i < len(content):
        # Skip if we're already inside a known LaTeX block
        skip = False
        for start, end in latex_blocks:
            if start <= i < end:
                skip = True
                break
        
        if skip:
            i += 1
            continue
        
        # Check for $ (but not part of $$)
        if content[i] == '$' and (i+1 >= len(content) or content[i+1] != '$'):
            start = i
            # Find the closing $
            i += 1
            while i < len(content):
                if content[i] == '$' and (i == 0 or content[i-1] != '\\'):
                    # Found closing $
                    latex_blocks.append((start, i + 1))
                    break
                i += 1
        i += 1
    
    return latex_blocks

def is_within_latex(content, position, latex_blocks=None):
    """
    Check if a position is within any LaTeX block.
    """
    if latex_blocks is None:
        latex_blocks = get_latex_blocks(content)
    
    for start, end in latex_blocks:
        if start <= position < end:
            return True
    
    return False

def fix_broken_links(content):
    """
    Fix various broken link formats in Markdown content.
    """
    # Fix patterns with extra brackets like [[[]][Topic]]
    content = re.sub(r'\[\[\[\]\]\[([^\]]+?)\]\]', r'[[\1]]', content)
    
    # Fix patterns with duplicate brackets like [[[[Topic]]]]
    content = re.sub(r'\[\[\[\[([^\]]+?)\]\]\]\]', r'[[\1]]', content)
    
    # Fix patterns with mismatched brackets like [[[Topic]]
    content = re.sub(r'\[\[\[([^\]]+?)\]\]', r'[[\1]]', content)
    
    # Fix patterns with mismatched brackets like [[Topic]]]
    content = re.sub(r'\[\[([^\]]+?)\]\]\]', r'[[\1]]', content)
    
    # Fix nested links like [[Doubling or Duplicating [[Regression]] Points]]
    # This finds links that contain other links inside them and removes the inner brackets
    nested_pattern = r'\[\[(.*?)\[\[(.*?)\]\](.*?)\]\]'
    while re.search(nested_pattern, content):
        content = re.sub(nested_pattern, r'[[\1\2\3]]', content)
    
    return content

def get_existing_links(content):
    """
    Get all existing links in the content.
    Returns a set of lowercase link texts.
    """
    existing_links = set()
    
    for match in re.finditer(r'\[\[(.*?)\]\]', content):
        link_text = match.group(1)
        if '|' in link_text:
            # Handle pipe syntax: [[Note|Display Text]]
            note_name = link_text.split('|')[0].strip()
            existing_links.add(note_name.lower())
        else:
            existing_links.add(link_text.lower())
    
    return existing_links

def get_link_positions(content):
    """
    Get positions of all existing links.
    Returns a list of (start, end) tuples.
    """
    positions = []
    
    for match in re.finditer(r'\[\[.*?\]\]', content):
        positions.append((match.start(), match.end()))
    
    return positions

def get_note_titles(vault_path):
    """
    Get all note titles in the vault.
    Returns a list of titles (without .md extension).
    """
    if not vault_path or not os.path.exists(vault_path):
        return []
    
    all_files = os.listdir(vault_path)
    return [f[:-3] for f in all_files if f.endswith('.md')]

def get_title_variations(title):
    """
    Generate case variations of a title for case-insensitive matching.
    """
    return [
        title,                                          # Original
        title.lower(),                                  # All lowercase
        title.upper(),                                  # All uppercase
        title.capitalize(),                             # First letter capitalized
        ' '.join(word.capitalize() for word in title.split())  # Title case
    ]

def is_within_existing_link(position, link_positions):
    """
    Check if a position is within an existing link.
    """
    for start, end in link_positions:
        if start <= position < end:
            return True
    return False

def autolink_content(content, note_titles):
    """
    Add wiki-style links to content for all note titles.
    Handles case variations and avoids linking inside LaTeX blocks.
    """
    # Keep the original content for comparison
    original_content = content
    
    # Preserve math blocks and code blocks by temporarily replacing them
    # These will be restored at the end to ensure they're untouched
    
    # Find all code blocks
    code_block_placeholders = {}
    code_blocks = re.findall(r'```.*?```', content, re.DOTALL)
    for i, block in enumerate(code_blocks):
        placeholder = f"__CODE_BLOCK_{i}__"
        code_block_placeholders[placeholder] = block
        content = content.replace(block, placeholder)
    
    # Find display math blocks ($$...$$)
    display_math_placeholders = {}
    display_matches = []
    for match in re.finditer(r'\$\$(.*?)\$\$', content, re.DOTALL):
        placeholder = f"__DISPLAY_MATH_{len(display_math_placeholders)}__"
        math_text = match.group(0)
        display_math_placeholders[placeholder] = math_text
        display_matches.append((match.start(), placeholder, math_text))
    
    # Replace display math blocks in reverse order to preserve positions
    for pos, placeholder, math_text in sorted(display_matches, reverse=True):
        content = content[:pos] + placeholder + content[pos + len(math_text):]
    
    # Find inline math blocks ($...$)
    # This is trickier because $ is used for both start and end
    inline_math_placeholders = {}
    
    # Simple approach: try to find matched pairs of $ that aren't $$
    i = 0
    processed_content = ""
    in_math = False
    current_math = ""
    math_count = 0
    
    while i < len(content):
        # Check for lone $ (not part of $$)
        if (content[i] == '$' and 
            (i == 0 or content[i-1] != '$') and
            (i >= len(content)-1 or content[i+1] != '$')):
            
            if not in_math:
                # Start of math
                in_math = True
                current_math = "$"
                i += 1
            else:
                # End of math
                in_math = False
                current_math += "$"
                
                # Replace with placeholder
                placeholder = f"__INLINE_MATH_{math_count}__"
                inline_math_placeholders[placeholder] = current_math
                processed_content += placeholder
                
                math_count += 1
                i += 1
        else:
            if in_math:
                current_math += content[i]
            else:
                processed_content += content[i]
            i += 1
    
    # If we ended while still in math, append the incomplete math
    if in_math:
        processed_content += current_math
    
    content = processed_content
    
    # Preserve existing pipe links like [[Note|Display Text]]
    pipe_link_placeholders = {}
    pipe_links = re.findall(r'\[\[([^|]+?)\|([^\]]+?)\]\]', content)
    
    for i, (note_title, display_text) in enumerate(pipe_links):
        full_link = f"[[{note_title}|{display_text}]]"
        placeholder = f"__PIPE_LINK_{i}__"
        pipe_link_placeholders[placeholder] = full_link
        content = content.replace(full_link, placeholder)
    
    # Now fix any broken link formatting
    content = fix_broken_links(content)
    
    # Get existing links to avoid re-linking
    existing_links = get_existing_links(content)
    link_positions = get_link_positions(content)
    
    # Sort note titles by length (descending) to handle longer matches first
    sorted_titles = sorted(note_titles, key=len, reverse=True)
    
    # Collect positions to replace
    replacements = []
    
    # First pass: find all positions to replace
    for title in sorted_titles:
        if title.lower() in existing_links:
            continue  # Skip already linked titles
        
        # Try different case variations of the title
        for variant in get_title_variations(title):
            # Find the title as a standalone word
            pattern = r'\b' + re.escape(variant) + r'\b'
            
            for match in re.finditer(pattern, content):
                start, end = match.span()
                
                # Skip if within a link
                if is_within_existing_link(start, link_positions):
                    continue
                
                # Check for overlap with previous replacements
                overlapping = False
                for r_start, r_end, _ in replacements:
                    if (r_start <= start < r_end) or (r_start < end <= r_end) or (start <= r_start and r_end <= end):
                        overlapping = True
                        break
                
                if not overlapping:
                    replacements.append((start, end, title))
    
    # Sort replacements in reverse order to preserve positions
    replacements.sort(reverse=True, key=lambda x: x[0])
    
    # Apply replacements
    result = content
    for start, end, title in replacements:
        replacement = f"[[{title}]]"
        result = result[:start] + replacement + result[end:]
    
    # Restore pipe links
    for placeholder, original in pipe_link_placeholders.items():
        result = result.replace(placeholder, original)
    
    # Restore math blocks
    for placeholder, original in inline_math_placeholders.items():
        result = result.replace(placeholder, original)
        
    for placeholder, original in display_math_placeholders.items():
        result = result.replace(placeholder, original)
    
    # Restore code blocks
    for placeholder, original in code_block_placeholders.items():
        result = result.replace(placeholder, original)
    
    # If we didn't change anything other than potentially fixing broken links,
    # compare with original to see if we should keep the changes
    if len(replacements) == 0 and result != original_content:
        # We only fixed links but didn't add any new ones
        # Check if the link formatting changes are valid
        if has_valid_math_formatting(result):
            return result
        else:
            # If math formatting got messed up, revert to original
            return original_content
            
    return result


def has_valid_math_formatting(content):
    """Checks if math formatting appears valid"""
    # Count dollars to ensure they're balanced
    dollar_count = content.count('$')
    if dollar_count % 2 != 0:
        return False
        
    # Check for balanced $$ pairs
    double_dollar_count = content.count('$$')
    if double_dollar_count % 2 != 0:
        return False
    
    return True

def process_note(note_path, note_titles, verbose=False, dry_run=False):
    """
    Process a single note file, adding links where appropriate.
    Returns a tuple of (was_modified, modifications_info).
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
        modified_content = autolink_content(content, note_titles)
        
        # Count new links
        new_link_count = len(re.findall(r'\[\[.*?\]\]', modified_content))
        links_added = new_link_count - orig_link_count
        
        # Collect info about modifications
        info = {
            'fixed_broken_links': has_broken_links,
            'fixed_nested_links': has_nested_links,
            'links_added': links_added
        }
        
        # Write back if changed and not in dry run mode
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
    
    return stats