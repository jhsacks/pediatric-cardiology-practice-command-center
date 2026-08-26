import calendar
from datetime import date, timedelta

import pandas as pd
import streamlit as st

PORTIONS = ["Full Day", "Morning", "Afternoon"]
PORTION_CREDIT = {"Full Day": 1.0, "Morning": 0.5, "Afternoon": 0.5}


def nth_weekday(year, month, weekday, n):
    values = [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, day).weekday() == weekday]
    return values[n - 1]


def last_weekday(year, month, weekday):
    values = [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, day).weekday() == weekday]
    return values[-1]


def default_office_closures(year):
    return [
        {"Date": date(year, 1, 1).isoformat(), "Reason": "New Year's Day", "Office Closed": True, "Notes": ""},
        {"Date": nth_weekday(year, 1, calendar.MONDAY, 3).isoformat(), "Reason": "MLK Day", "Office Closed": True, "Notes": ""},
        {"Date": last_weekday(year, 5, calendar.MONDAY).isoformat(), "Reason": "Memorial Day", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 7, 4).isoformat(), "Reason": "Fourth of July", "Office Closed": True, "Notes": "Observed date is editable"},
        {"Date": nth_weekday(year, 9, calendar.MONDAY, 1).isoformat(), "Reason": "Labor Day", "Office Closed": True, "Notes": ""},
        {"Date": nth_weekday(year, 11, calendar.THURSDAY, 4).isoformat(), "Reason": "Thanksgiving", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 12, 24).isoformat(), "Reason": "Christmas Eve", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 12, 25).isoformat(), "Reason": "Christmas Day", "Office Closed": True, "Notes": "Observed date is editable"},
        {"Date": date(year, 12, 31).isoformat(), "Reason": "New Year's Eve", "Office Closed": True, "Notes": ""},
    ]


