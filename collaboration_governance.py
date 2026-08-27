from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

DEFAULT_USERS = [
    {"name":"Jeffrey Sacks","email":"jhsacks@gmail.com","role":"Lead Physician","active":True,"admin":True},
    {"name":"Yoni Yaari","email":"jonathan.yaari@wellstar.org","role":"Physician","active":True,"admin":False},
    {"name":"Mohammad Khan","email":"mohammad.khan@wellstar.org","role":"Physician","active":True,"admin":False},
    {"name":"Luv Makadia","email":"luv.makadia@wellstar.org","role":"Physician","active":True,"admin":False},
    {"name":"Jackie Gurr","email":"jackie.gurr@wellstar.org","role":"Practice Manager","active":True,"admin":False},
]
VISIBILITY=["Everyone","Selected people","Only me"]
ARTICLE_STATES=["Unread","Reviewed","Not Relevant","Hidden For Me"]
INIT_STATUSES=["Proposed","Active","Blocked","Completed","Archived"]
DEC_STATUSES=["Draft","Open","Finalized","Archived"]
GROWTH_STATUSES=["Idea","Evaluating","Active","Completed","Archived"]
GROWTH_CATEGORIES=["Referral Growth","Recruiting","Outreach","Marketing","Hospital Relationships","Geographic Expansion","Service Line Growth","New Program Development","Other"]


def now(): return datetime.now(timezone.utc).isoformat()


def ensure_governance(extra):
    gov=extra.setdefault("collaboration",{})
    gov.setdefault("users",deepcopy(DEFAULT_USERS)); gov.setdefault("initiatives",[]); gov.setdefault("decisions",[]); gov.setdefault("practice_growth",[]); gov.setdefault("article_user_state",{})
    return gov


def names(gov): return [u["name"] for u in gov["users"] if u.get("active",True)]

def user_by_email(gov,email):
    email=str(email or "").casefold()
    return next((u for u in gov["users"] if str(u.get("email","")).casefold()==email),None)

def allowed(item,user):
    if item.get("created_by")==user or item.get("owner")==user: return True
    mode=item.get("sharing","Everyone")
    return mode=="Everyone" or (mode=="Selected people" and user in item.get("shared_with",[]))

def stamp(item,user,action):
    item["last_updated_by"]=user; item["last_updated_at"]=now(); item.setdefault("history",[]).append({"timestamp":now(),"user":user,"action":action})

def make(kind,title,owner,sharing,shared,user,**fields):
    item={"id":f"{kind[:3].upper()}-{uuid4().hex[:8]}","title":title.strip(),"owner":owner,"sharing":sharing,"shared_with":shared if sharing=="Selected people" else [],"created_by":user,"created_at":now(),"last_updated_by":user,"last_updated_at":now(),"comments":[],"history":[]}
    item.update(fields); stamp(item,user,"Created"); return item

def sharing_fields(gov,prefix,owner_default=None):
    owner=st.selectbox("Owner",names(gov),index=names(gov).index(owner_default) if owner_default in names(gov) else 0,key=f"{prefix}_owner")
    mode=st.selectbox("Share with",VISIBILITY,key=f"{prefix}_sharing")
    selected=st.multiselect("Selected people",[x for x in names(gov) if x!=owner],key=f"{prefix}_people") if mode=="Selected people" else []
    return owner,mode,selected

def sharing_editor(gov,item,key):
    owner=st.selectbox("Owner",names(gov),index=names(gov).index(item.get("owner")) if item.get("owner") in names(gov) else 0,key=f"{key}_owner")
    sharing=st.selectbox("Share with",VISIBILITY,index=VISIBILITY.index(item.get("sharing","Everyone")),key=f"{key}_sharing")
    selected=st.multiselect("Selected people",[x for x in names(gov) if x!=owner],default=[x for x in item.get("shared_with",[]) if x!=owner],key=f"{key}_people") if sharing=="Selected people" else []
    return owner,sharing,selected

def comments(item,user,save,key):
    for c in item.setdefault("comments",[]): st.write(f"{c.get('timestamp','')} | **{c.get('user','')}**: {c.get('text','')}")
    with st.form(f"comment_{key}"):
        text=st.text_area("Add comment")
        if st.form_submit_button("Post Comment") and text.strip(): item["comments"].append({"timestamp":now(),"user":user,"text":text.strip()}); stamp(item,user,"Commented"); save(); st.rerun()

def initiatives(gov,user,save):
    with st.expander("Create Initiative",False):
        with st.form("new_init"):
            title=st.text_input("Title"); owner,sharing,selected=sharing_fields(gov,"new_init",user); priority=st.selectbox("Priority",["Low","Medium","High","Critical"],index=1); status=st.selectbox("Status",INIT_STATUSES,index=1); notes=st.text_area("Notes")
            if st.form_submit_button("Create") and title.strip(): gov["initiatives"].append(make("initiative",title,owner,sharing,selected,user,priority=priority,status=status,notes=notes)); save(); st.rerun()
    show=st.toggle("Show archived initiatives",False)
    for item in [x for x in gov["initiatives"] if allowed(x,user) and (show or x.get("status")!="Archived")]:
        with st.expander(f"{item['title']} | {item.get('owner')} | {item.get('status')}"):
            with st.form(f"init_{item['id']}"):
                owner,sharing,selected=sharing_editor(gov,item,item['id']); status=st.selectbox("Status",INIT_STATUSES,index=INIT_STATUSES.index(item.get("status","Active"))); priority=st.selectbox("Priority",["Low","Medium","High","Critical"],index=["Low","Medium","High","Critical"].index(item.get("priority","Medium"))); notes=st.text_area("Notes",item.get("notes",""))
                if st.form_submit_button("Save"): item.update(owner=owner,sharing=sharing,shared_with=selected,status=status,priority=priority,notes=notes); stamp(item,user,"Updated initiative"); save(); st.rerun()
            comments(item,user,save,item['id'])

