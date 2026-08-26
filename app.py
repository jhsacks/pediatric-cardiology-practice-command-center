import json
from pathlib import Path

import pandas as pd
import streamlit as st

from team_backend import TeamStore

st.set_page_config(page_title="Pediatric Cardiology Practice Command Center", page_icon="❤️", layout="wide")
SEED_FILE = Path(__file__).parent / "practice_snapshot.json"
STATUSES = ["Discovery", "Planned", "In progress", "Blocked", "On Hold", "Backlog", "Complete", "Cancelled"]


def secret_value(name, default=""):
    try:
        return st.secrets[name]
    except Exception:
        return default


def as_email_set(value):
    if isinstance(value, list):
        return {str(x).strip().casefold() for x in value if str(x).strip()}
    text = str(value or "").strip()
    if not text:
        return set()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return {str(x).strip().casefold() for x in parsed if str(x).strip()}
    except json.JSONDecodeError:
        pass
    return {x.strip().casefold() for x in text.split(",") if x.strip()}


def current_user():
    try:
        if not st.user.is_logged_in:
            st.info("Sign in to access the Practice Command Center.")
            st.login()
            st.stop()
        return {"email": str(st.user.get("email", "")).casefold(), "name": str(st.user.get("name", st.user.get("email", "")))}
    except Exception:
        st.error("Authenticated user information is unavailable. Configure Streamlit authentication before enabling editing.")
        st.stop()


def load_seed():
    if not SEED_FILE.exists():
        return {"initiatives": [], "decisions": [], "roadmap": [], "growth": [], "clinical_intelligence": {"items": []}, "rvu_metrics": {}}
    return json.loads(SEED_FILE.read_text())


def owner_email(item):
    return str(item.get("owner_email", "")).strip().casefold()


def can_edit(item, user, admins):
    return user["email"] in admins or (owner_email(item) and owner_email(item) == user["email"])


def render_initiative(item, user, admins, store):
    archived = bool(item.get("archived", False))
    with st.expander(f"{'ARCHIVED | ' if archived else ''}{item.get('id','')} | {item.get('name','Untitled')} | {item.get('progress',0)}%"):
        st.caption(f"Owner: {item.get('owner','')} | {item.get('owner_email','Owner email not assigned')} | {item.get('status','')} | {item.get('priority','')}")
        actions = item.get("next_actions") or ([item.get("next_action")] if item.get("next_action") else [])
        if actions:
            st.markdown("**Next actions**")
            for action in actions:
                st.write(str(action))
        editable = can_edit(item, user, admins)
        if editable:
            with st.form(f"edit_{item.get('id')}"):
                status = st.selectbox("Status", STATUSES, index=STATUSES.index(item.get("status")) if item.get("status") in STATUSES else 1)
                progress = st.slider("Progress", 0, 100, int(item.get("progress", 0)))
                next_actions = st.text_area("Next actions, one per line", "\n".join(str(x).lstrip("⭐ ") for x in actions))
                notes = st.text_area("Owner update", item.get("owner_update", ""))
                if st.form_submit_button("Save Initiative Update"):
                    actions_list = [f"⭐ {line.strip().lstrip('⭐* ').strip()}" for line in next_actions.splitlines() if line.strip()]
                    store.update_initiative(item.get("id"), {"status": status, "progress": progress, "next_actions": actions_list, "next_action": actions_list[0] if actions_list else "", "owner_update": notes.strip()}, user)
                    st.rerun()
        else:
            st.info("Only the initiative owner or an administrator can change this initiative. All team members can comment.")
        st.markdown("**Comments**")
        for comment in item.get("comments", []):
            st.write(f"{comment.get('timestamp_utc','')} | **{comment.get('author_name') or comment.get('author_email')}**: {comment.get('comment','')}")
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


user = current_user()
admins = as_email_set(secret_value("TEAM_ADMIN_EMAILS", ""))
allowed = as_email_set(secret_value("TEAM_ALLOWED_EMAILS", ""))
if allowed and user["email"] not in allowed and user["email"] not in admins:
    st.error("This account is not authorized for the Practice Command Center.")
    st.stop()

store = TeamStore(secret_value("GOOGLE_SERVICE_ACCOUNT_JSON"), secret_value("GOOGLE_DRIVE_FOLDER_ID"), secret_value("PRACTICE_TEAM_FILE_NAME", "practice_team_data.json"))
data = store.load(load_seed())

with st.sidebar:
    st.title("❤️ Practice Command Center")
    page = st.radio("Navigate", ["Home", "Initiatives", "Decisions", "Roadmap", "Clinical Intelligence", "Practice Growth", "Physician RVUs"])
    st.caption(user["email"])
    if st.button("Refresh data"):
        st.rerun()
    try:
        if st.user.is_logged_in and st.button("Sign out"):
            st.logout()
    except Exception:
        pass

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
    mine = [x for x in data.get("initiatives", []) if owner_email(x) == user["email"]]
    for item in mine:
        render_initiative(item, user, admins, store)
    if not mine:
        st.info("No initiatives are assigned to this email yet.")
elif page == "Initiatives":
    show_archived = st.toggle("Show archived initiatives", value=False)
    initiatives = [x for x in data.get("initiatives", []) if show_archived or not x.get("archived", False)]
    for item in initiatives:
        render_initiative(item, user, admins, store)
elif page == "Decisions":
    st.dataframe(pd.DataFrame(data.get("decisions", [])), hide_index=True, use_container_width=True)
elif page == "Roadmap":
    st.dataframe(pd.DataFrame(data.get("roadmap", [])), hide_index=True, use_container_width=True)
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
    st.dataframe(pd.DataFrame(data.get("growth", [])), hide_index=True, use_container_width=True)
elif page == "Physician RVUs":
    rvu = data.get("rvu_metrics", {})
    tabs = st.tabs(["Historical Totals", "Physician Entries"])
    with tabs[0]:
        historical = pd.DataFrame(rvu.get("historical_totals", []))
        st.dataframe(historical, hide_index=True, use_container_width=True)
        if not historical.empty and "Fiscal Year" in historical.columns:
            months = [m for m in ["Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun"] if m in historical.columns]
            long = historical.melt(id_vars=["Fiscal Year"], value_vars=months, var_name="Month", value_name="RVUs")
            long["Order"] = long["Month"].map({m:i for i,m in enumerate(months)})
            chart = long.pivot(index="Order", columns="Fiscal Year", values="RVUs")
            chart.index = [months[int(i)] for i in chart.index]
            st.line_chart(chart)
    with tabs[1]:
        physician = pd.DataFrame(rvu.get("physician_rows", []))
        st.dataframe(physician, hide_index=True, use_container_width=True)
