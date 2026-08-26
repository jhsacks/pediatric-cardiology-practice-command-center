import calendar
from copy import deepcopy
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

PORTIONS = ["Full Day", "Morning", "Afternoon"]
PORTION_CREDIT = {"Full Day": 1.0, "Morning": 0.5, "Afternoon": 0.5}


def nth_weekday(year, month, weekday, n):
    dates = [date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, d).weekday() == weekday]
    return dates[n - 1]


def last_weekday(year, month, weekday):
    return [date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, d).weekday() == weekday][-1]


def default_office_closures(year):
    return [
        {"Date": date(year, 1, 1).isoformat(), "Reason": "New Year's Day", "Office Closed": True, "Notes": ""},
        {"Date": nth_weekday(year, 1, calendar.MONDAY, 3).isoformat(), "Reason": "MLK Day", "Office Closed": True, "Notes": ""},
        {"Date": last_weekday(year, 5, calendar.MONDAY).isoformat(), "Reason": "Memorial Day", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 7, 4).isoformat(), "Reason": "Fourth of July", "Office Closed": True, "Notes": "Observed date may be edited"},
        {"Date": nth_weekday(year, 9, calendar.MONDAY, 1).isoformat(), "Reason": "Labor Day", "Office Closed": True, "Notes": ""},
        {"Date": nth_weekday(year, 11, calendar.THURSDAY, 4).isoformat(), "Reason": "Thanksgiving", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 12, 24).isoformat(), "Reason": "Christmas Eve", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 12, 25).isoformat(), "Reason": "Christmas Day", "Office Closed": True, "Notes": "Observed date may be edited"},
        {"Date": date(year, 12, 31).isoformat(), "Reason": "New Year's Eve", "Office Closed": True, "Notes": ""},
    ]


def easter_date(year):
    a = year % 19; b = year // 100; c = year % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451; month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def generated_observances(year):
    easter = easter_date(year)
    values = [
        {"Date": date(year, 1, 6).isoformat(), "Observance": "Epiphany", "Tradition": "Christian", "Office Closed": False},
        {"Date": (easter - timedelta(days=46)).isoformat(), "Observance": "Ash Wednesday", "Tradition": "Christian", "Office Closed": False},
        {"Date": (easter - timedelta(days=7)).isoformat(), "Observance": "Palm Sunday", "Tradition": "Christian", "Office Closed": False},
        {"Date": (easter - timedelta(days=2)).isoformat(), "Observance": "Good Friday", "Tradition": "Christian", "Office Closed": False},
        {"Date": easter.isoformat(), "Observance": "Easter", "Tradition": "Christian", "Office Closed": False},
        {"Date": (easter + timedelta(days=49)).isoformat(), "Observance": "Pentecost", "Tradition": "Christian", "Office Closed": False},
        {"Date": date(year, 2, 14).isoformat(), "Observance": "Valentine's Day", "Tradition": "American", "Office Closed": False},
        {"Date": date(year, 6, 19).isoformat(), "Observance": "Juneteenth", "Tradition": "American", "Office Closed": False},
        {"Date": date(year, 11, 11).isoformat(), "Observance": "Veterans Day", "Tradition": "American", "Office Closed": False},
    ]
    if year == 2027:
        values.extend([
            {"Date": "2027-01-23", "Observance": "Tu BiShvat", "Tradition": "Jewish", "Office Closed": False},
            {"Date": "2027-03-23", "Observance": "Purim", "Tradition": "Jewish", "Office Closed": False},
            {"Date": "2027-02-08", "Observance": "Ramadan begins (tentative)", "Tradition": "Muslim", "Office Closed": False},
            {"Date": "2027-01-15", "Observance": "Pongal", "Tradition": "Indian/Hindu", "Office Closed": False},
            {"Date": "2027-02-06", "Observance": "Lunar New Year", "Tradition": "Asian", "Office Closed": False},
        ])
    return values


def doctors_from_value(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in str(value or "").split(",") if x.strip()]


def ensure_vacation_defaults(store):
    store.setdefault("vacation_blocks", [])
    closures = store.setdefault("office_closures", {})
    observances = store.setdefault("observances", {})
    for year_key, rows in store.get("years", {}).items():
        if not str(year_key).isdigit():
            continue
        year = int(year_key)
        closures.setdefault(str(year), default_office_closures(year))
        observances.setdefault(str(year), generated_observances(year))
        apply_vacations_and_observances(store, year)
    return store


def closed_dates(store, year):
    return {
        str(row.get("Date"))
        for row in store.get("office_closures", {}).get(str(year), [])
        if bool(row.get("Office Closed", False))
    }


def eligible_vacation_credit(day, portion, closed):
    if day.weekday() >= 5 or day.isoformat() in closed:
        return 0.0
    return PORTION_CREDIT.get(portion, 1.0)


