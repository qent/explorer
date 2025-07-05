from explorer.viewnode import parse_xml_to_tree, without_fields

# mypy: ignore-errors

XML = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
    <node index='0' package='com.app' class='android.widget.LinearLayout' bounds='[0,0][100,100]' visible-to-user='true'>
        <node index='1' package='com.app' class='android.widget.TextView' text='Hello' resource-id='text1' bounds='[0,0][50,50]' visible-to-user='true'/>
        <node index='2' package='com.app' class='android.widget.Button' text='Go' resource-id='btn1' bounds='[50,50][100,100]' visible-to-user='false'/>
    </node>
</hierarchy>"""


def test_parse_xml_to_tree() -> None:
    tree = parse_xml_to_tree(XML)
    root = tree[0]
    assert root.index == 0
    assert root.class_name == "android.widget.LinearLayout"
    children = root.children
    assert len(children) == 1
    child = children[0]
    assert child.index == 1
    assert child.text == "Hello"
    assert child.resource_id is not None


def test_without_fields() -> None:
    tree = parse_xml_to_tree(XML)
    cleaned = without_fields(tree, ["bounds"])
    assert cleaned[0].bounds is None
    assert cleaned[0].children[0].bounds is None
