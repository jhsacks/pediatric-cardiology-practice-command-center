import hashlib
import hmac
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from team_backend import TeamStore

st.set_page_config(page_title="Pediatric Cardiology Practice Command Center", page_icon="❤️", layout="wide")
SEED_FILE = Path(__file__).parent / "practice_snapshot.json"
STATUSES = ["Discovery", "Planned", "In progress", "Blocked", "On Hold", "Backlog", "Complete", "Cancelled"]


def secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return default


def team_users():
    raw = secret("TEAM_USERS", [])
    users = []
    for user in raw:
        users.append({
            "name": str(user.get("name", "")).strip(),
            "email": str(user.get("email", "")).strip().casefold(),
            "pin_hash": str(user.get("pin_hash", "")).strip().casefold(),
            "admin": bool(user.get("admin", False)),
        })
    return users


def pin_hash(pin):
    return hashlib.sha256(str(pin).encode("utf-8")).hexdigest()


def login():
    if st.session_state.get("team_user"):
        return st.session_state.team_user
    users = team_users()
    if not users:
        st.error("TEAM_USERS is missing from Streamlit Secrets.")
        st.stop()
    st.title("Practice Command Center Sign In")
    names = [u["name"] for u in users]
    selected = st.selectbox("Team member", names)
    pin = st.text_input("PIN", type="password")
    if st.button("Sign in", type="primary"):
        user = next(u for u in users if u["name"] == selected)
        supplied = pin_hash(pin)
        if user["pin_hash"] and hmac.compare_digest(supplied, user["pin_hash"]):
            st.session_state.team_user = {"name": user["name"], "email": user["email"], "admin": user["admin"]}
            st.rerun()
        st.error("The selected user and PIN did not match.")
    st.caption("This is lightweight app-level access control. Do not use it for PHI or patient-identifiable information.")
    st.stop()


def load_seed():
    if not SEED_FILE.exists():
        return {"initiatives": [], "decisions": [], "roadmap": [], "growth": [], "clinical_intelligence": {"items": []}, "rvu_metrics": {}}
    return json.loads(SEED_FILE.read_text())


def owner_emails(item):
    values = item.get("owner_emails", [])
    if isinstance(values, str):
        values = [x.strip() for x in values.split(",") if x.strip()]
    if not values and item.get("owner_email"):
        values = [item.get("owner_email")]
    return {str(x).strip().casefold() for x in values if str(x).strip()}


def can_edit(item, user):
    return bool(user.get("admin")) or user["email"] in owner_emails(item)


def display_owners(item):
    names = item.get("owners", [])
    if isinstance(names, str):
        names = [x.strip() for x in names.split(",") if x.strip()]
    if not names and item.get("owner"):
        names = [item.get("owner")]
    return ", ".join(str(x) for x in names if str(x).strip()) or "Unassigned"


def render_initiative(item, user, store):
    archived = bool(item.get("archived", False))
    with st.expander(f"{'ARCHIVED | ' if archived else ''}{item.get('id','')} | {item.get('name','Untitled')} | {item.get('progress',0)}%"):
        st.caption(f"Owners: {display_owners(item)} | {item.get('status','')} | {item.get('priority','')}")
        actions = item.get("next_actions") or ([item.get("next_action")] if item.get("next_action") else [])
        if actions:
            st.markdown("**Next actions**")
            for action in actions:
                st.write(str(action))
        if can_edit(item, user):
            with st.form(f"edit_{item.get('id')}"):
                status_value = item.get("status") if item.get("status") in STATUSES else "Planned"
                status = st.selectbox("Status", STATUSES, index=STATUSES.index(status_value))
                progress = st.slider("Progress", 0, 100, int(item.get("progress", 0)))
                action_text = "\n".join(str(x).lstrip("⭐ ") for x in actions)
                next_actions = st.text_area("Next actions, one per line", action_text)
                owner_update = st.text_area("Owner update", item.get("owner_update", ""))
                if st.form_submit_button("Save Initiative Update"):
                    action_list = [f"⭐ {line.strip().lstrip('⭐* ').strip()}" for line in next_actions.splitlines() if line.strip()]
                    store.update_initiative(item.get("id"), {
                        "status": status,
                        "progress": progress,
                        "next_actions": action_list,
                        "next_action": action_list[0] if action_list else "",
                        "owner_update": owner_update.strip(),
                    }, user)
                    st.rerun()
        else:
            st.info("Only an assigned owner or administrator can change this initiative. Every signed-in team member can comment.")
        st.markdown("**Comments**")
        comments = item.get("comments", [])
        for comment in comments:
            author = comment.get("author_name") or comment.get("author_email")
            st.write(f"{comment.get('timestamp_utc','')} | **{author}**: {comment.get('comment','')}")
        with st.form(f"comment_{item.get('id')}"):
            comment = st.text_area("Add a comment")
            if st.form_submit_button("Post Comment") and comment.strip():
                store.add_comment(item.get("id"), comment, user)
                st.rerun()
        with st.expander("History"):
            history = item.get("history", [])
            if history:
                st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
            else:
                st.write("No change history yet.")


