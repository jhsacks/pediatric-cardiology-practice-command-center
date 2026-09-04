from pathlib import Path
p=Path("growth_strategy_30.py");s=p.read_text()
imp='from growth_governance_31 import ensure31, visible31, leadership, submit_suggestion, comments, object_header, review_queue\n'
if imp not in s:s=s.replace('import streamlit as st\n','import streamlit as st\n'+imp,1)
s=s.replace('OBJECT_STATUSES = ["Idea", "Discovery", "Feasibility", "Business Case", "Approved", "Building", "Launch Ready", "Live", "Scaling", "Deferred", "Archived"]','OBJECT_STATUSES = ["Executive Brainstorming", "Suggestion", "Idea", "Planning", "Approved", "In Progress", "Archived"]')
s=s.replace('    ensure(data)\n    tabs=st.tabs(["📍 Location Strategy","💻 Telemedicine Engine","👥 Staffing Plan","🩻 Infrastructure Plan","🫀 Clinical Services","🔄 Roadmap Sync","👨‍⚕️ Recruitment Forecast","💡 Agent Suggestions","📋 Leadership Brief"])','    ensure(data); ensure31(data)\n    tabs=st.tabs(["📍 Location Strategy","💻 Telemedicine Engine","👥 Staffing Plan","🩻 Infrastructure Plan","🫀 Clinical Services","📨 Review Suggestions","🔄 Roadmap Sync","👨‍⚕️ Recruitment Forecast","💡 Agent Suggestions","📋 Leadership Brief"])')
s=s.replace('    with tabs[5]:sync_tab(data,extra,save_extra,user)\n    with tabs[6]:recruitment_tab(data,extra,save_extra,user)\n    with tabs[7]:agent_suggestions_tab(data,extra,save_extra,user)\n    with tabs[8]:briefing_tab(data,extra,save_extra,user)','    with tabs[5]:review_queue(data,extra,save_extra,user)\n    with tabs[6]:sync_tab(data,extra,save_extra,user)\n    with tabs[7]:recruitment_tab(data,extra,save_extra,user)\n    with tabs[8]:agent_suggestions_tab(data,extra,save_extra,user)\n    with tabs[9]:briefing_tab(data,extra,save_extra,user)')
# Suggestions in each strategic object section.
needle='    st.subheader(title)\n'
if 'submit_suggestion(data,extra,save_extra,user,title,bucket)' not in s:s=s.replace(needle,needle+'    submit_suggestion(data,extra,save_extra,user,title,bucket)\n',1)
# Status migration and visibility.
s=s.replace('        if not visible(x,user) or x.get("status")=="Archived": continue','        ensure31(data)\n        if not visible31(x,user,executive=leadership(data,user)) or x.get("status")=="Archived": continue')
# Simplified roadmap sync statuses and generated status.
s=s.replace('x.get("status") in {"Approved","Building","Launch Ready","Live","Scaling"}','x.get("status") in {"Approved","In Progress"}')
s=s.replace('"status":"Draft"','"status":"Idea"')
p.write_text(s)
print('Growth Strategy governance patched')
