import os
import openai

openai.api_key = os.environ.get('OPENAI_API_KEY')

def generate_joke(category):
    """Generate a joke using OpenAI API based on category"""
    try:
        prompt = f"Generate a family-friendly joke in the category '{category}'. The joke should be concise and suitable for all ages. Format: Only return the joke text, nothing else."
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a family-friendly joke generator. Keep jokes clean, simple, and suitable for all ages."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return None
