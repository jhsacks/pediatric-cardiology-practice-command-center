from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
import re

import pandas as pd
import streamlit as st
from strategy_agent_29 import enhanced_conversational_response
from roadmap_editor import render_roadmap_editor

HORIZONS = ["1 Year", "3 Years", "5 Years", "10-Year Vision"]
DOMAINS = ["Vision", "Physician Workforce", "Locations & Access", "Telemedicine", "Clinical Services", "Staffing", "Equipment & Infrastructure", "Hospital Integration", "Quality", "Finance"]
SERVICES = ["General Pediatric Cardiology", "Fetal Cardiology", "Advanced Cardiac Imaging", "Pediatric Electrophysiology", "Interventional Pediatric Cardiology", "Adult Congenital Cardiology", "Pediatric Cardiac Surgery", "NICU / PICU Integration", "Telemedicine"]
STAGES = ["Idea", "Discovery", "Feasibility", "Business Case", "Approved", "Building", "Launch Ready", "Live", "Scaling"]
GOVERNANCE = ["Suggestion", "Draft", "Under Review", "Approved", "Published", "Deferred", "Declined", "Superseded"]
SHARING = ["Everyone", "Selected people", "Only me"]
DEFAULT_ROLES = {"owner": "Jeffrey Sacks", "editor": "Jackie Gurr"}


def now(): return datetime.now(timezone.utc).isoformat()

def ensure(extra):
    data = extra.setdefault("growth_strategy_26", {})
    data.setdefault("roles", deepcopy(DEFAULT_ROLES))
    data.setdefault("published_version", None)
    data.setdefault("versions", [])
    data.setdefault("draft_items", [])
    data.setdefault("suggestions", [])
    data.setdefault("comments", {})
    data.setdefault("agent_history", {})
    data.setdefault("readiness", [])
    data.setdefault("location_plans", [])
    data.setdefault("workforce_plans", [])
    data.setdefault("telemedicine_plans", [])
    data.setdefault("strategy_inputs", {})
    return data

def user_name(current_user, executive):
    if executive: return "Jeffrey Sacks"
    return (current_user or {}).get("name") or "Current User"

def active_people(extra):
    return [str(x.get("name")) for x in extra.get("collaboration",{}).get("users",[]) if x.get("active",True) and x.get("name")]

def role(data, user):
    if user == data["roles"].get("owner"): return "Owner"
    if user == data["roles"].get("editor"): return "Editor"
    return "Contributor"

def can_edit(data,user): return role(data,user) in ["Owner","Editor"]
def can_publish(data,user): return role(data,user)=="Owner"

def infer_horizon(text):
    t=text.lower()
    if re.search(r"\b10\s*[- ]?year|ten year|long[- ]term vision",t): return "10-Year Vision"
    if re.search(r"\b5\s*[- ]?year|five year",t): return "5 Years"
    if re.search(r"\b3\s*[- ]?year|three year",t): return "3 Years"
    return "1 Year"

def infer_domain(text):
    t=text.lower()
    if any(x in t for x in ["telemedicine","telehealth","virtual","remote"]): return "Telemedicine"
    if any(x in t for x in ["doctor","physician","recruit","hire","provider"]): return "Physician Workforce"
    if any(x in t for x in ["clinic","location","site","griffin","paulding","acworth","woodstock","lagrange","spalding"]): return "Locations & Access"
    if any(x in t for x in ["equipment","echo","probe","ekg","space","infrastructure","room"]): return "Equipment & Infrastructure"
    if any(x in t for x in ["staff","nurse","ma","sonographer","front office"]): return "Staffing"
    if any(x in t for x in ["ep","electrophysiology","interventional","adult congenital","achd","surgery","fetal","imaging","service"]): return "Clinical Services"
    return "Vision"

