import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st

from database import db
from utils.excel_export import build_workbook, notes_for

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def dataframe(df, **kw):
    """st.dataframe at full width; works on old and new Streamlit versions."""
    kw = {k: v for k, v in kw.items() if v is not None}
    try:
        st.dataframe(df, hide_index=True, width="stretch", **kw)
    except Exception:
        st.dataframe(df, hide_index=True, use_container_width=True, **kw)


def plot(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)


def num(x, d=0):
    return "-" if x is None or x != x else f"{x:,.{d}f}"


def pct(x, d=1):
    return "-" if x is None or x != x else f"{x*100:.{d}f}%"


def show_table(df, pct_cols=(), dec_cols=(), int_cols=()):
    """Show a DataFrame; fractions in pct_cols are displayed as percentages."""
    d = df.copy()
    cfg = {}
    for c in pct_cols:
        if c in d:
            d[c] = d[c] * 100
            cfg[c] = st.column_config.NumberColumn(c, format="%.1f%%")
    for c in dec_cols:
        if c in d:
            cfg[c] = st.column_config.NumberColumn(c, format="%.2f")
    for c in int_cols:
        if c in d:
            cfg[c] = st.column_config.NumberColumn(c, format="%d")
    dataframe(d, column_config=cfg)


def excel_button(label, data_fn, filename, key=None):
    """data_fn is called only when the page is drawn; keeps files up to date with the database."""
    st.download_button(label, data=data_fn(), file_name=filename, mime=XLSX, key=key)


def table_button(label, sheets, filename, key=None):
    excel_button(label, lambda: build_workbook(sheets, None, notes_for(db.get_settings())), filename, key)


def npt_cards(ns, settings=None):
    c = st.columns(6)
    c[0].metric("Total NPT (hours)", num(ns["npt_h"], 1))
    c[1].metric("NPT events", num(ns["events"]))
    c[2].metric("Machines with NPT", num(ns["machines"]))
    c[3].metric("Average per event (min)", num(ns["avg_min"], 0))
    c[4].metric("Longest event (min)", num(ns["max_min"], 0))
    c[5].metric("NPT % of scheduled time", pct(ns["npt_pct"]),
                help="NPT hours / (machines x scheduled hours x days). Set 'Number of machines' in Settings to see it.")
    if ns.get("top_cause"):
        st.caption(f"Top NPT cause by hours: **{ns['top_cause']}**")


def rej_cards(rs):
    c = st.columns(5)
    c[0].metric("Rejected pieces", num(rs["pieces"]))
    c[1].metric("Rejected weight (kg)", num(rs["kg"], 1))
    c[2].metric("Rejection entries", num(rs["entries"]))
    c[3].metric("Machines with rejection", num(rs["machines"]))
    c[4].metric("Products rejected", num(rs["items"]))
    if rs.get("top_cause"):
        st.caption(f"Top rejection cause by pieces: **{rs['top_cause']}**")


def date_range_input(label="Date range", key="rng", default_days=30):
    lo, hi = db.date_bounds()
    if lo is None:
        return None, None
    start = max(lo, hi - dt.timedelta(days=default_days - 1))
    v = st.date_input(label, (start, hi), min_value=lo, max_value=hi, key=key, format="DD/MM/YYYY")
    if isinstance(v, (tuple, list)):
        return (v[0], v[1]) if len(v) == 2 else (v[0], v[0])
    return v, v


def machine_options():
    return list(db.query_df("SELECT machine_id FROM machines ORDER BY machine_id").machine_id)


def machine_filter(key="mf", label="Machine"):
    return st.multiselect(label, machine_options(), key=key) or None


def distinct(table, col):
    df = db.query_df(f"SELECT DISTINCT {col} AS v FROM {table} WHERE {col} IS NOT NULL ORDER BY 1")
    return list(df.v)


def no_data():
    st.info("No data yet. Open **Upload Reports** and upload the NPT and Rejection files.")
