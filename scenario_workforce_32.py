from copy import deepcopy
from uuid import uuid4

import pandas as pd
import streamlit as st

WEEKDAY_SLOTS = [
    "Monday AM", "Monday PM", "Tuesday AM", "Tuesday PM",
    "Wednesday AM", "Wednesday PM", "Thursday AM", "Thursday PM",
    "Friday AM", "Friday PM", "Sunday AM", "Sunday PM",
]
DEFAULT_HOSPITALS = [
    "Cobb", "Kennestone", "Paulding", "Acworth",
    "North Fulton", "Douglas", "West Georgia",
]


def _planning(extra):
    p = extra.setdefault("strategic_planning_12", {})
    p.setdefault("workforce_schedules", {})
    p.setdefault("schedule_hospitals", list(DEFAULT_HOSPITALS))
    p.setdefault("personal_scenarios", {})
    p.setdefault("scenarios", {})
    return p


def _user(current_user):
    return (current_user or {}).get("name") or "Jeffrey Sacks"


def _scenario_options(p, user):
    options = []
    for name in p.get("scenarios", {}):
        options.append((f"Shared: {name}", "shared", name, None))
    for item in p.get("personal_scenarios", {}).get(user, []):
        options.append((f"My: {item.get('name', 'Untitled')}", "personal", item.get("id"), item))
    return options


def _allocation(p, kind, key, item):
    if kind == "shared":
        value = p.get("scenarios", {}).get(key, {})
        return deepcopy(value) if isinstance(value, dict) else {}
    value = (item or {}).get("allocation", {})
    return deepcopy(value) if isinstance(value, dict) else {}


def _schedule_key(user, kind, key):
    return f"{kind}:{key}" if kind == "shared" else f"personal:{user}:{key}"


def _safe(value, default=0.0):
    try:
        value = float(value)
        return value if value == value else default
    except (TypeError, ValueError, OverflowError):
        return default


def _default_roster(extra):
    names = [
        str(x.get("name")) for x in extra.get("collaboration", {}).get("users", [])
        if x.get("active", True) and str(x.get("role", "")).lower().find("physician") >= 0
    ]
    if not names:
        names = ["Jeffrey Sacks", "Luv Makadia", "Jonathan Yaari", "Mohammad Khan"]
    return [{"Physician": name, "Available Days/Week": 4.0, "Active": True} for name in names]


def _default_assignments():
    return [{
        "Assignment ID": "ASN-" + uuid4().hex[:8],
        "Slot": "Monday AM",
        "Physician": "",
        "Location": "",
        "Hospitals Covered": "",
        "Frequency": "Weekly",
    }]


def _weekly_equivalent(row):
    frequency = str(row.get("Frequency", "Weekly"))
    slot_days = 0.5
    if frequency == "Monthly":
        return slot_days / 4.0
    if frequency == "Twice Monthly":
        return slot_days / 2.0
    return slot_days


def _metrics(roster, assignments, allocation):
    available = sum(
        _safe(row.get("Available Days/Week"))
        for row in roster if bool(row.get("Active", True))
    )
    assigned = sum(
        _weekly_equivalent(row)
        for row in assignments
        if str(row.get("Physician", "")).strip() and str(row.get("Location", "")).strip()
    )
    desired = sum(_safe(value) for value in allocation.values())
    workforce_gap = available - desired
    schedule_gap = assigned - desired
    return available, assigned, desired, workforce_gap, schedule_gap


def _signal(gap):
    if gap >= 0.5:
        return "🟢 Capacity available"
    if gap >= -0.5:
        return "🟡 Near balance"
    return "🔴 Capacity shortfall"


def _site_summary(assignments, allocation):
    sites = sorted(set(allocation) | {
        str(row.get("Location", "")).strip() for row in assignments
        if str(row.get("Location", "")).strip()
    })
    rows = []
    for site in sites:
        assigned = sum(
            _weekly_equivalent(row) for row in assignments
            if str(row.get("Location", "")).strip() == site
            and str(row.get("Physician", "")).strip()
        )
        desired = _safe(allocation.get(site, 0))
        rows.append({
            "Location": site,
            "Desired Days/Week": round(desired, 3),
            "Scheduled Days/Week": round(assigned, 3),
            "Over / (Short) Days": round(assigned - desired, 3),
            "Signal": _signal(assigned - desired),
        })
    rows.append({
        "Location": "TOTAL",
        "Desired Days/Week": round(sum(_safe(v) for v in allocation.values()), 3),
        "Scheduled Days/Week": round(sum(_weekly_equivalent(r) for r in assignments if str(r.get("Physician", "")).strip() and str(r.get("Location", "")).strip()), 3),
        "Over / (Short) Days": round(sum(_weekly_equivalent(r) for r in assignments if str(r.get("Physician", "")).strip() and str(r.get("Location", "")).strip()) - sum(_safe(v) for v in allocation.values()), 3),
        "Signal": _signal(sum(_weekly_equivalent(r) for r in assignments if str(r.get("Physician", "")).strip() and str(r.get("Location", "")).strip()) - sum(_safe(v) for v in allocation.values())),
    })
    return rows


