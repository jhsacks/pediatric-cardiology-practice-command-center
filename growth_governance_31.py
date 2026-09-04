from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

STATUSES = ["Executive Brainstorming", "Suggestion", "Idea", "Planning", "Approved", "In Progress", "Archived"]
ARCHIVE_REASONS = ["Completed", "Duplicate", "Already Addressed", "Declined", "Out of Scope", "Not Feasible", "Superseded", "Other"]
MIGRATION = {
    "Draft": "Idea", "Discovery": "Idea", "Feasibility": "Planning",
    "Business Case": "Planning", "Under Review": "Planning",
    "Building": "In Progress", "Launch Ready": "In Progress",
    "Live": "In Progress", "Scaling": "In Progress", "Published": "Approved",
    "Deferred": "Archived", "Declined": "Archived", "Superseded": "Archived",
}
BUCKETS = [
    ("Location Strategy", "location_objects"),
    ("Telemedicine", "telemedicine_objects"),
    ("Staffing", "staffing_objects"),
    ("Infrastructure", "infrastructure_objects"),
    ("Clinical Services", "service_objects"),
]


def now(): return datetime.now(timezone.utc).isoformat()
def migrate_status(value): return MIGRATION.get(str(value or "Idea"), str(value or "Idea") if str(value or "Idea") in STATUSES else "Idea")
def role(data,user):
    if user == data.get("roles",{}).get("owner"): return "Owner"
    if user == data.get("roles",{}).get("editor"): return "Editor"
    return "Contributor"
def leadership(data,user): return role(data,user) in {"Owner","Editor"}
def people(extra): return [str(x.get("name")) for x in extra.get("collaboration",{}).get("users",[]) if x.get("active",True) and x.get("name")]

def ensure31(data):
    for key in ["staffing_objects","infrastructure_objects","location_objects","telemedicine_objects","service_objects","sync_proposals","agent_suggestions","briefing_history","suggestion_queue"]: data.setdefault(key,[])
    data.setdefault("object_comments",{})
    data.setdefault("recruitment_settings",{"recruitment_lead_months":18,"utilization_trigger_pct":85.0,"shortage_trigger_slots":0.0})
    for _,bucket in BUCKETS:
        for x in data[bucket]:
            x["status"]=migrate_status(x.get("status")); x.setdefault("needs_executive_decision",False); x.setdefault("submitted_by",x.get("created_by",x.get("owner",""))); x.setdefault("submitted_at",x.get("created_at",now()))
    for x in data.get("draft_items",[]):
        x["status"]=migrate_status(x.get("status")); x.setdefault("needs_executive_decision",False)
    for s in data.get("suggestions",[]):
        if not any(q.get("legacy_id")==s.get("id") for q in data["suggestion_queue"]):
            data["suggestion_queue"].append({"id":s.get("id","SUG-"+uuid4().hex[:8]),"legacy_id":s.get("id"),"section":"General Strategy","title":str(s.get("text","Suggestion"))[:100],"description":s.get("text",""),"submitted_by":s.get("user","Unknown"),"submitted_at":s.get("time",now()),"reviewer":"Jackie Gurr","status":"Suggestion","archive_reason":""})
    return data

def visible31(x,user,executive=False):
    status=migrate_status(x.get("status"))
    if status=="Suggestion":
        return executive and leadership_context(x,user)
    sharing=x.get("sharing","Everyone")
    return (
        sharing=="Everyone"
        or x.get("owner")==user
        or x.get("created_by")==user
        or user in x.get("shared_with",[])
    )

def leadership_context(x,user): return user in {x.get("reviewer"),x.get("owner"),x.get("created_by"),"Jeffrey Sacks","Jackie Gurr"}

def submit_suggestion(data,extra,save_extra,user,section,bucket):
    with st.expander("💡 Submit a Suggestion",False):
        title=st.text_input("Suggestion title",key="sug31_"+bucket+"_title")
        description=st.text_area("Suggestion",key="sug31_"+bucket+"_desc")
        reviewer=st.selectbox("Send for review to",["Jackie Gurr","Jeffrey Sacks"],key="sug31_"+bucket+"_reviewer")
        if st.button("Submit Suggestion",type="primary",key="sug31_"+bucket+"_submit"):
            if not title.strip(): st.error("A title is required.")
            else:
                data["suggestion_queue"].append({"id":"SUG-"+uuid4().hex[:8],"section":section,"bucket":bucket,"title":title.strip(),"description":description.strip(),"submitted_by":user,"submitted_at":now(),"reviewer":reviewer,"status":"Suggestion","archive_reason":"","comments":[]})
                save_extra(extra); st.rerun()

