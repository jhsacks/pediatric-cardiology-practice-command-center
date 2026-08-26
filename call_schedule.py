import calendar
from copy import deepcopy
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

DEFAULT_DOCTORS = ["Jeffrey Sacks", "Luv Makadia", "Yoni Yaari"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKEND_DAYS = {"Friday", "Saturday", "Sunday"}
CALL_TYPES = ["Full Day", "Split"]


def holiday_dates(year):
    def nth_weekday(month, weekday, n):
        count = 0
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            candidate = date(year, month, day)
            if candidate.weekday() == weekday:
                count += 1
                if count == n:
                    return candidate

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
    rows = []
    for offset in range((date(year + 1, 1, 1) - start).days):
        current = start + timedelta(days=offset)
        rows.append({
            "Date": current.isoformat(),
            "Day": current.strftime("%A"),
            "Holiday": holidays.get(current, ""),
            "Call Type": "Full Day",
            "Full Day": "",
            "Morning": "",
            "Evening": "",
            "Vacation Doctors": "",
            "Notes": "",
        })
    return rows


def default_store():
    return {
        "doctors": [
            {"Doctor": "Jeffrey Sacks", "Vacation Allocation": 0.0, "Active": True},
            {"Doctor": "Luv Makadia", "Vacation Allocation": 0.0, "Active": True},
            {"Doctor": "Yoni Yaari", "Vacation Allocation": 0.0, "Active": True},
        ],
        "years": {"2027": empty_year(2027)},
        "owed_calls": [],
        "holiday_history": [
            {"Year": 2026, "Holiday": "Christmas Day", "Doctor": "Jeffrey Sacks", "Credit": 1.0},
            {"Year": 2026, "Holiday": "New Year's Day", "Doctor": "Yoni Yaari", "Credit": 1.0},
            {"Year": 2026, "Holiday": "Thanksgiving", "Doctor": "Luv Makadia", "Credit": 1.0},
        ],
    }


def ensure_store(extra):
    store = extra.setdefault("call_schedule", default_store())
    defaults = default_store()
    for key, value in defaults.items():
        store.setdefault(key, deepcopy(value))
    store.setdefault("years", {})
    return store


def doctor_names(store):
    return [
        str(row.get("Doctor", "")).strip()
        for row in store.get("doctors", [])
        if row.get("Active", True) and str(row.get("Doctor", "")).strip()
    ]


def vacation_names(value):
    return {name.strip() for name in str(value or "").split(",") if name.strip()}


def call_credits(row):
    if row.get("Call Type") == "Split":
        result = []
        if row.get("Morning"):
            result.append((row["Morning"], 0.5))
        if row.get("Evening"):
            result.append((row["Evening"], 0.5))
        return result
    return [(row.get("Full Day"), 1.0)] if row.get("Full Day") else []


def conflict_text(row):
    vacations = vacation_names(row.get("Vacation Doctors"))
    conflicts = [doctor for doctor, _ in call_credits(row) if doctor in vacations]
    return ", ".join(sorted(set(conflicts)))


def schedule_frame(store, year):
    rows = deepcopy(store.get("years", {}).get(str(year), empty_year(year)))
    frame = pd.DataFrame(rows)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.date
    frame["Conflict"] = frame.apply(conflict_text, axis=1)
    return frame


def call_summary(frame, doctors):
    totals = {doctor: {"Weekday": 0.0, "Weekend": 0.0, "Total": 0.0} for doctor in doctors}
    for _, row in frame.iterrows():
        bucket = "Weekend" if row["Day"] in WEEKEND_DAYS else "Weekday"
        for doctor, credit in call_credits(row):
            totals.setdefault(doctor, {"Weekday": 0.0, "Weekend": 0.0, "Total": 0.0})
            totals[doctor][bucket] += credit
            totals[doctor]["Total"] += credit
    return pd.DataFrame([{"Doctor": doctor, **values} for doctor, values in totals.items()])


def vacation_summary(frame, store):
    used = {doctor: 0.0 for doctor in doctor_names(store)}
    for value in frame.get("Vacation Doctors", pd.Series(dtype=str)):
        for doctor in vacation_names(value):
            used[doctor] = used.get(doctor, 0.0) + 1.0
    allocations = {row.get("Doctor"): float(row.get("Vacation Allocation", 0) or 0) for row in store.get("doctors", [])}
    return pd.DataFrame([
        {"Doctor": doctor, "Allocated": allocations.get(doctor, 0.0), "Used": count, "Remaining": allocations.get(doctor, 0.0) - count}
        for doctor, count in used.items()
    ])


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
    for current, holiday in holiday_dates(int(frame.iloc[0]["Date"].year)).items():
        counts = {doctor: 0.0 for doctor in doctors}
        if not history.empty:
            subset = history[history["Holiday"] == holiday]
            for _, row in subset.iterrows():
                if row["Doctor"] in counts:
                    counts[row["Doctor"]] += float(row.get("Credit", 0) or 0)
        minimum = min(counts.values()) if counts else 0
        suggested = [doctor for doctor, count in counts.items() if count == minimum]
        suggestions.append({"Holiday": holiday, "Date": current, "Suggested": ", ".join(suggested), "Historical Credits": "; ".join(f"{doctor}: {count:g}" for doctor, count in counts.items())})
    return pd.DataFrame(suggestions)


def render_readonly(store):
    years = sorted(int(year) for year in store.get("years", {}) if str(year).isdigit())
    if not years:
        st.info("No call schedule years are available.")
        return
    year = st.selectbox("Calendar year", years, index=len(years) - 1, key="practice_schedule_year")
    doctors = doctor_names(store)
    frame = schedule_frame(store, year)
    gaps = frame[frame.apply(lambda row: len(call_credits(row)) == 0, axis=1)]
    conflicts = frame[frame["Conflict"].astype(str).str.len() > 0]
    metrics = st.columns(4)
    metrics[0].metric("Unassigned dates", len(gaps))
    metrics[1].metric("Call/vacation conflicts", len(conflicts))
    metrics[2].metric("Weekend call credits", call_summary(frame, doctors)["Weekend"].sum())
    metrics[3].metric("Weekday call credits", call_summary(frame, doctors)["Weekday"].sum())
    tabs = st.tabs(["Calendar", "Coverage Gaps", "Call Equity", "Vacation", "Owed Call", "Holidays"])
    with tabs[0]:
        st.dataframe(frame, hide_index=True, use_container_width=True)
    with tabs[1]:
        if gaps.empty:
            st.success("Every date has call coverage.")
        else:
            st.dataframe(gaps[["Date", "Day", "Holiday", "Notes"]], hide_index=True, use_container_width=True)
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
        st.subheader(f"{year} Holiday Assignments")
        st.dataframe(holiday_assignments(frame), hide_index=True, use_container_width=True)
        st.subheader("Holiday History")
        history = holiday_history_table(store)
        st.dataframe(history, hide_index=True, use_container_width=True)


def render_editor(extra, save_extra, log_activity=None):
    store = ensure_store(extra)
    st.header("Call & Vacation Scheduler")
    years = sorted(int(year) for year in store.get("years", {}) if str(year).isdigit())
    controls = st.columns(3)
    year = controls[0].selectbox("Calendar year", years, index=len(years) - 1, key="editor_schedule_year")
    new_year = controls[1].number_input("Add year", min_value=2027, max_value=2100, value=max(years) + 1, step=1)
    if controls[2].button("Add Calendar Year"):
        store["years"].setdefault(str(int(new_year)), empty_year(int(new_year)))
        save_extra(extra)
        st.rerun()

    doctors = doctor_names(store)
    tabs = st.tabs(["Schedule", "Bulk Assign", "Doctors & Vacation", "Owed Call", "Equity", "Holidays"])

    with tabs[0]:
        frame = schedule_frame(store, year)
        options = [""] + doctors
        edited = st.data_editor(
            frame.drop(columns=["Conflict"]),
            hide_index=True,
            use_container_width=True,
            key=f"schedule_{year}",
            disabled=["Date", "Day", "Holiday"],
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "Day": st.column_config.TextColumn("Day"),
                "Holiday": st.column_config.TextColumn("Holiday"),
                "Call Type": st.column_config.SelectboxColumn("Call Type", options=CALL_TYPES),
                "Full Day": st.column_config.SelectboxColumn("Full Day", options=options),
                "Morning": st.column_config.SelectboxColumn("Morning", options=options),
                "Evening": st.column_config.SelectboxColumn("Evening", options=options),
                "Vacation Doctors": st.column_config.TextColumn("Vacation Doctors", help="Comma-separated doctor names"),
                "Notes": st.column_config.TextColumn("Notes"),
            },
        )
        preview = edited.copy()
        preview["Conflict"] = preview.apply(conflict_text, axis=1)
        conflicts = preview[preview["Conflict"].astype(str).str.len() > 0]
        if not conflicts.empty:
            st.warning(f"{len(conflicts)} call/vacation conflict(s) flagged.")
            st.dataframe(conflicts[["Date", "Conflict", "Notes"]], hide_index=True, use_container_width=True)
        if st.button("Save Annual Schedule", type="primary"):
            save_frame = edited.copy()
            save_frame["Date"] = save_frame["Date"].astype(str)
            store["years"][str(year)] = save_frame.where(pd.notna(save_frame), "").to_dict("records")
            save_extra(extra)
            if log_activity:
                log_activity(f"Updated {year} call and vacation schedule")
            st.rerun()

    with tabs[1]:
        weekday = st.selectbox("Day of week", WEEKDAYS)
        call_type = st.selectbox("Assignment type", CALL_TYPES)
        if call_type == "Full Day":
            full = st.selectbox("Doctor", doctors)
            morning = evening = ""
        else:
            morning = st.selectbox("Morning doctor", doctors)
            evening = st.selectbox("Evening doctor", doctors)
            full = ""
        if st.button("Apply to Every Matching Day"):
            rows = store["years"][str(year)]
            for row in rows:
                if row["Day"] == weekday:
                    row.update({"Call Type": call_type, "Full Day": full, "Morning": morning, "Evening": evening})
            save_extra(extra)
            st.rerun()

    with tabs[2]:
        doctor_frame = pd.DataFrame(store.get("doctors", []))
        edited_doctors = st.data_editor(doctor_frame, hide_index=True, use_container_width=True, num_rows="dynamic", key="doctor_roster")
        if st.button("Save Doctor Roster and Vacation Allocations"):
            store["doctors"] = edited_doctors.where(pd.notna(edited_doctors), "").to_dict("records")
            save_extra(extra)
            st.rerun()
        st.subheader(f"{year} Vacation Balance")
        st.dataframe(vacation_summary(schedule_frame(store, year), store), hide_index=True, use_container_width=True)

    with tabs[3]:
        owed = pd.DataFrame(store.get("owed_calls", []))
        if owed.empty:
            owed = pd.DataFrame(columns=["Debtor", "Creditor", "Type", "Quantity", "Notes"])
        edited_owed = st.data_editor(
            owed,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="owed_calls",
            column_config={
                "Debtor": st.column_config.SelectboxColumn("Debtor", options=doctors),
                "Creditor": st.column_config.SelectboxColumn("Creditor", options=doctors),
                "Type": st.column_config.SelectboxColumn("Type", options=["Weekday", "Weekend"]),
                "Quantity": st.column_config.NumberColumn("Quantity", min_value=0.5, step=0.5),
            },
        )
        if st.button("Save Owed Call Ledger"):
            store["owed_calls"] = edited_owed.where(pd.notna(edited_owed), "").to_dict("records")
            save_extra(extra)
            st.rerun()

    with tabs[4]:
        st.dataframe(call_summary(schedule_frame(store, year), doctors), hide_index=True, use_container_width=True)

    with tabs[5]:
        frame = schedule_frame(store, year)
        st.subheader(f"{year} Holiday Assignments")
        st.dataframe(holiday_assignments(frame), hide_index=True, use_container_width=True)
        st.subheader("Holiday Assignment Suggestions")
        st.dataframe(holiday_suggestions(store, frame, doctors), hide_index=True, use_container_width=True)
        st.subheader("Holiday History")
        history = holiday_history_table(store)
        edited_history = st.data_editor(history, hide_index=True, use_container_width=True, num_rows="dynamic", key="holiday_history")
        if st.button("Save Holiday History"):
            store["holiday_history"] = edited_history.where(pd.notna(edited_history), "").to_dict("records")
            save_extra(extra)
            st.rerun()
