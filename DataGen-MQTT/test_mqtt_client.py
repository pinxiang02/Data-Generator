"""
DataGen MQTT Test Client
------------------------
Connects to the local Mosquitto broker and prints EVERY message published to
it. Use this to confirm the generator's MQTT destination is working.

Note on ports (local machine):
    * Mosquitto (from Docker/docker-compose-mqtt.yml) is exposed on :1884
    * :1883 locally is NATS, not Mosquitto -- so point the generator's broker
      config at port 1884.

Run (paho-mqtt is available in the Manual-Publisher venv):
    ../Manual-Publisher/publisher/Scripts/python.exe test_mqtt_client.py
    # or, in any env with paho-mqtt installed:
    python test_mqtt_client.py
"""
import sys
from datetime import datetime

import paho.mqtt.client as mqtt

# Windows consoles default to cp1252; UTF-8 keeps payload printing crash-proof.
# line_buffering=True flushes each line immediately, so output shows promptly
# even when piped to a file or another process.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

BROKER = "127.0.0.1"
PORT = 1884          # Mosquitto's exposed port (see note above)
TOPIC = "#"          # Subscribe to everything; generator uses factory/nodes/...

state = {"received": 0}


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to broker {BROKER}:{PORT}")
        client.subscribe(TOPIC)
        print(f"Subscribed to '{TOPIC}'. Waiting for messages...\n")
    else:
        print(f"Connection failed (reason code {reason_code})")


def on_message(client, userdata, msg):
    state["received"] += 1
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}]  #{state['received']}  topic: {msg.topic}")
    print(msg.payload.decode(errors="replace"))
    print("-" * 55)


def main():
    print("=" * 55)
    print(" DataGen MQTT Test Client")
    print(f" Broker : {BROKER}:{PORT}   Topic: {TOPIC}")
    print("=" * 55)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
    except Exception as e:
        print(f"Could not connect to {BROKER}:{PORT} -> {e}")
        print("Is the Mosquitto broker running? (docker compose -f Docker/docker-compose-mqtt.yml up -d)")
        return

    client.loop_forever()


if __name__ == "__main__":
    main()
