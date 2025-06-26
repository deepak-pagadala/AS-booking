import json
import openai
from app.tools import check_slots as _old_check_slots
from app.tools import book_slot as _old_book_slot
from app.config import settings

openai.api_key = settings.OPENAI_API_KEY

# ────────────────────── thin wrappers so signatures match ──────────────────────
def check_slots(date: str):
    """Return {'slots': [...]}"""
    return _old_check_slots({"date": date})

def book_slot(name: str, date: str, slot: str, phone: str):
    return _old_book_slot({"name": name, "date": date, "slot": slot, "phone": phone})

def set_customer_info(name: str | None = None, phone: str | None = None):
    """Just echoes what was passed so we can merge into state."""
    return {"name": name, "phone": phone}

# ────────────────────────── OpenAI function schema ─────────────────────────────
FUNCTIONS = [
    {
        "name": "check_slots",
        "description": "Return free time slots for a given ISO date (YYYY-MM-DD).",
        "parameters": {
            "type": "object",
            "properties": {"date": {"type": "string"}},
            "required": ["date"],
        },
    },
    {
        "name": "set_customer_info",
        "description": "Store customer's name and/or phone number in memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "name":  {"type": "string"},
                "phone": {"type": "string"},
            },
        },
    },
    {
        "name": "book_slot",
        "description": "Reserve an available slot once all details are known.",
        "parameters": {
            "type": "object",
            "properties": {
                "name":  {"type": "string"},
                "date":  {"type": "string"},
                "slot":  {"type": "string"},
                "phone": {"type": "string"},
            },
            "required": ["name", "date", "slot", "phone"],
        },
    },
]

# ───────────────────────────── main agent loop ─────────────────────────────────
async def run_agent(state: dict, user_msg: str) -> tuple[str, dict]:
    """
    Exchange one turn with GPT and return (assistant_reply, new_state).
    `state` is a mutable dict we persist per user.
    """
    state.setdefault("phone", "")
    msgs = [
        {
            "role": "system",
            "content": (
                "You are an SMS booking assistant named Sita. You work at All Stars Cricket facility. Be helpful."
                "Collect name, phone, date (within 2 days) and slot. "
                "When mentioning the slots, always display available slots for the requested day."
                "Use the provided functions. "
                "Keep replies under 160 characters."
            ),
        },
        {"role": "assistant", "content": f"Current state: {json.dumps(state)}"},
        {"role": "user", "content": user_msg},
    ]

    tool_args: dict = {}  # prevent NameError later
    while True:
        resp = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=msgs,
            functions=FUNCTIONS,
            function_call="auto",
        )
        choice = resp.choices[0]

        # ── GPT chose to call a function ─────────────────────────────────────────
        if choice.finish_reason == "function_call":
            fn_name = choice.message.function_call.name
            tool_args = json.loads(choice.message.function_call.arguments or "{}")

            if fn_name == "check_slots":
                tool_resp = check_slots(**tool_args)
            elif fn_name == "book_slot":
                tool_resp = book_slot(**tool_args)
                if tool_resp.get("success"):
                    state["booked"] = True
            elif fn_name == "set_customer_info":
                tool_resp = set_customer_info(**tool_args)
                # merge directly into state
                for k, v in tool_resp.items():
                    if v:
                        state[k] = v
            else:
                tool_resp = {"error": "unknown tool"}

            msgs.append(
                {
                    "role": "function",
                    "name": fn_name,
                    "content": json.dumps(tool_resp),
                }
            )
            continue  # loop so GPT can respond to the tool output

        # ── GPT produced a normal assistant reply ───────────────────────────────
        assistant_reply = choice.message.content

        # update state from last tool_args (if any fields present)
        for key in ("name", "phone", "date", "slot"):
            if key in tool_args and tool_args[key]:
                state[key] = tool_args[key]

        return assistant_reply, state
