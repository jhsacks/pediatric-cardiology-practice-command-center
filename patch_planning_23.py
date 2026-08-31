from pathlib import Path
p=Path("strategic_planning.py"); s=p.read_text()
imp="from personal_scenarios import render_personal_scenarios\n"
if imp not in s:s=s.replace("import streamlit as st\n","import streamlit as st\n"+imp,1)
old='def render_strategic_planning_center(extra, save_extra):'; new='def render_strategic_planning_center(extra, save_extra, current_user=None):'
if old in s:s=s.replace(old,new,1)
elif new not in s:raise SystemExit("Strategic Planning renderer signature not found")
oldtabs='st.tabs(["Portfolio", "Scenarios", "Assumptions & Demand", "Roadmap", "Risks", "Notes"])'; newtabs='st.tabs(["Portfolio", "Shared Scenarios", "My Scenarios", "Assumptions & Demand", "Roadmap", "Risks", "Notes"])'
if oldtabs in s:
 s=s.replace(oldtabs,newtabs,1)
 # shift existing tab indices from highest to lowest
 for oldi,newi in [(5,6),(4,5),(3,4),(2,3)]:s=s.replace(f"with tabs[{oldi}]:",f"with tabs[{newi}]:")
 marker='    with tabs[3]:\n'
 personal='    with tabs[2]:\n        render_personal_scenarios(extra, save_extra, current_user, scenario_result)\n\n'
 if marker not in s:raise SystemExit("Assumptions tab marker not found")
 s=s.replace(marker,personal+marker,1)
elif newtabs not in s:raise SystemExit("Strategic Planning tabs not found")
p.write_text(s); print("Personal scenarios installed")
