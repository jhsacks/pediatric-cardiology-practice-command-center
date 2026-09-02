from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

HORIZONS = ["1 Year", "3 Years", "5 Years", "10-Year Vision"]
OBJECT_STATUSES = ["Idea", "Discovery", "Feasibility", "Business Case", "Approved", "Building", "Launch Ready", "Live", "Scaling", "Deferred", "Archived"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
SHARING = ["Everyone", "Selected people", "Only me"]
TELEMEDICINE_MODELS = ["In-person only", "Telemedicine only", "Hybrid", "Telemedicine between in-person clinics", "Local diagnostics + remote cardiology", "Provider-to-provider consultation", "Needs evaluation", "Not appropriate"]


def now(): return datetime.now(timezone.utc).isoformat()

def ensure(data):
    for key in ["staffing_objects", "infrastructure_objects", "location_objects", "telemedicine_objects", "service_objects", "sync_proposals", "agent_suggestions", "briefing_history"]:
        data.setdefault(key, [])
    data.setdefault("recruitment_settings", {"recruitment_lead_months": 18, "utilization_trigger_pct": 85.0, "shortage_trigger_slots": 0.0})
    return data

def people(extra): return [str(x.get("name")) for x in extra.get("collaboration",{}).get("users",[]) if x.get("active",True) and x.get("name")]
def role(data,user):
    if user == data.get("roles",{}).get("owner"): return "Owner"
    if user == data.get("roles",{}).get("editor"): return "Editor"
    return "Contributor"
def editable(data,user): return role(data,user) in {"Owner","Editor"}
def visible(x,user): return x.get("sharing","Everyone")=="Everyone" or x.get("owner")==user or x.get("created_by")==user or (x.get("sharing")=="Selected people" and user in x.get("shared_with",[]))
def opts(values,current): return values.index(current) if current in values else 0
def text_list(value): return "\n".join(value) if isinstance(value,list) else str(value or "")
def list_text(value): return [x.strip() for x in str(value or "").splitlines() if x.strip()]

def common_fields(extra,user,key,x):
    names=people(extra); a,b,c=st.columns(3)
    owner=a.selectbox("Owner",names,index=names.index(x.get("owner",user)) if x.get("owner",user) in names else 0,key=key+"_owner") if names else user
    horizon=b.selectbox("Horizon",HORIZONS,index=opts(HORIZONS,x.get("horizon","1 Year")),key=key+"_horizon")
    priority=c.selectbox("Priority",PRIORITIES,index=opts(PRIORITIES,x.get("priority","Medium")),key=key+"_priority")
    d,e=st.columns(2); status=d.selectbox("Status",OBJECT_STATUSES,index=opts(OBJECT_STATUSES,x.get("status","Discovery")),key=key+"_status"); target=e.text_input("Target date or period",x.get("target_date",""),key=key+"_target")
    sharing=st.selectbox("Share with",SHARING,index=opts(SHARING,x.get("sharing","Selected people")),key=key+"_sharing"); shared=[]
    if sharing=="Selected people": shared=st.multiselect("Selected people",[n for n in names if n!=owner],default=[n for n in x.get("shared_with",[]) if n in names and n!=owner],key=key+"_people")
    return {"owner":owner,"horizon":horizon,"priority":priority,"status":status,"target_date":target,"sharing":sharing,"shared_with":shared}

def save_object(data,bucket,extra,save_extra,user,x,values,new=False):
    x.update(values); x.setdefault("id",bucket[:3].upper()+"-"+uuid4().hex[:8]); x.setdefault("created_by",user); x.setdefault("created_at",now()); x["updated_by"]=user; x["updated_at"]=now()
    if new: data[bucket].append(x)
    save_extra(extra); st.rerun()

def object_module(data,extra,save_extra,user,bucket,title,kind_fields):
    st.subheader(title)
    if editable(data,user):
        with st.expander("➕ Add "+title.rstrip("s"),False):
            x={"owner":user,"sharing":"Selected people","shared_with":[data.get("roles",{}).get("editor","Jackie Gurr")]}; values={}
            values["title"]=st.text_input("Name",key="new_"+bucket+"_title"); values["description"]=st.text_area("Purpose / need",key="new_"+bucket+"_description"); values.update(common_fields(extra,user,"new_"+bucket,x))
            for label,name,kind,choices in kind_fields:
                if kind=="text": values[name]=st.text_input(label,key="new_"+bucket+"_"+name)
                elif kind=="area": values[name]=list_text(st.text_area(label+" (one per line)",key="new_"+bucket+"_"+name))
                elif kind=="select": values[name]=st.selectbox(label,choices,key="new_"+bucket+"_"+name)
                elif kind=="number": values[name]=st.number_input(label,value=0.0,key="new_"+bucket+"_"+name)
            if st.button("Create",type="primary",key="create_"+bucket):
                if not values["title"].strip(): st.error("Name is required.")
                else: save_object(data,bucket,extra,save_extra,user,x,values,True)
    for x in list(data[bucket]):
        if not visible(x,user) or x.get("status")=="Archived": continue
        with st.expander(f"{x.get('title','Untitled')} | {x.get('priority','Medium')} | {x.get('status','Discovery')}"):
            if editable(data,user):
                values={"title":st.text_input("Name",x.get("title",""),key=x["id"]+"_title"),"description":st.text_area("Purpose / need",x.get("description",""),key=x["id"]+"_description")}; values.update(common_fields(extra,user,x["id"],x))
                for label,name,kind,choices in kind_fields:
                    if kind=="text": values[name]=st.text_input(label,x.get(name,""),key=x["id"]+"_"+name)
                    elif kind=="area": values[name]=list_text(st.text_area(label+" (one per line)",text_list(x.get(name,[])),key=x["id"]+"_"+name))
                    elif kind=="select": values[name]=st.selectbox(label,choices,index=opts(choices,x.get(name,choices[0])),key=x["id"]+"_"+name)
                    elif kind=="number": values[name]=st.number_input(label,value=float(x.get(name,0) or 0),key=x["id"]+"_"+name)
                a,b=st.columns(2)
                if a.button("💾 Save",type="primary",key=x["id"]+"_save"): save_object(data,bucket,extra,save_extra,user,x,values)
                if b.button("📦 Archive",key=x["id"]+"_archive"): x["status"]="Archived";save_extra(extra);st.rerun()
            else: st.write(x.get("description",""))

def location_fields(): return [("Current state","current_state","area",None),("Desired state","desired_state","area",None),("Growth drivers","growth_drivers","area",None),("Access strategy","access_strategy","select",["Optimize current schedule","Add telemedicine","Add clinic sessions","Permanent expansion","Needs evaluation"]),("Current clinic days/week","current_days","number",None),("Desired clinic days/week","desired_days","number",None),("Dependencies","dependencies","area",None),("Risks","risks","area",None),("Success measures","success_measures","area",None)]
def staffing_fields(): return [("Role / FTE","role_fte","text",None),("Location / region","location","text",None),("Trigger","trigger","text",None),("Lead time","lead_time","text",None),("Linked services or locations","links","area",None),("Dependencies","dependencies","area",None)]
def infrastructure_fields(): return [("Location","location","text",None),("Need type","need_type","select",["Equipment","Space","Technology","Hospital capability","Diagnostic capability","Capital","Other"]),("Estimated cost","estimated_cost","text",None),("Required before","required_before","text",None),("Dependencies","dependencies","area",None)]
def telemedicine_fields(): return [("Locations / populations","locations","text",None),("Model","model","select",TELEMEDICINE_MODELS),("Eligible visit types","visit_types","area",None),("Local support","local_support","area",None),("Diagnostics","diagnostics","area",None),("Technology / compliance","technology","area",None),("Success measures","success_measures","area",None),("Expansion trigger","expansion_trigger","text",None)]
def service_fields(): return [("Service","service","text",None),("Demand evidence","demand","area",None),("Expertise / partnership model","expertise","area",None),("Hospital capabilities","hospital","area",None),("Staffing needs","staffing","area",None),("Infrastructure needs","infrastructure","area",None),("Quality / registry needs","quality","area",None),("Financial case","financial","area",None),("Dependencies","dependencies","area",None),("Next decision","next_decision","text",None)]

def roadmap_items(data): return data.get("draft_items",[])
def create_sync_proposals(data):
    existing={(p.get("source_type"),p.get("source_id"),p.get("action")) for p in data["sync_proposals"] if p.get("status")=="Pending"}
    mapping=[("Staffing","staffing_objects"),("Infrastructure","infrastructure_objects"),("Location","location_objects"),("Telemedicine","telemedicine_objects"),("Clinical Service","service_objects")]
    added=0
    for source_type,bucket in mapping:
        for x in data[bucket]:
            if x.get("status") in {"Approved","Building","Launch Ready","Live","Scaling"} and (source_type,x["id"],"Create roadmap item") not in existing:
                data["sync_proposals"].append({"id":"SYN-"+uuid4().hex[:8],"source_type":source_type,"source_id":x["id"],"source_title":x.get("title"),"action":"Create roadmap item","horizon":x.get("horizon","1 Year"),"reason":f"{source_type} object reached {x.get('status')}","status":"Pending","created_at":now()});added+=1
    return added

def sync_tab(data,extra,save_extra,user):
    st.subheader("Review Proposed Roadmap Updates")
    if editable(data,user) and st.button("Scan Strategy for Roadmap Implications"):
        added=create_sync_proposals(data);save_extra(extra);st.success(f"{added} new proposal(s) created.");st.rerun()
    for p in data["sync_proposals"]:
        if p.get("status")!="Pending": continue
        with st.expander(f"{p['action']}: {p['source_title']}"):
            st.write(p["reason"]);st.caption(f"Suggested horizon: {p['horizon']}")
            if editable(data,user):
                a,b=st.columns(2)
                if a.button("Apply to Roadmap",type="primary",key=p["id"]+"_apply"):
                    data.setdefault("draft_items",[]).append({"id":"GST-"+uuid4().hex[:8],"title":p["source_title"],"description":p["reason"],"horizon":p["horizon"],"domain":p["source_type"],"service":"General Pediatric Cardiology","owner":user,"status":"Draft","priority":"High","sharing":"Selected people","shared_with":[data.get("roles",{}).get("editor","Jackie Gurr")],"roadmap":["Validate the strategic object","Resolve dependencies","Create linked initiative and decision","Review progress and outcomes"],"dependencies":[],"risks":[],"success_measures":[],"created_at":now(),"updated_at":now()});p["status"]="Applied";save_extra(extra);st.rerun()
                if b.button("Dismiss",key=p["id"]+"_dismiss"):p["status"]="Dismissed";save_extra(extra);st.rerun()

def recommendation_dates(planning,settings):
    def safe_number(value, default=0.0):
        try:
            number = float(value)
            return number if number == number else default
        except (TypeError, ValueError, OverflowError):
            return default

    scenarios = planning.get("scenarios", {})
    demand_rows = planning.get("demand", [])
    assumptions = planning.get("assumptions", {})
    visits = safe_number(assumptions.get("Visits per full clinic day", 11), 11.0)
    weeks = safe_number(assumptions.get("Effective operating weeks", 45.2), 45.2)
    trigger = safe_number(settings.get("utilization_trigger_pct", 85.0), 85.0)
    output = []

    for scenario, allocation in scenarios.items():
        capacity = 0.0
        values = allocation.values() if isinstance(allocation, dict) else []
        for days in values:
            capacity += safe_number(days, 0.0) * visits * weeks

        demand = 0.0
        for row in demand_rows if isinstance(demand_rows, list) else []:
            if not isinstance(row, dict):
                continue
            override = row.get("FY27 Override")
            base = safe_number(row.get("FY26 Visits", 0), 0.0)
            growth = safe_number(row.get("Growth %", 0), 0.0)
            if override not in (None, "", "None"):
                demand += safe_number(override, base * (1 + growth / 100.0))
            else:
                demand += base * (1 + growth / 100.0)

        capacity = safe_number(capacity, 0.0)
        demand = safe_number(demand, 0.0)
        utilization = safe_number((demand / capacity * 100.0) if capacity > 0 else 999.0, 999.0)
        output.append({
            "Scenario": str(scenario),
            "Projected Demand": round(demand),
            "Capacity": round(capacity),
            "Utilization %": round(utilization, 1),
            "Recruitment Signal": "Begin planning" if utilization >= trigger else "Monitor",
        })
    return output

def recruitment_tab(data,extra,save_extra,user):
    st.subheader("Physician Recruitment Forecast")
    settings=data["recruitment_settings"]
    if editable(data,user):
        a,b=st.columns(2); settings["recruitment_lead_months"]=a.number_input("Recruitment and onboarding lead time (months)",min_value=1,value=int(settings.get("recruitment_lead_months",18))); settings["utilization_trigger_pct"]=b.number_input("Utilization trigger (%)",min_value=1.0,max_value=100.0,value=float(settings.get("utilization_trigger_pct",85.0)))
        if st.button("Save Recruitment Settings"):save_extra(extra);st.rerun()
    rows=recommendation_dates(extra.get("strategic_planning_12",{}),settings)
    if rows:st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    st.caption("The forecast is a planning signal based on saved scenario demand, capacity, effective operating weeks, and the selected utilization threshold. It does not assign a hiring date without a dated multi-year demand forecast.")

def briefing(data,extra):
    active=[x for x in roadmap_items(data) if x.get("status") not in {"Archived","Declined","Superseded"}]; high=[x for x in active if x.get("priority") in {"Critical","High"}]
    risks=extra.get("strategic_planning_12",{}).get("risks",[])
    return {"Generated":now(),"Active roadmap items":len(active),"High-priority roadmap items":len(high),"Staffing plans":len([x for x in data["staffing_objects"] if x.get("status")!="Archived"]),"Infrastructure plans":len([x for x in data["infrastructure_objects"] if x.get("status")!="Archived"]),"Location plans":len([x for x in data["location_objects"] if x.get("status")!="Archived"]),"Telemedicine plans":len([x for x in data["telemedicine_objects"] if x.get("status")!="Archived"]),"Clinical service plans":len([x for x in data["service_objects"] if x.get("status")!="Archived"]),"Strategic risks":len(risks)}
def briefing_tab(data,extra,save_extra,user):
    st.subheader("Leadership Brief")
    summary=briefing(data,extra);cols=st.columns(4)
    for i,(label,value) in enumerate(list(summary.items())[1:]):cols[i%4].metric(label,value)
    st.markdown("#### High-priority roadmap")
    for x in roadmap_items(data):
        if x.get("priority") in {"Critical","High"} and x.get("status") not in {"Archived","Declined","Superseded"}:st.write(f"• **{x.get('title')}** | {x.get('horizon')} | {x.get('status')} | Owner: {x.get('owner')}")
    st.markdown("#### Decisions and dependencies needing leadership attention")
    pending=[p for p in data["sync_proposals"] if p.get("status")=="Pending"]
    if pending:
        for p in pending:st.write(f"• {p.get('source_title')}: {p.get('reason')}")
    else:st.caption("No pending roadmap sync proposals.")
    if st.button("Save Briefing Snapshot"):data["briefing_history"].append(summary);save_extra(extra);st.success("Briefing snapshot saved.")

def agent_suggestions_tab(data,extra,save_extra,user):
    st.subheader("Proactive Strategy Suggestions")
    suggestions=[]
    planning=extra.get("strategic_planning_12",{})
    for row in recommendation_dates(planning,data["recruitment_settings"]):
        if row["Recruitment Signal"]=="Begin planning": suggestions.append({"title":f"Recruitment planning signal in {row['Scenario']}","reason":f"Projected utilization is {row['Utilization %']}%, at or above the saved trigger.","action":"Create a physician recruitment roadmap item"})
    for x in data["location_objects"]:
        if x.get("access_strategy")=="Add telemedicine" and not any(x.get("title") in str(t.get("locations","")) for t in data["telemedicine_objects"]): suggestions.append({"title":f"Telemedicine plan needed for {x.get('title')}","reason":"The location strategy calls for telemedicine but no linked telemedicine object was found.","action":"Create a telemedicine readiness plan"})
    data["agent_suggestions"]=suggestions
    if not suggestions:st.info("No proactive suggestions from the current saved data.")
    for i,s in enumerate(suggestions):
        with st.expander(s["title"]):st.write(s["reason"]);st.markdown("**Suggested action:** "+s["action"])

def render_growth_strategy_30(data,extra,save_extra,user,executive=False):
    ensure(data)
    tabs=st.tabs(["📍 Location Strategy","💻 Telemedicine Engine","👥 Staffing Plan","🩻 Infrastructure Plan","🫀 Clinical Services","🔄 Roadmap Sync","👨‍⚕️ Recruitment Forecast","💡 Agent Suggestions","📋 Leadership Brief"])
    with tabs[0]:object_module(data,extra,save_extra,user,"location_objects","Location Strategies",location_fields())
    with tabs[1]:object_module(data,extra,save_extra,user,"telemedicine_objects","Telemedicine Plans",telemedicine_fields())
    with tabs[2]:object_module(data,extra,save_extra,user,"staffing_objects","Staffing Plans",staffing_fields())
    with tabs[3]:object_module(data,extra,save_extra,user,"infrastructure_objects","Infrastructure Plans",infrastructure_fields())
    with tabs[4]:object_module(data,extra,save_extra,user,"service_objects","Clinical Service Plans",service_fields())
    with tabs[5]:sync_tab(data,extra,save_extra,user)
    with tabs[6]:recruitment_tab(data,extra,save_extra,user)
    with tabs[7]:agent_suggestions_tab(data,extra,save_extra,user)
    with tabs[8]:briefing_tab(data,extra,save_extra,user)
