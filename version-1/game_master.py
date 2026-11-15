
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.8-flash"

OFFLINE_TESTING = (
    os.getenv("OFFLINE_TESTING", "false").lower() == "true"
)

client = None

if not OFFLINE_TESTING:
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is missing from .env")
    client = genai.Client(api_key=API_KEY)


def create_game_chat(system_prompt):
    if OFFLINE_TESTING:
        return {
            "mode": "offline",
            "system_prompt": system_prompt,
            "history": [],
            "trials": 0,
            "curse": 0,
            "inventory": [],
            "escaped": False,
            "game_over": False,
        }

    return client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=900,
            thinking_config=types.ThinkingConfig(
                thinking_level="low"
            ),
        ),
    )


def get_status(chat):
    inventory = ",".join(chat["inventory"]) or "none"

    return (
        f"[[GAME_STATE: trials={chat['trials']}; "
        f"curse={chat['curse']}; inventory={inventory}; "
        f"escaped={str(chat['escaped']).lower()}; "
        f"game_over={str(chat['game_over']).lower()}]]"
    )



def offline_response(chat, message):
    text = message.lower().strip()

    is_submission = text.startswith("submit ")

    if is_submission:
        text = text[len("submit "):].strip()

    def reply(content):
        return content + "\n\n" + get_status(chat)

    # Show the complete opening scene.
    if "begin the game" in text:
        return reply(
            "You awaken inside the Hall of the Forgotten King.\n\n"
            "A massive stone Sentinel watches you from its throne. "
            "Three trials stand between you and freedom. "
            "Three incorrect answers will turn you into stone.\n\n"
            "Five objects surround you:\n\n"
            "1. Giant Sentinel\n"
            "2. Rune Tablet\n"
            "3. Forgotten Mural\n"
            "4. Sealed Reliquary\n"
            "5. Obsidian Gate\n\n"
            "Your journey begins now. What will you do?"
        )


    if chat["escaped"]:
        return reply("🏆 You have escaped the Cursed Dungeon!")

    if chat["game_over"]:
        return reply("💀 You have become a stone guardian.")

    # Object exploration
    if "rune tablet" in text or "tablet" in text:
        return reply(
            "The tablet reveals three clues: "
            "Sun means beginning, Crown means ruler, "
            "and Moon represents night. "
            "Submit the correct sequence."
        )

    if "forgotten mural" in text or "mural" in text:
        return reply(
            "The mural depicts sunrise, a crowned ruler, "
            "and the moon appearing at night."
        )

    if "giant sentinel" in text or "guardian" in text:
        return reply(
            "The Sentinel warns you: "
            "Three trials stand between you and freedom."
        )

    if "reliquary" in text or "chest" in text:
        return reply(
            "The inscription reads: Seven stars above, "
            "two moons below, one sun at dawn, "
            "and four chains bind the forgotten."
        )

    if "obsidian gate" in text or "gate" in text:
        return reply(
            "The gate requires the rewards of the first "
            "two trials and the answer to the final riddle."
        )

    # Trial 1
    if chat["trials"] == 0 and is_submission:
        normalized = re.sub(r"[^a-z]", "", text)

        if normalized == "suncrownmoon":
            chat["trials"] = 1
            chat["inventory"].append("Iron Key")

            return reply(
                "✨ TRIAL 1 COMPLETED! "
                "You earned the Iron Key."
            )

        return wrong_answer(chat, reply)

    # Trial 2
    if chat["trials"] == 1 and is_submission:
        if text == "7214":
            chat["trials"] = 2
            chat["inventory"].append("Ancient Seal")

            return reply(
                "✨ TRIAL 2 COMPLETED! "
                "You earned the Ancient Seal."
            )

        return wrong_answer(chat, reply)

    # Trial 3
    if chat["trials"] == 2 and is_submission:
        if text.strip().lower() == "memory":
            if (
                "Iron Key" in chat["inventory"]
                and "Ancient Seal" in chat["inventory"]
            ):
                chat["trials"] = 3
                chat["escaped"] = True
                chat["game_over"] = True
                chat["inventory"].append("Lost Horizon Map")

                return reply(
                    "🏆 FINAL TRIAL COMPLETED! "
                    "The Obsidian Gate opens. "
                    "You escaped the Cursed Dungeon!"
                )

            return reply(
                "You know the answer, but you still need "
                "the Iron Key and Ancient Seal."
            )

        return wrong_answer(chat, reply)

    if is_submission:
        return reply(
            "That is not an active puzzle submission. "
            "Explore the room to find your next challenge."
        )

    return reply(
        "The dungeon awaits. Examine the Giant Sentinel, "
        "Rune Tablet, Forgotten Mural, Sealed Reliquary "
        "or Obsidian Gate."
    )


def wrong_answer(chat, reply):
    chat["curse"] += 1

    if chat["curse"] >= 3:
        chat["game_over"] = True
        return reply(
            "💀 Three incorrect submissions! "
            "You have turned to stone."
        )

    return reply(
        f"Incorrect answer. Curse marks: {chat['curse']}/3."
    )


def send_game_message(chat, message):
    if OFFLINE_TESTING:
        chat["history"].append(message)
        response = offline_response(chat, message)
        chat["history"].append(response)
        return response

    delays = [3, 8, 15]

    for attempt in range(4):
        try:
            start_time = time.perf_counter()
            response = chat.send_message(message)

            print(
                f"\nGemini response time: "
                f"{time.perf_counter() - start_time:.2f} seconds"
            )

            if response.usage_metadata:
                print(
                    "Input tokens:",
                    response.usage_metadata.prompt_token_count,
                )
                print(
                    "Output tokens:",
                    response.usage_metadata.candidates_token_count,
                )

            return response.text or "The guardian remains silent..."

        except Exception as error:
            error_message = str(error)

            if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                return (
                    "The Gemini daily quota has been reached. "
                    "Your progress is safe. Please use offline testing."
                )

            if "503" in error_message or "UNAVAILABLE" in error_message:
                if attempt < 3:
                    wait = delays[attempt]
                    print(f"Gemini is busy. Retrying in {wait} seconds...")
                    time.sleep(wait)
                else:
                    return "The guardian is temporarily unavailable."

            else:
                return f"Gemini connection error: {error_message}"