def infer_service(text):
    t=text.lower()
    mapping=[("Pediatric Electrophysiology",["electrophysiology"," ep ","ablation","device"]),("Interventional Pediatric Cardiology",["interventional","cath lab","catheterization"]),("Adult Congenital Cardiology",["adult congenital","achd"]),("Pediatric Cardiac Surgery",["cardiac surgery","surgical program"]),("Fetal Cardiology",["fetal","mfm"]),("Advanced Cardiac Imaging",["imaging","mri","ct"]),("Telemedicine",["telemedicine","telehealth","virtual"]),("NICU / PICU Integration",["nicu","picu","hospital integration"])]
    padded=" "+t+" "
    for service,terms in mapping:
        if any(term in padded for term in terms): return service
    return "General Pediatric Cardiology"

def precise_prompt(domain,horizon):
    examples={
      "Telemedicine":f"Model a {horizon.lower()} hybrid telemedicine and in-person access plan for Griffin, including visit types, local support, diagnostics, staffing, technology, dependencies, milestones, and success measures.",
      "Physician Workforce":f"Create a {horizon.lower()} physician workforce plan using projected demand, recruitment lead time, clinic coverage, subspecialty needs, hospital duties, and trigger points for starting recruitment.",
      "Locations & Access":f"Evaluate location and clinic-day expansion over {horizon.lower()}, including demand, current capacity, physician days, staffing, equipment, space, telemedicine options, and launch criteria.",
      "Clinical Services":f"Develop a {horizon.lower()} readiness roadmap for the proposed clinical service, including demand, physician expertise, hospital support, staffing, equipment, quality, finance, dependencies, and launch stage.",
      "Equipment & Infrastructure":f"Identify the equipment, space, technology, hospital, and capital infrastructure required over {horizon.lower()} to support the proposed growth strategy.",
      "Staffing":f"Build a {horizon.lower()} staffing plan tied to physician growth, clinic expansion, outreach, telemedicine, diagnostic volume, and new clinical services.",
      "Vision":f"Draft an integrated {horizon.lower()} pediatric cardiology growth strategy covering workforce, locations, telemedicine, clinical services, staffing, equipment, hospital integration, risks, milestones, and measures.",
    }
    return examples.get(domain,examples["Vision"])

def context_summary(extra):
    planning=extra.get("strategic_planning_12",{}); collaboration=extra.get("collaboration",{}); demand=planning.get("demand",[]); scenarios=planning.get("scenarios",{})
    return {"sites":len(demand),"shared_scenarios":len(scenarios),"initiatives":len(collaboration.get("initiatives",[])),"decisions":len(collaboration.get("decisions",[])),"growth_items":len(collaboration.get("practice_growth",[])),"risks":len(planning.get("risks",[])),"milestones":len(planning.get("milestones",[]))}

def conversational_response(prompt,extra):
    horizon=infer_horizon(prompt); domain=infer_domain(prompt); service=infer_service(prompt); ctx=context_summary(extra)
    intro=f"I would approach this as a **{horizon} {domain.lower()} strategy**"
    if service!="General Pediatric Cardiology": intro+=f" centered on **{service}**"
    intro+="."
    telemedicine=(" Telemedicine should be tested as an access, outreach, follow-up, diagnostic-review, and provider-to-provider support option at every stage, not treated as a separate side project.")
    questions={
      "Telemedicine":["Which locations or populations should be prioritized?","Which visit types are appropriate for the proposed model?","What local clinical and diagnostic support is available?","What would trigger expansion, redesign, or discontinuation?"],
      "Physician Workforce":["What demand or utilization threshold should trigger recruitment?","Which competencies and geographic responsibilities are required?","What recruitment lead time should the roadmap assume?","What staffing, call, and hospital coverage changes follow each hire?"],
      "Locations & Access":["What are current demand, capacity, and next-available access?","Should growth be in-person, telemedicine, or hybrid?","What staffing, equipment, space, and diagnostic support are ready?","What launch and exit criteria should leadership approve?"],
      "Clinical Services":["What patient demand and referral base support the service?","What physician expertise, partnerships, and hospital capabilities are required?","What staffing, equipment, quality, registry, and financial work is needed?","Which dependencies must be completed before launch?"],
      "Vision":["What should be true at the end of this horizon?","Which locations, services, and patient populations matter most?","What workforce, infrastructure, and partnerships are required?","Which commitments belong in the official baseline versus a working draft?"]
    }
    qs=questions.get(domain,questions["Vision"])
    roadmap=[f"Define the desired {horizon.lower()} outcome and success measures",f"Validate demand, access, capacity, and readiness inputs for {ctx['sites']} modeled sites",f"Choose the service, location, workforce, and telemedicine sequence",f"Identify staffing, equipment, space, hospital, quality, financial, and technology dependencies",f"Create linked decisions, initiatives, risks, and milestones",f"Review with Jeffrey and Jackie before publishing the baseline"]
    return {"horizon":horizon,"domain":domain,"service":service,"answer":intro+telemedicine,"questions":qs,"roadmap":roadmap,"suggested_prompt":precise_prompt(domain,horizon)}

