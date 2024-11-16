import os
import logging
from openai import OpenAI, OpenAIError, APIError, AuthenticationError, RateLimitError, APIConnectionError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_api_key():
    """Validate the OpenAI API key"""
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


def generate_bulk_jokes(category, count=10):
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
        system_prompt = """You are a family-friendly comedian. Generate a list of short, clean jokes suitable for all ages."""

        user_prompt = f"""
                        Generate {count} unique, family-friendly jokes in the {category} category. 
                        Return the response as a JSON list of strings. For example:
                        
                        [
                            "Why don't skeletons fight each other? They don't have the guts.",
                            "What do you call a bear with no teeth? A gummy bear."
                        ]
                        """
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2000,  # Adjust token usage to fit 100 jokes
            temperature=0.7,
            presence_penalty=0.6,
            frequency_penalty=0.5
        )

        # Extract and split jokes into a list
        if response and response.choices:
            response_text = response.choices[0].message.content.strip()
            jokes = [line.strip() for line in response_text.split("\n") if line.strip()]
            print(jokes)
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


# Generate 100 jokes in the "animal" category
if __name__ == "__main__":
    category = "animal"
    jokes = generate_bulk_jokes(category, count=10)
    for idx, joke in enumerate(jokes, start=1):
        print(f"{idx}. {joke}")
