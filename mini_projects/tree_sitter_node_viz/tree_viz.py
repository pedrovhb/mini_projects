import asyncio
from pathlib import Path

from asynkets import Switch
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Grid
from textual.design import ColorSystem
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Tree,
    Static,
    TreeNode,
    Header,
    Footer,
    Button,
    ListView,
    ListItem,
    Placeholder,
    Label,
)

from mini_projects.tree_sitter_node_viz.base import Language
from mini_projects.tree_sitter_node_viz.tree_parse import (
    TreeSitterType,
    TreeSitterField,
    create_types_and_fields,
)

DEFAULT_COLORS = {
    "dark": ColorSystem(
        primary="#252F5F",
        secondary="#1C5D48",
        warning="#C47E22",
        error="#891316",
        success="#638227",
        accent="#C46B22",
        dark=True,
    ),
}


def add_tree_node(
    tree_node: TreeNode[TreeSitterType | TreeSitterField],
    node: TreeSitterType,
    expand: bool = False,
    allow_expand: bool = True,
) -> TreeNode:

    tree = tree_node.add(
        f"[bold blue]{node.name}[/]",
        node,
        expand=expand,
        allow_expand=allow_expand,
    )
    color_named = "green" if node.named else "red"
    tree.add_leaf(f"[bold green]named[/]: [{color_named}]{node.named}[/]", node)

    if node.fields:
        fields_tree = tree.add(
            f"[bold green]fields[/]:", node, expand=expand, allow_expand=allow_expand
        )
        for field_name, field_data in node.rich_fields().items():
            fields_tree.add_leaf(
                f"[bold yellow]{field_name}[/]: {field_data}",
                node.fields[field_name],
            )

    if node.children:

        multiple_indicator = "[bold orange1]*[/]" if node.children.multiple else ""
        optional_indicator = "[bold orange1]?[/]" if not node.children.required else ""
        children_label = f"{multiple_indicator}[bold green]children[/]{optional_indicator}:"
        children_tree = tree.add(
            children_label,
            node.children,
            expand=expand,
            allow_expand=allow_expand,
        )

        for i, (child_name, child_data) in enumerate(node.rich_children().items()):
            children_tree.add_leaf(
                f"[bold yellow]{child_name}[/]: {child_data}",
                node.children.types[i],
            )

    return tree


def nodes_textual_tree(nodes: list[TreeSitterType], language: Language) -> Tree:
    """Print a tree of the nodes in a rich format."""

    node_tree = Tree(f"Tree Sitter Nodes: [bold]{language.name}[/]")
    root_node = node_tree.root
    root_node.expand()

    for node in nodes:
        add_tree_node(root_node, node)

    return node_tree


def expand_recursively(node: TreeNode) -> None:
    node.expand()
    for child in node.children:
        expand_recursively(child)


def collapse_recursively(node: TreeNode) -> None:
    node.collapse()
    for child in node.children:
        collapse_recursively(child)


class LanguageSelectView(Screen):

    language = reactive[Language | None](None)

    def on_mount(self, event: events.Mount) -> None:
        self.update(self._get_language_display(self.language))

    def watch_language(self, language: Language | None) -> None:
        self.update(self._get_language_display(language))

    def _get_language_display(self, language: Language | None) -> str:
        if language:
            return f"Language: {language.name}"
        else:
            return "None"


