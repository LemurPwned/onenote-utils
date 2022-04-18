from typing import Dict, List, Tuple

import rich.box
from elasticsearch_dsl.connections import connections
from rich.panel import Panel
from rich.table import Table
from textual.app import App
from textual.widgets import Header, ScrollView, Static
from textual_inputs import TextInput

from onenutil.elastic import create_es_instance
from onenutil.interface.search import search_dsl
from onenutil.schemas.results import ArticleSearchResult


class SearchApp(App):

    def __init__(self,
                 screen: bool = True,
                 driver_class: None = None,
                 log: str = "",
                 log_verbosity: int = 1,
                 title: str = "Note search"):
        super().__init__(screen, driver_class, log, log_verbosity, title)
        self.es = create_es_instance()
        connections.create_connection(hosts=["localhost"])

    def build_search_bar(self):
        self.text_input = TextInput(name='search_term',
                                    placeholder='enter query...',
                                    title='Search',
                                    syntax='markdown',
                                    prompt="Search term: ",
                                    theme='monokai')
        return self.text_input

    async def on_load(self):
        await self.bind("enter", "search", "Search")

    async def populate_facets(self, facets: List[List[Tuple[str, int]]]):
        table = Table(show_lines=True, highlight=True)
        table.add_column("Facet", justify="left")
        table.add_column("Count", justify="center")
        for facet_group in facets:
            for (key, count) in facet_group:
                table.add_row(key, str(count))
            table.add_row("--", "--")
        await self.facet_box.update(
            Panel(table,
                  title="Facets",
                  border_style='yellow',
                  box=rich.box.SQUARE))

    async def populate_search_results(self,
                                      search_results: ArticleSearchResult):
        table = Table(show_lines=True, highlight=True)
        table.add_column("Score")
        table.add_column("Article", justify="left")
        # table.add_column("url", title="URL")
        table.add_column("Highlight", justify="right")
        table.add_column("Tags", justify="right")
        highlight_format = "[bold red]"
        for (highlight, score, title,
             tag) in zip(search_results.highlights, search_results.scores,
                         search_results.titles, search_results.tags):
            highlight = highlight.replace("<em>", highlight_format).replace(
                "</em>", f"[/]").replace("\n", " ")
            # highlight = "\n".join(highlight)
            table.add_row(
                str(score),
                title,
                # url=result.url,
                highlight,
                tag)
        await self.populate_facets(
            [search_results.keyword_terms, search_results.authors_terms])
        await self.body.update(
            Panel(table,
                  title="Search results",
                  border_style='red',
                  box=rich.box.SQUARE))

    async def action_search(self):
        self.search_value = self.text_input.value
        search_result = search_dsl(self.search_value)
        await self.populate_search_results(search_result)

    async def on_mount(self) -> None:
        self.facet_box = Static(renderable=Panel(
            "", title="Facets", border_style='yellow', box=rich.box.SQUARE))
        self.body = ScrollView(auto_width=False)
        await self.body.update(
            Panel(Table(),
                  title="Search results",
                  border_style='red',
                  box=rich.box.SQUARE))
        await self.view.dock(Header(style="white on black"), edge='top')
        await self.view.dock(self.facet_box, edge="left", size=48)
        await self.view.dock(self.build_search_bar(),
                             edge="top",
                             name='searchbar',
                             size=3)
        await self.view.dock(self.body, edge="bottom")


SearchApp.run(log="textual.log")
