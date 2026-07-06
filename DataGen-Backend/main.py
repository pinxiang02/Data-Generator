from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from ws_manager import ws_manager
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional

import models
import database
import engine
import transmitter
import schemas
import auth
import dbutil

# Auto-create tables in Postgres (includes the new users table)
models.Base.metadata.create_all(bind=database.engine)


# Lightweight in-place migrations for databases created with an older schema.
# create_all() only creates missing tables; it never alters existing ones.
def run_migrations():
    statements = [
        "ALTER TABLE generators ADD COLUMN IF NOT EXISTS selected_api_id INTEGER",
        "ALTER TABLE generators ADD COLUMN IF NOT EXISTS selected_mqtt_id INTEGER",
        "ALTER TABLE generators ADD COLUMN IF NOT EXISTS user_id INTEGER",
        "ALTER TABLE generators ADD COLUMN IF NOT EXISTS is_database_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE generators ADD COLUMN IF NOT EXISTS selected_db_id INTEGER",
        "ALTER TABLE apis ADD COLUMN IF NOT EXISTS user_id INTEGER",
        "ALTER TABLE mqtt_configs ADD COLUMN IF NOT EXISTS user_id INTEGER",
        "ALTER TABLE nodes ADD COLUMN IF NOT EXISTS faker_type VARCHAR",
        "ALTER TABLE apis ALTER COLUMN generator_id DROP NOT NULL",
        "ALTER TABLE mqtt_configs ALTER COLUMN generator_id DROP NOT NULL",
    ]
    with database.engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                print(f"[MIGRATION] Skipped '{stmt}': {e}")


run_migrations()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Ownership helper: fetch a generator that belongs to the current user, or 404 ---
def owned_generator(generator_id: int, user: models.User, db: Session) -> models.Generator:
    gen = db.query(models.Generator).filter(
        models.Generator.id == generator_id,
        models.Generator.user_id == user.id,
    ).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generator not found")
    return gen


@app.get("/")
def health_check():
    return {"status": "Backend is running with pg8000"}


