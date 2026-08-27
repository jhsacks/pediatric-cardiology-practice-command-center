from copy import deepcopy
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

SITES = ["Barrett", "Smyrna", "Douglasville", "Paulding", "Woodstock", "Acworth", "Avalon", "WGA", "Griffin"]
DEFAULT_DEMAND = [
    {"Site":"Barrett","FY26 Visits":2048,"Growth %":15.0,"FY27 Override":None,"Strategic Tier":"Super-hub","Notes":"Can support two physicians on one day each week."},
    {"Site":"Smyrna","FY26 Visits":1007,"Growth %":10.0,"FY27 Override":None,"Strategic Tier":"Core","Notes":"FY26 likely understated by new-provider maturation."},
    {"Site":"Douglasville","FY26 Visits":997,"Growth %":10.0,"FY27 Override":None,"Strategic Tier":"Core","Notes":"FY26 likely understated by new-provider maturation."},
    {"Site":"Paulding","FY26 Visits":602,"Growth %":20.0,"FY27 Override":None,"Strategic Tier":"Growth","Notes":"Capacity constrained for most of FY26; prioritize over Woodstock."},
    {"Site":"Woodstock","FY26 Visits":542,"Growth %":5.0,"FY27 Override":0,"Strategic Tier":"Reevaluate","Notes":"Set override to 0 when replacing with Acworth."},
    {"Site":"Acworth","FY26 Visits":0,"Growth %":0.0,"FY27 Override":300,"Strategic Tier":"Growth experiment","Notes":"Startup demand assumption; edit as referral evidence develops."},
    {"Site":"Avalon","FY26 Visits":295,"Growth %":10.0,"FY27 Override":None,"Strategic Tier":"Access","Notes":"Preserve measured presence; monitor commercial and referral value."},
    {"Site":"WGA","FY26 Visits":164,"Growth %":10.0,"FY27 Override":None,"Strategic Tier":"Outreach","Notes":"New-provider maturation may understate demand."},
    {"Site":"Griffin","FY26 Visits":131,"Growth %":0.0,"FY27 Override":None,"Strategic Tier":"Outreach","Notes":"Monthly Sunday clinic does not displace weekday capacity."},
]
DEFAULT_SCENARIOS = {
    "Four physicians": {"Barrett":5.5,"Smyrna":2.5,"Douglasville":2.5,"Paulding":2.0,"Woodstock":0.0,"Acworth":0.5,"Avalon":0.5,"WGA":0.25,"Griffin":0.25},
    "Three physicians": {"Barrett":5.5,"Smyrna":2.0,"Douglasville":2.0,"Paulding":1.5,"Woodstock":0.0,"Acworth":0.5,"Avalon":0.5,"WGA":0.25,"Griffin":0.25},
}
DEFAULT_MILESTONES = [
    {"Phase":"1. Baseline","Milestone":"Validate FY26 site volumes, templates, fill rates, and referral origins","Owner":"Jackie Gurr","Target":"2026-10-15","Status":"Not Started","Decision Required":"No"},
    {"Phase":"1. Baseline","Milestone":"Document Dr. Khan's clinic, call, and site contribution","Owner":"Jeffrey Sacks","Target":"2026-10-31","Status":"Not Started","Decision Required":"No"},
    {"Phase":"2. Transition","Milestone":"Approve three-physician interim clinic footprint","Owner":"Jeffrey Sacks","Target":"2026-11-15","Status":"Not Started","Decision Required":"Yes"},
    {"Phase":"2. Transition","Milestone":"Implement access and overload guardrails","Owner":"Jackie Gurr","Target":"2026-12-01","Status":"Not Started","Decision Required":"Yes"},
    {"Phase":"3. Recruitment","Milestone":"Define fourth-physician role and deployment profile","Owner":"Jeffrey Sacks","Target":"2027-01-15","Status":"Not Started","Decision Required":"Yes"},
    {"Phase":"3. Recruitment","Milestone":"Prepare Acworth startup and referral-development plan","Owner":"Heather","Target":"2027-02-15","Status":"Not Started","Decision Required":"Yes"},
    {"Phase":"4. Redesign","Milestone":"Select four-physician future-state clinic model","Owner":"Jeffrey Sacks","Target":"2027-06-30","Status":"Not Started","Decision Required":"Yes"},
    {"Phase":"5. Stabilize","Milestone":"Complete 90-day utilization and access review after hire","Owner":"Jackie Gurr","Target":"","Status":"Not Started","Decision Required":"No"},
]
DEFAULT_RISKS = [
    {"Risk":"Three-physician period creates access deterioration","Likelihood":"High","Impact":"High","Mitigation":"Weekly wait-time and fill-rate review; add overflow sessions when thresholds are exceeded.","Owner":"Jeffrey Sacks"},
    {"Risk":"Paulding demand remains hidden by constrained capacity","Likelihood":"High","Impact":"High","Mitigation":"Track denied appointments, next available, and fill rate separately by site.","Owner":"Jackie Gurr"},
    {"Risk":"Acworth does not develop adequate referrals","Likelihood":"Medium","Impact":"Medium","Mitigation":"Launch at 0.5 day/week with six-month expansion/exit criteria.","Owner":"Heather"},
    {"Risk":"Woodstock patients do not migrate to Acworth","Likelihood":"Medium","Impact":"Medium","Mitigation":"Track referral origin, patient geography, and leakage during transition.","Owner":"Jeffrey Sacks"},
    {"Risk":"New physician ramp-up depresses early utilization","Likelihood":"High","Impact":"Medium","Mitigation":"Use 30/60/90/180-day ramp assumptions and referral outreach plan.","Owner":"Jackie Gurr"},
]


