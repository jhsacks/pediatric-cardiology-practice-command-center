import calendar
from copy import deepcopy
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from vacation_manager import away_details, away_doctors, ensure_data, observance_text, vacation_controls, vacation_summary

DEFAULT_DOCTORS = ["Jeffrey Sacks", "Luv Makadia", "Yoni Yaari"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKEND_DAYS = {"Friday", "Saturday", "Sunday"}
SCOPES = ["One date", "All matching weekdays", "Remaining matching weekdays"]


def _nth(year, month, weekday, n):
    return [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, day).weekday() == weekday][n - 1]


def _last(year, month, weekday):
    return [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, day).weekday() == weekday][-1]


def holidays(year):
    return {date(year, 1, 1): "New Year's Day", _nth(year, 1, calendar.MONDAY, 3): "MLK Day", _last(year, 5, calendar.MONDAY): "Memorial Day", date(year, 7, 4): "Fourth of July", _nth(year, 9, calendar.MONDAY, 1): "Labor Day", _nth(year, 11, calendar.THURSDAY, 4): "Thanksgiving", date(year, 12, 24): "Christmas Eve", date(year, 12, 25): "Christmas Day", date(year, 12, 31): "New Year's Eve"}


def default_calls():
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
    start = date(year, 1, 1); special = holidays(year); rows = []
    for offset in range((date(year + 1, 1, 1) - start).days):
        current = start + timedelta(days=offset)
        rows.append({"Date": current.isoformat(), "Day": current.strftime("%A"), "Holiday": special.get(current, ""), "Call": "Unassigned", "Notes": ""})
    return rows


def defaults():
    return {"doctors": [{"Doctor": name, "Vacation Allocation": 0.0, "Active": True} for name in DEFAULT_DOCTORS], "years": {"2027": empty_year(2027)}, "call_templates": default_calls(), "owed_calls": [], "holiday_history": [{"Year": 2026, "Holiday": "Christmas Day", "Doctor": "Jeffrey Sacks", "Credit": 1.0}, {"Year": 2026, "Holiday": "New Year's Day", "Doctor": "Yoni Yaari", "Credit": 1.0}, {"Year": 2026, "Holiday": "Thanksgiving", "Doctor": "Luv Makadia", "Credit": 1.0}]}


def legacy_call(row):
    if row.get("Call") and row.get("Call") != "Unassigned": return row["Call"]
    if row.get("Pattern") and row.get("Pattern") != "Custom": return row["Pattern"]
    for item in default_calls():
        if row.get("Full Day") and row.get("Full Day") == item["Full Day"]: return item["Call"]
        if row.get("Call Type") == "Split" and row.get("Morning") == item["Morning"] and row.get("Evening") == item["Evening"]: return item["Call"]
    return "Unassigned"


def ensure_store(extra):
    store = extra.setdefault("call_schedule", defaults())
    for key, value in defaults().items(): store.setdefault(key, deepcopy(value))
    if "templates" in store and "call_templates" not in store:
        store["call_templates"] = [{"Call": row.get("Template", ""), "Full Day": row.get("Full Day", ""), "Morning": row.get("Morning", ""), "Evening": row.get("Evening", "")} for row in store["templates"]]
    for rows in store.get("years", {}).values():
        for row in rows:
            row["Call"] = legacy_call(row)
            for key in ["Pattern", "Call Type", "Full Day", "Morning", "Evening", "Vacation Doctors", "Vacation Details", "Observances", "Call Credits", "Schedule Issues"]: row.pop(key, None)
    ensure_data(store)
    return store


def roster(store): return [str(row.get("Doctor", "")).strip() for row in store["doctors"] if row.get("Active", True) and str(row.get("Doctor", "")).strip()]

def call_choices(store):
    values = ["Unassigned"]
    for row in store.get("call_templates", []):
        value = str(row.get("Call", "")).strip()
        if value and value != "Unassigned" and value not in values:
            values.append(value)
    return values

def assignments(store, call):
    item = next((row for row in store["call_templates"] if row.get("Call") == call), {})
    if item.get("Full Day"): return [(item["Full Day"], 1.0)]
    return [(name, 0.5) for name in [item.get("Morning"), item.get("Evening")] if name]


