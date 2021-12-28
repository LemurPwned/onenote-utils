from typing import Dict, Iterable
from tqdm import tqdm
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk
import os
import glob


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
                "url": {
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


def create_note_doc(metadata_file: os.Pathlike) -> Dict[str, str]:
    """Perform basic document creation from metadata"""
    bsn = os.path.basename(metadata_file)
    with open(metadata_file, 'r') as f:
        content = f.read()
    return {
        "_index": "notes",
        "_source": {
            "name": bsn,
            "content": content
        }
    }


def stream_documents(metadata_folder: os.PathLike) -> Iterable[Dict[str, str]]:
    """Streams the docs to ES server"""
    for fn in tqdm(glob.glob(os.path.join(metadata_folder, "*.txt")), desc="Streaming notes..."):
        yield create_note_doc(fn)


def create_es_instance() -> Elasticsearch:
    """Creates es instance"""
    return Elasticsearch()


def run_notes_upload(metadata_folder: os.PathLike):
    """Launches the note upload"""
    stream = stream_documents(metadata_folder)
    es = create_es_instance()
    # create or replace thei ndex
    create_note_index(es)
    for ok, response in streaming_bulk(es, actions=stream):
        if not ok:
            print(response)
