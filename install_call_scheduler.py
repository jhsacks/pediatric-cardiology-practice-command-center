from pathlib import Path
import os

mode = os.environ.get("CALL_SCHEDULER_MODE", "practice").strip().lower()
path = Path("app.py")
text = path.read_text()

import_line = "from call_schedule import ensure_store, render_editor, render_readonly\n"
if import_line not in text:
    anchor = "import streamlit as st\n"
    if anchor not in text:
        raise SystemExit("Could not find Streamlit import in app.py")
    text = text.replace(anchor, anchor + import_line, 1)

label = "📅 Call & Vacation"
if label not in text:
    # Insert into the first sidebar/navigation list containing Physician RVUs.
    candidates = [
        '"📊 Physician RVUs",',
        '"Physician RVUs",',
        '"📊 Physician RVUs"',
        '"Physician RVUs"',
    ]
    inserted = False
    for token in candidates:
        if token in text:
            replacement = token + '\n            "' + label + '",' if token.endswith(',') else token + ', "' + label + '"'
            text = text.replace(token, replacement, 1)
            inserted = True
            break
    if not inserted:
        raise SystemExit("Could not find Physician RVUs navigation item in app.py")

route = f'elif page == "{label}":'
if route not in text:
    renderer = "render_editor(extra, save_extra, log_activity)" if mode == "executive" else "render_readonly(ensure_store(extra))"
    # Add before Settings route when available, otherwise append.
    settings_markers = ['elif page == "⚙️ Settings":', 'elif page == "Settings":']
    block = f'elif page == "{label}":\n    {renderer}\n'
    placed = False
    for marker in settings_markers:
        if marker in text:
            text = text.replace(marker, block + marker, 1)
            placed = True
            break
    if not placed:
        text += "\n" + block

path.write_text(text)
print(f"Installed Call & Vacation Scheduler into {path} ({mode})")
