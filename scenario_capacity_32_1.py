import streamlit as st


def safe_number(value, default=0.0):
    try:
        number = float(value)
        return number if number == number else default
    except (TypeError, ValueError, OverflowError):
        return default


def scenario_schedule_key(user, kind, scenario_id):
    if kind == "shared":
        return f"shared:{scenario_id}"
    return f"personal:{user}:{scenario_id}"


def default_provider_days(extra):
    physicians = [
        row for row in extra.get("collaboration", {}).get("users", [])
        if row.get("active", True) and "physician" in str(row.get("role", "")).lower()
    ]
    count = len(physicians) if physicians else 4
    return count * 4.0


def capacity_values(extra, allocation, user, kind, scenario_id):
    planning = extra.setdefault("strategic_planning_12", {})
    schedules = planning.setdefault("workforce_schedules", {})
    key = scenario_schedule_key(user, kind, scenario_id)
    schedule = schedules.get(key, {})
    roster = schedule.get("roster", [])

    if roster:
        available = sum(
            safe_number(row.get("Available Days/Week"))
            for row in roster
            if bool(row.get("Active", True))
        )
    else:
        available = default_provider_days(extra)

    utilized = sum(safe_number(value) for value in (allocation or {}).values())
    remaining = available - utilized
    physician_equivalent = max(0.0, -remaining / 4.0)
    return available, utilized, remaining, physician_equivalent


def signal(remaining):
    if remaining >= 0.5:
        return "🟢 Capacity available"
    if remaining >= -0.5:
        return "🟡 Near balance"
    return "🔴 Capacity shortfall"


def render_capacity_summary(extra, allocation, user, kind, scenario_id, key_suffix=""):
    available, utilized, remaining, physician_equivalent = capacity_values(
        extra, allocation, user, kind, scenario_id
    )
    columns = st.columns(4)
    columns[0].metric("Provider Days Available", f"{available:.2f}")
    columns[1].metric("Provider Days Utilized", f"{utilized:.2f}")
    columns[2].metric("Provider Days Remaining", f"{remaining:+.2f}")
    columns[3].metric(
        "Additional Physician Equivalent",
        f"{physician_equivalent:.2f}" if physician_equivalent > 0 else "0.00",
    )
    st.markdown(f"### {signal(remaining)}")
    if remaining < -0.5:
        st.caption(
            "Recruitment planning signal: this scenario requires more provider days "
            "than the saved active physician roster supplies."
        )
    return {
        "available": available,
        "utilized": utilized,
        "remaining": remaining,
        "physician_equivalent": physician_equivalent,
        "signal": signal(remaining),
    }
