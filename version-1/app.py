
import re
import streamlit as st

from game_master import create_game_chat, send_game_message
from prompts import SYSTEM_PROMPT
from game_config import (
    GAME_TITLE,
    INTRODUCTION,
    ROOM_OBJECTS,
    TOTAL_TRIALS,
    MAX_CURSE_MARKS,
)

st.set_page_config(
    page_title=GAME_TITLE,
    page_icon="🏰",
    layout="wide",
)

# --------------------------------
# INITIALIZE GAME SESSION
# --------------------------------

def initialize_game():
    defaults = {
        "messages": [],
        "game_started": False,
        "game_over": False,
        "escaped": False,
        "inventory": [],
        "curse_marks": 0,
        "trials_completed": 0,
        "chat": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_game()


# --------------------------------
# READ AI GAME STATUS
# --------------------------------

def update_game_status(response):
    pattern = (
        r"\[\[GAME_STATE:\s*"
        r"trials=(\d+);\s*"
        r"curse=(\d+);\s*"
        r"inventory=(.*?);\s*"
        r"escaped=(true|false);\s*"
        r"game_over=(true|false)"
        r"\s*\]\]"
    )

    match = re.search(pattern, response, re.IGNORECASE)

    if match:
        st.session_state.trials_completed = min(
            int(match.group(1)), TOTAL_TRIALS
        )

        st.session_state.curse_marks = min(
            int(match.group(2)), MAX_CURSE_MARKS
        )

        inventory_text = match.group(3).strip()

        if inventory_text.lower() == "none":
            st.session_state.inventory = []
        else:
            st.session_state.inventory = [
                item.strip()
                for item in inventory_text.split(",")
                if item.strip()
            ]

        st.session_state.escaped = (
            match.group(4).lower() == "true"
        )

        st.session_state.game_over = (
            match.group(5).lower() == "true"
        )

        # Remove technical status information from the chat.
        response = re.sub(
            pattern,
            "",
            response,
            flags=re.IGNORECASE,
        ).strip()

    return response


# --------------------------------
# START OR RESTART GAME
# --------------------------------

def start_game():
    st.session_state.messages = []
    st.session_state.inventory = []
    st.session_state.curse_marks = 0
    st.session_state.trials_completed = 0
    st.session_state.game_over = False
    st.session_state.escaped = False
    st.session_state.game_started = True

    st.session_state.chat = create_game_chat(SYSTEM_PROMPT)

    opening_message = send_game_message(
        st.session_state.chat,
        "Begin the game. Introduce the dungeon, "
        "the five objects and the three-trial challenge. "
        "Use this story introduction:\n" + INTRODUCTION
    )

    opening_message = update_game_status(opening_message)

    st.session_state.messages.append({
        "role": "assistant",
        "content": opening_message,
    })


# --------------------------------
# SEND PLAYER MESSAGE
# --------------------------------

def send_player_message(user_message):
    st.session_state.messages.append({
        "role": "user",
        "content": user_message,
    })

    response = send_game_message(
        st.session_state.chat,
        user_message,
    )

    response = update_game_status(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
    })


# --------------------------------
# MAIN INTERFACE
# --------------------------------

st.title("🏰 THE CURSED DUNGEON")

st.caption(
    "An AI-Powered Escape Room | Version 1"
)

st.divider()


# --------------------------------
# SIDEBAR
# --------------------------------

with st.sidebar:

    st.header("⚔️ Dungeon Status")

    st.metric(
        "Completed Trials",
        f"{st.session_state.trials_completed}/{TOTAL_TRIALS}",
    )

    st.metric(
        "Curse Marks",
        f"{st.session_state.curse_marks}/{MAX_CURSE_MARKS}",
    )

    st.progress(
        st.session_state.trials_completed / TOTAL_TRIALS
    )

    st.divider()

    st.subheader("🎒 Inventory")

    if st.session_state.inventory:
        for item in st.session_state.inventory:
            st.write(f"🔑 {item}")
    else:
        st.write("Your inventory is empty.")

    st.divider()

    st.subheader("🔍 Room Objects")

    for obj in ROOM_OBJECTS:
        st.write(f"• {obj}")

    st.divider()

    if st.session_state.escaped:
        st.success("🏆 Dungeon escaped!")

    elif st.session_state.game_over:
        st.error("💀 Dungeon journey ended.")

    if st.button(
        "🔄 Restart Dungeon",
        use_container_width=True,
    ):
        with st.spinner("Restarting the dungeon..."):
            start_game()
        st.rerun()


# --------------------------------
# GAME START SCREEN
# --------------------------------

if not st.session_state.game_started:

    st.subheader("Your journey begins...")

    st.write(
        "You awaken in an ancient underground chamber. "
        "A mysterious guardian watches you. "
        "Three trials stand between you and freedom."
    )

    st.warning(
        "Three incorrect puzzle answers will turn "
        "you into a permanent stone guardian."
    )

    if st.button(
        "⚔️ ENTER THE DUNGEON",
        use_container_width=True,
    ):

        with st.spinner("Awakening the dungeon guardian..."):
            start_game()

        st.rerun()


# --------------------------------
# ACTIVE GAME SCREEN
# --------------------------------

else:

    st.subheader("💀 The Dungeon Guardian")

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if st.session_state.escaped:

        st.success(
            "🏆 Congratulations! You have escaped the Cursed Dungeon!"
        )

    elif st.session_state.game_over:

        st.error(
            "Your journey has ended. Restart the dungeon to try again."
        )

    else:

        user_input = st.chat_input(
            "Talk to the guardian, examine an object, or solve a puzzle..."
        )

        if user_input:

            with st.spinner("The guardian is thinking..."):

                send_player_message(user_input)

            st.rerun()
