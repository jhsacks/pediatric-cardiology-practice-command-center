from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

from shared_identity import hash_pin

DEFAULT_USERS = [
    {"name":"Jeffrey Sacks","email":"jhsacks@gmail.com","role":"Lead Physician","department":"Clinical","active":True,"admin":True},
    {"name":"Yoni Yaari","email":"jonathan.yaari@wellstar.org","role":"Physician","department":"Clinical","active":True,"admin":False},
    {"name":"Mohammad Khan","email":"mohammad.khan@wellstar.org","role":"Physician","department":"Clinical","active":True,"admin":False},
    {"name":"Luv Makadia","email":"luv.makadia@wellstar.org","role":"Physician","department":"Clinical","active":True,"admin":False},
    {"name":"Jackie Gurr","email":"jackie.gurr@wellstar.org","role":"Practice Manager","department":"Administration","active":True,"admin":False},
    {"name":"Delaine","email":"","role":"Lead Sonographer","department":"Imaging","active":True,"admin":False},
    {"name":"Heather","email":"","role":"Site Lead","department":"Operations","active":True,"admin":False},
]
SHARING = ["Everyone", "Selected people", "Only me"]
ARTICLE_STATES = ["Unread", "Reviewed", "Not Relevant", "Hidden For Me"]
STATUSES = ["Active", "Completed", "Archived"]


def now(): return datetime.now(timezone.utc).isoformat()


def ensure_collaboration(extra):
    data = extra.setdefault("collaboration", {})
    users = data.setdefault("users", [])
    existing = {str(row.get("name", "")): row for row in users}
    for default in DEFAULT_USERS:
        if default["name"] not in existing:
            users.append(deepcopy(default))
        else:
            for key, value in default.items(): existing[default["name"]].setdefault(key, value)
    for key, value in {"initiatives":[], "decisions":[], "practice_growth":[], "article_user_state":{}, "pin_hashes":{}, "pin_references":{}}.items():
        data.setdefault(key, deepcopy(value))
    return data


def active_names(data):
    return [str(row.get("name")) for row in data["users"] if row.get("active", True) and str(row.get("name", "")).strip()]


def normalize_item(item):
    mapping = {"Shared":"Everyone", "Practice":"Everyone", "Private":"Only me"}
    sharing = mapping.get(str(item.get("sharing", item.get("visibility", "Everyone"))), str(item.get("sharing", "Everyone")))
    item["sharing"] = sharing if sharing in SHARING else "Everyone"
    status = str(item.get("status", "Active"))
    status = "Completed" if status in ["Complete", "Finalized"] else status
    item["status"] = status if status in STATUSES else "Active"
    item.setdefault("shared_with", [])
    item.setdefault("creator", item.get("created_by", item.get("owner", "")))
    item.setdefault("owner", item.get("creator", ""))
    item.setdefault("notes", item.get("context", ""))
    item.setdefault("id", f"ITEM-{uuid4().hex[:8]}")
    return item


def can_access(item, user):
    normalize_item(item)
    return item.get("creator") == user or item.get("owner") == user or item.get("sharing") == "Everyone" or (item.get("sharing") == "Selected people" and user in item.get("shared_with", []))


def sharing_controls(data, key, owner_default, sharing_default="Everyone", selected_default=None):
    names = active_names(data)
    owner = st.selectbox("Owner", names, index=names.index(owner_default) if owner_default in names else 0, key=f"{key}_owner")
    sharing = st.selectbox("Share with", SHARING, index=SHARING.index(sharing_default) if sharing_default in SHARING else 0, key=f"{key}_sharing")
    selected = []
    if sharing == "Selected people":
        choices = [name for name in names if name != owner]
        selected = st.multiselect("Selected people", choices, default=[name for name in (selected_default or []) if name in choices], key=f"{key}_selected")
    return owner, sharing, selected


