from pathlib import Path
import re
MODE="practice"
p=Path("app.py");s=p.read_text();imp="from growth_strategy import render_growth_strategy\n"
if imp not in s:s=s.replace("import streamlit as st\n","import streamlit as st\n"+imp,1)
label='"🧭 Growth Strategy",'
if label not in s:
 anchor='"📊 Strategic Planning",'
 if anchor not in s:raise SystemExit("Strategic Planning menu anchor not found")
 s=s.replace(anchor,label+'\n            '+anchor,1)
pattern=r'(?ms)^elif page == "🧭 Growth Strategy":.*?(?=^elif page == |\Z)';callback="save_extra" if MODE=="executive" else "lambda updated: store.save(raw_data)";user="None" if MODE=="executive" else "user";executive="True" if MODE=="executive" else "False";route=f'elif page == "🧭 Growth Strategy":\n    render_growth_strategy(extra, {callback}, current_user={user}, executive={executive})\n'
if re.search(pattern,s):s=re.sub(pattern,route,s,count=1)
else:
 anchor='elif page == "📊 Strategic Planning":'
 if anchor not in s:raise SystemExit("Strategic Planning route anchor not found")
 s=s.replace(anchor,route+anchor,1)
for token in [imp.strip(),label,'render_growth_strategy(extra,']:
 if token not in s:raise SystemExit("Validation failed: "+token)
p.write_text(s);print(f"Growth Strategy 26 installed for {MODE}")
