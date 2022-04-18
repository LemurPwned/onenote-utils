import glob
import os
import re
import string
from typing import Callable, Dict, Iterable

from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk
from nltk.corpus import stopwords
from rich.progress import track
from tqdm import tqdm

from onenutil.interface.zotero_con import ZoteroCon
from onenutil.schemas.results import ZoteroExtractionResult

from .extract.pdf import extract_text_pdf
from .extract.ranking import TagExtractor

eng_stopwords = stopwords.words('english')


def create_note_index(es: Elasticsearch, index: str = "notes"):
    note_map = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "note_analyzer": {
                        "type": "standard",
                    },
                },
            },
        },
        "mappings": {
            "properties": {
                "content": {
                    "type": "text",
                    "analyzer": "note_analyzer"
                },
                "name": {
                    "type": "text"
                },
                "keywords": {
                    "type": "keyword"
                },
                "path": {
                    "type": "text"
                },
                "topic": {
                    "type": "keyword"
                }
            }
        }
    }
    es.indices.delete(index, ignore=[400, 404])
    es.indices.create(index=index, body=note_map)


def create_article_index(es: Elasticsearch,
                         index: str = "articles",
                         dims: int = 384):
    article_map = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "note_analyzer": {
                        "type": "standard",
                    },
                },
            },
        },
        "mappings": {
            "properties": {
                "content": {
                    "type": "text",
                    "analyzer": "note_analyzer"
                },
                "title": {
                    "type": "text"
                },
                "keywords": {
                    "type": "keyword"
                },
                "summary": {
                    "type": "text"
                },
                "embedding": {
                    "type": "dense_vector",
                    "dims": dims
                }
            }
        }
    }
    es.indices.delete(index, ignore=[400, 404])
    es.indices.create(index=index, body=article_map)


def create_note_doc(metadata_file: os.PathLike) -> Dict[str, str]:
    """Perform basic document creation from metadata"""
    bsn = os.path.basename(metadata_file)
    with open(metadata_file, 'r') as f:
        content = f.read()
    return {
        "_index": "notes",
        "_source": {
            "name": bsn,
            "content": content,
            "path": metadata_file
        }
    }


def stream_documents(metadata_folder: os.PathLike) -> Iterable[Dict[str, str]]:
    """Streams the docs to ES server"""
    for fn in tqdm(glob.glob(os.path.join(metadata_folder, "*.txt")),
                   desc="Streaming notes..."):
        yield create_note_doc(fn)


def create_es_instance() -> Elasticsearch:
    """Creates es instance"""
    return Elasticsearch()


def stream_pdfs(pdf_folder: os.PathLike) -> Iterable[Dict[str, str]]:
    """Streams pdf text to ES server"""
    tag_extractor = TagExtractor()
    fn_list = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    for fn in track(fn_list,
                    total=len(fn_list),
                    description="Streaming notes..."):
        content = extract_text_pdf(filename=fn)
        if not content:
            print("Content empty, skipping...: ", fn)
            continue
        bsn = os.path.basename(fn).replace(".pdf", "")
        bsn = bsn.lower()
        exclude = set(string.punctuation)
        s = ''.join(ch for ch in bsn if ch not in exclude)
        keywords = re.findall(r'\w+', s)
        keywords = [w for w in keywords if not w.lower() in eng_stopwords]

        tag_extraction = tag_extractor(content)
        yield {
            "_index": "notes",
            "_source": {
                "name": bsn,
                "keywords": tag_extraction.keywords,
                "summary": tag_extraction.summary,
                "path": fn,
                "content": content
            }
        }


def stream_zotero() -> Iterable[Dict[str, str]]:
    """Streams zotero data to ES server"""
    zotero_streamer = ZoteroCon()
    item: ZoteroExtractionResult
    for item in zotero_streamer():
        yield {
            "_index": "articles",
            "_source": {
                "title": item.article_name,
                "keywords": item.article_tags.keywords,
                "summary": item.article_tags.summary,
                "embedding": item.article_embeddings.embedding,
            }
        }


def run_zotero_upload():
    """Upload zotero data to ES server"""
    stream = stream_zotero()
    es = create_es_instance()
    # create or replace the index
    create_article_index(es)
    for ok, response in streaming_bulk(es,
                                       actions=tqdm(stream,
                                                    desc='Streaming zotero'),
                                       index="articles"):
        if not ok:
            print(response)


def run_note_upload(file_folder: os.PathLike, stream_fn: Callable):
    """Upload data using a given stream"""
    stream = stream_fn(file_folder)
    es = create_es_instance()
    # create or replace the index
    create_note_index(es)
    for ok, response in streaming_bulk(
            es,
            actions=tqdm(stream,
                         desc=f'Uploading documents [{file_folder}]...')):
        if not ok:
            print(response)
