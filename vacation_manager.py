import calendar
from datetime import date, timedelta

import pandas as pd
import streamlit as st

PORTIONS = ["Full Day", "Morning", "Afternoon"]
CREDIT = {"Full Day": 1.0, "Morning": 0.5, "Afternoon": 0.5}


def _nth(year, month, weekday, number):
    days = [date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, d).weekday() == weekday]
    return days[number - 1]


def _last(year, month, weekday):
    days = [date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1) if date(year, month, d).weekday() == weekday]
    return days[-1]


def office_closures(year):
    return [
        {"Date": date(year, 1, 1).isoformat(), "Reason": "New Year's Day", "Office Closed": True, "Notes": ""},
        {"Date": _nth(year, 1, calendar.MONDAY, 3).isoformat(), "Reason": "MLK Day", "Office Closed": True, "Notes": ""},
        {"Date": _last(year, 5, calendar.MONDAY).isoformat(), "Reason": "Memorial Day", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 7, 4).isoformat(), "Reason": "Fourth of July", "Office Closed": True, "Notes": "Edit observed date if needed"},
        {"Date": _nth(year, 9, calendar.MONDAY, 1).isoformat(), "Reason": "Labor Day", "Office Closed": True, "Notes": ""},
        {"Date": _nth(year, 11, calendar.THURSDAY, 4).isoformat(), "Reason": "Thanksgiving", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 12, 24).isoformat(), "Reason": "Christmas Eve", "Office Closed": True, "Notes": ""},
        {"Date": date(year, 12, 25).isoformat(), "Reason": "Christmas Day", "Office Closed": True, "Notes": "Edit observed date if needed"},
        {"Date": date(year, 12, 31).isoformat(), "Reason": "New Year's Eve", "Office Closed": True, "Notes": ""},
    ]


def _easter(year):
    a = year % 19; b = year // 100; c = year % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19*a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451; month = (h + l - 7*m + 114) // 31
    return date(year, month, ((h + l - 7*m + 114) % 31) + 1)


def observances(year):
    easter = _easter(year)
    rows = [
        {"Date": date(year, 1, 6).isoformat(), "Observance": "Epiphany", "Tradition": "Christian", "Notes": ""},
        {"Date": (easter - timedelta(days=46)).isoformat(), "Observance": "Ash Wednesday", "Tradition": "Christian", "Notes": ""},
        {"Date": (easter - timedelta(days=7)).isoformat(), "Observance": "Palm Sunday", "Tradition": "Christian", "Notes": ""},
        {"Date": (easter - timedelta(days=2)).isoformat(), "Observance": "Good Friday", "Tradition": "Christian", "Notes": ""},
        {"Date": easter.isoformat(), "Observance": "Easter", "Tradition": "Christian", "Notes": ""},
        {"Date": (easter + timedelta(days=49)).isoformat(), "Observance": "Pentecost", "Tradition": "Christian", "Notes": ""},
        {"Date": date(year, 6, 19).isoformat(), "Observance": "Juneteenth", "Tradition": "American", "Notes": ""},
        {"Date": date(year, 11, 11).isoformat(), "Observance": "Veterans Day", "Tradition": "American", "Notes": ""},
        {"Date": date(year, 1, 15).isoformat(), "Observance": "Pongal", "Tradition": "Indian/Hindu", "Notes": "Date may vary"},
    ]
    if year == 2027:
        rows += [
            {"Date": "2027-01-23", "Observance": "Tu BiShvat", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-03-23", "Observance": "Purim", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-04-22", "Observance": "Passover begins", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-06-11", "Observance": "Shavuot", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-10-02", "Observance": "Rosh Hashanah", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-10-11", "Observance": "Yom Kippur", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-12-25", "Observance": "Hanukkah begins", "Tradition": "Jewish", "Notes": "Begins at sundown previously"},
            {"Date": "2027-02-08", "Observance": "Ramadan begins", "Tradition": "Muslim", "Notes": "Tentative"},
            {"Date": "2027-03-09", "Observance": "Eid al-Fitr", "Tradition": "Muslim", "Notes": "Tentative"},
            {"Date": "2027-05-16", "Observance": "Eid al-Adha", "Tradition": "Muslim", "Notes": "Tentative"},
            {"Date": "2027-02-06", "Observance": "Lunar New Year", "Tradition": "Asian", "Notes": ""},
        ]
    return rows


def doctors(value):
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value or "").split(",") if v.strip()]


def valid_block(block):
    if not isinstance(block, dict) or not block.get("Start Date") or not block.get("End Date"):
        return False
    try:
        return date.fromisoformat(str(block["Start Date"])) <= date.fromisoformat(str(block["End Date"]))
    except (TypeError, ValueError):
        return False


def ensure_data(store):
    store["vacation_blocks"] = [b for b in store.get("vacation_blocks", []) if valid_block(b)]
    store.setdefault("office_closures", {})
    store.setdefault("observances", {})
    for year_key in store.get("years", {}):
        if str(year_key).isdigit():
            year = int(year_key)
            store["office_closures"].setdefault(str(year), office_closures(year))
            store["observances"].setdefault(str(year), observances(year))
    return store


