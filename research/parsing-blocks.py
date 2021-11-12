#!/usr/bin/env python
from nota.utils.parsing import Fragment, Pattern, parse, indentation
from nota.format.nd import structure, tree
from nota.utils.tree import Node
from typing import Optional
from pathlib import Path
import json
import re

# --
# # Block Parsing Example
#
# This example is about parsing blocks of texts (`#--` delimited comment blocks) as
# well as definitions and assignments, and generating a tree-like representation
# out of it. In other words, it's a (crude) way to extra the structure of Python-like
# code.


# --
# We introduce pattern delimiters, we extract cells, symbol definitions,
# assignments, comments and lines.

patterns = {
        "cell" : Pattern(
            re.compile(r"(?P<indent>[ \t]*)(#[ ]*--[ \t]*(?P<header>[^\n]*)\n)(?P<body>[ \t]*#[^\n]*\n)*", re.MULTILINE)),
        "def": Pattern(
            re.compile(r"(?P<indent>[ \t]*)(?P<type>class|def)[ ]+(?P<name>[\w\d_]+)")),
        "struct": Pattern(
            re.compile(r"(?P<indent>[ \t]*)(?P<type>(async[ ]+)for|while|if|elif|else)(?P<expr>[ ][.*]+)?:[ \t]*\n")),
        "assign": Pattern(
            re.compile(r"(?P<indent>[ \t]*)(?P<name>\w[^=\n]*)[ ]+=[^\n]+")),
        # "comment": Pattern(
        #     re.compile(r"(?P<indent>[ \t]*)#[^\n]*\n")),
        # "line": Pattern(
        #     re.compile(r"(?P<indent>[ \t]*)[^\n]+\n")),
 }


# --
# We create the document tree by parsing the patterns.

SOURCE = Path(__file__)
text = open(SOURCE).read()
root = Node("doc", dict(depth=0))
node = root
offset = 0
for name, match  in parse(patterns, text):
    indent = indentation(match.match.group("indent")) + 1
    while node.getAttribute("depth") >= indent or node.name == "cell":
        node = node.parent
    # if name == "comment":
    #     continue
    # elif name == "line":
    #     continue
    # Adds the text before
    if offset < match.fragment.start:
        s = offset
        offset = e = match.fragment.start
        div = node.append(Node("code", dict(depth=node.getAttribute("depth") + 1)))
        div.append(Node("#text", dict(start=s, end=e, value=text[s:e])))
    cur = Node(name, dict(depth=indent))
    node.add(cur)
    node = cur
    if name == "cell":
        s = offset
        offset = e = match.fragment.end
        node.append(Node("#text", dict(start=s, end=e, value=text[s:e])))
    elif name == "struct":
        offset = match.fragment.start
    else:
        node.setAttribute("symbol", match.match.group("name"))
        offset = match.fragment.start
node.append(Node("#text", dict(value=text[offset:])))

# --
# ## HTML Conversion
STYLE = """


pre {
border: 1px solid #E0E0E0;
}

.block {
margin: 5px;
border-left: 10px solid #E0E0E0;
}

.cell {
background-color: yellow;
}

"""
def to_html( node:Node ) -> Node:
    if node.name == "#text":
        return Node("pre").add(Node("#text", dict(value=node.getAttribute("value"))))
    else:
        res = Node("div", {"class":f"block {node.name}"})
        sym = node.getAttribute("symbol")
        if sym:
            res.add(Node("div", {"class":"symbol"}).add(Node("#text", dict(value=f"sym:{sym}"))))
        for child in node.children:
            n = to_html(child)
            if n:
                res.append(n)
        if  node.name == "doc":
            return Node("html").add(
                Node("head").add(
                    Node("style").add(
                         Node("#text", dict(value=STYLE))))
            ).add(
                Node("body").add(res))
        else:
            return res

with open("pouet.html", "wt") as f:
    f.write(to_html(root).toHTML())
with open("pouet.json", "wt") as f:
    f.write(json.dumps(root.asDict()))

print(root.toTDoc())



# EOF
