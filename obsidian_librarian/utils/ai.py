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
DEFAULT_LLM_MODEL = "gpt-4o"

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

def get_prerequisites_from_llm(
    note_content: str,
    model_name: str = DEFAULT_LLM_MODEL,
    original_topic: Optional[str] = None
) -> Optional[List[str]]:
    """
    Uses an LLM to identify prerequisite concepts for a given note's content.

    Args:
        note_content: The text content of the note.
        model_name: The identifier for the LLM model to use.
        original_topic: The name of the main topic being analyzed (for context).

    Returns:
        A list of prerequisite topic names, or None if an error occurs.
    """
    client = _get_openai_client()
    if not client:
        return None

    # --- Construct the prompt with context ---
    if original_topic:
        context_phrase = f" specifically as it relates to understanding the main subject: '{original_topic}'"
        focus_phrase = f" strictly necessary, foundational prerequisite concepts for grasping '{original_topic}'"
        avoid_phrase = f" Avoid tangential topics not directly needed for '{original_topic}'."
    else:
        # Fallback if original_topic is not provided
        context_phrase = ""
        focus_phrase = " essential, foundational prerequisite concepts"
        avoid_phrase = ""

    # --- REVISED PROMPT ---
    prompt = f"""Analyze the following note content about '{original_topic}'{context_phrase}.
Identify the {focus_phrase} mentioned or implied in the text. Your goal is to list the specific concepts or skills someone *must* understand *before* they can properly grasp '{original_topic}'.

CRITICAL INSTRUCTIONS:
1.  **Be Specific:** Do NOT list extremely broad fields. For example, if analyzing "Quantum Computing", do NOT list "Mathematics" or "Physics". Instead, list the *specific* areas required, such as "Linear Algebra", "Complex Numbers", "Probability Theory", or "Quantum Mechanics".
2.  **Identify Foundational Sub-Topics:** If a necessary prerequisite is itself a large topic (like "Quantum Mechanics"), identify the *key sub-concepts* within it that are essential for understanding '{original_topic}' (e.g., "Superposition", "Entanglement"). List these specific sub-concepts directly.
3.  **Focus on Necessity:** List only concepts that are truly prerequisite – knowledge that is built upon. Avoid listing related concepts or applications unless they are fundamental building blocks.
4.  **Atomic Knowledge:** Aim for concepts that represent relatively atomic pieces of knowledge required.
5.  **Exclude Original Topic:** Do NOT include the main topic '{original_topic}' itself in the list.
6.  **Format:** Output *only* a Python list of strings, where each string is a specific prerequisite concept. Example: ["Linear Algebra", "Complex Numbers", "Superposition", "Entanglement", "Basic Probability"]

Note Content:
---
{note_content[:3000]}
---
Prerequisites List (Python format):"""
    # --- END REVISED PROMPT ---

    # logger.debug(f"LLM Prompt for prerequisites:\n{prompt}") # Keep debug log

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                # --- Updated System Message ---
                {"role": "system", "content": "You are an expert academic analyst specializing in identifying granular prerequisite knowledge dependencies."},
                # --- End Updated System Message ---
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, # Lower temperature further for more focused, less "creative" prerequisite identification
            max_tokens=1000 # Keep max_tokens reasonable
        )
        # ... (rest of the function: parsing the response, error handling) ...
        raw_response = response.choices[0].message.content
        # logger.debug(f"LLM raw response for prerequisites: {raw_response}") # Keep debug log

        # Attempt to parse the response as a Python list
        try:
            # Basic cleaning: remove potential markdown code blocks
            cleaned_response = raw_response.strip().strip('`').strip()
            if cleaned_response.startswith("python"):
                 cleaned_response = cleaned_response[len("python"):].strip()

            # Use ast.literal_eval for safe evaluation of list string
            import ast
            prerequisites = ast.literal_eval(cleaned_response)
            if isinstance(prerequisites, list) and all(isinstance(item, str) for item in prerequisites):
                 # Further clean up whitespace in each item
                 cleaned_prerequisites = [item.strip() for item in prerequisites if item.strip()]
                 # Filter out the original topic again just in case LLM included it
                 if original_topic:
                     # Case-insensitive filtering
                     original_topic_lower = original_topic.lower()
                     cleaned_prerequisites = [p for p in cleaned_prerequisites if p.strip().lower() != original_topic_lower]
                 # --- Add filtering for overly broad terms (as a fallback) ---
                 broad_terms_to_filter = {"mathematics", "physics", "computer science", "science", "theory"} # Add more if needed
                 final_prerequisites = [p for p in cleaned_prerequisites if p.lower() not in broad_terms_to_filter]
                 if len(final_prerequisites) < len(cleaned_prerequisites):
                     logger.info(f"Filtered out overly broad terms from LLM prerequisite list.")
                 # --- End filtering ---
                 return final_prerequisites # Return the filtered list
            else:
                logger.warning(f"LLM response for prerequisites was not a valid list of strings: {raw_response}")
                return [] # Return empty list if format is wrong but response received
        except (SyntaxError, ValueError) as e:
            logger.warning(f"Could not parse LLM prerequisite response as a list: {e}. Response: {raw_response}")
            # Fallback: Try simple line splitting if list parsing fails
            lines = [line.strip('-* ').strip() for line in raw_response.split('\n') if line.strip()]
            if lines:
                 logger.info("Falling back to line splitting for prerequisites.")
                 if original_topic:
                     original_topic_lower = original_topic.lower()
                     lines = [p for p in lines if p.strip().lower() != original_topic_lower]
                 # Apply broad term filtering to fallback as well
                 broad_terms_to_filter = {"mathematics", "physics", "computer science", "science", "theory"}
                 lines = [p for p in lines if p.lower() not in broad_terms_to_filter]
                 return lines
            return [] # Return empty list if parsing fails

    except Exception as e:
        logger.error(f"Error calling OpenAI API for prerequisites ({model_name}): {e}", exc_info=True) # Log traceback
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
    # --- Use the helper function to get the client ---
    client = _get_openai_client()
    if not client:
        # Error message is handled within _get_openai_client
        return None
    # --- End client retrieval ---

    # 2. Define the prompt for note generation
    #    This prompt encourages markdown formatting and a concise explanation.
    prompt = f"""
    Please generate a technical and concise note about the following topic: "{topic}". These notes are meant to be for light retrieval, i.e. technical and rigorous while being concise. Compression/concision up to the point of not losing key information.

    Format the response as simple markdown. Include:
    1. A brief definition or explanation of the core concept.
    2. Key aspects or components, possibly using bullet points.
    3. An example or analogy, if appropriate.
    5. Do NOT include a title in the markdown (the filename will serve as the title).
    6. Do NOT add any introductory or concluding phrases like "Here is the note:" or "I hope this helps.". Just provide the markdown content directly.
    """

    # --- Remove Requesting log (if desired, or keep if useful) ---
    # logger.info(f"Requesting note generation for topic: {topic} using model {model_name}")
    # --- End Remove ---
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates concise, informative notes in markdown format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, # Lower temperature for more focused, less creative output
            max_tokens=500   # Limit response length
            # Timeout is handled by the client from _get_openai_client
        )

        content = response.choices[0].message.content

        if not content:
            logger.error("LLM returned an empty response for note generation.")
            return None

        logger.info(f"LLM generated note content for topic: {topic}")
        # Basic cleanup: remove leading/trailing whitespace
        return content.strip()

    # --- Keep existing error handling ---
    except OpenAIError as e:
        logger.error(f"OpenAI API error during note generation: {e}")
        # Use click echo if available, otherwise print
        try:
            import click
            click.secho(f"Error communicating with OpenAI: {e}", fg="red")
        except ImportError:
            print(f"Error communicating with OpenAI: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during note generation: {e}", exc_info=True) # Add exc_info for better debugging
        try:
            import click
            click.secho(f"An unexpected error occurred during note generation: {e}", fg="red")
        except ImportError:
            print(f"An unexpected error occurred: {e}")
        return None
    # --- End error handling ---

