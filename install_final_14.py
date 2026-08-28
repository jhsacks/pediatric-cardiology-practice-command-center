from pathlib import Path
p=Path('app.py'); s=p.read_text()
s=s.replace('from strategic_roadmap import render_roadmap\n','from strategic_planning import render_strategic_planning_center\nfrom shared_identity import active_directory, verify_pin\n')
# Initialize shared store before sign-in.
old='user = sign_in()\nroster = users()\nservice_account = dict(st.secrets["google_service_account"])\ndrive_settings = st.secrets["google_drive"]\nstore = TeamStore(\n    service_account,\n    str(drive_settings["folder_id"]),\n    str(drive_settings["file_name"]),\n)\nraw_data = store.load()\n'
new='service_account = dict(st.secrets["google_service_account"])\ndrive_settings = st.secrets["google_drive"]\nstore = TeamStore(service_account, str(drive_settings["folder_id"]), str(drive_settings["file_name"]))\nraw_data = store.load()\nextra = TeamStore.extras(raw_data)\n\ndef shared_users():\n    directory = active_directory(extra)\n    return directory if any(row.get("pin_hash") for row in directory) else users()\n\ndef shared_sign_in():\n    if st.session_state.get("practice_user"):\n        return st.session_state.practice_user\n    roster = shared_users()\n    st.title("Practice Command Center Sign In")\n    name = st.selectbox("Team member", [person["name"] for person in roster])\n    pin = st.text_input("PIN number (1-100)", type="password")\n    if st.button("Sign in", type="primary"):\n        match = next(person for person in roster if person["name"] == name)\n        valid = verify_pin(name, pin, match.get("pin_hash")) if match.get("pin_hash") else pin.strip() == str(match.get("pin", ""))\n        if valid:\n            st.session_state.practice_user = {key: match.get(key) for key in ["name", "email", "admin"]}\n            st.rerun()\n        st.error("The selected user and PIN did not match.")\n    st.stop()\n\nuser = shared_sign_in()\nroster = shared_users()\n'
if old not in s: raise SystemExit('Practice initialization block not found')
s=s.replace(old,new,1)
# Avoid duplicate extra assignment later.
s=s.replace('extra = TeamStore.extras(raw_data)\nwith st.sidebar:', 'with st.sidebar:',1)
# Clean navigation and headings.
s=s.replace('"Home", "Initiatives", "Decisions", "Roadmap",\n            "Clinical Intelligence", "Practice Growth", "Physician RVUs",','"Home", "Clinical Intelligence", "Physician RVUs",')
s=s.replace('"🗺️ Strategic Roadmap",','"📊 Strategic Planning",')
s=s.replace('st.title("Pediatric Cardiology Practice Command Center")\nst.caption(\n    "Initiatives are collaborative. RVUs, growth, decisions, roadmap, "\n    "and intelligence are view-only."\n)\n','')
# Remove legacy route blocks between Initiatives and Physician RVUs.
start=s.find('elif page == "Initiatives":')
end=s.find('elif page == "Physician RVUs":')
if start!=-1 and end!=-1: s=s[:start]+s[end:]
# Replace final strategic route.
s=s.replace('elif page == "🗺️ Strategic Roadmap":\n    render_roadmap(extra, lambda updated: store.save(raw_data), editable=True)','elif page == "📊 Strategic Planning":\n    render_strategic_planning_center(extra, lambda updated: store.save(raw_data))')
p.write_text(s)
