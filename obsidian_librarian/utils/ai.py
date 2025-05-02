import os
import json
import logging
from openai import OpenAI, OpenAIError, Timeout
from typing import Optional, List, Tuple # Import Optional, List, Tuple
from ..config import get_config # Import config loading function

# Configure logging
# logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# Use the root logger configured in cli.py instead of reconfiguring here
logger = logging.getLogger(__name__)

# Consider making the model name configurable later
DEFAULT_LLM_MODEL = "gpt-4o-mini"

# --- Define default timeouts (in seconds) ---
# --- Increase timeout to 120 seconds (2 minutes) ---
DEFAULT_API_TIMEOUT = 120.0 # Timeout for the API call itself
# --- End timeout increase ---
DEFAULT_CONNECT_TIMEOUT = 10.0 # Timeout for establishing connection
# --- End timeout definitions ---

def _get_openai_client() -> Optional[OpenAI]:
    """Helper to initialize OpenAI client, checking config and env vars."""
    config = get_config()
    api_key = config.get('api_key')

    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        logger.error("OpenAI API key not found in config file or OPENAI_API_KEY environment variable.")
        # Use click echo if available, otherwise print
        try:
            import click
            click.secho("Error: OpenAI API key is not set. Please run 'olib config setup' or set the OPENAI_API_KEY environment variable.", fg="red")
        except ImportError:
             print("Error: OpenAI API key is not set. Please run 'olib config setup' or set the OPENAI_API_KEY environment variable.")
        return None

    # --- Initialize client with timeouts ---
    try:
        client = OpenAI(
            api_key=api_key,
            timeout=DEFAULT_API_TIMEOUT, # Overall request timeout
            # connect_timeout=DEFAULT_CONNECT_TIMEOUT # Often less necessary, but can be added
        )
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        try:
            import click
            click.secho(f"Error initializing OpenAI client: {e}", fg="red")
        except ImportError:
            print(f"Error initializing OpenAI client: {e}")
        return None
    # --- End client initialization ---

def get_prerequisites_from_llm(note_content: str, model_name: str = DEFAULT_LLM_MODEL) -> Optional[list[str]]:
    """
    Uses an LLM to identify prerequisite concepts for the given note content.

    Args:
        note_content: The text content of the note to analyze.
        model_name: The OpenAI model to use.

    Returns:
        A list of prerequisite concept strings, or None if an error occurs.
    """
    # 1. Try getting API key from config file
    config = get_config()
    api_key = config.get('api_key')

    # 2. If not in config, try environment variable
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")

    # 3. If still not found, log error and exit
    if not api_key:
        logging.error("OpenAI API key not found in config file or OPENAI_API_KEY environment variable.")
        print("Error: OpenAI API key is not set. Please run 'olib config setup' or set the OPENAI_API_KEY environment variable.")
        return None

    client = _get_openai_client()
    if not client:
        return None

    prompt = f"""Analyze the following text. Identify the top 3-5 essential prerequisite concepts required for a deep understanding. Focus on foundational ideas assumed by the text. Output ONLY a JSON list of strings, like ["Concept Name 1", "Concept Name 2", "Concept Name 3"].

TEXT:
---
{note_content}
---

JSON prerequisites list:"""

    logger.info(f"Sending request to LLM ({model_name}) to find prerequisites...")
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert in identifying conceptual prerequisites."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Lower temperature for more deterministic output
            response_format={ "type": "json_object" } # Request JSON output directly if supported
        )

        # Debugging: Print raw response content
        # logging.debug(f"LLM Raw Response: {response.choices[0].message.content}")

        content = response.choices[0].message.content
        if not content:
            logging.error("LLM returned an empty response.")
            return None

        # Attempt to parse the JSON content
        try:
            # Find the JSON part if the model didn't strictly adhere to ONLY JSON
            json_start = content.find('[')
            json_end = content.rfind(']')
            if json_start != -1 and json_end != -1:
                json_str = content[json_start:json_end+1]
                prerequisites = json.loads(json_str)
                if isinstance(prerequisites, list) and all(isinstance(item, str) for item in prerequisites):
                    logger.info(f"LLM identified prerequisites: {prerequisites}")
                    return prerequisites
                else:
                    logger.error(f"LLM response JSON was not a list of strings: {json_str}")
                    return None
            else:
                logger.error(f"Could not find valid JSON list in LLM response: {content}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}\nResponse content: {content}")
            return None

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        print(f"Error communicating with OpenAI: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during LLM interaction: {e}")
        print(f"An unexpected error occurred: {e}")
        return None

