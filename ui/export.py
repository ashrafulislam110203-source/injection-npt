import datetime as dt
import os

import streamlit as st

from database import db
from utils import excel_export as ex
from .common import excel_button, no_data


def render():
    st.title("Excel Export & Backup")
    lo, hi = db.date_bounds()
    if lo is None:
        no_data()
        return
    st.subheader("Daily report")
    day = st.date_input("Date", hi, min_value=lo, max_value=hi, key="ex_day", format="DD/MM/YYYY")
    excel_button("Export Daily Report to Excel", lambda: ex.report_workbook(day, day, level="daily"), f"Daily_KPI_{day:%Y-%m-%d}.xlsx", "e1")
    st.subheader("Date range report")
    c = st.columns(2)
    a = c[0].date_input("From", max(lo, hi - dt.timedelta(days=29)), min_value=lo, max_value=hi, key="ex_a", format="DD/MM/YYYY")
    b = c[1].date_input("To", hi, min_value=lo, max_value=hi, key="ex_b", format="DD/MM/YYYY")
    if a <= b:
        excel_button("Export date range to Excel", lambda: ex.report_workbook(a, b, level="range"), f"KPI_{a:%Y-%m-%d}_to_{b:%Y-%m-%d}.xlsx", "e2")
    st.caption("Monthly, yearly, machine, NPT and Rejection workbooks have their own Export button on their pages, using the filters you chose.")
    st.subheader("All historical data")
    excel_button("Export All Historical Data", lambda: ex.history_workbook(), "All_Historical_Data.xlsx", "e3")
    st.subheader("Database backup")
    st.caption("Download a copy of the database. Backups are never deleted or overwritten by the app.")
    if os.path.exists(db.DB_PATH):
        with open(db.DB_PATH, "rb") as f:
            st.download_button("Download database backup", f.read(), file_name=f"kpi_backup_{dt.date.today():%Y-%m-%d}.db", mime="application/octet-stream")
