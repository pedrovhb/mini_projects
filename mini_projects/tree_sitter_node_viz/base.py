from __future__ import annotations

import asyncio
import json
from enum import Enum
from pathlib import Path
from typing import TypeAlias, Union

import httpx
from loguru import logger

client = httpx.AsyncClient()
BASE_URL = "https://raw.githubusercontent.com/"

NodeTypesDict: TypeAlias = dict[str, Union[str, bool, "NodeTypesDict"]]


class Language(str, Enum):
    agda = "agda"
    bash = "bash"
    c = "c"
    c_sharp = "c_sharp"
    cpp = "cpp"
    css = "css"
    go = "go"
    # haskell = "haskell"
    html = "html"
    java = "java"
    javascript = "javascript"
    jsdoc = "jsdoc"
    json = "json"
    julia = "julia"
    ocaml = "ocaml"
    ocaml_interface = "ocaml_interface"
    php = "php"
    python = "python"
    ql = "ql"
    ql_dbscheme = "ql_dbscheme"
    regex = "regex"
    ruby = "ruby"
    rust = "rust"
    # t = "scala"
    # swift = "swift"
    toml = "toml"
    tsq = "tsq"
    typescript = "typescript"
    tsx = "tsx"
    # verilog = "verilog"

    def __str__(self) -> str:
        return self.value

    @property
    def node_types_json_path(self) -> Path:
        return Path(__file__).parent / "node_json" / f"node_types_{self.value}.json"

    @property
    def node_types_dict(self) -> list[NodeTypesDict]:
        return json.loads(self.node_types_json_path.read_text())


LANGUAGE_ROUTES = {
    Language.agda: "/tree-sitter/tree-sitter-agda/master/src/node-types.json",
    Language.bash: "/tree-sitter/tree-sitter-bash/master/src/node-types.json",
    Language.c: "/tree-sitter/tree-sitter-c/master/src/node-types.json",
    Language.c_sharp: "/tree-sitter/tree-sitter-c-sharp/master/src/node-types.json",
    Language.cpp: "/tree-sitter/tree-sitter-cpp/master/src/node-types.json",
    Language.css: "/tree-sitter/tree-sitter-css/master/src/node-types.json",
    Language.go: "/tree-sitter/tree-sitter-go/master/src/node-types.json",
    # Language.haskell: "/tree-sitter/tree-sitter-haskell/master/src/node-types.json",
    Language.html: "/tree-sitter/tree-sitter-html/master/src/node-types.json",
    Language.java: "/tree-sitter/tree-sitter-java/master/src/node-types.json",
    Language.javascript: "/tree-sitter/tree-sitter-javascript/master/src/node-types.json",
    Language.jsdoc: "/tree-sitter/tree-sitter-jsdoc/master/src/node-types.json",
    Language.json: "/tree-sitter/tree-sitter-json/master/src/node-types.json",
    Language.julia: "/tree-sitter/tree-sitter-julia/master/src/node-types.json",
    Language.ocaml: "/tree-sitter/tree-sitter-ocaml/master/ocaml/src/node-types.json",
    Language.ocaml_interface: "/tree-sitter/tree-sitter-ocaml/master/interface/src/node-types.json",
    Language.php: "/tree-sitter/tree-sitter-php/master/src/node-types.json",
    Language.python: "/tree-sitter/tree-sitter-python/master/src/node-types.json",
    Language.ql: "/tree-sitter/tree-sitter-ql/master/src/node-types.json",
    Language.ql_dbscheme: "/tree-sitter/tree-sitter-ql-dbscheme/master/src/node-types.json",
    Language.regex: "/tree-sitter/tree-sitter-regex/master/src/node-types.json",
    Language.ruby: "/tree-sitter/tree-sitter-ruby/master/src/node-types.json",
    Language.rust: "/tree-sitter/tree-sitter-rust/master/src/node-types.json",
    # Language.scala: "/tree-sitter/tree-sitter-scala/master/src/node-types.json",
    # Language.swift: "/tree-sitter/tree-sitter-swift/master/src/node-types.json",
    Language.toml: "/tree-sitter/tree-sitter-toml/master/src/node-types.json",
    Language.tsq: "/tree-sitter/tree-sitter-tsq/master/src/node-types.json",
    Language.tsx: "/tree-sitter/tree-sitter-typescript/master/tsx/src/node-types.json",
    Language.typescript: "/tree-sitter/tree-sitter-typescript/master/typescript/src/node-types.json",
    # Language.verilog: "/tree-sitter/tree-sitter-verilog/master/src/node-types.json",
}
# Commented out languages are crashing the program for some
# reason (likely because e.g. Haskell is enormous)


async def _update_node_json_file(language: Language, client: httpx.AsyncClient) -> None:
    """Get language from tree-sitter."""
    logger.info(f"Getting {language} node-types.json")
    url = BASE_URL + LANGUAGE_ROUTES[language]
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    response = await response.aread()
    logger.info(f"Got {language} node-types.json - {len(response)} bytes")
    language.node_types_json_path.write_bytes(response)
    logger.info(f"Updated node_types_{language}.json")


async def update_node_json_files() -> None:
    """Update node.json files for all languages in tree-sitter."""
    logger.info("Updating node_types json files")
    tasks = [_update_node_json_file(language, client) for language in LANGUAGE_ROUTES]
    await asyncio.gather(*tasks)
    logger.success("Updated node_types json files!")


if __name__ == "__main__":
    asyncio.run(update_node_json_files())
