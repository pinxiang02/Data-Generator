# DataGen — Synthetic Telemetry Data Generator

DataGen is a full-stack web application for generating **synthetic / test data** and
streaming it to real destinations. You define a **generator**, give it a set of
**nodes** (the fields in each JSON payload) and generation rules, then start the
engine — it produces a payload on a fixed interval and delivers it to any
combination of an **HTTP API**, an **MQTT broker**, and a **SQL/NoSQL database**.

It's built for engineers who need realistic, continuous test data to exercise
ingestion pipelines, dashboards, alerting rules, message brokers, and database
tables — without wiring up a bespoke script every time.

---

## Features

- **Multi-user accounts** — sign up / log in (JWT). Every generator and
  destination config is private to its owner.
- **Flexible generators** — each field ("node") has a data type and a
  generation mode:
  - `Fixed`, `Random` (range), `List` (pick from values)
  - `Sequential` (counter), `Sine` (smooth wave), `Timestamp`, `UUID`
  - `Faker` — realistic names, emails, IPs, addresses, companies, etc.
- **Three destination types** (use any combination at once):
  - **HTTP API** — POST/PUT the payload to a URL with an optional header
  - **MQTT** — publish the payload to a broker topic
  - **Database** — insert into a table/collection of **PostgreSQL, MySQL,
    Oracle, or MongoDB**
- **Schema-aware database sink** — the app never creates tables; it validates
  that your generator's nodes align with the target table's columns (names +
  types) and prompts a clear error otherwise. It can also **auto-generate a
  matching generator from an existing table's schema**.
- **Live overview dashboard** — per-generator running status, message counts,
  throughput (msg/s) and sparklines.
- **Live console** — real-time payload + destination logs over WebSocket while
  a generator runs.
- **Configurable interval**, light/dark theme, and standalone **test clients**
  for the API and MQTT destinations.

---

## Architecture

```
Browser ──HTTP/WS──► Backend (FastAPI) ──► Generation engine (async loop)
                          │                      │
                          │                      ├─► HTTP API   (httpx)
                     App metadata                ├─► MQTT       (paho)
                     (PostgreSQL)                └─► Database   (SQLAlchemy / pymongo)
                                                        └─► PostgreSQL · MySQL · Oracle · MongoDB
```

| Layer | Stack |
|-------|-------|
| Frontend | Vue 3 + Vite + Vue Router (served by nginx in Docker) |
| Backend | FastAPI + SQLAlchemy + JWT auth |
| App database | PostgreSQL (stores users, generators, nodes, destination configs) |
| Destinations | HTTP, MQTT (Mosquitto), PostgreSQL / MySQL / Oracle / MongoDB |

---

## File structure

```
Data Generator/
├── README.md                     # This file
├── TESTING.md                    # Step-by-step end-to-end test procedure
│
├── Docker/
│   ├── docker-compose.yml        # Full stack: app + all databases + MQTT
│   └── mosquitto/config/         # Mosquitto broker config
│
├── DataGen-Backend/              # FastAPI backend
│   ├── Dockerfile
│   ├── main.py                   # API routes (auth, generators, nodes, destinations, WS)
│   ├── auth.py                   # JWT + password hashing + current-user dependency
│   ├── models.py                 # SQLAlchemy ORM models
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── database.py               # DB engine/session (DATABASE_URL configurable)
│   ├── engine.py                 # Async generation loop + value generators (incl. Faker)
│   ├── transmitter.py            # Send to API / MQTT / database
│   ├── dbutil.py                 # Multi-dialect DB introspection, validation, insert
│   ├── ws_manager.py             # WebSocket connection manager
│   └── requirements.txt
│
├── DataGen-Frontend/             # Vue 3 + Vite frontend
│   ├── Dockerfile                # Multi-stage build → nginx
│   ├── nginx.conf                # SPA history-mode fallback
│   ├── src/
│   │   ├── App.vue               # Shell: nav, auth state, theme toggle
│   │   ├── router/index.js       # Routes + auth guard
│   │   ├── services/api.js       # Axios client + token interceptor
│   │   ├── views/
│   │   │   ├── LoginView.vue / SignupView.vue
│   │   │   ├── DashboardView.vue        # Live overview
│   │   │   ├── GeneratorsView.vue       # Generator list
│   │   │   ├── GeneratorNodesView.vue   # Configure nodes + destinations + live console
│   │   │   ├── ApiConfigView.vue
│   │   │   ├── MqttConfigView.vue
│   │   │   └── DatabaseConfigView.vue   # DB destinations + connection test + auto-generate
│   │   └── assets/ , style.css , apple-theme.css
│   └── package.json
│
├── DataGen-APIClient/            # Test HTTP receiver (accepts any JSON) — :9000
│   └── test_api_client.py
├── DataGen-MQTT/                 # Test MQTT subscriber
│   └── test_mqtt_client.py
└── Manual-Publisher/             # One-off manual MQTT publisher
    └── manual_pub.py
```

