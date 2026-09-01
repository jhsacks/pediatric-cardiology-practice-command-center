from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

ALLOW_PUBLISH = False


def ensure(extra):
    planning = extra.setdefault("strategic_planning_12", {})
    planning.setdefault("personal_scenarios", {})
    planning.setdefault("scenarios", {})
    return planning


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def metrics(result):
    demand = float(result["Projected Future Demand"].sum())
    capacity = float(result["Annual Capacity"].sum())
    net = capacity - demand
    constrained = result.sort_values("Excess / (Shortage)").iloc[0] if len(result) else None
    growth = result.sort_values("Growth %", ascending=False).iloc[0] if len(result) else None
    columns = st.columns(5)
    columns[0].metric("Projected Future Demand", f"{demand:,.0f}")
    columns[1].metric("Projected Capacity", f"{capacity:,.0f}")
    columns[2].metric("Net Slot Position", f"{net:+,.0f}")
    columns[3].metric(
        "Most Constrained",
        constrained["Site"] if constrained is not None else "None",
        f"{constrained['Excess / (Shortage)']:+,.0f}" if constrained is not None else None,
    )
    columns[4].metric(
        "Highest Growth",
        growth["Site"] if growth is not None else "None",
        f"{growth['Growth %']:.0f}%" if growth is not None else None,
    )


def scenario_preview(planning, item, edited_allocation, scenario_result):
    preview = deepcopy(planning)
    preview["assumptions"] = deepcopy(item.get("assumptions", planning.get("assumptions", {})))
    preview["demand"] = deepcopy(item.get("demand", planning.get("demand", [])))
    preview.setdefault("scenarios", {})[item["id"]] = {
        row["Site"]: float(row.get("Days/Week") or 0)
        for row in edited_allocation.to_dict("records")
    }
    return scenario_result(preview, item["id"])


def unique_shared_name(shared, requested):
    name = requested.strip()
    if name not in shared:
        return name
    counter = 2
    while f"{name} ({counter})" in shared:
        counter += 1
    return f"{name} ({counter})"