def generate_note_content(topic: str, model_name: str = DEFAULT_LLM_MODEL) -> Optional[str]:
    """
    Uses an LLM to generate explanatory content for a given topic.

    Args:
        topic: The topic or concept to generate a note about.
        model_name: The OpenAI model to use.

    Returns:
        A string containing the generated markdown content, or None if an error occurs.
    """
    # 1. Get API Key (reuse logic from get_prerequisites_from_llm or refactor)
    config = get_config()
    api_key = config.get('api_key')
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.error("OpenAI API key not found in config or environment variables.")
        print("Error: OpenAI API key not configured. Set it via `olib config set api_key YOUR_KEY` or the OPENAI_API_KEY environment variable.")
        return None

    client = OpenAI(api_key=api_key)

    # 2. Define the prompt for note generation
    #    This prompt encourages markdown formatting and a concise explanation.
    prompt = f"""
    Please generate a concise explanatory note about the following topic: "{topic}"

    Format the response as simple markdown. Include:
    1. A brief definition or explanation of the core concept.
    2. Key aspects or components, possibly using bullet points.
    3. An example or analogy, if appropriate.
    4. Keep the tone informative and neutral.
    5. Do NOT include a title in the markdown (the filename will serve as the title).
    6. Do NOT add any introductory or concluding phrases like "Here is the note:" or "I hope this helps.". Just provide the markdown content directly.
    """

    logger.info(f"Requesting note generation for topic: {topic} using model {model_name}")
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates concise, informative notes in markdown format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, # Lower temperature for more focused, less creative output
            max_tokens=500   # Limit response length
        )

        content = response.choices[0].message.content

        if not content:
            logger.error("LLM returned an empty response for note generation.")
            return None

        logger.info(f"LLM generated note content for topic: {topic}")
        # Basic cleanup: remove leading/trailing whitespace
        return content.strip()

    except OpenAIError as e:
        logger.error(f"OpenAI API error during note generation: {e}")
        print(f"Error communicating with OpenAI: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during note generation: {e}")
        print(f"An unexpected error occurred: {e}")
        return None

