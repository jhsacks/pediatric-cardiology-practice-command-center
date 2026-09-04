from pathlib import Path

IMPORT = "from scenario_capacity_32_2 import render_live_capacity\n"

# Patch the exact Shared Scenarios structure supplied by the user.
path = Path("strategic_planning.py")
text = path.read_text()
if IMPORT not in text:
    marker = "import streamlit as st\n"
    if marker not in text:
        raise SystemExit("Streamlit import not found in strategic_planning.py. No changes made.")
    text = text.replace(marker, marker + IMPORT, 1)

needle = '''        preview_result = scenario_result(data, scenario, edited_allocation)
        scenario_metrics(preview_result)
'''
replacement = '''        preview_result = scenario_result(data, scenario, edited_allocation)
        live_allocation = {
            row["Site"]: number(row.get("Days/Week"))
            for row in edited_allocation.to_dict("records")
        }
        render_live_capacity(
            extra,
            live_allocation,
            (current_user or {}).get("name", "Jeffrey Sacks") if current_user else "Jeffrey Sacks",
            "shared",
            scenario,
        )
        scenario_metrics(preview_result)
'''
if needle in text:
    text = text.replace(needle, replacement, 1)
elif 'render_live_capacity(\n            extra,\n            live_allocation' not in text:
    raise SystemExit("Exact Shared Scenario preview block not found. No changes made.")
path.write_text(text)

# Patch My Scenarios against the currently installed personal scenario module.
path = Path("personal_scenarios.py")
text = path.read_text()
if IMPORT not in text:
    marker = "import streamlit as st\n"
    if marker not in text:
        raise SystemExit("Streamlit import not found in personal_scenarios.py. No changes made.")
    text = text.replace(marker, marker + IMPORT, 1)

candidates = [
    '            result = scenario_preview(planning, item, edited, scenario_result)\n',
    '            result=scenario_preview(planning,item,edited,scenario_result)\n',
]
inserted = False
for needle in candidates:
    if needle in text:
        replacement = '''            personal_live_allocation = {
                row["Site"]: float(row.get("Days/Week") or 0)
                for row in edited.to_dict("records")
            }
            render_live_capacity(
                extra,
                personal_live_allocation,
                user,
                "personal",
                item["id"],
            )
''' + needle
        text = text.replace(needle, replacement, 1)
        inserted = True
        break
if not inserted and 'personal_live_allocation' not in text:
    raise SystemExit("Personal Scenario preview block not found. No changes made.")
path.write_text(text)

print("Strategic Planning 32.2 live scenario capacity installed.")
