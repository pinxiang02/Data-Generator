import httpx
import json
import aiomqtt
import asyncio

async def send_to_api(api_config: dict, payload: dict) -> str:
    """Sends payload and returns a status string for the UI."""
    if not api_config:
        return ""

    async with httpx.AsyncClient() as client:
        try:
            res = await client.request(
                method=api_config.get('method', 'POST'),
                url=api_config['url'],
                json=payload,
                headers=api_config.get('headers', {}),
                timeout=2.0
            )
            return f"[{res.status_code}] Success -> {api_config['url']}"
        except Exception as e:
            return f"[Error] {str(e)}"
        
async def publish_to_mqtt(mqtt_config: dict, payload: dict) -> str:
    """Publishes JSON payload to MQTT broker with a strict non-blocking timeout."""
    if not mqtt_config:
        return ""

    # Force 127.0.0.1 to avoid Windows IPv6 Docker routing issues
    raw_broker = mqtt_config.get('host', '127.0.0.1')
    broker = '127.0.0.1' if raw_broker.lower() == 'localhost' else raw_broker
    
    port = mqtt_config.get('port', 1883)
    topic = mqtt_config.get('topic', 'factory/nodes/default')

    # Define the actual transmission logic as an internal coroutine
    async def _publish():
        async with aiomqtt.Client(hostname=broker, port=port) as client:
            json_payload = json.dumps(payload)
            await client.publish(topic, payload=json_payload)
        return f"[Published] Success -> {broker}:{port} | Topic: {topic}"

    try:
        # Wrap the connection and publish in a strict 0.5-second timeout
        # If the broker is offline, the generator loop will NOT stall.
        return await asyncio.wait_for(_publish(), timeout=0.5)
    
    except asyncio.TimeoutError:
        return f"[Error] MQTT Publish: Connection timed out (Fast fail)"
    except Exception as e:
        return f"[Error] MQTT Publish: {str(e)}"