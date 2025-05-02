import click
import os
import re
from pathlib import Path
import base64
import requests
from ..config import get_config
from openai import OpenAI
from ..utils.post_process_formatting import post_process_ocr_output
import pyperclip
import time
from ..utils.ai import generate_note_content
from ..utils.file_operations import sanitize_filename

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image_with_gpt4v(image_path, note_name):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    base64_image = encode_image(image_path)
    
    # Load the OCR prompt from the prompt file
    prompt_path = Path(__file__).parent.parent / "prompts" / "ocr_prompt.txt"
    try:
        with open(prompt_path, 'r') as f:
            prompt_template = f.read()
        # Format the prompt with the note name
        ocr_prompt = prompt_template.format(note_name=note_name)
    except Exception as e:
        # Fallback to basic prompt if file can't be read
        ocr_prompt = f"Please write detailed notes about {note_name}. Transcribe the content from the image faithfully, and then organize that information in an appropriate way. Format the response in markdown."
    
    client = OpenAI()
    
    # Use the most capable available model
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Current best model for vision tasks
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": ocr_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=8192,
            temperature=0.5
        )
    except Exception as e:
        # If gpt-4o fails, try to fall back to vision-preview
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": ocr_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=8192,
            temperature=0.5
        )

    return response.choices[0].message.content

def get_all_note_titles(vault_path):
    """Get all note titles in the vault (without .md extension)"""
    if not vault_path or not os.path.exists(vault_path):
        return []
    
    all_files = os.listdir(vault_path)
    note_titles = [f[:-3] for f in all_files if f.endswith('.md')]
    return note_titles


def get_matching_notes(vault_path, prefix):
    """Get all notes that start with the given prefix"""
    if not vault_path or not os.path.exists(vault_path):
        return []
    
    all_files = os.listdir(vault_path)
    matching_notes = [f[:-3] for f in all_files 
                     if f.endswith('.md') and 
                     f.startswith(prefix)]
    return matching_notes


def fix_broken_links(content):
    """Fix broken links like [[[]][Topic]] to [[Topic]]"""
    # Keep track if we made any changes
    original_content = content
    
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


def is_part_of_existing_link(content, match_start, match_end):
    """Check if a match is part of an existing link"""
    # Find all existing links
    link_positions = []
    for match in re.finditer(r'\[\[.*?\]\]', content):
        link_positions.append((match.start(), match.end()))
    
    # Check if the match is within any existing link
    for start, end in link_positions:
        if start <= match_start and match_end <= end:
            return True
    
    return False


def get_title_case_variations(title):
    """Generate case-insensitive variations of a title for matching"""
    return [
        title,  # Original
        title.lower(),  # All lowercase
        title.upper(),  # All uppercase
        title.capitalize(),  # First letter capitalized
        ' '.join(word.capitalize() for word in title.split())  # Title Case
    ]


def is_within_latex(content, match_start, match_end):
    """Check if a match position is within LaTeX delimiters ($ or $$)"""
    # Split the content by $ to find LaTeX blocks
    chunks = content.split('$')
    
    # If odd number of chunks, we have unclosed LaTeX
    if len(chunks) % 2 == 0:
        return False
    
    # Track position in original string
    pos = 0
    in_latex = False
    
    for i, chunk in enumerate(chunks):
        next_pos = pos + len(chunk)
        
        # If we're in a LaTeX section and our match overlaps with it
        if in_latex and pos <= match_start < next_pos:
            return True
            
        # Add $ length except for last chunk
        if i < len(chunks) - 1:
            next_pos += 1
        
        # Toggle LaTeX state
        in_latex = not in_latex
        pos = next_pos
    
    return False


from .fixed_latex_linking import process_note, process_vault, get_note_titles as get_all_titles

@click.group()
def notes():
    """Note manipulation commands"""
    pass