user = login()
service_account = secret("GOOGLE_SERVICE_ACCOUNT_JSON")
folder_id = secret("GOOGLE_DRIVE_FOLDER_ID", "")
file_name = secret("PRACTICE_TEAM_FILE_NAME", "practice_team_data.json")
if not service_account or not folder_id:
    st.error("Google Drive secrets are incomplete.")
    st.stop()
store = TeamStore(service_account, folder_id, file_name)
data = store.load(load_seed())

with st.sidebar:
    st.title("❤️ Practice Command Center")
    page = st.radio("Navigate", ["Home", "Initiatives", "Decisions", "Roadmap", "Clinical Intelligence", "Practice Growth", "Physician RVUs"])
    st.caption(f"Signed in: {user['name']}")
    if st.button("Refresh data"):
        st.rerun()
    if st.button("Sign out"):
        st.session_state.pop("team_user", None)
        st.rerun()

st.title("Pediatric Cardiology Practice Command Center")
st.caption("Collaborative initiatives. RVUs, metrics, decisions, roadmap, and intelligence are view-only.")

if page == "Home":
    cols = st.columns(5)
    cols[0].metric("Initiatives", len(data.get("initiatives", [])))
    cols[1].metric("Decisions", len(data.get("decisions", [])))
    cols[2].metric("Roadmap", len(data.get("roadmap", [])))
    cols[3].metric("Intelligence", len(data.get("clinical_intelligence", {}).get("items", [])))
    cols[4].metric("Growth rows", len(data.get("growth", [])))
    st.subheader("My Initiatives")
    mine = [x for x in data.get("initiatives", []) if user["email"] in owner_emails(x)]
    for item in mine:
        render_initiative(item, user, store)
    if not mine:
        st.info("No initiatives are assigned to this user yet.")
elif page == "Initiatives":
    show_archived = st.toggle("Show archived initiatives", value=False)
    initiatives = [x for x in data.get("initiatives", []) if show_archived or not x.get("archived", False)]
    for item in initiatives:
        render_initiative(item, user, store)
elif page == "Decisions":
    frame = pd.DataFrame(data.get("decisions", []))
    st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No practice decisions.")
elif page == "Roadmap":
    frame = pd.DataFrame(data.get("roadmap", []))
    st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No practice roadmap items.")
elif page == "Clinical Intelligence":
    for item in data.get("clinical_intelligence", {}).get("items", []):
        with st.expander(f"{item.get('content_type','')} | {item.get('title','Untitled')}"):
            st.write(item.get("summary", ""))
            if item.get("key_findings"):
                st.write(f"**Key findings:** {item['key_findings']}")
            if item.get("practice_relevance"):
                st.write(f"**Practice relevance:** {item['practice_relevance']}")
            if item.get("link"):
                st.link_button("Open original source", item["link"])
elif page == "Practice Growth":
    frame = pd.DataFrame(data.get("growth", []))
    st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No practice growth rows.")
elif page == "Physician RVUs":
    rvu = data.get("rvu_metrics", {})
    historical = pd.DataFrame(rvu.get("historical_totals", []))
    physician = pd.DataFrame(rvu.get("physician_rows", []))
    tabs = st.tabs(["Historical Totals", "Physician Entries", "Monthly Graphs"])
    with tabs[0]:
        st.dataframe(historical, hide_index=True, use_container_width=True) if not historical.empty else st.info("No historical data.")
    with tabs[1]:
        st.dataframe(physician, hide_index=True, use_container_width=True) if not physician.empty else st.info("No physician entries.")
    with tabs[2]:
        source = historical if not historical.empty else physician
        if source.empty or "Fiscal Year" not in source.columns:
            st.info("No graphable RVU data.")
        else:
            months = [m for m in ["Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun"] if m in source.columns]
            identifier = "Fiscal Year"
            long = source.melt(id_vars=[identifier], value_vars=months, var_name="Month", value_name="RVUs").dropna(subset=["RVUs"])
            long["Order"] = long["Month"].map({m:i for i,m in enumerate(months)})
            chart = long.pivot_table(index="Order", columns=identifier, values="RVUs", aggfunc="sum")
            chart.index = [months[int(i)] for i in chart.index]
            st.line_chart(chart)