---

## Setup

### Option A — Docker (recommended, runs everything)

Requires **Docker Desktop**. From the `Docker/` directory:

```bash
cd Docker
docker compose up -d --build
```

This starts the whole stack:

| Service | URL / Port |
|---------|-----------|
| **Frontend (UI)** | http://localhost:8081 |
| **Backend (API)** | http://localhost:8001 |
| PostgreSQL (app DB) | localhost:5436 |
| Mosquitto (MQTT) | localhost:1884 |
| Oracle Free | localhost:1523 (service `FREEPDB1`) |
| MySQL | localhost:3307 |
| MongoDB | localhost:27018 |

Open **http://localhost:8081** and create an account.

> The extra databases (Oracle/MySQL/MongoDB) are provided so you can test the
> database sink. Default credentials are `datagen` / `datagen`.

### Option B — Run locally for development

**Backend** (Python 3.11+):
```bash
cd DataGen-Backend
python -m venv datagen
datagen\Scripts\activate            # Windows  (source datagen/bin/activate on macOS/Linux)
pip install -r requirements.txt
# Needs a PostgreSQL reachable at the default URL, or set DATABASE_URL:
#   set DATABASE_URL=postgresql+pg8000://user:pass@host:5432/dbname
uvicorn main:app --host 127.0.0.1 --port 8000
```

**Frontend** (Node 18+):
```bash
cd DataGen-Frontend
npm install
npm run dev            # http://localhost:5173  (calls the backend at :8000)
```

You still need PostgreSQL (and, for the sink, any target DB) running — the
`Docker/docker-compose.yml` file can provide just those.

---

## How to use

1. **Sign up / log in** at the UI. Everything you create is private to your account.

2. **(Optional) Configure destinations** — go to **API Config**, **MQTT Config**,
   or **Database Config** and add a target:
   - *API*: a URL + method (+ optional header)
   - *MQTT*: host, port, topic
   - *Database*: type (PostgreSQL/MySQL/Oracle/MongoDB), connection string,
     target table/collection. Use **Test Connection** to verify it and preview
     the table's columns.

3. **Create a generator** — go to **Generators → Add Generator**, then **Configure**.

4. **Add nodes** — each node is one field in the payload. Pick a data type and a
   generation mode (Random, Sequential, Sine, Timestamp, UUID, Faker, …).

5. **Pick destinations & interval** — on the Configure page, enable API / MQTT /
   Database, choose the target(s), and set the generation interval (ms).

6. **Start the engine** — click **Start**. Watch the **live console** stream each
   payload and the destination responses. The **Dashboard** shows running status,
   message counts, and throughput across all your generators.

### Database sink — key rules

- The app **never creates or alters tables** — create your table/collection first.
- Your node names and types must **align** with the table's columns, or you get a
  clear validation error when starting.
- **Auto-generate:** on the Database Config page, **Generate** builds a fully-wired
  generator from an existing table's schema (mapping columns to sensible modes,
  e.g. an `email` column → Faker email, and skipping auto-increment/identity keys).

> When the backend runs in Docker, database-sink connection strings should use the
> compose **service names** (e.g. `mysql://datagen:datagen@mysql:3306/datagen`,
> `oracle://datagen:datagen@oracle:1521/?service_name=FREEPDB1`,
> `mongodb://datagen:datagen@mongodb:27017/datagen?authSource=admin`) instead of
> `localhost`. See **TESTING.md** for a full worked example.

### Verifying delivery

- **API**: run `python DataGen-APIClient/test_api_client.py` (listens on :9000,
  accepts any JSON) and point a generator's API destination at
  `http://127.0.0.1:9000/ingest`.
- **MQTT**: run `python DataGen-MQTT/test_mqtt_client.py` to print everything
  published to the broker.
- **Database**: query the target table/collection with your usual client.

See **[TESTING.md](TESTING.md)** for a complete, copy-paste end-to-end walkthrough.
