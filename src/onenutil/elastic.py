import string
import glob
import os
import re

from nltk.corpus import stopwords

from typing import Callable, Dict, Iterable

from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk
from tqdm import tqdm

from .extract.pdf import extract_text_pdf


eng_stopwords = stopwords.words('english')

def create_note_index(es: Elasticsearch, index: str = "notes"):
    dense_funds = {
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
                "keywords":{
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
    es.indices.create(index=index, body=dense_funds)


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
    for fn in tqdm(glob.glob(os.path.join(metadata_folder, "*.txt")), desc="Streaming notes..."):
        yield create_note_doc(fn)


def create_es_instance() -> Elasticsearch:
    """Creates es instance"""
    return Elasticsearch()


def stream_pdfs(pdf_folder: os.PathLike) -> Iterable[Dict[str, str]]:
    """Streams pdf text to ES server"""
    for fn in tqdm(glob.glob(os.path.join(pdf_folder, "*.pdf")), desc="Streaming notes..."):
        content = extract_text_pdf(filename=fn)
        if not content:
            continue
        bsn = os.path.basename(fn).replace(".pdf", "")
        bsn = bsn.lower()
        exclude = set(string.punctuation)
        s = ''.join(ch for ch in bsn if ch not in exclude)
        keywords = re.findall(r'\w+', s)
        keywords = [w for w in keywords if not w.lower() in eng_stopwords]

        yield {
            "_index": "notes", 
            "_source": {
                "name": bsn,
                "keywords": keywords,
                "path": fn,
                "content": content
            }
        }

def run_upload(file_folder: os.PathLike, stream_fn: Callable):
    """Upload data using a given stream"""
    stream = stream_fn(file_folder)
    es = create_es_instance()
    # create or replace thei ndex
    create_note_index(es)
    for ok, response in streaming_bulk(es, actions=tqdm(stream, desc=f'Uploading documents [{file_folder}]...')):
        if not ok:
            print(response)


