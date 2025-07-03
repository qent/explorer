from explorer.viewnode import parse_xml_to_tree

XML = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
    <node index='0' package='com.app' class='android.widget.LinearLayout' bounds='[0,0][100,100]' visible-to-user='true'>
        <node index='1' package='com.app' class='android.widget.TextView' text='Hello' resource-id='text1' bounds='[0,0][50,50]' visible-to-user='true'/>
        <node index='2' package='com.app' class='android.widget.Button' text='Go' resource-id='btn1' bounds='[50,50][100,100]' visible-to-user='false'/>
    </node>
</hierarchy>"""


def test_parse_xml_to_tree():
    tree = parse_xml_to_tree(XML)
    assert tree[0]["index"] == 0
    assert tree[0]["class"] == "android.widget.LinearLayout"
    children = tree[0]["children"]
    assert len(children) == 1
    child = children[0]
    assert child["index"] == 1
    assert child["text"] == "Hello"
    assert "resource-id" in child


def test_without_fields(monkeypatch):
    import explorer.viewnode as viewnode

    monkeypatch.setattr(viewnode, "ViewNode", dict)
    tree = parse_xml_to_tree(XML)
    cleaned = viewnode.without_fields(tree, ["bounds"])
    assert "bounds" not in cleaned[0]
    assert "bounds" not in cleaned[0]["children"][0]
