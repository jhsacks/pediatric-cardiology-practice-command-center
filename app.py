import json
from pathlib import Path

import pandas as pd
import streamlit as st

from team_backend import TeamStore

st.set_page_config(page_title="Practice Command Center", page_icon="❤️", layout="wide")
SEED = Path(__file__).parent / "practice_snapshot.json"
STATUSES = ["Discovery", "Planned", "In progress", "Blocked", "On Hold", "Backlog", "Complete", "Cancelled"]
MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]


def secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return default


def users():
    result = []
    for row in secret("TEAM_USERS", []):
        pin = int(row.get("pin", 0))
        if not 1 <= pin <= 100:
            continue
        result.append({"name": str(row.get("name", "")).strip(), "email": str(row.get("email", "")).strip().casefold(), "pin": str(pin), "admin": bool(row.get("admin", False))})
    return result


def sign_in():
    if st.session_state.get("practice_user"):
        return st.session_state.practice_user
    roster = users()
    if not roster:
        st.error("TEAM_USERS is missing or contains no PINs from 1 through 100.")
        st.stop()
    st.title("Practice Command Center Sign In")
    name = st.selectbox("Team member", [u["name"] for u in roster])
    pin = st.text_input("PIN number (1-100)", type="password")
    if st.button("Sign in", type="primary"):
        match = next(u for u in roster if u["name"] == name)
        if pin.strip() == match["pin"]:
            st.session_state.practice_user = {k: match[k] for k in ["name", "email", "admin"]}
            st.rerun()
        st.error("The selected user and PIN did not match.")
    st.caption("Lightweight access only. Do not place PHI or patient identifiers in this app.")
    st.stop()


def seed():
    if not SEED.exists():
        return {"initiatives": [], "decisions": [], "roadmap": [], "growth": [], "clinical_intelligence": {"items": []}, "rvu_metrics": {}}
    return json.loads(SEED.read_text())


def owner_emails(item):
    values = item.get("owner_emails", [])
    if isinstance(values, str): values = [x.strip() for x in values.split(",")]
    if not values and item.get("owner_email"): values = [item["owner_email"]]
    return {str(x).casefold() for x in values if str(x).strip()}


def render_initiative(item, user, store, roster):
    with st.expander(f"{'ARCHIVED | ' if item.get('archived') else ''}{item.get('id','')} | {item.get('name','Untitled')} | {item.get('progress',0)}%"):
        owners = item.get("owners") or ([item.get("owner")] if item.get("owner") else [])
        st.caption(f"Owners: {', '.join(owners) if owners else 'Unassigned'} | {item.get('status','')} | {item.get('priority','')}")
        editable = user["admin"] or user["email"] in owner_emails(item)
        if user["admin"]:
            current = owner_emails(item)
            options = {u["email"]: u["name"] for u in roster}
            selected = st.multiselect("Assigned owners", list(options), default=[e for e in current if e in options], format_func=lambda e: options[e], key=f"owners_{item.get('id')}")
            if st.button("Save owners", key=f"save_owners_{item.get('id')}"):
                store.update_initiative(item.get("id"), {"owner_emails": selected, "owners": [options[e] for e in selected]}, user)
                st.rerun()
        actions = item.get("next_actions") or ([item.get("next_action")] if item.get("next_action") else [])
        if editable:
            with st.form(f"edit_{item.get('id')}"):
                status_value = item.get("status") if item.get("status") in STATUSES else "Planned"
                status = st.selectbox("Status", STATUSES, index=STATUSES.index(status_value))
                progress = st.slider("Progress", 0, 100, int(item.get("progress", 0)))
                action_text = "\n".join(str(x).lstrip("⭐ ") for x in actions)
                action_input = st.text_area("Next actions, one per line", action_text)
                update = st.text_area("Owner update", item.get("owner_update", ""))
                if st.form_submit_button("Save Initiative Update"):
                    action_list = [f"⭐ {x.strip().lstrip('⭐* ').strip()}" for x in action_input.splitlines() if x.strip()]
                    store.update_initiative(item.get("id"), {"status": status, "progress": progress, "next_actions": action_list, "next_action": action_list[0] if action_list else "", "owner_update": update.strip()}, user)
                    st.rerun()
        else:
            st.info("Only an assigned owner or administrator can edit. Everyone can comment.")
        for comment in item.get("comments", []):
            st.write(f"{comment.get('timestamp_utc','')} | **{comment.get('author_name','')}**: {comment.get('comment','')}")
        with st.form(f"comment_{item.get('id')}"):
            text = st.text_area("Add a comment")
            if st.form_submit_button("Post Comment") and text.strip():
                store.add_comment(item.get("id"), text, user)
                st.rerun()
        with st.expander("History"):
            history = pd.DataFrame(item.get("history", []))
            st.dataframe(history, hide_index=True, use_container_width=True) if not history.empty else st.write("No history yet.")


