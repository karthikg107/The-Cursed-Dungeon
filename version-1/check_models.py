
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY is missing from .env")
else:
    client = genai.Client(api_key=api_key)

    print("\nGemini models available to your project:\n")

    for model in client.models.list():
        name = getattr(model, "name", "")
        actions = getattr(model, "supported_actions", [])

        if "gemini" in name.lower():
            print(f"Model: {name}")
            print(f"Supported actions: {actions}")
            print("-" * 45)
