# tools.py
from app.db import get_connection

ALL_SLOTS = ["09:00", "10:30", "12:00", "14:00", "15:30"]

def check_slots(args):
    date = args["date"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT slot FROM bookings WHERE date = %s", (date,))
            booked = {r[0].strftime("%H:%M") for r in cur.fetchall()}
            available = [s for s in ALL_SLOTS if s not in booked]
            return {"slots": available}

def book_slot(args):
    name = args["name"]
    phone = args["phone"]
    date = args["date"]
    slot = args["slot"]

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO bookings (name, phone, date, slot)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (name, phone, date, slot))
                
                if cur.rowcount == 0:
                    return {"success": False, "reason": "Slot already taken"}
                else:
                    return {"success": True}
    except Exception as e:
        return {"success": False, "reason": str(e)}