user = sign_in()
roster = users()

st.write("DEBUG FOLDER ID:", secret("GOOGLE_DRIVE_FOLDER_ID", "NOT_FOUND"))

store = TeamStore(
    dict(st.secrets["google_service_account"]),
    secret("GOOGLE_DRIVE_FOLDER_ID", ""),
    secret("PRACTICE_TEAM_FILE_NAME", "practice_team_data.json")
)

with st.sidebar:
    st.title("❤️ Practice Command Center")
    page = st.radio("Navigate", ["Home", "Initiatives", "Decisions", "Roadmap", "Clinical Intelligence", "Practice Growth", "Physician RVUs"])
    st.caption(f"Signed in: {user['name']}")
    if st.button("Refresh"): st.rerun()
    if st.button("Sign out"):
        st.session_state.pop("practice_user", None)
        st.rerun()

st.title("Pediatric Cardiology Practice Command Center")
st.caption("Initiatives are collaborative. RVUs, growth, decisions, roadmap, and intelligence are view-only.")

if page == "Home":
    cols = st.columns(4)
    cols[0].metric("Initiatives", len(data.get("initiatives", [])))
    cols[1].metric("Decisions", len(data.get("decisions", [])))
    cols[2].metric("Roadmap", len(data.get("roadmap", [])))
    cols[3].metric("Intelligence", len(data.get("clinical_intelligence", {}).get("items", [])))
    st.subheader("My Initiatives")
    mine = [i for i in data.get("initiatives", []) if user["admin"] or user["email"] in owner_emails(i)]
    for item in mine: render_initiative(item, user, store, roster)
elif page == "Initiatives":
    show_archived = st.toggle("Show archived", False)
    for item in [i for i in data.get("initiatives", []) if show_archived or not i.get("archived")]: render_initiative(item, user, store, roster)
elif page == "Decisions":
    frame = pd.DataFrame(data.get("decisions", [])); st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No practice decisions.")
elif page == "Roadmap":
    frame = pd.DataFrame(data.get("roadmap", [])); st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No roadmap items.")
elif page == "Clinical Intelligence":
    for item in data.get("clinical_intelligence", {}).get("items", []):
        with st.expander(item.get("title", "Untitled")):
            st.write(item.get("summary", ""))
            if item.get("link"): st.link_button("Open source", item["link"])
elif page == "Practice Growth":
    frame = pd.DataFrame(data.get("growth", [])); st.dataframe(frame, hide_index=True, use_container_width=True) if not frame.empty else st.info("No growth data.")
elif page == "Physician RVUs":
    rvu = data.get("rvu_metrics", {})
    hist = pd.DataFrame(rvu.get("historical_totals", [])); physician = pd.DataFrame(rvu.get("physician_rows", []))
    tabs = st.tabs(["Historical Totals", "Physician Data", "Graphs"])
    with tabs[0]: st.dataframe(hist, hide_index=True, use_container_width=True) if not hist.empty else st.info("No historical totals.")
    with tabs[1]: st.dataframe(physician, hide_index=True, use_container_width=True) if not physician.empty else st.info("No physician data.")
    with tabs[2]:
        source = hist if not hist.empty else physician
        if source.empty or "Fiscal Year" not in source: st.info("No graphable data.")
        else:
            months = [m for m in MONTHS if m in source]
            long = source.melt(id_vars=["Fiscal Year"], value_vars=months, value_name="RVUs", var_name="Month").dropna(subset=["RVUs"])
            long["Order"] = long["Month"].map({m:i for i,m in enumerate(months)})
            chart = long.pivot_table(index="Order", columns="Fiscal Year", values="RVUs", aggfunc="sum")
            chart.index = [months[int(i)] for i in chart.index]
            st.line_chart(chart)
