#!/usr/bin/env python
from nota.utils.parsing import Fragment, Pattern, parse, indentation
from nota.format.nd import structure
from nota.utils.tree import Node
from pathlib import Path
from typing import Iterable, Optional, NamedTuple
import re
import json

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


class Chunk(NamedTuple):
    name:str
    indent:int
    text:str

def make_chunk( name:str, text:str, indent:Optional[int]=None ) -> Chunk:
    return Chunk(name, indentation(text) if indent is None else indent, text)

def parse_chunks( text:str ) -> Iterable[Chunk]:
    offset = 0
    for name, match  in parse(patterns, text):
        yield make_chunk("#text", text[offset:match.fragment.start])
        # NOTE: assignments and structures have no content, they're just markers, so
        # their end is going to be the same as their start.
        end = match.fragment.end if name in ("cell","struct") else match.fragment.start
        yield make_chunk(name, text[match.fragment.start:end], indent=indentation(text[match.fragment.start:match.fragment.end]))
        offset = end
    yield make_chunk("#text", text[offset:])

def node_parent( node:Node, depth:int ) -> Node:
    while node and node.parent and (not node.hasAttribute("depth") or node.getAttribute("depth") >= depth):
        node = node.parent
    return node

def text_node(text:str):
    return Node("#text" ,dict(value=text))

RE_EMPTY = re.compile(r"^\s*$")

def make_tree( chunks:Iterable[Chunk] ) -> Node:
    root = node = Node("doc", dict(depth=-1))
    for chunk in chunks:
        if chunk.name == "#text":
            node_parent(node, indentation(chunk.text) + 1).append(text_node(chunk.text))
        else:
            new = Node(chunk.name, dict(depth=chunk.indent))
            if chunk.text:
                new.append(Node("#text", dict(value=chunk.text)))
            node_parent(node, chunk.indent).append(new)
            node = new
    return root

# --
SOURCE = Path(__file__)
text = open(SOURCE).read()
XXXtext = """
def parse_chunks( text:str ) -> Iterable[Chunk]:
    offset = 0
    for name, match  in parse(patterns, text):
        yield make_chunk("#text", text[offset:match.fragment.start])
        end = match.fragment.end if name in ("cell",) else match.fragment.start
        yield make_chunk(name, text[match.fragment.start:end], indent=indentation(text[match.fragment.start:match.fragment.end]))
"""
for chunk in enumerate(parse_chunks(text)):
    print(chunk)
print("-" * 50)
doc = make_tree(parse_chunks(text))


# --
# ## HTML Conversion
STYLE = """


.block--def, .block--struct {
margin: 5px;
border: 1px solid #F0F0F0;
border-left: 10px solid #E0E0E0;
}


.tag {
display:block;
background: yellow;
font-size: 9px;
font-family: monospace;

}


.cell {
background-color: yellow;
}
"""

def to_html( node:Node ) -> Node:
    if node.name == "#text":
        return Node("pre").add(Node("#text", dict(value=node.getAttribute("value"))))
    else:
        res = Node("div", {"class":f"block block--{node.name}"}).add(
            Node("span", {"class":f"tag tag--{node.name}"}).add(
                text_node(node.name)
            )
        )

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
    f.write(to_html(doc).toHTML())
with open("pouet.json", "wt") as f:
    f.write(json.dumps(doc.asDict()))

print("-" * 80)
print(doc.toTDoc())
print("-" * 80)
print(to_html(doc).toTDoc())
print("*" * 80)



# EOF
