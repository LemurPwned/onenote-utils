import xml
from typing import Dict, List

from elasticsearch import Elasticsearch
from elasticsearch_dsl import (DenseVector, Document, FacetedSearch, Keyword,
                               TermsFacet, Text)
from prompt_toolkit import HTML, print_formatted_text
from prompt_toolkit.styles import Style

from onenutil.schemas import ArticleSearchResult

style = Style.from_dict({
    "em": '#ff0066',
})


def basic_search(es: Elasticsearch, phrase: str, index: str) -> List[str]:
    """Basic search functionality:
    :param phrase: basic query string search on content field
    :param index: index to search through.
    """
    query = {
        'query': {
            'simple_query_string': {
                'query': phrase,
                "fields": ["content"]
            }
        },
        "highlight": {
            "fields": {
                "content": {}  # highlight here
            }
        }
    }
    results = es.search(index=index, body=query)
    return [r for r in results['hits']['hits']]


def search_format(search_list: List[Dict[str, str]], k: int = 10):
    """Format the search results according to some basic formatting style.
    :param search_list: list of plain search results returned
    :param k: top K results limiter
    """
    for i, sr in enumerate(search_list):
        score = sr['_score']
        indx = sr['_index']
        ref = sr["_source"]["path"]
        keywords = sr["_source"]["keywords"]
        name_href = f'<u><a href="{ref}">"file://{ref}"</a></u>'
        print_formatted_text(
            HTML(f"<violet>[{name_href}]</violet>"
                 f"\n<ansired>[{i}]</ansired>"
                 f"<skyblue>[index:{indx}]</skyblue>"
                 f"<ansigreen>[{score:.3f}]</ansigreen>"
                 f"\n<yellow>{keywords}</yellow>"))
        for cont in sr['highlight']['content']:
            try:
                print_formatted_text(HTML(cont.strip().replace("\n", "")),
                                     style=style)
            except xml.parsers.expat.ExpatError:
                continue
        if i >= k:
            return


class Article(Document):
    """
    Article class
    """
    title = Text()
    keywords: Keyword()
    summary: Text()
    embedding: DenseVector(384)


class ArticleSearch(FacetedSearch):
    index = "articles"
    doc_types = [Article]

    facets = {
        'keywords': TermsFacet(field='keywords'),
        'authors': TermsFacet(field='authors')
    }
    fields = ['title', 'keywords', 'summary']


def search_dsl(phrase: str, index: str = 'articles') -> List[str]:
    """Search using the elasticsearch_dsl library.
    :param phrase: basic query string search on content field
    """
    ArticleSearch.index = index.strip()
    s = ArticleSearch(phrase)
    response = s.execute()
    tag_terms = [(tag, count) for (tag, count, _) in response.facets.keywords]
    authors_terms = [(authors, count)
                     for (authors, count, _) in response.facets.authors]

    scores = []
    highlights = []
    titles = []
    tags = []
    paths = []
    for hit in response.hits:
        scores.append(hit.meta.score)
        titles.append(hit.title)
        highlight = []
        for k in hit.meta.highlight:
            highlight.append("\n".join(hit.meta.highlight[k]))
        highlight = "\n".join(highlight)
        highlights.append(highlight)
        tags.append(",".join(hit.keywords))
        paths.append(hit.path)

    return ArticleSearchResult(scores=scores,
                               highlights=highlights,
                               titles=titles,
                               tags=tags,
                               paths=paths,
                               keyword_terms=tag_terms,
                               authors_terms=authors_terms)


if __name__ == "__main__":
    from elasticsearch_dsl.connections import connections

    connections.create_connection(hosts=["localhost"])
    phrase = "machine learning"
    search_list = search_dsl(phrase)
    print(search_list)
