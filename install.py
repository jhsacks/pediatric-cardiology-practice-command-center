from pathlib import Path
p=Path('app.py'); s=p.read_text()
imp='from collaboration_governance import render_collaboration_center\n'
if imp not in s:s=s.replace('import streamlit as st\n','import streamlit as st\n'+imp,1)
label='🤝 Collaboration'
if label not in s:
    for t in ['"📅 Call & Vacation",','"Physician RVUs",']:
        if t in s:s=s.replace(t,t+'\n            "'+label+'",',1);break
route=f'elif page == "{label}":'
if route not in s:
    s+='\n'+route+'\n    render_collaboration_center(extra, lambda updated: store.save(raw_data), current_user=user, admin_mode=False)\n'
p.write_text(s)