@notes.command()
@click.argument('note_name', type=click.STRING, required=False)
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information about changes made')
@click.option('--dry-run', '-d', is_flag=True, help='Show what would be changed without making changes')
def autolink(note_name=None, verbose=False, dry_run=False):
    """Automatically add links to words in notes
    
    If note_name is provided, only process that specific note.
    Otherwise, process all notes in the vault.
    """
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        click.echo("Error: Vault path not configured")
        return
    
    # Get all note titles
    note_titles = get_all_titles(vault_path)
    
    if note_name:
        # Process a single note
        note_path = Path(vault_path) / f"{note_name}.md"
        if not note_path.exists():
            click.echo(f"Error: Note {note_name} not found")
            return
        
        # Process the note
        modified, info = process_note(note_path, note_titles, verbose, dry_run)
        
        if 'error' in info:
            click.echo(f"Error processing {note_name}: {info['error']}")
            return
        
        # Report results
        if modified:
            if verbose:
                if info['fixed_broken_links']:
                    click.echo(f"Found and fixed broken link formatting in {note_name}")
                if info['fixed_nested_links']:
                    click.echo(f"Found and fixed nested links in {note_name}")
                if info['links_added'] > 0:
                    click.echo(f"Added {info['links_added']} new links to {note_name}")
            
            if not dry_run:
                click.echo(f"Made changes to {note_name}")
            else:
                click.echo(f"Would make changes to {note_name} (dry run)")
        else:
            click.echo(f"No changes needed for {note_name}")
    else:
        # Process all notes in the vault
        stats = process_vault(vault_path, verbose, dry_run)
        
        if 'error' in stats:
            click.echo(f"Error: {stats['error']}")
            return
        
        # Report any errors
        if stats['errors']:
            for error in stats['errors']:
                click.echo(f"Error: {error}")
        
        # Report summary
        if verbose:
            if stats['broken_links_fixed'] > 0:
                click.echo(f"Fixed broken links in {stats['broken_links_fixed']} files")
            if stats['nested_links_fixed'] > 0:
                click.echo(f"Fixed nested links in {stats['nested_links_fixed']} files")
            if stats['total_links_added'] > 0:
                click.echo(f"Added {stats['total_links_added']} new links across all files")
        
        click.echo(f"Processed {stats['files_processed']} files, {'would modify' if dry_run else 'modified'} {stats['files_modified']} files")

