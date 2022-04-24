from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table


@dataclass
class TagResult:
    """Store the results of the tag extraction"""
    keywords: List[str]
    summary: List[str]

    def __rich_console__(self, console: Console,
                         options: ConsoleOptions) -> RenderResult:
        """
        Render the results table
        """
        table = Table(title="Keywords")
        table.add_column("Keywords", justify="left")
        table.add_column("Summary", justify="left")
        table.add_row(",".join(self.keywords), "\n".join(self.summary))
        yield table


@dataclass
class EmbeddingsResult:
    """Store the results of the embeddings extraction"""
    embedding: List[float]
    model_name: str


@dataclass
class ZoteroExtractionResult:
    """Store the results of the Zotero extraction"""
    article_tags: TagResult
    article_embeddings: EmbeddingsResult
    article_name: str
    article_authors: List[str]
    abstract: str = ""
    article_path: str = ""

    def __rich_console__(self, console: Console,
                         options: ConsoleOptions) -> RenderResult:
        """
        Render the results table
        """
        table = Table(title=self.article_name)
        table.add_column("Authors", justify="left")
        table.add_column("Keywords", justify="left")
        table.add_column("Summary", justify="left")
        table.add_row(",".join(self.article_authors),
                      ", ".join(self.article_tags.keywords),
                      "\n".join(self.article_tags.summary))
        yield table


@dataclass
class SearchResult:
    """
    Search result class
    """
    query: str
    results: List[Dict[str, Any]]

    @staticmethod
    def create_table(query, search_results):
        """
        Create and display a table
        """
        table = Table(title=f"Search Results [{query}]")
        table.add_column("#", justify="right")
        table.add_column("Score", justify="right")
        table.add_column("File", justify="left")
        table.add_column("Highlight", justify="center")
        table.add_column("Keyword/Tags", justify="left")
        highlight_format = "[bold red]"
        for i, result in enumerate(search_results):
            highlights = [
                highlight.replace("<em>",
                                  highlight_format).replace("</em>", f"[/]")
                for highlight in result["highlight"]["content"]
            ]
            highlights = "\n".join(highlights)
            table.add_row(str(i), str(result["_score"]),
                          result["_source"]["name"], highlights,
                          ",".join(result["_source"]["keywords"]))
        return table

    def __rich_console__(self, console: Console,
                         options: ConsoleOptions) -> RenderResult:
        """
        Render the results table
        """
        yield SearchResult.create_table(self.query, self.results)

    @classmethod
    def from_search(cls, query, es_search):
        """
        Create a SearchResult from a search
        """
        return cls(query=query, results=es_search)


@dataclass
class ArticleSearchResult:
    scores: List[float]
    highlights: List[str]
    titles: List[str]
    tags: List[str]
    keyword_terms: List[Tuple[str, int]]
    authors_terms: List[Tuple[str, int]]
    paths: List[str]
