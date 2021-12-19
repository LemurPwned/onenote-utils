from requests import Session
import os

from requests.api import head

PAGE_URL = "https://graph.microsoft.com/v1.0/me/onenote/pages/{note_id}/content"


class NoteDownloader:
    def __init__(self) -> None:
        self.session = Session()

    def download_note(self, note_id: str, include_ink: bool = True):
        req_url = PAGE_URL.format(note_id)
        headers = {
            "Authorization": "Bearer {}".format(
                os.environ["API_TOKEN"]
            )
        }
        if include_ink:
            req_url += "?includeinkML=true"
        self.session.get(
            req_url, headers=headers
        )
