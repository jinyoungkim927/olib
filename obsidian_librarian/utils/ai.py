import os
import json
import logging
from openai import OpenAI, OpenAIError
from typing import Optional # Import Optional
from ..config import get_config # Import config loading function

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Consider making the model name configurable later
DEFAULT_LLM_MODEL = "gpt-4o-mini"

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

    client = OpenAI(api_key=api_key)

    prompt = f"""Analyze the following text. Identify the top 3-5 essential prerequisite concepts required for a deep understanding. Focus on foundational ideas assumed by the text. Output ONLY a JSON list of strings, like ["Concept Name 1", "Concept Name 2", "Concept Name 3"].

TEXT:
---
{note_content}
---

JSON prerequisites list:"""

    logging.info(f"Sending request to LLM ({model_name}) to find prerequisites...")
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
                    logging.info(f"LLM identified prerequisites: {prerequisites}")
                    return prerequisites
                else:
                    logging.error(f"LLM response JSON was not a list of strings: {json_str}")
                    return None
            else:
                logging.error(f"Could not find valid JSON list in LLM response: {content}")
                return None
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from LLM response: {e}\nResponse content: {content}")
            return None

    except OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        print(f"Error communicating with OpenAI: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during LLM interaction: {e}")
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

    logging.info(f"Requesting note generation for topic: {topic} using model {model_name}")
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
            logging.error("LLM returned an empty response for note generation.")
            return None

        logging.info(f"LLM generated note content for topic: {topic}")
        # Basic cleanup: remove leading/trailing whitespace
        return content.strip()

    except OpenAIError as e:
        logging.error(f"OpenAI API error during note generation: {e}")
        print(f"Error communicating with OpenAI: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during note generation: {e}")
        print(f"An unexpected error occurred: {e}")
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