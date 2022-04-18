# OneNote utils

This is a package that allows you to do simple operations on OneNote notes written with InkNode (e-pen).
Here's a listing of functionalities you may expect:

1. Generating image or pdf from OneNote ink node.
2. Link and generate search index from Zotero account 
3. TUI supporting the searchable indexes from notes. 

That's it.

Cheers.

## Quickstart

Install by going:

```
python3 -m pip install onenutils
```

### Running Elasticsearch

Run a local ES. This deploys a single-node docker cluster:

```bash
docker run -p 9200:9200 -p 9300:9300 \
           -e "discovery.type=single-node" \
           docker.elastic.co/elasticsearch/elasticsearch:7.13.4
```

## Rationale

The OneNote export to PDF is simply terrible experience. The pages are weirdly cut and moved around instead of a continuous page like you can have from the iOS. In addition, you have NO option to export ALL the notes (or more than a single page) at once.
This package sort of aims to do just that. Export bunch of stuff automatically and forget about that god-awful app.

## Stack

Uses:

- `Beautiful Soup` 4 for XML parsing
- `pillow` for Image generation
- `MicrosoftGraph` for connecting to OneNote server and exporting your notes.
