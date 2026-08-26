import io
import json
from copy import deepcopy
from datetime import datetime, timezone

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


class TeamStore:
    def __init__(self, service_account_json, folder_id, file_name="practice_team_data.json"):
        info = json.loads(service_account_json) if isinstance(service_account_json, str) else service_account_json
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/drive"])
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
        self.folder_id = folder_id
        self.file_name = file_name
        self.file_id = self._find_file()

    def _find_file(self):
        safe = self.file_name.replace("'", "\\'")
        query = f"name = '{safe}' and '{self.folder_id}' in parents and trashed = false"
        files = self.service.files().list(q=query, fields="files(id,name)", pageSize=10).execute().get("files", [])
        return files[0]["id"] if files else None

    def load(self, seed=None):
        if not self.file_id:
            initial = deepcopy(seed or {})
            initial.setdefault("initiatives", [])
            initial.setdefault("decisions", [])
            initial.setdefault("roadmap", [])
            initial.setdefault("growth", [])
            initial.setdefault("clinical_intelligence", {"items": []})
            initial.setdefault("rvu_metrics", {})
            initial["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            self.save(initial)
            return initial
        content = self.service.files().get_media(fileId=self.file_id).execute()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        return json.loads(content)

    def save(self, data):
        data["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(data, indent=2, ensure_ascii=False, default=str).encode("utf-8")
        media = MediaIoBaseUpload(io.BytesIO(payload), mimetype="application/json", resumable=False)
        if self.file_id:
            self.service.files().update(fileId=self.file_id, media_body=media).execute()
        else:
            metadata = {"name": self.file_name, "parents": [self.folder_id], "mimeType": "application/json"}
            created = self.service.files().create(body=metadata, media_body=media, fields="id").execute()
            self.file_id = created["id"]

    def update_initiative(self, initiative_id, changes, actor):
        data = self.load()
        for item in data.get("initiatives", []):
            if str(item.get("id")) != str(initiative_id):
                continue
            history = item.setdefault("history", [])
            for field, new_value in changes.items():
                old_value = item.get(field)
                if old_value != new_value:
                    history.append({
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "actor_name": actor.get("name", ""),
                        "actor_email": actor.get("email", ""),
                        "field": field,
                        "old_value": old_value,
                        "new_value": new_value,
                    })
                    item[field] = new_value
            if item.get("status") == "Complete":
                item["progress"] = 100
                item["archived"] = True
            if int(item.get("progress", 0) or 0) == 100:
                item["status"] = "Complete"
                item["archived"] = True
            if item.get("status") == "Cancelled":
                item["archived"] = True
            item["last_update"] = datetime.now(timezone.utc).date().isoformat()
            self.save(data)
            return True
        return False

    def add_comment(self, initiative_id, comment, actor):
        data = self.load()
        for item in data.get("initiatives", []):
            if str(item.get("id")) == str(initiative_id):
                item.setdefault("comments", []).append({
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "author_name": actor.get("name", ""),
                    "author_email": actor.get("email", ""),
                    "comment": comment.strip(),
                })
                self.save(data)
                return True
        return False
