# Data Generator — Testing Procedure

End-to-end test that the generator produces data and delivers it to both an
HTTP API destination and an MQTT broker, using the two test clients.

## Components & ports

| Service              | Location                          | Port  |
|----------------------|-----------------------------------|-------|
| Postgres (DB)        | Docker container `postgresql`     | 5436  |
| Mosquitto (broker)   | Docker container `mqtt_broker`    | 1884  |
| Backend API          | `DataGen-Backend`                 | 8000  |
| Frontend (UI)        | `DataGen-Frontend`                | 5173  |
| **API test client**  | `DataGen-APIClient/test_api_client.py`  | 9000 |
| **MQTT test client** | `DataGen-MQTT/test_mqtt_client.py`      | (subscriber) |

> Port note: locally, **1883 is NATS** — the Mosquitto broker is on **1884**.
> Always configure the generator's MQTT destination with port **1884**.

Open a **separate terminal** for each long-running service below.
All commands are run from the project root:
`C:\Users\SA-SI-PINXIANG\OneDrive\ドキュメント\Data Generator`

---

## Step 1 — Start infrastructure (Postgres + Mosquitto)

```powershell
docker compose -f Docker\docker-compose.yml up -d            # Postgres :5436
docker compose -f Docker\docker-compose-mqtt.yml up -d mosquitto   # Mosquitto :1884
```

Verify both are up:

```powershell
docker ps --format "{{.Names}} {{.Ports}}"
# expect: postgresql ...:5436->5432  and  mqtt_broker ...:1884->1883
```

## Step 2 — Start the backend

```powershell
cd DataGen-Backend
.\datagen\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Confirm (in another terminal): open http://127.0.0.1:8000 →
`{"status":"Backend is running with pg8000"}`

## Step 3 — Start the API test client

```powershell
cd DataGen-APIClient
.\API\Scripts\python.exe test_api_client.py
```

Expected banner:
```
 DataGen API Test Client
 Listening on : http://127.0.0.1:9000
 Point generator API destination at: /ingest  (POST)
```

## Step 4 — Start the MQTT test client

```powershell
cd DataGen-MQTT
..\Manual-Publisher\publisher\Scripts\python.exe test_mqtt_client.py
```

Expected banner:
```
 DataGen MQTT Test Client
 Broker : 127.0.0.1:1884   Topic: #
Connected to broker 127.0.0.1:1884
Subscribed to '#'. Waiting for messages...
```

## Step 5 — Start the frontend (for configuration)

```powershell
cd DataGen-Frontend
npm install    # first time only
npm run dev
```

Open http://localhost:5173

---

## Step 6 — Configure a generator (via the UI)

1. **Generators** → *Add Generator* (e.g. name `Test Gen`). Click **Configure**.
2. **Add Nodes** (a few, to shape the JSON payload). Examples:
   - `Temperature` — Float, Random, min `20`, max `30`
   - `BatchCode`  — String, Random, max `6`  (random 6-char string)
   - `Status`     — String, List, values `OK, WARN, FAIL`
3. **API Config** page → *Add API Target*:
   - Name: `Test Receiver`
   - Target URL: `http://127.0.0.1:9000/ingest`
   - Method: `POST`
4. **MQTT Config** page → *Add MQTT Config*:
   - Name: `Local Mosquitto`
   - Host: `127.0.0.1`  ·  Port: `1884`  ·  Topic: `factory/nodes/demo`
5. Back on the generator's **Configure** page:
   - Tick **Enable API Destination** → select `Test Receiver`
   - Tick **Enable Message Broker** → select `Local Mosquitto`

## Step 7 — Run the generator

On the generator's Configure page click **▶ Start Engine**
(or click **Start** on the Generators list — it uses the saved destinations).

Watch the on-page consoles:
- **Live Payload Output** — the generated JSON each tick
- **API Response Logs** — `[API] [200] Success ...` and `[MQTT] [Published] Success ...`

---

## Step 8 — Verify the results

**API test client terminal** — one block per tick:
```
[09:35:11]  #157  POST /ingest
{
  "BatchCode": "ZRAmBt",
  "Status": "OK",
  "Temperature": 24.1168,
  "@timestamp": "2026-07-04T01:35:11.719780+00:00"
}
```

**MQTT test client terminal** — one line per tick:
```
[09:34:46]  #3  topic: factory/nodes/demo
{"BatchCode": "KYDbOz", "Status": "FAIL", "Temperature": 28.6465, "@timestamp": "..."}
```

**PASS criteria**
- [ ] API client counter increases every ~1s, each request returns `200`
- [ ] MQTT client counter increases every ~1s
- [ ] Payload keys match the nodes you configured
- [ ] Backend telemetry shows both successes:
  ```powershell
  curl.exe http://127.0.0.1:8000/generators/1/telemetry
  # api_log:  "[200] Success -> http://127.0.0.1:9000/ingest"
  # mqtt_log: "[Published] Success -> 127.0.0.1:1884 | Topic: factory/nodes/demo"
  ```

## Step 9 — Stop & tear down

1. Click **■ Stop** in the UI (or `curl.exe -X POST http://127.0.0.1:8000/generators/1/stop`).
2. `Ctrl+C` in the backend, API-client, MQTT-client, and frontend terminals.
3. Optional — stop containers:
   ```powershell
   docker compose -f Docker\docker-compose-mqtt.yml down
   docker compose -f Docker\docker-compose.yml down
   ```

---

## Quick API-only path (no UI)

Everything in Step 6–8 can be driven with the API directly:

```powershell
# create API + MQTT destinations
curl.exe -X POST http://127.0.0.1:8000/apis/  -H "Content-Type: application/json" -d '{\"APIName\":\"Test Receiver\",\"TargetUrl\":\"http://127.0.0.1:9000/ingest\",\"Method\":\"POST\"}'
curl.exe -X POST http://127.0.0.1:8000/mqtt/  -H "Content-Type: application/json" -d '{\"MQTTName\":\"Local Mosquitto\",\"Host\":\"127.0.0.1\",\"Port\":1884,\"Topic\":\"factory/nodes/demo\"}'

# add a node
curl.exe -X POST http://127.0.0.1:8000/generators/1/nodes/ -H "Content-Type: application/json" -d '{\"node_name\":\"Temperature\",\"data_type_enum\":\"Float\",\"generation_mode\":\"Random\",\"min_range\":20,\"max_range\":30}'

# start with explicit targets (use the ids returned above)
curl.exe -X POST http://127.0.0.1:8000/generators/1/start -H "Content-Type: application/json" -d '{\"target_api_id\":1,\"target_mqtt_id\":1}'
```

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| MQTT client never receives, `mqtt_log` shows timeout | Broker not on 1884, or config points at 1883 (NATS). Start Mosquitto; set port 1884. |
| API `mqtt_log: [Error] ... Connection refused` | Mosquitto container not running. |
| API client shows `422` | You're hitting the old `receiver.py` (fixed schema). Use `test_api_client.py`, which accepts any payload. |
| `active_destinations: ["Local Display Only"]` | No destination enabled/selected — payloads generate but aren't sent. |
| Backend won't start, DB error | Postgres container not up on 5436. |