def easter_date(year):
    a = year % 19; b = year // 100; c = year % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451; month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def default_observances(year):
    easter = easter_date(year)
    items = [
        {"Date": date(year, 1, 6).isoformat(), "Observance": "Epiphany", "Tradition": "Christian", "Notes": ""},
        {"Date": (easter - timedelta(days=46)).isoformat(), "Observance": "Ash Wednesday", "Tradition": "Christian", "Notes": ""},
        {"Date": (easter - timedelta(days=7)).isoformat(), "Observance": "Palm Sunday", "Tradition": "Christian", "Notes": ""},
        {"Date": (easter - timedelta(days=2)).isoformat(), "Observance": "Good Friday", "Tradition": "Christian", "Notes": ""},
        {"Date": easter.isoformat(), "Observance": "Easter", "Tradition": "Christian", "Notes": ""},
        {"Date": (easter + timedelta(days=49)).isoformat(), "Observance": "Pentecost", "Tradition": "Christian", "Notes": ""},
        {"Date": date(year, 6, 19).isoformat(), "Observance": "Juneteenth", "Tradition": "American", "Notes": ""},
        {"Date": date(year, 11, 11).isoformat(), "Observance": "Veterans Day", "Tradition": "American", "Notes": ""},
        {"Date": date(year, 1, 15).isoformat(), "Observance": "Pongal", "Tradition": "Indian/Hindu", "Notes": "Date may vary by community"},
    ]
    if year == 2027:
        items += [
            {"Date": "2027-01-23", "Observance": "Tu BiShvat", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-03-23", "Observance": "Purim", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-04-22", "Observance": "Passover begins", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-06-11", "Observance": "Shavuot", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-10-02", "Observance": "Rosh Hashanah", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-10-11", "Observance": "Yom Kippur", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-12-25", "Observance": "Hanukkah begins", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-02-08", "Observance": "Ramadan begins", "Tradition": "Muslim", "Notes": "Tentative; moon sighting may shift date"},
            {"Date": "2027-03-09", "Observance": "Eid al-Fitr", "Tradition": "Muslim", "Notes": "Tentative; moon sighting may shift date"},
            {"Date": "2027-05-16", "Observance": "Eid al-Adha", "Tradition": "Muslim", "Notes": "Tentative; moon sighting may shift date"},
            {"Date": "2027-02-06", "Observance": "Lunar New Year", "Tradition": "Asian", "Notes": ""},
        ]
    return items


def doctors_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def ensure_vacation_data(store):
    store.setdefault("vacation_blocks", [])
    store.setdefault("office_closures", {})
    store.setdefault("observances", {})
    for year_key in store.get("years", {}):
        if str(year_key).isdigit():
            year = int(year_key)
            store["office_closures"].setdefault(str(year), default_office_closures(year))
            store["observances"].setdefault(str(year), default_observances(year))
    return store


def closed_date_set(store, year):
    return {str(row.get("Date")) for row in store["office_closures"].get(str(year), []) if bool(row.get("Office Closed", False))}


def away_details(store, day):
    values = []
    for block in store.get("vacation_blocks", []):
        start = date.fromisoformat(str(block["Start Date"])); end = date.fromisoformat(str(block["End Date"]))
        if start <= day <= end:
            for doctor in doctors_list(block.get("Doctors")):
                values.append(f"{doctor} ({block.get('Portion', 'Full Day')})")
    return values


def away_doctors(store, day):
    return sorted({value.split(" (")[0] for value in away_details(store, day)})


def observance_text(store, day):
    return "; ".join(str(row.get("Observance", "")) for row in store["observances"].get(str(day.year), []) if str(row.get("Date")) == day.isoformat() and str(row.get("Observance", "")))


def vacation_summary(store):
    ensure_vacation_data(store)
    allocations = {str(row.get("Doctor")): float(row.get("Vacation Allocation", 0) or 0) for row in store.get("doctors", [])}
    used = {doctor: 0.0 for doctor in allocations}; full = {doctor: 0 for doctor in allocations}; half = {doctor: 0 for doctor in allocations}
    for block in store.get("vacation_blocks", []):
        start = date.fromisoformat(str(block["Start Date"])); end = date.fromisoformat(str(block["End Date"])); portion = str(block.get("Portion", "Full Day")); current = start
        while current <= end:
            credit = 0.0 if current.weekday() >= 5 or current.isoformat() in closed_date_set(store, current.year) else PORTION_CREDIT.get(portion, 1.0)
            for doctor in doctors_list(block.get("Doctors")):
                used[doctor] = used.get(doctor, 0.0) + credit
                if credit == 1.0: full[doctor] = full.get(doctor, 0) + 1
                elif credit == 0.5: half[doctor] = half.get(doctor, 0) + 1
            current += timedelta(days=1)
    return pd.DataFrame([{"Doctor": doctor, "Allocated": allocation, "Full Days": full.get(doctor, 0), "Half Days": half.get(doctor, 0), "Used": used.get(doctor, 0.0), "Remaining": allocation - used.get(doctor, 0.0)} for doctor, allocation in allocations.items()])


def render_vacation_planner(store, year, doctors, save_callback):
    ensure_vacation_data(store)
    st.subheader("Vacation Planner")
    st.caption("The full away range is visible for coverage. Only Monday-Friday office-open time is charged.")
    with st.form("add_vacation_block_v2"):
        selected = st.multiselect("Doctors", doctors)
        a, b, c = st.columns(3)
        start = a.date_input("Start date", date(year, 1, 1), min_value=date(year, 1, 1), max_value=date(year, 12, 31))
        end = b.date_input("End date", date(year, 1, 1), min_value=date(year, 1, 1), max_value=date(year, 12, 31))
        portion = c.selectbox("Portion", PORTIONS)
        notes = st.text_input("Notes")
        if st.form_submit_button("Add Vacation Block"):
            if selected and end >= start:
                store["vacation_blocks"].append({"Doctors": selected, "Start Date": start.isoformat(), "End Date": end.isoformat(), "Portion": portion, "Notes": notes})
                save_callback(); st.rerun()
            st.error("Select at least one doctor and a valid range.")
    blocks = pd.DataFrame(store["vacation_blocks"])
    if blocks.empty: blocks = pd.DataFrame(columns=["Doctors", "Start Date", "End Date", "Portion", "Notes"])
    changed = st.data_editor(blocks, hide_index=True, use_container_width=True, num_rows="dynamic", key="vacation_blocks_v2", column_config={"Portion": st.column_config.SelectboxColumn("Portion", options=PORTIONS)})
    if st.button("Save Vacation Blocks"):
        records = changed.where(pd.notna(changed), "").to_dict("records")
        for row in records: row["Doctors"] = doctors_list(row.get("Doctors"))
        store["vacation_blocks"] = records; save_callback(); st.rerun()
    st.dataframe(vacation_summary(store), hide_index=True, use_container_width=True)
    st.subheader("Office Closed Days")
    closures = pd.DataFrame(store["office_closures"][str(year)])
    changed_closures = st.data_editor(closures, hide_index=True, use_container_width=True, num_rows="dynamic", key=f"closed_{year}")
    if st.button("Save Office Closed Days"):
        store["office_closures"][str(year)] = changed_closures.where(pd.notna(changed_closures), "").to_dict("records"); save_callback(); st.rerun()
    st.subheader("Cultural and Religious Observances")
    st.caption("Reference only. These do not close the office. Lunar dates may vary and remain editable.")
    observations = pd.DataFrame(store["observances"][str(year)])
    changed_observances = st.data_editor(observations, hide_index=True, use_container_width=True, num_rows="dynamic", key=f"obs_{year}")
    if st.button("Save Observances"):
        store["observances"][str(year)] = changed_observances.where(pd.notna(changed_observances), "").to_dict("records"); save_callback(); st.rerun()
