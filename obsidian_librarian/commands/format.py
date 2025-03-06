import click
import os
import re
from pathlib import Path
from ..config import get_config
from ..utils.post_process_formatting import format_latex, convert_latex_delimiters
import pyperclip

# Should be a group command with subcommands for formatting and screenshot conversion
@click.group()
def format_notes():
    """Format notes and convert screenshots to text
    
    Automatically format your notes according to configured style guidelines
    and convert screenshots to searchable text.
    """
    pass

@format_notes.command()
def format():
    click.echo("Formatting...")

@format_notes.command()
def screenshot():
    click.echo("Screenshot...")

def fix_math_formatting(content):
    """
    Fix common math formatting issues in markdown:
    1. Balance $ and $$ delimiters
    2. Remove spaces between $ and content
    3. Fix OCR-related formatting issues with math expressions
    4. Convert LaTeX delimiters from \[ \] to $$...$$ format
    5. Convert alignment environments to proper format
    """
    # First, we preserve code blocks to avoid modifying code
    code_blocks = {}
    for i, match in enumerate(re.finditer(r'```.*?```', content, re.DOTALL)):
        placeholder = f"__CODE_BLOCK_{i}__"
        code_blocks[placeholder] = match.group(0)
        content = content.replace(match.group(0), placeholder)
    
    # Convert LaTeX delimiters from \[ \] to $$...$$ format
    content = convert_latex_delimiters(content)
    
    # Remove spaces between $ and content for inline math
    content = re.sub(r'\$ (.*?) \$', r'$\1$', content)
    content = re.sub(r'\$([ ]+)(.*?)([ ]+)\$', r'$\2$', content)
    
    # Standardize display math formatting
    content = re.sub(r'\$\$([ ]+)(.*?)([ ]+)\$\$', r'$$\2$$', content, flags=re.DOTALL)
    
    # Fix common OCR issues with math expressions
    
    # Replace "S" with "$" when it's likely meant to be a math delimiter
    # Look for patterns like "S x S" where S should be $
    content = re.sub(r'([^a-zA-Z])S ([^a-zA-Z]+) S([^a-zA-Z])', r'\1$ \2 $\3', content)
    
    # Balance unmatched delimiters
    # Count $ signs
    dollar_count = content.count('$') - content.count('$$') * 2
    if dollar_count % 2 != 0:
        # Try to detect if ending $ is missing
        matches = list(re.finditer(r'\$([^\$]+)$', content))
        if matches:
            # Add missing closing $
            match = matches[-1]
            content = content[:match.end()] + "$" + content[match.end():]
    
    # Check for unbalanced $$
    double_dollar_count = content.count('$$')
    if double_dollar_count % 2 != 0:
        # Try to detect where a closing $$ might be missing
        last_double_dollar = content.rfind('$$')
        if last_double_dollar != -1:
            # Add closing $$ at the end of the paragraph
            next_blank_line = content.find('\n\n', last_double_dollar)
            if next_blank_line != -1:
                content = content[:next_blank_line] + "\n$$" + content[next_blank_line:]
            else:
                content = content + "\n$$"
    
    # Fix alignment environments
    # Convert LaTeX align environments that might have been mangled by OCR
    content = re.sub(r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', 
                     lambda m: f"$$\n{m.group(1).strip()}\n$$", 
                     content, flags=re.DOTALL)
    
    # Restore code blocks
    for placeholder, original in code_blocks.items():
        content = content.replace(placeholder, original)
    
    return content

@format_notes.command()
@click.argument('note_name', type=click.STRING, required=False)
@click.option('--fix-math', '-m', is_flag=True, help='Fix math formatting issues')
@click.option('--dry-run', '-d', is_flag=True, help='Show changes without writing to file')
def fix(note_name=None, fix_math=True, dry_run=False):
    """Fix common formatting issues in notes
    
    This command fixes various formatting issues:
    - Math formatting: spaces between $ delimiters, unbalanced delimiters
    - LaTeX conversion: convert \[ \] to $$...$$ format
    - OCR artifacts: fix common OCR errors in math expressions
    
    If note_name is provided, only that note is processed.
    Otherwise, you'll be asked which notes to process.
    """
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        click.echo("Error: Vault path not configured")
        return
    
    if note_name:
        # Process a single note
        note_path = Path(vault_path) / f"{note_name}.md"
        if not note_path.exists():
            click.echo(f"Error: Note {note_name} not found")
            return
        
        process_note_formatting(note_path, fix_math=fix_math, dry_run=dry_run)
    else:
        # Ask which notes to process
        notes_choice = click.prompt(
            "Which notes would you like to process?",
            type=click.Choice(['single', 'recent', 'all']),
            default='single'
        )
        
        if notes_choice == 'single':
            # Ask for note name
            available_notes = [f[:-3] for f in os.listdir(vault_path) if f.endswith('.md')]
            if not available_notes:
                click.echo("No notes found in vault")
                return
            
            # Display a few notes as examples
            click.echo("\nExample notes:")
            for note in sorted(available_notes)[:5]:
                click.echo(f"- {note}")
            
            note_name = click.prompt("Enter note name")
            note_path = Path(vault_path) / f"{note_name}.md"
            if not note_path.exists():
                click.echo(f"Error: Note {note_name} not found")
                return
            
            process_note_formatting(note_path, fix_math=fix_math, dry_run=dry_run)
            
        elif notes_choice == 'recent':
            # Process 5 most recently modified notes
            md_files = [os.path.join(vault_path, f) for f in os.listdir(vault_path) if f.endswith('.md')]
            recent_files = sorted(md_files, key=os.path.getmtime, reverse=True)[:5]
            
            for file_path in recent_files:
                click.echo(f"\nProcessing {os.path.basename(file_path)[:-3]}...")
                process_note_formatting(file_path, fix_math=fix_math, dry_run=dry_run)
                
        elif notes_choice == 'all':
            if not click.confirm("This will process all notes in your vault. Continue?"):
                return
                
            md_files = [os.path.join(vault_path, f) for f in os.listdir(vault_path) if f.endswith('.md')]
            
            with click.progressbar(md_files, label='Processing notes') as bar:
                for file_path in bar:
                    process_note_formatting(file_path, fix_math=fix_math, dry_run=dry_run, quiet=True)
            
            click.echo("All notes processed!")

def process_note_formatting(note_path, fix_math=True, dry_run=False, quiet=False):
    """
    Process a single note to fix formatting issues.
    Returns True if changes were made, False otherwise.
    """
    try:
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified_content = content
        
        # Apply formatting fixes
        if fix_math:
            modified_content = fix_math_formatting(modified_content)
        
        # Check if any changes were made
        if content == modified_content:
            if not quiet:
                click.echo(f"No changes needed for {os.path.basename(note_path)}")
            return False
            
        # Show diff if in dry run mode
        if dry_run:
            if not quiet:
                click.echo(f"Would update {os.path.basename(note_path)} with these changes:")
                
                # Show a simple diff
                if len(content) > 1000:
                    click.echo("(File too large for complete diff, showing sample changes)")
                    
                for i, (old_line, new_line) in enumerate(zip(content.split('\n'), modified_content.split('\n'))):
                    if old_line != new_line:
                        click.echo(f"- {old_line}")
                        click.echo(f"+ {new_line}")
                        # Only show a few diff lines
                        if i > 10:
                            click.echo("...")
                            break
        else:
            # Write changes
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            if not quiet:
                click.echo(f"Updated {os.path.basename(note_path)}")
                
        return True
        
    except Exception as e:
        if not quiet:
            click.echo(f"Error processing {os.path.basename(note_path)}: {e}")
        return False