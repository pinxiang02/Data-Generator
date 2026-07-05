"""
Database sink helpers for multiple engines.

Relational engines (PostgreSQL, MySQL, Oracle) go through SQLAlchemy — the
Inspector gives dialect-agnostic column introspection, and column types are
normalized to a small set of categories via each type's Python type. MongoDB is
document-based, so it uses pymongo directly: the "table" is a collection and
alignment is checked against a sampled document.

The application never creates or alters tables/collections.
"""
import datetime as _dt
import decimal as _decimal
import uuid as _uuid

from sqlalchemy import create_engine, inspect, MetaData, Table

SUPPORTED_TYPES = {"PostgreSQL", "MySQL", "Oracle", "MongoDB"}
SQL_TYPES = {"PostgreSQL", "MySQL", "Oracle"}

# What column categories each generator data type may be written into.
COMPAT = {
    "Integer": {"int", "float", "str"},
    "Float":   {"float", "int", "str"},
    "Boolean": {"bool", "int", "str"},
    "String":  {"str", "datetime", "uuid", "other"},
}

_engines = {}   # normalized SQLAlchemy URL -> Engine
_tables = {}    # (url, table) -> reflected Table
_mongo_clients = {}


# ---------------------------------------------------------------- connection strings
def normalize_conn(db_type: str, conn_str: str) -> str:
    """Force the installed driver for each SQL dialect."""
    s = (conn_str or "").strip()
    if db_type == "PostgreSQL":
        if s.startswith("postgresql+"):
            return s
        if s.startswith("postgresql://"):
            return "postgresql+pg8000://" + s[len("postgresql://"):]
        if s.startswith("postgres://"):
            return "postgresql+pg8000://" + s[len("postgres://"):]
    elif db_type == "MySQL":
        if s.startswith("mysql+"):
            return s
        if s.startswith("mysql://"):
            return "mysql+pymysql://" + s[len("mysql://"):]
    elif db_type == "Oracle":
        if s.startswith("oracle+"):
            return s
        if s.startswith("oracle://"):
            return "oracle+oracledb://" + s[len("oracle://"):]
    return s


def get_engine(db_type: str, conn_str: str):
    url = normalize_conn(db_type, conn_str)
    eng = _engines.get(url)
    if eng is None:
        eng = create_engine(url, pool_pre_ping=True)
        _engines[url] = eng
    return eng


def _effective_table(db_type: str, table: str) -> str:
    # SQLAlchemy's Oracle dialect already maps a lowercase name to Oracle's
    # upper-case object and returns lowercase column names, so pass names
    # through unchanged for every dialect and let SQLAlchemy normalize.
    return table


def _category_from_type(sa_type) -> str:
    try:
        pt = sa_type.python_type
    except (NotImplementedError, Exception):
        return "other"
    if pt is bool:
        return "bool"
    if pt is int:
        return "int"
    if pt in (float, _decimal.Decimal):
        return "float"
    if pt in (_dt.datetime, _dt.date, _dt.time):
        return "datetime"
    if pt is _uuid.UUID:
        return "uuid"
    if pt is str:
        return "str"
    return "other"


# ---------------------------------------------------------------- MongoDB helpers
def _mongo_client(conn_str: str):
    cl = _mongo_clients.get(conn_str)
    if cl is None:
        import pymongo
        cl = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=3000)
        _mongo_clients[conn_str] = cl
    return cl


def _mongo_db(conn_str: str):
    cl = _mongo_client(conn_str)
    db = cl.get_default_database()
    if db is None:
        raise ValueError("MongoDB connection string must include a database name, e.g. mongodb://host:27017/mydb")
    return db


def _py_category(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, (float, _decimal.Decimal)):
        return "float"
    if isinstance(value, (_dt.datetime, _dt.date)):
        return "datetime"
    return "str"


def _mongo_columns(conn_str: str, collection: str):
    """Sample one document to infer fields. Returns {} for an empty collection,
    or None if the collection does not exist."""
    db = _mongo_db(conn_str)
    if collection not in db.list_collection_names():
        return None
    doc = db[collection].find_one()
    cols = {}
    if doc:
        for k, v in doc.items():
            cols[k] = {"type": type(v).__name__, "category": _py_category(v),
                       "nullable": True, "auto": (k == "_id")}
    return cols


# ---------------------------------------------------------------- public API
def get_table_columns(conn_str: str, db_type: str, table: str):
    """Return {col: {type, category, nullable, auto}} or None if table/collection missing."""
    if db_type == "MongoDB":
        return _mongo_columns(conn_str, table)

    engine = get_engine(db_type, conn_str)
    eff = _effective_table(db_type, table)
    insp = inspect(engine)
    try:
        raw = insp.get_columns(eff)
    except Exception:
        raw = []
    if not raw:
        return None
    cols = {}
    for c in raw:
        # A column is "auto" (safe to omit from inserts) if it auto-increments,
        # is an IDENTITY column, or has a server default.
        auto = (
            bool(c.get("autoincrement", False))
            or bool(c.get("identity"))
            or c.get("default") is not None
        )
        sa = c["type"]
        cols[c["name"]] = {
            "type": str(sa),
            "category": _category_from_type(sa),
            "nullable": bool(c.get("nullable", True)),
            "auto": auto,
            "length": getattr(sa, "length", None),        # varchar length
            "precision": getattr(sa, "precision", None),   # numeric precision
            "scale": getattr(sa, "scale", None),           # numeric scale
        }
    return cols


