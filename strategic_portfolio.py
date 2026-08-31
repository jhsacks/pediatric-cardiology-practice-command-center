import pandas as pd
import streamlit as st

PROGRESS={"Not Started":0,"Open":10,"Pending Data":25,"Pending Leadership":40,"In Progress":50,"Waiting":50,"Blocked":35,"Approved":75,"Implemented":100,"Completed":100,"Archived":100,"Declined":100}
def _share(x): return {"Shared":"Everyone","Practice":"Everyone","Private":"Only me"}.get(str(x.get("sharing",x.get("visibility","Everyone"))),str(x.get("sharing",x.get("visibility","Everyone"))))
def _view(x,u): return _share(x)=="Everyone" or x.get("owner")==u or x.get("creator",x.get("created_by"))==u or (_share(x)=="Selected people" and u in x.get("shared_with",[]))
def _user(extra,current=None):
 names=[x.get("name") for x in extra.get("collaboration",{}).get("users",[]) if x.get("active",True) and x.get("name")]
 return current if current in names else (st.selectbox("Portfolio view for",names,key="portfolio_user") if names else "")
def render_strategic_portfolio(extra,current_user=None):
 u=_user(extra,(current_user or {}).get("name") if current_user else None); rows=[]; c=extra.get("collaboration",{})
 for kind,bucket in [("Initiative","initiatives"),("Decision","decisions"),("Growth","practice_growth")]:
  for x in c.get(bucket,[]):
   if _view(x,u):
    status=str(x.get("status","Not Started")); rows.append({"Type":kind,"Title":x.get("title","Untitled"),"Owner":x.get("owner",""),"Category":x.get("category","Other"),"Strategic Goal":x.get("strategic_goal") or "Unassigned","Status":status,"Priority":x.get("priority","Medium"),"Deadline":x.get("deadline",x.get("target_date","")),"Progress %":PROGRESS.get(status,0)})
 st.subheader("Strategic Portfolio"); st.caption("Calculated from accessible Initiatives, Decisions, and Practice Growth records.")
 if not rows: st.info("No accessible portfolio records yet."); return
 f=pd.DataFrame(rows); active=f[~f["Status"].isin(["Archived","Declined"])]
 cols=st.columns(5); cols[0].metric("Active Work",len(active)); cols[1].metric("Initiatives",int((active["Type"]=="Initiative").sum())); cols[2].metric("Open Decisions",int((active["Type"]=="Decision").sum())); cols[3].metric("Growth Items",int((active["Type"]=="Growth").sum())); cols[4].metric("Average Progress",f"{active['Progress %'].mean():.0f}%" if len(active) else "0%")
 st.markdown("#### Progress by Portfolio"); st.bar_chart(active.groupby("Category",as_index=False)["Progress %"].mean().set_index("Category")); st.dataframe(active,hide_index=True,use_container_width=True)
def render_growth_planner(extra,current_user=None):
 u=_user(extra,(current_user or {}).get("name") if current_user else None); rows=[]
 for x in extra.get("collaboration",{}).get("practice_growth",[]):
  if _view(x,u): rows.append({"Opportunity":x.get("title","Untitled"),"Owner":x.get("owner",""),"Site":x.get("site","System-wide"),"Priority":x.get("priority","Medium"),"Status":x.get("status","Not Started"),"Deadline":x.get("deadline","")})
 st.subheader("Practice Growth Planner"); st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True) if rows else st.info("No accessible Practice Growth records yet.")
