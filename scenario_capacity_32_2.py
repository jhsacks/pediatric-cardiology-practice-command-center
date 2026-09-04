import streamlit as st


def safe_number(value, default=0.0):
    try:
        number = float(value)
        return number if number == number else default
    except (TypeError, ValueError, OverflowError):
        return default


def schedule_key(user, kind, scenario_id):
    if kind == "shared":
        return f"shared:{scenario_id}"
    return f"personal:{user}:{scenario_id}"


def default_available_days(extra):
    physicians = [
        row for row in extra.get("collaboration", {}).get("users", [])
        if row.get("active", True)
        and "physician" in str(row.get("role", "")).lower()
    ]
    return (len(physicians) if physicians else 4) * 4.0


def capacity_values(extra, allocation, user, kind, scenario_id):
    planning = extra.setdefault("strategic_planning_12", {})
    saved = planning.setdefault("workforce_schedules", {}).get(
        schedule_key(user, kind, scenario_id), {}
    )
    roster = saved.get("roster", [])
    if roster:
        available = sum(
            safe_number(row.get("Available Days/Week"))
            for row in roster
            if bool(row.get("Active", True))
        )
    else:
        available = default_available_days(extra)

    utilized = sum(safe_number(value) for value in (allocation or {}).values())
    remaining = available - utilized
    additional_fte = max(0.0, -remaining / 4.0)
    return available, utilized, remaining, additional_fte


def capacity_signal(remaining):
    if remaining >= 0.5:
        return "🟢 Capacity available"
    if remaining >= -0.5:
        return "🟡 Near balance"
    return "🔴 Capacity shortfall"


def render_live_capacity(extra, allocation, user, kind, scenario_id):
    available, utilized, remaining, additional_fte = capacity_values(
        extra, allocation, user, kind, scenario_id
    )
    columns = st.columns(4)
    columns[0].metric("Provider Days Available", f"{available:.2f}")
    columns[1].metric("Provider Days Utilized", f"{utilized:.2f}")
    columns[2].metric("Provider Days Remaining", f"{remaining:+.2f}")
    columns[3].metric("Additional Physician Equivalent", f"{additional_fte:.2f}")
    st.markdown(f"### {capacity_signal(remaining)}")
    if remaining < -0.5:
        st.caption(
            "Recruitment planning signal: desired clinic days exceed the active "
            "provider days saved for this scenario."
        )
