from typing import Dict, cast
from xml.etree import ElementTree


class ViewNode(Dict):
    pass


def parse_node(xml_node) -> ViewNode:
    attrib = xml_node.attrib

    node = ViewNode()
    node["index"] = int(attrib.get("index"))
    node["package"] = attrib.get("package")
    node["bounds"] = attrib.get("bounds")

    if attrib.get("class"):
        node["class"] = attrib.get("class")
    if attrib.get("text"):
        node["text"] = attrib.get("text")
    if attrib.get("resource-id"):
        node["resource-id"] = attrib.get("resource-id")
    if attrib.get("content-desc"):
        node["content-desc"] = attrib.get("content-desc")

    node_children = xml_node.findall("node")
    if node_children:
        node["children"] = []
        for child in node_children:
            if child.attrib.get("visible-to-user") == "true":
                node["children"].append(parse_node(child))

    return node


def parse_xml_to_tree(xml_path: str) -> list[ViewNode]:
    tree = ElementTree.ElementTree(ElementTree.fromstring(xml_path))
    root = cast(ElementTree.Element, tree.getroot())
    top_nodes = root.findall("node")
    result = [parse_node(node) for node in top_nodes]
    return result


def without_fields(
    nodes: list[ViewNode], fields: list[str] | None = None
) -> list[ViewNode]:
    result: list[ViewNode] = []
    for node in nodes:
        node_copy = node.copy()
        for field in fields or []:
            if node_copy.get(field):
                node_copy.pop(field)

        children = node_copy.get("children")
        if children:
            node_copy["children"] = without_fields(children, fields)

        result.append(ViewNode(node_copy))

    return result
