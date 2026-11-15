
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Gemini API key not found in .env")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.8-flash"



def create_game_chat(system_prompt):
    """Create a faster Gemini conversation."""

    return client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=900,
            thinking_config=types.ThinkingConfig(
                thinking_level="low"
            )
        )
    )




def send_game_message(chat, message):
    """Send a message with retries for temporary API failures."""

    delays = [3, 8, 15]

    for attempt in range(4):
        try:
            start_time = time.perf_counter()

            response = chat.send_message(message)

            elapsed = time.perf_counter() - start_time
            print(f"\nGemini response time: {elapsed:.2f} seconds")

            if response.usage_metadata:
                print(
                    "Input tokens:",
                    response.usage_metadata.prompt_token_count
                )
                print(
                    "Output tokens:",
                    response.usage_metadata.candidates_token_count
                )

            return response.text or "The guardian remains silent..."

        except Exception as error:

            error_message = str(error)

            if "503" in error_message or "UNAVAILABLE" in error_message:

                if attempt < 3:
                    wait = delays[attempt]
                    print(
                        f"Gemini is busy. Retrying in {wait} seconds..."
                    )
                    time.sleep(wait)
                else:
                    return (
                        "The dungeon guardian is temporarily unavailable. "
                        "Your progress is safe. Please try again shortly."
                    )

            else:
                return f"Gemini connection error: {error_message}"
