import os
import logging
import time
from openai import OpenAI, OpenAIError, RateLimitError, APIError, APIConnectionError, AuthenticationError
from tenacity import retry, stop_after_attempt, wait_exponential

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

def validate_response(response):
    """Validate the OpenAI API response"""
    if not response or not response.choices:
        logger.error("Invalid response format from OpenAI API")
        return False
    
    joke = response.choices[0].message.content.strip()
    if not joke or len(joke) < 10:  # Basic validation for joke content
        logger.error("Generated joke content is too short or empty")
        return False
    
    return True

# Initialize OpenAI client with latest version
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

@retry(
    wait=wait_exponential(multiplier=2, min=2, max=10),
    stop=stop_after_attempt(3),
    retry_error_callback=lambda retry_state: None
)
def generate_joke(category):
    """
    Generate a family-friendly joke using OpenAI API based on category
    
    Args:
        category (str): The category of joke to generate
        
    Returns:
        str: Generated joke text or None if generation fails
    """
    try:
        # Validate API key before making request
        if not validate_api_key():
            logger.error("Invalid or missing API key")
            return None

        logger.info(f"Attempting to generate joke for category: {category}")
        
        # Optimized prompt for reduced token usage
        system_prompt = """You are a family-friendly comedian. Create short, clean jokes suitable for all ages."""
        
        user_prompt = f"Generate a short, family-friendly {category} joke (2-3 sentences max)."
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=100,
            temperature=0.6,
            presence_penalty=0.4,
            frequency_penalty=0.4
        )
        
        # Validate response
        if not validate_response(response):
            return None

        joke = response.choices[0].message.content.strip()
        logger.info("Successfully generated joke")
        return joke
        
    except AuthenticationError as e:
        logger.error(f"Authentication error: Invalid API key - {str(e)}")
        return None
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {str(e)}")
        raise  # Let retry handle this
    except APIConnectionError as e:
        logger.error(f"API Connection error: {str(e)}")
        raise  # Let retry handle this
    except APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return None
    except OpenAIError as e:
        logger.error(f"General OpenAI error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during joke generation: {str(e)}")
        return None
