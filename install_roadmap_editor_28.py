from pathlib import Path

path = Path("growth_strategy.py")
text = path.read_text()

import_line = "from roadmap_editor import render_roadmap_editor\n"
if import_line not in text:
    marker = "import streamlit as st\n"
    if marker not in text:
        raise SystemExit("Growth Strategy Streamlit import not found. No changes made.")
    text = text.replace(marker, marker + import_line, 1)

old = "    with tabs[8]: roadmap_tab(data,extra,save_extra,user)"
new = "    with tabs[8]: render_roadmap_editor(data, extra, save_extra, user, executive=executive)"
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("Growth Strategy Roadmap tab call not found. No changes made.")

for token in [import_line.strip(), "render_roadmap_editor(data, extra, save_extra, user, executive=executive)"]:
    if token not in text:
        raise SystemExit("Roadmap Editor validation failed: " + token)

path.write_text(text)
print("Roadmap Editor 28 installed.")
