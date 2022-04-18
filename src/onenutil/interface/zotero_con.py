import os
from typing import Iterable

from pyzotero import zotero

from ..extract.embeddings import EmbeddingsExtractor
from ..extract.ranking import TagExtractor
from ..schemas import ZoteroExtractionResult
from rich.progress import track


class ZoteroCon:

    def __init__(self, library_id: str, api_key: str) -> None:
        self.zot = zotero.Zotero(library_id=library_id,
                                 library_type='user',
                                 api_key=api_key)
        self.embeddings_extractor = EmbeddingsExtractor()
        self.tag_extractor = TagExtractor()

    @classmethod
    def create_zotero_connection(cls,
                                 library_id: str = "",
                                 api_key: str = "") -> 'ZoteroCon':
        """Create a connection to the Zotero library"""
        if library_id and api_key:
            return cls(library_id=library_id, api_key=api_key)
        try:
            library_id = os.environ['ZOTERO_LIBRARY_ID']
            api_key = os.environ['ZOTERO_API_KEY']
        except KeyError:
            library_id = input('Zotero library id: ')
            api_key = input('Zotero api key: ')

        return cls(library_id=library_id, api_key=api_key)

    def get_items(self, item_type: str = "journalArticle") -> Iterable[dict]:
        """Get the items from the Zotero library
        :param item_type: the type of item to get
        :return: the items
        """
        itms = self.zot.everything(self.zot.items(itemType=item_type))
        total = len(itms)
        for item in track(itms,
                          total=total,
                          description="Parsing Zotero library"):
            yield item

    def get_tags(self, abstract_content: str):
        return self.tag_extractor(abstract_content)

    def get_embeddings(self, summary: str):
        return self.embeddings_extractor(summary)

    def __call__(self) -> Iterable[ZoteroExtractionResult]:
        """Extract the tags and embeddings from the Zotero library"""
        for item in self.get_items():
            abstract_content = item['data'].get('abstractNote', '')
            title = item['data'].get('title', '')
            if (not abstract_content) or (not title):
                # this is empty
                continue
            tags = self.get_tags(abstract_content)
            embeddings = self.get_embeddings(tags.summary)
            authors = [
                f"{dat.get('firstName', '')} {dat.get('lastName', '')}"
                for dat in item['data']['creators']
            ]

            yield ZoteroExtractionResult(
                article_tags=tags,
                article_embeddings=embeddings,
                article_name=item['data']['title'],
                article_authors=authors,
                abstract=abstract_content)
