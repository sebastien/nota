from nota.format.nd import parse
from nota.utils.tree import Node, toSExpr
from typing import ContextManager, Optional, Iterable, Union, Generic, TypeVar, cast
from enum import Enum
from fnmatch import fnmatch
import inspect
import functools

# --
# This notebook explores the declaration of tree transformations
# to transform an AST into another one. XSLT and React are two
# well-known examples of that field, so we're trying to find
# something that is expressive. Tree-Sitter pattern queries
# are also a good example of expresive patterns.

T = TypeVar('T')

# SEE: https://github.com/sebastien/tlang/blob/master/docs/query.txto


class Axis(Enum):
    NextSiblings = ">"
    PreviousSiblings = ">"
    Ancestors = "\\"
    Descendants = "/"


class Query:

    @classmethod
    def Parse(cls, query: str) -> 'Query':
        axis = None
        name = query
        limit = None
        if query.startswith("//"):
            axis = Axis.Descendants
            name = name[2:]
        elif query.startswith("/"):
            axis = Axis.Descendants
            limit = 1
            name = name[1:]
        elif query.startswith(">>"):
            axis = Axis.NextSiblings
            name = name[2:]
        elif query.startswith(">"):
            axis = Axis.NextSiblings
            limit = 1
            name = name[1:]
        elif query.startswith(">>"):
            axis = Axis.PreviousSiblings
            name = name[2:]
        elif query.startswith(">"):
            axis = Axis.PreviousSiblings
            limit = 1
            name = name[1:]
        return cls(name, axis, limit)

    def __init__(self, name: str, axis: Optional[Axis] = None, limit: Optional[int] = None):
        self.name = name
        self.axis = axis
        self.limit = limit

    def match(self, node: Node) -> bool:
        name = node.name.split(":", 1)[0]
        if fnmatch(name, self.name):
            return True
        else:
            return False

    def matchGroups(self, node: Node) -> Iterable[list[Node]]:
        group = 0
        res: list[Node] = []
        for g, n in self.matchIter(node):
            if g != group and res:
                yield res
                res = []
            res.append(n)
            group = g
        if res:
            yield res

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

    def __repr__(self):
        axis = self.axis.value if self.axis else "/"
        return f"(select \"{axis}{self.limit or axis}{self.name}\")"


class MatchContext:

    def __init__(self, parent: Optional['MatchContext'] = None):
        self.parent = parent
        self.entries: dict[int, list[Node]] = {}

    def set(self, id: int, nodes: list[Node]) -> list[Node]:
        self.entries[id] = nodes
        return nodes

    def get(self, id: int) -> Optional[list[Node]]:
        if id in self.entries:
            return self.entries[id]
        elif self.parent:
            return self.parent.get(id)
        else:
            return None

    def derive(self) -> 'MatchContext':
        return MatchContext(self)


class Transform:

    def apply(self, context: MatchContext):
        raise NotImplementedError


class Selection(ContextManager):

    IDS: int = 0
    Stack: list['Selection'] = []

    def __init__(self, query: Query):
        self.id = Selection.IDS = Selection.IDS + 1
        self.query = query
        self.parent: Optional[Selection] = None
        self.selections: list[Selection] = []
        self.transforms: list[Transform] = []

    def add(self, value: Union['Selection', Transform]) -> Union['Selection', Transform]:
        if isinstance(value, Transform):
            transform = value
            self.transforms.append(transform)
            return transform
        else:
            selection = value
            assert not selection.parent
            assert not selection in self.selections
            selection.parent = self
            self.selections.append(selection)
            return selection

    # --
    # Queries

    def select(self, query: str) -> 'Selection':
        return cast(Selection, self.add(Selection(Query.Parse(query))))

    def next(self, query: str) -> 'Selection':
        return cast(Selection, self.add(Selection(Query(query, axis=Axis.NextSiblings))))

    # --
    # Application

    def apply(self, node: Node, context: Optional[MatchContext] = None):
        ctx = MatchContext() if context is None else context
        for nodes in self.query.matchGroups(node):
            ctx.set(self.id, nodes)
            for transform in self.transforms:
                transform.apply(ctx)
            for selection in self.selections:
                # FIXME: This should really be addressed holistically,
                # as it will be super inefficient if the selection
                # is a siblings or descendants
                derived = ctx.derive()
                for node in nodes:
                    selection.apply(node, derived)
            # for node in nodes:
            #     yield node

    # --
    # Context

    def __enter__(self):
        Selection.Stack.append(self)
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
        Selection.Stack.pop()

    def __str__(self):
        return f"<Selection id={self.id} query=\"{self.query.axis.value if self.query.axis else '/'}{self.query.name}\">"


class Replace(Transform):

    def __init__(self, original: Selection, new: Selection):
        self.original = original
        self.new = new

    # FIXME: That does not quite work, as we basically need to remap
    # a tree A to a tree B. In a way, the apply should produce a list of remappings
    # and then as a result, tree B should be constructed from the remapping. Otherwise
    # we'd be iterating on a mutable structure, which we don't want.
    def apply(self, context: MatchContext):
        la = context.get(self.original.id) or ()
        lb = context.get(self.new.id) or ()
        replaced = []
        for a in la:
            parent = a.parent
            print("Replacing", toSExpr(parent))
            for b in lb:
                if a.parent:
                    a.replaceWith(b.copy())
            print("XXX replaced", toSExpr(parent))


class Remove(Transform):

    def __init__(self, selection: Selection):
        selection

    def apply(self, context: MatchContext):
        print("Remove", context)


class Effect(Transform):

    def __init__(self, selection: Selection, functor):
        self.selection = selection
        self.functor = functor

    def apply(self, context: MatchContext):
        self.functor(context.get(self.selection.id))

# --
# We use a React-like functional API that will automatically
# register created objects in the currnet chain. This pattern
# leverages


def registered(f):
    """Decorator that passes the result of the wrapped function
    to `register`"""
    def wrapper(*args, **kwargs):
        res = f(*args, **kwargs)
        return Selection.Stack[-1].add(res) if Selection.Stack else res
    functools.update_wrapper(wrapper, f)
    return wrapper


@registered
def select(query: str) -> Selection:
    return Selection(Query.Parse(query))


@registered
def replace(original: Selection, by: Selection) -> Replace:
    return Replace(original, by)


@registered
def remove(selection: Selection) -> Remove:
    return Remove(selection)


@registered
def effect(selection: Selection, functor) -> Effect:
    return Effect(selection, functor)


with (ListItems := select("paragraph")) as p:
    with p.select("list-item") as c:
        replace(p, c)


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

with (ExpandParagraphs := select("//paragraph")) as p:
    with select("*") as contents:
        replace(p, contents)
        effect(contents, lambda _: print("Content", _))

with (AggregateText := select("#text")) as p:
    with p.next("#text") as text:
        remove(p)


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
# print(toSExpr(tree))
# print("*" * 20)
print(ExpandParagraphs)
print(ExpandParagraphs.apply(tree))
print("OK")
# print(toSExpr(tree))
# print("*" * 20)

# print(list(select("//list-item").apply(tree)))

# EOF
