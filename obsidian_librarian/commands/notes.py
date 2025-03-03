import click
import os
from pathlib import Path
import base64
import requests
import re
from ..config import get_config
from openai import OpenAI
from ..utils.post_process_formatting import post_process_ocr_output

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image_with_gpt4v(image_path, note_name):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    base64_image = encode_image(image_path)
    
    client = OpenAI()
    
    response = client.chat.completions.create(
        model="gpt-4.5-preview", # This model is not available in the API
        # model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Please write detailed notes about {note_name}. Transcribe the content from the image faithfully, and then organize that information in an appropriate way. Format the response in markdown."
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

def get_matching_notes(vault_path, prefix):
    """Get all notes that start with the given prefix"""
    if not vault_path or not os.path.exists(vault_path):
        return []
    
    all_files = os.listdir(vault_path)
    matching_notes = [f[:-3] for f in all_files 
                     if f.endswith('.md') and 
                     f.startswith(prefix)]
    return matching_notes

@click.group()
def notes():
    """Note manipulation commands"""
    pass

@notes.command()
def format():
    """Format individual notes"""
    click.echo("Formatting notes...")

@notes.command()
def fill():
    """Complete partial notes"""
    click.echo("Filling notes...")

@notes.command()
@click.argument('note_name', type=click.STRING, autocompletion=get_matching_notes)
def ocr(note_name):
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
            ocr_content = post_process_ocr_output(process_image_with_gpt4v(str(image_path), note_name))
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
