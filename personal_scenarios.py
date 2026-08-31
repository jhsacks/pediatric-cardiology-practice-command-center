from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
import pandas as pd
import streamlit as st

def ensure(extra):
    p=extra.setdefault("strategic_planning_12",{}); p.setdefault("personal_scenarios",{}); return p
def render_personal_scenarios(extra,save_extra,current_user,shared_result_function):
    p=ensure(extra); user=(current_user or {}).get("name") if current_user else None
    if not user: st.error("A signed-in user is required for personal scenarios."); return
    mine=p["personal_scenarios"].setdefault(user,[]); shared=p.get("scenarios",{})
    st.subheader("My Private Scenarios"); st.caption("Changes here do not modify shared scenarios or another user's scenarios.")
    with st.form("new_personal_scenario",clear_on_submit=True):
        name=st.text_input("Scenario name"); base=st.selectbox("Start from",list(shared)) if shared else None; notes=st.text_area("Notes")
        if st.form_submit_button("Create private scenario") and name.strip() and base:
            mine.append({"id":"PSC-"+uuid4().hex[:8],"name":name.strip(),"base":base,"allocation":deepcopy(shared[base]),"assumptions":deepcopy(p.get("assumptions",{})),"demand":deepcopy(p.get("demand",[])),"notes":notes,"updated_at":datetime.now(timezone.utc).isoformat()}); save_extra(extra); st.rerun()
    for item in mine:
        with st.expander(item["name"]):
            allocation=pd.DataFrame([{"Site":k,"Days/Week":v} for k,v in item.get("allocation",{}).items()]); edited=st.data_editor(allocation,hide_index=True,use_container_width=True,key=item["id"]+"_allocation"); notes=st.text_area("Notes",item.get("notes",""),key=item["id"]+"_notes")
            preview=deepcopy(p); preview["assumptions"]=deepcopy(item.get("assumptions",p.get("assumptions",{}))); preview["demand"]=deepcopy(item.get("demand",p.get("demand",[]))); preview.setdefault("scenarios",{})[item["id"]]={r["Site"]:float(r.get("Days/Week") or 0) for r in edited.to_dict("records")}
            st.dataframe(shared_result_function(preview,item["id"]),hide_index=True,use_container_width=True)
            if st.button("Save private scenario",key=item["id"]+"_save"):
                item["allocation"]={r["Site"]:float(r.get("Days/Week") or 0) for r in edited.to_dict("records")}; item["notes"]=notes; item["updated_at"]=datetime.now(timezone.utc).isoformat(); save_extra(extra); st.rerun()
