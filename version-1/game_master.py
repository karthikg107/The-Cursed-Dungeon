
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

PRIMARY_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.7-flash"

OFFLINE_TESTING = (
    os.getenv("OFFLINE_TESTING", "false").lower() == "true"
)

client = None

if not OFFLINE_TESTING:
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is missing from .env")

    client = genai.Client(api_key=API_KEY)


def create_model_chat(model, system_prompt, history=None):
    return client.chats.create(
        model=model,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=900,
            thinking_config=types.ThinkingConfig(
                thinking_level="low"
            ),
        ),
        history=history or [],
    )


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

    return {
        "mode": "gemini",
        "system_prompt": system_prompt,
        "active_model": PRIMARY_MODEL,
        "client_chat": create_model_chat(
            PRIMARY_MODEL,
            system_prompt
        ),
        "game_state": {
            "trials": 0,
            "curse": 0,
            "inventory": [],
            "escaped": False,
            "game_over": False,
        },
    }


def get_status(chat):
    inventory = ",".join(chat["inventory"]) or "none"

    return (
        f"[[GAME_STATE: trials={chat['trials']}; "
        f"curse={chat['curse']}; inventory={inventory}; "
        f"escaped={str(chat['escaped']).lower()}; "
        f"game_over={str(chat['game_over']).lower()}]]"
    )


def parse_game_state(response_text):
    pattern = (
        r"\[\[GAME_STATE:\s*"
        r"trials=(\d+);\s*"
        r"curse=(\d+);\s*"
        r"inventory=(.*?);\s*"
        r"escaped=(true|false);\s*"
        r"game_over=(true|false)\]\]"
    )

    match = re.search(pattern, response_text, re.IGNORECASE)

    if not match:
        return None

    inventory_text = match.group(3).strip()

    inventory = (
        []
        if inventory_text.lower() == "none"
        else [item.strip() for item in inventory_text.split(",")]
    )

    return {
        "trials": int(match.group(1)),
        "curse": int(match.group(2)),
        "inventory": inventory,
        "escaped": match.group(4).lower() == "true",
        "game_over": match.group(5).lower() == "true",
    }


def switch_to_offline(chat):
    state = chat.get(
        "game_state",
        {
            "trials": 0,
            "curse": 0,
            "inventory": [],
            "escaped": False,
            "game_over": False,
        },
    )

    chat.clear()

    chat.update({
        "mode": "offline",
        "system_prompt": "",
        "history": [],
        "trials": state["trials"],
        "curse": state["curse"],
        "inventory": list(state["inventory"]),
        "escaped": state["escaped"],
        "game_over": state["game_over"],
    })


SUBMISSION_PREFIXES = (
    "submit ",
    "the answer is ",
    "my answer is ",
    "answer:",
    "answer ",
)

TRIAL_1_SYMBOLS = {"sun", "crown", "moon"}


def looks_like_direct_answer(chat, text):
    """Return True if a message without 'submit' is clearly a puzzle answer."""
    if chat["trials"] == 0:
        words = re.findall(r"[a-z]+", text)
        return len(words) == 3 and set(words) <= TRIAL_1_SYMBOLS

    if chat["trials"] == 1:
        return re.fullmatch(r"\d{4}", text) is not None

    if chat["trials"] == 2:
        # Only the exact word is accepted without a prefix. A wrong
        # single word (e.g. "hello") should not cost a curse mark.
        return text.strip(" .!") == "memory"

    return False


def offline_response(chat, message):
    text = message.lower().strip()

    # A message counts as a puzzle submission if it starts with one of
    # these prefixes (e.g. "submit 7214" or "the answer is memory").
    is_submission = False

    for prefix in SUBMISSION_PREFIXES:
        if text.startswith(prefix):
            is_submission = True
            text = text[len(prefix):].strip(" :")
            break

    # Natural answers without a prefix are accepted only when they
    # clearly look like an answer to the CURRENT trial. This keeps
    # normal exploration from being counted as a wrong answer.
    if not is_submission and looks_like_direct_answer(chat, text):
        is_submission = True

    def reply(content):
        return content + "\n\n" + get_status(chat)

    # Opening scene
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
        if text.strip(" .") == "7214":
            chat["trials"] = 2
            chat["inventory"].append("Ancient Seal")

            return reply(
                "✨ TRIAL 2 COMPLETED! "
                "You earned the Ancient Seal."
            )

        return wrong_answer(chat, reply)

    # Trial 3
    if chat["trials"] == 2 and is_submission:
        if text.strip(" .!").lower() == "memory":
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

    if "inventory" in text:
        items = ", ".join(chat["inventory"]) or "nothing yet"
        return reply(f"Your inventory: {items}.")

    if text in ("help", "hint", "instructions"):
        return reply(
            "Examine the five objects to find clues. Answer a puzzle by "
            "typing the answer (for example a sequence of symbols or a "
            "four-digit code), or start with 'submit'."
        )

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
    if chat["mode"] == "offline":
        chat["history"].append(message)

        response = offline_response(chat, message)

        chat["history"].append(response)

        return response

    models_to_try = [
        PRIMARY_MODEL,
        FALLBACK_MODEL,
    ]

    delays = [3, 5]

    for model_index, model in enumerate(models_to_try):
        try:
            # Reuse the existing chat if already on this model.
            if chat["active_model"] != model:
                history = chat["client_chat"].get_history()

                print(f"Switching to {model}...")

                chat["client_chat"] = create_model_chat(
                    model,
                    chat["system_prompt"],
                    history,
                )

                chat["active_model"] = model

            start_time = time.perf_counter()

            response = chat["client_chat"].send_message(message)

            print(
                f"\nGemini model: {model}"
            )

            print(
                f"Response time: "
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

            response_text = (
                response.text or "The guardian remains silent..."
            )

            # Save the latest reported game state.
            new_state = parse_game_state(response_text)

            if new_state:
                chat["game_state"] = new_state

            return response_text

        except Exception as error:
            error_message = str(error)

            print(
                f"{model} failed: {error_message}"
            )

            # Retry a temporary service failure once.
            is_temporary = (
                "503" in error_message
                or "UNAVAILABLE" in error_message
                or "500" in error_message
                or "INTERNAL" in error_message
            )

            if is_temporary and model_index == 0:
                print("Retrying primary model...")
                time.sleep(delays[0])

                try:
                    response = chat["client_chat"].send_message(
                        message
                    )

                    response_text = (
                        response.text
                        or "The guardian remains silent..."
                    )

                    new_state = parse_game_state(response_text)

                    if new_state:
                        chat["game_state"] = new_state

                    return response_text

                except Exception as retry_error:
                    print(
                        "Primary retry failed:",
                        str(retry_error)
                    )

            # Continue to the next model.
            continue

    # Both Gemini models failed.
    print("Both Gemini models failed. Switching to offline mode.")

    switch_to_offline(chat)

    return (
        "⚠️ The magical connection has been interrupted. "
        "The dungeon's local system has taken control. "
        "Your available progress has been preserved.\n\n"
        + offline_response(chat, message)
    )