# ==========================================
# AUTH ENDPOINTS
# ==========================================
@app.post("/auth/signup", response_model=schemas.Token)
def signup(user_data: schemas.UserCreate, db: Session = Depends(database.get_db)):
    username = user_data.username.strip()
    if not username or not user_data.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    exists = db.query(models.User).filter(models.User.username == username).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = models.User(username=username, hashed_password=auth.hash_password(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.Token(access_token=auth.create_access_token(user), username=user.username)


@app.post("/auth/login", response_model=schemas.Token)
def login(user_data: schemas.UserCreate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == user_data.username.strip()).first()
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return schemas.Token(access_token=auth.create_access_token(user), username=user.username)


@app.get("/auth/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ==========================================
# GENERATOR ENDPOINTS (scoped to current user)
# ==========================================
@app.post("/generators/")
def create_generator(
    name: str,
    desc: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    new_gen = models.Generator(name=name, description=desc, user_id=current_user.id)
    db.add(new_gen)
    db.commit()
    db.refresh(new_gen)
    return new_gen


@app.get("/generators/")
def list_generators(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    return db.query(models.Generator).filter(models.Generator.user_id == current_user.id).all()


@app.get("/generators/status")
def generators_status(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Which of the user's generators are running, plus messages sent so far."""
    gens = db.query(models.Generator.id).filter(models.Generator.user_id == current_user.id).all()
    result = {}
    for (gid,) in gens:
        result[gid] = {
            "running": gid in engine.active_tasks,
            "count": engine.message_counts.get(gid, 0),
        }
    return result


@app.put("/generators/{generator_id}")
def update_generator(
    generator_id: int,
    name: Optional[str] = None,
    desc: Optional[str] = None,
    gen_update: Optional[schemas.GeneratorUpdate] = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    db_generator = owned_generator(generator_id, current_user, db)

    # Query params (edit modal). 'if name:' protects against empty strings.
    if name:
        db_generator.name = name
    if desc:
        db_generator.description = desc

    # JSON body (destination settings / interval)
    if gen_update:
        update_data = gen_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key in ["name", "description"] and not value:
                continue
            setattr(db_generator, key, value)

    db.commit()
    db.refresh(db_generator)
    return db_generator


@app.delete("/generators/{generator_id}")
def delete_generator(
    generator_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    gen = owned_generator(generator_id, current_user, db)
    engine.stop_generator(generator_id)  # ensure no orphan worker keeps running
    db.delete(gen)
    db.commit()
    return {"message": "Deleted"}


@app.post("/generators/{generator_id}/start")
async def start_generator_endpoint(
    generator_id: int,
    payload: schemas.EngineStartPayload,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    gen = owned_generator(generator_id, current_user, db)

    api_config_dict = None
    mqtt_config_dict = None
    db_config_dict = None

    # Fallback to the generator's saved destination settings (empty-payload start).
    if payload.target_api_id is None and payload.target_mqtt_id is None and payload.target_db_id is None:
        if gen.is_api_enabled and gen.selected_api_id:
            payload.target_api_id = gen.selected_api_id
        if gen.is_message_broker_enabled and gen.selected_mqtt_id:
            payload.target_mqtt_id = gen.selected_mqtt_id
        if gen.is_database_enabled and gen.selected_db_id:
            payload.target_db_id = gen.selected_db_id

    # API config (must belong to the user)
    if payload.target_api_id:
        api_record = db.query(models.API).filter(
            models.API.APIid == payload.target_api_id,
            models.API.user_id == current_user.id,
        ).first()
        if not api_record:
            raise HTTPException(status_code=404, detail="Selected API Target not found.")
        headers = {}
        if api_record.HeaderName and api_record.HeaderValue:
            headers[api_record.HeaderName] = api_record.HeaderValue
        api_config_dict = {
            "id": api_record.APIid,
            "url": api_record.TargetUrl,
            "method": api_record.Method.upper(),
            "headers": headers,
        }

    # MQTT config (must belong to the user)
    if payload.target_mqtt_id:
        mqtt_record = db.query(models.MQTT).filter(
            models.MQTT.MQTTid == payload.target_mqtt_id,
            models.MQTT.user_id == current_user.id,
        ).first()
        if not mqtt_record:
            raise HTTPException(status_code=404, detail="Selected MQTT Broker not found.")
        mqtt_config_dict = {
            "id": mqtt_record.MQTTid,
            "host": mqtt_record.Host,
            "port": mqtt_record.Port,
            "topic": mqtt_record.Topic,
        }

    # Database config (must belong to the user). We introspect the target table
    # and validate schema alignment here so the user gets a clear error BEFORE
    # the engine starts. The table is never auto-created.
    if payload.target_db_id:
        db_record = db.query(models.Database).filter(
            models.Database.DBid == payload.target_db_id,
            models.Database.user_id == current_user.id,
        ).first()
        if not db_record:
            raise HTTPException(status_code=404, detail="Selected Database target not found.")
        if db_record.DBType not in dbutil.SUPPORTED_TYPES:
            raise HTTPException(status_code=400, detail=f"{db_record.DBType} is not supported.")

        try:
            columns = dbutil.get_table_columns(db_record.ConnectionString, db_record.DBType, db_record.TableName)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not connect to the database: {str(e).splitlines()[0]}")
        if columns is None:
            raise HTTPException(status_code=400, detail=f"Table/collection '{db_record.TableName}' does not exist. Create it first — the app does not auto-create it.")

        nodes = db.query(models.Node).filter(models.Node.generator_id == generator_id).all()
        node_defs = [(n.node_name, n.data_type_enum) for n in nodes]
        ok, err = dbutil.validate_alignment(node_defs, columns, db_record.DBType)
        if not ok:
            raise HTTPException(status_code=400, detail=err)

        db_config_dict = {
            "id": db_record.DBid,
            "db_type": db_record.DBType,
            "conn": db_record.ConnectionString,
            "table": db_record.TableName,
            "columns": columns,
        }

    success = engine.start_generator(
        generator_id,
        api_config=api_config_dict,
        mqtt_config=mqtt_config_dict,
        db_config=db_config_dict,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Already running")

    modes = []
    if api_config_dict: modes.append("API")
    if mqtt_config_dict: modes.append("MQTT")
    if db_config_dict: modes.append("Database")

    return {
        "status": "started",
        "active_destinations": modes if modes else ["Local Display Only"],
    }


@app.post("/generators/{generator_id}/stop")
async def stop_engine(
    generator_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    owned_generator(generator_id, current_user, db)
    success = engine.stop_generator(generator_id)
    if not success:
        raise HTTPException(status_code=400, detail="Engine is not running")
    return {"message": "Engine stopped"}


@app.get("/generators/{generator_id}/telemetry")
def get_telemetry(
    generator_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    owned_generator(generator_id, current_user, db)
    return engine.latest_telemetry.get(generator_id, {"status": "waiting", "timestamp": 0})


# --- NODE CRUD ENDPOINTS (scoped via parent generator ownership) ---
@app.get("/generators/{generator_id}/nodes/")
def get_nodes(
    generator_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    owned_generator(generator_id, current_user, db)
    return db.query(models.Node).filter(models.Node.generator_id == generator_id).all()


@app.post("/generators/{generator_id}/nodes/")
def create_node(
    generator_id: int,
    node_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    owned_generator(generator_id, current_user, db)
    new_node = models.Node(**node_data, generator_id=generator_id)
    db.add(new_node); db.commit(); db.refresh(new_node)
    return new_node


@app.put("/generators/{generator_id}/nodes/{node_id}")
def update_node(
    generator_id: int,
    node_id: int,
    node_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    owned_generator(generator_id, current_user, db)
    db_node = db.query(models.Node).filter(
        models.Node.id == node_id, models.Node.generator_id == generator_id
    ).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    # id/generator_id are not editable via the payload
    node_data.pop("id", None)
    node_data.pop("generator_id", None)
    for key, value in node_data.items():
        setattr(db_node, key, value)
    db.commit()
    db.refresh(db_node)
    return db_node


@app.delete("/generators/{generator_id}/nodes/{node_id}")
def delete_node(
    generator_id: int,
    node_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    owned_generator(generator_id, current_user, db)
    db_node = db.query(models.Node).filter(
        models.Node.id == node_id, models.Node.generator_id == generator_id
    ).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(db_node)
    db.commit()
    return {"message": "Node deleted"}


# ==========================================
# API DESTINATION ENDPOINTS (scoped to user)
# ==========================================
@app.get("/apis/")
def list_apis(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    return db.query(models.API).filter(models.API.user_id == current_user.id).all()


@app.post("/apis/")
def create_api(
    api_data: schemas.APICreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    new_api = models.API(**api_data.dict())
    new_api.user_id = current_user.id
    db.add(new_api)
    db.commit()
    db.refresh(new_api)
    return new_api


@app.put("/apis/{api_id}")
def update_api(
    api_id: int,
    api_data: schemas.APIUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    db_api = db.query(models.API).filter(
        models.API.APIid == api_id, models.API.user_id == current_user.id
    ).first()
    if not db_api:
        raise HTTPException(status_code=404, detail="API not found")
    for key, value in api_data.dict(exclude_unset=True).items():
        setattr(db_api, key, value)
    db.commit()
    db.refresh(db_api)
    return db_api


@app.delete("/apis/{api_id}")
def delete_api(
    api_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    api = db.query(models.API).filter(
        models.API.APIid == api_id, models.API.user_id == current_user.id
    ).first()
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    db.delete(api)
    db.commit()
    return {"message": "API deleted"}


# ==========================================
# MQTT BROKER ENDPOINTS (scoped to user)
# ==========================================
@app.get("/mqtt/")
def list_mqtt(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    return db.query(models.MQTT).filter(models.MQTT.user_id == current_user.id).all()


@app.post("/mqtt/")
def create_mqtt(
    mqtt_data: schemas.MQTTCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    new_mqtt = models.MQTT(**mqtt_data.dict())
    new_mqtt.user_id = current_user.id
    db.add(new_mqtt)
    db.commit()
    db.refresh(new_mqtt)
    return new_mqtt


@app.put("/mqtt/{mqtt_id}")
def update_mqtt(
    mqtt_id: int,
    mqtt_data: schemas.MQTTUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    db_mqtt = db.query(models.MQTT).filter(
        models.MQTT.MQTTid == mqtt_id, models.MQTT.user_id == current_user.id
    ).first()
    if not db_mqtt:
        raise HTTPException(status_code=404, detail="MQTT config not found")
    for key, value in mqtt_data.dict(exclude_unset=True).items():
        setattr(db_mqtt, key, value)
    db.commit()
    db.refresh(db_mqtt)
    return db_mqtt


@app.delete("/mqtt/{mqtt_id}")
def delete_mqtt(
    mqtt_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    mqtt = db.query(models.MQTT).filter(
        models.MQTT.MQTTid == mqtt_id, models.MQTT.user_id == current_user.id
    ).first()
    if not mqtt:
        raise HTTPException(status_code=404, detail="MQTT config not found")
    db.delete(mqtt)
    db.commit()
    return {"message": "MQTT config deleted"}


# ==========================================
# DATABASE DESTINATION ENDPOINTS (scoped to user) — PostgreSQL sink
# ==========================================
@app.get("/databases/")
def list_databases(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    return db.query(models.Database).filter(models.Database.user_id == current_user.id).all()


@app.post("/databases/")
def create_database(
    data: schemas.DatabaseCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    new_db = models.Database(**data.dict())
    new_db.user_id = current_user.id
    db.add(new_db)
    db.commit()
    db.refresh(new_db)
    return new_db


@app.put("/databases/{db_id}")
def update_database(
    db_id: int,
    data: schemas.DatabaseUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    rec = db.query(models.Database).filter(
        models.Database.DBid == db_id, models.Database.user_id == current_user.id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Database config not found")
    for key, value in data.dict(exclude_unset=True).items():
        setattr(rec, key, value)
    db.commit()
    db.refresh(rec)
    return rec


@app.delete("/databases/{db_id}")
def delete_database(
    db_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    rec = db.query(models.Database).filter(
        models.Database.DBid == db_id, models.Database.user_id == current_user.id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Database config not found")
    db.delete(rec)
    db.commit()
    return {"message": "Database config deleted"}


@app.post("/databases/test")
def test_database(
    data: schemas.DatabaseTest,
    current_user: models.User = Depends(auth.get_current_user),
):
    """Test the connection (and, if a table is given, that it exists + its columns)."""
    ok, message, columns = dbutil.test_connection(data.ConnectionString, data.DBType, data.TableName)
    return {"ok": ok, "message": message, "columns": columns}


@app.get("/databases/{db_id}/schema")
def database_schema(
    db_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    rec = db.query(models.Database).filter(
        models.Database.DBid == db_id, models.Database.user_id == current_user.id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Database config not found")
    if rec.DBType not in dbutil.SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"{rec.DBType} is not supported.")
    try:
        columns = dbutil.get_table_columns(rec.ConnectionString, rec.DBType, rec.TableName)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect: {str(e).splitlines()[0]}")
    if columns is None:
        raise HTTPException(status_code=400, detail=f"Table/collection '{rec.TableName}' does not exist.")
    return {"table": rec.TableName, "columns": columns}


# Map a column (category + size metadata) to a sensible generator node,
# keeping generated values within the column's capacity so inserts succeed.
def _category_to_node(col_name: str, meta: dict) -> dict:
    cat = meta.get("category", "str")
    type_str = str(meta.get("type", "")).lower()
    precision = meta.get("precision")
    scale = meta.get("scale")
    length = meta.get("length")
    node = {"node_name": col_name}

    def int_cap():
        # Respect small integer column widths so values never overflow.
        if "tinyint(1)" in type_str or type_str == "boolean" or type_str == "bit":
            return 1
        if "tinyint" in type_str:
            return 127
        if "smallint" in type_str:
            return 30000
        if precision:  # NUMBER(p) / NUMERIC(p,0)
            return min(1000, 10 ** int(precision) - 1)
        return 1000

    if cat == "bool":
        node.update(data_type_enum="Boolean", generation_mode="Random")
    elif cat == "int":
        node.update(data_type_enum="Integer", generation_mode="Random", min_range=0, max_range=int_cap())
    elif cat == "float":
        # A fixed-scale-0 numeric behaves like an integer; keep it whole to avoid rounding overflow.
        if scale == 0:
            node.update(data_type_enum="Integer", generation_mode="Random", min_range=0, max_range=int_cap())
        else:
            hi = 100
            if precision is not None and scale is not None:
                intdigits = max(1, int(precision) - int(scale))
                hi = min(hi, 10 ** intdigits - 1)
            node.update(data_type_enum="Float", generation_mode="Random", min_range=0, max_range=hi)
    elif cat == "uuid" or "uuid" in type_str:
        node.update(data_type_enum="String", generation_mode="UUID")
    elif cat == "datetime":
        node.update(data_type_enum="String", generation_mode="Timestamp")
    else:
        # Guess a realistic Faker provider from the column name; fall back to random text.
        faker = _guess_faker(col_name)
        if faker:
            node.update(data_type_enum="String", generation_mode="Faker", faker_type=faker)
        else:
            maxlen = min(10, int(length)) if length else 10
            node.update(data_type_enum="String", generation_mode="Random", min_range=1, max_range=maxlen)
    return node


# Heuristic: pick a Faker provider from a column name for realistic auto-generated data.
def _guess_faker(col_name: str):
    n = col_name.lower()
    rules = [
        ("email", "email"),
        ("first_name", "first_name"), ("last_name", "last_name"),
        ("username", "user_name"), ("user_name", "user_name"),
        ("name", "name"),
        ("phone", "phone_number"), ("mobile", "phone_number"),
        ("street", "street_address"), ("address", "street_address"),
        ("city", "city"), ("state", "state"), ("country", "country"),
        ("zip", "postcode"), ("postal", "postcode"), ("postcode", "postcode"),
        ("company", "company"), ("employer", "company"),
        ("job", "job"), ("title", "job"),
        ("ip", "ipv4"), ("mac", "mac_address"),
        ("url", "url"), ("website", "url"), ("domain", "domain_name"),
        ("color", "color_name"), ("currency", "currency_code"),
    ]
    for key, provider in rules:
        if key in n:
            return provider
    return None


@app.post("/databases/{db_id}/generate-generator")
def generate_generator_from_schema(
    db_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """ADVANCED: build a generator + nodes automatically from a table's schema."""
    rec = db.query(models.Database).filter(
        models.Database.DBid == db_id, models.Database.user_id == current_user.id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Database config not found")
    if rec.DBType not in dbutil.SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"{rec.DBType} is not supported.")

    try:
        columns = dbutil.get_table_columns(rec.ConnectionString, rec.DBType, rec.TableName)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect: {str(e).splitlines()[0]}")
    if columns is None:
        raise HTTPException(status_code=400, detail=f"Table/collection '{rec.TableName}' does not exist.")
    if not columns:
        raise HTTPException(status_code=400, detail="Collection is empty — cannot infer a schema. Insert a sample document first, or add nodes manually.")

    # Create the generator, pre-wired to this database destination.
    gen = models.Generator(
        name=f"{rec.TableName} generator",
        description=f"Auto-generated from table '{rec.TableName}'",
        user_id=current_user.id,
        is_database_enabled=True,
        selected_db_id=rec.DBid,
    )
    db.add(gen)
    db.commit()
    db.refresh(gen)

    # One node per column, skipping auto-generated columns (serial / identity / _id).
    created = 0
    for col_name, meta in columns.items():
        if meta["auto"]:
            continue
        node_data = _category_to_node(col_name, meta)
        db.add(models.Node(generator_id=gen.id, **node_data))
        created += 1
    db.commit()

    return {"generator": {"id": gen.id, "name": gen.name}, "nodes_created": created,
            "skipped_auto_columns": [c for c, m in columns.items() if m["auto"]]}


@app.websocket("/ws/generators/{generator_id}")
async def websocket_endpoint(websocket: WebSocket, generator_id: int, token: str = ""):
    # Authenticate the socket via a token query param, and confirm ownership.
    with database.SessionLocal() as db:
        user = auth.get_user_from_raw_token(token, db)
        owns = user and db.query(models.Generator).filter(
            models.Generator.id == generator_id,
            models.Generator.user_id == user.id,
        ).first()
    if not owns:
        await websocket.close(code=1008)  # policy violation
        return

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
