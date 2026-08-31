from datetime import date, datetime, timedelta

import streamlit as st

PAGE_LABELS = {
    "initiative": "🚀 Initiatives",
    "decision": "⚖️ Decisions",
    "growth": "🌱 Practice Growth",
    "milestone": "📊 Strategic Planning",
    "risk": "📊 Strategic Planning",
    "article": "📚 Clinical Intelligence",
}
HIGH_PRIORITIES = {"Critical", "High"}
OPEN_STATUSES = {
    "initiative": {"Not Started", "In Progress", "Waiting", "Blocked", "Active", "Proposed"},
    "decision": {"Open", "Pending Data", "Pending Leadership", "Draft"},
    "growth": {"Not Started", "In Progress", "Waiting", "Blocked", "Active", "Idea", "Evaluating"},
}


def _parse_date(value):
    if value in (None, "", "None"):
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _sharing(item):
    value = str(item.get("sharing", item.get("visibility", "Everyone")))
    return {"Shared": "Everyone", "Practice": "Everyone", "Private": "Only me"}.get(value, value)


def _can_view(item, user_name):
    sharing = _sharing(item)
    return (
        sharing == "Everyone"
        or item.get("owner") == user_name
        or item.get("creator", item.get("created_by")) == user_name
        or (sharing == "Selected people" and user_name in item.get("shared_with", []))
    )


def _work_items(extra, user_name):
    collaboration = extra.get("collaboration", {})
    today = date.today()
    horizon = today + timedelta(days=30)
    rows = []
    for kind, bucket in (("initiative", "initiatives"), ("decision", "decisions"), ("growth", "practice_growth")):
        for item in collaboration.get(bucket, []):
            if not _can_view(item, user_name):
                continue
            status = str(item.get("status", ""))
            if status not in OPEN_STATUSES[kind]:
                continue
            deadline = _parse_date(item.get("deadline", item.get("target_date", item.get("decision_due_date"))))
            priority = str(item.get("priority", "Medium"))
            overdue = bool(deadline and deadline < today)
            due_soon = bool(deadline and today <= deadline <= horizon)
            high = priority in HIGH_PRIORITIES
            if not (overdue or due_soon or high):
                continue
            rows.append({
                "id": str(item.get("id", item.get("title", ""))),
                "kind": kind,
                "title": str(item.get("title", item.get("name", "Untitled"))),
                "owner": str(item.get("owner", "")),
                "priority": priority,
                "status": status,
                "deadline": deadline,
                "reason": "Overdue" if overdue else "Due within 30 days" if due_soon else "High priority",
            })
    return sorted(rows, key=lambda row: (row["deadline"] is None, row["deadline"] or date.max, row["priority"] != "Critical"))


def _planning_items(extra):
    planning = extra.get("strategic_planning_12", {})
    today = date.today()
    horizon = today + timedelta(days=30)
    rows = []
    for item in planning.get("milestones", []):
        status = str(item.get("Status", item.get("status", "")))
        if status.lower() in {"complete", "completed", "archived"}:
            continue
        deadline = _parse_date(item.get("Target", item.get("target", item.get("deadline"))))
        if deadline and deadline <= horizon:
            rows.append({
                "id": str(item.get("id", item.get("Milestone", item.get("milestone", "")))),
                "kind": "milestone",
                "title": str(item.get("Milestone", item.get("milestone", "Untitled milestone"))),
                "owner": str(item.get("Owner", item.get("owner", ""))),
                "priority": "",
                "status": status,
                "deadline": deadline,
                "reason": "Overdue" if deadline < today else "Due within 30 days",
            })
    for item in planning.get("risks", []):
        likelihood = str(item.get("Likelihood", item.get("likelihood", "")))
        impact = str(item.get("Impact", item.get("impact", "")))
        status = str(item.get("Status", item.get("status", "Open")))
        if status.lower() in {"closed", "complete", "completed", "archived"}:
            continue
        if likelihood == "High" or impact == "High":
            rows.append({
                "id": str(item.get("id", item.get("Risk", item.get("risk", "")))),
                "kind": "risk",
                "title": str(item.get("Risk", item.get("risk", "Untitled risk"))),
                "owner": str(item.get("Owner", item.get("owner", ""))),
                "priority": f"{likelihood} likelihood / {impact} impact",
                "status": status,
                "deadline": None,
                "reason": "High strategic risk",
            })
    return rows


