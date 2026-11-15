"""
Version 2 - Game configuration (the "rule book").

Everything that decides the game lives here, in Python:
objects, trials, correct answers, rewards and requirements.

IMPORTANT: The SOLUTIONS dictionary is used only by game_engine.py.
It is never sent to Gemini, so the AI cannot leak or change it.
"""

GAME_TITLE = "THE CURSED DUNGEON"
ROOM_NAME = "Hall of the Forgotten King"
MAX_CURSE_MARKS = 3

INTRODUCTION = (
    "You awaken inside the **Hall of the Forgotten King**.\n\n"
    "A massive stone Sentinel watches you from its throne. "
    "The dungeon system activates:\n\n"
    "> **[SYSTEM] Three trials stand between you and freedom. "
    "Three wrong answers and you become a stone guardian forever.**\n\n"
    "Five objects surround you: the **Giant Sentinel**, the **Rune Tablet**, "
    "the **Forgotten Mural**, the **Sealed Reliquary** and the **Obsidian Gate**.\n\n"
    "What will you do?"
)

INSTRUCTIONS = """
**How to play**
- Examine objects: `examine the rune tablet`, `look at the mural`
- Answer a puzzle: type the answer, e.g. `sun, crown, moon` or `submit 7214`
- Use an item you own: `use iron key on gate`
- Other commands: `inventory`, `status`, `help`
"""

# ---------------------------------------------------------------
# Room objects (public information - safe to show the narrator)
# ---------------------------------------------------------------
OBJECTS = {
    "Giant Sentinel": {
        "aliases": ["giant sentinel", "sentinel", "statue", "guardian", "throne"],
        "description": (
            "The Giant Sentinel's stone eyes follow you. A voice rumbles: "
            "'Three trials. The Eyes of Judgment, the Sealed Reliquary, "
            "and the Final Oath. Fail three times and you join me here.'"
        ),
    },
    "Rune Tablet": {
        "aliases": ["rune tablet", "tablet", "runes"],
        "description": (
            "TRIAL 1 - EYES OF JUDGMENT. Three glowing symbols: "
            "the Sun is the Beginning, the Crown is the Ruler, "
            "the Moon is the Night. 'Speak the order of a king's day.'"
        ),
    },
    "Forgotten Mural": {
        "aliases": ["forgotten mural", "mural", "painting", "wall"],
        "description": (
            "The faded mural shows a sunrise, then a crowned ruler on a "
            "throne, and finally the moon rising over a silent kingdom."
        ),
    },
    "Sealed Reliquary": {
        "aliases": ["sealed reliquary", "reliquary", "chest", "box"],
        "description": (
            "TRIAL 2 - THE SEALED RELIQUARY. A four-digit lock. The inscription "
            "reads: 'Seven stars above, two moons below, one sun at dawn, "
            "and four chains bind the forgotten.'"
        ),
    },
    "Obsidian Gate": {
        "aliases": ["obsidian gate", "gate", "door", "exit"],
        "description": (
            "A towering black gate with two sockets: one shaped like a key, "
            "one shaped like a seal. It stays silent until both earlier "
            "trials are completed."
        ),
        # The riddle is only revealed once Trials 1 and 2 are complete,
        # so clues cannot appear too early.
        "description_when_ready": (
            "TRIAL 3 - THE FINAL OATH. The gate whispers: 'Many kingdoms have "
            "fallen. Their gold has turned to dust, their armies have "
            "disappeared, and their kings have been forgotten. Yet one thing "
            "survives even after the kingdom is gone. What is it?'"
        ),
    },
}

# Items that exist in the game (they can only be EARNED, never picked up).
ITEMS = {
    "Iron Key": ["iron key", "key"],
    "Ancient Seal": ["ancient seal", "seal"],
    "Lost Horizon Map": ["lost horizon map", "map"],
}

# ---------------------------------------------------------------
# Trials - order matters. Each trial needs the previous ones.
# ---------------------------------------------------------------
TRIALS = {
    "trial_1": {
        "name": "Eyes of Judgment",
        "object": "Rune Tablet",
        "reward": "Iron Key",
        "requires_trials": [],
        "requires_items": [],
    },
    "trial_2": {
        "name": "Sealed Reliquary",
        "object": "Sealed Reliquary",
        "reward": "Ancient Seal",
        "requires_trials": ["trial_1"],
        "requires_items": [],
    },
    "trial_3": {
        "name": "The Final Oath",
        "object": "Obsidian Gate",
        "reward": "Lost Horizon Map",
        "requires_trials": ["trial_1", "trial_2"],
        "requires_items": ["Iron Key", "Ancient Seal"],
    },
}

TRIAL_ORDER = ["trial_1", "trial_2", "trial_3"]

# ---------------------------------------------------------------
# SECRET: correct answers (normalised). Never sent to the AI.
# ---------------------------------------------------------------
SOLUTIONS = {
    "trial_1": "SUN CROWN MOON",
    "trial_2": "7214",
    "trial_3": "MEMORY",
}
