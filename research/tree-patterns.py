from nota.format.nd import parse
from nota.utils.tree import Node, toSExpr
from typing import ContextManager, Optional, Iterable
import inspect
from enum import Enum

# --
# This notebook explores the declaration of tree transformations
# to transform an AST into another one. XSLT and React are two
# well-known examples of that field, so we're trying to find
# something that is expressive. Tree-Sitter pattern queries
# are also a good example of expresive patterns.


# SEE: https://github.com/sebastien/tlang/blob/master/docs/query.txto
class Axis(Enum):
    NextSiblings = ">"
    PreviousSiblings = ">"
    Ancestors = "\\"
    Descendants = "/"


class Query:

    def __init__(self, name: str, axis: Optional[Axis] = None):
        self.name = name
        self.axis = axis

    def match(self, node: Node) -> bool:
        if node.name.startswith(self.name):
            return True
        else:
            return False

    def matchIter(self, node: Node) -> Iterable[tuple[int, Node]]:
        """Iterates through the matches of that query, starting with
        the given node, returning couples `(group,node)`, where consecutive
        nodes on the axis share the same group. Groups make it possible
        to batch nodes together."""
        axis = self.axis or Axis.Descendants
        group: int = 0
        previous: Optional[Node] = None
        if axis == Axis.Descendants:
            for child in node.descendants:
                if self.match(child):
                    if previous and child.parent != previous:
                        group += 1
                    yield (group, child)
                    previous = child
        elif axis == Axis.Ancestors:
            for parent in node.ancestors:
                if self.match(parent):
                    if previous not in parent.children:
                        group += 1
                    yield (group, parent)
                    previous = parent
        elif axis == Axis.NextSiblings:
            for sibling in node.nextSiblings:
                if self.match(sibling):
                    if previous and sibling.previousSibling != previous:
                        group += 1
                    yield (group, sibling)
                    previous = sibling
        elif axis == Axis.PreviousSiblings:
            for sibling in node.previousSiblings:
                if self.match(sibling):
                    if previous and sibling.nextSibling != previous:
                        group += 1
                    yield (group, sibling)
                    previous = sibling
        else:
            raise ValueError(f"Unsuported axis: {axis}")


class Selection(ContextManager):

    def __init__(self, query: Query):
        self.query = query
        self.parent: Optional[Selection] = None
        self.children: list[Selection] = []

    def add(self, selection: 'Selection') -> 'Selection':
        assert not selection.parent
        assert not selection in self.children
        selection.parent = self
        self.children.append(selection)
        return selection

    # --
    # Queries

    def select(self, name: str) -> 'Selection':
        return self.add(Selection(Query(name)))

    def next(self, name: str) -> 'Selection':
        return self.add(Selection(Query(name, axis=Axis.NextSiblings)))

    # --
    # Operations

    def replaceWith(self, *nodes):
        return self

    def remove(self, *nodes):
        return self.replaceWith()

    # --
    # Application
    def apply(self, node: Node):
        for group, matched in self.query.matchIter(node):
            print(group, matched)

    # --
    # Context

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        parent_locals = inspect.currentframe().f_back.f_locals
        # Upon exit, we name any atom that we find in the scope
        for k, v in ((k, v) for k, v in parent_locals.items()):
            if isinstance(v, Selection) and not v.parent:
                self.add(v)
            # if RE_OPTION.match(k) and t in self.ACCEPTED_TYPES:
            #     # TODO: Should look in the environment
            #     env = os.getenv(k, None)
            #     if env is not None:
            #         parent_locals[k] = self.ACCEPTED_TYPES[t](env)


def select(name: str):
    return Selection(Query(name))


with (ListItems := select("paragraph")) as p:
    with p.select("list-item") as c:
        p.replaceWith(c)


# We want the following
#
# ```
# (list-item:bullet)
#    (#text "This is another list")
#    (paragraph
#      (#text "  dsadssa"))
#    (paragraph)
#      (#text "  sadada"))
# ```
#
# To become
#
# ```
# (list-item:bullet)
#    (#text "This is another list  dsadssa  sadada"))
# ```
#
# To do so, we want to do:
# - Any paragraph content is merged in to the parent
# - Consecutive text nodes are merged

with (ExpandParagraphs := select("paragraph")) as p:
    with select("*") as contents:
        p.replaceWith(contents)

with (AggregateText := select("#text")) as p:
    with p.next("#text") as text:
        p.remove()


tree = parse("""
1) sdsad
2) assda

- This a  list
  sadsadsa *code*
  asdsadsasao *code here too*

- This is another list
  dsadssa
  sadada

""")
print(toSExpr(tree))
ExpandParagraphs.apply(tree)
# EOF
