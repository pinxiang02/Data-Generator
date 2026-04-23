import paho.mqtt.client as mqtt
import json
import time

BROKER = "127.0.0.1"
PORT = 1884
TOPIC = "factory/nodes/manual-test"

payload = {
    "MachineID": "TEST-UNIT-01",
    "Temperature": 24.5,
    "Status": "OK",
    "ManualOverride": True,
    "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
}

def send_test_message():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    try:
        print(f"Connecting to broker at {BROKER}:{PORT}...")
        client.connect(BROKER, PORT, 60)
        
        message = json.dumps(payload)
        print(f"Sending payload to topic [{TOPIC}]:")
        print(message)
        
        client.publish(TOPIC, message)
        print("Message published successfully!")
        
        client.disconnect()
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Check if your Docker 'mqtt_broker' container is running.")
        
if __name__ == "__main__":
    send_test_message()