from copy import deepcopy
import pandas as pd
import streamlit as st
DEFAULT={"assumptions":{"Visits per full clinic day":11.0,"Effective operating weeks":45.2},"demand":[{"Site":"Barrett","Projected Demand":2355},{"Site":"Smyrna","Projected Demand":1108},{"Site":"Douglasville","Projected Demand":1097},{"Site":"Paulding","Projected Demand":722},{"Site":"Acworth","Projected Demand":300},{"Site":"Avalon","Projected Demand":325},{"Site":"WGA","Projected Demand":180},{"Site":"Griffin","Projected Demand":131}],"scenarios":{"Four physicians":{"Barrett":5.5,"Smyrna":2.5,"Douglasville":2.5,"Paulding":2.0,"Acworth":0.5,"Avalon":0.5,"WGA":0.25,"Griffin":0.25},"Three physicians":{"Barrett":5.5,"Smyrna":2.0,"Douglasville":2.0,"Paulding":1.5,"Acworth":0.5,"Avalon":0.5,"WGA":0.25,"Griffin":0.25}},"milestones":[],"risks":[],"notes":""}
def ensure(extra): return extra.setdefault("strategic_planning_12",deepcopy(DEFAULT))
def calc(d,n):
 demand=pd.DataFrame(d["demand"]); alloc=pd.DataFrame([{"Site":k,"Days/Week":v} for k,v in d["scenarios"][n].items()]); f=demand.merge(alloc,on="Site",how="left").fillna(0); f["Capacity"]=(f["Days/Week"]*float(d["assumptions"]["Visits per full clinic day"])*float(d["assumptions"]["Effective operating weeks"])).round(0); f["Excess / (Shortage)"]=f["Capacity"]-f["Projected Demand"]; return f
def render_strategic_planning_center(extra,save_extra):
 d=ensure(extra); save=lambda:save_extra(extra); st.header("Strategic Planning"); tabs=st.tabs(["Scenarios","Assumptions & Demand","Roadmap","Risks","Notes"])
 with tabs[0]:
  n=st.selectbox("Scenario",list(d["scenarios"])); f=calc(d,n); st.dataframe(f,hide_index=True,use_container_width=True); a=pd.DataFrame([{"Site":k,"Days/Week":v} for k,v in d["scenarios"][n].items()]); e=st.data_editor(a,hide_index=True,use_container_width=True,key="sp13"+n)
  if st.button("Save Scenario"): d["scenarios"][n]={r["Site"]:float(r["Days/Week"]) for r in e.to_dict("records")}; save(); st.rerun()
 with tabs[1]:
  a=pd.DataFrame([{"Assumption":k,"Value":v} for k,v in d["assumptions"].items()]); ea=st.data_editor(a,hide_index=True,use_container_width=True); ed=st.data_editor(pd.DataFrame(d["demand"]),hide_index=True,use_container_width=True)
  if st.button("Save Planning Inputs"): d["assumptions"]={r["Assumption"]:r["Value"] for r in ea.to_dict("records")}; d["demand"]=ed.to_dict("records"); save(); st.rerun()
 with tabs[2]:
  e=st.data_editor(pd.DataFrame(d["milestones"]),hide_index=True,use_container_width=True,num_rows="dynamic")
  if st.button("Save Roadmap"): d["milestones"]=e.to_dict("records"); save(); st.rerun()
 with tabs[3]:
  e=st.data_editor(pd.DataFrame(d["risks"]),hide_index=True,use_container_width=True,num_rows="dynamic")
  if st.button("Save Risks"): d["risks"]=e.to_dict("records"); save(); st.rerun()
 with tabs[4]:
  x=st.text_area("Leadership notes",d["notes"],height=300)
  if st.button("Save Notes"): d["notes"]=x; save(); st.rerun()
