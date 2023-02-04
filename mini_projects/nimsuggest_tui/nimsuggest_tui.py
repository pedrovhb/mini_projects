from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import NamedTuple, AsyncIterable
import asyncio


class NimSuggestCommands(str, Enum):
    sug = "sug"
    con = "con"
    def_ = "def"
    use = "use"
    dus = "dus"
    chk = "chk"
    mod = "mod"
    highlight = "highlight"
    outline = "outline"
    known = "known"
    project = "project"


async def query_nimsuggest(
    command_type: str,
    file: str | Path,
    line: int | None = None,
    col: int | None = None,
    host: str = "localhost",
    port: int = 6000,
) -> AsyncIterable[str]:
    reader, writer = await asyncio.open_connection(host, port)

    location = f"{file}:{line}:{col}" if line and col else file
    command = f"{command_type} {location}\n"
    writer.write(command.encode())
    await writer.drain()

    async for line in reader:
        decoded = line.decode().strip()
        if not decoded:
            continue
        yield decoded
    writer.close()


class NimSuggestionOutput(NamedTuple):
    """A suggestion from nimsuggest.

    The following is an example of the output of nimsuggest:

        sug	skType	system.csize	csize
        /nix/store/xi5jh6390c45l1rdlhi18g7f0pcns5xh-nim-unwrapped-1.6.10/nim/lib/system.nim	1418
        2	"This isn\'t the same as `size_t` in *C*. Don\'t use it."	95	None

    The output consists of a tab-separated list of properties including:
        1. The suggestion type (sug)
        2. The type of the suggestion (skType)
        3. The name of the module (system.csize)
        4. The name of the symbol (csize)
        5. The path to the file containing the symbol (system.nim)
        6. The line number of the symbol (1418)
        7. The column number of the symbol (2)
        8. The documentation of the symbol (This isn't the same as `size_t` in *C*. Don't use it.)
        9. The score of the suggestion (95)
        10. The parent of the symbol (None)
    """

    suggestion_type: str
    suggestion_node_type: str
    module: str
    symbol: str
    file: Path
    line: int
    column: int
    documentation: str
    score: int
    parent: str

    @classmethod
    async def query(
        cls,
        file: str | Path,
        line: int | None = None,
        col: int | None = None,
        host: str = "localhost",
        port: int = 6000,
    ) -> AsyncIterable[NimSuggestionOutput]:
        async for line in query_nimsuggest("sug", file, line, col, host, port):
            yield cls.from_line(line)

    @classmethod
    def from_line(cls, output: str) -> NimSuggestionOutput:
        """Parse a nimsuggest output string into a NimSuggestionOutput."""
        (
            suggestion_type,
            suggestion_node_type,
            module,
            symbol,
            file,
            line,
            column,
            documentation,
            score,
            parent,
        ) = output.split("\t")
        return cls(
            suggestion_type=suggestion_type,
            suggestion_node_type=suggestion_node_type,
            module=module,
            symbol=symbol,
            file=Path(file),
            line=int(line),
            column=int(column),
            documentation=documentation,
            score=int(score),
            parent=parent,
        )


class NimDefinitionOutput(NamedTuple):
    """A nimsuggest definition output.

    The output consists of a tab-separated list of properties including:

        1. The suggestion type (def)
        2. The type of the suggestion (skProc)
        3. The name of the module (xlib.XDefaultScreen)
        4. The name of the symbol (proc (para1: PDisplay): cint{.cdecl.})
        5. The path to the file containing the symbol (xlib.nim)
        6. The line number of the symbol (1536)
        7. The column number of the symbol (5)
        8. The documentation of the symbol (empty)
        9. The score of the suggestion (100)
    """

    suggestion_type: str
    suggestion_node_type: str
    module: str
    symbol: str
    file: Path
    line: int
    column: int
    documentation: str
    score: int

    @classmethod
    async def query(
        cls,
        file: str | Path,
        line: int | None = None,
        col: int | None = None,
        host: str = "localhost",
        port: int = 6000,
    ) -> AsyncIterable[NimDefinitionOutput]:
        async for line in query_nimsuggest("def", file, line, col, host, port):
            yield cls.from_line(line)

    @classmethod
    def from_line(cls, output: str) -> NimDefinitionOutput:
        """Parse a nimsuggest output string into a NimSuggestionOutput."""
        (
            suggestion_type,
            suggestion_node_type,
            module,
            symbol,
            file,
            line,
            column,
            documentation,
            score,
        ) = output.split("\t")
        return cls(
            suggestion_type=suggestion_type,
            suggestion_node_type=suggestion_node_type,
            module=module,
            symbol=symbol,
            file=Path(file),
            line=int(line),
            column=int(column),
            documentation=documentation,
            score=int(score),
        )


