from nota.utils.parsing import Fragment, Pattern, parse, indentation
from nota.format.nd import structure, tree
from nota.utils.tree import Node
from typing import Optional
import json
import re


# --
# We introduce pattern delimiters

patterns = {
        "cell" : Pattern(
            re.compile(r"(?P<indent>[ \t]*)(#[ ]*--[ \t]*(?P<header>[^\n]*)\n)(?P<body>[ \t]*#[^\n]*\n)*", re.MULTILINE)),
        # "def": Pattern(
        #     re.compile(r"(?P<indent>[ \t]*)(?P<type>class|def)[ ]+(?P<name>[^ \t\n]+)")),
        "assign": Pattern(
            re.compile(r"(?P<indent>[ \t]*)(?P<lhs>\w[^=\n]*)[ ]+=[^\n]+"))
 }


# --
# Creates the tree
text = open(__file__.replace(".py", ".txt")).read()
root = Node("doc", dict(depth=0))
fragment:Optional[Fragment] = None
node = root
for name, match  in parse(patterns, text):
    indent = indentation(match.match.group("indent")) + 1
    print (name, match)
    continue
    while node.getAttribute("depth") >= indent:
        node = node.parent
    if not fragment or fragment.end < match.fragment.start:
        s = fragment.end if fragment else 0
        e = match.fragment.start
        node.append(Node("#text", dict(start=s, end=e, value=text[s:e])))
    node = node.append(Node(name, dict(depth=indent)))
    s = match.fragment.start
    e = match.fragment.end
    node.append(Node("#text", dict(start=s, end=e, value=text[s:e])))
    fragment = match.fragment

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
        res = scope = Node("div", {"class":"block"})
    for child in node.children:
        scope.append(to_html(child))
    return res
# print(to_html(root).toXML())



# EOF