def save_proposal(data,user,response,prompt,sharing="Only me",selected=None):
    data["draft_items"].append({"id":"GST-"+uuid4().hex[:8],"title":prompt[:100] or "Strategy Proposal","description":response["answer"],"horizon":response["horizon"],"domain":response["domain"],"service":response["service"],"questions":response["questions"],"roadmap":response["roadmap"],"owner":user,"status":"Draft","sharing":sharing,"shared_with":selected or [],"created_at":now(),"updated_at":now()})

def agent_tab(extra,data,save_extra,user):
    history=data["agent_history"].setdefault(user,[])
    st.caption("Ask naturally. The agent will only suggest more precise language when a more specific request would materially improve the plan.")
    starters=["Help me think through our growth strategy","How could telemedicine expand access?","When should we add another physician?","What should our long-term clinical services roadmap look like?"]
    cols=st.columns(2)
    for i,text in enumerate(starters):
        if cols[i%2].button(text,key=f"starter_{i}",use_container_width=True): st.session_state["growth_agent_prompt"]=text
    prompt=st.text_area("Talk to the Strategy Agent",value=st.session_state.get("growth_agent_prompt",""),height=120,placeholder="For example: We do not go to Griffin often. How could we expand access without immediately adding another full clinic day?")
    if st.button("Analyze",type="primary") and prompt.strip():
        response=enhanced_conversational_response(prompt,extra); history.append({"prompt":prompt,"response":response,"time":now()}); save_extra(extra); st.session_state["growth_agent_last"]=response
    response=st.session_state.get("growth_agent_last") or (history[-1]["response"] if history else None)
    if response:
        st.markdown(response["answer"])
        if response.get("context"):
            st.markdown("#### What I considered")
            for line in response["context"]:
                st.write("• " + line)
        st.markdown("#### Questions worth answering")
        for q in response["questions"]: st.write("• "+q)
        st.markdown("#### Proposed roadmap structure")
        for step in response["roadmap"]: st.write("• "+step)
        with st.expander("Suggested wording if you want a more specific analysis"):
            st.code(response["suggested_prompt"],language=None)
        share=st.selectbox("Save proposal as",SHARING,key="agent_save_share"); selected=[]
        if share=="Selected people": selected=st.multiselect("Share proposal with",active_people(extra),key="agent_save_people")
        if st.button("Save as Strategy Draft"):
            save_proposal(data,user,response,prompt,share,selected); save_extra(extra); st.success("Saved to the working strategy draft.")

def grid_tab(data,key,label,columns,save_extra,extra,editable):
    st.subheader(label); frame=pd.DataFrame(data[key]); edited=st.data_editor(frame,hide_index=True,use_container_width=True,num_rows="dynamic" if editable else "fixed",disabled=not editable,key="gs_"+key)
    if editable and st.button("Save "+label,key="save_"+key): data[key]=edited.where(pd.notna(edited),"").to_dict("records"); save_extra(extra); st.rerun()

