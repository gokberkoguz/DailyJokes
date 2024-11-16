import os
import logging
from openai import OpenAI, OpenAIError, RateLimitError, APIError, APIConnectionError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client with latest version
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

def generate_joke(category):
    """
    Generate a family-friendly joke using OpenAI API based on category
    
    Args:
        category (str): The category of joke to generate
        
    Returns:
        str: Generated joke text or None if generation fails
        
    Raises:
        Various OpenAI exceptions handled within the function
    """
    try:
        logger.info(f"Attempting to generate joke for category: {category}")
        
        # Enhanced prompt engineering for better joke generation
        system_prompt = """You are a professional comedian specialized in family-friendly humor.
        Your jokes should be:
        - Clean and appropriate for all ages
        - Easy to understand
        - Cleverly crafted
        - Related to the given category
        - Original and engaging
        - Between 2-4 sentences maximum
        
        Format your response as a complete joke without any additional text or explanations."""
        
        user_prompt = f"""Generate a family-friendly joke about {category}.
        The joke should be witty but clean, and suitable for all ages.
        Do not include any offensive, controversial, or inappropriate content."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=150,
            temperature=0.7,
            presence_penalty=0.6,
            frequency_penalty=0.8
        )
        
        joke = response.choices[0].message.content.strip()
        logger.info("Successfully generated joke")
        return joke
        
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {str(e)}")
        return None
    except APIConnectionError as e:
        logger.error(f"API Connection error: {str(e)}")
        return None
    except APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return None
    except OpenAIError as e:
        logger.error(f"General OpenAI error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during joke generation: {str(e)}")
        return None
