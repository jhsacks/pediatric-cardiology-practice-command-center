import hashlib
import json

import pandas as pd
import streamlit as st

ARTICLE_STATES = ["Unread", "Reviewed", "Not Relevant", "Archived For Me"]


def _article_list(extra):
    clinical = extra.get("clinical_intelligence", {})
    return clinical.get("items", clinical.get("articles", []))


def _article_id(article):
    existing = article.get("id") or article.get("link") or article.get("url")
    if existing:
        return str(existing)
    identity = json.dumps(
        {
            "title": article.get("title", ""),
            "source": article.get("source", ""),
            "date": article.get("date_added", article.get("date", "")),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _active_names(extra):
    return [
        str(row.get("name"))
        for row in extra.get("collaboration", {}).get("users", [])
        if row.get("active", True) and str(row.get("name", "")).strip()
    ]


def _resolve_user(extra, current_user, key):
    names = _active_names(extra)
    current_name = (current_user or {}).get("name") if current_user else None
    if current_name in names:
        return current_name
    if names:
        return st.selectbox("Clinical Intelligence for", names, key=key)
    return current_name or "Current User"


def _save_state(extra, save_extra, user, article_id, state):
    collaboration = extra.setdefault("collaboration", {})
    states = collaboration.setdefault("article_user_state", {})
    states.setdefault(user, {})[article_id] = state
    save_extra(extra)


def _summary(article):
    return (
        article.get("synopsis")
        or article.get("summary")
        or article.get("abstract")
        or article.get("description")
        or "No synopsis is available for this article."
    )


def _team_status(extra, article_id):
    all_states = extra.get("collaboration", {}).get("article_user_state", {})
    return [
        {
            "User": name,
            "Status": all_states.get(name, {}).get(article_id, "Unread"),
        }
        for name in _active_names(extra)
    ]


def render_personal_clinical_intelligence(extra, save_extra, current_user=None):
    collaboration = extra.setdefault("collaboration", {})
    all_states = collaboration.setdefault("article_user_state", {})
    user = _resolve_user(extra, current_user, "personal_ci_user")
    personal = all_states.setdefault(user, {})
    articles = _article_list(extra)

    st.subheader("Clinical Intelligence")
    st.caption(f"Personalized for {user}. Article actions do not change another user's status.")

    counts = {state: 0 for state in ARTICLE_STATES}
    for article in articles:
        article_id = _article_id(article)
        state = personal.get(article_id, "Unread")
        if state not in ARTICLE_STATES:
            state = "Unread"
        counts[state] += 1

    columns = st.columns(4)
    for column, state in zip(columns, ARTICLE_STATES):
        column.metric(state, counts[state])

    filters = st.multiselect(
        "Show articles with my status",
        ARTICLE_STATES,
        default=["Unread"],
        key=f"personal_ci_filters_20260831_{user}",
    )

    visible = 0
    for index, article in enumerate(articles):
        article_id = _article_id(article)
        current = personal.get(article_id, "Unread")
        if current not in ARTICLE_STATES:
            current = "Unread"
        if current not in filters:
            continue
        visible += 1

        title = str(article.get("title", "Untitled article"))
        st.markdown(f"### {title}")
        st.caption(f"My status: {current}")

        buttons = st.columns(4)
        actions = [
            ("Mark Unread", "Unread", "unread"),
            ("Mark Reviewed", "Reviewed", "reviewed"),
            ("Not Relevant", "Not Relevant", "not_relevant"),
            ("Archive For Me", "Archived For Me", "archive"),
        ]
        selected = None
        for column, (label, state, suffix) in zip(buttons, actions):
            if column.button(
                label,
                key=f"ci_{suffix}_{user}_{article_id}_{index}",
                use_container_width=True,
            ):
                selected = state
        if selected:
            _save_state(extra, save_extra, user, article_id, selected)
            st.rerun()

        st.write(_summary(article))

        with st.expander("Full article details"):
            details = [
                ("Key Findings", "key_findings"),
                ("Practice Relevance", "practice_relevance"),
                ("Source", "source"),
                ("Date", "date_added"),
            ]
            for label, field in details:
                if article.get(field):
                    st.markdown(f"**{label}:** {article[field]}")
            link = article.get("link") or article.get("url")
            if link:
                st.link_button("Open source", link)
            team = _team_status(extra, article_id)
            st.markdown("**Team review status**")
            if team:
                st.dataframe(pd.DataFrame(team), hide_index=True, use_container_width=True)
            else:
                st.caption("No team directory is available.")
        st.divider()

    if visible == 0:
        st.info("No articles match the selected personal status filters.")
