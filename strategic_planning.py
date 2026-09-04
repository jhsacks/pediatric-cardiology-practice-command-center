from copy import deepcopy

import pandas as pd
import streamlit as st
from scenario_workforce_32 import render_scenario_workforce
from personal_scenarios import render_personal_scenarios

from strategic_portfolio import render_growth_planner, render_strategic_portfolio

DEFAULT = {
    "assumptions": {
        "Visits per full clinic day": 11.0,
        "Effective operating weeks": 45.2,
    },
    "demand": [
        {"Site": "Barrett", "FY26 Visits": 2048, "Growth %": 15.0, "FY27 Override": None, "Tier": "Super-hub", "Notes": "Can support two physicians on one weekday."},
        {"Site": "Smyrna", "FY26 Visits": 1007, "Growth %": 10.0, "FY27 Override": None, "Tier": "Core", "Notes": "New-provider maturation may understate demand."},
        {"Site": "Douglasville", "FY26 Visits": 997, "Growth %": 10.0, "FY27 Override": None, "Tier": "Core", "Notes": "New-provider maturation may understate demand."},
        {"Site": "Paulding", "FY26 Visits": 602, "Growth %": 20.0, "FY27 Override": None, "Tier": "Growth", "Notes": "Capacity constrained during much of FY26."},
        {"Site": "Woodstock", "FY26 Visits": 542, "Growth %": 5.0, "FY27 Override": 0, "Tier": "Reevaluate", "Notes": "Modeled as replaced by Acworth; override is editable."},
        {"Site": "Acworth", "FY26 Visits": 0, "Growth %": 0.0, "FY27 Override": 300, "Tier": "Growth experiment", "Notes": "Editable first-year startup-demand assumption."},
        {"Site": "Avalon", "FY26 Visits": 295, "Growth %": 10.0, "FY27 Override": None, "Tier": "Access", "Notes": "Maintain measured presence and monitor referral value."},
        {"Site": "WGA", "FY26 Visits": 164, "Growth %": 10.0, "FY27 Override": None, "Tier": "Outreach", "Notes": "New-provider maturation may understate demand."},
        {"Site": "Griffin", "FY26 Visits": 131, "Growth %": 0.0, "FY27 Override": None, "Tier": "Outreach", "Notes": "Monthly Sunday clinic does not displace weekday capacity."},
    ],
    "scenarios": {
        "Four physicians": {"Barrett": 5.5, "Smyrna": 2.5, "Douglasville": 2.5, "Paulding": 2.0, "Woodstock": 0.0, "Acworth": 0.5, "Avalon": 0.5, "WGA": 0.25, "Griffin": 0.25},
        "Three physicians": {"Barrett": 5.5, "Smyrna": 2.0, "Douglasville": 2.0, "Paulding": 1.5, "Woodstock": 0.0, "Acworth": 0.5, "Avalon": 0.5, "WGA": 0.25, "Griffin": 0.25},
    },
    "milestones": [],
    "risks": [],
    "notes": "",
}


def ensure_planning(extra):
    data = extra.setdefault("strategic_planning_12", deepcopy(DEFAULT))
    for key, value in DEFAULT.items():
        data.setdefault(key, deepcopy(value))
    return data


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def demand_table(data):
    frame = pd.DataFrame(data.get("demand", [])).copy()
    if frame.empty:
        frame = pd.DataFrame(deepcopy(DEFAULT["demand"]))
    if "Site" not in frame.columns:
        frame["Site"] = ""
    if "FY26 Visits" not in frame.columns:
        frame["FY26 Visits"] = 0.0
    if "Growth %" not in frame.columns:
        frame["Growth %"] = 0.0
    if "FY27 Override" not in frame.columns:
        frame["FY27 Override"] = None
    if "Tier" not in frame.columns:
        frame["Tier"] = ""
    if "Notes" not in frame.columns:
        frame["Notes"] = ""

    fy26 = pd.to_numeric(frame["FY26 Visits"], errors="coerce").fillna(0.0)
    growth = pd.to_numeric(frame["Growth %"], errors="coerce").fillna(0.0)
    override = pd.to_numeric(frame["FY27 Override"], errors="coerce")

    if "Projected Demand" in frame.columns:
        projected_existing = pd.to_numeric(frame["Projected Demand"], errors="coerce")
    else:
        projected_existing = pd.Series(index=frame.index, dtype=float)

    projected = fy26 * (1.0 + growth / 100.0)
    projected.loc[projected_existing.notna()] = projected_existing.loc[projected_existing.notna()]
    projected.loc[override.notna()] = override.loc[override.notna()]

    frame["FY26 Visits"] = fy26.round(0)
    frame["Growth %"] = growth
    frame["Projected Future Demand"] = projected.round(0)
    return frame


