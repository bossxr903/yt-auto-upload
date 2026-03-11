import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class YouTubeClient:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(self, token_file="token.json", client_secret_file="client_secret.json"):
        # Reuse the same token file as Drive (scopes must include youtube.upload)
        self.token_file = token_file
        self.client_secret_file = client_secret_file
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Get credentials and build YouTube service."""
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        self.service = build("youtube", "v3", credentials=creds)

    def upload_video(self, video_path: str, title: str, description: str,
                     tags: str, privacy_status: str = "private",
                     publish_at: str = None) -> str:
        """
        Upload video to YouTube.
        If publish_at is provided (ISO 8601), video will be scheduled.
        Returns the YouTube video ID.
        """
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            }
        }

        if publish_at:
            body["status"]["publishAt"] = publish_at

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

        try:
            request = self.service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%.")
            print(f"Video uploaded successfully. Video ID: {response['id']}")
            return response["id"]
        except HttpError as error:
            print(f"YouTube upload error: {error}")
            raise