def _unread_articles(extra, user_name):
    collaboration = extra.get("collaboration", {})
    states = collaboration.get("article_user_state", {}).get(user_name, {})
    clinical = extra.get("clinical_intelligence", {})
    articles = clinical.get("items", clinical.get("articles", []))
    rows = []
    for article in articles:
        article_id = str(article.get("id") or article.get("link") or article.get("title"))
        if states.get(article_id, "Unread") == "Unread":
            rows.append({
                "id": article_id,
                "kind": "article",
                "title": str(article.get("title", "Untitled article")),
                "owner": str(article.get("source", "")),
                "priority": "",
                "status": "Unread",
                "deadline": None,
                "reason": "Unread",
            })
    return rows


def _open_page(item):
    st.session_state["practice_home_target_page"] = PAGE_LABELS[item["kind"]]
    st.session_state["practice_home_focus_item_id"] = item["id"]
    st.rerun()


def _section(title, items, key_prefix):
    with st.expander(f"{title} ({len(items)})", expanded=bool(items)):
        if not items:
            st.caption("Nothing currently requires attention.")
            return
        for index, item in enumerate(items):
            deadline = item["deadline"].strftime("%b %d, %Y") if item["deadline"] else "No deadline"
            st.markdown(f"**{item['title']}**")
            st.caption(f"{item['reason']} | {item['priority'] or item['status']} | Owner: {item['owner'] or 'Unassigned'} | {deadline}")
            if st.button(f"Open {PAGE_LABELS[item['kind']]}", key=f"{key_prefix}_{index}_{item['kind']}_{item['id']}"):
                _open_page(item)
            if index < len(items) - 1:
                st.divider()


def render_practice_home(extra, current_user):
    user_name = (current_user or {}).get("name", "")
    work = _work_items(extra, user_name)
    planning = _planning_items(extra)
    unread = _unread_articles(extra, user_name)

    high_priority = [item for item in work if item["priority"] in HIGH_PRIORITIES]
    due_or_overdue = [item for item in work + planning if item["reason"] in {"Due within 30 days", "Overdue"}]
    initiatives = [item for item in work if item["kind"] == "initiative"]
    decisions = [item for item in work if item["kind"] == "decision"]
    growth = [item for item in work if item["kind"] == "growth"]
    risks = [item for item in planning if item["kind"] == "risk"]

    st.subheader("Practice Attention Dashboard")
    st.caption(f"Personalized for {user_name}. Only accessible records requiring attention are shown.")

    metrics = st.columns(6)
    metrics[0].metric("High Priority", len(high_priority))
    metrics[1].metric("Due in 30 Days", len(due_or_overdue))
    metrics[2].metric("Initiatives", len(initiatives))
    metrics[3].metric("Open Decisions", len(decisions))
    metrics[4].metric("Strategic Risks", len(risks))
    metrics[5].metric("Unread Articles", len(unread))

    left, right = st.columns(2)
    with left:
        _section("📅 Due or Overdue", due_or_overdue, "practice_due")
        _section("🚀 Priority Initiatives", initiatives, "practice_initiatives")
        _section("⚖️ Decisions Requiring Attention", decisions, "practice_decisions")
    with right:
        _section("🔥 High-Priority Work", high_priority, "practice_priority")
        _section("🌱 Growth Opportunities", growth, "practice_growth")
        _section("⚠️ Strategic Risks", risks, "practice_risks")
        _section("📚 Unread Clinical Intelligence", unread[:10], "practice_articles")