def comments(data,extra,save_extra,user,item_id):
    thread=data["object_comments"].setdefault(item_id,[])
    for c in thread: st.caption(f"{c.get('user')} | {c.get('time')}: {c.get('text')}")
    text=st.text_input("Comment",key=item_id+"_comment31")
    if st.button("Add Comment",key=item_id+"_comment31_add") and text.strip(): thread.append({"user":user,"time":now(),"text":text.strip()});save_extra(extra);st.rerun()

def object_header(data,extra,user,key,x):
    status=migrate_status(x.get("status")); x["status"]=status
    if leadership(data,user):
        status=st.selectbox("Status",STATUSES,index=STATUSES.index(status),key=key+"_status31")
        needs=st.checkbox("Needs Executive Decision",value=bool(x.get("needs_executive_decision",False)),key=key+"_need31")
        sharing=x.get("sharing","Selected people")
        shared=x.get("shared_with",[])
        sharing=st.selectbox("Share with",["Only me","Selected people","Everyone"],index=["Only me","Selected people","Everyone"].index(sharing) if sharing in ["Only me","Selected people","Everyone"] else 1,key=key+"_sharing31")
        if sharing=="Selected people":
            shared=st.multiselect("Selected people",people(extra),default=[p for p in shared if p in people(extra)],key=key+"_people31")
        elif sharing!="Selected people":
            shared=[]
        return status,needs,sharing,shared
    return status,bool(x.get("needs_executive_decision",False)),"Everyone",[]

def review_queue(data,extra,save_extra,user):
    st.subheader("Suggestions Awaiting Review")
    pending=[x for x in data["suggestion_queue"] if x.get("status")=="Suggestion"]
    if not pending: st.info("No suggestions are awaiting review.")
    for x in pending:
        with st.expander(f"{x.get('title')} | {x.get('section')} | Reviewer: {x.get('reviewer')}"):
            st.write(x.get("description","")); st.caption(f"Submitted by {x.get('submitted_by')} | {x.get('submitted_at')}")
            comments(data,extra,save_extra,user,x["id"])
            if leadership(data,user):
                reviewer=st.selectbox("Reviewer",["Jackie Gurr","Jeffrey Sacks"],index=0 if x.get("reviewer")!="Jeffrey Sacks" else 1,key=x["id"]+"_reviewer31")
                x["reviewer"]=reviewer
                a,b=st.columns(2)
                if a.button("Promote to Idea",type="primary",key=x["id"]+"_promote31"):
                    bucket=x.get("bucket") or "service_objects"
                    if bucket not in dict((b,a) for a,b in BUCKETS).values(): bucket="service_objects"
                    data[bucket].append({"id":bucket[:3].upper()+"-"+uuid4().hex[:8],"title":x.get("title"),"description":x.get("description"),"owner":reviewer,"created_by":x.get("submitted_by"),"submitted_by":x.get("submitted_by"),"submitted_at":x.get("submitted_at"),"status":"Idea","priority":"Medium","horizon":"1 Year","sharing":"Everyone","shared_with":[],"needs_executive_decision":False,"created_at":now(),"updated_at":now()});x["status"]="Promoted";save_extra(extra);st.rerun()
                if b.button("Archive Suggestion",key=x["id"]+"_archive31"): st.session_state[x["id"]+"_archive_open31"]=True
                if st.session_state.get(x["id"]+"_archive_open31"):
                    reason=st.selectbox("Archive reason",ARCHIVE_REASONS,key=x["id"]+"_reason31")
                    if st.button("Confirm Archive",key=x["id"]+"_confirm31"): x["status"]="Archived";x["archive_reason"]=reason;save_extra(extra);st.rerun()

def governance_counts(data):
    all_items=[x for _,b in BUCKETS for x in data.get(b,[])]+data.get("draft_items",[])
    return {"Suggestions Awaiting Review":sum(x.get("status")=="Suggestion" for x in data.get("suggestion_queue",[])),"Ideas":sum(migrate_status(x.get("status"))=="Idea" for x in all_items),"Planning":sum(migrate_status(x.get("status"))=="Planning" for x in all_items),"Approved":sum(migrate_status(x.get("status"))=="Approved" for x in all_items),"In Progress":sum(migrate_status(x.get("status"))=="In Progress" for x in all_items),"Needs Executive Decision":sum(bool(x.get("needs_executive_decision")) and migrate_status(x.get("status"))!="Archived" for x in all_items)}

def render_governance_home(extra):
    data=ensure31(extra.setdefault("growth_strategy_26",{}));counts=governance_counts(data);st.markdown("### Strategic Governance");cols=st.columns(6)
    for col,(label,value) in zip(cols,counts.items()): col.metric(label,value)
