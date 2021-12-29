import os

import click

from .interface.search import basic_search, search_format
from .elastic import create_es_instance, run_upload, stream_pdfs
from .interface.shell import NoteSearchShell


@click.group()
def cli():
    ...

@cli.command(name='start', help="Start search shell")
def start_shell():
    NoteSearchShell().cmdloop()
    

@cli.command(name='search', help='Do a single search')
@click.argument("phrase", type=str)
def upload_folder(phrase: os.PathLike): 
    es_instance = create_es_instance()
    results = basic_search(
        es_instance, phrase, "notes"
    )
    search_format(results)



@cli.command(name='upload', help='Upload a given folder to ES')
@click.argument("path", type=click.Path(exists=True))
def upload_folder(path: os.PathLike): 
    run_upload(path, stream_fn=stream_pdfs)
    print("Upload completed successfully")

if __name__ == "__main__":
    cli()
