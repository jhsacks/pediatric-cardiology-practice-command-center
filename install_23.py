from pathlib import Path
import re

path = Path("app.py")
text = path.read_text()

import_line = (
    "from collaborative_work import "
    "render_initiatives as render_work_initiatives, "
    "render_decisions as render_work_decisions, "
    "render_growth as render_work_growth, "
    "render_user_admin\n"
)
if import_line not in text:
    marker = "import streamlit as st\n"
    if marker not in text:
        raise SystemExit("Streamlit import not found. No changes made.")
    text = text.replace(marker, marker + import_line, 1)

routes = {
    "🚀 Initiatives": (
        "render_work_initiatives(extra, lambda updated: store.save(raw_data), "
        "current_user=user, allow_view_as=False)"
    ),
    "⚖️ Decisions": (
        "render_work_decisions(extra, lambda updated: store.save(raw_data), "
        "current_user=user, allow_view_as=False)"
    ),
    "🌱 Practice Growth": (
        "render_work_growth(extra, lambda updated: store.save(raw_data), "
        "current_user=user, allow_view_as=False)"
    ),
    "📊 Strategic Planning": (
        "render_strategic_planning_center(extra, "
        "lambda updated: store.save(raw_data), current_user=user)"
    ),
}

for label, call in routes.items():
    pattern = rf'(?ms)^elif page == "{re.escape(label)}":.*?(?=^elif page == |\Z)'
    replacement = f'elif page == "{label}":\n    {call}\n'
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"Route not found: {label}. No changes made.")

required = [
    import_line.strip(),
    "current_user=user, allow_view_as=False",
    "render_strategic_planning_center(extra, lambda updated: store.save(raw_data), current_user=user)",
]
missing = [token for token in required if token not in text]
if missing:
    raise SystemExit("Practice installer validation failed: " + " | ".join(missing))

if "allow_view_as=True" in text:
    raise SystemExit("Practice still contains an enabled View As route. No changes made.")

path.write_text(text)
print("Identity and Permissions 23 installed for Practice.")
