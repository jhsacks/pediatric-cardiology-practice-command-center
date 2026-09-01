from datetime import date, datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

from access_control import pin_hash

SHARING = ["Everyone", "Selected people", "Only me"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
WORK_STATUSES = ["Not Started", "In Progress", "Waiting", "Blocked", "Completed", "Archived"]
DECISION_STATUSES = ["Open", "Pending Data", "Pending Leadership", "Approved", "Declined", "Implemented", "Archived"]
CATEGORIES = ["Practice Growth", "Clinical Operations", "Patient Experience", "Staff Issues", "Challenges", "IT / Automation", "Quality", "Finance", "Marketing", "Facilities", "Provider Development", "Strategic Planning", "Personal", "Other"]
SITES = ["System-wide", "Barrett", "Smyrna", "Douglasville", "Paulding", "Woodstock", "Acworth", "Avalon", "WGA", "Griffin", "Other"]


def now(): return datetime.now(timezone.utc).isoformat()
def ensure(extra):
    c=extra.setdefault("collaboration",{})
    for key,default in {"users":[],"initiatives":[],"decisions":[],"practice_growth":[],"pin_hashes":{},"pin_references":{},"article_user_state":{}}.items(): c.setdefault(key,default)
    return c
def names(c): return [str(x.get("name")) for x in c["users"] if x.get("active",True) and str(x.get("name","")).strip()]
def normalize(x,kind):
    mapping={"Shared":"Everyone","Practice":"Everyone","Private":"Only me"}; raw=str(x.get("sharing",x.get("visibility","Everyone"))); x["sharing"]=mapping.get(raw,raw) if mapping.get(raw,raw) in SHARING else "Everyone"
    x.setdefault("shared_with",[]); x.setdefault("owner",x.get("creator",x.get("created_by",""))); x.setdefault("creator",x.get("created_by",x.get("owner",""))); x.setdefault("id",f"{kind[:3].upper()}-{uuid4().hex[:8]}"); x.setdefault("title",x.get("name","Untitled")); x.setdefault("description",x.get("notes",x.get("context",""))); x.setdefault("date_started",str(x.get("created_at",""))[:10]); x.setdefault("deadline",x.get("target_date",x.get("decision_due_date",""))); x.setdefault("priority","Medium"); x.setdefault("category","Other"); x.setdefault("site","System-wide"); x.setdefault("strategic_goal",""); x.setdefault("related_item","")
    statuses=DECISION_STATUSES if kind=="Decision" else WORK_STATUSES; status=str(x.get("status",statuses[0])); x["status"]="Implemented" if kind=="Decision" and status in ["Complete","Completed","Finalized"] else "Completed" if kind!="Decision" and status in ["Complete","Finalized"] else status if status in statuses else statuses[0]
    if kind=="Decision": x.setdefault("impact_level","Medium"); x.setdefault("options_considered",""); x.setdefault("final_decision","")
    return x
def can_access(x,user,kind):
    normalize(x,kind); return x["sharing"]=="Everyone" or x.get("owner")==user or x.get("creator")==user or (x["sharing"]=="Selected people" and user in x.get("shared_with",[]))
def page_user(c,current_user,allow_view_as,key):
    current=(current_user or {}).get("name") if current_user else None
    if allow_view_as:
        people=names(c); return st.selectbox("View as",people,index=people.index(current) if current in people else 0,key=key) if people else None
    return current

def sharing_widgets(c,key,user,x=None):
    x=x or {}; people=names(c); owner_default=x.get("owner",user)
    owner=st.selectbox("Owner",people,index=people.index(owner_default) if owner_default in people else 0,key=key+"_owner")
    share_default=x.get("sharing","Everyone"); sharing=st.selectbox("Share with",SHARING,index=SHARING.index(share_default) if share_default in SHARING else 0,key=key+"_sharing")
    selected=[]
    if sharing=="Selected people":
        choices=[n for n in people if n!=owner]
        selected=st.multiselect("Selected people",choices,default=[n for n in x.get("shared_with",[]) if n in choices],key=key+"_people")
    return owner,sharing,selected

def details_widgets(key,x,kind):
    title=st.text_input("Title",x.get("title",""),key=key+"_title"); description=st.text_area("Description",x.get("description",""),key=key+"_description")
    a,b,c=st.columns(3); started=a.text_input("Date started",x.get("date_started",str(date.today())),key=key+"_start"); deadline=b.text_input("Deadline",x.get("deadline",""),key=key+"_deadline"); priority=c.selectbox("Priority",PRIORITIES,index=PRIORITIES.index(x.get("priority","Medium")) if x.get("priority") in PRIORITIES else 2,key=key+"_priority")
    d,e=st.columns(2); category=d.selectbox("Category",CATEGORIES,index=CATEGORIES.index(x.get("category","Other")) if x.get("category") in CATEGORIES else len(CATEGORIES)-1,key=key+"_category"); site=e.selectbox("Site",SITES,index=SITES.index(x.get("site","System-wide")) if x.get("site") in SITES else 0,key=key+"_site")
    goal=st.text_input("Related strategic goal",x.get("strategic_goal",""),key=key+"_goal"); related=st.text_input("Related initiative or decision",x.get("related_item",""),key=key+"_related")
    statuses=DECISION_STATUSES if kind=="Decision" else WORK_STATUSES; status=st.selectbox("Status",statuses,index=statuses.index(x.get("status",statuses[0])) if x.get("status") in statuses else 0,key=key+"_status")
    values={"title":title,"description":description,"date_started":started,"deadline":deadline,"priority":priority,"category":category,"site":site,"strategic_goal":goal,"related_item":related,"status":status}
    if kind=="Decision":
        values["impact_level"]=st.selectbox("Impact level",["High","Medium","Low"],index=["High","Medium","Low"].index(x.get("impact_level","Medium")),key=key+"_impact"); values["options_considered"]=st.text_area("Options considered",x.get("options_considered",""),key=key+"_options"); values["final_decision"]=st.text_area("Final decision",x.get("final_decision",""),key=key+"_final")
    return values

def render_page(extra,save_extra,current_user,bucket,kind,allow_view_as=False):
    c=ensure(extra); user=page_user(c,current_user,allow_view_as,bucket+"_view_as")
    if not user: st.error("Your signed-in account is not active in the Executive user directory."); return
    save=lambda:save_extra(extra)
    with st.expander(f"Create {kind}",False):
        owner,sharing,selected=sharing_widgets(c,"new_"+bucket,user)
        values=details_widgets("new_"+bucket,{},kind)
        if st.button("Create",key="create_button_"+bucket,type="primary"):
            if not values["title"].strip(): st.error("Title is required.")
            else:
                c[bucket].append({"id":f"{kind[:3].upper()}-{uuid4().hex[:8]}","creator":user,"created_at":now(),"updated_at":now(),"updated_by":user,"owner":owner,"sharing":sharing,"shared_with":selected,**values}); save()
                for suffix in ["title","description","start","deadline","goal","related"]: st.session_state.pop("new_"+bucket+"_"+suffix,None)
                st.success(f"{kind} created."); st.rerun()
    for x in c[bucket]:
        normalize(x,kind)
        if not can_access(x,user,kind): continue
        with st.expander(f"{x['title']} | {x['owner']} | {x['status']}"):
            owner,sharing,selected=sharing_widgets(c,x["id"],user,x); values=details_widgets(x["id"],x,kind)
            if st.button("Save changes",key="save_"+x["id"],type="primary"):
                x.update(owner=owner,sharing=sharing,shared_with=selected,updated_at=now(),updated_by=user,**values); save(); st.rerun()
def render_initiatives(extra,save_extra,current_user=None,allow_view_as=False): render_page(extra,save_extra,current_user,"initiatives","Initiative",allow_view_as)
def render_decisions(extra,save_extra,current_user=None,allow_view_as=False): render_page(extra,save_extra,current_user,"decisions","Decision",allow_view_as)
def render_growth(extra,save_extra,current_user=None,allow_view_as=False): render_page(extra,save_extra,current_user,"practice_growth","Growth Opportunity",allow_view_as)
def render_user_admin(extra,save_extra):
    c=ensure(extra); save=lambda:save_extra(extra); st.subheader("User Directory & PINs"); edited=st.data_editor(pd.DataFrame(c["users"]),hide_index=True,use_container_width=True,num_rows="dynamic",key="directory24")
    if st.button("Save user directory"): c["users"]=edited.where(pd.notna(edited),"").to_dict("records"); save(); st.rerun()
    st.markdown("#### Add user"); a,b=st.columns(2); name=a.text_input("Name",key="add_name24"); email=b.text_input("Email",key="add_email24"); c1,d=st.columns(2); role=c1.text_input("Role",key="add_role24"); department=d.text_input("Department",key="add_department24"); active=st.checkbox("Active",True,key="add_active24"); admin=st.checkbox("Executive administrator",False,key="add_admin24"); pin=st.text_input("PIN (1-100)",type="password",key="add_pin24")
    if st.button("Add user",type="primary"):
        try:number=int(pin)
        except (TypeError,ValueError):number=0
        if not name.strip():st.error("Name is required.")
        elif name.strip() in names(c):st.error("That user already exists.")
        elif not 1<=number<=100:st.error("PIN must be from 1 through 100.")
        else:c["users"].append({"name":name.strip(),"email":email.strip().casefold(),"role":role.strip(),"department":department.strip(),"active":active,"admin":admin});c["pin_hashes"][name.strip()]=pin_hash(name.strip(),number);c["pin_references"][name.strip()]=str(number);save();st.success("User added.");st.rerun()
    st.dataframe(pd.DataFrame([{"User":n,"PIN":c["pin_references"].get(n,"Not recorded")} for n in names(c)]),hide_index=True,use_container_width=True)
