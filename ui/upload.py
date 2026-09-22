import datetime as dt

import streamlit as st

from database import db, repository as repo
from processing.cleaner import FileValidationError
from processing.npt_processor import parse_npt
from processing.rejection_processor import parse_rejection
from .common import dataframe

TYPES = [("NPT", "NPT / Downtime Report"), ("Rejection", "Rejection Report")]
LABEL = dict(TYPES)


def _parse(kind, f, day, s):
    return parse_npt(f, f.name, day, s) if kind == "NPT" else parse_rejection(f, f.name, day, s)


def _save_all(pending, choices):
    results = []
    for kind, rep in pending["reports"].items():
        info = pending["dups"][kind]
        choice = choices.get(kind, "Replace Existing Data") if info["existing"] else None
        rd = rep.report_date.isoformat()
        if choice == "Cancel":
            repo.add_history(kind, rep.file_name, rd, rep.rows_read, 0, len(rep.rejected), "Cancelled", "Cancelled by user", 0)
            results.append((kind, "Cancelled - nothing saved."))
            continue
        mode = "new" if not info["existing"] else ("replace" if choice == "Replace Existing Data" else "skip")
        dup_status = {"new": "No duplicate", "replace": "Replaced", "skip": "Skipped duplicates"}[mode]
        uid = repo.add_history(kind, rep.file_name, rd, rep.rows_read, rep.rows_valid, len(rep.rejected),
                               "Success" if not rep.rejected else "Success with rejected rows", dup_status,
                               len(rep.rejected), "; ".join(rep.warnings)[:500])
        n = repo.save_report(rep, uid, mode)
        db.execute("UPDATE upload_history SET records_valid=? WHERE id=?", (n, uid))
        results.append((kind, f"Saved {n} record(s). {dup_status}."))
    return results


def render():
    st.title("Upload Reports")
    s = db.get_settings()
    start = dt.date.fromisoformat(s["data_start_date"])
    if db.DEMO:
        st.warning("PRACTICE MODE: this is a separate demo database. Do not use it for real data.")
    day = st.date_input("Report Date", max(start, dt.date.today() - dt.timedelta(days=1)), min_value=start, format="DD/MM/YYYY",
                        help=f"The database starts on {start:%d-%b-%Y}. Earlier dates are not accepted (change this in Settings).")
    files = {}
    cols = st.columns(2)
    for (kind, label), c in zip(TYPES, cols):
        files[kind] = c.file_uploader(label, type=["xlsx", "xlsm"], key=f"up_{kind}")

    if st.button("PROCESS REPORTS", type="primary"):
        st.session_state.pop("last_results", None)
        if not any(files.values()):
            st.error("Please upload at least one file.")
            return
        if day > dt.date.today():
            st.error("The report date is in the future.")
            return
        reports, errors = {}, {}
        with st.spinner("Reading and checking the files..."):
            for kind, _ in TYPES:
                f = files[kind]
                if f is None:
                    continue
                try:
                    reports[kind] = _parse(kind, f, day, s)
                except FileValidationError as e:
                    errors[kind] = str(e)
                except Exception as e:  # a bad file must never crash the page
                    errors[kind] = f"The file could not be read: {e}"
        for kind, msg in errors.items():
            repo.add_history(kind, files[kind].name, day.isoformat(), 0, 0, 0, "Failed", "-", 1, msg[:500])
        dups = {k: repo.existing_info(r) for k, r in reports.items()}
        st.session_state["pending"] = dict(reports=reports, errors=errors, dups=dups, date=day)
        if reports and not any(d["existing"] for d in dups.values()):
            st.session_state["last_results"] = _save_all(st.session_state["pending"], {})
            st.session_state["pending_view"] = st.session_state.pop("pending")
            st.session_state["pending_done"] = True
        else:
            st.session_state["pending_done"] = False

    pending = st.session_state.get("pending") or st.session_state.get("pending_view")
    if not pending:
        return
    done = st.session_state.get("pending_done", False)
    for kind, msg in pending["errors"].items():
        st.error(f"**{LABEL[kind]}:** {msg}")
    for kind, rep in pending["reports"].items():
        with st.expander(f"{LABEL[kind]} - {rep.rows_valid} valid row(s), {len(rep.rejected)} rejected row(s)", expanded=True):
            st.write(f"Report date: {rep.report_date:%d-%b-%Y} | rows read: {rep.rows_read} | valid: {rep.rows_valid} | rejected: {len(rep.rejected)}")
            if rep.rejected:
                st.write("Rows not saved:")
                dataframe([{"Where": w, "Reason": r} for w, r in rep.rejected])
            for w in rep.warnings:
                st.warning(w)
            if rep.flags:
                st.write(f"{len(rep.flags)} data warning(s):")
                dataframe([{"Type": f["kind"], "Details": f["message"]} for f in rep.flags[:200]])
            info = pending["dups"][kind]
            if info["existing"] and not done:
                st.warning(f"Data for this report/date already exists. {info['detail']}")

    if not done:
        need = {k: d for k, d in pending["dups"].items() if d["existing"]}
        choices = {}
        for kind in need:
            choices[kind] = st.radio(f"{LABEL[kind]} - what should be done?",
                                     ["Replace Existing Data", "Skip Duplicate Records", "Cancel"], key=f"choice_{kind}", horizontal=True)
        ok = True
        if any(c == "Replace Existing Data" for c in choices.values()):
            ok = st.checkbox("I confirm: existing records for this date will be replaced. Upload history is kept.", key="confirm_replace")
        if pending["reports"] and st.button("Save to database", type="primary", disabled=not ok):
            st.session_state["last_results"] = _save_all(pending, choices)
            st.session_state["pending_view"] = st.session_state.pop("pending")
            st.session_state["pending_done"] = True
            st.rerun()
    for kind, msg in st.session_state.get("last_results", []):
        st.success(f"{LABEL[kind]}: {msg}")
    if done and st.session_state.get("last_results"):
        st.info("Dashboards are updated. Open **Dashboard** or **Daily Analysis**.")
