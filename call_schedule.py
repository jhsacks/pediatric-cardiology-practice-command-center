import calendar
from copy import deepcopy
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from vacation_manager import away_details, away_doctors, ensure_vacation_data, observance_text, render_vacation_planner, vacation_summary

DEFAULT_DOCTORS = ["Jeffrey Sacks", "Luv Makadia", "Yoni Yaari"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKEND_DAYS = {"Friday", "Saturday", "Sunday"}
SCOPES = ["One date", "All matching weekdays", "Remaining matching weekdays"]


def nth_weekday(year, month, weekday, n):
    return [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, day).weekday() == weekday][n - 1]


def last_weekday(year, month, weekday):
    return [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, day).weekday() == weekday][-1]


def holiday_dates(year):
    return {date(year, 1, 1): "New Year's Day", nth_weekday(year, 1, calendar.MONDAY, 3): "MLK Day", last_weekday(year, 5, calendar.MONDAY): "Memorial Day", date(year, 7, 4): "Fourth of July", nth_weekday(year, 9, calendar.MONDAY, 1): "Labor Day", nth_weekday(year, 11, calendar.THURSDAY, 4): "Thanksgiving", date(year, 12, 24): "Christmas Eve", date(year, 12, 25): "Christmas Day", date(year, 12, 31): "New Year's Eve"}


def default_templates():
    return [
        {"Call": "Sacks AM / Yaari PM", "Full Day": "", "Morning": "Jeffrey Sacks", "Evening": "Yoni Yaari"},
        {"Call": "Yaari AM / Sacks PM", "Full Day": "", "Morning": "Yoni Yaari", "Evening": "Jeffrey Sacks"},
        {"Call": "Sacks AM / Makadia PM", "Full Day": "", "Morning": "Jeffrey Sacks", "Evening": "Luv Makadia"},
        {"Call": "Makadia AM / Yaari PM", "Full Day": "", "Morning": "Luv Makadia", "Evening": "Yoni Yaari"},
        {"Call": "Yaari AM / Makadia PM", "Full Day": "", "Morning": "Yoni Yaari", "Evening": "Luv Makadia"},
        {"Call": "Full Day Sacks", "Full Day": "Jeffrey Sacks", "Morning": "", "Evening": ""},
        {"Call": "Full Day Makadia", "Full Day": "Luv Makadia", "Morning": "", "Evening": ""},
        {"Call": "Full Day Yaari", "Full Day": "Yoni Yaari", "Morning": "", "Evening": ""},
    ]


def empty_year(year):
    start = date(year, 1, 1); holidays = holiday_dates(year); rows = []
    for offset in range((date(year + 1, 1, 1) - start).days):
        current = start + timedelta(days=offset)
        rows.append({"Date": current.isoformat(), "Day": current.strftime("%A"), "Holiday": holidays.get(current, ""), "Call": "Unassigned", "Notes": ""})
    return rows


def default_store():
    return {"doctors": [{"Doctor": doctor, "Vacation Allocation": 0.0, "Active": True} for doctor in DEFAULT_DOCTORS], "years": {"2027": empty_year(2027)}, "owed_calls": [], "call_templates": default_templates(), "holiday_history": [{"Year": 2026, "Holiday": "Christmas Day", "Doctor": "Jeffrey Sacks", "Credit": 1.0}, {"Year": 2026, "Holiday": "New Year's Day", "Doctor": "Yoni Yaari", "Credit": 1.0}, {"Year": 2026, "Holiday": "Thanksgiving", "Doctor": "Luv Makadia", "Credit": 1.0}]}


def template_from_legacy(row):
    if row.get("Call") and row.get("Call") != "Unassigned": return row["Call"]
    if row.get("Pattern") and row.get("Pattern") != "Custom": return row["Pattern"]
    if row.get("Call Type") == "Split":
        morning = row.get("Morning", ""); evening = row.get("Evening", "")
        for template in default_templates():
            if template["Morning"] == morning and template["Evening"] == evening: return template["Call"]
    full = row.get("Full Day", "")
    for template in default_templates():
        if full and template["Full Day"] == full: return template["Call"]
    return "Unassigned"


def ensure_store(extra):
    store = extra.setdefault("call_schedule", default_store())
    defaults = default_store()
    for key, value in defaults.items(): store.setdefault(key, deepcopy(value))
    if "templates" in store and "call_templates" not in store:
        store["call_templates"] = [{"Call": row.get("Template", ""), "Full Day": row.get("Full Day", ""), "Morning": row.get("Morning", ""), "Evening": row.get("Evening", "")} for row in store["templates"]]
    for year_key, rows in store.get("years", {}).items():
        for row in rows:
            row["Call"] = template_from_legacy(row)
            for duplicate in ["Pattern", "Call Type", "Full Day", "Morning", "Evening", "Vacation Doctors", "Vacation Details", "Observances", "Call Credits", "Schedule Issues"]: row.pop(duplicate, None)
    ensure_vacation_data(store)
    return store


