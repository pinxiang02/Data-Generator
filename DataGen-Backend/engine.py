import asyncio
import random
import time
from database import SessionLocal
import models
from datetime import datetime, timezone
import transmitter
import httpx

# Global memory
latest_telemetry = {} 
active_tasks = {}
runtime_configs = {} # <-- NEW: Temporarily holds the API ID for the running session

def generate_value(node: models.Node):
    """Processes generation logic for the 3 required modes."""
    try:
        if node.generation_mode == "Fixed":
            if node.data_type_enum == "Integer": return int(node.fixed_value) if node.fixed_value else 0
            elif node.data_type_enum == "Float": return float(node.fixed_value) if node.fixed_value else 0.0
            elif node.data_type_enum == "Boolean": return str(node.fixed_value).lower() in ['true', '1', 't', 'y', 'yes']
            return node.fixed_value
        elif node.generation_mode == "Random":
            min_v = float(node.min_range or 0)
            max_v = float(node.max_range or 100)
            if node.data_type_enum == "Integer": return random.randint(int(min_v), int(max_v))
            elif node.data_type_enum == "Float": return round(random.uniform(min_v, max_v), 4)
            return random.choice([True, False]) if node.data_type_enum == "Boolean" else "rand_str"
        elif node.generation_mode == "List" and node.value_list:
            items = [i.strip() for i in str(node.value_list).split(",")]
            return random.choice(items)
    except: return None

async def generator_worker(generator_id: int):
    """Background loop that writes to UI and sends to API & MQTT."""
    
    # Retrieve BOTH configurations from memory for this session
    config = runtime_configs.get(generator_id, {})
    api_config = config.get("api_config")
    mqtt_config = config.get("mqtt_config") # <-- NEW: Fetch MQTT config
    
    print(f"\n[SYSTEM] Worker Started for Generator #{generator_id}")
    if api_config:
        print(f"[SYSTEM] Loaded API Destination: {api_config['method']} {api_config['url']}")
    if mqtt_config:
        print(f"[SYSTEM] Loaded MQTT Broker: {mqtt_config.get('host')}:{mqtt_config.get('port')} | Topic: {mqtt_config.get('topic')}")
    if not api_config and not mqtt_config:
        print("[SYSTEM] No Destinations selected. Running in Local Mode.")
    print("-" * 50)
    
    # Removed the 'async with httpx.AsyncClient()' block. 
    # The transmitter.py file now handles the connections.
    while True:
        with SessionLocal() as db:
            # Still need DB for the dynamic nodes
            nodes = db.query(models.Node).filter(models.Node.generator_id == generator_id).all()
            
            # 1. Generate the dynamic node data
            payload = {n.node_name: generate_value(n) for n in nodes}
            payload["@timestamp"] = datetime.now(timezone.utc).isoformat()
            
            print(f"📦 GENERATED PAYLOAD (Gen #{generator_id}):\n{payload}")

            api_log_msg = None
            mqtt_log_msg = None

            # 2. Use transmitter.py to send to API
            if api_config:
                api_log_msg = await transmitter.send_to_api(api_config, payload)
                print(f"   🌐 {api_log_msg}")

            # 3. Use transmitter.py to send to MQTT
            if mqtt_config:
                mqtt_log_msg = await transmitter.publish_to_mqtt(mqtt_config, payload)
                print(f"   📡 {mqtt_log_msg}")

            # 4. Update UI Memory so Vue can poll it!
            latest_telemetry[generator_id] = {
                "data": payload, 
                "timestamp": time.time(),
                "api_log": api_log_msg,
                "mqtt_log": mqtt_log_msg # <-- Added to telemetry
            }
                    
        await asyncio.sleep(1.0)
        
# Update the arguments to accept mqtt_config
def start_generator(generator_id: int, api_config: dict = None, mqtt_config: dict = None) -> bool:
    if generator_id in active_tasks: 
        return False
        
    # Store BOTH configurations in memory
    runtime_configs[generator_id] = {
        "api_config": api_config,
        "mqtt_config": mqtt_config
    }
    
    loop = asyncio.get_running_loop()
    active_tasks[generator_id] = loop.create_task(generator_worker(generator_id))
    return True

def stop_generator(generator_id: int) -> bool:
    if generator_id in active_tasks:
        active_tasks[generator_id].cancel()
        del active_tasks[generator_id]
        
        # Clean up the memory when stopped
        if generator_id in runtime_configs:
            del runtime_configs[generator_id]
            
        return True
    return False