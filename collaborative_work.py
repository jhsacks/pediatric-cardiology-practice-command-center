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
    c = extra.setdefault("collaboration", {})
    for key, default in {"users": [], "initiatives": [], "decisions": [], "practice_growth": [], "pin_hashes": {}, "pin_references": {}, "article_user_state": {}}.items(): c.setdefault(key, default)
    return c

def names(c): return [str(x.get("name")) for x in c["users"] if x.get("active", True) and str(x.get("name", "")).strip()]
def normalize(x, kind):
    mapshare={"Shared":"Everyone","Practice":"Everyone","Private":"Only me"}; share=str(x.get("sharing",x.get("visibility","Everyone"))); x["sharing"]=mapshare.get(share,share) if mapshare.get(share,share) in SHARING else "Everyone"
    x.setdefault("shared_with",[]); x.setdefault("owner",x.get("creator",x.get("created_by",""))); x.setdefault("creator",x.get("created_by",x.get("owner",""))); x.setdefault("id",f"{kind[:3].upper()}-{uuid4().hex[:8]}"); x.setdefault("title",x.get("name","Untitled")); x.setdefault("description",x.get("notes",x.get("context",""))); x.setdefault("date_started",str(x.get("created_at",""))[:10]); x.setdefault("deadline",x.get("target_date",x.get("decision_due_date",""))); x.setdefault("priority","Medium"); x.setdefault("category","Other"); x.setdefault("site","System-wide"); x.setdefault("strategic_goal",""); x.setdefault("related_item","")
    statuses=DECISION_STATUSES if kind=="Decision" else WORK_STATUSES; status=str(x.get("status",statuses[0])); x["status"]="Implemented" if kind=="Decision" and status in ["Complete","Completed","Finalized"] else "Completed" if kind!="Decision" and status in ["Complete","Finalized"] else status if status in statuses else statuses[0]
    if kind=="Decision": x.setdefault("impact_level","Medium"); x.setdefault("options_considered",""); x.setdefault("final_decision","")
    return x
def can_access(x,user,kind):
    normalize(x,kind); return x["sharing"]=="Everyone" or x.get("owner")==user or x.get("creator")==user or (x["sharing"]=="Selected people" and user in x.get("shared_with",[]))
def locked_user(c,current_user,allow_view_as=False,key="work_view_as"):
    current=(current_user or {}).get("name") if current_user else None
    if allow_view_as: return st.selectbox("View as",names(c),index=names(c).index(current) if current in names(c) else 0,key=key)
    return current if current in names(c) else None

def fields(c,key,user,x=None,kind="Initiative"):
    x=x or {}; people=names(c); owner_default=x.get("owner",user); owner=st.selectbox("Owner",people,index=people.index(owner_default) if owner_default in people else 0,key=key+"_owner")
    share_default=x.get("sharing","Everyone"); sharing=st.selectbox("Share with",SHARING,index=SHARING.index(share_default) if share_default in SHARING else 0,key=key+"_sharing")
    selected=[]
    if sharing=="Selected people": selected=st.multiselect("Selected people",[n for n in people if n!=owner],default=[n for n in x.get("shared_with",[]) if n in people and n!=owner],key=key+"_people")
    a,b,c1=st.columns(3); started=a.text_input("Date started",x.get("date_started",str(date.today())),key=key+"_start"); deadline=b.text_input("Deadline",x.get("deadline",""),key=key+"_deadline"); priority=c1.selectbox("Priority",PRIORITIES,index=PRIORITIES.index(x.get("priority","Medium")) if x.get("priority") in PRIORITIES else 2,key=key+"_priority")
    d,e=st.columns(2); category=d.selectbox("Category",CATEGORIES,index=CATEGORIES.index(x.get("category","Other")) if x.get("category") in CATEGORIES else len(CATEGORIES)-1,key=key+"_category"); site=e.selectbox("Site",SITES,index=SITES.index(x.get("site","System-wide")) if x.get("site") in SITES else 0,key=key+"_site")
    goal=st.text_input("Related strategic goal",x.get("strategic_goal",""),key=key+"_goal"); related=st.text_input("Related initiative or decision",x.get("related_item",""),key=key+"_related"); statuses=DECISION_STATUSES if kind=="Decision" else WORK_STATUSES; status=st.selectbox("Status",statuses,index=statuses.index(x.get("status",statuses[0])) if x.get("status") in statuses else 0,key=key+"_status")
    return {"owner":owner,"sharing":sharing,"shared_with":selected,"date_started":started,"deadline":deadline,"priority":priority,"category":category,"site":site,"strategic_goal":goal,"related_item":related,"status":status}