def doctor_names(store): return [str(row.get("Doctor", "")).strip() for row in store["doctors"] if row.get("Active", True) and str(row.get("Doctor", "")).strip()]

def call_options(store): return ["Unassigned"] + [str(row.get("Call", "")).strip() for row in store.get("call_templates", []) if str(row.get("Call", "")).strip()]

def template_map(store): return {str(row.get("Call", "")): row for row in store.get("call_templates", [])}


def call_parts(store, call_name):
    template = template_map(store).get(str(call_name), {})
    if template.get("Full Day"): return [(template["Full Day"], 1.0)]
    return [(doctor, 0.5) for doctor in [template.get("Morning"), template.get("Evening")] if doctor]


def display_frame(store, year):
    base = deepcopy(store.get("years", {}).get(str(year), empty_year(year))); rows = []
    for row in base:
        current = date.fromisoformat(str(row["Date"])); calls = call_parts(store, row.get("Call")); away = away_doctors(store, current); conflicts = sorted({doctor for doctor, _ in calls if doctor in away}); issues = []
        if not calls: issues.append("Unassigned call")
        if conflicts: issues.append("Call/vacation: " + ", ".join(conflicts))
        if row.get("Holiday") and not calls: issues.append("Unassigned holiday")
        rows.append({"Date": current, "Day": row.get("Day", current.strftime("%A")), "Holiday": row.get("Holiday", ""), "Observances": observance_text(store, current), "Call": row.get("Call", "Unassigned"), "Vacation": "; ".join(away_details(store, current)), "Notes": row.get("Notes", ""), "Call Credits": ", ".join(f"{doctor}: {credit:g}" for doctor, credit in calls), "Schedule Issues": "; ".join(issues)})
    return pd.DataFrame(rows)


def call_summary(frame, store, doctors):
    totals = {doctor: {"Weekday": 0.0, "Weekend": 0.0, "Holiday": 0.0, "Total": 0.0} for doctor in doctors}
    for _, row in frame.iterrows():
        bucket = "Weekend" if row["Day"] in WEEKEND_DAYS else "Weekday"
        for doctor, credit in call_parts(store, row["Call"]):
            totals.setdefault(doctor, {"Weekday": 0.0, "Weekend": 0.0, "Holiday": 0.0, "Total": 0.0}); totals[doctor][bucket] += credit; totals[doctor]["Total"] += credit
            if row["Holiday"]: totals[doctor]["Holiday"] += credit
    return pd.DataFrame([{"Doctor": doctor, **values} for doctor, values in totals.items()])


def dashboard(frame, store, doctors):
    summary = call_summary(frame, store, doctors); columns = st.columns(5)
    columns[0].metric("Unassigned dates", frame["Call"].eq("Unassigned").sum()); columns[1].metric("Conflicts", frame["Schedule Issues"].str.contains("Call/vacation", regex=False).sum()); columns[2].metric("Weekday credits", f"{summary['Weekday'].sum():g}"); columns[3].metric("Weekend credits", f"{summary['Weekend'].sum():g}"); columns[4].metric("Holiday credits", f"{summary['Holiday'].sum():g}")


def render_readonly(store):
    years = sorted(int(year) for year in store["years"] if str(year).isdigit()); year = st.selectbox("Calendar year", years, index=len(years) - 1, key="practice_schedule_year"); doctors = doctor_names(store); frame = display_frame(store, year); dashboard(frame, store, doctors); tabs = st.tabs(["Calendar", "Schedule Issues", "Call Equity", "Vacation", "Owed Call", "Holidays"])
    with tabs[0]: st.dataframe(frame[["Date", "Day", "Holiday", "Observances", "Call", "Vacation", "Notes"]], hide_index=True, use_container_width=True)
    with tabs[1]:
        issues = frame[frame["Schedule Issues"].str.len() > 0]; st.dataframe(issues[["Date", "Schedule Issues", "Notes"]], hide_index=True, use_container_width=True) if not issues.empty else st.success("No schedule issues.")
    with tabs[2]: st.dataframe(call_summary(frame, store, doctors), hide_index=True, use_container_width=True)
    with tabs[3]: st.dataframe(vacation_summary(store), hide_index=True, use_container_width=True)
    with tabs[4]:
        owed = pd.DataFrame(store.get("owed_calls", [])); st.dataframe(owed, hide_index=True, use_container_width=True) if not owed.empty else st.info("No owed calls recorded.")
    with tabs[5]:
        holidays = frame[frame["Holiday"].str.len() > 0][["Date", "Holiday", "Call"]]; st.dataframe(holidays, hide_index=True, use_container_width=True); st.dataframe(pd.DataFrame(store.get("holiday_history", [])), hide_index=True, use_container_width=True)


