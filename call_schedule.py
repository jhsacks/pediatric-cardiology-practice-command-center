import calendar
from copy import deepcopy
from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
import streamlit as st
from single_vacation_column_36_1 import apply_vacation_changes, migrate_previous_direct_entries, vacation_choices

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
    migrate_previous_direct_entries(store)
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


def _qgenda_vacation_text(items):
    labels = []
    for item in items or []:
        name = str(item.get("person", "")).strip()
        session = str(item.get("session", "BOTH")).upper()
        if not name:
            continue
        label = "Full Day" if session == "BOTH" else session
        labels.append(f"{name} ({label})")
    return "; ".join(labels)


def _qgenda_call_text(store, planned_call, call_data):
    call_type = str((call_data or {}).get("type", "UNASSIGNED"))
    if call_type == "FULL_DAY":
        physician = str(call_data.get("full_day", "")).strip()
        exact = next((x.get("Call") for x in store.get("call_templates", []) if x.get("Full Day") == physician), None)
        return exact or (f"Full Day {physician.split()[-1]}" if physician else "Unassigned")
    physicians = [str(x).strip() for x in call_data.get("physicians", []) if str(x).strip()]
    if call_type in ("SPLIT_UNORDERED", "REVIEW") and physicians:
        planned_people = [name for name, _ in assignments(store, planned_call)]
        if len(planned_people) == len(physicians) and set(planned_people) == set(physicians):
            return planned_call
        matching = next((x.get("Call") for x in store.get("call_templates", []) if set(filter(None, [x.get("Morning"), x.get("Evening")])) == set(physicians)), None)
        return matching or " / ".join(physicians)
    return "Unassigned"


def qgenda_frame(store, year, operational):
    planned = frame(store, year)
    qdays = (operational or {}).get("days", {})
    rows = []
    for _, planned_row in planned.iterrows():
        current = planned_row["Date"]
        day = qdays.get(current.isoformat())
        if day:
            current_call = _qgenda_call_text(store, planned_row.get("Call", "Unassigned"), day.get("call", {}))
            current_vacation = _qgenda_vacation_text(day.get("vacations", []))
            source = "QGenda"
        else:
            current_call = planned_row.get("Call", "Unassigned")
            current_vacation = planned_row.get("Vacation", "")
            source = "Annual plan"
        call_people = assignments(store, current_call)
        away = {x.strip().split(" (")[0] for x in current_vacation.split(";") if x.strip()}
        conflicts = sorted({name for name, _ in call_people if name in away})
        issues = []
        if not call_people:
            issues.append("Unassigned call")
        if conflicts:
            issues.append("Call/vacation: " + ", ".join(conflicts))
        rows.append({
            "Date": current,
            "Day": planned_row.get("Day", current.strftime("%A")),
            "Holiday": planned_row.get("Holiday", ""),
            "Observances": planned_row.get("Observances", ""),
            "Call": current_call,
            "Vacation": current_vacation,
            "Notes": planned_row.get("Notes", ""),
            "Issues": "; ".join(issues),
            "Source": source,
            "Planned Call": planned_row.get("Call", "Unassigned"),
            "Planned Vacation": planned_row.get("Vacation", ""),
        })
    return pd.DataFrame(rows)


def qgenda_vacation_summary(data, store, doctors):
    closed = {"New Year's Day", "MLK Day", "Memorial Day", "Fourth of July", "Labor Day", "Thanksgiving", "Christmas Day"}
    used = {name: 0.0 for name in doctors}
    for _, row in data.iterrows():
        current = row["Date"]
        if current.weekday() >= 5 or row.get("Holiday", "") in closed:
            continue
        for item in str(row.get("Vacation", "") or "").split(";"):
            item = item.strip()
            for doctor in doctors:
                if item.startswith(doctor + " ("):
                    used[doctor] += 0.5 if item.endswith("(AM)") or item.endswith("(PM)") else 1.0
    allocations = {str(x.get("Doctor", "")): float(x.get("Vacation Allocation", 0) or 0) for x in store.get("doctors", [])}
    return pd.DataFrame([{"Doctor": name, "Allocation": allocations.get(name, 0.0), "Days Used": used[name], "Days Remaining": allocations.get(name, 0.0) - used[name]} for name in doctors])


