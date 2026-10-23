"""Writing albums into MFYN_Library on Google Drive."""
import mimetypes
import re

from googleapiclient.http import MediaFileUpload

FOLDER = "application/vnd.google-apps.folder"
PARTIAL_PREFIX = ".partial - "
# Not allowed in Windows file names, and the library is synced to H:\My Drive.
UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

mimetypes.add_type("audio/flac", ".flac")


def folder_name(artist, title):
    name = UNSAFE.sub("_", f"{artist} - {title}")
    return re.sub(r"\s+", " ", name).strip(" .")


def _find_folder(drive, parent_id, name):
    escaped = name.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name = '{escaped}' and '{parent_id}' in parents and mimeType = '{FOLDER}' and trashed = false"
    found = drive.files().list(q=q, fields="files(id)", pageSize=1).execute()["files"]
    return found[0]["id"] if found else None


def exists(drive, parent_id, name):
    return _find_folder(drive, parent_id, name) is not None


def add_album(drive, parent_id, name, files):
    """Upload files into a new folder. It's named `.partial - …` until every
    file is in, so an interrupted run never leaves a folder that looks done."""
    partial = PARTIAL_PREFIX + name
    leftover = _find_folder(drive, parent_id, partial)
    if leftover:
        drive.files().update(fileId=leftover, body={"trashed": True}).execute()

    folder_id = drive.files().create(
        body={"name": partial, "mimeType": FOLDER, "parents": [parent_id]}, fields="id"
    ).execute()["id"]
    for path in files:
        media = MediaFileUpload(
            str(path),
            mimetype=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            resumable=True,
            chunksize=16 << 20,
        )
        request = drive.files().create(body={"name": path.name, "parents": [folder_id]}, media_body=media, fields="id")
        response = None
        while response is None:
            _, response = request.next_chunk()
    drive.files().update(fileId=folder_id, body={"name": name}).execute()
