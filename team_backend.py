import io
import json
from datetime import datetime, timezone

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


class TeamStore:
    def __init__(self, service_account_info, folder_id, file_name):
        creds = Credentials.from_service_account_info(
            dict(service_account_info),
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
        self.folder_id = str(folder_id)
        self.file_name = str(file_name)
        self.file_id = self._find_file()
        if not self.file_id:
            raise RuntimeError(f"{self.file_name} was not found in the configured Google Drive folder.")

    def _find_file(self):
        safe_name = self.file_name.replace("'", "\\'")
        query = (
            f"name = '{safe_name}' and "
            f"'{self.folder_id}' in parents and trashed = false"
        )
        files = self.service.files().list(
            q=query,
            fields="files(id,name)",
            pageSize=10,
        ).execute().get("files", [])
        return files[0]["id"] if files else None

    def load(self):
        body = self.service.files().get_media(fileId=self.file_id).execute()
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return json.loads(body)

    def save(self, data):
        data["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        media = MediaIoBaseUpload(
            io.BytesIO(payload),
            mimetype="application/json",
            resumable=False,
        )
        self.service.files().update(
            fileId=self.file_id,
            media_body=media,
        ).execute()

    @staticmethod
    def initiatives(data):
        if isinstance(data.get("initiatives"), list):
            return data["initiatives"]
        command_center = data.setdefault("command_center", {})
        return command_center.setdefault("initiatives", [])

    @staticmethod
    def extras(data):
        return data.setdefault("command_center", {})

    def update_initiative(self, initiative_id, changes, actor):
        data = self.load()
        for item in self.initiatives(data):
            if str(item.get("id")) != str(initiative_id):
                continue
            history = item.setdefault("history", [])
            now = datetime.now(timezone.utc).isoformat()
            for field, value in changes.items():
                previous = item.get(field)
                if previous != value:
                    history.append(
                        {
                            "timestamp_utc": now,
                            "actor_name": actor["name"],
                            "actor_email": actor["email"],
                            "field": field,
                            "old_value": previous,
                            "new_value": value,
                        }
                    )
                    item[field] = value
            if item.get("status") == "Complete" or int(item.get("progress", 0) or 0) == 100:
                item.update(status="Complete", progress=100, archived=True)
            elif item.get("status") == "Cancelled":
                item["archived"] = True
            item["team_updated_at_utc"] = now
            item["last_update"] = now[:10]
            self.save(data)
            return True
        return False

    def add_comment(self, initiative_id, comment, actor):
        data = self.load()
        for item in self.initiatives(data):
            if str(item.get("id")) != str(initiative_id):
                continue
            now = datetime.now(timezone.utc).isoformat()
            item.setdefault("comments", []).append(
                {
                    "timestamp_utc": now,
                    "author_name": actor["name"],
                    "author_email": actor["email"],
                    "comment": comment.strip(),
                }
            )
            item["team_updated_at_utc"] = now
            self.save(data)
            return True
        return False