def ensure_roadmap(extra):
    data=extra.setdefault("physician_transition_roadmap",{})
    data.setdefault("assumptions",{"Visits per full day":11.0,"Effective operating weeks":45.2,"PTO days per physician":26,"Closed holidays":7,"Expected Khan departure":"2026-12-31","Fourth physician start":"","Presentation audience":"Kellie Turner"})
    data.setdefault("demand",deepcopy(DEFAULT_DEMAND)); data.setdefault("scenarios",deepcopy(DEFAULT_SCENARIOS)); data.setdefault("milestones",deepcopy(DEFAULT_MILESTONES)); data.setdefault("risks",deepcopy(DEFAULT_RISKS)); data.setdefault("notes","")
    return data


def demand_table(data):
    frame=pd.DataFrame(data["demand"])
    frame["FY26 Visits"]=pd.to_numeric(frame["FY26 Visits"],errors="coerce").fillna(0)
    frame["Growth %"]=pd.to_numeric(frame["Growth %"],errors="coerce").fillna(0)
    override=pd.to_numeric(frame["FY27 Override"],errors="coerce")
    frame["Projected Demand"]=(frame["FY26 Visits"]*(1+frame["Growth %"]/100)).round(0)
    frame.loc[override.notna(),"Projected Demand"]=override[override.notna()]
    return frame


def scenario_table(data,name):
    demand=demand_table(data)[["Site","Projected Demand","Strategic Tier","Notes"]]
    allocations=pd.DataFrame([{"Site":site,"Provider Days/Week":days} for site,days in data["scenarios"][name].items()])
    frame=demand.merge(allocations,on="Site",how="left").fillna({"Provider Days/Week":0})
    visits=float(data["assumptions"].get("Visits per full day",11) or 11); weeks=float(data["assumptions"].get("Effective operating weeks",45.2) or 45.2)
    frame["Annual Capacity"]=(frame["Provider Days/Week"]*visits*weeks).round(0)
    frame["Excess / (Shortage)"]=(frame["Annual Capacity"]-frame["Projected Demand"]).round(0)
    projected = pd.to_numeric(frame["Projected Demand"], errors="coerce").fillna(0.0).astype(float)
    capacity = pd.to_numeric(frame["Annual Capacity"], errors="coerce").fillna(0.0).astype(float)
    frame["Utilization %"] = 0.0
    positive_capacity = capacity > 0
    frame.loc[positive_capacity, "Utilization %"] = (
        projected.loc[positive_capacity]
        .div(capacity.loc[positive_capacity])
        .mul(100.0)
        .round(1)
    )
    frame.loc[(capacity == 0) & (projected > 0), "Utilization %"] = float("inf")
    return frame


def summary_metrics(data,name):
    frame=scenario_table(data,name); total_days=frame["Provider Days/Week"].sum(); demand=frame["Projected Demand"].sum(); capacity=frame["Annual Capacity"].sum(); net=capacity-demand
    cols=st.columns(5); cols[0].metric("Provider days/week",f"{total_days:.2f}"); cols[1].metric("Projected visits",f"{demand:,.0f}"); cols[2].metric("Annual capacity",f"{capacity:,.0f}"); cols[3].metric("Net excess / shortage",f"{net:+,.0f}"); cols[4].metric("Overall utilization",f"{(demand/capacity*100 if capacity else 0):.1f}%")
    return frame


