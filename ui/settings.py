import streamlit as st

from database import db


def render():
    st.title("Settings")
    s = db.get_settings()
    with st.form("settings"):
        st.subheader("Department")
        c = st.columns(3)
        mc = c[0].text_input("Number of machines", s["machine_count"], help="Used only for 'NPT % of scheduled time'. Leave empty to hide that KPI.")
        sched = c[1].number_input("Scheduled time per machine per day (h)", 1.0, 24.0, float(s["scheduled_hours"]), 0.5, help="2 shifts x 12 h")
        sa = c[2].text_input("Shift A start hour (0-23)", s["shift_a_start"], help="Example: 8 means A = 08:00-20:00, B = 20:00-08:00. Leave empty to turn shift split off.")
        st.subheader("Data checks")
        longnpt = st.number_input("Warn for one NPT event longer than (h)", 1.0, 240.0, float(s["long_npt_hours"]), 1.0)
        st.subheader("Optional goals (shown as a dashed line on daily charts)")
        c = st.columns(2)
        ng = c[0].text_input("NPT goal (hours per day)", s["npt_goal_h_per_day"])
        rg = c[1].text_input("Rejection goal (pieces per day)", s["rejection_goal_pieces_per_day"])
        st.subheader("Rejection report units")
        c = st.columns(2)
        qf = c[0].number_input("Quantity x this = pieces", 0.0001, 1e6, float(s["rejection_qty_to_pieces"]), help="Report Quantity is in thousand pieces")
        wf = c[1].number_input("Weight x this = kg", 0.0001, 1e6, float(s["rejection_weight_to_kg"]), help="Report Weight is in tons")
        st.caption("Unit changes apply to files uploaded after saving. Stored rejection records keep the values they were saved with.")
        if st.form_submit_button("Save settings", type="primary"):
            bad = [n for n, v in (("Number of machines", mc), ("Shift A start hour", sa), ("NPT goal", ng), ("Rejection goal", rg)) if v.strip() and not _num(v)]
            if bad or (sa.strip() and not 0 <= float(sa) <= 23):
                st.error("Please enter numbers only" + (f" ({', '.join(bad)})" if bad else " (shift hour must be 0-23)") + ".")
            else:
                for k, v in dict(machine_count=mc.strip(), scheduled_hours=sched, shift_a_start=sa.strip(), long_npt_hours=longnpt,
                                 npt_goal_h_per_day=ng.strip(), rejection_goal_pieces_per_day=rg.strip(),
                                 rejection_qty_to_pieces=qf, rejection_weight_to_kg=wf).items():
                    db.set_setting(k, v)
                st.success("Saved.")
    st.caption("Machines are created automatically from the reports (IMM-380-03 and IMM-380-3 are the same machine). "
               "NPT and rejection causes are read from the reports, so new causes appear automatically.")


def _num(v):
    try:
        float(v)
        return True
    except ValueError:
        return False
