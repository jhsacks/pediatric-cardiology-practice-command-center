import json
from pathlib import Path

import pandas as pd
import streamlit as st

from team_backend import TeamStore

st.set_page_config(
    page_title="Practice Command Center",
    page_icon="❤️",
    layout="wide",
)

SEED = Path(__file__).parent / "practice_snapshot.json"
STATUSES = [
    "Discovery",
    "Planned",
    "In progress",
    "Blocked",
    "On Hold",
    "Backlog",
    "Complete",
    "Cancelled",
]
MONTHS = [
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
]


def users():
    result = []
    for row in st.secrets.get("TEAM_USERS", []):
        try:
            pin = int(row.get("pin", 0))
        except (TypeError, ValueError):
            continue
        if not 1 <= pin <= 100:
            continue
        result.append(
            {
                "name": str(row.get("name", "")).strip(),
                "email": str(row.get("email", "")).strip().casefold(),
                "pin": str(pin),
                "admin": bool(row.get("admin", False)),
            }
        )
    return result


def sign_in():
    if st.session_state.get("practice_user"):
        return st.session_state.practice_user

    roster = users()
    if not roster:
        st.error("TEAM_USERS is missing or contains no PINs from 1 through 100.")
        st.stop()

    st.title("Practice Command Center Sign In")
    name = st.selectbox("Team member", [user["name"] for user in roster])
    pin = st.text_input("PIN number (1-100)", type="password")

    if st.button("Sign in", type="primary"):
        match = next(user for user in roster if user["name"] == name)
        if pin.strip() == match["pin"]:
            st.session_state.practice_user = {
                key: match[key] for key in ["name", "email", "admin"]
            }
            st.rerun()
        st.error("The selected user and PIN did not match.")

    st.caption(
        "Lightweight access only. Do not place PHI or patient identifiers in this app."
    )
    st.stop()


def seed():
    if not SEED.exists():
        return {
            "initiatives": [],
            "decisions": [],
            "roadmap": [],
            "growth": [],
            "clinical_intelligence": {"items": []},
            "rvu_metrics": {},
        }
    return json.loads(SEED.read_text())


def owner_emails(item):
    values = item.get("owner_emails", [])
    if isinstance(values, str):
        values = [value.strip() for value in values.split(",") if value.strip()]
    if not values and item.get("owner_email"):
        values = [item["owner_email"]]
    return {
        str(value).strip().casefold()
        for value in values
        if str(value).strip()
    }


def render_initiative(item, user, store, roster):
    archived_label = "ARCHIVED | " if item.get("archived") else ""
    title = (
        f"{archived_label}{item.get('id', '')} | "
        f"{item.get('name', 'Untitled')} | {item.get('progress', 0)}%"
    )

    with st.expander(title):
        owners = item.get("owners") or (
            [item.get("owner")] if item.get("owner") else []
        )
        owner_text = ", ".join(str(owner) for owner in owners) or "Unassigned"
        st.caption(
            f"Owners: {owner_text} | {item.get('status', '')} | "
            f"{item.get('priority', '')}"
        )

        editable = user["admin"] or user["email"] in owner_emails(item)

        if user["admin"]:
            current = owner_emails(item)
            options = {person["email"]: person["name"] for person in roster}
            selected = st.multiselect(
                "Assigned owners",
                list(options),
                default=[email for email in current if email in options],
                format_func=lambda email: options[email],
                key=f"owners_{item.get('id')}",
            )
            if st.button("Save owners", key=f"save_owners_{item.get('id')}"):
                store.update_initiative(
                    item.get("id"),
                    {
                        "owner_emails": selected,
                        "owners": [options[email] for email in selected],
                    },
                    user,
                )
                st.rerun()

        actions = item.get("next_actions") or (
            [item.get("next_action")] if item.get("next_action") else []
        )

        if editable:
            with st.form(f"edit_{item.get('id')}"):
                status_value = (
                    item.get("status")
                    if item.get("status") in STATUSES
                    else "Planned"
                )
                status = st.selectbox(
                    "Status",
                    STATUSES,
                    index=STATUSES.index(status_value),
                )
                progress = st.slider(
                    "Progress",
                    0,
                    100,
                    int(item.get("progress", 0)),
                )
                action_text = "\n".join(
                    str(action).lstrip("⭐ ") for action in actions
                )
                action_input = st.text_area(
                    "Next actions, one per line",
                    action_text,
                )
                update = st.text_area(
                    "Owner update",
                    item.get("owner_update", ""),
                )

                if st.form_submit_button("Save Initiative Update"):
                    action_list = [
                        f"⭐ {line.strip().lstrip('⭐* ').strip()}"
                        for line in action_input.splitlines()
                        if line.strip()
                    ]
                    store.update_initiative(
                        item.get("id"),
                        {
                            "status": status,
                            "progress": progress,
                            "next_actions": action_list,
                            "next_action": action_list[0] if action_list else "",
                            "owner_update": update.strip(),
                        },
                        user,
                    )
                    st.rerun()
        else:
            st.info(
                "Only an assigned owner or administrator can edit. "
                "Everyone can comment."
            )

        st.markdown("**Comments**")
        for comment in item.get("comments", []):
            st.write(
                f"{comment.get('timestamp_utc', '')} | "
                f"**{comment.get('author_name', '')}**: "
                f"{comment.get('comment', '')}"
            )

        with st.form(f"comment_{item.get('id')}"):
            text = st.text_area("Add a comment")
            if st.form_submit_button("Post Comment") and text.strip():
                store.add_comment(item.get("id"), text, user)
                st.rerun()

        with st.expander("History"):
            history = pd.DataFrame(item.get("history", []))
            if history.empty:
                st.write("No history yet.")
            else:
                st.dataframe(history, hide_index=True, use_container_width=True)


