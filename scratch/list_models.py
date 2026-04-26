import os
import json
from urllib import request as urllib_request
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No API key found.")
else:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        with urllib_request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            print("Available Models:")
            for model in data.get('models', []):
                print(f" - {model['name'].replace('models/', '')}")
    except Exception as e:
        print(f"Error: {e}")
