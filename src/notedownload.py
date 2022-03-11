
import uuid
from azure.identity import DeviceCodeCredential
from msgraph.core import GraphClient
from config import CLIENT_ID
from tqdm import tqdm
import logging
import os 
import re 


logger = logging.getLogger(__file__)

xml_finder = re.compile("<\?xml version=")
xml_finito_finder = re.compile("</inkml:ink>") # this is the ending tag


class NoteDownloader:
    """
    Use GraphAPI + Azure Identity library to authenticate and access 
    OneNoteAPI. Download all the pages and save them under sections pages.
    """
    def __init__(self, client_id: str, target_note_location: os.PathLike) -> None:
        scopes = ['User.Read.All', 'Notes.Read.All', 'Notes.Create', 'Notes.Read', 'Notes.ReadWrite']
        # scopes = ['User.Read.All', 'Notes.Read.All', 'Notes.Read', 'Notes.ReadWrite']
        credential = DeviceCodeCredential(client_id=client_id,  tenant_id="common")
        self.client = GraphClient(credential=credential, scopes=scopes)
        self.target_note_location = target_note_location

    def __locate_xml_part(self, response_content: str):
        """
        OneNote Graph API returns lotta rubbish alongside 
        the actual XML response, so let's strip the XML
        out of the response
        """
        if isinstance(response_content, bytes):
            # make sure we're working with a string
            response_content = str(response_content)
        match_start = xml_finder.search(response_content)
        match_end  = xml_finito_finder.search(response_content)
        if (not match_start) or (not match_end):
            raise ValueError("Could not locate boundaries of the XML in the response!")
        start = match_start.span()[0]
        end = match_end.span()[-1]
        return response_content[start:end]
        

    def __iterate_pages(self):
        result = self.client.get('/me/onenote/pages').json()
        for page in result['value']:
            page_id  = page['id']
            # the source section
            yield self.__fetch_page(page_id)

    def __fetch_page(self, note_id: int):
        # get the page infor first 
        response = self.client.get(f'/me/onenote/pages/{note_id}')
        note_info = response.json()
        if not (response.status_code in (200, 202)):
            logger.error(f"Request for page: {note_id} info failed!")
            return None, None
        response = self.client.get(f'/me/onenote/pages/{note_id}/content?includeinkML=true')
        if not (response.status_code in (200, 202)):
            logger.error(f"Request for page: {note_id} info failed!")
            return None, None
        xml_response = response.content # this is in fact XML + rubbish 
        try:
            xml_response = self.__locate_xml_part(xml_response) # this is going to be pure xml
        except ValueError as e:
            logger.error(e)
            return None, None
        return xml_response, note_info

    def save_notes(self):
        for (note, note_info) in tqdm(self.__iterate_pages(), 
        desc='Parsing all pages from OneNote...'):
            if note is None:
                continue
            note_title = note_info['title'].replace(" ", "_")
            if not len(note_title):
                note_title = str(uuid.uuid4)
            note_path = os.path.join(
                self.target_note_location, 
                note_info['parentSection']['displayName'].replace(" ", "_")
            )
            os.makedirs(note_path, exist_ok=True)
            # no need to parse the XML, let's download first
            with open(os.path.join(note_path,  f"{note_title}.xml"), 'w') as f:
                f.write(note)

if __name__ == "__main__":
    nd = NoteDownloader(CLIENT_ID, target_note_location='/Users/jm/Documents/Notes')
    nd.save_notes()
