from pathlib import Path

# Personal scenario live summary.
p = Path("personal_scenarios.py")
s = p.read_text()
imp = "from scenario_capacity_32_1 import render_capacity_summary\n"
if imp not in s:
    marker = "import streamlit as st\n"
    if marker not in s:
        raise SystemExit("personal_scenarios.py Streamlit import not found. No changes made.")
    s = s.replace(marker, marker + imp, 1)

needle = '            result = scenario_preview(planning, item, edited, scenario_result)\n'
insert = '''            live_allocation = {
                row["Site"]: float(row.get("Days/Week") or 0)
                for row in edited.to_dict("records")
            }
            render_capacity_summary(
                extra,
                live_allocation,
                user,
                "personal",
                item["id"],
                key_suffix=item["id"],
            )
            result = scenario_preview(planning, item, edited, scenario_result)
'''
if needle in s:
    s = s.replace(needle, insert, 1)
elif "render_capacity_summary(" not in s:
    raise SystemExit("Personal scenario preview location not found. No changes made.")
p.write_text(s)

# Shared scenario live summary. Insert next to the shared scenario allocation editor.
p = Path("strategic_planning.py")
s = p.read_text()
if imp not in s:
    marker = "import streamlit as st\n"
    if marker not in s:
        raise SystemExit("strategic_planning.py Streamlit import not found. No changes made.")
    s = s.replace(marker, marker + imp, 1)

# The current shared scenario renderer calculates result from scenario_result.
# Add a summary immediately before that calculation using the edited allocation table.
candidates = [
    "result = scenario_result(p, scenario_name)",
    "result = scenario_result(planning, scenario_name)",
    "result = scenario_result(p, selected_scenario)",
    "result = scenario_result(planning, selected_scenario)",
]
patched = False
for candidate in candidates:
    if candidate in s:
        scenario_var = "scenario_name" if "scenario_name" in candidate else "selected_scenario"
        planning_var = "p" if "scenario_result(p," in candidate else "planning"
        block = f'''shared_live_allocation = {planning_var}.get("scenarios", {{}}).get({scenario_var}, {{}})
        render_capacity_summary(
            extra,
            shared_live_allocation,
            (current_user or {{}}).get("name", "Jeffrey Sacks") if current_user else "Jeffrey Sacks",
            "shared",
            {scenario_var},
            key_suffix=str({scenario_var}),
        )
        {candidate}'''
        s = s.replace(candidate, block, 1)
        patched = True
        break

# If an edited DataFrame is available, prefer it so totals update live while building.
if "shared_live_allocation" in s:
    s = s.replace(
        'shared_live_allocation = planning.get("scenarios", {}).get(scenario_name, {})',
        'shared_live_allocation = {row["Site"]: float(row.get("Days/Week") or 0) for row in edited.to_dict("records")} if "edited" in locals() else planning.get("scenarios", {}).get(scenario_name, {})'
    )
    s = s.replace(
        'shared_live_allocation = p.get("scenarios", {}).get(scenario_name, {})',
        'shared_live_allocation = {row["Site"]: float(row.get("Days/Week") or 0) for row in edited.to_dict("records")} if "edited" in locals() else p.get("scenarios", {}).get(scenario_name, {})'
    )

if not patched and "render_capacity_summary(" not in s:
    raise SystemExit("Shared scenario result calculation not found. No changes made.")
p.write_text(s)
print("Strategic Planning 32.1 live scenario capacity installed.")
