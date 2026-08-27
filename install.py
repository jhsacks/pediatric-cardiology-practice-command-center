from pathlib import Path
p=Path('app.py'); s=p.read_text(); imp='from strategic_roadmap import render_roadmap\n'
if imp not in s:s=s.replace('import streamlit as st\n','import streamlit as st\n'+imp,1)
label='🗺️ Strategic Roadmap'
if label not in s:
    for token in ['"🤝 Collaboration",','"📅 Call & Vacation",']:
        if token in s:s=s.replace(token,token+'\n            "'+label+'",',1);break
route=f'elif page == "{label}":'
if route not in s:s+='\n'+route+'\n    render_roadmap(extra, lambda updated: store.save(raw_data), editable=True)\n'
p.write_text(s)