def decisions(gov,user,save):
    with st.expander("Create Decision",False):
        with st.form("new_dec"):
            title=st.text_input("Title"); owner,sharing,selected=sharing_fields(gov,"new_dec",user); status=st.selectbox("Status",DEC_STATUSES,index=1); context=st.text_area("Context"); final=st.text_area("Final decision")
            if st.form_submit_button("Create") and title.strip(): gov["decisions"].append(make("decision",title,owner,sharing,selected,user,status=status,context=context,final_decision=final)); save(); st.rerun()
    show=st.toggle("Show archived decisions",False)
    for item in [x for x in gov["decisions"] if allowed(x,user) and (show or x.get("status")!="Archived")]:
        with st.expander(f"{item['title']} | {item.get('owner')} | {item.get('status')}"):
            with st.form(f"dec_{item['id']}"):
                owner,sharing,selected=sharing_editor(gov,item,item['id']); status=st.selectbox("Status",DEC_STATUSES,index=DEC_STATUSES.index(item.get("status","Open"))); context=st.text_area("Context",item.get("context","")); final=st.text_area("Final decision",item.get("final_decision",""))
                if st.form_submit_button("Save"): item.update(owner=owner,sharing=sharing,shared_with=selected,status=status,context=context,final_decision=final); stamp(item,user,"Updated decision"); save(); st.rerun()
            comments(item,user,save,item['id'])

def articles(extra,gov,user,save):
    state=gov["article_user_state"].setdefault(user,{})
    filters=st.multiselect("Show",ARTICLE_STATES,default=["Unread","Reviewed","Not Relevant"])
    for article in extra.get("clinical_intelligence",{}).get("items",[]):
        aid=str(article.get("id") or article.get("link") or article.get("title")); current=state.get(aid,"Unread")
        if current not in filters: continue
        with st.expander(f"{article.get('title','Untitled')} | {current}"):
            st.write(article.get("summary","")); chosen=st.radio("My status",ARTICLE_STATES,index=ARTICLE_STATES.index(current),horizontal=True,key=f"article_{user}_{aid}")
            if st.button("Save My Status",key=f"save_{user}_{aid}"): state[aid]=chosen; save(); st.rerun()
            if article.get("link"): st.link_button("Open source",article["link"])
    st.caption("Hidden For Me and Not Relevant are personal states and never remove an article for another user.")

def growth(gov,user,save):
    with st.expander("Add Growth Opportunity",False):
        with st.form("new_growth"):
            title=st.text_input("Opportunity"); category=st.selectbox("Category",GROWTH_CATEGORIES); owner,sharing,selected=sharing_fields(gov,"new_growth","Jackie Gurr"); impact=st.text_input("Expected impact"); notes=st.text_area("Notes")
            if st.form_submit_button("Add") and title.strip(): gov["practice_growth"].append(make("growth",title,owner,sharing,selected,user,category=category,status="Idea",expected_impact=impact,notes=notes)); save(); st.rerun()
    show=st.toggle("Show archived growth",False)
    for item in [x for x in gov["practice_growth"] if allowed(x,user) and (show or x.get("status")!="Archived")]:
        with st.expander(f"{item['title']} | {item.get('owner')} | {item.get('status')}"):
            with st.form(f"growth_{item['id']}"):
                owner,sharing,selected=sharing_editor(gov,item,item['id']); status=st.selectbox("Status",GROWTH_STATUSES,index=GROWTH_STATUSES.index(item.get("status","Idea"))); impact=st.text_input("Expected impact",item.get("expected_impact","")); notes=st.text_area("Notes",item.get("notes",""))
                if st.form_submit_button("Save"): item.update(owner=owner,sharing=sharing,shared_with=selected,status=status,expected_impact=impact,notes=notes); stamp(item,user,"Updated growth"); save(); st.rerun()

def render_collaboration_center(extra,save_extra,current_user=None,admin_mode=False):
    gov=ensure_governance(extra); save=lambda:save_extra(extra)
    st.header("Collaboration Center")
    if current_user:
        match=user_by_email(gov,current_user.get("email")); user=match["name"] if match else current_user.get("name")
        st.caption(f"Working as {user}")
    else:
        user=st.selectbox("Working as",names(gov))
    tabs=st.tabs(["Initiatives","Decisions","Article Review","Practice Growth"] + (["Users"] if admin_mode else []))
    with tabs[0]: initiatives(gov,user,save)
    with tabs[1]: decisions(gov,user,save)
    with tabs[2]: articles(extra,gov,user,save)
    with tabs[3]: growth(gov,user,save)
    if admin_mode:
        with tabs[4]:
            edited=st.data_editor(pd.DataFrame(gov["users"]),hide_index=True,use_container_width=True,num_rows="dynamic",key="users_admin")
            if st.button("Save User Directory"): gov["users"]=edited.where(pd.notna(edited),"").to_dict("records"); save(); st.rerun()
