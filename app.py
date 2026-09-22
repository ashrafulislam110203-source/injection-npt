"""Production KPI Management System - Injection Moulding, Version 1 (NPT + Rejection).  Run:  streamlit run app.py"""
import os

import streamlit as st

from database import db
from ui import (daily, dashboard, data_quality, export, history, machine_analysis, monthly, npt_analysis,
                rejection_analysis, settings, upload, upload_history, yearly)

st.set_page_config(page_title="Production KPI - Injection Moulding", layout="wide")
db.init_db()


def _password():
    if os.environ.get("KPI_APP_PASSWORD"):
        return os.environ["KPI_APP_PASSWORD"]
    try:
        return st.secrets.get("KPI_APP_PASSWORD")
    except Exception:          # no secrets file = no password
        return None


pwd = _password()
if pwd and not st.session_state.get("auth"):
    st.title("Production KPI")
    entered = st.text_input("Password", type="password")
    if st.button("Log in"):
        if entered == pwd:
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

PAGES = {"Dashboard": dashboard.render, "Upload Reports": upload.render, "Daily Analysis": daily.render,
         "Monthly Analysis": monthly.render, "Yearly Analysis": yearly.render, "Machine Analysis": machine_analysis.render,
         "NPT Analysis": npt_analysis.render, "Rejection Analysis": rejection_analysis.render,
         "Data History": history.render, "Upload History": upload_history.render, "Data Quality": data_quality.render,
         "Excel Export & Backup": export.render, "Settings": settings.render}
st.sidebar.title("Production KPI")
st.sidebar.caption("Injection Moulding")
page = st.sidebar.radio("Go to", list(PAGES), label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption("Version 1 - NPT and Rejection")
PAGES[page]()