def frame(store, year):
    output = []
    for row in deepcopy(store["years"].get(str(year), empty_year(year))):
        current = date.fromisoformat(str(row["Date"])); calls = assignments(store, row.get("Call")); away = away_doctors(store, current); issues = []
        if not calls: issues.append("Unassigned call")
        conflicts = sorted({name for name, _ in calls if name in away})
        if conflicts: issues.append("Call/vacation: " + ", ".join(conflicts))
        if row.get("Holiday") and not calls: issues.append("Unassigned holiday")
        output.append({"Date": current, "Day": row.get("Day", current.strftime("%A")), "Holiday": row.get("Holiday", ""), "Observances": observance_text(store, current), "Call": row.get("Call", "Unassigned"), "Vacation": "; ".join(away_details(store, current)), "Notes": row.get("Notes", ""), "Issues": "; ".join(issues)})
    return pd.DataFrame(output)


def equity(data, store, doctors):
    totals = {name: {"Weekday": 0.0, "Weekend": 0.0, "Holiday": 0.0, "Total": 0.0} for name in doctors}
    for _, row in data.iterrows():
        bucket = "Weekend" if row["Day"] in WEEKEND_DAYS else "Weekday"
        for name, credit in assignments(store, row["Call"]):
            totals.setdefault(name, {"Weekday": 0.0, "Weekend": 0.0, "Holiday": 0.0, "Total": 0.0}); totals[name][bucket] += credit; totals[name]["Total"] += credit
            if row["Holiday"]: totals[name]["Holiday"] += credit
    return pd.DataFrame([{"Doctor": name, **values} for name, values in totals.items()])


def metrics(data, store, doctors):
    summary = equity(data, store, doctors); columns = st.columns(5)
    columns[0].metric("Unassigned dates", data["Call"].eq("Unassigned").sum()); columns[1].metric("Conflicts", data["Issues"].str.contains("Call/vacation", regex=False).sum()); columns[2].metric("Weekday credits", f"{summary['Weekday'].sum():g}"); columns[3].metric("Weekend credits", f"{summary['Weekend'].sum():g}"); columns[4].metric("Holiday credits", f"{summary['Holiday'].sum():g}")


def render_readonly(store):
    years = sorted(int(year) for year in store["years"]); year = st.selectbox("Calendar year", years, index=len(years)-1, key="practice_schedule_year"); doctors = roster(store); data = frame(store, year); metrics(data, store, doctors); tabs = st.tabs(["Calendar", "Schedule Issues", "Call Equity", "Vacation", "Owed Call", "Holidays"])
    with tabs[0]: st.dataframe(data[["Date", "Day", "Holiday", "Observances", "Call", "Vacation", "Notes"]], hide_index=True, use_container_width=True)
    with tabs[1]:
        problem = data[data["Issues"].str.len() > 0]
        if problem.empty: st.success("No schedule issues.")
        else: st.dataframe(problem[["Date", "Issues", "Notes"]], hide_index=True, use_container_width=True)
    with tabs[2]: st.dataframe(equity(data, store, doctors), hide_index=True, use_container_width=True)
    with tabs[3]: st.dataframe(vacation_summary(store), hide_index=True, use_container_width=True)
    with tabs[4]:
        owed = pd.DataFrame(store.get("owed_calls", []))
        if owed.empty: st.info("No owed calls recorded.")
        else: st.dataframe(owed, hide_index=True, use_container_width=True)
    with tabs[5]: st.dataframe(data[data["Holiday"].str.len() > 0][["Date", "Holiday", "Call"]], hide_index=True, use_container_width=True)


