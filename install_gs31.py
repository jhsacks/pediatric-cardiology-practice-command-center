from pathlib import Path
import re
MODE='practice'
# Patch Growth Strategy 30.
exec(compile(Path('patch_growth31.py').read_text(),'patch_growth31.py','exec'))
# Executive home widget.
app=Path('app.py');s=app.read_text();imp='from growth_governance_31 import render_governance_home\n'
if MODE=='executive':
    if imp not in s:s=s.replace('import streamlit as st\n','import streamlit as st\n'+imp,1)
    if 'render_governance_home(extra)' not in s:
        s=s.replace('    render_executive_home(extra)','    render_executive_home(extra)\n    render_governance_home(extra)',1)
app.write_text(s)
# Migrate roadmap editor choices.
r=Path('roadmap_editor.py')
if r.exists():
    t=r.read_text();t=re.sub(r'STATUSES = \[[^\n]+\]','STATUSES = ["Executive Brainstorming", "Suggestion", "Idea", "Planning", "Approved", "In Progress", "Archived"]',t,count=1);t=t.replace('item.setdefault("status", "Draft")','item.setdefault("status", "Idea")');r.write_text(t)
print('Growth Strategy 31 installed for '+MODE)
