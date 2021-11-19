#!/usr/bin/env python
from nota.utils.parsing import Fragment, Pattern, parse, indentation
from nota.format.nd import structure
from nota.utils.tree import Node
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
            re.compile(r"(?P<indent>[ \t]*)(?P<type>(async[ ]+)?(for|while|if|elif|else))(?P<expr>[ ].*)?:[ \t]*\n", re.MULTILINE)),
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
text = """
pouet = 10
if a == 10:
    b = 20
elif a == 30:
    b = 40
else:
    b = 50
"""
root = Node("doc", dict(depth=0))
node = root
offset = 0
def node_find_parent( node:Node, source:str, start:int, end:int ) -> Node:
    text = source[start:end]
    indent = indentation(text) + 1
    print ("INDENT", indent, ":", repr(text), ":", node.getAttribute("depth"))
    while node.parent and (node.getAttribute("depth") >= indent or node.name == "cell"):
        print ("  shift", node.getAttribute("depth"))
        node = node.parent
    print ("   ==", node.getAttribute("depth"))
    return node


def node_append_text( node:Node, source:str, start:int, end:int ) -> Node:
    text = source[start:end]
    indent = indentation(text) + 1
    code = Node("code", dict(depth=indent))
    code.append(Node("#text", dict(start=start, end=end, value=text)))
    return node_find_parent(node, source, start, end).append(code)

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
        #div = Node("code", dict(depth=node.getAttribute("depth") + 1))
        # div.append(Node("#text", dict(start=s, end=e, value=text[s:e])))
        #node.append(div)
        node_append_text(node, text, s, e)

    # We create the new node with the given matched name
    cur = Node(name, dict(depth=indent))
    # We add it to the current node (scope)
    node.add(cur)
    node = cur
    if name == "cell":
        s = offset
        offset = e = match.fragment.end
        node_append_text(node, text, s, e)
    elif name == "struct":
        offset = match.fragment.start
    else:
        node.setAttribute("symbol", match.match.group("name"))
        offset = match.fragment.start
# We append the rest of the text
# TODO: We should find the proper parent based on the indentation
node_append_text(node, text, offset, len(text))

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
            div = Node("div", {"class":"symbol"}).add(Node("#text", dict(value=f"sym:{sym}")))
            res.add(div)
        for child in node.children:
            n = to_html(child)
            if n:
                res.append(n)
        if not res.children:
            res.add(Node("#text",dict(value="")))
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
print("*" * 80)



# EOF
