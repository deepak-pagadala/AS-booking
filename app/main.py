from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from app.agent import run_booking_agent
import traceback
import sys

app = FastAPI()

class TestSMS(BaseModel):
    From: str
    Body: str

@app.post("/sms")
async def sms_reply(request: Request):
    form = await request.form()
    user_number = form.get("From")
    user_message = form.get("Body")
    
    response_text = await run_booking_agent(user_number, user_message)
    return PlainTextResponse(content=response_text)

# 👇 Add this test endpoint for Swagger UI or JSON testing


@app.post("/sms-test")
async def sms_test(request: Request):
    data = await request.json()
    try:
        reply = await run_booking_agent(data.get("From", ""), data.get("Body", ""))
        return PlainTextResponse(reply)
    except Exception:
        traceback.print_exc(file=sys.stderr)   # <-- force traceback
        return PlainTextResponse("500 error", status_code=500)