def test_connection(conn_str: str, db_type: str = "PostgreSQL", table: str = None):
    """Return (ok, message, columns|None)."""
    if db_type not in SUPPORTED_TYPES:
        return False, f"{db_type} is not supported.", None

    if db_type == "MongoDB":
        try:
            db = _mongo_db(conn_str)
            db.client.admin.command("ping")
        except Exception as e:
            return False, f"Connection failed: {e}", None
        if table:
            cols = _mongo_columns(conn_str, table)
            if cols is None:
                return False, f"Connected, but collection '{table}' was not found. Create it first.", None
            note = f"{len(cols)} fields sampled" if cols else "collection is empty"
            return True, f"Connection OK. Collection '{table}' exists ({note}).", cols
        return True, "Connection successful.", None

    # SQL engines
    try:
        from sqlalchemy import text
        eng = get_engine(db_type, conn_str)
        probe = "SELECT 1 FROM DUAL" if db_type == "Oracle" else "SELECT 1"
        with eng.connect() as c:
            c.execute(text(probe))
    except Exception as e:
        return False, f"Connection failed: {str(e).splitlines()[0]}", None

    if table:
        cols = get_table_columns(conn_str, db_type, table)
        if cols is None:
            return False, f"Connected, but table '{table}' was not found. Create it first.", None
        return True, f"Connection OK. Table '{table}' has {len(cols)} columns.", cols
    return True, "Connection successful.", None


def validate_alignment(node_defs, columns, db_type="PostgreSQL"):
    """node_defs: [(name, data_type_enum)]. Returns (ok, error_message|None)."""
    if not node_defs:
        return False, "This generator has no nodes to insert."

    # MongoDB is schemaless: only require the collection exists (columns is not None).
    # If it already has documents, node names must match existing fields.
    if db_type == "MongoDB":
        if columns:  # non-empty collection -> enforce field alignment
            existing = set(columns.keys()) - {"_id"}
            missing = [n for (n, _) in node_defs if n not in existing]
            if missing:
                return False, (
                    f"These node(s) are not fields in existing documents: {', '.join(missing)}. "
                    f"Document fields are: {', '.join(sorted(existing))}."
                )
        return True, None

    col_names = set(columns.keys())
    missing = [n for (n, _) in node_defs if n not in col_names]
    if missing:
        return False, (
            f"These node(s) have no matching column in the table: {', '.join(missing)}. "
            f"Table columns are: {', '.join(sorted(col_names))}."
        )

    type_errors = []
    for name, dtype in node_defs:
        cat = columns[name]["category"]
        if cat not in COMPAT.get(dtype, set()):
            type_errors.append(f"'{name}' ({dtype}) -> column type '{columns[name]['type']}'")
    if type_errors:
        return False, "Type mismatch between generator and table: " + "; ".join(type_errors)

    produced = {n for (n, _) in node_defs}
    unfilled_required = [
        c for c, meta in columns.items()
        if not meta["nullable"] and not meta["auto"] and c not in produced
    ]
    if unfilled_required:
        return False, (
            "The table has NOT NULL column(s) that no node fills: "
            f"{', '.join(unfilled_required)}. Add matching nodes or make the columns nullable."
        )
    return True, None


# ---------------------------------------------------------------- inserts
def _parse_dt(v):
    if isinstance(v, str):
        try:
            return _dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return v
    return v


def insert_row(db_type: str, conn_str: str, table: str, columns: dict, payload: dict) -> str:
    """Insert one row/document. Returns a one-line status string."""
    if db_type == "MongoDB":
        db = _mongo_db(conn_str)
        doc = dict(payload)  # store the full generated document
        db[table].insert_one(doc)
        return f"[Inserted] 1 document -> {table}"

    # SQL engines: reflect the table (cached) and insert only real columns.
    engine = get_engine(db_type, conn_str)
    eff = _effective_table(db_type, table)
    key = (str(engine.url), eff)
    tbl = _tables.get(key)
    if tbl is None:
        tbl = Table(eff, MetaData(), autoload_with=engine)
        _tables[key] = tbl

    row = {}
    for k, v in payload.items():
        if k not in columns:
            continue
        if columns[k]["category"] == "datetime":
            v = _parse_dt(v)
        row[k] = v
    if not row:
        return "[Error] Insert: no generated fields match the columns"

    with engine.begin() as c:
        c.execute(tbl.insert().values(**row))
    return f"[Inserted] 1 row -> {table}"
