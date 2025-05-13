import click
import os
from pathlib import Path
import base64
# import json # No longer needed for this direct API call
# import requests # Will use the OpenAI client instead
from openai import OpenAI # Add OpenAI import
from ..config import get_config

def encode_image(image_path):
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

    # Consider using a shared prompt or loading from a file like in notes.py for more complex prompts
    ocr_prompt = f"Please write detailed notes about {note_name}. Transcribe the content from the image faithfully, and then organize that information in an appropriate way. Format the response in markdown."

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

@click.command()
@click.argument('note_name')
def ocr_note(note_name):
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

    # Find all images in the note's directory
    note_dir = note_path.parent
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    images = [f for f in note_dir.glob(f"{note_name}.*") if f.suffix.lower() in image_extensions]

    if not images:
        click.echo("No images found for this note")
        return

    for image_path in images:
        click.echo(f"Processing image: {image_path}")
        try:
            content = process_image_with_gpt4v(str(image_path), note_name)
            
            # Create new markdown file with OCR results
            output_path = note_dir / f"{note_name}_ocr.md"
            with open(output_path, 'w') as f:
                f.write(content)
            
            click.echo(f"OCR results saved to: {output_path}")
        except Exception as e:
            click.echo(f"Error processing image: {e}")
