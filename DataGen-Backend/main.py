from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from ws_manager import ws_manager
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models
import database
import engine
import transmitter
from pydantic import BaseModel
from typing import Optional

class APICreate(BaseModel):
    APIName: str
    TargetUrl: str
    Method: str = "POST"
    HeaderName: Optional[str] = None
    HeaderValue: Optional[str] = None

class MQTTCreate(BaseModel):
    MQTTName: str
    Host: str = "localhost" # <-- NEW
    Port: int = 1883        # <-- NEW
    Topic: str

class EngineStartPayload(BaseModel):
    target_api_id: Optional[int] = None
    target_mqtt_id: Optional[int] = None

# Auto-create tables in Postgres
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "Backend is running with pg8000"}

@app.post("/generators/")
def create_generator(name: str, desc: str, db: Session = Depends(database.get_db)):
    new_gen = models.Generator(name=name, description=desc)
    db.add(new_gen)
    db.commit()
    db.refresh(new_gen)
    return new_gen

@app.get("/generators/")
def list_generators(db: Session = Depends(database.get_db)):
    return db.query(models.Generator).all()

@app.put("/generators/{generator_id}")
def update_generator(generator_id: int, name: str, desc: str, db: Session = Depends(database.get_db)):
    gen = db.query(models.Generator).filter(models.Generator.id == generator_id).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generator not found")
    gen.name = name
    gen.description = desc
    db.commit()
    db.refresh(gen)
    return gen

@app.delete("/generators/{generator_id}")
def delete_generator(generator_id: int, db: Session = Depends(database.get_db)):
    gen = db.query(models.Generator).filter(models.Generator.id == generator_id).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generator not found")
    db.delete(gen)
    db.commit()
    return {"message": "Deleted"}

@app.post("/generators/{generator_id}/start")
async def start_generator_endpoint(
    generator_id: int, 
    payload: EngineStartPayload,
    db: Session = Depends(database.get_db)
):
    api_config_dict = None
    mqtt_config_dict = None
    
    # --- 1. Process API Configuration ---
    if payload.target_api_id:
        api_record = db.query(models.API).filter(models.API.APIid == payload.target_api_id).first()
        if not api_record:
            raise HTTPException(status_code=404, detail="Selected API Target not found.")
            
        headers = {}
        if api_record.HeaderName and api_record.HeaderValue:
            headers[api_record.HeaderName] = api_record.HeaderValue
            
        api_config_dict = {
            "id": api_record.APIid,
            "url": api_record.TargetUrl,
            "method": api_record.Method.upper(),
            "headers": headers
        }

    # --- 2. Process MQTT Configuration (NEW) ---
    if payload.target_mqtt_id:
        mqtt_record = db.query(models.MQTT).filter(models.MQTT.MQTTid == payload.target_mqtt_id).first()
        if not mqtt_record:
            raise HTTPException(status_code=404, detail="Selected MQTT Broker not found.")
            
        mqtt_config_dict = {
            "id": mqtt_record.MQTTid,
            "host": mqtt_record.Host,
            "port": mqtt_record.Port,
            "topic": mqtt_record.Topic
        }

    # --- 3. Pass both compiled dictionaries to the engine ---
    # Ensure your start_generator function in engine.py is updated to accept both!
    success = engine.start_generator(
        generator_id, 
        api_config=api_config_dict, 
        mqtt_config=mqtt_config_dict
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Already running")
    
    # --- 4. Detailed Response Message ---
    modes = []
    if api_config_dict: modes.append("API")
    if mqtt_config_dict: modes.append("MQTT")
    
    return {
        "status": "started", 
        "active_destinations": modes if modes else ["Local Display Only"]
    }

@app.post("/generators/{generator_id}/stop")
async def stop_engine(generator_id: int): # <--- ADD 'async' HERE
    success = engine.stop_generator(generator_id)
    if not success:
        raise HTTPException(status_code=400, detail="Engine is not running")
    return {"message": "Engine stopped"}

@app.get("/generators/{generator_id}/telemetry")
def get_telemetry(generator_id: int):
    # This feeds the Vue polling logic
    return engine.latest_telemetry.get(generator_id, {"status": "waiting", "timestamp": 0})

# --- NODE CRUD ENDPOINTS ---

@app.get("/generators/{generator_id}/nodes/")
def get_nodes(generator_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.Node).filter(models.Node.generator_id == generator_id).all()

@app.post("/generators/{generator_id}/nodes/")
def create_node(generator_id: int, node_data: dict, db: Session = Depends(database.get_db)):
    new_node = models.Node(**node_data, generator_id=generator_id)
    db.add(new_node); db.commit(); db.refresh(new_node)
    return new_node

@app.put("/generators/{generator_id}/nodes/{node_id}")
def update_node(generator_id: int, node_id: int, node_data: dict, db: Session = Depends(database.get_db)):
    db_node = db.query(models.Node).filter(models.Node.id == node_id, models.Node.generator_id == generator_id).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    for key, value in node_data.items():
        setattr(db_node, key, value)
        
    db.commit()
    db.refresh(db_node)
    return db_node

@app.delete("/generators/{generator_id}/nodes/{node_id}")
def delete_node(generator_id: int, node_id: int, db: Session = Depends(database.get_db)):
    db_node = db.query(models.Node).filter(models.Node.id == node_id, models.Node.generator_id == generator_id).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(db_node)
    db.commit()
    return {"message": "Node deleted"}

# ==========================================
# API DESTINATION ENDPOINTS
# ==========================================
@app.get("/apis/")
def list_apis(db: Session = Depends(database.get_db)):
    return db.query(models.API).all()

@app.post("/apis/")
def create_api(api_data: APICreate, db: Session = Depends(database.get_db)):
    # .model_dump() is for Pydantic v2; use .dict() if on v1
    new_api = models.API(**api_data.dict()) 
    db.add(new_api)
    db.commit()
    db.refresh(new_api)
    return new_api

@app.delete("/apis/{api_id}")
def delete_api(api_id: int, db: Session = Depends(database.get_db)):
    api = db.query(models.API).filter(models.API.APIid == api_id).first()
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    db.delete(api)
    db.commit()
    return {"message": "API deleted"}

# ==========================================
# MQTT BROKER ENDPOINTS
# ==========================================
@app.get("/mqtt/")
def list_mqtt(db: Session = Depends(database.get_db)):
    return db.query(models.MQTT).all()

@app.post("/mqtt/")
def create_mqtt(mqtt_data: MQTTCreate, db: Session = Depends(database.get_db)):
    new_mqtt = models.MQTT(**mqtt_data.dict())
    db.add(new_mqtt)
    db.commit()
    db.refresh(new_mqtt)
    return new_mqtt

@app.delete("/mqtt/{mqtt_id}")
def delete_mqtt(mqtt_id: int, db: Session = Depends(database.get_db)):
    mqtt = db.query(models.MQTT).filter(models.MQTT.MQTTid == mqtt_id).first()
    if not mqtt:
        raise HTTPException(status_code=404, detail="MQTT config not found")
    db.delete(mqtt)
    db.commit()
    return {"message": "MQTT config deleted"}

@app.websocket("/ws/generators/{generator_id}")
async def websocket_endpoint(websocket: WebSocket, generator_id: int):
    await ws_manager.connect(websocket, generator_id)
    try:
        while True:
            # Keeps the pipe open so the engine can push data to the UI
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, generator_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)