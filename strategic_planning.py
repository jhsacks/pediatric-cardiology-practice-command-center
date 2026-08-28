from copy import deepcopy
import pandas as pd
import streamlit as st

DEFAULT = {
    "assumptions": {"Visits per full clinic day": 11.0, "Effective operating weeks": 45.2},
    "demand": [
        {"Site":"Barrett","Projected Demand":2355}, {"Site":"Smyrna","Projected Demand":1108},
        {"Site":"Douglasville","Projected Demand":1097}, {"Site":"Paulding","Projected Demand":722},
        {"Site":"Acworth","Projected Demand":300}, {"Site":"Avalon","Projected Demand":325},
        {"Site":"WGA","Projected Demand":180}, {"Site":"Griffin","Projected Demand":131},
    ],
    "scenarios": {
        "Four physicians": {"Barrett":5.5,"Smyrna":2.5,"Douglasville":2.5,"Paulding":2.0,"Acworth":0.5,"Avalon":0.5,"WGA":0.25,"Griffin":0.25},
        "Three physicians": {"Barrett":5.5,"Smyrna":2.0,"Douglasville":2.0,"Paulding":1.5,"Acworth":0.5,"Avalon":0.5,"WGA":0.25,"Griffin":0.25},
    },
    "milestones": [], "risks": [], "notes": "",
}

def ensure_planning(extra):
    data = extra.setdefault("strategic_planning_12", deepcopy(DEFAULT))
    for key, value in DEFAULT.items():
        data.setdefault(key, deepcopy(value))
    return data

def calculate(data, scenario):
    demand = pd.DataFrame(data.get("demand", []))
    if "Projected Demand" not in demand.columns:
        fy26 = pd.to_numeric(demand.get("FY26 Visits", 0), errors="coerce").fillna(0.0)
        growth = pd.to_numeric(demand.get("Growth %", 0), errors="coerce").fillna(0.0)
        demand["Projected Demand"] = (fy26 * (1 + growth / 100)).round(0)
    demand["Projected Demand"] = pd.to_numeric(demand["Projected Demand"], errors="coerce").fillna(0.0)
    allocation = pd.DataFrame([{"Site": site, "Days/Week": days} for site, days in data["scenarios"][scenario].items()])
    result = demand.merge(allocation, on="Site", how="left")
    result["Days/Week"] = pd.to_numeric(result["Days/Week"], errors="coerce").fillna(0.0)
    visits = float(data["assumptions"].get("Visits per full clinic day", 11.0) or 11.0)
    weeks = float(data["assumptions"].get("Effective operating weeks", 45.2) or 45.2)
    result["Capacity"] = (result["Days/Week"] * visits * weeks).round(0)
    result["Excess / (Shortage)"] = result["Capacity"] - result["Projected Demand"]
    return result

def render_strategic_planning_center(extra, save_extra):
    data = ensure_planning(extra); save = lambda: save_extra(extra)
    tabs = st.tabs(["Scenarios", "Assumptions & Demand", "Roadmap", "Risks", "Notes"])
    with tabs[0]:
        scenario = st.selectbox("Scenario", list(data["scenarios"]), key="planning_scenario_final")
        result = calculate(data, scenario)
        st.dataframe(result, hide_index=True, use_container_width=True)
        allocation = pd.DataFrame([{"Site": site, "Days/Week": days} for site, days in data["scenarios"][scenario].items()])
        edited = st.data_editor(allocation, hide_index=True, use_container_width=True, key=f"planning_allocation_final_{scenario}")
        if st.button("Save Scenario"):
            data["scenarios"][scenario] = {row["Site"]: float(row.get("Days/Week") or 0) for row in edited.to_dict("records")}
            save(); st.rerun()
    with tabs[1]:
        assumptions = pd.DataFrame([{"Assumption": key, "Value": value} for key, value in data["assumptions"].items()])
        edited_assumptions = st.data_editor(assumptions, hide_index=True, use_container_width=True)
        edited_demand = st.data_editor(pd.DataFrame(data["demand"]), hide_index=True, use_container_width=True)
        if st.button("Save Planning Inputs"):
            data["assumptions"] = {row["Assumption"]: row["Value"] for row in edited_assumptions.to_dict("records")}
            data["demand"] = edited_demand.to_dict("records")
            save(); st.rerun()
    with tabs[2]:
        edited = st.data_editor(pd.DataFrame(data["milestones"]), hide_index=True, use_container_width=True, num_rows="dynamic")
        if st.button("Save Roadmap"):
            data["milestones"] = edited.to_dict("records"); save(); st.rerun()
    with tabs[3]:
        edited = st.data_editor(pd.DataFrame(data["risks"]), hide_index=True, use_container_width=True, num_rows="dynamic")
        if st.button("Save Risks"):
            data["risks"] = edited.to_dict("records"); save(); st.rerun()
    with tabs[4]:
        notes = st.text_area("Leadership notes", data["notes"], height=300)
        if st.button("Save Notes"):
            data["notes"] = notes; save(); st.rerun()
