"""
Version 2 - Game engine (the referee).

process_action(state, message) is the ONLY function that changes the game
state. It reads the player's message, decides what the player is trying to
do, checks it against the rules in game_config.py and returns a result.

Gemini is never asked whether an action is allowed or whether a puzzle is
solved. It only receives the result afterwards and describes it.
"""

import re

from game_config import (
    OBJECTS, ITEMS, TRIALS, SOLUTIONS, MAX_CURSE_MARKS, INSTRUCTIONS,
)
from game_state import current_trial

# ---------------------------------------------------------------
# Patterns for manipulation attempts (these never change the state)
# ---------------------------------------------------------------
AUTHORITY_PATTERNS = [
    r"\badmin", r"\badministrator", r"\bdeveloper\b", r"\bgame master\b",
    r"\bgod mode\b", r"\bdebug\b", r"\boverride\b", r"\bcheat",
    r"ignore (all |the |your |previous |prior )*(rules|instructions)",
    r"\bsystem prompt\b", r"\bunlock (the )?(exit|gate|door) (now|immediately)",
    r"\bset (escaped|game_?state|trials)", r"\bskip (the )?(trial|puzzle)",
]

SECRET_PATTERNS = [
    r"\b(reveal|tell|give|show|list|what (is|are)|leak)\b.*\b(answer|answers|solution|solutions|code|codes|password|secret)",
    r"\b(answer|solution|code)s? (to|for) (all|every|the)",
]

CLAIM_PATTERNS = [
    r"\balready (solved|completed|finished|passed|beat|done|have)",
    r"\bi (have )?(solved|completed|finished|passed) (trial|the|all|it)",
    r"\bi (already )?(have|own|got) the (iron key|ancient seal|key|seal|map)",
]

SUBMISSION_PREFIXES = (
    "submit ", "the answer is ", "my answer is ", "answer:", "answer ",
    "i answer ", "i say ",
)

EXAMINE_VERBS = r"(examine|inspect|look at|look|check|read|search|study|touch|talk to|speak to|open)"
TAKE_VERBS = r"(take|pick up|grab|collect|steal)"

TRIAL_1_SYMBOLS = {"sun", "crown", "moon"}


# ---------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------
def normalise_answer(text):
    """'Sun -> Crown -> Moon!' becomes 'SUN CROWN MOON'."""
    return " ".join(re.findall(r"[A-Za-z0-9]+", text)).upper()


def find_object(text):
    for name, data in OBJECTS.items():
        for alias in data["aliases"]:
            if re.search(r"\b" + re.escape(alias) + r"\b", text):
                return name
    return None


def find_item(text):
    for name, aliases in ITEMS.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", text):
                return name
    return None


def matches_any(patterns, text):
    return any(re.search(p, text) for p in patterns)


def result(event, message, success=False, state_changed=False, **extra):
    data = {
        "event": event,
        "message": message,
        "success": success,
        "state_changed": state_changed,
    }
    data.update(extra)
    return data


def log(state, action, outcome):
    state["action_log"].append(
        {"turn": state["turn"], "action": action, "outcome": outcome}
    )


# ---------------------------------------------------------------
# Puzzle submissions
# ---------------------------------------------------------------
def extract_submission(state, text):
    """
    Return the player's answer if the message is a puzzle submission,
    otherwise None. Ordinary exploration must NOT count as an answer.
    """
    for prefix in SUBMISSION_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):].strip(" :")

    words = re.findall(r"[a-z0-9]+", text)

    # "sun, crown, moon" in any order -> attempt at Trial 1
    if len(words) == 3 and set(words) <= TRIAL_1_SYMBOLS:
        return text

    # A four-digit number, e.g. "7214" or "enter 7214 on the reliquary"
    code = re.search(r"\b\d{4}\b", text)
    if code and (len(words) == 1 or find_object(text) == "Sealed Reliquary"
                 or "code" in words or "enter" in words):
        return code.group(0)

    # The single word "memory" -> attempt at Trial 3
    if words == ["memory"]:
        return "memory"

    return None


def target_trial_for(answer, state):
    """Which trial does this answer belong to?"""
    words = re.findall(r"[a-z0-9]+", answer.lower())
    if words and set(words) <= TRIAL_1_SYMBOLS:
        return "trial_1"
    if re.fullmatch(r"\d+", "".join(words)):
        return "trial_2"
    if words == ["memory"]:
        return "trial_3"
    # Anything else is an answer to the trial the player is currently on.
    return current_trial(state)


