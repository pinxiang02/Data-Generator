"""
DataGen API Test Client
-----------------------
A tiny HTTP endpoint that accepts ANY JSON payload the Data Generator sends
and prints it to the console. Use this to confirm the generator's API
destination is working, regardless of which nodes are configured.

Run:
    python test_api_client.py
Then point a generator's API destination at:
    http://127.0.0.1:9000/ingest   (Method: POST)
"""
import json
import sys
from datetime import datetime

from fastapi import FastAPI, Request
import uvicorn

# Windows consoles default to cp1252, which cannot encode some characters.
# Reconfiguring to UTF-8 keeps printing payloads from ever crashing the client.
# line_buffering=True flushes each line immediately so output shows promptly.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

app = FastAPI(title="DataGen API Test Client")

state = {"received": 0}


@app.get("/")
def health():
    """Simple status endpoint so you can see the client is alive in a browser."""
    return {"status": "API test client running", "messages_received": state["received"]}


@app.post("/ingest")
async def ingest(request: Request):
    """Accept any JSON body, print it, and echo back a receipt."""
    state["received"] += 1

    try:
        payload = await request.json()
    except Exception:
        # Not valid JSON? Show the raw body so nothing is silently dropped.
        raw = (await request.body()).decode(errors="replace")
        payload = {"_raw_body": raw}

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}]  #{state['received']}  POST /ingest")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("-" * 55)

    keys = list(payload.keys()) if isinstance(payload, dict) else None
    return {"status": "received", "count": state["received"], "keys": keys}


if __name__ == "__main__":
    print("=" * 55)
    print(" DataGen API Test Client")
    print(" Listening on : http://127.0.0.1:9000")
    print(" Point generator API destination at: /ingest  (POST)")
    print("=" * 55)
    uvicorn.run(app, host="127.0.0.1", port=9000)
