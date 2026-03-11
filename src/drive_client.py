import os
import io
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError


class GoogleDriveClient:
    SCOPES = [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/youtube.upload"
    ]

    def __init__(self, token_file="token.json", client_secret_file="client_secret.json"):
        self.token_file = token_file
        self.client_secret_file = client_secret_file
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Get credentials and build Drive service."""
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

        self.service = build("drive", "v3", credentials=creds)

    def list_video_files(self, folder_id: str):
        """
        Return list of video files in the given folder, sorted by created time ascending.
        Only considers common video MIME types.
        """
        video_mime_types = [
            "video/mp4", "video/x-msvideo", "video/quicktime",
            "video/x-matroska", "video/webm", "video/ogg"
        ]
        mime_query = " or ".join([f"mimeType='{mime}'" for mime in video_mime_types])

        query = f"'{folder_id}' in parents and ({mime_query}) and trashed=false"
        try:
            results = self.service.files().list(
                q=query,
                pageSize=50,
                fields="files(id, name, createdTime)",
                orderBy="createdTime"
            ).execute()
            return results.get("files", [])
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def download_file(self, file_id: str, destination: str):
        """Download a file from Drive to local destination."""
        try:
            request = self.service.files().get_media(fileId=file_id)
            with io.FileIO(destination, "wb") as file:
                downloader = MediaIoBaseDownload(file, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    print(f"Download {int(status.progress() * 100)}%.")
        except HttpError as error:
            print(f"Download error: {error}")
            raise

    def move_file(self, file_id: str, target_folder_id: str):
        """Move a file from its current parent to a new folder."""
        try:
            # Get current parents
            file = self.service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents", []))
            # Move to new folder
            self.service.files().update(
                fileId=file_id,
                addParents=target_folder_id,
                removeParents=previous_parents,
                fields="id, parents"
            ).execute()
            print(f"File {file_id} moved to folder {target_folder_id}.")
        except HttpError as error:
            print(f"Move error: {error}")
            raise
