import cmd
import sys
import shlex

from elasticsearch.client import Elasticsearch

from src.onenutil.elastic import create_es_instance
from .search import basic_search, search_format
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText


# The style sheet.
style = Style.from_dict({
    'error': '#ff0066 italic',
})

class NoteSearchShell(cmd.Cmd):
    intro = 'Welcome to notes-search shell.\tType help or ? to list commands.\n'
    prompt = '(notes) '
    es_instance: Elasticsearch = create_es_instance()
    index = "notes"
    def do_search(self, arg):
        """
        Do basic note search.
        """
        arg_parsed = shlex.split(arg)
        if not len(arg_parsed):
            print_formatted_text(
                FormattedText([
                ("class:error", "You need to provide a search phrase!")
                ]), style=style)
                
            return
        print(f"Performing a search on: {arg_parsed}")
        result = basic_search(self.es_instance, arg_parsed[0], self.index)
        search_format(result)
        
    def do_quit(self, _):
        """
        Quits the programme.
        """
        sys.exit(0)

if __name__ == '__main__':
    NoteSearchShell().cmdloop()