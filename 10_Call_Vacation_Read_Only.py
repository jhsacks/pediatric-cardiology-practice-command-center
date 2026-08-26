import json

import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from call_schedule import ensure_store, render_readonly

service_account = dict(st.secrets["google_service_account"])
drive = st.secrets["google_drive"]
creds = Credentials.from_service_account_info(
    service_account,
    scopes=["https://www.googleapis.com/auth/drive"],
)
service = build("drive", "v3", credentials=creds, cache_discovery=False)
folder_id = str(drive["folder_id"])
file_name = str(drive["file_name"])
query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
files = service.files().list(
    q=query,
    fields="files(id,name)",
    pageSize=10,
).execute().get("files", [])
if not files:
    st.error("Practice data file was not found.")
    st.stop()
body = service.files().get_media(fileId=files[0]["id"]).execute()
if isinstance(body, bytes):
    body = body.decode("utf-8")
raw = json.loads(body)
extra = raw.setdefault("command_center", {})
st.header("Call & Vacation Schedule")
st.caption("Read-only practice view")
render_readonly(ensure_store(extra))
