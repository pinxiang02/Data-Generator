import asyncio
import math
import random
import string
import sys
import time
import uuid
from database import SessionLocal
import models
from datetime import datetime, timezone
import transmitter
from ws_manager import ws_manager

# On Windows a redirected stdout defaults to cp1252, which cannot encode the
# emoji used in the log lines below. A failed print must never kill a worker.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Global memory
latest_telemetry = {}
active_tasks = {}
runtime_configs = {}   # holds the API/MQTT config for the running session
message_counts = {}    # generator_id -> number of payloads generated this run
run_state = {}         # generator_id -> {node_id: {...}} state for stateful modes

def generate_value(node: models.Node, state: dict = None):
    """Generate one value for a node.

    Modes: Fixed, Random, List, Sequential, Sine, Timestamp, UUID.
    `state` is a per-node dict (persisted for the run) used by the stateful
    modes (Sequential counter, Sine phase).
    """
    if state is None:
        state = {}
    try:
        mode = node.generation_mode

        if mode == "Fixed":
            if node.data_type_enum == "Integer": return int(node.fixed_value) if node.fixed_value else 0
            elif node.data_type_enum == "Float": return float(node.fixed_value) if node.fixed_value else 0.0
            elif node.data_type_enum == "Boolean": return str(node.fixed_value).lower() in ['true', '1', 't', 'y', 'yes']
            return node.fixed_value

        elif mode == "Random":
            min_v = float(node.min_range or 0)
            max_v = float(node.max_range or 100)
            if min_v > max_v: min_v, max_v = max_v, min_v  # Guard against swapped ranges
            if node.data_type_enum == "Integer": return random.randint(int(min_v), int(max_v))
            elif node.data_type_enum == "Float": return round(random.uniform(min_v, max_v), 4)
            elif node.data_type_enum == "Boolean": return random.choice([True, False])
            # String: random alphanumeric, length from max_range (default 8)
            length = max(1, int(max_v)) if node.max_range is not None else 8
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

        elif mode == "List" and node.value_list:
            items = [i.strip() for i in str(node.value_list).split(",") if i.strip()]
            return random.choice(items) if items else None

        elif mode == "Sequential":
            # Auto-incrementing counter starting at min_range (default 0), step 1.
            if "seq" not in state:
                state["seq"] = int(node.min_range or 0)
            value = state["seq"]
            state["seq"] += 1
            return value

        elif mode == "Sine":
            # Smooth oscillation between min_range and max_range.
            min_v = float(node.min_range if node.min_range is not None else 0)
            max_v = float(node.max_range if node.max_range is not None else 100)
            if min_v > max_v: min_v, max_v = max_v, min_v
            mid = (min_v + max_v) / 2.0
            amp = (max_v - min_v) / 2.0
            t = state.get("t", 0.0)
            state["t"] = t + 0.2
            return round(mid + amp * math.sin(t), 4)

        elif mode == "Timestamp":
            # Epoch seconds for Integer, ISO-8601 otherwise.
            if node.data_type_enum == "Integer":
                return int(time.time())
            return datetime.now(timezone.utc).isoformat()

        elif mode == "UUID":
            return str(uuid.uuid4())

        return None
    except Exception as e:
        print(f"[ENGINE] Failed to generate value for node '{node.node_name}': {e}")
        return None