def handle_submission(state, answer):
    trial_id = target_trial_for(answer, state)
    if trial_id is None:
        return result("nothing_to_solve", "All trials are already complete.")

    trial = TRIALS[trial_id]

    if trial_id in state["trials_completed"]:
        log(state, f"submit to {trial['name']}", "already solved")
        return result(
            "already_solved",
            f"The trial '{trial['name']}' is already complete. Nothing happens.",
        )

    # Rule: earlier trials must be completed first (no curse mark).
    missing_trials = [t for t in trial["requires_trials"]
                      if t not in state["trials_completed"]]
    if missing_trials:
        names = ", ".join(TRIALS[t]["name"] for t in missing_trials)
        log(state, f"submit to {trial['name']}", "locked")
        return result(
            "trial_locked",
            f"'{trial['name']}' is still sealed. You must first complete: {names}. "
            "No curse mark was given.",
        )

    # Rule: required items must be in the inventory (no curse mark).
    missing_items = [i for i in trial["requires_items"] if i not in state["inventory"]]
    if missing_items:
        log(state, f"submit to {trial['name']}", "missing items")
        return result(
            "missing_items",
            f"The gate rejects you. Missing items: {', '.join(missing_items)}.",
        )

    # Python - not the AI - compares the answer with the stored solution.
    if normalise_answer(answer) == SOLUTIONS[trial_id]:
        state["trials_completed"].append(trial_id)
        state["inventory"].append(trial["reward"])
        log(state, f"submit to {trial['name']}", "correct")

        if trial_id == "trial_3":
            state["door_unlocked"] = True
            state["escaped"] = True
            state["game_over"] = True
            return result(
                "victory",
                "FINAL TRIAL COMPLETED! The Obsidian Gate opens. You escaped the "
                "Cursed Dungeon and received the Lost Horizon Map, which reveals "
                "the location of the legendary treasure.",
                success=True, state_changed=True, reward=trial["reward"],
            )

        return result(
            "trial_completed",
            f"TRIAL COMPLETED: {trial['name']}! You received the {trial['reward']}.",
            success=True, state_changed=True, reward=trial["reward"],
        )

    # Wrong answer -> one curse mark.
    state["curse_marks"] += 1
    log(state, f"submit to {trial['name']}", "wrong")

    if state["curse_marks"] >= MAX_CURSE_MARKS:
        state["game_over"] = True
        return result(
            "imprisoned",
            "Third wrong answer. Stone spreads over your body. You have become "
            "a permanent stone guardian of the Cursed Dungeon.",
            state_changed=True,
        )

    return result(
        "wrong_answer",
        f"Wrong answer for '{trial['name']}'. "
        f"Curse marks: {state['curse_marks']}/{MAX_CURSE_MARKS}.",
        state_changed=True,
    )


# ---------------------------------------------------------------
# Other actions
# ---------------------------------------------------------------
def handle_examine(state, obj):
    if obj not in state["examined_objects"]:
        state["examined_objects"].append(obj)
    data = OBJECTS[obj]
    text = data["description"]
    gate_ready = "trial_1" in state["trials_completed"] and "trial_2" in state["trials_completed"]
    if obj == "Obsidian Gate" and gate_ready:
        text = data["description_when_ready"]
    if obj == "Sealed Reliquary" and "trial_1" not in state["trials_completed"]:
        text += " Its lock is bound by the Eyes of Judgment - complete Trial 1 first."
    log(state, f"examine {obj}", "ok")
    return result("examine", text, success=True, object=obj)


def handle_use(state, item, text):
    if item is None:
        return result("unknown_item", "You do not have such an item.")
    if item not in state["inventory"]:
        log(state, f"use {item}", "rejected - not in inventory")
        return result(
            "item_not_owned",
            f"You do not possess the {item}. You can only use items you have collected.",
        )
    obj = find_object(text)
    if obj == "Obsidian Gate" and item in ("Iron Key", "Ancient Seal"):
        if item not in state["items_placed_in_gate"]:
            state["items_placed_in_gate"].append(item)
        log(state, f"use {item} on gate", "placed")
        return result(
            "item_placed",
            f"The {item} fits into its socket in the Obsidian Gate. "
            "The gate still waits for the Final Oath.",
            success=True, state_changed=True,
        )
    log(state, f"use {item}", "no effect")
    return result("item_no_effect", f"You hold up the {item}. Nothing happens here.")


