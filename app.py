"""Production KPI Management System - Injection Moulding, Version 1 (NPT + Rejection).  Run:  streamlit run app.py"""
import os

import streamlit as st

from database import db
from ui import (daily, dashboard, data_quality, export, history, machine_analysis, monthly, npt_analysis,
                rejection_analysis, settings, upload, upload_history, yearly)
from ui.common import inject_css, sidebar_profile

st.set_page_config(page_title="Production KPI - Injection Moulding", layout="wide", page_icon="📊")
db.init_db()
inject_css()


def _password():
    if os.environ.get("KPI_APP_PASSWORD"):
        return os.environ["KPI_APP_PASSWORD"]
    try:
        return st.secrets.get("KPI_APP_PASSWORD")
    except Exception:          # no secrets file = no password
        return None


pwd = _password()
if pwd and not st.session_state.get("auth"):
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center;margin-bottom:0'>📊 Production KPI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#6B7280;margin-top:0'>Injection Moulding &middot; NPT and Rejection Analysis</p>", unsafe_allow_html=True)
        with st.form("login"):
            entered = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
            ok = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if ok:
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
sidebar_profile("Ashraful Islam", "Trainee Engineer - DPL Production, PRAN-RFL Group",
               os.path.join(os.path.dirname(__file__), "assets", "profile.jpg"))
st.sidebar.title("Production KPI")
st.sidebar.caption("Injection Moulding")
page = st.sidebar.radio("Go to", list(PAGES), label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption("Version 1 - NPT and Rejection")
if db.DEMO:
    st.sidebar.error("PRACTICE MODE (demo database)")
PAGES[page]()
