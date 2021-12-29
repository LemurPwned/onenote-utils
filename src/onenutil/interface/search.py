from elasticsearch import Elasticsearch
from typing import Dict, List
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.styles import Style 
import xml

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
            HTML(
                f"<violet>[{name_href}]</violet>"
                f"\n<ansired>[{i}]</ansired>"
                f"<skyblue>[index:{indx}]</skyblue>"
                f"<ansigreen>[{score:.3f}]</ansigreen>"
                f"\n<yellow>{keywords}</yellow>"
            )
        )
        for cont in sr['highlight']['content']:
            try:
                print_formatted_text(
                 HTML(cont.strip().replace("\n", "")), style=style)
            except xml.parsers.expat.ExpatError:
                continue
        if i >= k:
            return
        