def render_scenario_workforce(extra, save_extra, current_user=None, executive=False):
    p = _planning(extra)
    user = _user(current_user)
    st.subheader("Physician Workforce & Schedule")
    st.caption("Build a physician roster and Monday-Friday plus monthly Sunday schedule for either a Shared Scenario or My Scenario. Assignments use half-day blocks; multiple physicians may be assigned to the same location and slot.")

    options = _scenario_options(p, user)
    if not options:
        st.info("Create a Shared Scenario or My Scenario first.")
        return
    labels = [x[0] for x in options]
    selected = st.selectbox("Scenario", labels, key=f"workforce32_scenario_{user}")
    label, kind, scenario_id, personal_item = options[labels.index(selected)]
    allocation = _allocation(p, kind, scenario_id, personal_item)
    key = _schedule_key(user, kind, scenario_id)
    store = p["workforce_schedules"].setdefault(key, {
        "roster": _default_roster(extra),
        "assignments": _default_assignments(),
        "owner": user,
        "scenario_label": label,
    })

    st.markdown("### Physician roster")
    roster = st.data_editor(
        pd.DataFrame(store.get("roster", [])),
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key=f"workforce32_roster_{key}",
        column_config={
            "Available Days/Week": st.column_config.NumberColumn(min_value=0.0, max_value=7.0, step=0.25),
            "Active": st.column_config.CheckboxColumn(),
        },
    )
    roster_rows = roster.where(pd.notna(roster), "").to_dict("records")
    physician_names = [str(row.get("Physician", "")).strip() for row in roster_rows if str(row.get("Physician", "")).strip() and bool(row.get("Active", True))]

    st.markdown("### Hospital coverage list")
    hospitals = st.data_editor(
        pd.DataFrame({"Hospital": p.get("schedule_hospitals", DEFAULT_HOSPITALS)}),
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key="workforce32_hospitals",
    )
    hospital_names = [str(v).strip() for v in hospitals["Hospital"].tolist() if str(v).strip()]

    st.markdown("### Weekly schedule")
    st.caption("Use one row per physician assignment. Add multiple rows for multiple physicians at the same location. Griffin Sunday can use Monthly frequency, where one half-day per month equals 0.125 average days/week.")
    location_options = sorted(set(allocation.keys()) | {"Barrett", "Smyrna", "Douglasville", "Paulding", "Woodstock", "Acworth", "Avalon", "WGA", "Griffin", "LaGrange"})
    assignments = st.data_editor(
        pd.DataFrame(store.get("assignments", _default_assignments())),
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key=f"workforce32_assignments_{key}",
        column_config={
            "Assignment ID": None,
            "Slot": st.column_config.SelectboxColumn(options=WEEKDAY_SLOTS, required=True),
            "Physician": st.column_config.SelectboxColumn(options=physician_names),
            "Location": st.column_config.SelectboxColumn(options=location_options),
            "Hospitals Covered": st.column_config.TextColumn(help="Enter one or more hospitals separated by commas. Available list: " + ", ".join(hospital_names)),
            "Frequency": st.column_config.SelectboxColumn(options=["Weekly", "Twice Monthly", "Monthly"], required=True),
        },
    )
    assignment_rows = assignments.where(pd.notna(assignments), "").to_dict("records")
    for row in assignment_rows:
        row.setdefault("Assignment ID", "ASN-" + uuid4().hex[:8])

    available, assigned, desired, workforce_gap, schedule_gap = _metrics(roster_rows, assignment_rows, allocation)
    st.markdown("### Scenario capacity")
    cols = st.columns(5)
    cols[0].metric("Physician Days Available", f"{available:.2f}")
    cols[1].metric("Days Scheduled", f"{assigned:.2f}")
    cols[2].metric("Scenario Days Desired", f"{desired:.2f}")
    cols[3].metric("Available vs Desired", f"{workforce_gap:+.2f}")
    cols[4].metric("Scheduled vs Desired", f"{schedule_gap:+.2f}")
    st.markdown(f"## {_signal(workforce_gap)}")

    st.markdown("### Location day reconciliation")
    st.dataframe(pd.DataFrame(_site_summary(assignment_rows, allocation)), hide_index=True, use_container_width=True)

    physician_summary = []
    for name in physician_names:
        used = sum(_weekly_equivalent(row) for row in assignment_rows if str(row.get("Physician", "")).strip() == name and str(row.get("Location", "")).strip())
        available_days = next((_safe(row.get("Available Days/Week")) for row in roster_rows if str(row.get("Physician", "")).strip() == name), 0.0)
        physician_summary.append({"Physician": name, "Available Days/Week": available_days, "Scheduled Days/Week": round(used, 3), "Remaining / (Over)": round(available_days - used, 3)})
    st.markdown("### Physician utilization")
    st.dataframe(pd.DataFrame(physician_summary), hide_index=True, use_container_width=True)

    if st.button("Save Workforce & Schedule", type="primary", key=f"workforce32_save_{key}"):
        store["roster"] = roster_rows
        store["assignments"] = assignment_rows
        store["scenario_label"] = label
        p["schedule_hospitals"] = hospital_names
        save_extra(extra)
        st.success("Scenario workforce and schedule saved.")
