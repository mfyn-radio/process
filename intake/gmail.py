"""Gmail access as mfyn@."""
from googleapiclient.discovery import build


def client(creds):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def label_id(service, name):
    for label in service.users().labels().list(userId="me").execute()["labels"]:
        if label["name"] == name:
            return label["id"]
    return service.users().labels().create(userId="me", body={"name": name}).execute()["id"]
