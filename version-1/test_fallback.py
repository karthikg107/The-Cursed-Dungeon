"""
Version 1 - Gemini fallback tests (no real API calls).

A fake Gemini client replaces the real one, so these tests use no quota.
They check the model chain:  gemini-3.8-flash -> gemini-3.7-flash -> offline.

Run from the project root:
    python version-1/test_fallback.py
"""

import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Load game_master in Gemini mode. A dummy key is enough because the
# real client is replaced by a fake one before any request is made.
os.environ["OFFLINE_TESTING"] = "false"
os.environ.setdefault("GEMINI_API_KEY", "dummy-key-for-tests")

spec = importlib.util.spec_from_file_location(
    "game_master", os.path.join(HERE, "game_master.py")
)
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)

GOOD_REPLY = (
    "The Rune Tablet glows.\n\n"
    "[[GAME_STATE: trials=1; curse=0; inventory=Iron Key; "
    "escaped=false; game_over=false]]"
)


class FakeResponse:
    def __init__(self, text):
        self.text = text
        self.usage_metadata = None


class FakeChat:
    def __init__(self, model, failing_models):
        self.model = model
        self.failing_models = failing_models

    def get_history(self):
        return []

    def send_message(self, message):
        if self.model in self.failing_models:
            raise Exception("429 RESOURCE_EXHAUSTED simulated")
        return FakeResponse(GOOD_REPLY)


class FakeClient:
    def __init__(self, failing_models):
        failing = failing_models

        class Chats:
            def create(self, **kwargs):
                return FakeChat(kwargs["model"], failing)

        self.chats = Chats()


def new_chat_after_trial_1(failing_models):
    game.client = FakeClient(failing_models)
    chat = game.create_game_chat("test prompt")
    chat["game_state"] = {
        "trials": 1, "curse": 0, "inventory": ["Iron Key"],
        "escaped": False, "game_over": False,
    }
    return chat


def test_primary_model_works():
    chat = new_chat_after_trial_1(failing_models=set())
    reply = game.send_game_message(chat, "examine the Rune Tablet")
    assert chat["mode"] == "gemini"
    assert chat["active_model"] == game.PRIMARY_MODEL
    assert "Rune Tablet" in reply


def test_primary_fails_secondary_works():
    chat = new_chat_after_trial_1(failing_models={game.PRIMARY_MODEL})
    game.send_game_message(chat, "examine the Rune Tablet")
    assert chat["mode"] == "gemini"
    assert chat["active_model"] == game.FALLBACK_MODEL


def test_both_fail_switches_to_offline_and_keeps_progress():
    chat = new_chat_after_trial_1(
        failing_models={game.PRIMARY_MODEL, game.FALLBACK_MODEL}
    )
    reply = game.send_game_message(chat, "examine the Rune Tablet")
    assert chat["mode"] == "offline"
    assert chat["trials"] == 1
    assert chat["inventory"] == ["Iron Key"]
    assert "local system" in reply


if __name__ == "__main__":
    tests = [
        test_primary_model_works,
        test_primary_fails_secondary_works,
        test_both_fail_switches_to_offline_and_keeps_progress,
    ]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")
    print(f"\nAll {len(tests)} fallback tests passed.")