def render_editor(extra, save_extra, log_activity=None):
    store = ensure_store(extra); st.header("Call & Vacation Scheduler"); years = sorted(int(year) for year in store["years"] if str(year).isdigit()); top = st.columns(3); year = top[0].selectbox("Calendar year", years, index=len(years)-1, key="editor_schedule_year"); new_year = top[1].number_input("Add year", 2027, 2100, max(years)+1, 1)
    if top[2].button("Add Calendar Year"): store["years"].setdefault(str(int(new_year)), empty_year(int(new_year))); ensure_vacation_data(store); save_extra(extra); st.rerun()
    doctors = doctor_names(store); frame = display_frame(store, year); dashboard(frame, store, doctors); tabs = st.tabs(["Schedule", "Quick Assign", "Vacation Planner", "Doctors", "Owed Call", "Equity", "Holidays", "Schedule Issues"])
    with tabs[0]:
        visible = frame[["Date", "Day", "Holiday", "Observances", "Call", "Vacation", "Notes"]]
        edited = st.data_editor(visible, hide_index=True, use_container_width=True, key=f"canonical_schedule_{year}", disabled=["Date", "Day", "Holiday", "Observances", "Vacation"], column_config={"Date": st.column_config.DateColumn("Date"), "Call": st.column_config.SelectboxColumn("Call", options=call_options(store))})
        if st.button("Save Annual Schedule", type="primary"):
            by_date = {str(row["Date"]): row for row in store["years"][str(year)]}
            for row in edited.to_dict("records"):
                key = str(row["Date"]); target = by_date[key]; target["Call"] = row.get("Call", "Unassigned"); target["Notes"] = row.get("Notes", "")
            save_extra(extra)
            if log_activity: log_activity(f"Updated {year} call schedule")
            st.rerun()
    with tabs[1]:
        templates = pd.DataFrame(store["call_templates"]); selected = st.selectbox("Call", call_options(store)[1:]); a, b, c = st.columns(3); start = a.date_input("Starting date", date(year, 1, 2), min_value=date(year, 1, 1), max_value=date(year, 12, 31)); weekday = b.selectbox("Day of week", WEEKDAYS, index=5); scope = c.selectbox("Apply to", SCOPES, index=1)
        if st.button("Apply Call", type="primary"):
            for row in store["years"][str(year)]:
                current = date.fromisoformat(row["Date"]); match = current == start if scope == "One date" else row["Day"] == weekday if scope == "All matching weekdays" else row["Day"] == weekday and current >= start
                if match: row["Call"] = selected
            save_extra(extra); st.rerun()
        st.subheader("Manage Calls"); changed = st.data_editor(templates, hide_index=True, use_container_width=True, num_rows="dynamic", key="canonical_calls")
        if st.button("Save Calls"):
            store["call_templates"] = changed.where(pd.notna(changed), "").to_dict("records"); valid = set(call_options(store))
            for rows in store["years"].values():
                for row in rows:
                    if row.get("Call") not in valid: row["Call"] = "Unassigned"
            save_extra(extra); st.rerun()
    with tabs[2]: render_vacation_planner(store, year, doctors, lambda: save_extra(extra))
    with tabs[3]:
        roster = pd.DataFrame(store["doctors"]); changed = st.data_editor(roster, hide_index=True, use_container_width=True, num_rows="dynamic", key="canonical_doctors")
        if st.button("Save Doctors"): store["doctors"] = changed.where(pd.notna(changed), "").to_dict("records"); save_extra(extra); st.rerun()
    with tabs[4]:
        owed = pd.DataFrame(store.get("owed_calls", [])) if store.get("owed_calls") else pd.DataFrame(columns=["Debtor", "Creditor", "Type", "Quantity", "Notes"]); changed = st.data_editor(owed, hide_index=True, use_container_width=True, num_rows="dynamic", key="canonical_owed", column_config={"Debtor": st.column_config.SelectboxColumn("Debtor", options=doctors), "Creditor": st.column_config.SelectboxColumn("Creditor", options=doctors), "Type": st.column_config.SelectboxColumn("Type", options=["Weekday", "Weekend"]), "Quantity": st.column_config.NumberColumn("Quantity", min_value=0.5, step=0.5)})
        if st.button("Save Owed Calls"): store["owed_calls"] = changed.where(pd.notna(changed), "").to_dict("records"); save_extra(extra); st.rerun()
    with tabs[5]: st.dataframe(call_summary(frame, store, doctors), hide_index=True, use_container_width=True)
    with tabs[6]:
        st.dataframe(frame[frame["Holiday"].str.len() > 0][["Date", "Holiday", "Call"]], hide_index=True, use_container_width=True); history = pd.DataFrame(store["holiday_history"]); changed = st.data_editor(history, hide_index=True, use_container_width=True, num_rows="dynamic", key="canonical_holiday_history")
        if st.button("Save Holiday History"): store["holiday_history"] = changed.where(pd.notna(changed), "").to_dict("records"); save_extra(extra); st.rerun()
    with tabs[7]:
        issues = frame[frame["Schedule Issues"].str.len() > 0]; st.dataframe(issues[["Date", "Day", "Holiday", "Schedule Issues", "Notes"]], hide_index=True, use_container_width=True) if not issues.empty else st.success("No schedule issues.")
