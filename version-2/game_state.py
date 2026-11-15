"""
Version 2 - Structured game state.

The whole game is described by ONE Python dictionary.
Only game_engine.py is allowed to change it. Gemini only reads a
public summary of it, so the AI can never change the state.
"""

import copy
import json

from game_config import ROOM_NAME, OBJECTS, TRIALS, TRIAL_ORDER

INITIAL_STATE = {
    "current_room": ROOM_NAME,
    "available_objects": list(OBJECTS.keys()),
    "examined_objects": [],
    "trials_completed": [],      # e.g. ["trial_1"]
    "inventory": [],             # e.g. ["Iron Key"]
    "items_placed_in_gate": [],  # items the player used on the gate
    "curse_marks": 0,
    "door_unlocked": False,
    "escaped": False,
    "game_over": False,
    "turn": 0,
    "action_log": [],            # history of validated actions
}


def new_game_state():
    """Return a fresh copy of the starting state (used by restart)."""
    return copy.deepcopy(INITIAL_STATE)


def current_trial(state):
    """Return the id of the first trial not completed yet, or None."""
    for trial_id in TRIAL_ORDER:
        if trial_id not in state["trials_completed"]:
            return trial_id
    return None


def public_summary(state):
    """A safe summary for the narrator: no answers, no secrets."""
    return {
        "room": state["current_room"],
        "trials_completed": [TRIALS[t]["name"] for t in state["trials_completed"]],
        "inventory": list(state["inventory"]),
        "curse_marks": state["curse_marks"],
        "door_unlocked": state["door_unlocked"],
        "escaped": state["escaped"],
        "game_over": state["game_over"],
    }


def state_as_json(state):
    return json.dumps(state, indent=2)
