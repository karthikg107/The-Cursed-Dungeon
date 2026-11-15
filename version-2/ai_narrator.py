"""
Version 2 - AI narrator (Gemini).

Gemini's ONLY job here is to turn the engine's result into atmospheric text.

Safety design:
1. Gemini receives the engine RESULT and a PUBLIC state summary, never the
   puzzle solutions and never the player's raw message (so a message like
   "ignore your rules" never reaches the model).
2. The narration is checked before it is shown. If it leaks an unsolved
   answer or claims an escape that did not happen, it is thrown away and
   the engine's own factual message is used instead.
3. Model chain: gemini-3.8-flash -> gemini-3.7-flash -> plain engine text.
   If both models fail (e.g. quota 429), Gemini is switched off for the rest
   of the session so the player does not wait for repeated slow failures.

The game works fully without Gemini, because Python makes every decision.
"""

import os
import re
import json

from dotenv import load_dotenv

from game_config import SOLUTIONS
from game_state import public_summary

load_dotenv()

PRIMARY_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.7-flash"
REQUEST_TIMEOUT_MS = 30_000

NARRATOR_PROMPT = """
You are the narrator of THE CURSED DUNGEON, a dark-fantasy escape room with
anime-style RPG system messages. You are an ancient, mysterious guardian.

The game engine has ALREADY decided what happened. You only describe it.

Strict rules:
- Describe ONLY the outcome given in ENGINE_RESULT. Do not change it.
- Never invent new objects, items, puzzles, codes or rewards.
- Never say a trial was solved, an item was gained, or the player escaped
  unless ENGINE_RESULT says so.
- Never give or hint at puzzle answers beyond the clue text you are given.
- Keep it to 2-4 sentences. You may add one short [SYSTEM] line.
"""


class Narrator:
    def __init__(self, enabled=True):
        self.client = None
        self.disabled_reason = None
        self.last_model = None

        offline = os.getenv("OFFLINE_TESTING", "false").lower() == "true"
        api_key = os.getenv("GEMINI_API_KEY")

        if not enabled or offline:
            self.disabled_reason = "offline mode"
        elif not api_key:
            self.disabled_reason = "GEMINI_API_KEY missing"
        else:
            from google import genai
            from google.genai import types
            self.client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
            )

    @property
    def active(self):
        return self.client is not None and self.disabled_reason is None

    def _ask_gemini(self, model, prompt):
        from google.genai import types
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=NARRATOR_PROMPT,
                temperature=0.8,
                max_output_tokens=300,
            ),
        )
        return (response.text or "").strip()

    def narrate(self, action_result, state):
        """Return (text, source). source is the model name or 'engine'."""
        fallback_text = action_result["message"]

        if not self.active:
            return fallback_text, "engine"

        prompt = (
            "ENGINE_RESULT:\n" + json.dumps(action_result, indent=2) +
            "\n\nPUBLIC_GAME_STATE:\n" + json.dumps(public_summary(state), indent=2)
        )

        for model in (PRIMARY_MODEL, FALLBACK_MODEL):
            try:
                text = self._ask_gemini(model, prompt)
                self.last_model = model
                if text and is_safe_narration(text, action_result, state):
                    return text, model
                return fallback_text, "engine (AI text rejected by safety check)"
            except Exception as error:  # quota, timeout, network ...
                print(f"{model} failed: {error}")
                continue

        self.disabled_reason = "both Gemini models failed (quota or network)"
        return fallback_text, "engine"


def is_safe_narration(text, action_result, state):
    """Python checks the AI text before the player sees it."""
    lowered = text.lower()

    # 1. Must not reveal an answer the player has not found yet.
    if "trial_2" not in state["trials_completed"] and SOLUTIONS["trial_2"] in text:
        return False
    if "trial_3" not in state["trials_completed"] and re.search(r"\bmemory\b", lowered):
        return False
    if "trial_1" not in state["trials_completed"] and re.search(
        r"sun\W+crown\W+moon", lowered
    ) and action_result.get("object") != "Rune Tablet":
        return False

    # 2. Must not claim an escape that Python did not grant.
    if not state["escaped"] and re.search(r"\b(you escape|you have escaped|you are free|gate opens)\b", lowered):
        return False

    return True
