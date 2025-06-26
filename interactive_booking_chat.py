import httpx

BASE_URL = "http://localhost:8000/sms-test"
USER_NUMBER = "+15551234567"  # Use the same number for the session

print("=== Chat with your Booking AI ===")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    if user_input.lower().strip() in ("exit", "quit"):
        print("Goodbye!")
        break

    payload = {
        "From": USER_NUMBER,
        "Body": user_input
    }
    try:
        response = httpx.post(BASE_URL, json=payload)
        response.raise_for_status()
        print("AI:", response.text)
    except Exception as e:
        print(f"❌ Error: {e}")