def render_collection(data, user, save, bucket, singular):
    with st.expander(f"Create {singular}", expanded=False):
        with st.form(f"create_{bucket}", clear_on_submit=True):
            title = st.text_input("Title")
            owner, sharing, selected = sharing_controls(data, f"create_{bucket}", user)
            notes = st.text_area("Notes")
            if st.form_submit_button("Create") and title.strip():
                data[bucket].append({"id":f"{bucket[:3].upper()}-{uuid4().hex[:8]}", "title":title.strip(), "owner":owner, "creator":user, "sharing":sharing, "shared_with":selected, "status":"Active", "notes":notes.strip(), "created_at":now(), "updated_at":now(), "updated_by":user})
                save()
                st.success(f"{singular} created. The form is ready for another entry.")
    show_archived = st.toggle(f"Show archived {bucket.replace('_', ' ')}", False, key=f"show_{bucket}")
    for item in data[bucket]:
        normalize_item(item)
        if not can_access(item, user) or (item["status"] == "Archived" and not show_archived): continue
        with st.expander(f"{item.get('title', 'Untitled')} | {item.get('owner')} | {item.get('sharing')}"):
            with st.form(f"edit_{item['id']}"):
                owner, sharing, selected = sharing_controls(data, item["id"], item.get("owner"), item.get("sharing"), item.get("shared_with"))
                status = st.selectbox("Status", STATUSES, index=STATUSES.index(item.get("status", "Active")))
                notes = st.text_area("Notes", item.get("notes", ""))
                if st.form_submit_button("Save"):
                    item.update(owner=owner, sharing=sharing, shared_with=selected, status=status, notes=notes, updated_at=now(), updated_by=user)
                    save(); st.rerun()


def article_team_status(data, article_id):
    rows = []
    for name in active_names(data):
        rows.append({"User":name, "Status":data["article_user_state"].get(name, {}).get(article_id, "Unread")})
    return rows


def render_article_review(extra, data, user, save):
    personal = data["article_user_state"].setdefault(user, {})
    filters = st.multiselect("Show", ARTICLE_STATES, default=["Unread", "Reviewed", "Not Relevant"], key="article_filters_final")
    articles = extra.get("clinical_intelligence", {}).get("items", [])
    visible = 0
    for article in articles:
        article_id = str(article.get("id") or article.get("link") or article.get("title"))
        current = personal.get(article_id, "Unread")
        if current not in ARTICLE_STATES: current = "Unread"
        if current not in filters: continue
        visible += 1
        with st.expander(f"{article.get('title', 'Untitled')} | {current}"):
            if article.get("source"): st.caption(f"Source: {article['source']}")
            if article.get("date_added"): st.caption(f"Added: {article['date_added']}")
            if article.get("summary"): st.markdown(f"**Summary**\n\n{article['summary']}")
            if article.get("key_findings"): st.markdown(f"**Key Findings**\n\n{article['key_findings']}")
            if article.get("practice_relevance"): st.markdown(f"**Practice Relevance**\n\n{article['practice_relevance']}")
            choice = st.radio("My status", ARTICLE_STATES, index=ARTICLE_STATES.index(current), horizontal=True, key=f"article_{user}_{article_id}")
            if st.button("Save My Status", key=f"save_article_{user}_{article_id}"):
                personal[article_id] = choice; save(); st.rerun()
            if article.get("link"): st.link_button("Open source", article["link"])
            with st.expander("Team review status"):
                st.dataframe(pd.DataFrame(article_team_status(data, article_id)), hide_index=True, use_container_width=True)
    if visible == 0: st.info("No articles match the selected personal-status filters.")


