from pathlib import Path
p=Path("growth_strategy.py");s=p.read_text();imp="from growth_strategy_30 import render_growth_strategy_30\n"
if imp not in s:s=s.replace("import streamlit as st\n","import streamlit as st\n"+imp,1)
needle='    tabs=st.tabs(["💬 Strategy Agent","🎯 Vision","📍 Locations & Access","💻 Telemedicine","👨‍⚕️ Physician Workforce","🫀 Clinical Services","👥 Staffing","🩻 Infrastructure","🗺️ Roadmap","💡 Suggestions","📊 Leadership View"])'
replacement='    tabs=st.tabs(["💬 Strategy Agent","🎯 Vision","🧩 Strategy Engine","🗺️ Roadmap","💡 Suggestions","📊 Leadership View"])'
if needle not in s and replacement not in s:raise SystemExit("Growth Strategy 26 tab structure not found")
if needle in s:
    start=s.index(needle); end=s.index('\ndef ',start) if '\ndef ' in s[start:] else len(s)
    old=s[start:end]
    new='''    tabs=st.tabs(["💬 Strategy Agent","🎯 Vision","🧩 Strategy Engine","🗺️ Roadmap","💡 Suggestions","📊 Leadership View"])
    with tabs[0]: agent_tab(extra,data,save_extra,user)
    with tabs[1]:
        st.subheader("Strategic Vision")
        vision=data["strategy_inputs"].get("vision","")
        edited=st.text_area("What should the practice become?",vision,height=220,disabled=not can_edit(data,user))
        if can_edit(data,user) and st.button("Save Vision"):
            data["strategy_inputs"]["vision"]=edited;save_extra(extra);st.rerun()
    with tabs[2]: render_growth_strategy_30(data, extra, save_extra, user, executive=executive)
    with tabs[3]: render_roadmap_editor(data, extra, save_extra, user, executive=executive)
    with tabs[4]:
        st.subheader("Suggestions")
        suggestion=st.text_area("Suggest a roadmap item, risk, service, location, or assumption change")
        if st.button("Submit suggestion") and suggestion.strip():
            data["suggestions"].append({"id":"SUG-"+uuid4().hex[:8],"user":user,"text":suggestion.strip(),"status":"Suggestion","time":now()});save_extra(extra);st.rerun()
        for x in data["suggestions"]: st.write(f"**{x['user']}**: {x['text']} ({x['status']})")
    with tabs[5]:
        version=data.get("published_version")
        st.subheader("Leadership View")
        if version:
            st.success(f"Published baseline version {version['version']} | Published by {version['published_by']}")
            st.dataframe(pd.DataFrame(version["items"]),hide_index=True,use_container_width=True)
        else: st.info("No official baseline has been published yet.")
'''
    s=s[:start]+new+s[end:]
for token in [imp.strip(),"render_growth_strategy_30(data, extra, save_extra, user"]:
    if token not in s:raise SystemExit("Validation failed: "+token)
p.write_text(s);print("Growth Strategy 30 installed")
