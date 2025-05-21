"""
OCR command for converting images to text.

This module provides a CLI command to extract text from images in markdown notes
using OpenAI's GPT-4 Vision model and format the results.
"""

import click
import os
from pathlib import Path
import base64
import re
import datetime
from openai import OpenAI

from ..config import get_config
from ..utils.post_process_formatting import post_process_ocr_output
from .utilities.format_fixer import FormatFixer


def encode_image(image_path):
    """Encode an image file to base64 for API transmission."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def process_image_with_gpt4v(image_path, note_name):
    """Process an image using GPT-4 Vision and return the extracted text."""
    config = get_config()
    api_key = config.get('api_key')
    if not api_key:
        raise ValueError("OpenAI API key not found in config. Run 'olib config setup'.")

    client = OpenAI(api_key=api_key)
    base64_image = encode_image(image_path)

    # Load prompt from file if it exists
    prompt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                             "prompts", "ocr_prompt.txt")
    
    if os.path.exists(prompt_file):
        with open(prompt_file, 'r') as f:
            ocr_prompt_template = f.read()
        ocr_prompt = ocr_prompt_template.replace("{note_name}", note_name)
    else:
        # Fallback prompt
        ocr_prompt = (
            f"Please transcribe the content from this image related to {note_name}. "
            f"Format the response in clean markdown. "
            f"Convert all mathematical notation to proper LaTeX format with $ and $$ delimiters. "
            f"Use single $ for inline math and $$ for display math."
        )

    try:
        # Try with newest model first
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": ocr_prompt
                }, {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                }]
            }],
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        # Fallback to previous model if newest fails
        click.echo(f"gpt-4o failed with {e}, trying gpt-4-vision-preview...")
        try:
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": ocr_prompt
                    }, {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }]
                }],
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as final_e:
            raise Exception(f"OpenAI API Error after fallback: {final_e}")


def extract_image_paths_from_md(md_path):
    """Extract image references from markdown file."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all image references in the format ![[image.png]]
    image_references = re.findall(r'!\[\[(.*?)\]\]', content)
    
    # Map to full paths
    note_dir = md_path.parent
    image_paths = []
    for ref in image_references:
        # Handle relative paths within the vault
        img_path = note_dir / ref
        if img_path.exists():
            image_paths.append(img_path)
    
    return image_paths


@click.command()
@click.argument('note_name')
@click.option('--keep-timestamps', is_flag=True, help='Keep OCR processing timestamps in output')
def ocr_note(note_name, keep_timestamps=False):
    """Convert images in notes to text using OCR."""
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        click.echo("Error: Vault path not configured")
        return

    note_path = Path(vault_path) / f"{note_name}.md"
    if not note_path.exists():
        click.echo(f"Error: Note {note_name} not found")
        return
    
    # Create formatter instance
    formatter = FormatFixer(verbose=True)
    
    # Get image paths
    image_paths = extract_image_paths_from_md(note_path)
    if not image_paths:
        click.echo("No image references found in note")
        return
    
    # Read file content
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process each image
    successful_count = 0
    for image_path in image_paths:
        click.echo(f"Processing image: {image_path.name}")
        try:
            # Get OCR text
            raw_ocr = process_image_with_gpt4v(str(image_path), note_name)
            
            # Process OCR text
            processed_ocr = post_process_ocr_output(raw_ocr)
            
            # Add timestamp if requested
            if keep_timestamps:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                processed_ocr = f"---\n\nOCR processing: {timestamp}\n\n{processed_ocr}"
            
            # Format math
            formatted_ocr = formatter.apply_math_fixes(processed_ocr)
            
            # Replace image reference
            image_ref = f"!\\[\\[{re.escape(image_path.name)}\\]\\]"
            if re.search(image_ref, content):
                content = re.sub(
                    image_ref,
                    f"![[{image_path.name}]]\n{formatted_ocr}",
                    content
                )
                successful_count += 1
            else:
                click.echo(f"  Warning: Could not find reference to {image_path.name}")
        except Exception as e:
            click.echo(f"Error processing image {image_path.name}: {e}")
    
    # Update file
    if successful_count > 0:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        click.echo(f"OCR results added for {successful_count} image(s) in: {note_path.name}")
    else:
        click.echo("No OCR results were added to the note.")