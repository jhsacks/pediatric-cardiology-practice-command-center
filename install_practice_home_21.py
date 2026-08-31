from pathlib import Path
import re

path = Path("app.py")
text = path.read_text()

import_line = "from practice_home_dashboard import render_practice_home\n"
if import_line not in text:
    marker = "import streamlit as st\n"
    if marker not in text:
        raise SystemExit("Streamlit import not found. No change made.")
    text = text.replace(marker, marker + import_line, 1)

# Replace exactly the legacy Home route and everything up to Physician RVUs.
pattern = r'(?ms)^if page == "Home":.*?(?=^elif page == "Physician RVUs":)'
replacement = '''target_page = st.session_state.pop("practice_home_target_page", None)
if target_page:
    page = target_page

if page == "Home":
    render_practice_home(extra, user)

'''
updated, count = re.subn(pattern, replacement, text, count=1)
if count != 1:
    raise SystemExit("Legacy Practice Home block not found exactly once. No change made.")

required = [
    import_line.strip(),
    'render_practice_home(extra, user)',
    'practice_home_target_page',
    'elif page == "Physician RVUs":',
]
missing = [token for token in required if token not in updated]
if missing:
    raise SystemExit("Practice Home validation failed: " + " | ".join(missing))

path.write_text(updated)
print("Practice Home 21 installed.")