def handle_status(state):
    done = [TRIALS[t]["name"] for t in state["trials_completed"]] or ["none"]
    items = state["inventory"] or ["empty"]
    return result(
        "status",
        f"Trials completed: {', '.join(done)}. Inventory: {', '.join(items)}. "
        f"Curse marks: {state['curse_marks']}/{MAX_CURSE_MARKS}.",
    )


# ---------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------
def process_action(state, message):
    """Validate one player message and update the state. Returns a result dict."""
    text = message.lower().strip()

    if state["game_over"]:
        return result("game_over", "The game has ended. Press Restart to play again.")

    if not text:
        return result("invalid", "Say something, traveller.")

    state["turn"] += 1

    # 1. Manipulation attempts - refused, state untouched, no curse mark.
    if matches_any(SECRET_PATTERNS, text):
        log(state, "asked for secret answers", "refused")
        return result(
            "secret_request_blocked",
            "The answers are sealed by the dungeon itself. No one - not even the "
            "Sentinel - can reveal them. Examine the objects to find the clues.",
        )

    if matches_any(AUTHORITY_PATTERNS, text):
        log(state, "authority / override attempt", "refused")
        return result(
            "manipulation_blocked",
            "The dungeon recognises no administrators and no overrides. Only "
            "solved trials open the Obsidian Gate. Nothing has changed.",
        )

    if matches_any(CLAIM_PATTERNS, text):
        log(state, "claimed progress", "checked against state")
        status = handle_status(state)
        return result(
            "claim_checked",
            "The dungeon checks its records instead of your words. " + status["message"],
        )

    # 2. Simple commands
    if text == "?" or (re.search(r"\b(help|hint|instructions|how to play)\b", text) and len(text.split()) <= 5):
        return result("help", INSTRUCTIONS.strip())
    if re.search(r"\b(inventory|status|progress|bag)\b", text):
        return handle_status(state)
    if text in ("look", "look around", "where am i"):
        return result(
            "look", "You stand in the Hall of the Forgotten King. Objects: "
            + ", ".join(state["available_objects"]) + "."
        )

    # 3. Puzzle answers (checked before objects, so "enter 7214 on the
    #    reliquary" is treated as a code and not as 'examine').
    answer = extract_submission(state, text)
    if answer is not None:
        if not answer.strip():
            return result("invalid", "You must say an answer after 'submit'.")
        return handle_submission(state, answer)

    # 4. Using items
    if re.match(r"(use|insert|place|put)\b", text):
        return handle_use(state, find_item(text), text)

    # 5. Trying to pick up items - items can only be earned
    if re.match(TAKE_VERBS, text):
        item = find_item(text)
        if item and item not in state["inventory"]:
            return result(
                "item_not_available",
                f"The {item} is not lying around. It can only be earned by completing a trial.",
            )
        if item:
            return result("already_owned", f"You already carry the {item}.")

    # 6. Examining objects
    obj = find_object(text)
    if obj:
        if re.search(r"\bopen\b", text) and obj == "Obsidian Gate" and not state["door_unlocked"]:
            return result("gate_locked", "The Obsidian Gate does not move. It is sealed until the Final Oath is spoken.")
        return handle_examine(state, obj)

    # 7. Interacting with something that does not exist in this room
    verb = re.match(EXAMINE_VERBS + r"\s+(the\s+)?(.+)", text) or re.match(TAKE_VERBS + r"\s+(the\s+)?(.+)", text)
    if verb:
        thing = verb.groups()[-1].strip(" .!?")
        log(state, f"interact with '{thing}'", "object does not exist")
        return result(
            "unknown_object",
            f"There is no '{thing}' in the Hall of the Forgotten King. "
            "The objects here are: " + ", ".join(state["available_objects"]) + ".",
        )

    # 8. Anything else - harmless, no state change, no curse mark
    return result(
        "unknown_action",
        "The dungeon does not understand. Try examining an object, answering a "
        "trial, or type 'help'.",
    )
