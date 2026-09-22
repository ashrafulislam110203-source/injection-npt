"""SQLite database layer.

Only plain SQL types are used (TEXT, INTEGER, REAL) so the same schema can be moved
to PostgreSQL / Supabase later. The database path can be changed with the
KPI_DB_PATH environment variable (use a persistent disk when you deploy).
"""
import os
import sqlite3
from contextlib import closing

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.environ.get("KPI_DEMO") == "1"      # practice mode: separate database, never mixed with real data
DB_PATH = os.environ.get("KPI_DB_PATH", os.path.join(BASE_DIR, "data", "demo.db" if DEMO else "kpi.db"))

# Editable in the Settings page. Empty string = not set.
DEFAULT_SETTINGS = {
    "data_start_date": "2026-09-01",      # first day of the real database; earlier report dates are refused
    "scheduled_hours": "24",              # 2 shifts x 12 hours
    "shift_a_start": "8",                 # shift A = 08:00-20:00, shift B = 20:00-08:00 (empty = shift split off)
    "machine_count": "",                  # number of machines in the department (for NPT % of scheduled time)
    "long_npt_hours": "24",               # warn for a single NPT event longer than this
    "npt_goal_h_per_day": "",             # optional goal line on charts
    "rejection_goal_pieces_per_day": "",  # optional goal line on charts
    "rejection_qty_to_pieces": "1000",    # Rejection report: Quantity is in thousand pieces
    "rejection_weight_to_kg": "1000",     # Rejection report: Weight is in tons
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT PRIMARY KEY,
    size TEXT,
    first_seen TEXT
);

CREATE TABLE IF NOT EXISTS upload_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_time TEXT,
    report_date TEXT,
    report_type TEXT,
    file_name TEXT,
    records_total INTEGER,
    records_valid INTEGER,
    records_rejected INTEGER,
    status TEXT,
    duplicate_status TEXT,
    error_count INTEGER,
    message TEXT
);

CREATE TABLE IF NOT EXISTS npt_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL,
    machine_raw TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_sec REAL,
    cause_raw TEXT,
    cause TEXT,
    added_by TEXT,
    added_time TEXT,
    upload_id INTEGER,
    UNIQUE (machine_id, start_time, end_time)
);
CREATE INDEX IF NOT EXISTS ix_npt_start ON npt_events(start_time);

CREATE TABLE IF NOT EXISTS rejection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    machine_raw TEXT,
    item_name TEXT,
    item_code TEXT,
    wip_name TEXT,
    qty_raw REAL,                      -- as in the report (thousand pieces)
    weight_raw REAL,                   -- as in the report (tons)
    qty_pieces REAL,
    weight_kg REAL,
    cause_raw TEXT,
    cause TEXT,
    added_by TEXT,
    added_time TEXT,
    upload_id INTEGER
);
CREATE INDEX IF NOT EXISTS ix_rej_date ON rejection(report_date, machine_id);

CREATE TABLE IF NOT EXISTS data_warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER,
    warn_date TEXT,
    machine_id TEXT,
    kind TEXT,
    message TEXT
);
"""


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(connect()) as conn:
        conn.executescript(SCHEMA)
        for k, v in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))
        conn.commit()


def execute(sql, params=()):
    with closing(connect()) as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def query_df(sql, params=()):
    with closing(connect()) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_settings():
    init_db()
    df = query_df("SELECT key, value FROM settings")
    s = dict(DEFAULT_SETTINGS)
    s.update(dict(zip(df["key"], df["value"])))
    return s


def set_setting(key, value):
    execute("INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def date_bounds():
    """Earliest / latest date that has any data."""
    init_db()
    df = query_df("""
        SELECT MIN(d) AS lo, MAX(d) AS hi FROM (
            SELECT substr(start_time,1,10) AS d FROM npt_events
            UNION ALL SELECT report_date FROM rejection)""")
    lo, hi = df.iloc[0]["lo"], df.iloc[0]["hi"]
    if lo is None:
        return None, None
    return pd.to_datetime(lo).date(), pd.to_datetime(hi).date()