def generate_note_content_from_topic(
    topic: str,
    model_name: str = DEFAULT_LLM_MODEL,
    popular_tags: Optional[List[str]] = None
) -> Optional[Tuple[str, List[str]]]:
    """
    Uses an LLM to generate markdown content for a given topic and suggest relevant tags.

    Args:
        topic: The concept/topic for the note.
        model_name: The OpenAI model to use.
        popular_tags: An optional list of popular tags to suggest from.

    Returns:
        A tuple containing (generated_markdown_content, suggested_tags_list),
        or None if an error occurs. suggested_tags_list may be empty.
    """
    client = _get_openai_client()
    if not client:
        return None

    # --- Build the prompt ---
    prompt_lines = [
        f"Generate a concise, informative markdown note explaining the concept: '{topic}'.",
        "Include:",
        "1. A brief definition or explanation.",
        "2. Key ideas or components.",
        "3. (Optional) A simple example if applicable.",
        "\nFormat the output as clean markdown, suitable for a knowledge base note.",
        "Start directly with the content (no preamble like 'Here is the note:')."
    ]

    # --- Add tag suggestion part to prompt if popular tags are provided ---
    if popular_tags:
        tags_string = ", ".join(popular_tags)
        prompt_lines.extend([
            "\n---\n",
            "After the markdown content, on a new line starting with 'Suggested Tags:', list any relevant tags for this topic from the following list ONLY:",
            f"[{tags_string}]",
            "List only the tag names, separated by commas. If none seem relevant, write 'Suggested Tags: None'."
        ])
    # --- End tag suggestion prompt ---

    prompt = "\n".join(prompt_lines)
    # --- End prompt building ---


    logger.info(f"Sending request to LLM ({model_name}) to generate content and tags for '{topic}' (Timeout: {DEFAULT_API_TIMEOUT}s)...")
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert technical writer, creating clear and concise explanations and suggesting relevant tags."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=700 # Increased slightly for tags
            # Timeout is handled by the client instance now
        )

        full_response_content = response.choices[0].message.content
        if not full_response_content:
            logger.error(f"LLM returned an empty response for topic '{topic}'.")
            return None

        # --- Parse content and tags ---
        content_part = full_response_content
        suggested_tags_list = []
        tag_section_marker = "\nSuggested Tags:"

        if tag_section_marker in content_part:
            parts = content_part.split(tag_section_marker, 1)
            content_part = parts[0].strip() # The main markdown content
            tags_line = parts[1].strip()
            if tags_line.lower() != 'none':
                 # Split by comma, strip whitespace and '#' if present
                 suggested_tags_list = [tag.strip().strip('#') for tag in tags_line.split(',') if tag.strip()]
            logger.info(f"LLM suggested tags for '{topic}': {suggested_tags_list}")
        else:
             logger.warning(f"Could not find tag suggestion marker in LLM response for '{topic}'.")
        # --- End parsing ---


        if content_part:
            logger.info(f"LLM generated content for '{topic}'.")
            # Return content and the parsed tags
            return content_part.strip(), suggested_tags_list
        else:
            # Handle case where parsing might leave content empty (e.g., only tags returned)
            logger.error(f"LLM response for '{topic}' seemed to contain only tags or was malformed after parsing.")
            return None


    except Timeout as e:
        logger.error(f"OpenAI API request timed out while generating content for '{topic}': {e}")
        try:
            import click
            click.secho(f"Error: OpenAI request timed out (> {DEFAULT_API_TIMEOUT}s) for '{topic}'. Try again later or check network.", fg="red")
        except ImportError:
            print(f"Error: OpenAI request timed out (> {DEFAULT_API_TIMEOUT}s) for '{topic}'.")
        return None
    except OpenAIError as e:
        logger.error(f"OpenAI API error while generating content for '{topic}': {e}")
        # Use click echo if available, otherwise print
        try:
            import click
            click.secho(f"Error communicating with OpenAI while generating content for '{topic}': {e}", fg="red")
        except ImportError:
            print(f"Error communicating with OpenAI while generating content for '{topic}': {e}")
        return None
    except Exception as e: # Catch other potential errors
        logger.error(f"An unexpected error occurred during content generation for '{topic}': {e}")
        try:
            import click
            click.secho(f"An unexpected error occurred during content generation for '{topic}': {e}", fg="red")
        except ImportError:
            print(f"An unexpected error occurred during content generation for '{topic}': {e}")
        return None

# Example usage (for testing purposes)
if __name__ == '__main__':
    test_content = """
    Nash Equilibrium represents a state in game theory where no player can improve their outcome by unilaterally changing their strategy, assuming all other players' strategies remain constant. It's crucial for understanding strategic interactions in economics, politics, and biology.
    """
    print("Testing LLM prerequisite generation...")
    # Ensure OPENAI_API_KEY is set in your environment for this test
    prereqs = get_prerequisites_from_llm(test_content)
    if prereqs:
        print(f"Identified Prerequisites: {prereqs}")
    else:
        print("Failed to get prerequisites.")

    print("\nTesting LLM note generation...")
    test_topic = "Nash Equilibrium"
    generated_content = generate_note_content(test_topic)
    if generated_content:
        print(f"--- Generated Content for '{test_topic}' ---")
        print(generated_content)
        print("--- End Generated Content ---")
    else:
        print(f"Failed to generate content for '{test_topic}'.") 
