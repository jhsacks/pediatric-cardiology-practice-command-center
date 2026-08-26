import calendar
from copy import deepcopy
from datetime import date, timedelta

import pandas as pd
import streamlit as st

DEFAULT_DOCTORS = ["Jeffrey Sacks", "Luv Makadia", "Yoni Yaari"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKEND_DAYS = {"Friday", "Saturday", "Sunday"}
CALL_TYPES = ["Full Day", "Split"]
SCOPES = ["One date", "All matching weekdays", "Remaining matching weekdays"]


def holiday_dates(year):
    def nth_weekday(month, weekday, n):
        hits = []
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            candidate = date(year, month, day)
            if candidate.weekday() == weekday:
                hits.append(candidate)
        return hits[n - 1]

    def last_weekday(month, weekday):
        for day in range(calendar.monthrange(year, month)[1], 0, -1):
            candidate = date(year, month, day)
            if candidate.weekday() == weekday:
                return candidate

    return {
        date(year, 1, 1): "New Year's Day",
        nth_weekday(1, calendar.MONDAY, 3): "MLK Day",
        last_weekday(5, calendar.MONDAY): "Memorial Day",
        date(year, 7, 4): "Fourth of July",
        nth_weekday(9, calendar.MONDAY, 1): "Labor Day",
        nth_weekday(11, calendar.THURSDAY, 4): "Thanksgiving",
        date(year, 12, 24): "Christmas Eve",
        date(year, 12, 25): "Christmas Day",
        date(year, 12, 31): "New Year's Eve",
    }


def empty_year(year):
    holidays = holiday_dates(year)
    start = date(year, 1, 1)
    return [{
        "Date": (start + timedelta(days=offset)).isoformat(),
        "Day": (start + timedelta(days=offset)).strftime("%A"),
        "Holiday": holidays.get(start + timedelta(days=offset), ""),
        "Call Type": "Full Day",
        "Full Day": "",
        "Morning": "",
        "Evening": "",
        "Vacation Doctors": "",
        "Notes": "",
    } for offset in range((date(year + 1, 1, 1) - start).days)]


def default_templates():
    return [
        {"Template": "Sacks AM / Yaari PM", "Call Type": "Split", "Full Day": "", "Morning": "Jeffrey Sacks", "Evening": "Yoni Yaari"},
        {"Template": "Yaari AM / Sacks PM", "Call Type": "Split", "Full Day": "", "Morning": "Yoni Yaari", "Evening": "Jeffrey Sacks"},
        {"Template": "Full Day Sacks", "Call Type": "Full Day", "Full Day": "Jeffrey Sacks", "Morning": "", "Evening": ""},
        {"Template": "Full Day Makadia", "Call Type": "Full Day", "Full Day": "Luv Makadia", "Morning": "", "Evening": ""},
        {"Template": "Full Day Yaari", "Call Type": "Full Day", "Full Day": "Yoni Yaari", "Morning": "", "Evening": ""},
    ]


def default_store():
    return {
        "doctors": [{"Doctor": name, "Vacation Allocation": 0.0, "Active": True} for name in DEFAULT_DOCTORS],
        "years": {"2027": empty_year(2027)},
        "owed_calls": [],
        "templates": default_templates(),
        "holiday_history": [
            {"Year": 2026, "Holiday": "Christmas Day", "Doctor": "Jeffrey Sacks", "Credit": 1.0},
            {"Year": 2026, "Holiday": "New Year's Day", "Doctor": "Yoni Yaari", "Credit": 1.0},
            {"Year": 2026, "Holiday": "Thanksgiving", "Doctor": "Luv Makadia", "Credit": 1.0},
        ],
    }


def ensure_store(extra):
    store = extra.setdefault("call_schedule", default_store())
    for key, value in default_store().items():
        store.setdefault(key, deepcopy(value))
    return store


def doctor_names(store):
    return [str(row.get("Doctor", "")).strip() for row in store.get("doctors", []) if row.get("Active", True) and str(row.get("Doctor", "")).strip()]


def vacation_names(value):
    return {name.strip() for name in str(value or "").split(",") if name.strip()}


def normalize_row(row):
    result = dict(row)
    if result.get("Call Type") == "Split":
        result["Full Day"] = ""
    else:
        result["Morning"] = ""
        result["Evening"] = ""
    return result


def call_credits(row):
    normalized = normalize_row(row)
    if normalized.get("Call Type") == "Split":
        credits = []
        if normalized.get("Morning"):
            credits.append((normalized["Morning"], 0.5))
        if normalized.get("Evening"):
            credits.append((normalized["Evening"], 0.5))
        return credits
    return [(normalized.get("Full Day"), 1.0)] if normalized.get("Full Day") else []


def credit_text(row):
    return ", ".join(f"{doctor}: {credit:g}" for doctor, credit in call_credits(row))


def issue_text(row):
    issues = []
    if row.get("Call Type") == "Full Day" and (row.get("Morning") or row.get("Evening")):
        issues.append("Full Day with morning/evening values")
    if row.get("Call Type") == "Split" and row.get("Full Day"):
        issues.append("Split with full-day value")
    if not call_credits(row):
        issues.append("Unassigned call")
    vacations = vacation_names(row.get("Vacation Doctors"))
    conflicts = sorted({doctor for doctor, _ in call_credits(row) if doctor in vacations})
    if conflicts:
        issues.append("Call/vacation: " + ", ".join(conflicts))
    if row.get("Holiday") and not call_credits(row):
        issues.append("Unassigned holiday")
    return "; ".join(issues)


def schedule_frame(store, year):
    frame = pd.DataFrame(deepcopy(store.get("years", {}).get(str(year), empty_year(year))))
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.date
    frame["Call Credits"] = frame.apply(credit_text, axis=1)
    frame["Schedule Issues"] = frame.apply(issue_text, axis=1)
    return frame


def call_summary(frame, doctors):
    totals = {doctor: {"Weekday": 0.0, "Weekend": 0.0, "Holiday": 0.0, "Total": 0.0} for doctor in doctors}
    for _, row in frame.iterrows():
        bucket = "Weekend" if row["Day"] in WEEKEND_DAYS else "Weekday"
        for doctor, credit in call_credits(row):
            totals.setdefault(doctor, {"Weekday": 0.0, "Weekend": 0.0, "Holiday": 0.0, "Total": 0.0})
            totals[doctor][bucket] += credit
            totals[doctor]["Total"] += credit
            if row.get("Holiday"):
                totals[doctor]["Holiday"] += credit
    return pd.DataFrame([{"Doctor": doctor, **values} for doctor, values in totals.items()])


def vacation_summary(frame, store):
    used = {doctor: 0.0 for doctor in doctor_names(store)}
    for value in frame.get("Vacation Doctors", pd.Series(dtype=str)):
        for doctor in vacation_names(value):
            used[doctor] = used.get(doctor, 0.0) + 1.0
    allocation = {row.get("Doctor"): float(row.get("Vacation Allocation", 0) or 0) for row in store.get("doctors", [])}
    return pd.DataFrame([{"Doctor": doctor, "Allocated": allocation.get(doctor, 0.0), "Used": count, "Remaining": allocation.get(doctor, 0.0) - count} for doctor, count in used.items()])


def holiday_assignments(frame):
    rows = []
    for _, row in frame[frame["Holiday"].astype(str).str.len() > 0].iterrows():
        credits = call_credits(row)
        if not credits:
            rows.append({"Date": row["Date"], "Holiday": row["Holiday"], "Doctor": "Unassigned", "Credit": 0.0})
        for doctor, credit in credits:
            rows.append({"Date": row["Date"], "Holiday": row["Holiday"], "Doctor": doctor, "Credit": credit})
    return pd.DataFrame(rows)


def holiday_history_table(store, current=None):
    rows = list(store.get("holiday_history", []))
    if current is not None and not current.empty:
        for _, row in current.iterrows():
            rows.append({"Year": row["Date"].year, "Holiday": row["Holiday"], "Doctor": row["Doctor"], "Credit": row["Credit"]})
    return pd.DataFrame(rows)


def holiday_suggestions(store, frame, doctors):
    history = holiday_history_table(store, holiday_assignments(frame))
    suggestions = []
    year = int(frame.iloc[0]["Date"].year)
    for current, holiday in holiday_dates(year).items():
        counts = {doctor: 0.0 for doctor in doctors}
        if not history.empty:
            for _, row in history[history["Holiday"] == holiday].iterrows():
                if row["Doctor"] in counts:
                    counts[row["Doctor"]] += float(row.get("Credit", 0) or 0)
        minimum = min(counts.values()) if counts else 0
        suggestions.append({"Holiday": holiday, "Date": current, "Suggested": ", ".join(doctor for doctor, count in counts.items() if count == minimum), "Historical Credits": "; ".join(f"{doctor}: {count:g}" for doctor, count in counts.items())})
    return pd.DataFrame(suggestions)


def dashboard(frame, doctors):
    summary = call_summary(frame, doctors)
    issues = frame[frame["Schedule Issues"].astype(str).str.len() > 0]
    gaps = frame[frame.apply(lambda row: len(call_credits(row)) == 0, axis=1)]
    conflicts = frame[frame["Schedule Issues"].astype(str).str.contains("Call/vacation", regex=False)]
    cols = st.columns(5)
    cols[0].metric("Unassigned dates", len(gaps))
    cols[1].metric("Conflicts", len(conflicts))
    cols[2].metric("Weekday credits", f"{summary['Weekday'].sum():g}")
    cols[3].metric("Weekend credits", f"{summary['Weekend'].sum():g}")
    cols[4].metric("Holiday credits", f"{summary['Holiday'].sum():g}")
    return issues


def render_readonly(store):
    years = sorted(int(year) for year in store.get("years", {}) if str(year).isdigit())
    if not years:
        st.info("No call schedule years are available.")
        return
    year = st.selectbox("Calendar year", years, index=len(years) - 1, key="practice_schedule_year")
    doctors = doctor_names(store)
    frame = schedule_frame(store, year)
    issues = dashboard(frame, doctors)
    tabs = st.tabs(["Calendar", "Schedule Issues", "Call Equity", "Vacation", "Owed Call", "Holidays"])
    with tabs[0]:
        st.dataframe(frame, hide_index=True, use_container_width=True)
    with tabs[1]:
        if issues.empty:
            st.success("No schedule issues.")
        else:
            st.dataframe(issues[["Date", "Day", "Holiday", "Schedule Issues", "Notes"]], hide_index=True, use_container_width=True)
    with tabs[2]:
        st.dataframe(call_summary(frame, doctors), hide_index=True, use_container_width=True)
    with tabs[3]:
        st.dataframe(vacation_summary(frame, store), hide_index=True, use_container_width=True)
    with tabs[4]:
        owed = pd.DataFrame(store.get("owed_calls", []))
        if owed.empty:
            st.info("No owed calls recorded.")
        else:
            st.dataframe(owed, hide_index=True, use_container_width=True)
    with tabs[5]:
        st.dataframe(holiday_assignments(frame), hide_index=True, use_container_width=True)
        st.subheader("Holiday History")
        st.dataframe(holiday_history_table(store), hide_index=True, use_container_width=True)


def render_editor(extra, save_extra, log_activity=None):
    store = ensure_store(extra)
    st.header("Call & Vacation Scheduler")
    years = sorted(int(year) for year in store.get("years", {}) if str(year).isdigit())
    top = st.columns(3)
    year = top[0].selectbox("Calendar year", years, index=len(years) - 1, key="editor_schedule_year")
    new_year = top[1].number_input("Add year", min_value=2027, max_value=2100, value=max(years) + 1, step=1)
    if top[2].button("Add Calendar Year"):
        store["years"].setdefault(str(int(new_year)), empty_year(int(new_year)))
        save_extra(extra)
        st.rerun()

    doctors = doctor_names(store)
    frame = schedule_frame(store, year)
    issues = dashboard(frame, doctors)
    tabs = st.tabs(["Schedule", "Quick Assign", "Doctors & Vacation", "Owed Call", "Equity", "Holidays", "Schedule Issues"])

    with tabs[0]:
        options = [""] + doctors
        edited = st.data_editor(
            frame.drop(columns=["Call Credits", "Schedule Issues"]),
            hide_index=True,
            use_container_width=True,
            key=f"schedule_v3_{year}",
            disabled=["Date", "Day", "Holiday"],
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "Call Type": st.column_config.SelectboxColumn("Call Type", options=CALL_TYPES),
                "Full Day": st.column_config.SelectboxColumn("Full Day", options=options),
                "Morning": st.column_config.SelectboxColumn("Morning", options=options),
                "Evening": st.column_config.SelectboxColumn("Evening", options=options),
                "Vacation Doctors": st.column_config.TextColumn("Vacation Doctors", help="Comma-separated doctor names"),
            },
        )
        preview = edited.copy()
        preview["Call Credits"] = preview.apply(credit_text, axis=1)
        preview["Schedule Issues"] = preview.apply(issue_text, axis=1)
        st.subheader("Assignment Preview")
        st.dataframe(preview[["Date", "Call Credits", "Schedule Issues"]], hide_index=True, use_container_width=True)
        if st.button("Save Annual Schedule", type="primary"):
            cleaned = pd.DataFrame([normalize_row(row) for row in edited.to_dict("records")])
            cleaned["Date"] = cleaned["Date"].astype(str)
            store["years"][str(year)] = cleaned.where(pd.notna(cleaned), "").to_dict("records")
            save_extra(extra)
            if log_activity:
                log_activity(f"Updated {year} call and vacation schedule")
            st.rerun()

    with tabs[1]:
        templates = pd.DataFrame(store.get("templates", default_templates()))
        template_names = templates["Template"].tolist()
        selected_name = st.selectbox("Favorite pattern", template_names)
        selected_template = templates[templates["Template"] == selected_name].iloc[0].to_dict()
        c1, c2, c3 = st.columns(3)
        target_date = c1.date_input("Starting date", value=date(year, 1, 2), min_value=date(year, 1, 1), max_value=date(year, 12, 31))
        weekday = c2.selectbox("Day of week", WEEKDAYS, index=5)
        scope = c3.selectbox("Apply to", SCOPES, index=1)
        st.info(f"{selected_name}: {credit_text(selected_template)}")
        if st.button("Apply Favorite Pattern", type="primary"):
            for row in store["years"][str(year)]:
                row_date = date.fromisoformat(row["Date"])
                match = False
                if scope == "One date":
                    match = row_date == target_date
                elif scope == "All matching weekdays":
                    match = row["Day"] == weekday
                else:
                    match = row["Day"] == weekday and row_date >= target_date
                if match:
                    row.update({key: selected_template.get(key, "") for key in ["Call Type", "Full Day", "Morning", "Evening"]})
                    row.update(normalize_row(row))
            save_extra(extra)
            st.rerun()
        st.subheader("Manage Favorite Patterns")
        edited_templates = st.data_editor(templates, hide_index=True, use_container_width=True, num_rows="dynamic", key="call_templates")
        if st.button("Save Favorite Patterns"):
            store["templates"] = [normalize_row(row) for row in edited_templates.where(pd.notna(edited_templates), "").to_dict("records")]
            save_extra(extra)
            st.rerun()

    with tabs[2]:
        roster = pd.DataFrame(store.get("doctors", []))
        edited_roster = st.data_editor(roster, hide_index=True, use_container_width=True, num_rows="dynamic", key="doctor_roster_v3")
        if st.button("Save Doctor Roster and Vacation Allocations"):
            store["doctors"] = edited_roster.where(pd.notna(edited_roster), "").to_dict("records")
            save_extra(extra)
            st.rerun()
        st.dataframe(vacation_summary(schedule_frame(store, year), store), hide_index=True, use_container_width=True)

    with tabs[3]:
        owed = pd.DataFrame(store.get("owed_calls", []))
        if owed.empty:
            owed = pd.DataFrame(columns=["Debtor", "Creditor", "Type", "Quantity", "Notes"])
        edited_owed = st.data_editor(owed, hide_index=True, use_container_width=True, num_rows="dynamic", key="owed_v3", column_config={
            "Debtor": st.column_config.SelectboxColumn("Debtor", options=doctors),
            "Creditor": st.column_config.SelectboxColumn("Creditor", options=doctors),
            "Type": st.column_config.SelectboxColumn("Type", options=["Weekday", "Weekend"]),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=0.5, step=0.5),
        })
        if st.button("Save Owed Call Ledger"):
            store["owed_calls"] = edited_owed.where(pd.notna(edited_owed), "").to_dict("records")
            save_extra(extra)
            st.rerun()

    with tabs[4]:
        st.dataframe(call_summary(schedule_frame(store, year), doctors), hide_index=True, use_container_width=True)

    with tabs[5]:
        fresh = schedule_frame(store, year)
        st.subheader(f"{year} Holiday Assignments")
        st.dataframe(holiday_assignments(fresh), hide_index=True, use_container_width=True)
        st.subheader("Holiday Assignment Suggestions")
        st.dataframe(holiday_suggestions(store, fresh, doctors), hide_index=True, use_container_width=True)
        history = holiday_history_table(store)
        edited_history = st.data_editor(history, hide_index=True, use_container_width=True, num_rows="dynamic", key="holiday_history_v3")
        if st.button("Save Holiday History"):
            store["holiday_history"] = edited_history.where(pd.notna(edited_history), "").to_dict("records")
            save_extra(extra)
            st.rerun()

    with tabs[6]:
        current_issues = schedule_frame(store, year)
        current_issues = current_issues[current_issues["Schedule Issues"].astype(str).str.len() > 0]
        if current_issues.empty:
            st.success("No schedule issues.")
        else:
            st.dataframe(current_issues[["Date", "Day", "Holiday", "Schedule Issues", "Notes"]], hide_index=True, use_container_width=True)
