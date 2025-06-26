import os
from datetime import datetime, timedelta
import re
import dateparser
from app.tools import check_slots, book_slot
from app.config import settings
from app.ai_agent import run_agent

sessions: dict[str, dict] = {}

"""
booking_agent.py (v2) – more natural name extraction & cleaner replies
---------------------------------------------------------------------
Key upgrade: `get_name()` now extracts the user’s name from natural phrases like
"my name is Deepak", "I am Deepak", "this is Deepak" rather than echoing the
whole sentence. Regular‑expression heuristics cover common patterns; otherwise
fallback to the last word.
"""

# ───────────────────────── Conversation Node Helpers ───────────────────────────
NAME_PATTERNS = [
    re.compile(r"my name is (.+)", re.I),
    re.compile(r"i am (.+)", re.I),
    re.compile(r"i'm (.+)", re.I),
    re.compile(r"this is (.+)", re.I),
]

def clean_name(raw: str) -> str:
    """Extract probable name from user input."""
    raw = raw.strip()
    for pat in NAME_PATTERNS:
        m = pat.match(raw)
        if m:
            candidate = m.group(1)
            break
    else:
        # fallback – take last word as name
        candidate = raw.split()[-1]
    # Title‑case the name ("deepak" → "Deepak")
    return candidate.strip().title()

# ───────────────────────── Conversation Node Callbacks ──────────────────────────

def ask_name(state):
    return "Hi! What is your name?", "get_name"


def get_name(state):
    msg = state.get("message", "").strip()
    if not msg:
        return "Sorry, I didn't catch your name. Could you repeat it?", "get_name"

    name = clean_name(msg)
    state["name"] = name
    return f"Nice to meet you, {name}! What date would you like to book? (Today, tomorrow, or a specific date)", "get_date"


def get_date(state):
    msg = state.get("message", "")
    parsed = dateparser.parse(msg)
    if not parsed:
        return "I couldn't understand that date. Could you rephrase (e.g., 'tomorrow' or '2025-06-27')?", "get_date"

    today = datetime.now().date()
    date_only = parsed.date()
    if not (today <= date_only <= today + timedelta(days=2)):
        return "You can only book within the next 2 days. Please pick today, tomorrow, or the day after.", "get_date"

    state["date"] = date_only.isoformat()
    slots = check_slots({"date": state["date"]}).get("slots", [])
    if not slots:
        return "No slots are available that day. Please choose another date.", "get_date"
    state["slots"] = slots
    return f"Available slots on {state['date']}: {', '.join(slots)}. Which slot do you prefer?", "get_slot"


def get_slot(state):
    msg = state.get("message", "").strip()
    if msg not in state.get("slots", []):
        return "That slot isn't available. Please choose one from the list I sent you.", "get_slot"
    state["slot"] = msg
    return f"Great – booking {state['slot']} on {state['date']}. Please confirm by replying 'yes'.", "confirm"


def confirm(state):
    if state.get("message", "").lower() not in ("yes", "y", "confirm"):
        return "Booking cancelled. If you'd like to start over, just say 'hi'.", "end"

    result = book_slot({
        "name": state["name"],
        "date": state["date"],
        "slot": state["slot"],
        "phone": state.get("phone")
    })
    if result.get("success"):
        return f"You're booked for {state['date']} at {state['slot']}! 🎉", "end"
    else:
        slots = check_slots({"date": state["date"]}).get("slots", [])
        state["slots"] = slots
        if not slots:
            return "Oops, that slot was just taken and no others are free that day. Try another date.", "get_date"
        return f"Oops, that slot was taken. Remaining slots: {', '.join(slots)}. Choose one.", "get_slot"


def end_node(state):
    return "You're all set!", "end"

NODES = {
    "ask_name": ask_name,
    "get_name": get_name,
    "get_date": get_date,
    "get_slot": get_slot,
    "confirm": confirm,
    "end": end_node,
}

# ──────────────────────────── Session Management ───────────────────────────────
'''
sessions = {}

async def run_booking_agent(user_number: str, message: str) -> str:
    if user_number not in sessions or sessions[user_number].get("step") == "end":
        sessions[user_number] = {
            "step": "ask_name",
            "name": None,
            "date": None,
            "slot": None,
            "phone": user_number,
        }

    state = sessions[user_number]
    state["message"] = message
    state["phone"] = user_number

    # Run current node once
    reply, next_step = NODES[state["step"]](state)
    state["step"] = next_step
    sessions[user_number] = state
    return reply
'''


async def run_booking_agent(user_num: str, message: str) -> str:
    # reset session if brand-new user or last booking finished
    if user_num not in sessions or sessions[user_num].get("booked"):
        sessions[user_num] = {}

    reply, new_state = await run_agent(sessions[user_num], message)
    sessions[user_num] = new_state
    return reply