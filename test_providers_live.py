import os
import sys
from dotenv import load_dotenv

# Add current directory to path to import provider modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from provider.openai_provider import OpenAIProvider
from provider.gemini_provider import GeminiProvider

load_dotenv()

def test_openai():
    print("\n--- Testing OpenAI Provider ---")
    try:
        provider = OpenAIProvider()
        response = provider.generate("Hello, say 'OpenAI is working!'")
        print(f"Response: {response}")
        return True
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return False

def test_gemini():
    print("\n--- Testing Gemini Provider ---")
    try:
        provider = GeminiProvider()
        response = provider.generate("Hello, say 'Gemini is working!'")
        print(f"Response: {response}")
        return True
    except Exception as e:
        print(f"Gemini Error: {e}")
        return False

if __name__ == "__main__":
    openai_ok = test_openai()
    gemini_ok = test_gemini()
    
    print("\n--- Final Summary ---")
    print(f"OpenAI Status: {'✅ Working' if openai_ok else '❌ Failed'}")
    print(f"Gemini Status: {'✅ Working' if gemini_ok else '❌ Failed'}")