def roadmap_tab(data,extra,save_extra,user):
    items=data["draft_items"]; st.subheader("1 / 3 / 5 / 10-Year Roadmap")
    for horizon in HORIZONS:
        with st.expander(horizon,expanded=True):
            subset=[x for x in items if x.get("horizon")==horizon and x.get("status") not in ["Declined","Superseded"]]
            if not subset: st.caption("No items yet.")
            for item in subset:
                st.markdown(f"**{item.get('title')}**")
                st.caption(f"{item.get('domain')} | {item.get('service')} | {item.get('status')} | Owner: {item.get('owner')}")
                st.write(item.get("description",""))
                with st.expander("Roadmap steps, comments, and governance"):
                    for step in item.get("roadmap",[]): st.write("• "+step)
                    comments=data["comments"].setdefault(item["id"],[])
                    for c in comments: st.caption(f"{c['user']}: {c['text']}")
                    comment=st.text_input("Comment or suggestion",key=item["id"]+"_comment")
                    if st.button("Add comment",key=item["id"]+"_add_comment") and comment.strip(): comments.append({"user":user,"text":comment.strip(),"time":now()}); save_extra(extra); st.rerun()
                    if can_edit(data,user):
                        status=st.selectbox("Governance status",GOVERNANCE,index=GOVERNANCE.index(item.get("status","Draft")) if item.get("status") in GOVERNANCE else 1,key=item["id"]+"_status")
                        if st.button("Save status",key=item["id"]+"_save_status"): item["status"]=status;item["updated_at"]=now();save_extra(extra);st.rerun()
                    if can_publish(data,user) and st.button("Publish as official baseline",key=item["id"]+"_publish"):
                        version={"version":f"{len(data['versions'])+1}.0","published_at":now(),"published_by":user,"items":deepcopy([x for x in items if x.get("status") in ["Approved","Published"]])}; data["versions"].append(version);data["published_version"]=version;item["status"]="Published";save_extra(extra);st.rerun()

def render_growth_strategy(extra,save_extra,current_user=None,executive=False):
    data=ensure(extra); user=user_name(current_user,executive); user_role=role(data,user)
    st.header("🧭 Growth Strategy"); st.caption(f"Working as {user} | Role: {user_role}")
    tabs=st.tabs(["💬 Strategy Agent","🎯 Vision","📍 Locations & Access","💻 Telemedicine","👨‍⚕️ Physician Workforce","🫀 Clinical Services","👥 Staffing","🩻 Infrastructure","🗺️ Roadmap","💡 Suggestions","📊 Leadership View"])
    with tabs[0]: agent_tab(extra,data,save_extra,user)
    with tabs[1]:
        st.subheader("Strategic Vision"); vision=data["strategy_inputs"].get("vision",""); edited=st.text_area("What should the practice become?",vision,height=220,disabled=not can_edit(data,user))
        if can_edit(data,user) and st.button("Save Vision"): data["strategy_inputs"]["vision"]=edited;save_extra(extra);st.rerun()
    with tabs[2]: grid_tab(data,"location_plans","Locations & Access",[],save_extra,extra,can_edit(data,user))
    with tabs[3]: grid_tab(data,"telemedicine_plans","Telemedicine",[],save_extra,extra,can_edit(data,user))
    with tabs[4]: grid_tab(data,"workforce_plans","Physician Workforce",[],save_extra,extra,can_edit(data,user))
    with tabs[5]: grid_tab(data,"readiness","Clinical Service Readiness",[],save_extra,extra,can_edit(data,user))
    with tabs[6]: st.info("Staffing needs are captured as roadmap dependencies and linked initiatives in this first release.")
    with tabs[7]: st.info("Equipment, space, technology, and hospital infrastructure needs are captured as roadmap dependencies in this first release.")
    with tabs[8]: render_roadmap_editor(data, extra, save_extra, user, executive=executive)
    with tabs[9]:
        st.subheader("Suggestions"); suggestion=st.text_area("Suggest a roadmap item, risk, service, location, or assumption change")
        if st.button("Submit suggestion") and suggestion.strip(): data["suggestions"].append({"id":"SUG-"+uuid4().hex[:8],"user":user,"text":suggestion.strip(),"status":"Suggestion","time":now()});save_extra(extra);st.rerun()
        for x in data["suggestions"]: st.write(f"**{x['user']}**: {x['text']} ({x['status']})")
    with tabs[10]:
        version=data.get("published_version"); st.subheader("Leadership View")
        if version: st.success(f"Published baseline version {version['version']} | Published by {version['published_by']}"); st.dataframe(pd.DataFrame(version["items"]),hide_index=True,use_container_width=True)
        else: st.info("No official baseline has been published yet.")
