import os
import warnings

import click

from .elastic import (create_es_instance, run_note_upload, run_zotero_upload,
                      stream_pdfs)
from .interface.search import basic_search, search_format
from .interface.term import SearchApp

warnings.filterwarnings(action='ignore')

@click.group()
def cli():
    ...


@cli.command(name='start', help="Start search application")
def start_shell():
    SearchApp.run(log="textual.log")


@cli.command(name='search', help='Do a single search')
@click.argument("phrase", type=str)
def upload_folder(phrase: os.PathLike):
    es_instance = create_es_instance()
    results = basic_search(es_instance, phrase, "notes")
    search_format(results)


@cli.command(name='upload', help='Upload a given folder to ES')
@click.argument("path", type=click.Path(exists=True))
def upload_folder(path: os.PathLike):
    run_note_upload(path, stream_fn=stream_pdfs)
    print("Upload completed successfully")


@cli.command(name='zotero-upload', help='Upload zotero data to ES')
def upload_zotero():
    # TODO: check for the environment secrets
    run_zotero_upload()
    print("Upload completed successfully")


if __name__ == "__main__":
    cli()