def generate_note_content_from_topic(
    topic_name: str,
    model_name: str = DEFAULT_LLM_MODEL,
    popular_tags: Optional[List[str]] = None,
    original_topic: Optional[str] = None
) -> Optional[Tuple[str, List[str]]]:
    """
    Uses an LLM to generate placeholder content and suggest tags for a given topic.

    Args:
        topic_name: The name of the topic for the new note.
        model_name: The identifier for the LLM model to use.
        popular_tags: Optional list of popular tags for context.
        original_topic: Optional name of the main topic this is a prerequisite for.

    Returns:
        A tuple containing (generated_content, suggested_tags), or None if an error occurs.
    """
    client = _get_openai_client()
    if not client:
        return None

    # --- Construct prompt for note generation ---
    context_phrase = f" This topic is needed as a prerequisite for understanding '{original_topic}'." if original_topic else ""
    tag_context = f" Consider suggesting relevant tags, potentially drawing inspiration from these common tags in the knowledge base: {popular_tags}" if popular_tags else ""

    # --- MODIFIED PROMPT ---
    prompt = f"""Generate a technically detailed and rigorous explanatory note for the topic: "{topic_name}".{context_phrase}
This note serves as foundational knowledge for someone learning related, more advanced topics. Aim for clarity and accuracy, suitable for someone needing to understand this concept before moving on.

The note should:
1. Provide a clear, technically precise definition of the core concept.
2. Explain its key aspects, principles, or components in sufficient detail. Use bullet points or numbered lists where appropriate for structure.
3. Include a simple example, analogy, or use case if it aids understanding, ensuring it doesn't oversimplify the technical nature.
4. Be formatted in standard Markdown. Do NOT include an H1 title matching the topic name (it will be added automatically).
5. Conclude with a section suggesting relevant technical tags for this topic. Format this section *exactly* as:
Suggested Tags: #tag1 #tag2 #another-tag

{tag_context}

Generate *only* the Markdown content below, starting directly with the explanation:
"""
    # --- END MODIFIED PROMPT ---

    # --- Remove Requesting log ---
    # logger.info(f"Requesting note generation from LLM ({model_name}) for topic '{topic_name}'.")
    # --- End Remove ---
    # logger.debug(f"LLM Prompt for note generation:\n{prompt}") # Keep debug log

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                # --- Updated System Message ---
                {"role": "system", "content": "You are an expert technical writer and educator. Generate detailed, accurate, and foundational Markdown notes."},
                # --- End Updated System Message ---
                {"role": "user", "content": prompt}
            ],
            temperature=0.4, # Slightly lower temp for more factual/less creative output
            max_tokens=800 # Increase max tokens to allow for more detailed content
        )
        raw_response = response.choices[0].message.content
        # logger.debug(f"LLM raw response for note generation: {raw_response}") # Keep debug log

        # --- Parse content and tags ---
        content_parts = raw_response.split("Suggested Tags:")
        generated_content = content_parts[0].strip()
        suggested_tags = []
        if len(content_parts) > 1:
            tag_line = content_parts[1].strip()
            # Extract tags (handles #tag, tag, #tag-name)
            suggested_tags = [tag.strip('#') for tag in tag_line.split() if tag.strip()]

        if not generated_content:
             logger.warning(f"LLM generated empty content for topic '{topic_name}'.")
             return None # Treat empty content as failure

        return generated_content, suggested_tags
        # --- End parsing ---

    except Exception as e:
        logger.error(f"Error calling OpenAI API for note generation ({model_name}): {e}", exc_info=True) # Log traceback
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