user = sign_in()
roster = users()

service_account = dict(st.secrets["google_service_account"])
drive_settings = st.secrets["google_drive"]
folder_id = str(drive_settings["folder_id"])
team_file_name = st.secrets["google_drive"]["file_name"]

store = TeamStore(
    service_account,
    folder_id,
    team_file_name,
)
data = store.load(seed())

with st.sidebar:
    st.title("❤️ Practice Command Center")
    page = st.radio(
        "Navigate",
        [
            "Home",
            "Initiatives",
            "Decisions",
            "Roadmap",
            "Clinical Intelligence",
            "Practice Growth",
            "Physician RVUs",
        ],
    )
    st.caption(f"Signed in: {user['name']}")
    if st.button("Refresh"):
        st.rerun()
    if st.button("Sign out"):
        st.session_state.pop("practice_user", None)
        st.rerun()

st.title("Pediatric Cardiology Practice Command Center")
st.caption(
    "Initiatives are collaborative. RVUs, growth, decisions, roadmap, "
    "and intelligence are view-only."
)

if page == "Home":
    cols = st.columns(4)
    cols[0].metric("Initiatives", len(data.get("initiatives", [])))
    cols[1].metric("Decisions", len(data.get("decisions", [])))
    cols[2].metric("Roadmap", len(data.get("roadmap", [])))
    cols[3].metric(
        "Intelligence",
        len(data.get("clinical_intelligence", {}).get("items", [])),
    )

    st.subheader("My Initiatives")
    mine = [
        item
        for item in data.get("initiatives", [])
        if user["admin"] or user["email"] in owner_emails(item)
    ]
    if not mine:
        st.info("No initiatives are assigned to this user yet.")
    for item in mine:
        render_initiative(item, user, store, roster)

elif page == "Initiatives":
    show_archived = st.toggle("Show archived", False)
    initiatives = [
        item
        for item in data.get("initiatives", [])
        if show_archived or not item.get("archived")
    ]
    if not initiatives:
        st.info("No practice initiatives are available.")
    for item in initiatives:
        render_initiative(item, user, store, roster)

elif page == "Decisions":
    frame = pd.DataFrame(data.get("decisions", []))
    if frame.empty:
        st.info("No practice decisions.")
    else:
        st.dataframe(frame, hide_index=True, use_container_width=True)

elif page == "Roadmap":
    frame = pd.DataFrame(data.get("roadmap", []))
    if frame.empty:
        st.info("No roadmap items.")
    else:
        st.dataframe(frame, hide_index=True, use_container_width=True)

elif page == "Clinical Intelligence":
    items = data.get("clinical_intelligence", {}).get("items", [])
    if not items:
        st.info("No Clinical Intelligence items.")
    for item in items:
        with st.expander(item.get("title", "Untitled")):
            st.write(item.get("summary", ""))
            if item.get("key_findings"):
                st.write(f"**Key findings:** {item['key_findings']}")
            if item.get("practice_relevance"):
                st.write(
                    f"**Practice relevance:** {item['practice_relevance']}"
                )
            if item.get("link"):
                st.link_button("Open source", item["link"])

elif page == "Practice Growth":
    frame = pd.DataFrame(data.get("growth", []))
    if frame.empty:
        st.info("No growth data.")
    else:
        st.dataframe(frame, hide_index=True, use_container_width=True)

elif page == "Physician RVUs":
    rvu = data.get("rvu_metrics", {})
    historical = pd.DataFrame(rvu.get("historical_totals", []))
    physician = pd.DataFrame(rvu.get("physician_rows", []))

    tabs = st.tabs(["Historical Totals", "Physician Data", "Graphs"])

    with tabs[0]:
        if historical.empty:
            st.info("No historical totals.")
        else:
            st.dataframe(
                historical,
                hide_index=True,
                use_container_width=True,
            )

    with tabs[1]:
        if physician.empty:
            st.info("No physician data.")
        else:
            st.dataframe(
                physician,
                hide_index=True,
                use_container_width=True,
            )

    with tabs[2]:
        source = historical if not historical.empty else physician
        if source.empty or "Fiscal Year" not in source.columns:
            st.info("No graphable data.")
        else:
            months = [month for month in MONTHS if month in source.columns]
            if not months:
                st.info("No monthly RVU columns are available.")
            else:
                long = source.melt(
                    id_vars=["Fiscal Year"],
                    value_vars=months,
                    value_name="RVUs",
                    var_name="Month",
                ).dropna(subset=["RVUs"])
                long["Order"] = long["Month"].map(
                    {month: index for index, month in enumerate(months)}
                )
                chart = long.pivot_table(
                    index="Order",
                    columns="Fiscal Year",
                    values="RVUs",
                    aggfunc="sum",
                )
                chart.index = [months[int(index)] for index in chart.index]
                st.line_chart(chart)
