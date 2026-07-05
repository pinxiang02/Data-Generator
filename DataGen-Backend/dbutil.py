"""
PostgreSQL sink helpers: connection-string normalization, connection testing,
table introspection, and schema-alignment validation between a generator's
nodes and a target table.

Only PostgreSQL is implemented today; the DBType argument is threaded through so
Oracle / MongoDB can be added later without changing call sites.
"""
from sqlalchemy import create_engine, text

# Cache engines by normalized connection string (avoid reconnecting every tick).
_engines = {}

SUPPORTED_TYPES = {"PostgreSQL"}

# What Postgres column types each generator data type may be written into.
# (Insertion uses explicit CAST, so string->uuid/timestamp etc. also work.)
COMPAT = {
    "Integer": {"integer", "bigint", "smallint", "numeric", "decimal",
                "real", "double precision", "character varying", "text", "character", "char"},
    "Float":   {"numeric", "decimal", "real", "double precision",
                "character varying", "text", "character", "char"},
    "Boolean": {"boolean", "character varying", "text"},
    "String":  {"character varying", "text", "character", "char", "uuid",
                "timestamp without time zone", "timestamp with time zone",
                "date", "time without time zone", "json", "jsonb"},
}


def normalize_conn(conn_str: str) -> str:
    """Force the pg8000 driver (the only Postgres driver installed)."""
    s = (conn_str or "").strip()
    if s.startswith("postgresql+"):
        return s
    if s.startswith("postgresql://"):
        return "postgresql+pg8000://" + s[len("postgresql://"):]
    if s.startswith("postgres://"):
        return "postgresql+pg8000://" + s[len("postgres://"):]
    return s


def get_engine(conn_str: str):
    norm = normalize_conn(conn_str)
    eng = _engines.get(norm)
    if eng is None:
        eng = create_engine(norm, pool_pre_ping=True)
        _engines[norm] = eng
    return eng


def test_connection(conn_str: str, db_type: str = "PostgreSQL", table: str = None):
    """Return (ok: bool, message: str, columns: dict|None)."""
    if db_type not in SUPPORTED_TYPES:
        return False, f"{db_type} is not supported yet. Only PostgreSQL is available.", None
    try:
        eng = create_engine(normalize_conn(conn_str), pool_pre_ping=True)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        eng.dispose()
    except Exception as e:
        return False, f"Connection failed: {e}", None

    if table:
        cols = get_table_columns(conn_str, table)
        if cols is None:
            return False, f"Connected, but table '{table}' was not found. Create it first.", None
        return True, f"Connection OK. Table '{table}' has {len(cols)} columns.", cols
    return True, "Connection successful.", None


def get_table_columns(conn_str: str, table: str):
    """Return {col: {type, nullable, auto}} for the table, or None if it doesn't exist."""
    eng = get_engine(conn_str)
    with eng.connect() as c:
        rows = c.execute(text(
            """
            SELECT column_name, data_type, is_nullable, column_default, is_identity
            FROM information_schema.columns
            WHERE table_name = :t
            ORDER BY ordinal_position
            """
        ), {"t": table}).fetchall()
    if not rows:
        return None
    cols = {}
    for name, dtype, nullable, default, identity in rows:
        auto = (identity == "YES") or (default is not None and "nextval" in str(default))
        cols[name] = {"type": dtype, "nullable": nullable == "YES", "auto": auto}
    return cols


def validate_alignment(node_defs, columns):
    """
    node_defs: list of (node_name, data_type_enum).
    columns: dict from get_table_columns.
    Returns (ok, error_message). Requirement: every node must map to a column
    of a compatible type; the app never creates or alters the table.
    """
    if not node_defs:
        return False, "This generator has no nodes to insert."

    col_names = set(columns.keys())
    missing = [n for (n, _) in node_defs if n not in col_names]
    if missing:
        return False, (
            f"These node(s) have no matching column in the table: {', '.join(missing)}. "
            f"Table columns are: {', '.join(sorted(col_names))}."
        )

    type_errors = []
    for name, dtype in node_defs:
        pg_type = columns[name]["type"]
        allowed = COMPAT.get(dtype, set())
        if pg_type not in allowed:
            type_errors.append(f"'{name}' ({dtype}) -> column type '{pg_type}'")
    if type_errors:
        return False, "Type mismatch between generator and table: " + "; ".join(type_errors)

    # Non-nullable columns not produced by any node (and not auto-generated) would
    # break inserts — warn about that as a misalignment too.
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