def away_details(store, day):
    result = []
    for block in store.get("vacation_blocks", []):
        if not valid_block(block):
            continue
        start = date.fromisoformat(str(block["Start Date"])); end = date.fromisoformat(str(block["End Date"]))
        if start <= day <= end:
            result += [f"{name} ({block.get('Portion', 'Full Day')})" for name in doctors(block.get("Doctors"))]
    return result


def away_doctors(store, day):
    return sorted({item.split(" (")[0] for item in away_details(store, day)})


def observance_text(store, day):
    return "; ".join(str(row.get("Observance", "")) for row in store.get("observances", {}).get(str(day.year), []) if str(row.get("Date")) == day.isoformat() and str(row.get("Observance", "")))


def vacation_summary(store):
    ensure_data(store)
    allocations = {str(row.get("Doctor")): float(row.get("Vacation Allocation", 0) or 0) for row in store.get("doctors", [])}
    used = {name: 0.0 for name in allocations}; full = {name: 0 for name in allocations}; half = {name: 0 for name in allocations}
    closed = {str(year): {str(row.get("Date")) for row in rows if bool(row.get("Office Closed", False))} for year, rows in store.get("office_closures", {}).items()}
    for block in store.get("vacation_blocks", []):
        if not valid_block(block):
            continue
        current = date.fromisoformat(str(block["Start Date"])); end = date.fromisoformat(str(block["End Date"])); portion = str(block.get("Portion", "Full Day"))
        while current <= end:
            credit = 0.0 if current.weekday() >= 5 or current.isoformat() in closed.get(str(current.year), set()) else CREDIT.get(portion, 1.0)
            for name in doctors(block.get("Doctors")):
                used[name] = used.get(name, 0.0) + credit
                if credit == 1.0: full[name] = full.get(name, 0) + 1
                elif credit == 0.5: half[name] = half.get(name, 0) + 1
            current += timedelta(days=1)
    return pd.DataFrame([{"Doctor": name, "Allocated": allocation, "Full Days": full.get(name, 0), "Half Days": half.get(name, 0), "Used": used.get(name, 0.0), "Remaining": allocation - used.get(name, 0.0)} for name, allocation in allocations.items()])


def vacation_controls(store, year, roster, save_callback):
    ensure_data(store)
    with st.expander("Vacation Management", expanded=False):
        st.caption("Add, edit, or remove vacation records. Weekends and office-closed dates remain visible as away but do not use vacation balance.")
        with st.form("main_schedule_vacation_form"):
            selected = st.multiselect("Vacation doctors", roster)
            a, b, c = st.columns(3)
            start = a.date_input("Start", date(year, 1, 1), min_value=date(year, 1, 1), max_value=date(year, 12, 31))
            end = b.date_input("End", date(year, 1, 1), min_value=date(year, 1, 1), max_value=date(year, 12, 31))
            portion = c.selectbox("Portion", PORTIONS)
            notes = st.text_input("Vacation notes")
            if st.form_submit_button("Add Vacation"):
                if selected and end >= start:
                    store["vacation_blocks"].append({"Doctors": selected, "Start Date": start.isoformat(), "End Date": end.isoformat(), "Portion": portion, "Notes": notes})
                    save_callback(); st.rerun()
                st.error("Select a doctor and valid date range.")
        blocks = pd.DataFrame(store.get("vacation_blocks", []))
        if blocks.empty:
            blocks = pd.DataFrame(columns=["Doctors", "Start Date", "End Date", "Portion", "Notes"])
        changed = st.data_editor(blocks, hide_index=True, use_container_width=True, num_rows="dynamic", key="main_vacations", column_config={"Portion": st.column_config.SelectboxColumn("Portion", options=PORTIONS)})
        if st.button("Save Vacation Changes"):
            records = []
            for block in changed.where(pd.notna(changed), "").to_dict("records"):
                block["Doctors"] = doctors(block.get("Doctors"))
                if valid_block(block):
                    records.append(block)
            store["vacation_blocks"] = records; save_callback(); st.rerun()
    with st.expander("Vacation Balances & Calendar Settings", expanded=False):
        st.dataframe(vacation_summary(store), hide_index=True, use_container_width=True)
        st.markdown("##### Office closed days")
        closures = pd.DataFrame(store["office_closures"][str(year)])
        changed_closed = st.data_editor(closures, hide_index=True, use_container_width=True, num_rows="dynamic", key=f"closed_{year}")
        if st.button("Save Office Closed Days"):
            store["office_closures"][str(year)] = changed_closed.where(pd.notna(changed_closed), "").to_dict("records"); save_callback(); st.rerun()
        st.markdown("##### Cultural and religious observances")
        reference = pd.DataFrame(store["observances"][str(year)])
        changed_reference = st.data_editor(reference, hide_index=True, use_container_width=True, num_rows="dynamic", key=f"observances_{year}")
        if st.button("Save Observances"):
            store["observances"][str(year)] = changed_reference.where(pd.notna(changed_reference), "").to_dict("records"); save_callback(); st.rerun()
