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


def now():
    return datetime.now(timezone.utc).isoformat()


def ensure_collaboration(extra):
    data = extra.setdefault("collaboration", {})
    existing = {str(row.get("name", "")): row for row in data.setdefault("users", [])}
    for default in DEFAULT_USERS:
        if default["name"] not in existing:
            data["users"].append(deepcopy(default))
        else:
            for key, value in default.items():
                existing[default["name"]].setdefault(key, value)
    data.setdefault("initiatives", [])
    data.setdefault("decisions", [])
    data.setdefault("practice_growth", [])
    data.setdefault("article_user_state", {})
    data.setdefault("pin_hashes", {})
    return data


def active_names(data):
    return [str(row.get("name")) for row in data["users"] if row.get("active", True) and str(row.get("name", "")).strip()]


def normalize_item(item):
    sharing = item.get("sharing", item.get("visibility", "Everyone"))
    mapping = {"Shared": "Everyone", "Practice": "Everyone", "Private": "Only me"}
    item["sharing"] = mapping.get(str(sharing), str(sharing))
    if item["sharing"] not in SHARING:
        item["sharing"] = "Everyone"
    status = str(item.get("status", "Active"))
    if status in ["Complete", "Finalized"]:
        status = "Completed"
    if status not in STATUSES:
        status = "Active"
    item["status"] = status
    item.setdefault("shared_with", [])
    item.setdefault("creator", item.get("created_by", item.get("owner", "")))
    item.setdefault("owner", item.get("creator", ""))
    item.setdefault("notes", item.get("context", ""))
    item.setdefault("id", f"ITEM-{uuid4().hex[:8]}")
    return item


def can_access(item, user):
    normalize_item(item)
    return (
        item.get("creator") == user
        or item.get("owner") == user
        or item.get("sharing") == "Everyone"
        or (item.get("sharing") == "Selected people" and user in item.get("shared_with", []))
    )


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
            submitted = st.form_submit_button("Create")
            if submitted and title.strip():
                data[bucket].append({
                    "id": f"{bucket[:3].upper()}-{uuid4().hex[:8]}",
                    "title": title.strip(), "owner": owner, "creator": user,
                    "sharing": sharing, "shared_with": selected,
                    "status": "Active", "notes": notes.strip(),
                    "created_at": now(), "updated_at": now(), "updated_by": user,
                })
                save()
                st.success(f"{singular} created.")
    show_archived = st.toggle(f"Show archived {bucket.replace('_', ' ')}", False, key=f"show_{bucket}")
    for item in data[bucket]:
        normalize_item(item)
        if not can_access(item, user) or (item["status"] == "Archived" and not show_archived):
            continue
        with st.expander(f"{item.get('title', 'Untitled')} | {item.get('owner')} | {item.get('sharing')}"):
            with st.form(f"edit_{item['id']}"):
                owner, sharing, selected = sharing_controls(data, item["id"], item.get("owner"), item.get("sharing"), item.get("shared_with"))
                status = st.selectbox("Status", STATUSES, index=STATUSES.index(item.get("status", "Active")))
                notes = st.text_area("Notes", item.get("notes", ""))
                if st.form_submit_button("Save"):
                    item.update(owner=owner, sharing=sharing, shared_with=selected, status=status, notes=notes, updated_at=now(), updated_by=user)
                    save()
                    st.rerun()


def render_collaboration_center(extra, save_extra, current_user=None, admin_mode=False):
    data = ensure_collaboration(extra)
    save = lambda: save_extra(extra)
    user = (current_user or {}).get("name") if current_user else None
    if user not in active_names(data):
        user = st.selectbox("Working as", active_names(data), key="collaboration_working_as")
    tabs = st.tabs(["Initiatives", "Decisions", "Article Review", "Practice Growth"] + (["Users & PINs"] if admin_mode else []))
    with tabs[0]:
        render_collection(data, user, save, "initiatives", "Initiative")
    with tabs[1]:
        render_collection(data, user, save, "decisions", "Decision")
    with tabs[2]:
        states = data["article_user_state"].setdefault(user, {})
        for article in extra.get("clinical_intelligence", {}).get("items", []):
            article_id = str(article.get("id") or article.get("link") or article.get("title"))
            current = states.get(article_id, "Unread")
            if current not in ARTICLE_STATES:
                current = "Unread"
            with st.expander(f"{article.get('title', 'Untitled')} | {current}"):
                choice = st.radio("My status", ARTICLE_STATES, index=ARTICLE_STATES.index(current), horizontal=True, key=f"article_{user}_{article_id}")
                if st.button("Save My Status", key=f"save_article_{user}_{article_id}"):
                    states[article_id] = choice
                    save()
                    st.rerun()
                if article.get("link"):
                    st.link_button("Open source", article["link"])
    with tabs[3]:
        render_collection(data, user, save, "practice_growth", "Growth Opportunity")
    if admin_mode:
        with tabs[4]:
            users = pd.DataFrame(data["users"])
            edited = st.data_editor(users, hide_index=True, use_container_width=True, num_rows="dynamic", key="user_directory_final")
            if st.button("Save User Directory"):
                data["users"] = edited.where(pd.notna(edited), "").to_dict("records")
                save()
                st.rerun()
            st.subheader("Assign or reset PIN")
            with st.form("assign_pin", clear_on_submit=True):
                pin_user = st.selectbox("User", active_names(data))
                pin = st.text_input("New PIN (1-100)", type="password")
                if st.form_submit_button("Save PIN"):
                    try:
                        number = int(pin)
                    except (TypeError, ValueError):
                        number = 0
                    if 1 <= number <= 100:
                        data["pin_hashes"][pin_user] = hash_pin(pin_user, number)
                        save()
                        st.success("PIN saved.")
                    else:
                        st.error("PIN must be from 1 through 100.")
