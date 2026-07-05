import httpx
import json
import asyncio
import paho.mqtt.publish as mqtt_publish
import dbutil

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
    """Publishes a JSON payload to an MQTT broker with a non-blocking timeout.

    Uses paho's synchronous one-shot publish (connect + publish + disconnect)
    run in a worker thread. This avoids aiomqtt, which depends on
    loop.add_reader/add_writer -- unsupported by the Windows Proactor event
    loop that uvicorn uses by default (it raises NotImplementedError, which
    previously surfaced here as a misleading "connection timed out").
    """
    if not mqtt_config:
        return ""

    # Force 127.0.0.1 to avoid Windows IPv6 Docker routing issues
    raw_broker = mqtt_config.get('host', '127.0.0.1')
    broker = '127.0.0.1' if raw_broker.lower() == 'localhost' else raw_broker

    port = mqtt_config.get('port', 1883)
    topic = mqtt_config.get('topic', 'factory/nodes/default')
    json_payload = json.dumps(payload)

    # Synchronous connect+publish+disconnect; safe to run off the event loop.
    def _publish():
        mqtt_publish.single(
            topic,
            payload=json_payload,
            hostname=broker,
            port=port,
            keepalive=5,
        )

    try:
        # Run the blocking publish in a thread with a timeout so a dead broker
        # can never stall the generator loop.
        await asyncio.wait_for(asyncio.to_thread(_publish), timeout=3.0)
        return f"[Published] Success -> {broker}:{port} | Topic: {topic}"

    except asyncio.TimeoutError:
        return f"[Error] MQTT Publish: Connection timed out"
    except Exception as e:
        return f"[Error] MQTT Publish: {str(e)}"


async def insert_to_database(db_config: dict, payload: dict) -> str:
    """Insert one payload row/document into the configured database.

    db_config = {db_type, conn, table, columns}. Works for PostgreSQL, MySQL,
    Oracle (relational) and MongoDB (document). The blocking driver call runs in
    a worker thread with a timeout so a slow/dead DB can't stall the generator.
    The table/collection is never created or altered here (per requirements).
    """
    if not db_config:
        return ""

    db_type = db_config.get("db_type", "PostgreSQL")
    conn = db_config["conn"]
    table = db_config["table"]
    columns = db_config.get("columns", {})

    def _insert():
        return dbutil.insert_row(db_type, conn, table, columns, payload)

    try:
        return await asyncio.wait_for(asyncio.to_thread(_insert), timeout=5.0)
    except asyncio.TimeoutError:
        return "[Error] DB Insert: timed out"
    except Exception as e:
        return f"[Error] DB Insert: {str(e).splitlines()[0]}"