class Sidebar(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lv = ListView(
            *(ListItem(Label(lang), name=lang, classes="language_item") for lang in Language),
            id="language_list",
        )

    def compose(self) -> ComposeResult:
        yield Static("Languages", classes="sidebar_header")
        yield self._lv
        self._lv.focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self.app.highlighted_language = Language(event.item.name)
        self.log("highlighted", event.item.name)
        self._lv.scroll_to_widget(event.item)
        print(event.item.visible)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.app.selected_language = Language(event.item.name)
        self.log("selected", event.item.name)


class SelectedNodeInfo(Static):

    data: reactive[TreeSitterType | TreeSitterField | None] = None

    def watch_data(self):
        if isinstance(self.data, TreeSitterType):
            node_types = [t for t in self.data.fields.keys()]
            node_types = "\n  - ".join(node_types)
            self.log.debug(f"Selected node. Possible types: \n - {node_types}")
            self.selected_node_info.selected_node = self.data

            tree = self.selected_node_info
            tree.clear()
            add_tree_node(tree.root, self.data, expand=True)

        elif isinstance(self.data, TreeSitterField):
            node_types = [t.name for t in self.data.types]
            node_types = "\n  - ".join(node_types)
            self.log.debug(f"Selected node. Possible types: \n - {node_types}")
            self.selected_node_info.selected_node = self.data

            tree = self.selected_node_info
            tree.clear()
            tree.root.add_leaf(f"[bold green]multiple[/]: {self.data.multiple}")
            tree.root.add_leaf(f"[bold green]required[/]: {self.data.required}")
            node_types = tree.root.add(f"[bold green]types[/]", expand=True)
            for type_ in self.data.types:
                add_tree_node(node_types, type_, expand=True)

    def compose(self) -> ComposeResult:
        yield Static("Selected Node Info", classes="sidebar_header")
        yield (
            Tree(
                "Selected Node Info",
                classes="selected_node_info",
            )
        )


class TreeVizApp(App):

    CSS_PATH = Path(__file__).parent / "tree_viz.css"

    selected_language = reactive[Language](Language.python)

    BINDINGS = [
        Binding(key="q", action="quit()", description="Quit"),
        Binding(key="e", action="expand_collapse()", description="Expand/collapse nodes"),
        Binding(key="t", action="toggle_sidebar()", description="Toggle language panel"),
    ]

    sidebar_dock_anim_duration = 0.3

    def __init__(self, language: Language):
        super().__init__()
        self._sidebar = Sidebar(id="sidebar", name="sidebar")
        self._sidebar.visible = True
        self._node_tree_expanded = False
        self.node_tree = self._build_tree(language)
        self.selected_node_info = Tree[TreeSitterType | TreeSitterField]("Selected Node Info")
        self.selected_node_info.auto_expand = True

    async def show_sidebar(self) -> None:
        self._sidebar.can_focus = True
        self._sidebar.visible = True
        self._sidebar.query_one("#language_list").focus()
        self._sidebar.styles.animate(
            "width",
            30,
            duration=self.sidebar_dock_anim_duration,
            easing="in_out_quint",
        )

    async def hide_sidebar(self) -> None:
        self._sidebar.can_focus = False

        def on_complete():
            self._sidebar.visible = False
            self.node_tree.focus()

        self._sidebar.styles.animate(
            "width",
            "0",
            duration=self.sidebar_dock_anim_duration,
            easing="in_out_quint",
            on_complete=on_complete,
        )

    async def action_toggle_sidebar(self) -> None:
        if self._sidebar.visible:
            await self.hide_sidebar()
        else:
            await self.show_sidebar()

    def action_expand_collapse(self) -> None:
        if self._node_tree_expanded:
            for child in self.node_tree.root.children:
                collapse_recursively(child)
        else:
            expand_recursively(self.node_tree.root)
        self._node_tree_expanded = not self._node_tree_expanded

    def _build_tree(self, language: Language) -> Tree:
        types = create_types_and_fields(language.node_types_dict)
        new_node_tree = nodes_textual_tree(list(types.values()), language)
        expand_recursively(new_node_tree.root)
        return new_node_tree

    def watch_selected_language(self, language: Language) -> None:
        self.log("selected language", language)

        self.selected_node_info.clear()
        new_node_tree = self._build_tree(language)

        self._node_tree_expanded = True

        self.mount(new_node_tree, after=self.node_tree)
        self.node_tree.remove()
        self.node_tree = new_node_tree

    async def on_mount(self) -> None:
        await self.show_sidebar()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data: TreeSitterType = event.node.data
        if isinstance(data, TreeSitterType):
            node_types = [t for t in data.fields.keys()]
            node_types = "\n  - ".join(node_types)
            self.log.debug(f"Selected node. Possible types: \n - {node_types}")
            self.selected_node_info.selected_node = data

            tree = self.selected_node_info
            tree.clear()
            add_tree_node(tree.root, data, expand=True)

        elif isinstance(data, TreeSitterField):
            node_types = [t.name for t in data.types]
            node_types = "\n  - ".join(node_types)
            self.log.debug(f"Selected node. Possible types: \n - {node_types}")
            self.selected_node_info.selected_node = data

            tree = self.selected_node_info
            tree.clear()
            tree.root.add_leaf(f"[bold green]multiple[/]: {data.multiple}")
            tree.root.add_leaf(f"[bold green]required[/]: {data.required}")
            node_types = tree.root.add(f"[bold green]types[/]", expand=True)
            for type_ in data.types:
                add_tree_node(node_types, type_, expand=True)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, name="Tree Sitter Node Viz")
        yield Container(
            self._sidebar,
            Container(
                Container(self.node_tree, name="tree", id="node_tree"),
                Container(
                    self.selected_node_info, name="selected_node_info", id="selected_node_info"
                ),
                id="main_container",
            ),
        )
        yield Footer()

    @property
    def design(self):
        return DEFAULT_COLORS

    # Setter ignores the value
    @design.setter
    def design(self, value):
        pass


if __name__ in ("__main__", "<run_path>"):

    ts = create_types_and_fields(Language.css.node_types_dict)

    app = TreeVizApp(Language.python)
    app.design = DEFAULT_COLORS
    app.run()
else:
    print(f"Name is {__name__}")
