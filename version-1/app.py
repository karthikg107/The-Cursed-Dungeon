
import streamlit as st

from game_master import create_game_chat, send_game_message
from prompts import SYSTEM_PROMPT
from game_config import (
    GAME_TITLE,
    INTRODUCTION,
    ROOM_OBJECTS,
    TOTAL_TRIALS,
    MAX_CURSE_MARKS
)

st.set_page_config(
    page_title=GAME_TITLE,
    page_icon="🏰",
    layout="wide"
)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if "game_over" not in st.session_state:
    st.session_state.game_over = False

if "inventory" not in st.session_state:
    st.session_state.inventory = []

if "curse_marks" not in st.session_state:
    st.session_state.curse_marks = 0

if "chat" not in st.session_state:
    st.session_state.chat = None


# Start or restart game
def start_game():

    st.session_state.messages = []
    st.session_state.inventory = []
    st.session_state.curse_marks = 0
    st.session_state.game_over = False
    st.session_state.game_started = True

    st.session_state.chat = create_game_chat(SYSTEM_PROMPT)

    opening_message = send_game_message(
        st.session_state.chat,
        "Begin the game. Introduce the dungeon, "
        "the five objects and the three-trial challenge. "
        "Use this story introduction:\n" + INTRODUCTION
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": opening_message
    })


# Send player message
def send_message(user_message):

    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })

    response = send_game_message(
        st.session_state.chat,
        user_message
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })


# Main title
st.title("🏰 THE CURSED DUNGEON")
st.caption("An AI-Powered Escape Room | Version 1")

st.divider()


# Sidebar
with st.sidebar:

    st.header("⚔️ Dungeon Status")

    st.metric(
        "Curse Marks",
        f"{st.session_state.curse_marks}/{MAX_CURSE_MARKS}"
    )

    st.metric(
        "Trials",
        f"0/{TOTAL_TRIALS}"
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

    if st.button("🔄 Restart Dungeon", use_container_width=True):
        start_game()
        st.rerun()


# Welcome screen
if not st.session_state.game_started:

    st.subheader("Your journey begins...")

    st.write(
        "You awaken in an ancient underground chamber. "
        "A mysterious guardian watches you. "
        "Three trials stand between you and freedom."
    )

    st.warning(
        "Three incorrect puzzle answers will turn you "
        "into a permanent stone guardian."
    )

    if st.button("⚔️ ENTER THE DUNGEON", use_container_width=True):
        with st.spinner("Awakening the dungeon guardian..."):
            start_game()
        st.rerun()


# Game interface
else:

    st.subheader("💀 The Dungeon Guardian")

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not st.session_state.game_over:

        user_input = st.chat_input(
            "Talk to the guardian, examine an object, or solve a puzzle..."
        )

        if user_input:

            with st.spinner("The guardian is thinking..."):

                send_message(user_input)

            st.rerun()

    else:
        st.error("Your journey has ended. Restart to play again.")
