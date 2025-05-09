# Note generator


## Kindle 

### Scrapping highlights 

Use Amazon email and password.

```bash
python3 kindle/notescrap.py --email mymail@whatever.com --password myamazonpass
```

This command will generate `kindle_highlights.json` file. 


### Obsidian note generator 

Generate Obsidian notes from your Kindle highlights.

```bash
python3 kindle/agent.py --highlights kindle-highlights.json
```
This will create a folder with obsidian notes for each of the books. A note will not be generated if there's fewer than 3 highlights. 

To interactively select which books to process:
```bash
python3 kindle/agent.py --highlights kindle-highlights.json --interactive
```
This will show books in batches of 10 and allow you to select specific books to process.


See help for more options like output dir and model change:
```bash 
python3 kindle/agent.py --help
```
