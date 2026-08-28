from pathlib import Path
p=Path('collaboration_governance.py')
s=p.read_text()
old='sharing=st.selectbox("Share with",SHARING,index=SHARING.index(x.get("sharing","Everyone")),key=x["id"]+"s")'
new='sharing_value=x.get("sharing","Everyone")\n    if sharing_value not in SHARING: sharing_value="Everyone"\n    sharing=st.selectbox("Share with",SHARING,index=SHARING.index(sharing_value),key=x["id"]+"s")'
s=s.replace(old,new)
old2='status=st.selectbox("Status",["Active","Completed","Archived"],index=["Active","Completed","Archived"].index(x.get("status","Active")))'
new2='status_options=["Active","Completed","Archived"]\n    status_value=x.get("status","Active")\n    if status_value not in status_options: status_value="Active"\n    status=st.selectbox("Status",status_options,index=status_options.index(status_value))'
s=s.replace(old2,new2)
p.write_text(s)
print('fixed')
