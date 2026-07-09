import os
from openai import OpenAI
from dotenv import load_dotenv

def verify_openai():
    # Load from the .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Use the key provided by the user in .env
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in .env file.")
        return

    print(f"Verifying user key starting with: {api_key[:10]}...")

    try:
        # Explicitly setting base_url to OpenAI's official API to bypass system proxy
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.openai.com/v1"
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=5
        )
        print(f"✅ Success! Response: {response.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"❌ Error verifying OpenAI key: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    verify_openai()