def render_collaboration_home(extra, current_user=None):
    data = ensure_collaboration(extra)
    user = (current_user or {}).get("name") if current_user else None
    if user not in active_names(data): user = st.selectbox("Dashboard for", active_names(data), key="home_dashboard_user")
    accessible_initiatives = [x for x in data["initiatives"] if can_access(x, user) and normalize_item(x).get("status") == "Active"]
    accessible_decisions = [x for x in data["decisions"] if can_access(x, user) and normalize_item(x).get("status") == "Active"]
    accessible_growth = [x for x in data["practice_growth"] if can_access(x, user) and normalize_item(x).get("status") == "Active"]
    articles = extra.get("clinical_intelligence", {}).get("items", [])
    states = data["article_user_state"].setdefault(user, {})
    unread = sum(states.get(str(a.get("id") or a.get("link") or a.get("title")), "Unread") == "Unread" for a in articles)
    planning = extra.get("strategic_planning_12", {})
    milestones = planning.get("milestones", [])
    risks = planning.get("risks", [])
    open_milestones = sum(str(x.get("Status", x.get("status", ""))).lower() not in ["complete", "completed"] for x in milestones)
    high_risks = sum(str(x.get("Likelihood", x.get("likelihood", ""))).lower() == "high" and str(x.get("Impact", x.get("impact", ""))).lower() == "high" for x in risks)
    cols = st.columns(6)
    cols[0].metric("Active Initiatives", len(accessible_initiatives)); cols[1].metric("Open Decisions", len(accessible_decisions)); cols[2].metric("Growth Items", len(accessible_growth)); cols[3].metric("Unread Articles", unread); cols[4].metric("Roadmap Milestones", open_milestones); cols[5].metric("High Risks", high_risks)
    st.subheader("My Active Work")
    rows = ([{"Type":"Initiative", "Title":x.get("title"), "Owner":x.get("owner")} for x in accessible_initiatives] + [{"Type":"Decision", "Title":x.get("title"), "Owner":x.get("owner")} for x in accessible_decisions] + [{"Type":"Growth", "Title":x.get("title"), "Owner":x.get("owner")} for x in accessible_growth])
    if rows: st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else: st.info("No active accessible work items.")


def render_collaboration_center(extra, save_extra, current_user=None, admin_mode=False):
    data = ensure_collaboration(extra); save = lambda: save_extra(extra)
    user = (current_user or {}).get("name") if current_user else None
    if user not in active_names(data): user = st.selectbox("Working as", active_names(data), key="collaboration_working_as")
    tabs = st.tabs(["Initiatives", "Decisions", "Article Review", "Practice Growth"] + (["Users & PINs"] if admin_mode else []))
    with tabs[0]: render_collection(data, user, save, "initiatives", "Initiative")
    with tabs[1]: render_collection(data, user, save, "decisions", "Decision")
    with tabs[2]: render_article_review(extra, data, user, save)
    with tabs[3]: render_collection(data, user, save, "practice_growth", "Growth Opportunity")
    if admin_mode:
        with tabs[4]:
            users = pd.DataFrame(data["users"])
            edited = st.data_editor(users, hide_index=True, use_container_width=True, num_rows="dynamic", key="user_directory_15")
            if st.button("Save User Directory"):
                data["users"] = edited.where(pd.notna(edited), "").to_dict("records"); save(); st.rerun()
            st.subheader("Assigned PIN reference")
            pin_rows = [{"User":name, "PIN":data["pin_references"].get(name, "Not recorded") } for name in active_names(data)]
            st.dataframe(pd.DataFrame(pin_rows), hide_index=True, use_container_width=True)
            with st.form("assign_pin_15", clear_on_submit=True):
                pin_user = st.selectbox("User", active_names(data)); pin = st.text_input("New PIN (1-100)", type="password")
                if st.form_submit_button("Save PIN"):
                    try: number = int(pin)
                    except (TypeError, ValueError): number = 0
                    if 1 <= number <= 100:
                        data["pin_hashes"][pin_user] = hash_pin(pin_user, number)
                        data["pin_references"][pin_user] = str(number)
                        save(); st.success("PIN saved. The reference table now shows the assigned PIN.")
                    else: st.error("PIN must be from 1 through 100.")
