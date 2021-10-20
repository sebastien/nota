import re
from ..utils.tree import Node, toSExpr
from ..utils import parsing
from dataclasses import dataclass
from typing import Iterable, Optional, cast
from ..model import ReferenceType, Reference


def inline(expr: str, multiline=True):
    return parsing.Pattern(re.compile(expr, re.MULTILINE if multiline else 0))


def block(expr: str, open=True, multiline=False):
    return parsing.Pattern(re.compile(expr, re.MULTILINE if multiline else 0), type="open" if open else "closed")


def closedblock(expr: str, multiline=False):
    return block(expr, open=False, multiline=multiline)


def node(name: str, content: Optional[list[str]] = None):
    res = Node(name)
    for t in (content or ()):
        res.append(text(t))
    return res


def text(content: str):
    res = Node("#text")
    res.data = content
    return res


# NOTE: Leaving this there for now, as I'm not sure if we'll go down that route.
# class TreeBuilder:
#
#     def __init__(self):
#         self.root = node("document")
#         self.stack = [self.root]
#
#     @property
#     def current(self) -> Node:
#         return self.stack[-1]
#
#     def process(self, name: str, match: Match):
#         prefix_variant = name.split(":", 1)
#         prefix = prefix_variant[0]
#         key = f"on_{prefix}"
#         if hasattr(self, key):
#             getattr(self, key)(name, match)
#         else:
#             self.on_default(name, match)
#
#     def on_default(self, name: str, match: Match):
#         print(name, match)
#         pass
#
#     def push(self, node: Node) -> Node:
#         self.current.append(node)
#         return node
#
#     def pop(self, name: Optional[str] = None) -> Optional[Node]:
#         if not name:
#             return self.pop() if len(self.stack) > 1 else None
#         else:
#             while len(self.stack) > 1 and self.current != name:
#                 self.stack.pop()
#             return self.current if self.current.name == name else None
#
#
# class DocumentTreeBuilder(TreeBuilder):
#
#     SCHEMA = {
#         "heading": ["inline"],
#         "list-item": ["inline"],
#         "list": ["list-item"],
#         "p": ["inline"],
#
#     }
#
#     def on_heading(self, name: str, match: Match):
#         self.push(node("heading"))
#
#     def on_list_item(self, name: str, match: Match):
#         if self.current.name == "list-item":
#             self.pop().push(node("list-item"))
#         else:
#             self.push(node("list")).push(node("list-item"))
#
#
# def build(matches: Iterable[tuple[str, Match]]):
#     builder = DocumentTreeBuilder()
#     for name, match in matches:
#         builder.process(name, match)
#     return builder.root


REFERENCES = {
    ReferenceType.Term: inline(r"_(?P<content>[^_]+)_"),
    ReferenceType.Tag: inline(r"#(?P<name>[\w\-_]+)"),
    ReferenceType.Link: inline(r"\[?P<name>[\w\-_]+\](\((?P<target>[^\)]+)\))"),
    ReferenceType.Date: inline(r"\d\d\d\d\-[01]\d\-[0123]\d"),
    ReferenceType.Time: inline(r"[012]\d:[012345]\d:[012345]\d"),
    ReferenceType.URL: inline(r"<(?P<value>[a-z+]+://[^>]+)>"),
}

STRUCTURE = {
    "heading:prefixed": closedblock(r"(?P<depth>#+)\s+(?P<content>.+)\n", multiline=True),
    "heading:suffixed": closedblock(r"(?P<content>.+)\n(?P<underline>(===+|\-\-\-+))\n", multiline=True),
    "list-item:numeric": block(r"^(?P<depth>\s*)\d\)\s+"),
    "list-item:alpha": block(r"^(?P<depth>\s*)\[a-z]\)\s+"),
    "list-item:bullet": block(r"^(?P<depth>\s*)\-\s+"),
    "paragraph": block(r"\n+"),
    "code": block(r"^```"),
    "block": block(r"^\-\-"),
}


def indentation(line: str, tabsize=4) -> int:
    """Returns the indentation level of the given `line`, expanding tabs
    to spaces."""
    indent = 0
    for c in line:
        if c == ' ':
            indent += 1
        elif c == '\t':
            indent += tabsize - (indent % tabsize)
        else:
            break
    return indent


@dataclass
class Block:
    name: Optional[str]
    indentation: int
    content: list[str]


def references(text: str) -> list[Block]:
    res = []
    for reftype, delimiter in cast(Iterable[tuple[ReferenceType, parsing.Match]], parsing.parse(REFERENCES, text)):
        res.append(Reference(reftype, delimiter.match.group()))
    return res


def structure(text: str, patterns: dict[str, parsing.Pattern] = STRUCTURE) -> list[Block]:
    """Parses the given text using the given patterns, and returns the list of
    recognized blocks. The patterns are used as delimiters."""
    offset = 0
    block: Optional[Block] = None
    blocks: list[Block] = []
    for name, delimiter in parsing.parse(patterns, text):
        before = text[offset:delimiter.fragment.start]
        if not before:
            pass
        elif not block:
            blocks.append(Block(None, indentation(before), [before]))
        else:
            if block.indentation == -1:
                block.indentation = indentation(before)
            block.content.append(before)
        try:
            content = delimiter.match.group("content")
            block = Block(name, indentation(content), [content])
        except IndexError:
            block = Block(name, -1, [])
        blocks.append(block)
        offset = delimiter.fragment.end
    return blocks


def tree(blocks: list[Block]) -> Node:
    """Takes the list of blocks returned by `structure` and folds them into
    a tree."""
    stack: list[tuple[Block, Node]] = []
    root = node("document")
    for block in blocks:
        block_node = node(block.name or "paragraph", block.content)
        while stack and stack[-1][0].indentation >= block.indentation:
            stack.pop()
        if not stack:
            root.append(block_node)
        else:
            stack[-1][1].append(block_node)
        stack.append((block, block_node))
    return root


def parse(text: str) -> Node:
    return tree(structure(text))


# with open("/home/sebastien/.nota/tools/git.nd", "rt") as f:
# value = f.read()
# print(toSExpr(tree(structure(value))))
# print(references(value))

# EOF
