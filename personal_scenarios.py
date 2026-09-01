from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st


def ensure(extra):
    planning=extra.setdefault("strategic_planning_12",{}); planning.setdefault("personal_scenarios",{}); return planning

def metrics(result):
    demand=float(result["Projected Future Demand"].sum()); capacity=float(result["Annual Capacity"].sum()); net=capacity-demand; constrained=result.sort_values("Excess / (Shortage)").iloc[0] if len(result) else None; growth=result.sort_values("Growth %",ascending=False).iloc[0] if len(result) else None
    cols=st.columns(5); cols[0].metric("Projected Future Demand",f"{demand:,.0f}"); cols[1].metric("Projected Capacity",f"{capacity:,.0f}"); cols[2].metric("Net Slot Position",f"{net:+,.0f}"); cols[3].metric("Most Constrained",constrained["Site"] if constrained is not None else "None",f"{constrained['Excess / (Shortage)']:+,.0f}" if constrained is not None else None); cols[4].metric("Highest Growth",growth["Site"] if growth is not None else "None",f"{growth['Growth %']:.0f}%" if growth is not None else None)
def render_personal_scenarios(extra,save_extra,current_user,scenario_result):
    planning=ensure(extra); user=(current_user or {}).get("name") if current_user else None
    if not user:st.error("A signed-in user is required for personal scenarios.");return
    mine=planning["personal_scenarios"].setdefault(user,[]); shared=planning.get("scenarios",{}); st.subheader("My Private Scenarios"); st.caption("Private scenarios do not modify shared scenarios or another user's scenarios.")
    with st.form("new_personal_scenario",clear_on_submit=True):
        name=st.text_input("Scenario name"); base=st.selectbox("Start from",list(shared)) if shared else None; notes=st.text_area("Notes")
        if st.form_submit_button("Create private scenario") and name.strip() and base:mine.append({"id":"PSC-"+uuid4().hex[:8],"name":name.strip(),"base":base,"allocation":deepcopy(shared[base]),"assumptions":deepcopy(planning.get("assumptions",{})),"demand":deepcopy(planning.get("demand",[])),"notes":notes,"updated_at":datetime.now(timezone.utc).isoformat()});save_extra(extra);st.rerun()
    for item in mine:
        with st.expander(item["name"],expanded=True):
            allocation=pd.DataFrame([{"Site":k,"Days/Week":v} for k,v in item.get("allocation",{}).items()]); edited=st.data_editor(allocation,hide_index=True,use_container_width=True,key=item["id"]+"_allocation",column_config={"Days/Week":st.column_config.NumberColumn("Provider Days/Week",min_value=0.0,step=0.25)}); notes=st.text_area("Notes",item.get("notes",""),key=item["id"]+"_notes")
            preview=deepcopy(planning); preview["assumptions"]=deepcopy(item.get("assumptions",planning.get("assumptions",{}))); preview["demand"]=deepcopy(item.get("demand",planning.get("demand",[]))); preview.setdefault("scenarios",{})[item["id"]]={r["Site"]:float(r.get("Days/Week") or 0) for r in edited.to_dict("records")}; result=scenario_result(preview,item["id"])
            metrics(result); st.markdown("#### Future Demand, Capacity, and Utilization"); columns=["Site","FY26 Visits","Growth %","FY27 Override","Projected Future Demand","Days/Week","Annual Capacity","Excess / (Shortage)","Utilization %","Tier"]; st.dataframe(result[[c for c in columns if c in result.columns]],hide_index=True,use_container_width=True)
            if st.button("Save private scenario",key=item["id"]+"_save",type="primary"):item["allocation"]={r["Site"]:float(r.get("Days/Week") or 0) for r in edited.to_dict("records")};item["notes"]=notes;item["updated_at"]=datetime.now(timezone.utc).isoformat();save_extra(extra);st.rerun()
