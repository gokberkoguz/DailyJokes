import os
import logging
import json
from openai import OpenAI, OpenAIError, APIError, AuthenticationError, RateLimitError, APIConnectionError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_api_key():
    """Validate the OpenAI API key."""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.error("OpenAI API key is missing")
        return False

    if not api_key.startswith('sk-'):
        logger.error("Invalid OpenAI API key format")
        return False

    return True


# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))


def sanitize_and_parse_response(response_text):
    """
    Sanitize and parse JSON text from the response.

    Args:
        response_text (str): Raw JSON-like text from the API response.

    Returns:
        list: Parsed JSON object if valid; otherwise, an empty list.
    """
    try:
        # Remove code block markers (e.g., ```json ... ```)
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Strip "```json"
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Strip trailing "```"

        # Attempt to parse as JSON
        jokes = json.loads(response_text.strip())
        if isinstance(jokes, list) and all(isinstance(joke, str) for joke in jokes):
            return jokes
        else:
            logger.error("Response is not a valid JSON list of strings")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed: {e}")
        logger.info("Attempting to clean the response and parse again...")

        # Additional sanitization if needed
        try:
            # Clean and ensure it starts and ends with square brackets
            sanitized_response = response_text.strip()
            if not sanitized_response.startswith("["):
                sanitized_response = "[" + sanitized_response.split("[", 1)[-1]
            if not sanitized_response.endswith("]"):
                sanitized_response = sanitized_response.rsplit("]", 1)[0] + "]"

            # Parse sanitized response
            jokes = json.loads(sanitized_response)
            if isinstance(jokes, list) and all(isinstance(joke, str) for joke in jokes):
                return jokes
        except Exception as clean_error:
            logger.error(f"Failed to parse sanitized response: {clean_error}")
    return []


def generate_bulk_jokes(category,category_description, count=10):
    """
    Generate multiple jokes in one API call.

    Args:
        category (str): The category of jokes to generate.
        count (int): The number of jokes to generate.

    Returns:
        list: A list of jokes.
    """
    try:
        # Validate API key
        if not validate_api_key():
            logger.error("Invalid or missing API key")
            return []
        logger.info(f"Attempting to generate {count} jokes in the {category} category")

        # Create a single prompt to generate multiple jokes
        system_prompt = """
        You are an offensive comedian specializing in dark humor, catering to adults with a taste for edgy and sarcastic jokes. Stay within the bounds of dark comedy, avoiding content that promotes hate speech or illegal themes.
        """

        user_prompt = f"""
        Generate {count} unique, edgy, and dark humor jokes in the "{category}" category. 
        The category description is: "{category_description}". Use this description to tailor the jokes specifically to the context provided.

        Additional guidelines:
        - Ensure the jokes are concise, witty, and formatted as a JSON list of strings.
        - Avoid generic or unrelated content and stick closely to the category description.
        - Avoid any form of hate speech, explicit slurs, or offensive stereotypes.
        - Ensure the jokes remain in good taste for adults with a dark sense of humor, aligned with the provided category description.

        Return the output strictly as valid JSON. Example:
        [
            "Why does Zoro never get lost? Because he doesn't even know where he's supposed to be!",
            "Luffy walked into a bar. The bartender said, 'Stretch yourself to another place!'"
        ]
        """
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2000,  # Adjust token usage to fit the jokes
            temperature=0.7,
            presence_penalty=0.6,
            frequency_penalty=0.5
        )

        if response and response.choices:
            response_text = response.choices[0].message.content.strip()
            logger.debug(f"Raw response from OpenAI: {response_text}")

            # Parse the sanitized response
            jokes = sanitize_and_parse_response(response_text)
            if jokes:
                logger.info(f"Successfully generated {len(jokes)} jokes")
                return jokes
        else:
            logger.error("Invalid response format or no jokes generated")
        return []
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        return []
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {str(e)}")
        return []
    except APIConnectionError as e:
        logger.error(f"API connection error: {str(e)}")
        return []
    except APIError as e:
        logger.error(f"API error: {str(e)}")
        return []
    except OpenAIError as e:
        logger.error(f"OpenAI error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return []


if __name__ == "__main__":
    category = "dark humor"
    jokes = generate_bulk_jokes(category, count=10)
    if jokes:
        print("Generated Jokes:")
        for idx, joke in enumerate(jokes, start=1):
            print(f"{idx}. {joke}")
    else:
        print("No jokes were generated.")