def _excel_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def build_synced_workbook(uploaded_file, data, vacation_summary, operational):
    workbook = load_workbook(BytesIO(uploaded_file.getvalue()))
    sheet = workbook[workbook.sheetnames[0]]
    headers = {}
    header_row = None
    for row in range(1, min(sheet.max_row, 30) + 1):
        values = {str(sheet.cell(row, col).value or "").strip(): col for col in range(1, sheet.max_column + 1)}
        if "Date" in values and "Call" in values and "Vacation" in values:
            headers = values
            header_row = row
            break
    if not header_row:
        raise ValueError("The workbook must contain Date, Call, and Vacation columns.")
    by_date = {row["Date"]: row for _, row in data.iterrows()}
    for row in range(header_row + 1, sheet.max_row + 1):
        current = _excel_date(sheet.cell(row, headers["Date"]).value)
        if current not in by_date:
            continue
        values = by_date[current]
        sheet.cell(row, headers["Call"]).value = values.get("Call", "")
        sheet.cell(row, headers["Vacation"]).value = values.get("Vacation", "")
        if "Days used" in headers:
            vacation = str(values.get("Vacation", ""))
            credit = 0.0
            if current.weekday() < 5 and values.get("Holiday", "") not in {"New Year's Day", "MLK Day", "Memorial Day", "Fourth of July", "Labor Day", "Thanksgiving", "Christmas Day"}:
                for item in vacation.split(";"):
                    if item.strip():
                        credit += 0.5 if item.strip().endswith("(AM)") or item.strip().endswith("(PM)") else 1.0
            sheet.cell(row, headers["Days used"]).value = credit if credit else ""
    name = "QGenda Sync Summary"
    if name in workbook.sheetnames:
        del workbook[name]
    summary = workbook.create_sheet(name, 0)
    summary.sheet_view.showGridLines = False
    summary["A1"] = "QGenda Operational Schedule Sync"
    summary["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    summary["A1"].fill = PatternFill("solid", fgColor="2670C8")
    summary.merge_cells("A1:E1")
    summary["A3"] = "Last synced"
    summary["B3"] = operational.get("synced_at", "")
    summary["A4"] = "Coverage"
    summary["B4"] = f"{operational.get('range_start', '')} through {operational.get('range_end', '')}"
    summary.append([])
    summary.append(["Doctor", "Allocation", "Days Used", "Days Remaining"])
    for cell in summary[6]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="277B7F")
    for _, row in vacation_summary.iterrows():
        summary.append([row["Doctor"], row["Allocation"], row["Days Used"], row["Days Remaining"]])
    summary.append([])
    summary.append(["Doctor", "Weekday Call", "Weekend Call", "Total Call"])
    call_header = summary.max_row
    for cell in summary[call_header]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="CF303B")
    call_counts = operational.get("counts", {}).get("call", {})
    for doctor in vacation_summary["Doctor"].tolist():
        counts = call_counts.get(doctor, {})
        summary.append([doctor, counts.get("weekday", 0), counts.get("weekend", 0), counts.get("total", 0)])
    for column, width in {"A": 25, "B": 24, "C": 18, "D": 18, "E": 18}.items():
        summary.column_dimensions[column].width = width
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def render_qgenda_operational(store, year, operational):
    doctors = roster(store)
    data = qgenda_frame(store, year, operational)
    metrics(data, store, doctors)
    balances = qgenda_vacation_summary(data, store, doctors)
    tabs = st.tabs(["Operational Schedule", "Vacation Balances", "Call Equity", "Plan Differences", "Export Excel"])
    with tabs[0]:
        st.dataframe(data[["Date", "Day", "Holiday", "Call", "Vacation", "Source", "Issues"]], hide_index=True, use_container_width=True)
    with tabs[1]:
        st.dataframe(balances, hide_index=True, use_container_width=True)
    with tabs[2]:
        st.dataframe(equity(data, store, doctors), hide_index=True, use_container_width=True)
    with tabs[3]:
        differences = data[(data["Call"] != data["Planned Call"]) | (data["Vacation"] != data["Planned Vacation"])]
        if differences.empty:
            st.success("QGenda matches the annual plan for the selected year.")
        else:
            st.dataframe(differences[["Date", "Planned Call", "Call", "Planned Vacation", "Vacation"]], hide_index=True, use_container_width=True)
    with tabs[4]:
        st.caption("Upload the current Teams doctor schedule workbook. The generated copy updates Call, Vacation, Days used, and adds a QGenda Sync Summary sheet.")
        workbook_file = st.file_uploader("Doctor schedule workbook", type=["xlsx"], key=f"doctor_schedule_workbook_{year}")
        if workbook_file:
            try:
                synced = build_synced_workbook(workbook_file, data, balances, operational)
                st.download_button("Download synchronized doctor schedule", synced, file_name=f"Doc.schedule {year}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            except Exception as exc:
                st.error(f"Workbook synchronization failed: {exc}")


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


def render_editor(extra, save_extra, log_activity=None, qgenda_operational=None):
    store = ensure_store(extra); st.header("Call & Vacation Scheduler"); years = sorted(int(year) for year in store["years"]); top = st.columns(3); year = top[0].selectbox("Calendar year", years, index=len(years)-1, key="editor_schedule_year"); new_year = top[1].number_input("Add year", 2027, 2100, max(years)+1, 1)
    if top[2].button("Add Calendar Year"): store["years"].setdefault(str(int(new_year)), empty_year(int(new_year))); ensure_data(store); save_extra(extra); st.rerun()
    qgenda_operational = qgenda_operational or {}
    qgenda_available = bool(qgenda_operational.get("days"))
    view = st.radio("Schedule view", ["Annual plan", "QGenda operational"], horizontal=True, disabled=not qgenda_available, key=f"schedule_view_{year}")
    if not qgenda_available:
        st.info("No shared QGenda operational schedule is available yet. The annual plan remains active.")
        view = "Annual plan"
    else:
        st.caption(f"QGenda synced {qgenda_operational.get('synced_at', '')} · Coverage {qgenda_operational.get('range_start', '')} through {qgenda_operational.get('range_end', '')}")
    if view == "QGenda operational":
        render_qgenda_operational(store, year, qgenda_operational)
        return
    doctors = roster(store); data = frame(store, year); metrics(data, store, doctors); tabs = st.tabs(["Schedule", "Quick Assign", "Doctors", "Owed Call", "Equity", "Holidays", "Schedule Issues"])
    with tabs[0]:
        vacation_controls(store, year, doctors, lambda: save_extra(extra))
        st.markdown("#### Daily schedule")
        autosave = st.toggle("Auto-save schedule changes", value=True, key=f"schedule_autosave_{year}")
        st.caption("Edit Call, Vacation, or Notes directly. Single-day vacation choices save into the existing vacation balance and conflict system.")
        edited = st.data_editor(
            data[["Date", "Day", "Holiday", "Observances", "Call", "Vacation", "Notes"]],
            hide_index=True,
            use_container_width=True,
            key=f"main_schedule_{year}",
            disabled=["Date", "Day", "Holiday", "Observances"],
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "Call": st.column_config.SelectboxColumn("Call", options=call_choices(store), required=True),
                "Vacation": st.column_config.SelectboxColumn("Vacation", options=vacation_choices(doctors, data["Vacation"].tolist())),
            },
        )
        edited_records = edited.where(pd.notna(edited), "").to_dict("records")
        original_records = data.where(pd.notna(data), "").to_dict("records")
        vacation_pending = any(
            str(original.get("Vacation", "")) != str(updated.get("Vacation", ""))
            for original, updated in zip(original_records, edited_records)
        )
        saved = {str(row["Date"]): row for row in store["years"][str(year)]}
        pending = []
        for row in edited_records:
            key = str(row["Date"])
            new_call = str(row.get("Call") or "Unassigned")
            new_notes = str(row.get("Notes") or "")
            target = saved.get(key)
            if target and (str(target.get("Call") or "Unassigned") != new_call or str(target.get("Notes") or "") != new_notes):
                pending.append((target, new_call, new_notes))
        if (pending or vacation_pending) and autosave:
            for target, new_call, new_notes in pending:
                target["Call"] = new_call
                target["Notes"] = new_notes
            applied, protected = apply_vacation_changes(store, original_records, edited_records) if vacation_pending else (0, 0)
            save_extra(extra)
            if protected:
                st.warning("Bulk or multiple-provider vacations must be edited in Vacation Management.")
            st.success(f"Auto-saved {len(pending) + applied} schedule change(s).")
            st.rerun()
        elif pending or vacation_pending:
            st.warning(f"{len(pending) + (1 if vacation_pending else 0)} unsaved schedule change(s).")
        else:
            st.caption("Saved")
        if st.button("Save Schedule Now", type="primary", disabled=not (pending or vacation_pending)):
            for target, new_call, new_notes in pending:
                target["Call"] = new_call
                target["Notes"] = new_notes
            applied, protected = apply_vacation_changes(store, original_records, edited_records) if vacation_pending else (0, 0)
            save_extra(extra)
            if protected:
                st.warning("Bulk or multiple-provider vacations must be edited in Vacation Management.")
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
