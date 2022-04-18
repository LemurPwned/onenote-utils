
from textual.app import App
from textual.widgets import  Static, ScrollView, Header
from textual_inputs import TextInput
import rich.box 
from rich.panel import Panel
from rich.table import Table
from typing import List
from onenutil.interface.search import basic_search
from onenutil.schemas import SearchResult
from onenutil.elastic import create_es_instance


class SearchApp(App):

    def __init__(self, screen: bool = True, driver_class:  None = None, log: str = "", 
                    log_verbosity: int = 1, title: str = "Note search"):
        super().__init__(screen, driver_class, log, log_verbosity, title)
        self.es = create_es_instance()    

    def build_search_bar(self):
        self.text_input =  TextInput(
            name='search_term',
            placeholder='enter query...',
            title='Search',
            syntax='markdown',
            prompt="Search term: ",
            theme='monokai'
        )
        return self.text_input

    async def on_load(self):
        await self.bind("enter", "search", "Search")

    async def populate_search_results(self, search_results: List[SearchResult]):
        table = Table(show_lines=True, highlight=True)
        table.add_column("Score")
        table.add_column("Article", justify="left")
        # table.add_column("url", title="URL")
        table.add_column("Highlight", justify="right")
        highlight_format = "[bold red]"
        for result in search_results.results:
            highlights = [
                highlight.replace("<em>", highlight_format).replace("</em>", f"[/]").replace("\n", " ") 
                for highlight in result["highlight"]["content"]
            ]
            highlights = "\n".join(highlights)
            table.add_row(
                str(result['_score']),
                result['_source']['name'],
                # url=result.url,
                highlights
            )
        await self.body.update(Panel(table, title="Search results", border_style='red', box=rich.box.SQUARE))

    async def action_search(self):
        self.search_value = self.text_input.value
        results = basic_search(self.es, self.search_value, 'notes')
        await self.populate_search_results(SearchResult.from_search(self.search_value, results))

    async def on_mount(self) -> None:
        self.output = Static(
            renderable=Panel(
                "", title="Facets", border_style='yellow', box=rich.box.SQUARE
            )
        )
        self.body= ScrollView(auto_width=False)
        await self.body.update(Panel(Table(), title="Search results", border_style='red', box=rich.box.SQUARE))
        await self.view.dock(Header(style="white on black"), edge='top')
        await self.view.dock(self.output, edge="left", size=48)
        await self.view.dock(self.build_search_bar(), edge="top", name='searchbar', size=3)
        await self.view.dock(self.body, edge="bottom")


SearchApp.run(log="textual.log")