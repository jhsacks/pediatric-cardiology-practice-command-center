from datetime import date,datetime,timezone
from uuid import uuid4
import pandas as pd
import streamlit as st
SHARING=["Everyone","Selected people","Only me"]; ARTICLE=["Unread","Reviewed","Not Relevant","Archived For Me"]; PRIORITY=["Critical","High","Medium","Low"]; CATEGORIES=["Practice Growth","Clinical Operations","Patient Experience","Staff Issues","Challenges","IT / Automation","Quality","Finance","Marketing","Facilities","Provider Development","Strategic Planning","Personal","Other"]; SITES=["System-wide","Barrett","Smyrna","Douglasville","Paulding","Woodstock","Acworth","Avalon","WGA","Griffin","Other"]
def _ensure(extra):
 c=extra.setdefault("collaboration",{}); [c.setdefault(k,v) for k,v in {"users":[],"initiatives":[],"decisions":[],"practice_growth":[],"article_user_state":{}}.items()]; return c
def _names(c): return [x.get("name") for x in c["users"] if x.get("active",True) and x.get("name")]
def _user(c,current,key):
 u=(current or {}).get("name") if current else None; return u if u in _names(c) else st.selectbox("Working as",_names(c),key=key)
def _share(x): return {"Shared":"Everyone","Practice":"Everyone","Private":"Only me"}.get(str(x.get("sharing",x.get("visibility","Everyone"))),str(x.get("sharing",x.get("visibility","Everyone"))))
def _view(x,u): return _share(x)=="Everyone" or x.get("owner")==u or x.get("creator",x.get("created_by"))==u or (_share(x)=="Selected people" and u in x.get("shared_with",[]))
def _page(extra,save_extra,current,bucket,kind):
 c=_ensure(extra); u=_user(c,current,bucket+"_user"); save=lambda:save_extra(extra); names=_names(c)
 with st.expander("Create "+kind,False):
  with st.form("new_"+bucket,clear_on_submit=True):
   title=st.text_input("Title"); desc=st.text_area("Description"); owner=st.selectbox("Owner",names,index=names.index(u) if u in names else 0); sharing=st.selectbox("Share with",SHARING); shared=st.multiselect("Selected people",[n for n in names if n!=owner]) if sharing=="Selected people" else []; a,b,c1=st.columns(3); started=a.date_input("Date started",date.today()); deadline=b.date_input("Deadline",None); priority=c1.selectbox("Priority",PRIORITY,index=2); d,e=st.columns(2); category=d.selectbox("Category",CATEGORIES); site=e.selectbox("Site",SITES); goal=st.text_input("Related strategic goal"); related=st.text_input("Related initiative or decision"); status=st.selectbox("Status",["Open","Pending Data","Pending Leadership","Approved","Declined","Implemented","Archived"] if kind=="Decision" else ["Not Started","In Progress","Waiting","Blocked","Completed","Archived"])
   if st.form_submit_button("Create") and title.strip(): c[bucket].append({"id":kind[:3].upper()+"-"+uuid4().hex[:8],"title":title,"description":desc,"owner":owner,"creator":u,"sharing":sharing,"shared_with":shared,"date_started":str(started),"deadline":str(deadline or ""),"priority":priority,"category":category,"site":site,"strategic_goal":goal,"related_item":related,"status":status}); save(); st.success(kind+" created. Form cleared.")
 for x in c[bucket]:
  if not _view(x,u) or x.get("status")=="Archived": continue
  with st.expander(f"{x.get('title','Untitled')} | {x.get('owner','')} | {x.get('status','')}"):
   st.write(x.get("description",x.get("notes",""))); st.caption(f"{x.get('priority','Medium')} | {x.get('category','Other')} | Due: {x.get('deadline','') or 'None'} | {_share(x)}")
def _articles(extra):
 ci=extra.get("clinical_intelligence",{}); return ci.get("items",ci.get("articles",[]))
def render_clinical_intelligence(extra,save_extra,current_user=None):
 c=_ensure(extra); u=_user(c,current_user,"ci_user"); states=c["article_user_state"].setdefault(u,{}); arts=_articles(extra); counts={k:0 for k in ARTICLE}
 for a in arts:
  aid=str(a.get("id") or a.get("link") or a.get("title")); state=states.get(aid,"Unread"); counts[state if state in ARTICLE else "Unread"]+=1
 cols=st.columns(4)
 for col,state in zip(cols,ARTICLE): col.metric(state,counts[state])
 filters=st.multiselect("Show",ARTICLE,default=["Unread","Reviewed","Not Relevant"])
 for a in arts:
  aid=str(a.get("id") or a.get("link") or a.get("title")); cur=states.get(aid,"Unread"); cur=cur if cur in ARTICLE else "Unread"
  if cur not in filters: continue
  st.markdown("### "+str(a.get("title","Untitled"))); buttons=st.columns(4); choice=None
  for col,state in zip(buttons,ARTICLE):
   if col.button(state,key=state+u+aid): choice=state
  if choice: states[aid]=choice; save_extra(extra); st.rerun()
  synopsis=a.get("synopsis") or a.get("summary") or a.get("abstract"); st.write(synopsis) if synopsis else None
  with st.expander("Full article details"):
   for label,key in [("Key Findings","key_findings"),("Practice Relevance","practice_relevance"),("Source","source"),("Date","date_added")]:
    if a.get(key): st.markdown(f"**{label}:** {a[key]}")
   if a.get("link"): st.link_button("Open source",a["link"])
   team=[{"User":n,"Status":c["article_user_state"].get(n,{}).get(aid,"Unread")} for n in _names(c)]; st.dataframe(pd.DataFrame(team),hide_index=True,use_container_width=True)
  st.divider()
def render_initiatives_page(extra,save_extra,current_user=None): _page(extra,save_extra,current_user,"initiatives","Initiative")
def render_decisions_page(extra,save_extra,current_user=None): _page(extra,save_extra,current_user,"decisions","Decision")
def render_growth_page(extra,save_extra,current_user=None): _page(extra,save_extra,current_user,"practice_growth","Growth Opportunity")
def render_collaboration_center(extra,save_extra,current_user=None,admin_mode=False): st.info("Use the separate Clinical Intelligence, Initiatives, Decisions, and Practice Growth pages.")
def render_pin_admin(extra,save_extra): st.info("PIN administration is available in Executive only.")
