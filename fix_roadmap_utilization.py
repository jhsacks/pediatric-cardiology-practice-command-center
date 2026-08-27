from pathlib import Path

path = Path("strategic_roadmap.py")
text = path.read_text()

old = '''    frame["Utilization %"]=(frame["Projected Demand"]/frame["Annual Capacity"].replace(0,pd.NA)*100).round(1)'''
new = '''    projected = pd.to_numeric(frame["Projected Demand"], errors="coerce").fillna(0.0).astype(float)
    capacity = pd.to_numeric(frame["Annual Capacity"], errors="coerce").fillna(0.0).astype(float)
    frame["Utilization %"] = 0.0
    positive_capacity = capacity > 0
    frame.loc[positive_capacity, "Utilization %"] = (
        projected.loc[positive_capacity]
        .div(capacity.loc[positive_capacity])
        .mul(100.0)
        .round(1)
    )
    frame.loc[(capacity == 0) & (projected > 0), "Utilization %"] = float("inf")'''

if old not in text:
    raise SystemExit("The expected utilization calculation was not found. No file was changed.")

text = text.replace(old, new, 1)

required = [
    'projected = pd.to_numeric(frame["Projected Demand"]',
    'capacity = pd.to_numeric(frame["Annual Capacity"]',
    'positive_capacity = capacity > 0',
]
missing = [token for token in required if token not in text]
if missing:
    raise SystemExit("Fix validation failed: " + ", ".join(missing))

path.write_text(text)
print("Fixed roadmap utilization calculation.")