def apply_vacations_and_observances(store, year):
    rows = store.get("years", {}).get(str(year), [])
    if not rows:
        return
    blocks = store.get("vacation_blocks", [])
    observances = store.get("observances", {}).get(str(year), [])
    obs_by_date = {}
    for obs in observances:
        obs_by_date.setdefault(str(obs.get("Date")), []).append(str(obs.get("Observance", "")))
    for row in rows:
        row_date = date.fromisoformat(str(row["Date"]))
        away = []
        details = []
        for block in blocks:
            start = date.fromisoformat(str(block["Start Date"]))
            end = date.fromisoformat(str(block["End Date"]))
            if start <= row_date <= end:
                for doctor in doctors_from_value(block.get("Doctors")):
                    away.append(doctor)
                    details.append(f"{doctor} ({block.get('Portion', 'Full Day')})")
        row["Vacation Doctors"] = ", ".join(sorted(set(away)))
        row["Vacation Details"] = "; ".join(details)
        row["Observances"] = "; ".join(x for x in obs_by_date.get(row_date.isoformat(), []) if x)
        user_notes = str(row.get("Notes", ""))
        row["Notes"] = user_notes


def vacation_summary_v2(frame, store):
    ensure_vacation_defaults(store)
    allocations = {str(x.get("Doctor")): float(x.get("Vacation Allocation", 0) or 0) for x in store.get("doctors", [])}
    used = {doctor: 0.0 for doctor in allocations}
    full = {doctor: 0 for doctor in allocations}
    half = {doctor: 0 for doctor in allocations}
    for block in store.get("vacation_blocks", []):
        start = date.fromisoformat(str(block["Start Date"])); end = date.fromisoformat(str(block["End Date"]))
        portion = str(block.get("Portion", "Full Day"))
        current = start
        while current <= end:
            closed = closed_dates(store, current.year)
            credit = eligible_vacation_credit(current, portion, closed)
            for doctor in doctors_from_value(block.get("Doctors")):
                used[doctor] = used.get(doctor, 0.0) + credit
                if credit == 1.0: full[doctor] = full.get(doctor, 0) + 1
                elif credit == 0.5: half[doctor] = half.get(doctor, 0) + 1
            current += timedelta(days=1)
    return pd.DataFrame([
        {"Doctor": doctor, "Allocated": allocated, "Full Days": full.get(doctor, 0), "Half Days": half.get(doctor, 0), "Used": used.get(doctor, 0.0), "Remaining": allocated - used.get(doctor, 0.0)}
        for doctor, allocated in allocations.items()
    ])


def render_vacation_planner(store, year, doctors, save_callback):
    ensure_vacation_defaults(store)
    st.subheader("Vacation Planner")
    st.caption("Away dates include weekends for coverage awareness. Vacation balances charge only Monday-Friday office-open time.")
    with st.form("add_vacation_block"):
        selected = st.multiselect("Doctors", doctors)
        c1, c2, c3 = st.columns(3)
        start = c1.date_input("Start date", value=date(year, 1, 1), min_value=date(year, 1, 1), max_value=date(year, 12, 31))
        end = c2.date_input("End date", value=date(year, 1, 1), min_value=date(year, 1, 1), max_value=date(year, 12, 31))
        portion = c3.selectbox("Day portion", PORTIONS)
        notes = st.text_input("Vacation notes")
        if st.form_submit_button("Add Vacation Block"):
            if selected and end >= start:
                store["vacation_blocks"].append({"Doctors": selected, "Start Date": start.isoformat(), "End Date": end.isoformat(), "Portion": portion, "Notes": notes})
                apply_vacations_and_observances(store, year)
                save_callback()
                st.rerun()
            st.error("Select at least one doctor and a valid date range.")
    blocks = pd.DataFrame(store.get("vacation_blocks", []))
    if blocks.empty:
        blocks = pd.DataFrame(columns=["Doctors", "Start Date", "End Date", "Portion", "Notes"])
    edited = st.data_editor(blocks, hide_index=True, use_container_width=True, num_rows="dynamic", key="vacation_blocks_v1", column_config={"Portion": st.column_config.SelectboxColumn("Portion", options=PORTIONS)})
    if st.button("Save Vacation Blocks"):
        records = edited.where(pd.notna(edited), "").to_dict("records")
        for record in records:
            if isinstance(record.get("Doctors"), str):
                record["Doctors"] = doctors_from_value(record["Doctors"])
        store["vacation_blocks"] = records
        apply_vacations_and_observances(store, year)
        save_callback(); st.rerun()
    st.subheader(f"{year} Vacation Balance")
    st.dataframe(vacation_summary_v2(pd.DataFrame(), store), hide_index=True, use_container_width=True)
    st.subheader("Office Closed Days")
    closures = pd.DataFrame(store["office_closures"].get(str(year), default_office_closures(year)))
    edited_closures = st.data_editor(closures, hide_index=True, use_container_width=True, num_rows="dynamic", key=f"closures_{year}")
    if st.button("Save Office Closed Days"):
        store["office_closures"][str(year)] = edited_closures.where(pd.notna(edited_closures), "").to_dict("records")
        apply_vacations_and_observances(store, year)
        save_callback(); st.rerun()
    st.subheader("Cultural and Religious Observances")
    st.caption("Reference only. These do not close the office unless separately added above. Lunar-calendar dates can vary by community or observation and remain editable.")
    observances = pd.DataFrame(store["observances"].get(str(year), generated_observances(year)))
    edited_obs = st.data_editor(observances, hide_index=True, use_container_width=True, num_rows="dynamic", key=f"observances_{year}")
    if st.button("Save Observances"):
        store["observances"][str(year)] = edited_obs.where(pd.notna(edited_obs), "").to_dict("records")
        apply_vacations_and_observances(store, year)
        save_callback(); st.rerun()
