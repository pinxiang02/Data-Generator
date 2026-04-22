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
    """Background loop that writes to UI and sends to API."""
    
    # Retrieve the API configuration from memory for this session
    api_config = runtime_configs.get(generator_id, {}).get("api_config")
    
    print(f"\n[SYSTEM] Worker Started for Generator #{generator_id}")
    if api_config:
        print(f"[SYSTEM] Loaded API Destination: {api_config['method']} {api_config['url']}")
    else:
        print("[SYSTEM] No API Destination selected. Running in Local Mode.")
    print("-" * 50)
    
    # Open a persistent HTTP client for performance
    async with httpx.AsyncClient() as http_client:
        while True:
            with SessionLocal() as db:
                # Still need DB for the dynamic nodes
                nodes = db.query(models.Node).filter(models.Node.generator_id == generator_id).all()
                
                # 1. Generate the dynamic node data
                payload = {n.node_name: generate_value(n) for n in nodes}
                payload["@timestamp"] = datetime.now(timezone.utc).isoformat()
                
                # 2. Update UI Memory
                latest_telemetry[generator_id] = {"data": payload, "timestamp": time.time()}
                print(f"📦 GENERATED PAYLOAD (Gen #{generator_id}):\n{payload}")

                # 3. Use the cached API Config to send the data
                # 3. Use the cached API Config to send the data
                if api_config:
                    try:
                        if api_config["method"] == "POST":
                            res = await http_client.post(api_config["url"], json=payload, headers=api_config["headers"])
                        elif api_config["method"] == "PUT":
                            res = await http_client.put(api_config["url"], json=payload, headers=api_config["headers"])
                        elif api_config["method"] == "PATCH":
                            res = await http_client.patch(api_config["url"], json=payload, headers=api_config["headers"])
                            
                        # Grab the actual text body the API responded with
                        response_body = res.text 
                            
                        print(f"   ✅ API RESPONSE: [{res.status_code}] -> {api_config['url']}")
                        print(f"   📝 API SAYS: {response_body}")
                        
                        # Add it back to UI Memory so Vue can poll it!
                        latest_telemetry[generator_id] = {
                            "data": payload, 
                            "timestamp": time.time(),
                            "api_log": f"[{res.status_code}] {response_body}" # <-- Added this back
                        }
                        
                    except Exception as e:
                        print(f"   ❌ API FAILED: {str(e)}")
                        latest_telemetry[generator_id] = {
                            "data": payload, 
                            "timestamp": time.time(),
                            "api_log": f"[Error] {str(e)}"
                        }
                else:
                    # If no API is selected, just update the payload display
                    latest_telemetry[generator_id] = {
                        "data": payload, 
                        "timestamp": time.time(),
                        "api_log": None
                    }
                            
            await asyncio.sleep(1.0)

# CHANGED: Added target_api_id argument so main.py doesn't throw a TypeError
def start_generator(generator_id: int, api_config: dict = None) -> bool:
    if generator_id in active_tasks: 
        return False
        
    # Store the complete API details in memory for future use by the worker
    runtime_configs[generator_id] = {"api_config": api_config}
    
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