@notes.command()
@click.argument('note_name', type=click.STRING)
@click.option('--fix-math', '-m', is_flag=True, default=True, help='Fix math formatting issues in OCR output')
def ocr(note_name, fix_math=True):
    """Convert screenshots to text"""
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        click.echo("Error: Vault path not configured")
        return

    note_path = Path(vault_path) / f"{note_name}.md"
    if not note_path.exists():
        click.echo(f"Error: Note {note_name} not found")
        return
    
    # Read the note content and find image references
    with open(note_path, 'r') as f:
        content = f.read()
    
    # Find all image references in the ![[image]] format
    image_refs = re.findall(r'!\[\[(.*?)\]\]', content)
    
    if not image_refs:
        click.echo("No image references found in this note")
        return

    modified_content = content
    for image_ref in image_refs:
        image_path = Path(vault_path) / image_ref
        if not image_path.exists():
            click.echo(f"Warning: Image not found: {image_ref}")
            continue
            
        click.echo(f"Processing image: {image_path}")
        try:
            # Get OCR result and apply post-processing
            ocr_content = post_process_ocr_output(process_image_with_gpt4v(str(image_path), note_name))
            
            # Apply additional math formatting fixes if requested
            if fix_math:
                # Import here to avoid circular imports
                from ..commands.format import fix_math_formatting
                ocr_content = fix_math_formatting(ocr_content)
                
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Find the image reference in the content and add OCR result right after it
            image_pattern = f"![[{image_ref}]]"
            ocr_block = f"\n---\nOCR processing: {timestamp}\n\n{ocr_content}\n"
            modified_content = modified_content.replace(image_pattern, f"{image_pattern}{ocr_block}")
            
        except Exception as e:
            click.echo(f"Error processing image: {e}")
    
    # Write the modified content back to the file
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    click.echo(f"OCR results added to: {note_path}")
    
    
def find_problematic_files(vault_path, min_size=10, max_size=50000, check_empty=True, 
                       check_duplicates=False, check_broken_links=False):
    """Find problematic files in the vault"""
    
    problems = {}
    
    # Get all markdown files
    md_files = [f for f in os.listdir(vault_path) if f.endswith('.md')]
    
    # Check for empty or very small files
    if check_empty:
        empty_files = []
        large_files = []
        
        for filename in md_files:
            filepath = os.path.join(vault_path, filename)
            size = os.path.getsize(filepath)
            
            if size < min_size:
                empty_files.append((filename, size))
            elif size > max_size:
                large_files.append((filename, size))
        
        if empty_files:
            problems['empty_files'] = empty_files
        
        if large_files:
            problems['large_files'] = large_files
    
    # Check for duplicate titles (case-insensitive)
    if check_duplicates:
        title_map = {}
        duplicates = {}
        
        for filename in md_files:
            title = filename[:-3]  # Remove .md extension
            lower_title = title.lower()
            
            if lower_title in title_map:
                if lower_title not in duplicates:
                    duplicates[lower_title] = [title_map[lower_title]]
                duplicates[lower_title].append(title)
            else:
                title_map[lower_title] = title
        
        if duplicates:
            problems['duplicate_titles'] = duplicates
    
    # Check for broken internal links
    if check_broken_links:
        broken_links = {}
        note_titles = set(f[:-3] for f in md_files)  # All note titles without .md
        
        # Get all image files in the vault
        image_files = set()
        for root, dirs, files in os.walk(vault_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.heic')):
                    # Store relative path from vault_path
                    rel_path = os.path.relpath(os.path.join(root, file), vault_path)
                    image_files.add(rel_path)
                    # Also add just the filename for images in the root directory
                    image_files.add(file)
        
        for filename in md_files:
            filepath = os.path.join(vault_path, filename)
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create a cleaned version of the content with code blocks and math removed
            cleaned_content = content
            
            # Remove code blocks
            cleaned_content = re.sub(r'```.*?```', '', cleaned_content, flags=re.DOTALL)
            
            # Remove inline math expressions
            # This approach skips the actual parsing of $ signs which causes issues
            # and just removes common patterns
            cleaned_content = re.sub(r'\$[^\$\n]+?\$', '', cleaned_content)
            
            # Remove display math expressions
            cleaned_content = re.sub(r'\$\$.*?\$\$', '', cleaned_content, flags=re.DOTALL)
            
            # Find all embeds (both regular and image)
            all_embeds = re.findall(r'(?:!)?(\[\[(.*?)(?:\|.*?)?\]\])', cleaned_content)
            
            # Find image embeds
            image_embeds = re.findall(r'!\[\[(.*?)(?:\|.*?)?\]\]', cleaned_content)
            
            # Process regular embeds (non-image)
            broken_links_in_file = []
            
            for full_embed, embed_content in all_embeds:
                # Skip if it's an image embed
                if full_embed.startswith('!'):
                    continue
                
                # Extract the link portion (before any | character)
                link = embed_content.split('|')[0].strip() if '|' in embed_content else embed_content
                
                # Skip if it's an existing note
                if link in note_titles:
                    continue
                
                # Skip if it's an image file
                if link in image_files or any(link.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.heic')):
                    continue
                    
                # Add to broken links
                broken_links_in_file.append(embed_content)
            
            if broken_links_in_file:
                broken_links[filename] = broken_links_in_file
        
        if broken_links:
            problems['broken_links'] = broken_links
    
    return problems


def format_problems_report(problems, vault_path):
    """Format the problems report"""
    
    lines = []
    
    # Report empty files
    if 'empty_files' in problems:
        lines.append("Empty or very small files:")
        for filename, size in sorted(problems['empty_files']):
            lines.append(f"- {filename} ({size} bytes)")
        lines.append("")
    
    # Report large files
    if 'large_files' in problems:
        lines.append("Excessively large files:")
        for filename, size in sorted(problems['large_files'], key=lambda x: x[1], reverse=True):
            lines.append(f"- {filename} ({size/1024:.1f} KB)")
        lines.append("")
    
    # Report duplicate titles
    if 'duplicate_titles' in problems:
        lines.append("Duplicate titles (case-insensitive):")
        for title, variants in sorted(problems['duplicate_titles'].items()):
            lines.append(f"- '{title}' has {len(variants)} variants:")
            for variant in variants:
                filepath = os.path.join(vault_path, f"{variant}.md")
                size = os.path.getsize(filepath)
                lines.append(f"  * {variant}.md ({size/1024:.1f} KB)")
        lines.append("")
    
    # Report broken links
    if 'broken_links' in problems:
        lines.append("Broken internal links:")
        for filename, links in sorted(problems['broken_links'].items()):
            lines.append(f"- {filename} contains {len(links)} broken links:")
            for link in sorted(links):
                lines.append(f"  * [[{link}]]")
        lines.append("")
    
    return "\n".join(lines)


def handle_file_cleanup(empty_files, vault_path):
    """Handle cleanup of empty files"""
    
    click.echo("\nProcessing empty files:")
    
    for i, (filename, size) in enumerate(empty_files):
        filepath = os.path.join(vault_path, filename)
        
        click.echo(f"\n[{i+1}/{len(empty_files)}] {filename} ({size} bytes)")
        
        # Show file preview
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            preview = content[:500] + ("..." if len(content) > 500 else "")
            click.echo("\nPreview:")
            click.echo(preview)
        except Exception as e:
            click.echo(f"Error reading file: {e}")
        
        # Ask what to do with this file
        action = click.prompt(
            "\nWhat would you like to do?",
            type=click.Choice(['delete', 'keep', 'skip', 'skip all']),
            default='skip'
        )
        
        if action == 'delete':
            try:
                os.remove(filepath)
                click.echo(f"Deleted {filename}")
            except Exception as e:
                click.echo(f"Error deleting file: {e}")
        elif action == 'skip all':
            click.echo("Skipping remaining files...")
            break


def handle_duplicate_cleanup(duplicates, vault_path):
    """Handle cleanup of duplicate files"""
    
    click.echo("\nProcessing duplicate files:")
    
    for i, (title, variants) in enumerate(duplicates.items()):
        click.echo(f"\n[{i+1}/{len(duplicates)}] Duplicates of '{title}':")
        
        # Display info about each variant
        for j, variant in enumerate(variants):
            filepath = os.path.join(vault_path, f"{variant}.md")
            size = os.path.getsize(filepath)
            modified = os.path.getmtime(filepath)
            modified_date = time.ctime(modified)
            
            # Show preview
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                preview = content[:100] + ("..." if len(content) > 100 else "")
                preview = preview.replace('\n', ' ')
            except Exception:
                preview = "(error reading file)"
            
            click.echo(f"  [{j+1}] {variant}.md ({size/1024:.1f} KB), modified {modified_date}")
            click.echo(f"      Preview: {preview}")
        
        # Ask what to do with these duplicates
        action = click.prompt(
            "\nWhat would you like to do?",
            type=click.Choice(['keep all', 'choose one', 'skip', 'skip all']),
            default='skip'
        )
        
        if action == 'choose one':
            keep_idx = click.prompt(
                "Enter the number of the variant to keep (others will be deleted)",
                type=int,
                default=1
            ) - 1
            
            if 0 <= keep_idx < len(variants):
                # Delete all variants except the chosen one
                for j, variant in enumerate(variants):
                    if j != keep_idx:
                        filepath = os.path.join(vault_path, f"{variant}.md")
                        try:
                            os.remove(filepath)
                            click.echo(f"Deleted {variant}.md")
                        except Exception as e:
                            click.echo(f"Error deleting file: {e}")
            else:
                click.echo("Invalid selection, skipping...")
        elif action == 'skip all':
            click.echo("Skipping remaining duplicates...")
            break


def handle_broken_links(broken_links, vault_path):
    """Handle cleanup of broken links"""
    
    click.echo("\nProcessing broken links:")
    
    for i, (filename, links) in enumerate(broken_links.items()):
        click.echo(f"\n[{i+1}/{len(broken_links)}] {filename} has {len(links)} broken links")
        
        filepath = os.path.join(vault_path, filename)
        
        # Read file content
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Ask what to do with this file's broken links
        action = click.prompt(
            "\nWhat would you like to do?",
            type=click.Choice(['fix all', 'list and choose', 'skip', 'skip all']),
            default='skip'
        )
        
        if action == 'fix all':
            # Replace all broken links with plain text
            modified_content = content
            for link in links:
                modified_content = modified_content.replace(f"[[{link}]]", link)
            
            # Write back to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            click.echo(f"Fixed all broken links in {filename}")
            
        elif action == 'list and choose':
            # Show each broken link and ask what to do
            modified_content = content
            
            for j, link in enumerate(links):
                click.echo(f"\n  [{j+1}/{len(links)}] Broken link: [[{link}]]")
                
                link_action = click.prompt(
                    "  What would you like to do?",
                    type=click.Choice(['remove brackets', 'delete link', 'keep', 'skip rest']),
                    default='remove brackets'
                )
                
                if link_action == 'remove brackets':
                    modified_content = modified_content.replace(f"[[{link}]]", link)
                    click.echo(f"  Removed brackets from [[{link}]]")
                elif link_action == 'delete link':
                    modified_content = modified_content.replace(f"[[{link}]]", "")
                    click.echo(f"  Deleted link [[{link}]]")
                elif link_action == 'skip rest':
                    break
            
            # Write back to file if changed
            if modified_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                click.echo(f"Saved changes to {filename}")
        
        elif action == 'skip all':
            click.echo("Skipping remaining files with broken links...")
            break


@notes.command()
@click.option('--min-size', '-m', default=10, type=int, help='Minimum note size in bytes (default: 10)')
@click.option('--max-size', '-M', default=50000, type=int, help='Maximum note size in bytes (default: 50000)')
@click.option('--empty-only', '-e', is_flag=True, help='Only check for empty files')
@click.option('--duplicate-titles', '-d', is_flag=True, help='Check for case-insensitive duplicate titles')
@click.option('--broken-links', '-b', is_flag=True, help='Check for broken internal links')
@click.option('--all', '-a', is_flag=True, help='Run all checks')
def check_garbage(min_size=10, max_size=50000, empty_only=False, duplicate_titles=False, broken_links=False, all=False):
    """Check for problematic files in the vault
    
    This command identifies various issues with your notes:
    - Empty or nearly empty notes (less than min-size bytes)
    - Excessively large notes (more than max-size bytes)
    - Duplicate notes (case-insensitive title duplicates)
    - Notes with broken internal links
    
    Results are displayed in the terminal and can be saved to clipboard.
    """
    import time
    
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        click.echo("Error: Vault path not configured")
        return
    
    # Run all checks if --all flag is set
    if all:
        empty_only = duplicate_titles = broken_links = True
    
    # Default to empty check if no specific checks are selected
    if not any([empty_only, duplicate_titles, broken_links]):
        empty_only = True
    
    problems = find_problematic_files(
        vault_path, 
        min_size=min_size, 
        max_size=max_size,
        check_empty=empty_only or all,
        check_duplicates=duplicate_titles or all, 
        check_broken_links=broken_links or all
    )
    
    if not problems:
        click.echo("No problems found in your vault!")
        return
    
    # Display results
    total_issues = sum(len(files) for files in problems.values())
    click.echo(f"\nFound {total_issues} potential issues in your vault:\n")
    
    # Format results for display and clipboard
    result_text = format_problems_report(problems, vault_path)
    click.echo(result_text)
    
    # Ask to copy to clipboard
    if click.confirm("\nDo you want to copy this report to your clipboard?"):
        try:
            pyperclip.copy(result_text)
            click.echo("Report copied to clipboard!")
        except Exception as e:
            click.echo(f"Failed to copy to clipboard: {e}")
    
    # Ask to delete empty files
    if problems.get('empty_files') and click.confirm("\nDo you want to handle empty files?"):
        handle_file_cleanup(problems['empty_files'], vault_path)
    
    # Ask to handle duplicates
    if problems.get('duplicate_titles') and click.confirm("\nDo you want to handle duplicate files?"):
        handle_duplicate_cleanup(problems['duplicate_titles'], vault_path)
    
    # Ask to fix broken links
    if problems.get('broken_links') and click.confirm("\nDo you want to fix broken links?"):
        handle_broken_links(problems['broken_links'], vault_path)

@notes.command()
@click.option('--topic', '-t', required=True, help='The topic or concept for the note.')
@click.option('--output-dir', '-o', default=None, type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Directory within the vault to save the note (default: vault root).')
@click.option('--llm-model', default=None, help='Specify the LLM model to use (e.g., gpt-4o-mini). Uses default if not set.')
def generate(topic, output_dir, llm_model):
    """Generates a draft note for a given topic using an LLM."""

    vault_path_str = get_config().get('vault_path')
    if not vault_path_str:
        click.secho("Error: Vault path not configured. Run 'olib config setup' first.", fg="red")
        return

    vault_path = Path(vault_path_str)

    # Determine save directory
    save_dir = vault_path
    if output_dir:
        # Ensure output_dir is relative to vault_path or handle absolute paths appropriately
        # For simplicity, let's assume output_dir is relative for now
        save_dir = vault_path / output_dir
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            click.secho(f"Error creating output directory '{save_dir}': {e}", fg="red")
            return

    # Generate filename from topic
    # Use a utility to remove invalid characters for filenames
    safe_filename = sanitize_filename(topic) + ".md"
    output_filepath = save_dir / safe_filename

    click.echo(f"Generating note for topic: '{topic}'...")
    if llm_model:
        click.echo(f"Using LLM model: {llm_model}")

    # Call the AI function
    generated_content = generate_note_content(topic, model_name=llm_model) if llm_model else generate_note_content(topic)

    if not generated_content:
        click.secho("Failed to generate note content from LLM.", fg="red")
        return

    # Save the content
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(generated_content)
        click.secho(f"Successfully generated and saved note to:", fg="green")
        click.echo(str(output_filepath))
    except IOError as e:
        click.secho(f"Error saving generated note to '{output_filepath}': {e}", fg="red")