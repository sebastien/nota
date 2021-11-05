from nota.utils.parsing import Fragment, Pattern, parse, indentation
from nota.format.nd import structure, tree
from nota.utils.tree import Node
from typing import Optional
from pathlib import Path
import json
import re


# --
# We introduce pattern delimiters

patterns = {
        "cell" : Pattern(
            re.compile(r"(?P<indent>[ \t]*)(#[ ]*--[ \t]*(?P<header>[^\n]*)\n)(?P<body>[ \t]*#[^\n]*\n)*", re.MULTILINE)),
        "def": Pattern(
            re.compile(r"(?P<indent>[ \t]*)(?P<type>class|def)[ ]+(?P<name>[\w\d_]+)")),
        "assign": Pattern(
            re.compile(r"(?P<indent>[ \t]*)(?P<name>\w[^=\n]*)[ ]+=[^\n]+"))
 }


# --
# Creates the tree
#SOURCE = __file__.replace(".py", ".txt")
SOURCE = Path(__file__).parent / "python-embedded.py"
text = open(SOURCE).read()
root = Node("doc", dict(depth=0))
node = root
offset = 0
for name, match  in parse(patterns, text):
    indent = indentation(match.match.group("indent")) + 1
    while node.getAttribute("depth") >= indent or node.name == "cell":
        node = node.parent
    # Adds the text before
    if offset < match.fragment.start:
        s = offset
        offset = e = match.fragment.start
        div = node.append(Node("code", dict(depth=node.getAttribute("depth") + 1)))
        div.append(Node("#text", dict(start=s, end=e, value=text[s:e])))
    node = node.append(Node(name, dict(depth=indent)))
    if name == "cell":
        s = offset
        offset = e = match.fragment.end
        node.append(Node("#text", dict(start=s, end=e, value=text[s:e])))
    else:
        node.setAttribute("symbol", match.match.group("name"))
        offset = match.fragment.start
node.append(Node("#text", dict(value=text[offset:])))

print(root.toTDoc())

STYLE = """
.block{
margin: 5px 1px;
border-left: 32px solid #E0E0E0;
}


.cell {
background-color: yellow;
}

"""
def to_html( node:Node ) -> Node:
    res = node
    if (name := node.name) == "doc":
        res = html = Node("html")
        head = html.append(Node("head"))
        style = head.append(Node("style"))
        style.append(Node("#text", dict(value=STYLE)))
        scope = body = html.append(Node("body"))
    elif name == "#text":
        res = scope = Node("pre")
        res.append(Node("#text", {"value":node.getAttribute("value")}))
    elif name == "cell":
        res = scope = Node("div", {"class":"block cell"})
    else:
        res = scope = Node("div", {"class":"block", "data-name":node.getAttribute("symbol")})
    for child in node.children:
        scope.append(to_html(child))
    return res

with open("pouet.html", "wt") as f:
    f.write(to_html(root).toXML())
with open("pouet.json", "wt") as f:
    f.write(json.dumps(root.asDict()))

print(to_html(root).toTDoc())



# EOF
