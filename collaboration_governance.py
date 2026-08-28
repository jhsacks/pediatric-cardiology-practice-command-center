from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
import pandas as pd
import streamlit as st

USERS = [
 {"name":"Jeffrey Sacks","role":"Lead Physician","department":"Clinical","active":True,"admin":True},
 {"name":"Yoni Yaari","role":"Physician","department":"Clinical","active":True,"admin":False},
 {"name":"Mohammad Khan","role":"Physician","department":"Clinical","active":True,"admin":False},
 {"name":"Luv Makadia","role":"Physician","department":"Clinical","active":True,"admin":False},
 {"name":"Jackie Gurr","role":"Practice Manager","department":"Administration","active":True,"admin":False},
 {"name":"Delaine","role":"Lead Sonographer","department":"Imaging","active":True,"admin":False},
 {"name":"Heather","role":"Site Lead","department":"Operations","active":True,"admin":False},
]
SHARING=["Everyone","Selected people","Only me"]
ARTICLE_STATES=["Unread","Reviewed","Not Relevant","Hidden For Me"]

def now(): return datetime.now(timezone.utc).isoformat()
def ensure(extra):
 g=extra.setdefault("collaboration",{}); g.setdefault("users",deepcopy(USERS)); g.setdefault("initiatives",[]); g.setdefault("decisions",[]); g.setdefault("practice_growth",[]); g.setdefault("article_user_state",{}); g.setdefault("pin_assignments",{}); return g
def names(g): return [u["name"] for u in g["users"] if u.get("active",True)]
def allowed(x,u): return x.get("creator")==u or x.get("owner")==u or x.get("sharing","Everyone")=="Everyone" or (x.get("sharing")=="Selected people" and u in x.get("shared_with",[]))
def record(kind,title,owner,sharing,shared,user): return {"id":f"{kind[:3].upper()}-{uuid4().hex[:8]}","title":title,"owner":owner,"sharing":sharing,"shared_with":shared if sharing=="Selected people" else [],"creator":user,"created_at":now(),"updated_by":user,"updated_at":now(),"status":"Active","notes":""}
def share_fields(g,key,default):
 owner=st.selectbox("Owner",names(g),index=names(g).index(default) if default in names(g) else 0,key=key+"o"); sharing=st.selectbox("Share with",SHARING,key=key+"s"); shared=st.multiselect("Selected people",[x for x in names(g) if x!=owner],key=key+"p") if sharing=="Selected people" else []; return owner,sharing,shared
def render_list(g,user,save,bucket,label):
 with st.expander(f"Create {label}",False):
  with st.form(f"new_{bucket}",clear_on_submit=True):
   title=st.text_input("Title"); owner,sharing,shared=share_fields(g,"new"+bucket,user); notes=st.text_area("Notes")
   if st.form_submit_button("Create") and title.strip():
    x=record(bucket,title.strip(),owner,sharing,shared,user); x["notes"]=notes; g[bucket].append(x); save(); st.rerun()
 for x in [i for i in g[bucket] if allowed(i,user) and i.get("status")!="Archived"]:
  with st.expander(f"{x['title']} | {x.get('owner')} | {x.get('sharing')}"):
   with st.form("edit_"+x["id"]):
    owner=st.selectbox("Owner",names(g),index=names(g).index(x.get("owner")) if x.get("owner") in names(g) else 0,key=x["id"]+"o"); sharing=st.selectbox("Share with",SHARING,index=SHARING.index(x.get("sharing","Everyone")),key=x["id"]+"s"); shared=st.multiselect("Selected people",[n for n in names(g) if n!=owner],default=x.get("shared_with",[]),key=x["id"]+"p") if sharing=="Selected people" else []; status=st.selectbox("Status",["Active","Completed","Archived"],index=["Active","Completed","Archived"].index(x.get("status","Active"))); notes=st.text_area("Notes",x.get("notes",""))
    if st.form_submit_button("Save"): x.update(owner=owner,sharing=sharing,shared_with=shared,status=status,notes=notes,updated_by=user,updated_at=now()); save(); st.rerun()
def render_collaboration_center(extra,save_extra,current_user=None,admin_mode=False):
 g=ensure(extra); save=lambda:save_extra(extra); st.header("Collaboration")
 user=(current_user or {}).get("name") if current_user else None
 if user not in names(g): user=st.selectbox("Working as",names(g))
 tabs=st.tabs(["Initiatives","Decisions","Article Review","Practice Growth"] + (["Users & PINs"] if admin_mode else []))
 with tabs[0]: render_list(g,user,save,"initiatives","Initiative")
 with tabs[1]: render_list(g,user,save,"decisions","Decision")
 with tabs[2]:
  states=g["article_user_state"].setdefault(user,{})
  for a in extra.get("clinical_intelligence",{}).get("items",[]):
   aid=str(a.get("id") or a.get("link") or a.get("title")); state=states.get(aid,"Unread")
   with st.expander(f"{a.get('title','Untitled')} | {state}"):
    choice=st.radio("My status",ARTICLE_STATES,index=ARTICLE_STATES.index(state),horizontal=True,key=user+aid)
    if st.button("Save My Status",key="save"+user+aid): states[aid]=choice; save(); st.rerun()
 with tabs[3]: render_list(g,user,save,"practice_growth","Growth Opportunity")
 if admin_mode:
  with tabs[4]:
   users=pd.DataFrame(g["users"]); changed=st.data_editor(users,hide_index=True,use_container_width=True,num_rows="dynamic",key="users13")
   if st.button("Save Users"): g["users"]=changed.where(pd.notna(changed),"").to_dict("records"); save(); st.rerun()
   st.caption("PIN assignments are stored for administration only. Existing login authentication remains unchanged in this build.")
   pins=pd.DataFrame([{"User":n,"PIN":g["pin_assignments"].get(n,"")} for n in names(g)]); changed_pins=st.data_editor(pins,hide_index=True,use_container_width=True,key="pins13")
   if st.button("Save PIN Assignments"): g["pin_assignments"]={r["User"]:str(r.get("PIN","")).strip() for r in changed_pins.to_dict("records")}; save(); st.rerun()
