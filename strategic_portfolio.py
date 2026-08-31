import pandas as pd
import streamlit as st

PROGRESS = {
    "Not Started": 0,
    "Open": 10,
    "Pending Data": 25,
    "Pending Leadership": 40,
    "In Progress": 50,
    "Waiting": 50,
    "Blocked": 35,
    "Approved": 75,
    "Implemented": 100,
    "Completed": 100,
    "Archived": 100,
    "Declined": 100,
}


def _share(item):
    value = str(item.get("sharing", item.get("visibility", "Everyone")))
    return {
        "Shared": "Everyone",
        "Practice": "Everyone",
        "Private": "Only me",
    }.get(value, value)


def _view(item, user):
    sharing = _share(item)
    return (
        sharing == "Everyone"
        or item.get("owner") == user
        or item.get("creator", item.get("created_by")) == user
        or (
            sharing == "Selected people"
            and user in item.get("shared_with", [])
        )
    )


def _user(extra, current=None, widget_key="portfolio_user"):
    names = [
        row.get("name")
        for row in extra.get("collaboration", {}).get("users", [])
        if row.get("active", True) and row.get("name")
    ]

    if current in names:
        return current

    if not names:
        return ""

    return st.selectbox(
        "Portfolio view for",
        names,
        key=widget_key,
    )


def render_strategic_portfolio(extra, current_user=None):
    current_name = (
        (current_user or {}).get("name")
        if current_user
        else None
    )
    user = _user(
        extra,
        current_name,
        widget_key="portfolio_user_main",
    )

    rows = []
    collaboration = extra.get("collaboration", {})

    for kind, bucket in [
        ("Initiative", "initiatives"),
        ("Decision", "decisions"),
        ("Growth", "practice_growth"),
    ]:
        for item in collaboration.get(bucket, []):
            if not _view(item, user):
                continue

            status = str(item.get("status", "Not Started"))
            rows.append(
                {
                    "Type": kind,
                    "Title": item.get("title", "Untitled"),
                    "Owner": item.get("owner", ""),
                    "Category": item.get("category", "Other"),
                    "Strategic Goal": (
                        item.get("strategic_goal") or "Unassigned"
                    ),
                    "Status": status,
                    "Priority": item.get("priority", "Medium"),
                    "Deadline": item.get(
                        "deadline",
                        item.get("target_date", ""),
                    ),
                    "Progress %": PROGRESS.get(status, 0),
                }
            )

    st.subheader("Strategic Portfolio")
    st.caption(
        "Calculated from accessible Initiatives, Decisions, "
        "and Practice Growth records."
    )

    if not rows:
        st.info("No accessible portfolio records yet.")
        return

    frame = pd.DataFrame(rows)
    active = frame[~frame["Status"].isin(["Archived", "Declined"])]

    columns = st.columns(5)
    columns[0].metric("Active Work", len(active))
    columns[1].metric(
        "Initiatives",
        int((active["Type"] == "Initiative").sum()),
    )
    columns[2].metric(
        "Open Decisions",
        int((active["Type"] == "Decision").sum()),
    )
    columns[3].metric(
        "Growth Items",
        int((active["Type"] == "Growth").sum()),
    )
    columns[4].metric(
        "Average Progress",
        f"{active['Progress %'].mean():.0f}%" if len(active) else "0%",
    )

    st.markdown("#### Progress by Portfolio")
    progress = (
        active.groupby("Category", as_index=False)["Progress %"]
        .mean()
        .set_index("Category")
    )
    st.bar_chart(progress)

    st.markdown("#### Portfolio Work")
    st.dataframe(active, hide_index=True, use_container_width=True)


def render_growth_planner(extra, current_user=None):
    current_name = (
        (current_user or {}).get("name")
        if current_user
        else None
    )
    user = _user(
        extra,
        current_name,
        widget_key="portfolio_user_growth",
    )

    rows = []
    collaboration = extra.get("collaboration", {})

    for item in collaboration.get("practice_growth", []):
        if not _view(item, user):
            continue

        rows.append(
            {
                "Opportunity": item.get("title", "Untitled"),
                "Owner": item.get("owner", ""),
                "Site": item.get("site", "System-wide"),
                "Priority": item.get("priority", "Medium"),
                "Status": item.get("status", "Not Started"),
                "Deadline": item.get("deadline", ""),
            }
        )

    st.subheader("Practice Growth Planner")

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No accessible Practice Growth records yet.")
