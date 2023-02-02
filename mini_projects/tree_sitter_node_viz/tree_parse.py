from __future__ import annotations

from dataclasses import field, dataclass

from rich.console import Console
from rich.tree import Tree

from mini_projects.tree_sitter_node_viz.base import Language, NodeTypesDict


@dataclass
class TreeSitterType:

    name: str
    named: bool
    fields: dict[str, TreeSitterField] = field(default_factory=dict)
    children: TreeSitterField | None = None

    def __str__(self):
        return f"TreeSitterType({self.name})"

    def __rich__(self):
        return f"TreeSitterType([bold yellow]{self.name}[/])"

    def rich_fields(self) -> dict[str, str]:
        d = {}
        for field_name, field_data in self.fields.items():
            multiple_indicator = "[bold orange1]*[/]" if field_data.multiple else ""
            optional_indicator = "[bold orange1]?[/]" if not field_data.required else ""
            d[field_name] = f"{multiple_indicator}[bold blue]{field_name}[/]{optional_indicator}"
        return d

    def rich_children(self) -> dict[str, str]:
        d = {}
        if self.children:
            for child_type in self.children.types:
                named_indicator = "[green]True[/]" if child_type.named else "[red]False[/]"
                named_indicator = f"(named: {named_indicator})"

                d[child_type.name] = f"[bold blue]{child_type.name}[/] {named_indicator}"
        return d


@dataclass
class TreeSitterField:

    multiple: bool
    required: bool
    types: list[TreeSitterType]

    def __str__(self):
        return f"{'*' if self.multiple else ''}{'?' if not self.required else ''}{self.types}"


def create_types_and_fields(data: list[NodeTypesDict]):

    types = {
        type_data["type"]: TreeSitterType(name=type_data["type"], named=type_data["named"])
        for type_data in data
    }

    for type_data in data:
        fields = type_data.get("fields")
        children = type_data.get("children")

        if fields:

            for field_name, field_data in fields.items():
                field_ = TreeSitterField(
                    multiple=field_data["multiple"],
                    required=field_data["required"],
                    types=[types[t["type"]] for t in field_data["types"] if t["type"] in types],
                )
                types[type_data["type"]].fields[field_name] = field_

        if children:
            types[type_data["type"]].children = TreeSitterField(
                multiple=children["multiple"],
                required=children["required"],
                types=[types[t["type"]] for t in children["types"]],
            )

    return types


def nodes_rich_tree(node: TreeSitterType) -> Tree:
    """Print a tree of the nodes in a rich format."""
    tree = Tree(f"[bold blue]{node.name}[/]")
    color_named = "green" if node.named else "red"
    tree.add(f"[bold green]named[/]: [{color_named}]{node.named}[/]")

    if node.fields:
        fields_tree = tree.add(f"[bold green]fields[/]:")
        for field_name, field_data in node.rich_fields().items():
            fields_tree.add(f"[bold yellow]{field_name}[/]: {field_data}")

    if node.children:

        multiple_indicator = "[bold orange1]*[/]" if node.children.multiple else ""
        optional_indicator = "[bold orange1]?[/]" if not node.children.required else ""
        children_label = f"{multiple_indicator}[bold green]children[/]{optional_indicator}:"
        children_tree = tree.add(children_label)

        for child_name, child_data in node.rich_children().items():

            children_tree.add(f"[bold yellow]{child_name}[/]: {child_data}")

    return tree


def main():
    ts = create_types_and_fields(Language.python.node_types_dict)

    root = Tree("[bold]TreeSitter Nodes[/]")
    for type_ in ts.values():
        root.add(nodes_rich_tree(type_))
    console.print(root)


if __name__ == "__main__":
    console = Console()
    main()