def render_page(extra,save_extra,current_user,bucket,kind,allow_view_as=False):
    c=ensure(extra); user=locked_user(c,current_user,allow_view_as,key=bucket+"_view_as")
    if not user: st.error("Your signed-in account is not active in the Executive user directory."); return
    save=lambda:save_extra(extra)
    with st.expander(f"Create {kind}",False):
        with st.form("create_"+bucket,clear_on_submit=True):
            title=st.text_input("Title"); description=st.text_area("Description"); values=fields(c,"new_"+bucket,user,kind=kind)
            if kind=="Decision": impact=st.selectbox("Impact level",["High","Medium","Low"],index=1); options=st.text_area("Options considered"); final=st.text_area("Final decision")
            if st.form_submit_button("Create") and title.strip():
                row={"id":f"{kind[:3].upper()}-{uuid4().hex[:8]}","title":title.strip(),"description":description,"creator":user,"created_at":now(),"updated_at":now(),"updated_by":user,**values}
                if kind=="Decision": row.update(impact_level=impact,options_considered=options,final_decision=final)
                c[bucket].append(row); save(); st.success(f"{kind} created.")
    for x in c[bucket]:
        normalize(x,kind)
        if not can_access(x,user,kind): continue
        with st.expander(f"{x['title']} | {x['owner']} | {x['status']}"):
            with st.form("edit_"+x["id"]):
                title=st.text_input("Title",x["title"]); description=st.text_area("Description",x["description"]); values=fields(c,x["id"],user,x,kind)
                if kind=="Decision": impact=st.selectbox("Impact level",["High","Medium","Low"],index=["High","Medium","Low"].index(x.get("impact_level","Medium"))); options=st.text_area("Options considered",x.get("options_considered","")); final=st.text_area("Final decision",x.get("final_decision",""))
                if st.form_submit_button("Save changes"):
                    x.update(title=title,description=description,updated_at=now(),updated_by=user,**values)
                    if kind=="Decision": x.update(impact_level=impact,options_considered=options,final_decision=final)
                    save(); st.rerun()
def render_initiatives(extra,save_extra,current_user=None,allow_view_as=False): render_page(extra,save_extra,current_user,"initiatives","Initiative",allow_view_as)
def render_decisions(extra,save_extra,current_user=None,allow_view_as=False): render_page(extra,save_extra,current_user,"decisions","Decision",allow_view_as)
def render_growth(extra,save_extra,current_user=None,allow_view_as=False): render_page(extra,save_extra,current_user,"practice_growth","Growth Opportunity",allow_view_as)
def render_user_admin(extra,save_extra):
    c=ensure(extra); save=lambda:save_extra(extra); st.subheader("User Directory & PINs")
    edit=pd.DataFrame(c["users"]); edited=st.data_editor(edit,hide_index=True,use_container_width=True,num_rows="dynamic",key="directory23")
    if st.button("Save user directory"): c["users"]=edited.where(pd.notna(edited),"").to_dict("records"); save(); st.rerun()
    with st.form("add_user23",clear_on_submit=True):
        st.markdown("#### Add user"); a,b=st.columns(2); name=a.text_input("Name"); email=b.text_input("Email"); c1,d=st.columns(2); role=c1.text_input("Role"); department=d.text_input("Department"); active=st.checkbox("Active",True); admin=st.checkbox("Executive administrator",False); pin=st.text_input("PIN (1-100)",type="password")
        if st.form_submit_button("Add user"):
            try: number=int(pin)
            except (TypeError,ValueError): number=0
            if not name.strip(): st.error("Name is required.")
            elif name.strip() in names(c): st.error("That user already exists.")
            elif not 1<=number<=100: st.error("PIN must be from 1 through 100.")
            else:
                c["users"].append({"name":name.strip(),"email":email.strip().casefold(),"role":role.strip(),"department":department.strip(),"active":active,"admin":admin}); c["pin_hashes"][name.strip()]=pin_hash(name.strip(),number); c["pin_references"][name.strip()]=str(number); save(); st.success("User added.")
    st.dataframe(pd.DataFrame([{"User":n,"PIN":c["pin_references"].get(n,"Not recorded")} for n in names(c)]),hide_index=True,use_container_width=True)
    with st.form("reset_pin23",clear_on_submit=True):
        person=st.selectbox("User",names(c)); reset=st.text_input("New PIN",type="password")
        if st.form_submit_button("Reset PIN"):
            try: number=int(reset)
            except (TypeError,ValueError): number=0
            if 1<=number<=100: c["pin_hashes"][person]=pin_hash(person,number); c["pin_references"][person]=str(number); save(); st.success("PIN reset.")
            else: st.error("PIN must be from 1 through 100.")
