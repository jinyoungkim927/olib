import click
import os
from pathlib import Path
import base64
import re
import datetime
# import json # No longer needed for this direct API call
# import requests # Will use the OpenAI client instead
from openai import OpenAI # Add OpenAI import
from ..config import get_config
from ..utils.post_process_formatting import clean_raw_llm_output, post_process_ocr_output
from .utilities.format_fixer import FormatFixer

def encode_image(image_path):
    """Encode an image file to base64 for API transmission."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image_with_gpt4v(image_path, note_name):
    """Process an image using GPT-4 Vision and return the text description."""
    config = get_config()
    api_key = config.get('api_key')
    if not api_key:
        # Fallback or specific error for this command if API key not in config
        # For consistency with notes.py, let's raise ValueError
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
            f"Convert all mathematical notation to proper LaTeX format with $ and $$ delimiters. "
            f"Format the response in clean markdown with appropriate headers, lists, and paragraphs. "
            f"Be particularly careful with LaTeX formatting - use single $ for inline math and $$ for display math."
        )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Or "gpt-4-vision-preview" if preferred as primary
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
            max_tokens=4096 # Max tokens can be adjusted as needed
        )
        return response.choices[0].message.content
    except Exception as e:
        # Fallback to gpt-4-vision-preview if gpt-4o fails
        click.echo(f"gpt-4o failed with {e}, trying gpt-4-vision-preview...")
        try:
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
    """Convert images in notes to text using OCR"""
    config = get_config()
    vault_path = config.get('vault_path')
    
    if not vault_path:
        click.echo("Error: Vault path not configured")
        return

    note_path = Path(vault_path) / f"{note_name}.md"
    if not note_path.exists():
        click.echo(f"Error: Note {note_name} not found")
        return
    
    # Create the FormatFixer instance
    formatter = FormatFixer(verbose=True)
    
    # Process images referenced in the markdown file
    image_paths = extract_image_paths_from_md(note_path)
    
    if not image_paths:
        click.echo("No image references found in note")
        return
    
    # Read the original file content
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process each referenced image
    successful_ocr_count = 0
    for image_path in image_paths:
        click.echo(f"Processing image: {image_path.name}")
        try:
            # Get OCR content
            raw_ocr_content = process_image_with_gpt4v(str(image_path), note_name)
            
            # Apply comprehensive OCR-specific cleanup
            # First apply general LLM output cleanup
            cleaned_content = clean_raw_llm_output(raw_ocr_content)
            
            # Then apply more comprehensive OCR formatting
            cleaned_content = post_process_ocr_output(cleaned_content)
            
            # Add timestamp if requested
            if keep_timestamps:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                processed_content = f"---\n\nOCR processing: {timestamp}\n\n{cleaned_content}"
            else:
                processed_content = cleaned_content
            
            # Find the image reference and replace it
            image_ref_pattern = f"!\\[\\[{re.escape(image_path.name)}\\]\\]"
            if re.search(image_ref_pattern, content):
                # Apply final formatting using FormatFixer
                # This will handle math blocks, spacing, and other formatting details
                formatted_content = formatter.apply_math_fixes(processed_content)
                
                # Replace the image reference with both the image and the OCR text
                content = re.sub(
                    image_ref_pattern,
                    f"![[{image_path.name}]]\n{formatted_content}",
                    content
                )
                successful_ocr_count += 1
            else:
                click.echo(f"  Warning: Could not find reference to {image_path.name} in the note")
        except Exception as e:
            click.echo(f"Error processing image {image_path.name}: {e}")
    
    # Write the updated content back to the file
    if successful_ocr_count > 0:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        click.echo(f"OCR results added for {successful_ocr_count} image(s) in: {note_path.name}")
    else:
        click.echo("No OCR results were added to the note.")
    
