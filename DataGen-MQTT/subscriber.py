import os
import time
import paho.mqtt.client as mqtt

# Internal Docker hostname for the broker
BROKER = "mosquitto" 
PORT = 1883
TOPIC = "factory/nodes/#"

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("✅ SUCCESS: Connected to Broker!", flush=True)
        client.subscribe(TOPIC)
        print(f"📡 Subscribed to: {TOPIC}", flush=True)
    else:
        print(f"❌ FAILED: Connection error code {reason_code}", flush=True)

def on_message(client, userdata, msg):
    print(f"\n📥 DATA RECEIVED [{msg.topic}]:", flush=True)
    print(msg.payload.decode(), flush=True)
    print("-" * 30, flush=True)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print("🚀 Subscriber Starting...", flush=True)

connected = False
while not connected:
    try:
        client.connect(BROKER, PORT, 60)
        connected = True
    except Exception as e:
        print(f"⏳ Waiting for Broker... ({e})", flush=True)
        time.sleep(2)

client.loop_forever()