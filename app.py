import pandas as pd
import streamlit as st

from team_backend import TeamStore

st.set_page_config(page_title="Practice Command Center", page_icon="❤️", layout="wide")

STATUSES = [
    "Discovery", "Planned", "In progress", "Blocked",
    "On Hold", "Backlog", "Complete", "Cancelled",
]
MONTHS = [
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
]


def users():
    roster = []
    for row in st.secrets.get("TEAM_USERS", []):
        try:
            pin = int(row.get("pin", 0))
        except (TypeError, ValueError):
            continue
        if 1 <= pin <= 100:
            roster.append(
                {
                    "name": str(row.get("name", "")).strip(),
                    "email": str(row.get("email", "")).strip().casefold(),
                    "pin": str(pin),
                    "admin": bool(row.get("admin", False)),
                }
            )
    return roster


def sign_in():
    if st.session_state.get("practice_user"):
        return st.session_state.practice_user
    roster = users()
    if not roster:
        st.error("TEAM_USERS is missing or contains no PINs from 1 through 100.")
        st.stop()
    st.title("Practice Command Center Sign In")
    name = st.selectbox("Team member", [person["name"] for person in roster])
    pin = st.text_input("PIN number (1-100)", type="password")
    if st.button("Sign in", type="primary"):
        match = next(person for person in roster if person["name"] == name)
        if pin.strip() == match["pin"]:
            st.session_state.practice_user = {
                key: match[key] for key in ["name", "email", "admin"]
            }
            st.rerun()
        st.error("The selected user and PIN did not match.")
    st.caption("Do not place PHI or patient identifiers in this app.")
    st.stop()


