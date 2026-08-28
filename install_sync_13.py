from pathlib import Path
import re

MODE = "practice"
p = Path("app.py")
s = p.read_text()

# Remove repeated top-level branding calls except in the Home branch.
lines = s.splitlines()
out = []
current_branch = None
for line in lines:
    stripped = line.strip()
    if stripped.startswith(('if page == ', 'elif page == ')):
        current_branch = stripped
    repeated_brand = ('AI Command Center' in line and ('st.title(' in line or 'st.header(' in line or 'st.markdown(' in line))
    if repeated_brand and current_branch and 'Home' not in current_branch:
        continue
    out.append(line)
s = "\n".join(out) + "\n"

# Hide legacy navigation labels while retaining their data and functions.
legacy_labels = [
    '"Initiatives",', '"Decisions",', '"Roadmap",',
    '"🗺️ Strategic Roadmap",', '"Strategic Roadmap",',
]
for label in legacy_labels:
    s = s.replace(label, "")

# Ensure shared Collaboration module import.
collab_import = "from collaboration_governance import render_collaboration_center\n"
if collab_import not in s:
    s = s.replace("import streamlit as st\n", "import streamlit as st\n" + collab_import, 1)

# Ensure shared Strategic Planning module import.
planning_import = "from strategic_planning import render_strategic_planning_center\n"
if planning_import not in s:
    s = s.replace("import streamlit as st\n", "import streamlit as st\n" + planning_import, 1)

# Add unique menu items if absent.
for label in ["🤝 Collaboration", "📊 Strategic Planning"]:
    if label not in s:
        for token in ['"📅 Call & Vacation",', '"Physician RVUs",', '"📊 Physician RVUs",']:
            if token in s:
                s = s.replace(token, token + f'\n            "{label}",', 1)
                break

# Add routes if absent. Existing shared save callbacks are used per app.
if 'elif page == "🤝 Collaboration":' not in s:
    callback = "save_extra" if MODE == "executive" else "lambda updated: store.save(raw_data)"
    admin = "True" if MODE == "executive" else "False"
    user_arg = "" if MODE == "executive" else ", current_user=user"
    block = f'elif page == "🤝 Collaboration":\n    render_collaboration_center(extra, {callback}{user_arg}, admin_mode={admin})\n'
    marker = 'elif page == "⚙️ Settings":'
    s = s.replace(marker, block + marker, 1) if marker in s else s + "\n" + block

if 'elif page == "📊 Strategic Planning":' not in s:
    callback = "save_extra" if MODE == "executive" else "lambda updated: store.save(raw_data)"
    block = f'elif page == "📊 Strategic Planning":\n    render_strategic_planning_center(extra, {callback})\n'
    marker = 'elif page == "⚙️ Settings":'
    s = s.replace(marker, block + marker, 1) if marker in s else s + "\n" + block

p.write_text(s)
print(f"Applied synchronized navigation and cleanup for {MODE}.")