def render_editor(extra, save_extra, log_activity=None):
    store = ensure_store(extra); st.header("Call & Vacation Scheduler"); years = sorted(int(year) for year in store["years"]); top = st.columns(3); year = top[0].selectbox("Calendar year", years, index=len(years)-1, key="editor_schedule_year"); new_year = top[1].number_input("Add year", 2027, 2100, max(years)+1, 1)
    if top[2].button("Add Calendar Year"): store["years"].setdefault(str(int(new_year)), empty_year(int(new_year))); ensure_data(store); save_extra(extra); st.rerun()
    doctors = roster(store); data = frame(store, year); metrics(data, store, doctors); tabs = st.tabs(["Schedule", "Quick Assign", "Doctors", "Owed Call", "Equity", "Holidays", "Schedule Issues"])
    with tabs[0]:
        vacation_controls(store, year, doctors, lambda: save_extra(extra))
        st.markdown("#### Daily schedule")
        autosave = st.toggle("Auto-save schedule changes", value=True, key=f"schedule_autosave_{year}")
        st.caption("Auto-save writes Call and Notes changes after each completed grid edit. Vacation, Quick Assign, office-closure, and observance actions already save when their action button is selected.")
        edited = st.data_editor(
            data[["Date", "Day", "Holiday", "Observances", "Call", "Vacation", "Notes"]],
            hide_index=True,
            use_container_width=True,
            key=f"main_schedule_{year}",
            disabled=["Date", "Day", "Holiday", "Observances", "Vacation"],
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "Call": st.column_config.SelectboxColumn("Call", options=call_choices(store), required=True),
            },
        )
        saved = {str(row["Date"]): row for row in store["years"][str(year)]}
        pending = []
        for row in edited.to_dict("records"):
            key = str(row["Date"])
            new_call = str(row.get("Call") or "Unassigned")
            new_notes = str(row.get("Notes") or "")
            target = saved.get(key)
            if target and (str(target.get("Call") or "Unassigned") != new_call or str(target.get("Notes") or "") != new_notes):
                pending.append((target, new_call, new_notes))
        if pending and autosave:
            for target, new_call, new_notes in pending:
                target["Call"] = new_call
                target["Notes"] = new_notes
            save_extra(extra)
            st.success(f"Auto-saved {len(pending)} schedule change(s).")
        elif pending:
            st.warning(f"{len(pending)} unsaved schedule change(s).")
        else:
            st.caption("Saved")
        if st.button("Save Schedule Now", type="primary", disabled=not pending):
            for target, new_call, new_notes in pending:
                target["Call"] = new_call
                target["Notes"] = new_notes
            save_extra(extra)
            if log_activity:
                log_activity(f"Updated {year} call and vacation schedule")
            st.rerun()
    with tabs[1]:
        selected = st.selectbox("Call", call_choices(store)); a, b, c = st.columns(3); start = a.date_input("Starting date", date(year, 1, 2), min_value=date(year, 1, 1), max_value=date(year, 12, 31)); weekday = b.selectbox("Day", WEEKDAYS, index=5); scope = c.selectbox("Apply to", SCOPES, index=1)
        if st.button("Apply Call", type="primary"):
            for row in store["years"][str(year)]:
                current = date.fromisoformat(row["Date"]); match = current == start if scope == "One date" else row["Day"] == weekday if scope == "All matching weekdays" else row["Day"] == weekday and current >= start
                if match: row["Call"] = selected
            save_extra(extra); st.rerun()
        calls = pd.DataFrame(store["call_templates"]); changed = st.data_editor(calls, hide_index=True, use_container_width=True, num_rows="dynamic", key="call_definitions")
        if st.button("Save Call Choices"):
            store["call_templates"] = changed.where(pd.notna(changed), "").to_dict("records"); valid = set(call_choices(store))
            for rows in store["years"].values():
                for row in rows:
                    if row.get("Call") not in valid: row["Call"] = "Unassigned"
            save_extra(extra); st.rerun()
    with tabs[2]:
        changed = st.data_editor(pd.DataFrame(store["doctors"]), hide_index=True, use_container_width=True, num_rows="dynamic", key="doctor_list")
        if st.button("Save Doctors"): store["doctors"] = changed.where(pd.notna(changed), "").to_dict("records"); save_extra(extra); st.rerun()
    with tabs[3]:
        owed = pd.DataFrame(store.get("owed_calls", [])) if store.get("owed_calls") else pd.DataFrame(columns=["Debtor", "Creditor", "Type", "Quantity", "Notes"]); changed = st.data_editor(owed, hide_index=True, use_container_width=True, num_rows="dynamic", key="owed_calls", column_config={"Debtor": st.column_config.SelectboxColumn("Debtor", options=doctors), "Creditor": st.column_config.SelectboxColumn("Creditor", options=doctors), "Type": st.column_config.SelectboxColumn("Type", options=["Weekday", "Weekend"]), "Quantity": st.column_config.NumberColumn("Quantity", min_value=0.5, step=0.5)})
        if st.button("Save Owed Calls"): store["owed_calls"] = changed.where(pd.notna(changed), "").to_dict("records"); save_extra(extra); st.rerun()
    with tabs[4]: st.dataframe(equity(data, store, doctors), hide_index=True, use_container_width=True)
    with tabs[5]: st.dataframe(data[data["Holiday"].str.len() > 0][["Date", "Holiday", "Call"]], hide_index=True, use_container_width=True)
    with tabs[6]:
        problem = data[data["Issues"].str.len() > 0]
        if problem.empty: st.success("No schedule issues.")
        else: st.dataframe(problem[["Date", "Day", "Holiday", "Issues", "Notes"]], hide_index=True, use_container_width=True)