def scenario_result(data, scenario_name, allocation_frame=None):
    demand = demand_table(data)
    if allocation_frame is None:
        allocation_frame = pd.DataFrame([
            {"Site": site, "Days/Week": days}
            for site, days in data.get("scenarios", {}).get(scenario_name, {}).items()
        ])
    allocation = allocation_frame.copy()
    if allocation.empty:
        allocation = pd.DataFrame(columns=["Site", "Days/Week"])
    allocation["Days/Week"] = pd.to_numeric(allocation.get("Days/Week", 0), errors="coerce").fillna(0.0)

    result = demand.merge(allocation[["Site", "Days/Week"]], on="Site", how="left")
    result["Days/Week"] = pd.to_numeric(result["Days/Week"], errors="coerce").fillna(0.0)
    visits = number(data.get("assumptions", {}).get("Visits per full clinic day"), 11.0)
    weeks = number(data.get("assumptions", {}).get("Effective operating weeks"), 45.2)
    result["Annual Capacity"] = (result["Days/Week"] * visits * weeks).round(0)
    result["Excess / (Shortage)"] = (result["Annual Capacity"] - result["Projected Future Demand"]).round(0)
    result["Utilization %"] = 0.0
    positive = result["Annual Capacity"] > 0
    result.loc[positive, "Utilization %"] = (
        result.loc[positive, "Projected Future Demand"]
        .div(result.loc[positive, "Annual Capacity"])
        .mul(100.0)
        .round(1)
    )
    result.loc[(result["Annual Capacity"] == 0) & (result["Projected Future Demand"] > 0), "Utilization %"] = float("inf")
    return result


def scenario_metrics(result):
    demand = float(result["Projected Future Demand"].sum())
    capacity = float(result["Annual Capacity"].sum())
    net = capacity - demand
    shortage = result.sort_values("Excess / (Shortage)").iloc[0] if len(result) else None
    highest_growth = result.sort_values("Growth %", ascending=False).iloc[0] if len(result) else None
    columns = st.columns(5)
    columns[0].metric("Projected Future Demand", f"{demand:,.0f}")
    columns[1].metric("Projected Capacity", f"{capacity:,.0f}")
    columns[2].metric("Net Slot Position", f"{net:+,.0f}")
    columns[3].metric("Most Constrained", shortage["Site"] if shortage is not None else "None", f"{shortage['Excess / (Shortage)']:+,.0f}" if shortage is not None else None)
    columns[4].metric("Highest Growth", highest_growth["Site"] if highest_growth is not None else "None", f"{highest_growth['Growth %']:.0f}%" if highest_growth is not None else None)


def impact_preview(saved, preview):
    comparison = saved[["Site", "Days/Week", "Annual Capacity", "Excess / (Shortage)", "Utilization %"]].merge(
        preview[["Site", "Days/Week", "Annual Capacity", "Excess / (Shortage)", "Utilization %"]],
        on="Site",
        suffixes=(" Saved", " Preview"),
    )
    changed = comparison[comparison["Days/Week Saved"].round(4) != comparison["Days/Week Preview"].round(4)].copy()
    if changed.empty:
        st.caption("Change one or more Days/Week values below to preview the effect before saving.")
        return
    changed["Days Change"] = changed["Days/Week Preview"] - changed["Days/Week Saved"]
    changed["Capacity Change"] = changed["Annual Capacity Preview"] - changed["Annual Capacity Saved"]
    changed["Slot Position Change"] = changed["Excess / (Shortage) Preview"] - changed["Excess / (Shortage) Saved"]
    changed["Utilization Change"] = changed["Utilization % Preview"] - changed["Utilization % Saved"]
    st.markdown("#### Live Change Impact")
    st.dataframe(
        changed[["Site", "Days/Week Saved", "Days/Week Preview", "Days Change", "Capacity Change", "Slot Position Change", "Utilization % Saved", "Utilization % Preview", "Utilization Change"]],
        hide_index=True,
        use_container_width=True,
    )
    total_capacity_change = changed["Capacity Change"].sum()
    total_days_change = changed["Days Change"].sum()
    st.info(f"Preview impact: {total_days_change:+.2f} provider days/week and {total_capacity_change:+,.0f} annual patient slots.")


