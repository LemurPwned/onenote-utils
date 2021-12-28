

from config import CLIENT_SECRET, CLIENT_ID, TENNANT_ID

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

import os 
ME_URL = "https://graph.microsoft.com/v1.0/me/onenote{}"
CORE_URL = "https://graph.microsoft.com/v1.0/users/{}/onenote{}"
PAGE_URL = "https://graph.microsoft.com/v1.0/me/onenote/pages/{note_id}/content"


class NoteDownloader:
    def __init__(self, client_id: str, client_secret: str, directory_id: str) -> None:
        self.scope = ["https://graph.microsoft.com/.default"]
        self.token_url = "https://login.microsoftonline.com/{}/oauth2/v2.0/token"
        self.session, self.token = self.__init_session(
            client_id, client_secret, directory_id
        )
        self.headers = {
            "Authorization": "Bearer {}".format(
                self.token
            )
        }

    def __init_session(self, client_id: str, client_secret: str, directory_id: str):
        """
        OAuth2 to get access token
        First set up a backend client, mind to set grant_type
        build a OAuth2 Session with the client
        get access token

        Mind: python 3.x oauthlib requires scope params on more calls than py 2.x
        """
        client = BackendApplicationClient(
            client_id=client_id, scope=self.scope, grant_type="client_credentials")
        session = OAuth2Session(client=client, scope=self.scope)
        # fill access token
        token = session.fetch_token(token_url=self.token_url.format(directory_id),
                                    client_id=client_id,
                                    scope=self.scope,
                                    client_secret=client_secret)

        return session, token


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


    def list_notebooks(self, uid: str):
        PTH = CORE_URL.format(uid, "/notebooks")
        # PTH = ME_URL.format("/notebooks")
        response = self.session.get(PTH , headers=self.headers)
        print(response.status_code)
        print(response.json())




if __name__ == "__main__":
    nd = NoteDownloader(
        CLIENT_ID, CLIENT_SECRET, TENNANT_ID
    )
    UID = "2DEA5DF71E06A510"
    nd.list_notebooks(uid=UID)