"""Utilities for parsing Android view hierarchies."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from xml.etree import ElementTree


@dataclass(slots=True)
class ViewNode:
    """Representation of a single node in the UI hierarchy."""

    index: int | None = None
    package: str | None = None
    bounds: str | None = None
    class_name: str | None = None
    text: str | None = None
    resource_id: str | None = None
    content_desc: str | None = None
    children: list["ViewNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the node without ``None`` values."""

        node_dict = asdict(self)
        node_dict["class"] = node_dict.pop("class_name")
        node_dict["resource-id"] = node_dict.pop("resource_id")
        node_dict["content-desc"] = node_dict.pop("content_desc")
        node_dict["children"] = [child.to_dict() for child in self.children]
        return {k: v for k, v in node_dict.items() if v not in (None, [], {})}


def parse_node(xml_node: ElementTree.Element) -> ViewNode:
    """Recursively parse ``xml_node`` into :class:`ViewNode` objects."""

    attrib = xml_node.attrib
    children = [
        parse_node(child)
        for child in xml_node.findall("node")
        if child.attrib.get("visible-to-user") == "true"
    ]
    return ViewNode(
        index=int(attrib["index"]) if attrib.get("index") else None,
        package=attrib.get("package"),
        bounds=attrib.get("bounds"),
        class_name=attrib.get("class"),
        text=attrib.get("text"),
        resource_id=attrib.get("resource-id"),
        content_desc=attrib.get("content-desc"),
        children=children,
    )


def parse_xml_to_tree(xml_path: str) -> list[ViewNode]:
    """Parse ``xml_path`` hierarchy string into a list of :class:`ViewNode` objects."""

    root = ElementTree.fromstring(xml_path)
    return [parse_node(node) for node in root.findall("node")]


def without_fields(
    nodes: list[ViewNode], fields: list[str] | None = None
) -> list[ViewNode]:
    """Return a copy of ``nodes`` with selected fields removed."""

    fields_set = set(fields or [])
    result: list[ViewNode] = []
    for node in nodes:
        result.append(
            ViewNode(
                index=node.index,
                package=node.package,
                bounds=None if "bounds" in fields_set else node.bounds,
                class_name=None if "class" in fields_set else node.class_name,
                text=None if "text" in fields_set else node.text,
                resource_id=None if "resource-id" in fields_set else node.resource_id,
                content_desc=(
                    None if "content-desc" in fields_set else node.content_desc
                ),
                children=without_fields(node.children, fields) if node.children else [],
            )
        )

    return result