async def generator_worker(generator_id: int):
    """Background loop that writes to UI and sends to API & MQTT."""
    
    # Retrieve BOTH configurations from memory for this session
    config = runtime_configs.get(generator_id, {})
    api_config = config.get("api_config")
    mqtt_config = config.get("mqtt_config")
    db_config = config.get("db_config")

    print(f"\n[SYSTEM] Worker Started for Generator #{generator_id}")
    if api_config:
        print(f"[SYSTEM] Loaded API Destination: {api_config['method']} {api_config['url']}")
    if mqtt_config:
        print(f"[SYSTEM] Loaded MQTT Broker: {mqtt_config.get('host')}:{mqtt_config.get('port')} | Topic: {mqtt_config.get('topic')}")
    if db_config:
        print(f"[SYSTEM] Loaded Database: table '{db_config.get('table')}'")
    if not api_config and not mqtt_config and not db_config:
        print("[SYSTEM] No Destinations selected. Running in Local Mode.")
    print("-" * 50)
    
    # Removed the 'async with httpx.AsyncClient()' block. 
    # The transmitter.py file now handles the connections.
    interval_s = 1.0
    while True:
      # A failure in one iteration (DB hiccup, logging, serialization) must not
      # silently kill the whole generator loop.
      try:
        with SessionLocal() as db:
            # Still need DB for the dynamic nodes (and the configurable interval)
            gen = db.query(models.Generator).filter(models.Generator.id == generator_id).first()
            if gen and gen.interval_ms:
                interval_s = max(0.1, gen.interval_ms / 1000.0)

            nodes = db.query(models.Node).filter(models.Node.generator_id == generator_id).all()

            # 1. Generate the dynamic node data (passing per-node state for
            #    stateful modes like Sequential/Sine).
            node_states = run_state.setdefault(generator_id, {})
            payload = {
                n.node_name: generate_value(n, node_states.setdefault(n.id, {}))
                for n in nodes
            }
            payload["@timestamp"] = datetime.now(timezone.utc).isoformat()

            # Track how many payloads this generator has produced this run.
            message_counts[generator_id] = message_counts.get(generator_id, 0) + 1

            print(f"📦 GENERATED PAYLOAD (Gen #{generator_id}):\n{payload}")

            api_log_msg = None
            mqtt_log_msg = None
            db_log_msg = None

            # 2. Use transmitter.py to send to API
            if api_config:
                api_log_msg = await transmitter.send_to_api(api_config, payload)
                print(f"   🌐 {api_log_msg}")

            # 3. Use transmitter.py to send to MQTT
            if mqtt_config:
                mqtt_log_msg = await transmitter.publish_to_mqtt(mqtt_config, payload)
                print(f"   📡 {mqtt_log_msg}")

            # 4. Use transmitter.py to insert into the database
            if db_config:
                db_log_msg = await transmitter.insert_to_database(db_config, payload)
                print(f"   🗄️ {db_log_msg}")

            # 5. Update UI Memory so Vue can poll it!
            latest_telemetry[generator_id] = {
                "data": payload,
                "timestamp": time.time(),
                "api_log": api_log_msg,
                "mqtt_log": mqtt_log_msg,
                "db_log": db_log_msg
            }

            # 5. Push the same telemetry to any connected WebSocket clients
            await ws_manager.broadcast(generator_id, "telemetry", latest_telemetry[generator_id])

      except asyncio.CancelledError:
        raise
      except Exception as e:
        print(f"[ENGINE] Worker iteration error (Gen #{generator_id}): {e}")

      await asyncio.sleep(interval_s)
        
# Update the arguments to accept mqtt_config
def start_generator(generator_id: int, api_config: dict = None, mqtt_config: dict = None, db_config: dict = None) -> bool:
    if generator_id in active_tasks:
        return False

    # Store all destination configurations in memory
    runtime_configs[generator_id] = {
        "api_config": api_config,
        "mqtt_config": mqtt_config,
        "db_config": db_config
    }

    # Fresh counters/state for this run
    message_counts[generator_id] = 0
    run_state[generator_id] = {}

    loop = asyncio.get_running_loop()
    active_tasks[generator_id] = loop.create_task(generator_worker(generator_id))
    return True

def stop_generator(generator_id: int) -> bool:
    if generator_id in active_tasks:
        active_tasks[generator_id].cancel()
        del active_tasks[generator_id]
        
        # Clean up the memory when stopped (keep message_counts so the UI can
        # still show the final total after stopping).
        runtime_configs.pop(generator_id, None)
        run_state.pop(generator_id, None)

        return True
    return False