def leadership_summary(data,name,frame):
    shortage=frame[frame["Excess / (Shortage)"]<0].sort_values("Excess / (Shortage)")
    excess=frame[frame["Excess / (Shortage)"]>0].sort_values("Excess / (Shortage)",ascending=False)
    net=frame["Excess / (Shortage)"].sum(); days=frame["Provider Days/Week"].sum()
    st.markdown(f"### Kellie leadership summary: {name}")
    st.write(f"The modeled footprint uses **{days:.2f} provider clinic days per week** and produces a network position of **{net:+,.0f} annual patient slots** based on the current assumptions.")
    st.write("**Strategic direction:** Protect Barrett as the super-hub; protect Smyrna and Douglasville while new-provider panels mature; prioritize Paulding because FY26 activity was capacity constrained; seed Acworth cautiously; treat Avalon, WGA, and Griffin as measured access points; and reevaluate Woodstock rather than automatically preserving historical allocation.")
    if not shortage.empty: st.write("**Largest modeled shortages:** "+", ".join(f"{r.Site} {r['Excess / (Shortage)']:+,.0f}" for _,r in shortage.head(4).iterrows()))
    if not excess.empty: st.write("**Largest modeled buffers:** "+", ".join(f"{r.Site} {r['Excess / (Shortage)']:+,.0f}" for _,r in excess.head(4).iterrows()))
    st.write("**Leadership decisions needed:** interim three-physician footprint, Acworth launch criteria, Woodstock transition approach, fourth-physician recruitment/deployment profile, and access thresholds that trigger temporary overflow clinics.")


def render_roadmap(extra,save_extra,editable=True):
    data=ensure_roadmap(extra); save=lambda:save_extra(extra)
    st.header("Physician Transition & Clinic Optimization Roadmap")
    st.caption("Living strategy for the expected December 2026 physician transition and the future four-physician clinic redesign.")
    tabs=st.tabs(["Executive Summary","Scenario Analytics","Assumptions & Demand","Roadmap","Risks","Leadership Notes"])
    with tabs[0]:
        name=st.radio("Scenario",list(data["scenarios"]),horizontal=True,key="roadmap_exec_scenario"); frame=summary_metrics(data,name); leadership_summary(data,name,frame); st.dataframe(frame[["Site","Projected Demand","Provider Days/Week","Annual Capacity","Excess / (Shortage)","Utilization %","Strategic Tier"]],hide_index=True,use_container_width=True)
    with tabs[1]:
        name=st.selectbox("Analyze scenario",list(data["scenarios"])); frame=summary_metrics(data,name); st.bar_chart(frame.set_index("Site")[["Projected Demand","Annual Capacity"]]); st.dataframe(frame,hide_index=True,use_container_width=True)
        if editable:
            st.subheader("Edit provider days per week")
            alloc=pd.DataFrame([{"Site":site,"Provider Days/Week":value} for site,value in data["scenarios"][name].items()]); changed=st.data_editor(alloc,hide_index=True,use_container_width=True,key=f"scenario_{name}",column_config={"Provider Days/Week":st.column_config.NumberColumn(min_value=0.0,step=0.25)})
            if st.button("Save Scenario",key=f"save_{name}"): data["scenarios"][name]={row["Site"]:float(row["Provider Days/Week"] or 0) for row in changed.to_dict("records")}; save(); st.rerun()
    with tabs[2]:
        st.markdown("#### Planning assumptions")
        assumptions=pd.DataFrame([{"Assumption":key,"Value":value} for key,value in data["assumptions"].items()]); edited_a=st.data_editor(assumptions,hide_index=True,use_container_width=True,disabled=not editable,key="roadmap_assumptions")
        if editable and st.button("Save Assumptions"): data["assumptions"]={row["Assumption"]:row["Value"] for row in edited_a.to_dict("records")}; save(); st.rerun()
        st.markdown("#### Site demand model")
        edited_d=st.data_editor(pd.DataFrame(data["demand"]),hide_index=True,use_container_width=True,disabled=not editable,key="roadmap_demand")
        if editable and st.button("Save Demand Model"): data["demand"]=edited_d.where(pd.notna(edited_d),None).to_dict("records"); save(); st.rerun()
        st.dataframe(demand_table(data),hide_index=True,use_container_width=True)
    with tabs[3]:
        milestones=pd.DataFrame(data["milestones"]); edited=st.data_editor(milestones,hide_index=True,use_container_width=True,num_rows="dynamic" if editable else "fixed",disabled=not editable,key="roadmap_milestones",column_config={"Status":st.column_config.SelectboxColumn(options=["Not Started","In Progress","Blocked","Complete"]),"Decision Required":st.column_config.SelectboxColumn(options=["Yes","No"])})
        if editable and st.button("Save Roadmap"): data["milestones"]=edited.where(pd.notna(edited),"").to_dict("records"); save(); st.rerun()
    with tabs[4]:
        risks=pd.DataFrame(data["risks"]); edited=st.data_editor(risks,hide_index=True,use_container_width=True,num_rows="dynamic" if editable else "fixed",disabled=not editable,key="roadmap_risks")
        if editable and st.button("Save Risks"): data["risks"]=edited.where(pd.notna(edited),"").to_dict("records"); save(); st.rerun()
    with tabs[5]:
        notes=st.text_area("Leadership notes and meeting outcomes",data.get("notes",""),height=350,disabled=not editable)
        if editable and st.button("Save Leadership Notes"): data["notes"]=notes; data["last_updated_at"]=datetime.now(timezone.utc).isoformat(); save(); st.rerun()