def render_personal_scenarios(extra, save_extra, current_user, scenario_result):
    planning = ensure(extra)
    user = (current_user or {}).get("name") if current_user else None
    if not user:
        st.error("A signed-in user is required for personal scenarios.")
        return

    mine = planning["personal_scenarios"].setdefault(user, [])
    shared = planning.get("scenarios", {})

    st.subheader("My Private Scenarios")
    st.caption("Private scenarios do not modify Shared Scenarios or another user's scenarios.")

    with st.form("new_personal_scenario", clear_on_submit=True):
        new_name = st.text_input("Scenario name")
        base = st.selectbox("Start from", list(shared)) if shared else None
        new_notes = st.text_area("Notes")
        if st.form_submit_button("Create private scenario") and new_name.strip() and base:
            mine.append(
                {
                    "id": "PSC-" + uuid4().hex[:8],
                    "name": new_name.strip(),
                    "base": base,
                    "allocation": deepcopy(shared[base]),
                    "assumptions": deepcopy(planning.get("assumptions", {})),
                    "demand": deepcopy(planning.get("demand", [])),
                    "notes": new_notes,
                    "updated_at": timestamp(),
                }
            )
            save_extra(extra)
            st.rerun()

    if not mine:
        st.info("No private scenarios yet.")
        return

    for item in list(mine):
        item.setdefault("id", "PSC-" + uuid4().hex[:8])
        item.setdefault("name", "Untitled Scenario")
        item.setdefault("allocation", {})
        item.setdefault("notes", "")

        with st.expander(item["name"], expanded=True):
            scenario_name = st.text_input(
                "Scenario name",
                item["name"],
                key=item["id"] + "_name",
            )
            notes = st.text_area(
                "Notes",
                item.get("notes", ""),
                key=item["id"] + "_notes",
            )
            allocation = pd.DataFrame(
                [
                    {"Site": site, "Days/Week": days}
                    for site, days in item.get("allocation", {}).items()
                ]
            )
            edited = st.data_editor(
                allocation,
                hide_index=True,
                use_container_width=True,
                key=item["id"] + "_allocation",
                column_config={
                    "Days/Week": st.column_config.NumberColumn(
                        "Provider Days/Week",
                        min_value=0.0,
                        step=0.25,
                    )
                },
            )

            result = scenario_preview(planning, item, edited, scenario_result)
            metrics(result)
            st.markdown("#### Future Demand, Capacity, and Utilization")
            display_columns = [
                "Site",
                "FY26 Visits",
                "Growth %",
                "FY27 Override",
                "Projected Future Demand",
                "Days/Week",
                "Annual Capacity",
                "Excess / (Shortage)",
                "Utilization %",
                "Tier",
            ]
            st.dataframe(
                result[[column for column in display_columns if column in result.columns]],
                hide_index=True,
                use_container_width=True,
            )

            left, middle, right = st.columns(3)
            if left.button("💾 Save Changes", key=item["id"] + "_save", type="primary"):
                if not scenario_name.strip():
                    st.error("Scenario name is required.")
                else:
                    item["name"] = scenario_name.strip()
                    item["allocation"] = {
                        row["Site"]: float(row.get("Days/Week") or 0)
                        for row in edited.to_dict("records")
                    }
                    item["notes"] = notes
                    item["updated_at"] = timestamp()
                    save_extra(extra)
                    st.rerun()

            if middle.button("📄 Duplicate", key=item["id"] + "_duplicate"):
                copy_item = deepcopy(item)
                copy_item["id"] = "PSC-" + uuid4().hex[:8]
                copy_item["name"] = f"{scenario_name.strip() or item['name']} Copy"
                copy_item["allocation"] = {
                    row["Site"]: float(row.get("Days/Week") or 0)
                    for row in edited.to_dict("records")
                }
                copy_item["notes"] = notes
                copy_item["updated_at"] = timestamp()
                mine.append(copy_item)
                save_extra(extra)
                st.rerun()

            delete_key = item["id"] + "_confirm_delete"
            if right.button("🗑 Delete", key=item["id"] + "_delete"):
                st.session_state[delete_key] = True

            if st.session_state.get(delete_key):
                st.warning(f'Delete "{item["name"]}" permanently?')
                yes, no = st.columns(2)
                if yes.button("Yes, delete", key=item["id"] + "_delete_yes", type="primary"):
                    mine.remove(item)
                    st.session_state.pop(delete_key, None)
                    save_extra(extra)
                    st.rerun()
                if no.button("Cancel", key=item["id"] + "_delete_no"):
                    st.session_state.pop(delete_key, None)
                    st.rerun()

            if ALLOW_PUBLISH:
                st.divider()
                st.markdown("#### Executive Publishing")
                publish_name = st.text_input(
                    "Shared scenario name",
                    value=scenario_name.strip() or item["name"],
                    key=item["id"] + "_publish_name",
                )
                publish_key = item["id"] + "_confirm_publish"
                if st.button("📢 Publish to Shared Scenarios", key=item["id"] + "_publish"):
                    st.session_state[publish_key] = True
                if st.session_state.get(publish_key):
                    st.warning("Publishing creates a new Shared Scenario. It does not delete the private scenario.")
                    yes, no = st.columns(2)
                    if yes.button("Publish", key=item["id"] + "_publish_yes", type="primary"):
                        final_name = unique_shared_name(shared, publish_name or item["name"])
                        shared[final_name] = {
                            row["Site"]: float(row.get("Days/Week") or 0)
                            for row in edited.to_dict("records")
                        }
                        item["last_published_as"] = final_name
                        item["updated_at"] = timestamp()
                        st.session_state.pop(publish_key, None)
                        save_extra(extra)
                        st.rerun()
                    if no.button("Cancel", key=item["id"] + "_publish_no"):
                        st.session_state.pop(publish_key, None)
                        st.rerun()