class NimUseOutput(NamedTuple):
    """A nimsuggest use output.

    The output consists of a tab-separated list of properties including:

        1. The suggestion type (def)
        2. The type of the suggestion (skProc)
        3. The name of the module (xlib.XDefaultScreen)
        4. The name of the symbol (proc (para1: PDisplay): cint{.cdecl.})
        5. The path to the file containing the symbol (xlib.nim)
        6. The line number of the symbol (1536)
        7. The column number of the symbol (5)
        8. The documentation of the symbol (empty)
        9. The score of the suggestion (100)
    """

    suggestion_type: str
    suggestion_node_type: str
    module: str
    symbol: str
    file: Path
    line: int
    column: int
    documentation: str
    score: int

    @classmethod
    async def query(
        cls,
        file: str | Path,
        line: int | None = None,
        col: int | None = None,
        host: str = "localhost",
        port: int = 6000,
    ) -> AsyncIterable[NimDefinitionOutput]:
        async for line in query_nimsuggest("use", file, line, col, host, port):
            yield cls.from_line(line)

    @classmethod
    def from_line(cls, output: str) -> NimUseOutput:
        """Parse a nimsuggest output string into a NimSuggestionOutput."""
        (
            suggestion_type,
            suggestion_node_type,
            module,
            symbol,
            file,
            line,
            column,
            documentation,
            score,
        ) = output.split("\t")
        return cls(
            suggestion_type=suggestion_type,
            suggestion_node_type=suggestion_node_type,
            module=module,
            symbol=symbol,
            file=Path(file),
            line=int(line),
            column=int(column),
            documentation=documentation,
            score=int(score),
        )


class NimCheckOutput(NamedTuple):
    """A nimsuggest definition output.

    The output consists of a tab-separated list of properties including:

        1. The suggestion type (chk)
        2. The type of the suggestion (skUnknown)
        3. The name of the module (empty)
        4. The name of the symbol (Error)
        5. The path to the file containing the symbol (nim.cfg)
        6. The line number of the symbol (1)
        7. The column number of the symbol (0)
        8. The documentation of the symbol (undeclared identifier: 'os' candidates (edit distance, scope distance); see '--spellSuggest...)
        9. The score of the suggestion (0)
    """

    suggestion_type: str
    suggestion_node_type: str
    module: str
    symbol: str
    file: Path
    line: int
    column: int
    documentation: str
    score: int

    @classmethod
    async def query(
        cls,
        file: str | Path,
        line: int | None = None,
        col: int | None = None,
        host: str = "localhost",
        port: int = 6000,
    ) -> AsyncIterable[NimCheckOutput]:
        async for line in query_nimsuggest("chk", file, line, col, host, port):
            yield cls.from_line(line)

    @classmethod
    def from_line(cls, output: str) -> NimCheckOutput:
        """Parse a nimsuggest output string into a NimSuggestionOutput."""
        (
            suggestion_type,
            suggestion_node_type,
            module,
            symbol,
            file,
            line,
            column,
            documentation,
            score,
        ) = output.split("\t")
        return cls(
            suggestion_type=suggestion_type,
            suggestion_node_type=suggestion_node_type,
            module=module,
            symbol=symbol,
            file=Path(file),
            line=int(line),
            column=int(column),
            documentation=documentation,
            score=int(score),
        )


def get_event_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()


async def handle_nimsuggest(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Handle a nimsuggest command."""


if __name__ == "__main__":

    async def main() -> None:
        async for line in NimSuggestionOutput.query("wm_scratch_pad/scratchpad.nim"):
            print(line)
        async for line in NimCheckOutput.query("wm_scratch_pad/scratchpad.nim"):
            print(line)
        async for line in NimDefinitionOutput.query("wm_scratch_pad/scratchpad.nim:27:5"):
            print(line)
        async for line in NimUseOutput.query("wm_scratch_pad/scratchpad.nim:27:5"):
            print(line)

    asyncio.run(main())