def owner_emails(item):
    values = item.get("owner_emails", [])
    if isinstance(values, str):
        values = [value.strip() for value in values.split(",") if value.strip()]
    if not values and item.get("owner_email"):
        values = [item["owner_email"]]
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def render_initiative(item, user, store, roster):
    archived = "ARCHIVED | " if item.get("archived") else ""
    with st.expander(
        f"{archived}{item.get('id', '')} | "
        f"{item.get('name', 'Untitled')} | {item.get('progress', 0)}%"
    ):
        names = item.get("owners") or ([item.get("owner")] if item.get("owner") else [])
        st.caption(
            f"Owners: {', '.join(str(name) for name in names) or 'Unassigned'} | "
            f"{item.get('status', '')} | {item.get('priority', '')}"
        )
        editable = user["admin"] or user["email"] in owner_emails(item)

        if user["admin"]:
            options = {person["email"]: person["name"] for person in roster}
            selected = st.multiselect(
                "Assigned owners",
                list(options),
                default=[email for email in owner_emails(item) if email in options],
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
                current_status = item.get("status") if item.get("status") in STATUSES else "Planned"
                status = st.selectbox(
                    "Status",
                    STATUSES,
                    index=STATUSES.index(current_status),
                )
                progress = st.slider("Progress", 0, 100, int(item.get("progress", 0)))
                next_actions = st.text_area(
                    "Next actions, one per line",
                    "\n".join(str(action).lstrip("⭐ ") for action in actions),
                )
                owner_update = st.text_area("Owner update", item.get("owner_update", ""))
                if st.form_submit_button("Save Initiative Update"):
                    action_list = [
                        f"⭐ {line.strip().lstrip('⭐* ').strip()}"
                        for line in next_actions.splitlines()
                        if line.strip()
                    ]
                    store.update_initiative(
                        item.get("id"),
                        {
                            "status": status,
                            "progress": progress,
                            "next_actions": action_list,
                            "next_action": action_list[0] if action_list else "",
                            "owner_update": owner_update.strip(),
                        },
                        user,
                    )
                    st.rerun()
        else:
            st.info("Only an assigned owner or administrator can edit. Everyone can comment.")

        st.markdown("**Comments**")
        for comment in item.get("comments", []):
            st.write(
                f"{comment.get('timestamp_utc', '')} | "
                f"**{comment.get('author_name', '')}**: {comment.get('comment', '')}"
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


def practice_total_rows(rvu):
    historical = pd.DataFrame(rvu.get("historical_totals", []))
    physician = pd.DataFrame(rvu.get("physician_rows", []))
    if physician.empty:
        return historical
    for month in MONTHS:
        if month not in physician.columns:
            physician[month] = None
        physician[month] = pd.to_numeric(physician[month], errors="coerce")
    calculated = physician.groupby("Fiscal Year", as_index=False)[MONTHS].sum(min_count=1)
    calculated["Source"] = "Calculated from physician entries"
    if historical.empty:
        return calculated
    historical["Source"] = "Imported historical total"
    calculated_years = set(calculated["Fiscal Year"].astype(str))
    historical = historical[~historical["Fiscal Year"].astype(str).isin(calculated_years)]
    return pd.concat([historical, calculated], ignore_index=True, sort=False)


user = sign_in()
roster = users()
service_account = dict(st.secrets["google_service_account"])
drive_settings = st.secrets["google_drive"]
store = TeamStore(
    service_account,
    str(drive_settings["folder_id"]),
    str(drive_settings["file_name"]),
)
raw_data = store.load()
initiatives = TeamStore.initiatives(raw_data)
extra = TeamStore.extras(raw_data)

with st.sidebar:
    st.title("❤️ Practice Command Center")
    page = st.radio(
        "Navigate",
        [
            "Home", "Initiatives", "Decisions", "Roadmap",
            "Clinical Intelligence", "Practice Growth", "Physician RVUs",
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
    cols[0].metric("Initiatives", len(initiatives))
    cols[1].metric("Decisions", len(extra.get("decisions", [])))
    cols[2].metric("Roadmap", len(extra.get("roadmap", [])))
    cols[3].metric(
        "Intelligence",
        len(extra.get("clinical_intelligence", {}).get("items", [])),
    )
    st.subheader("My Initiatives")
    mine = [
        item for item in initiatives
        if user["admin"] or user["email"] in owner_emails(item)
    ]
    if not mine:
        st.info("No initiatives are assigned to this user yet.")
    for item in mine:
        render_initiative(item, user, store, roster)

elif page == "Initiatives":
    show_archived = st.toggle("Show archived", False)
    visible = [
        item for item in initiatives
        if show_archived or not item.get("archived")
    ]
    for item in visible:
        render_initiative(item, user, store, roster)
    if not visible:
        st.info("No practice initiatives are available.")

elif page == "Decisions":
    frame = pd.DataFrame(extra.get("decisions", []))
    st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No practice decisions.")

elif page == "Roadmap":
    frame = pd.DataFrame(extra.get("roadmap", []))
    st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No roadmap items.")

elif page == "Clinical Intelligence":
    items = extra.get("clinical_intelligence", {}).get("items", [])
    practice_items = [
        item for item in items
        if str(item.get("sharing", "Practice")) in ["Practice", "Shared"]
    ]
    for item in practice_items:
        with st.expander(item.get("title", "Untitled")):
            st.write(item.get("summary", ""))
            if item.get("key_findings"):
                st.write(f"**Key findings:** {item['key_findings']}")
            if item.get("practice_relevance"):
                st.write(f"**Practice relevance:** {item['practice_relevance']}")
            if item.get("link"):
                st.link_button("Open source", item["link"])
    if not practice_items:
        st.info("No practice-visible Clinical Intelligence items.")

elif page == "Practice Growth":
    frame = pd.DataFrame(extra.get("growth", []))
    st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No growth data.")

elif page == "Physician RVUs":
    rvu = extra.get("rvu_metrics", {})
    historical = pd.DataFrame(rvu.get("historical_totals", []))
    physician = pd.DataFrame(rvu.get("physician_rows", []))
    totals = practice_total_rows(rvu)
    tabs = st.tabs(["Practice Totals", "Physician Data", "Graphs"])
    with tabs[0]:
        st.dataframe(totals, hide_index=True, use_container_width=True) if not totals.empty else st.info("No RVU totals.")
    with tabs[1]:
        st.dataframe(physician, hide_index=True, use_container_width=True) if not physician.empty else st.info("No physician data.")
    with tabs[2]:
        if totals.empty or "Fiscal Year" not in totals.columns:
            st.info("No graphable RVU data.")
        else:
            months = [month for month in MONTHS if month in totals.columns]
            long = totals.melt(
                id_vars=["Fiscal Year"],
                value_vars=months,
                var_name="Month",
                value_name="RVUs",
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
