from collections import Counter

from ..schemas import ZoteroExtractionResult


class GraphStatistics:

    def __init__(self):
        self.stats = {'authors': Counter(), 'keywords': Counter(), 'total': 0}

    def add_zotero_entry(self, zotero_entry: ZoteroExtractionResult):
        for keyword in zotero_entry.article_tags.keywords:
            self.stats['keywords'][keyword] += 1
        for author in zotero_entry.article_authors:
            self.stats['authors'][author] += 1
        self.stats['total'] += 1
