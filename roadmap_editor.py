from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st

HORIZONS = ["1 Year", "3 Years", "5 Years", "10-Year Vision"]
DOMAINS = ["Vision", "Physician Workforce", "Locations & Access", "Telemedicine", "Clinical Services", "Staffing", "Equipment & Infrastructure", "Hospital Integration", "Quality", "Finance", "Other"]
SERVICES = ["General Pediatric Cardiology", "Fetal Cardiology", "Advanced Cardiac Imaging", "Pediatric Electrophysiology", "Interventional Pediatric Cardiology", "Adult Congenital Cardiology", "Pediatric Cardiac Surgery", "NICU / PICU Integration", "Telemedicine", "Other"]
STATUSES = ["Suggestion", "Draft", "Under Review", "Approved", "Published", "Deferred", "Declined", "Archived", "Superseded"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
SHARING = ["Everyone", "Selected people", "Only me"]


def now():
    return datetime.now(timezone.utc).isoformat()


def active_people(extra):
    return [
        str(row.get("name"))
        for row in extra.get("collaboration", {}).get("users", [])
        if row.get("active", True) and str(row.get("name", "")).strip()
    ]


def role(data, user):
    if user == data.get("roles", {}).get("owner"):
        return "Owner"
    if user == data.get("roles", {}).get("editor"):
        return "Editor"
    return "Contributor"


def can_edit(data, user):
    return role(data, user) in {"Owner", "Editor"}


def can_publish(data, user, executive):
    return executive and role(data, user) == "Owner"


def normalize(item):
    item.setdefault("id", "GST-" + uuid4().hex[:8])
    item.setdefault("title", "Untitled Roadmap Item")
    item.setdefault("description", "")
    item.setdefault("horizon", "1 Year")
    item.setdefault("domain", "Other")
    item.setdefault("service", "General Pediatric Cardiology")
    item.setdefault("owner", "")
    item.setdefault("status", "Draft")
    item.setdefault("priority", "Medium")
    item.setdefault("target_date", "")
    item.setdefault("sharing", "Selected people")
    item.setdefault("shared_with", [])
    item.setdefault("dependencies", [])
    item.setdefault("risks", [])
    item.setdefault("success_measures", [])
    item.setdefault("roadmap", [])
    item.setdefault("linked_initiative", "")
    item.setdefault("linked_decision", "")
    item.setdefault("linked_growth_item", "")
    item.setdefault("linked_scenario", "")
    item.setdefault("updated_at", now())
    return item


def permitted(item, user):
    normalize(item)
    return (
        item["sharing"] == "Everyone"
        or item.get("owner") == user
        or item.get("created_by") == user
        or (item["sharing"] == "Selected people" and user in item.get("shared_with", []))
    )


def titles(rows):
    return [str(row.get("title", row.get("name", "Untitled"))) for row in rows]


def lines(value):
    if isinstance(value, list):
        return "\n".join(str(x) for x in value)
    return str(value or "")


def list_value(value):
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def choice(options, current):
    return options.index(current) if current in options else 0


def editor_fields(data, extra, user, item, key):
    people = active_people(extra)
    collaboration = extra.get("collaboration", {})
    planning = extra.get("strategic_planning_12", {})

    title = st.text_input("Title", item.get("title", ""), key=key + "_title")
    description = st.text_area("Description", item.get("description", ""), height=130, key=key + "_description")
    a, b, c = st.columns(3)
    horizon = a.selectbox("Horizon", HORIZONS, index=choice(HORIZONS, item.get("horizon")), key=key + "_horizon")
    priority = b.selectbox("Priority", PRIORITIES, index=choice(PRIORITIES, item.get("priority")), key=key + "_priority")
    target_date = c.text_input("Target date or period", item.get("target_date", ""), key=key + "_target")

    d, e, f = st.columns(3)
    domain = d.selectbox("Domain", DOMAINS, index=choice(DOMAINS, item.get("domain")), key=key + "_domain")
    service = e.selectbox("Clinical service", SERVICES, index=choice(SERVICES, item.get("service")), key=key + "_service")
    status = f.selectbox("Status", STATUSES, index=choice(STATUSES, item.get("status")), key=key + "_status")

    owner_default = item.get("owner", user)
    owner = st.selectbox("Owner", people, index=people.index(owner_default) if owner_default in people else 0, key=key + "_owner") if people else user
    sharing = st.selectbox("Share with", SHARING, index=choice(SHARING, item.get("sharing")), key=key + "_sharing")
    shared_with = []
    if sharing == "Selected people":
        candidates = [name for name in people if name != owner]
        shared_with = st.multiselect("Selected people", candidates, default=[name for name in item.get("shared_with", []) if name in candidates], key=key + "_people")

    st.markdown("#### Plan details")
    steps = st.text_area("Roadmap steps, one per line", lines(item.get("roadmap")), height=150, key=key + "_steps")
    dependencies = st.text_area("Dependencies, one per line", lines(item.get("dependencies")), height=110, key=key + "_dependencies")
    risks = st.text_area("Risks, one per line", lines(item.get("risks")), height=110, key=key + "_risks")
    success = st.text_area("Success measures, one per line", lines(item.get("success_measures")), height=110, key=key + "_success")

    st.markdown("#### Linked Command Center records")
    initiative_options = [""] + titles(collaboration.get("initiatives", []))
    decision_options = [""] + titles(collaboration.get("decisions", []))
    growth_options = [""] + titles(collaboration.get("practice_growth", []))
    scenario_options = [""] + list(planning.get("scenarios", {}).keys())
    l1, l2 = st.columns(2)
    linked_initiative = l1.selectbox("Linked initiative", initiative_options, index=choice(initiative_options, item.get("linked_initiative")), key=key + "_initiative")
    linked_decision = l2.selectbox("Linked decision", decision_options, index=choice(decision_options, item.get("linked_decision")), key=key + "_decision")
    l3, l4 = st.columns(2)
    linked_growth = l3.selectbox("Linked growth item", growth_options, index=choice(growth_options, item.get("linked_growth_item")), key=key + "_growth")
    linked_scenario = l4.selectbox("Linked shared scenario", scenario_options, index=choice(scenario_options, item.get("linked_scenario")), key=key + "_scenario")

    return {
        "title": title.strip(), "description": description.strip(), "horizon": horizon,
        "priority": priority, "target_date": target_date.strip(), "domain": domain,
        "service": service, "status": status, "owner": owner, "sharing": sharing,
        "shared_with": shared_with, "roadmap": list_value(steps),
        "dependencies": list_value(dependencies), "risks": list_value(risks),
        "success_measures": list_value(success), "linked_initiative": linked_initiative,
        "linked_decision": linked_decision, "linked_growth_item": linked_growth,
        "linked_scenario": linked_scenario,
    }


def create_item(data, extra, save_extra, user):
    with st.expander("➕ New Roadmap Item", expanded=False):
        new_item = normalize({"owner": user, "created_by": user, "sharing": "Selected people", "shared_with": [data.get("roles", {}).get("editor", "Jackie Gurr")]})
        values = editor_fields(data, extra, user, new_item, "new_roadmap28")
        if st.button("Create Roadmap Item", type="primary", key="create_roadmap28"):
            if not values["title"]:
                st.error("Title is required.")
            else:
                new_item.update(values)
                new_item["created_at"] = now()
                new_item["updated_at"] = now()
                data.setdefault("draft_items", []).append(new_item)
                save_extra(extra)
                st.rerun()


def publish_baseline(data, extra, save_extra, user):
    approved = [deepcopy(normalize(item)) for item in data.get("draft_items", []) if item.get("status") in {"Approved", "Published"}]
    version = {
        "version": f"{len(data.setdefault('versions', [])) + 1}.0",
        "published_at": now(), "published_by": user, "items": approved,
    }
    data["versions"].append(version)
    data["published_version"] = version
    save_extra(extra)


def item_card(data, extra, save_extra, user, item, executive):
    normalize(item)
    with st.expander(f"{item['title']} | {item['priority']} | {item['status']}", expanded=False):
        if can_edit(data, user):
            values = editor_fields(data, extra, user, item, item["id"])
            a, b, c = st.columns(3)
            if a.button("💾 Save Changes", type="primary", key=item["id"] + "_save"):
                if not values["title"]:
                    st.error("Title is required.")
                else:
                    item.update(values)
                    item["updated_at"] = now()
                    item["updated_by"] = user
                    save_extra(extra)
                    st.rerun()
            if b.button("📄 Duplicate", key=item["id"] + "_duplicate"):
                duplicate = deepcopy(item)
                duplicate["id"] = "GST-" + uuid4().hex[:8]
                duplicate["title"] = values["title"] + " Copy"
                duplicate["status"] = "Draft"
                duplicate["created_by"] = user
                duplicate["created_at"] = now()
                duplicate["updated_at"] = now()
                data["draft_items"].append(duplicate)
                save_extra(extra)
                st.rerun()
            if c.button("📦 Archive", key=item["id"] + "_archive"):
                item["status"] = "Archived"
                item["updated_at"] = now()
                save_extra(extra)
                st.rerun()

            delete_key = item["id"] + "_delete_confirm"
            if role(data, user) == "Owner" and st.button("🗑 Delete Permanently", key=item["id"] + "_delete"):
                st.session_state[delete_key] = True
            if st.session_state.get(delete_key):
                st.warning(f'Delete "{item["title"]}" permanently? This cannot be undone.')
                yes, no = st.columns(2)
                if yes.button("Yes, delete", type="primary", key=item["id"] + "_delete_yes"):
                    data["draft_items"].remove(item)
                    data.setdefault("comments", {}).pop(item["id"], None)
                    st.session_state.pop(delete_key, None)
                    save_extra(extra)
                    st.rerun()
                if no.button("Cancel", key=item["id"] + "_delete_no"):
                    st.session_state.pop(delete_key, None)
                    st.rerun()
        else:
            st.write(item.get("description", ""))
            st.caption(f"{item['horizon']} | {item['domain']} | {item['service']} | Owner: {item['owner']}")
            for heading, field in [("Roadmap steps", "roadmap"), ("Dependencies", "dependencies"), ("Risks", "risks"), ("Success measures", "success_measures")]:
                if item.get(field):
                    st.markdown(f"**{heading}**")
                    for value in item[field]:
                        st.write("• " + str(value))

        st.markdown("#### Discussion")
        comments = data.setdefault("comments", {}).setdefault(item["id"], [])
        for comment in comments:
            st.caption(f"{comment['user']}: {comment['text']}")
        comment = st.text_input("Comment or suggestion", key=item["id"] + "_comment")
        if st.button("Add Comment", key=item["id"] + "_comment_add") and comment.strip():
            comments.append({"user": user, "text": comment.strip(), "time": now()})
            save_extra(extra)
            st.rerun()


def render_roadmap_editor(data, extra, save_extra, user, executive=False):
    st.subheader("1 / 3 / 5 / 10-Year Roadmap")
    st.caption("Create, edit, move, link, duplicate, archive, or retire roadmap items directly. Agent-saved drafts appear here too.")

    if can_edit(data, user):
        create_item(data, extra, save_extra, user)

    controls = st.columns(4)
    horizon_filter = controls[0].multiselect("Horizon", HORIZONS, default=HORIZONS, key="roadmap28_horizons")
    status_filter = controls[1].multiselect(
    "Status",
    STATUSES,
    default=["Idea", "Planning", "Approved", "In Progress"],
    key="roadmap28_status"
    )
    domain_filter = controls[2].multiselect("Domain", DOMAINS, default=DOMAINS, key="roadmap28_domain")
    show_archived = controls[3].toggle("Show archived", False, key="roadmap28_archived")

    visible = []
    for item in data.setdefault("draft_items", []):
        normalize(item)
        if not permitted(item, user):
            continue
        if item["horizon"] not in horizon_filter or item["domain"] not in domain_filter:
            continue
        if item["status"] == "Archived" and not show_archived:
            continue
        if item["status"] != "Archived" and item["status"] not in status_filter:
            continue
        visible.append(item)

    for horizon in HORIZONS:
        horizon_items = [item for item in visible if item["horizon"] == horizon]
        with st.expander(f"{horizon} ({len(horizon_items)})", expanded=True):
            if not horizon_items:
                st.caption("No roadmap items match the current filters.")
            for item in horizon_items:
                item_card(data, extra, save_extra, user, item, executive)

    if can_publish(data, user, executive):
        st.divider()
        st.markdown("#### Official Baseline")
        st.caption("Publishing creates a preserved version from all Approved and Published roadmap items.")
        confirm_key = "roadmap28_publish_confirm"
        if st.button("📢 Publish Official Baseline", key="roadmap28_publish"):
            st.session_state[confirm_key] = True
        if st.session_state.get(confirm_key):
            approved_count = sum(item.get("status") in {"Approved", "Published"} for item in data["draft_items"])
            st.warning(f"Publish a new baseline with {approved_count} approved items?")
            yes, no = st.columns(2)
            if yes.button("Publish", type="primary", key="roadmap28_publish_yes"):
                publish_baseline(data, extra, save_extra, user)
                st.session_state.pop(confirm_key, None)
                st.rerun()
            if no.button("Cancel", key="roadmap28_publish_no"):
                st.session_state.pop(confirm_key, None)
                st.rerun()
