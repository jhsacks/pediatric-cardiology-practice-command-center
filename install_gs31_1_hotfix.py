from pathlib import Path


def replace_required(text, old, new, label):
    if old in text:
        return text.replace(old, new)
    if new in text:
        return text
    raise SystemExit(f"Could not locate {label}. No files were changed.")

# 1. Stop governance migration from forcing Idea+ items to Everyone.
gov_path = Path("growth_governance_31.py")
gov = gov_path.read_text()
gov = gov.replace(
    '            if x["status"]!="Executive Brainstorming": x["sharing"]="Everyone"; x["shared_with"]=[]\n',
    ''
)
gov = gov.replace(
    '        if x["status"]!="Executive Brainstorming": x["sharing"]="Everyone"; x["shared_with"]=[]\n',
    ''
)

# Visibility must always honor sharing, regardless of workflow status.
old_visible = '''def visible31(x,user,executive=False):
    status=migrate_status(x.get("status"))
    if status=="Suggestion": return executive and leadership_context(x,user)
    if status=="Executive Brainstorming": return x.get("sharing","Only me")=="Everyone" or x.get("owner")==user or x.get("created_by")==user or user in x.get("shared_with",[])
    return True
'''
new_visible = '''def visible31(x,user,executive=False):
    status=migrate_status(x.get("status"))
    if status=="Suggestion":
        return executive and leadership_context(x,user)
    sharing=x.get("sharing","Everyone")
    return (
        sharing=="Everyone"
        or x.get("owner")==user
        or x.get("created_by")==user
        or user in x.get("shared_with",[])
    )
'''
gov = replace_required(gov, old_visible, new_visible, "visibility policy")

# Retain sharing controls for every leadership-managed status.
old_header = '''        if status=="Executive Brainstorming":
            sharing=st.selectbox("Share with",["Only me","Selected people","Everyone"],index=["Only me","Selected people","Everyone"].index(sharing) if sharing in ["Only me","Selected people","Everyone"] else 1,key=key+"_sharing31")
            if sharing=="Selected people": shared=st.multiselect("Selected people",people(extra),default=[p for p in shared if p in people(extra)],key=key+"_people31")
        else: sharing="Everyone";shared=[];st.caption("Visible to everyone at Idea stage and later.")
'''
new_header = '''        sharing=st.selectbox("Share with",["Only me","Selected people","Everyone"],index=["Only me","Selected people","Everyone"].index(sharing) if sharing in ["Only me","Selected people","Everyone"] else 1,key=key+"_sharing31")
        if sharing=="Selected people":
            shared=st.multiselect("Selected people",people(extra),default=[p for p in shared if p in people(extra)],key=key+"_people31")
        elif sharing!="Selected people":
            shared=[]
'''
gov = replace_required(gov, old_header, new_header, "sharing controls")
gov_path.write_text(gov)

# 2. Clear every new-object widget after a successful create.
engine_path = Path("growth_strategy_30.py")
engine = engine_path.read_text()
old_save = '''def save_object(data,bucket,extra,save_extra,user,x,values,new=False):
    x.update(values); x.setdefault("id",bucket[:3].upper()+"-"+uuid4().hex[:8]); x.setdefault("created_by",user); x.setdefault("created_at",now()); x["updated_by"]=user; x["updated_at"]=now()
    if new: data[bucket].append(x)
    save_extra(extra); st.rerun()
'''
new_save = '''def save_object(data,bucket,extra,save_extra,user,x,values,new=False):
    x.update(values); x.setdefault("id",bucket[:3].upper()+"-"+uuid4().hex[:8]); x.setdefault("created_by",user); x.setdefault("created_at",now()); x["updated_by"]=user; x["updated_at"]=now()
    if new:
        data[bucket].append(x)
        prefix="new_"+bucket+"_"
        for state_key in list(st.session_state.keys()):
            if str(state_key).startswith(prefix):
                del st.session_state[state_key]
    save_extra(extra); st.rerun()
'''
engine = replace_required(engine, old_save, new_save, "new-item reset behavior")
engine_path.write_text(engine)

print("Growth Strategy 31.1 visibility and form-reset hotfix installed.")
