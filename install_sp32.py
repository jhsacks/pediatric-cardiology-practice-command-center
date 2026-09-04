from pathlib import Path
import re

# Patch strategic_planning.py by adding a final tab to the existing renderer.
p = Path("strategic_planning.py")
s = p.read_text()
imp = "from scenario_workforce_32 import render_scenario_workforce\n"
if imp not in s:
    marker = "import streamlit as st\n"
    if marker not in s:
        raise SystemExit("Strategic Planning Streamlit import not found. No changes made.")
    s = s.replace(marker, marker + imp, 1)

old_tabs = 'st.tabs(["Portfolio", "Shared Scenarios", "My Scenarios", "Assumptions & Demand", "Roadmap", "Risks", "Notes"])'
new_tabs = 'st.tabs(["Portfolio", "Shared Scenarios", "My Scenarios", "Assumptions & Demand", "Roadmap", "Risks", "Notes", "Workforce & Schedule"])'
if old_tabs in s:
    s = s.replace(old_tabs, new_tabs, 1)
elif new_tabs not in s:
    raise SystemExit("Expected Strategic Planning tab list not found. No changes made.")

call = '    with tabs[7]:\n        render_scenario_workforce(extra, save_extra, current_user=current_user)\n'
if "render_scenario_workforce(extra, save_extra" not in s:
    start = s.find("def render_strategic_planning_center(")
    if start < 0:
        raise SystemExit("Strategic Planning renderer not found. No changes made.")
    next_def = s.find("\ndef ", start + 5)
    insert_at = next_def if next_def >= 0 else len(s)
    s = s[:insert_at].rstrip() + "\n" + call + "\n" + s[insert_at:].lstrip("\n")

p.write_text(s)

# Fix Add Location Strategie typo caused by rstrip('s').
g = Path("growth_strategy_30.py")
if g.exists():
    text = g.read_text()
    old = 'with st.expander("➕ Add "+title.rstrip("s"),False):'
    new = 'with st.expander("➕ Add "+("Location Strategy" if title=="Location Strategies" else title[:-1] if title.endswith("s") else title),False):'
    if old in text:
        text = text.replace(old, new, 1)
    g.write_text(text)

print("Strategic Planning 32 installed.")
