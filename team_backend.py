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
            data = deepcopy(seed or {})
            data.setdefault("initiatives", [])
            data.setdefault("decisions", [])
            data.setdefault("roadmap", [])
            data.setdefault("growth", [])
            data.setdefault("clinical_intelligence", {"items": []})
            data.setdefault("rvu_metrics", {})
            self.save(data)
            return data
        body = self.service.files().get_media(fileId=self.file_id).execute()
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return json.loads(body)

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
            for field, value in changes.items():
                previous = item.get(field)
                if previous != value:
                    history.append({"timestamp_utc": datetime.now(timezone.utc).isoformat(), "actor_name": actor["name"], "actor_email": actor["email"], "field": field, "old_value": previous, "new_value": value})
                    item[field] = value
            if item.get("status") == "Complete" or int(item.get("progress", 0) or 0) == 100:
                item.update(status="Complete", progress=100, archived=True)
            if item.get("status") == "Cancelled":
                item["archived"] = True
            item["team_updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            self.save(data)
            return True
        return False

    def add_comment(self, initiative_id, comment, actor):
        data = self.load()
        for item in data.get("initiatives", []):
            if str(item.get("id")) == str(initiative_id):
                item.setdefault("comments", []).append({"timestamp_utc": datetime.now(timezone.utc).isoformat(), "author_name": actor["name"], "author_email": actor["email"], "comment": comment.strip()})
                item["team_updated_at_utc"] = datetime.now(timezone.utc).isoformat()
                self.save(data)
                return True
        return False
