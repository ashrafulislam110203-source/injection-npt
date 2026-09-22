"""Saving parsed reports into the database (replace / skip / new) and upload history."""
import datetime as dt
from contextlib import closing

import pandas as pd

from processing.cleaner import machine_size
from . import db

NPT_COLS = ["machine_id", "machine_raw", "start_time", "end_time", "duration_sec", "cause_raw", "cause",
            "added_by", "added_time"]
REJ_COLS = ["report_date", "machine_id", "machine_raw", "item_name", "item_code", "wip_name", "qty_raw",
            "weight_raw", "qty_pieces", "weight_kg", "cause_raw", "cause", "added_by", "added_time"]


def _clean(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v.item() if hasattr(v, "item") else v


def _records(df, cols, upload_id):
    return [tuple(_clean(r[c]) for c in cols) + (upload_id,) for r in df.to_dict("records")]


def existing_info(rep):
    """How much of this report is already in the database? -> dict(existing, total, detail)"""
    db.init_db()
    df = rep.df
    if df.empty:
        return dict(existing=0, total=0, detail="")
    if rep.report_type == "NPT":
        lo = (pd.to_datetime(df.start_time).min() - pd.Timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        hi = (pd.to_datetime(df.start_time).max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        q = db.query_df("SELECT machine_id, start_time, end_time FROM npt_events WHERE start_time BETWEEN ? AND ?", (lo, hi))
        have = set(zip(q.machine_id, q.start_time, q.end_time))
        n = sum((a, b, c) in have for a, b, c in zip(df.machine_id, df.start_time, df.end_time))
        return dict(existing=n, total=len(df), detail=f"{n} of {len(df)} events are already stored")
    q = db.query_df("SELECT COUNT(*) n FROM rejection WHERE report_date=?", (rep.report_date.isoformat(),))
    n = int(q.n.iloc[0])
    return dict(existing=n, total=len(df), detail=f"{n} records already stored for {rep.report_date:%d-%b-%Y}")


def add_history(rep_type, file_name, report_date, total, valid, rejected, status, dup_status, errors, message=""):
    db.init_db()
    return db.execute(
        "INSERT INTO upload_history(upload_time, report_date, report_type, file_name, records_total, records_valid,"
        " records_rejected, status, duplicate_status, error_count, message) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), report_date, rep_type, file_name, total, valid,
         rejected, status, dup_status, errors, message))


def save_report(rep, upload_id, mode="new"):
    """mode: 'new' (nothing exists), 'replace', 'skip'. Returns number of rows written."""
    db.init_db()
    df = rep.df
    written = 0
    with closing(db.connect()) as conn:
        cur = conn.cursor()
        if rep.report_type == "NPT":
            if mode == "replace":
                cur.execute("DELETE FROM npt_events WHERE substr(start_time,1,10)=?", (rep.report_date.isoformat(),))
            verb = "INSERT OR REPLACE" if mode == "replace" else "INSERT OR IGNORE"
            before = conn.total_changes
            cur.executemany(f"{verb} INTO npt_events ({','.join(NPT_COLS)}, upload_id) VALUES ({','.join('?'*(len(NPT_COLS)+1))})",
                            _records(df, NPT_COLS, upload_id))
            written = conn.total_changes - before
        else:
            if mode == "skip":
                use = df.iloc[0:0]
            else:
                if mode == "replace":
                    cur.execute("DELETE FROM rejection WHERE report_date=?", (rep.report_date.isoformat(),))
                use = df
            cur.executemany(f"INSERT INTO rejection ({','.join(REJ_COLS)}, upload_id) VALUES ({','.join('?'*(len(REJ_COLS)+1))})",
                            _records(use, REJ_COLS, upload_id))
            written = len(use)
        for m in df.machine_id.dropna().unique():
            cur.execute("INSERT OR IGNORE INTO machines(machine_id, size, first_seen) VALUES (?,?,?)",
                        (m, machine_size(m), dt.date.today().isoformat()))
        for f in rep.flags:
            cur.execute("INSERT INTO data_warnings(upload_id, warn_date, machine_id, kind, message) VALUES (?,?,?,?,?)",
                        (upload_id, f.get("warn_date"), f.get("machine_id"), f.get("kind"), f.get("message")))
        for loc, why in rep.rejected:
            cur.execute("INSERT INTO data_warnings(upload_id, warn_date, machine_id, kind, message) VALUES (?,?,?,?,?)",
                        (upload_id, rep.report_date.isoformat() if rep.report_date else None, None, "Row rejected", f"{loc}: {why}"))
        conn.commit()
    return written


def backup_db(tag="backup"):
    """Copy of the database file in a 'backups' folder next to it. Existing backups are never overwritten."""
    import os
    import sqlite3
    folder = os.path.join(os.path.dirname(db.DB_PATH), "backups")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"kpi_{tag}_{dt.datetime.now():%Y%m%d_%H%M%S}.db")
    with closing(db.connect()) as src, closing(sqlite3.connect(path)) as dst:
        src.backup(dst)
    return path


def delete_day(kind, day):
    """Remove one report type for one date (NPT: events that START on that date). Upload history is kept."""
    db.init_db()
    with closing(db.connect()) as conn:
        if kind == "NPT":
            cur = conn.execute("DELETE FROM npt_events WHERE substr(start_time,1,10)=?", (day.isoformat(),))
        else:
            cur = conn.execute("DELETE FROM rejection WHERE report_date=?", (day.isoformat(),))
        n = cur.rowcount
        conn.commit()
    add_history(kind, "(deleted by user)", day.isoformat(), n, 0, 0, "Deleted", "-", 0, f"{n} record(s) removed")
    return n


def reset_all():
    """Delete ALL NPT / Rejection data and history of warnings. A backup is made first. Returns backup path."""
    path = backup_db("before_reset")
    with closing(db.connect()) as conn:
        for t in ("npt_events", "rejection", "data_warnings", "machines"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
    add_history("-", "(database reset by user)", None, 0, 0, 0, "Reset", "-", 0, "backup: " + path)
    return path
