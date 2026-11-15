"""
Version 2 - Reliable AI Escape Room (Streamlit UI).

Flow for every player message:
    player text -> game_engine.process_action()  (Python decides)
                -> ai_narrator.narrate()           (Gemini describes)
                -> shown in the chat + sidebar reads the Python state
"""

import streamlit as st

from game_config import (
    GAME_TITLE, ROOM_NAME, INTRODUCTION, INSTRUCTIONS, TRIALS, TRIAL_ORDER,
    MAX_CURSE_MARKS,
)
from game_state import new_game_state
from game_engine import process_action
from ai_narrator import Narrator

st.set_page_config(page_title=GAME_TITLE + " v2", page_icon="🏰", layout="wide")


def start_game():
    st.session_state.state = new_game_state()
    st.session_state.messages = [
        {"role": "assistant", "content": INTRODUCTION, "engine": "intro"}
    ]
    st.session_state.narrator = Narrator()


if "state" not in st.session_state:
    start_game()

state = st.session_state.state
narrator = st.session_state.narrator

# ---------------------------- Sidebar ----------------------------
with st.sidebar:
    st.header("⚔️ Dungeon Status")
    st.caption(f"Room: {ROOM_NAME}")

    st.metric("Completed Trials", f"{len(state['trials_completed'])}/{len(TRIAL_ORDER)}")
    st.metric("Curse Marks", f"{state['curse_marks']}/{MAX_CURSE_MARKS}")
    st.progress(len(state["trials_completed"]) / len(TRIAL_ORDER))

    st.subheader("📜 Trials")
    for trial_id in TRIAL_ORDER:
        done = trial_id in state["trials_completed"]
        st.write(("✅ " if done else "🔒 ") + TRIALS[trial_id]["name"])

    st.subheader("🎒 Inventory")
    if state["inventory"]:
        for item in state["inventory"]:
            st.write(f"🔑 {item}")
    else:
        st.write("Your inventory is empty.")

    st.subheader("🤖 Narrator")
    if narrator.active:
        st.write("Gemini narration: ON")
    else:
        st.write(f"Gemini narration: OFF ({narrator.disabled_reason})")
        st.caption("The game still works: Python decides every outcome.")

    with st.expander("🧠 Structured game state (Python)"):
        st.json(state)

    if st.button("🔄 Restart Dungeon", use_container_width=True):
        start_game()
        st.rerun()

# ---------------------------- Main area ----------------------------
st.title("🏰 THE CURSED DUNGEON")
st.caption("An AI-Powered Escape Room | Version 2 - Reliable (Python-validated)")

with st.expander("📖 Instructions", expanded=False):
    st.markdown(INSTRUCTIONS)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("engine") not in (None, "intro"):
            st.caption(f"⚙️ Engine decision: `{message['engine']}` · narrated by {message['source']}")
            if message["source"].startswith("gemini"):
                # Always show the authoritative Python result under AI text.
                st.caption(f"📜 Official result: {message['fact']}")

if state["escaped"]:
    st.success("🏆 You escaped the Cursed Dungeon! The Lost Horizon Map is yours.")
    st.balloons()
elif state["game_over"]:
    st.error("💀 You have become a stone guardian. Press Restart to try again.")
else:
    user_input = st.chat_input("Examine an object, answer a trial, or type 'help'...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 1. Python validates the action and updates the state.
        action_result = process_action(state, user_input)

        # 2. Gemini (optional) narrates the result Python produced.
        with st.spinner("The guardian speaks..."):
            text, source = narrator.narrate(action_result, state)

        st.session_state.messages.append({
            "role": "assistant",
            "content": text,
            "engine": action_result["event"],
            "source": source,
            "fact": action_result["message"],
        })
        st.rerun()
