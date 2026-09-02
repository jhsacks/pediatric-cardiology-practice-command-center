from pathlib import Path

path = Path("growth_strategy_30.py")
text = path.read_text()

start = text.find("def recommendation_dates(planning,settings):")
end = text.find("\ndef recruitment_tab", start)
if start < 0 or end < 0:
    raise SystemExit("recommendation_dates function not found. No changes made.")

replacement = '''def recommendation_dates(planning,settings):
    def safe_number(value, default=0.0):
        try:
            number = float(value)
            return number if number == number else default
        except (TypeError, ValueError, OverflowError):
            return default

    scenarios = planning.get("scenarios", {})
    demand_rows = planning.get("demand", [])
    assumptions = planning.get("assumptions", {})
    visits = safe_number(assumptions.get("Visits per full clinic day", 11), 11.0)
    weeks = safe_number(assumptions.get("Effective operating weeks", 45.2), 45.2)
    trigger = safe_number(settings.get("utilization_trigger_pct", 85.0), 85.0)
    output = []

    for scenario, allocation in scenarios.items():
        capacity = 0.0
        values = allocation.values() if isinstance(allocation, dict) else []
        for days in values:
            capacity += safe_number(days, 0.0) * visits * weeks

        demand = 0.0
        for row in demand_rows if isinstance(demand_rows, list) else []:
            if not isinstance(row, dict):
                continue
            override = row.get("FY27 Override")
            base = safe_number(row.get("FY26 Visits", 0), 0.0)
            growth = safe_number(row.get("Growth %", 0), 0.0)
            if override not in (None, "", "None"):
                demand += safe_number(override, base * (1 + growth / 100.0))
            else:
                demand += base * (1 + growth / 100.0)

        capacity = safe_number(capacity, 0.0)
        demand = safe_number(demand, 0.0)
        utilization = safe_number((demand / capacity * 100.0) if capacity > 0 else 999.0, 999.0)
        output.append({
            "Scenario": str(scenario),
            "Projected Demand": round(demand),
            "Capacity": round(capacity),
            "Utilization %": round(utilization, 1),
            "Recruitment Signal": "Begin planning" if utilization >= trigger else "Monitor",
        })
    return output
'''

updated = text[:start] + replacement + text[end:]
path.write_text(updated)
print("Growth Strategy 30.2 emergency hotfix installed.")
