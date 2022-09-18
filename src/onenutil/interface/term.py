import glob
from typing import List, Tuple

import rich.box
from elasticsearch import NotFoundError
from elasticsearch_dsl.connections import connections
from rich.panel import Panel
from rich.table import Table
from textual.app import App
from textual.widgets import Header, ScrollView, Static
from textual_inputs import TextInput

from onenutil.elastic import create_es_instance
from onenutil.interface.search import search_dsl
from onenutil.schemas.results import ArticleSearchResult
from textual.reactive import Reactive
from textual.widget import Widget


class Hover(Widget):

    mouse_over = Reactive(False)

    def render(self) -> Panel:
        return Panel("Hello [b]World[/b]",
                     style=("on red" if self.mouse_over else ""))

    def on_enter(self) -> None:
        self.mouse_over = True

    def on_leave(self) -> None:
        self.mouse_over = False


class SearchApp(App):
    """
    A basic search interface with term aggregation.
    """

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
        await self.bind("q", "quit", "quit")

    async def populate_facets(self, facets: List[List[Tuple[str, int]]]):
        table = Table(show_lines=True, highlight=True, expand=True)
        table.add_column("Facet", justify="left")
        table.add_column("Count", justify="center")
        for facet_group in facets:
            for (key, count) in facet_group:
                table.add_row(key, str(count))
            table.add_row(end_section=True)
        await self.facet_box.update(
            Panel(table,
                  title="Facets",
                  border_style='yellow',
                  box=rich.box.SQUARE))

    async def populate_search_results(self,
                                      search_results: ArticleSearchResult):
        table = Table(show_lines=True, highlight=True, expand=True)
        table.add_column("Score")
        table.add_column("Article", justify="left")
        table.add_column("Highlight", justify="right")
        table.add_column("Tags", justify="right")
        highlight_format = "[bold red]"
        for (highlight, score, title, tag,
             path) in zip(search_results.highlights, search_results.scores,
                          search_results.titles, search_results.tags,
                          search_results.paths):
            highlight = highlight.replace("<em>", highlight_format).replace(
                "</em>", f"[/]").replace("\n", " ")
            fns = glob.glob(f"/Users/jm/Zotero/storage/{path}/*.pdf")
            if fns:
                local_path = "file://{}".format(fns[0]).replace(" ", "%20")
                title_str = f"[link={local_path}]{title}[/link]"
            else:
                title_str = title
            table.add_row(str(score), title_str, highlight, tag)
        await self.populate_facets(
            [search_results.keyword_terms, search_results.authors_terms])
        await self.body.update(
            Panel(table,
                  title="Search results",
                  border_style='red',
                  box=rich.box.SQUARE))

    async def action_search(self):
        self.search_value = self.text_input.value
        if self.search_value:
            try:
                search_result = search_dsl(self.search_value,
                                           self.index_str.value)
                await self.populate_search_results(search_result)
            except NotFoundError:
                await self.body.update(
                    Panel(Table(),
                          title=f"No index:{self.index_str.value} found",
                          border_style='red',
                          box=rich.box.SQUARE))

    async def action_clear(self):
        self.text_input.value = ""

    def index_select(self):
        self.index_str = TextInput(name='index_select',
                                   placeholder='articles',
                                   title='Index',
                                   syntax='markdown',
                                   prompt="Type in index",
                                   theme='monokai')
        return self.index_str

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
        await self.view.dock(self.index_select(), edge='right', size=20)
        await self.view.dock(self.facet_box, edge="left", size=48)
        await self.view.dock(self.build_search_bar(),
                             edge="top",
                             name='searchbar',
                             size=3)
        await self.view.dock(self.body, edge="left")
