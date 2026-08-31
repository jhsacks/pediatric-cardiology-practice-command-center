from pathlib import Path
import re
p=Path("app.py"); s=p.read_text()
imp="from collaboration_governance import render_collaboration_center, render_clinical_intelligence, render_initiatives_page, render_decisions_page, render_growth_page, render_pin_admin\n"
s=re.sub(r"from collaboration_governance import [^\n]+\n",imp,s,count=1)
if imp not in s:s=s.replace("import streamlit as st\n","import streamlit as st\n"+imp,1)
pimp="from strategic_planning import render_strategic_planning_center\n"
s=re.sub(r"from strategic_(?:roadmap|planning) import [^\n]+\n",pimp,s,count=1)
if pimp not in s:s=s.replace("import streamlit as st\n","import streamlit as st\n"+pimp,1)
for q in ['"Clinical Intelligence",','"📚 Clinical Intelligence",','"Initiatives",','"🚀 Initiatives",','"Decisions",','"⚖️ Decisions",','"Practice Growth",','"🌱 Practice Growth",','"🤝 Collaboration",','"Strategic Roadmap",','"🗺️ Strategic Roadmap",'] : s=s.replace(q,"")
anchor='"📊 Strategic Planning",'
if anchor not in s:s=s.replace('"Strategic Planning",',anchor,1)
if anchor not in s:raise SystemExit("Strategic Planning menu anchor not found")
s=s.replace(anchor,'"📚 Clinical Intelligence",\n            "🚀 Initiatives",\n            "⚖️ Decisions",\n            "🌱 Practice Growth",\n            '+anchor,1)
for label in ["🤝 Collaboration","Clinical Intelligence","📚 Clinical Intelligence","Initiatives","🚀 Initiatives","Decisions","⚖️ Decisions","Practice Growth","🌱 Practice Growth","Strategic Roadmap","🗺️ Strategic Roadmap","📊 Strategic Planning"]:
 s=re.sub(rf'(?ms)^elif page == "{re.escape(label)}":.*?(?=^elif page == |\Z)',"",s)
routes='''elif page == "📚 Clinical Intelligence":
    render_clinical_intelligence(extra, lambda updated: store.save(raw_data), current_user=user)
elif page == "🚀 Initiatives":
    render_initiatives_page(extra, lambda updated: store.save(raw_data), current_user=user)
elif page == "⚖️ Decisions":
    render_decisions_page(extra, lambda updated: store.save(raw_data), current_user=user)
elif page == "🌱 Practice Growth":
    render_growth_page(extra, lambda updated: store.save(raw_data), current_user=user)
elif page == "📊 Strategic Planning":
    render_strategic_planning_center(extra, lambda updated: store.save(raw_data))
'''
marker='elif page == "⚙️ Settings":'; s=s.replace(marker,routes+marker,1) if marker in s else s+'\n'+routes
for token in [imp.strip(),pimp.strip(),'"📚 Clinical Intelligence",','render_strategic_planning_center(extra, lambda updated: store.save(raw_data))']:
 if token not in s:raise SystemExit("Validation failed: "+token)
p.write_text(s); print("Practice Command Center 20 installed")
