import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def authenticate_gdrive():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    "credentials.json not found. Download from Google Cloud Console "
                    "and place it in the project root directory."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def find_or_create_folder(service, folder_name, parent_folder_id=None):
    query = (
        f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get("files", [])
    if items:
        return items[0]["id"]
    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_folder_id:
        folder_metadata["parents"] = [parent_folder_id]
    folder = service.files().create(body=folder_metadata, fields="id").execute()
    return folder.get("id")


def upload_file_to_gdrive(service, file_path, folder_id):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    filename = os.path.basename(file_path)
    media = MediaFileUpload(file_path, resumable=True)
    file_metadata = {"name": filename, "parents": [folder_id]}
    file = service.files().create(
        body=file_metadata, media_body=media, fields="id, name"
    ).execute()
    return file.get("id")


def list_files_in_folder(service, folder_id, extension_filter=None):
    query = f"'{folder_id}' in parents and trashed=false"
    if extension_filter:
        query += f" and name contains '{extension_filter}'"
    results = service.files().list(
        q=query,
        fields="files(id, name, createdTime, size)",
        orderBy="createdTime desc",
    ).execute()
    return results.get("files", [])


def download_file_from_gdrive(service, file_id, destination_path):
    request = service.files().get_media(fileId=file_id)
    os.makedirs(os.path.dirname(destination_path) or ".", exist_ok=True)
    with open(destination_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return destination_path


def get_latest_zip_from_gdrive():
    service = authenticate_gdrive()
    folder_id = find_or_create_folder(service, "scraped_files")
    files = list_files_in_folder(service, folder_id, extension_filter=".zip")
    if not files:
        return None, None
    latest = files[0]
    dest_path = os.path.join("downloads", latest["name"])
    os.makedirs("downloads", exist_ok=True)
    download_file_from_gdrive(service, latest["id"], dest_path)
    return dest_path, latest["name"]
