import asyncio
from pathlib import Path
import argparse

from rich.panel import Panel
from textual import events, log as textual_log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.widgets import Header, Placeholder, Footer

from mini_projects.nimsuggest_tui.nimsuggest_tui import NimSuggest, NimSuggestCommands


class Logger:
    def __call__(self, *args: object, **kwargs: object) -> None:
        textual_log(Panel(*args, **kwargs, style="on red"))

    def __getattr__(self, name: str) -> object:
        attr = getattr(textual_log, name)
        if callable(attr):

            def wrapper(*args: object, **kwargs: object) -> None:
                attr(Panel(*args, **kwargs, style="on red"))

            return wrapper


log = Logger()


class MyApp(App):
    BINDINGS = (Binding("q", "quit", "Quit"),)

    def __init__(self) -> None:
        super().__init__()

        self.log(Panel("Hello, world!"))
        self.log("hello")

        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--project-file", type=Path, help="Path to .nimble project file")
        args = parser.parse_args()

        self.project_file = args.project_file or Path("mini_projects.nimble")
        self.project_nim_files = self.project_file.parent.rglob("**/*.nim")

        self.log.info(f"Project file: {self.project_file}")
        self.log.info(f"Project files: {self.project_nim_files}")

        self._nimsuggest = NimSuggest(self.project_file)

    async def _provide_suggestions(self):
        async with self._nimsuggest:
            for file in self.project_nim_files:
                self.log.info(f"Providing suggestions for {file}")
                await self._nimsuggest.send(NimSuggestCommands.sug, file, 1, 0)

    async def on_click(self, event: events.Click) -> None:
        log.error(f"Mickey move: {event}")

    def compose(self) -> ComposeResult:
        yield Header(name="NimSuggest TUI")
        yield Grid(
            Placeholder(),
            Placeholder(),
            Placeholder(),
        )
        yield Footer()


if __name__ == "__main__":
    MyApp().run()