def render_strategic_planning_center(extra, save_extra, current_user=None):
    data = ensure_planning(extra)
    save = lambda: save_extra(extra)
    tabs = st.tabs(["Portfolio", "Shared Scenarios", "My Scenarios", "Assumptions & Demand", "Roadmap", "Risks", "Notes", "Workforce & Schedule"])

    with tabs[0]:
        render_strategic_portfolio(extra)
        render_growth_planner(extra)

    with tabs[1]:
        scenario = st.selectbox("Scenario", list(data["scenarios"]), key="planning_scenario_19")
        saved_allocation = pd.DataFrame([
            {"Site": site, "Days/Week": days}
            for site, days in data["scenarios"][scenario].items()
        ])
        edited_allocation = st.data_editor(
            saved_allocation,
            hide_index=True,
            use_container_width=True,
            key=f"planning_allocation_19_{scenario}",
            column_config={"Days/Week": st.column_config.NumberColumn("Provider Days/Week", min_value=0.0, step=0.25)},
        )
        saved_result = scenario_result(data, scenario, saved_allocation)
        preview_result = scenario_result(data, scenario, edited_allocation)
        scenario_metrics(preview_result)
        st.markdown("#### Future Demand, Capacity, and Utilization")
        st.dataframe(
            preview_result[["Site", "FY26 Visits", "Growth %", "FY27 Override", "Projected Future Demand", "Days/Week", "Annual Capacity", "Excess / (Shortage)", "Utilization %", "Tier"]],
            hide_index=True,
            use_container_width=True,
        )
        impact_preview(saved_result, preview_result)
        if st.button("Save Scenario", type="primary"):
            data["scenarios"][scenario] = {row["Site"]: number(row.get("Days/Week")) for row in edited_allocation.to_dict("records")}
            save()
            st.rerun()

    with tabs[2]:
        render_personal_scenarios(extra, save_extra, current_user, scenario_result)

    with tabs[3]:
        st.markdown("#### Planning Assumptions")
        assumptions = pd.DataFrame([{"Assumption": key, "Value": value} for key, value in data["assumptions"].items()])
        edited_assumptions = st.data_editor(assumptions, hide_index=True, use_container_width=True, key="planning_assumptions_19")
        st.markdown("#### Site Demand Inputs")
        editable_demand = pd.DataFrame(data["demand"])
        edited_demand = st.data_editor(editable_demand, hide_index=True, use_container_width=True, key="planning_demand_19")
        st.markdown("#### Calculated Future Demand")
        preview_data = deepcopy(data)
        preview_data["assumptions"] = {row["Assumption"]: row["Value"] for row in edited_assumptions.to_dict("records")}
        preview_data["demand"] = edited_demand.where(pd.notna(edited_demand), None).to_dict("records")
        st.dataframe(demand_table(preview_data), hide_index=True, use_container_width=True)
        if st.button("Save Planning Inputs", type="primary"):
            data["assumptions"] = preview_data["assumptions"]
            data["demand"] = preview_data["demand"]
            save()
            st.rerun()

    with tabs[4]:
        edited = st.data_editor(pd.DataFrame(data["milestones"]), hide_index=True, use_container_width=True, num_rows="dynamic", key="planning_milestones_19")
        if st.button("Save Roadmap"):
            data["milestones"] = edited.to_dict("records")
            save()
            st.rerun()

    with tabs[5]:
        edited = st.data_editor(pd.DataFrame(data["risks"]), hide_index=True, use_container_width=True, num_rows="dynamic", key="planning_risks_19")
        if st.button("Save Risks"):
            data["risks"] = edited.to_dict("records")
            save()
            st.rerun()

    with tabs[6]:
        notes = st.text_area("Leadership notes", data["notes"], height=300)
        if st.button("Save Notes"):
            data["notes"] = notes
            save()
            st.rerun()
    with tabs[7]:
        render_scenario_workforce(extra, save_extra, current_user=current_user)

