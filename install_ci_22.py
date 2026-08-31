from pathlib import Path
import re

MODE = "executive"
path = Path("app.py")
text = path.read_text()

import_line = "from personal_clinical_intelligence import render_personal_clinical_intelligence\n"
if import_line not in text:
    marker = "import streamlit as st\n"
    if marker not in text:
        raise SystemExit("Streamlit import not found. No changes made.")
    text = text.replace(marker, marker + import_line, 1)

labels = ["📚 Clinical Intelligence", "Clinical Intelligence"]
route_found = False
for label in labels:
    pattern = rf'(?ms)^(elif|if) page == "{re.escape(label)}":.*?(?=^(?:elif|if) page == |\Z)'
    match = re.search(pattern, text)
    if not match:
        continue
    prefix = match.group(1)
    callback = "save_extra" if MODE == "executive" else "lambda updated: store.save(raw_data)"
    user_arg = "" if MODE == "executive" else ", current_user=user"
    replacement = (
        f'{prefix} page == "{label}":\n'
        f'    render_personal_clinical_intelligence(extra, {callback}{user_arg})\n'
    )
    text = text[:match.start()] + replacement + text[match.end():]
    route_found = True
    break

if not route_found:
    raise SystemExit("Clinical Intelligence route not found. No changes made.")

required = [
    import_line.strip(),
    "render_personal_clinical_intelligence(extra,",
]
missing = [token for token in required if token not in text]
if missing:
    raise SystemExit("Clinical Intelligence validation failed: " + " | ".join(missing))

path.write_text(text)
print(f"Clinical Intelligence 22 installed for {MODE}.")
