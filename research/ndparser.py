# --
# # Nota Parser
#
# I know this one is going to be big, it's the parsing of Nota, a Markdown derived
# format designed for semantic note taking.

from typing import (
    Optional,
    Union,
    NamedTuple,
    Iterator,
    Callable,
    Generic,
    TypeVar,
    Any,
)
from nota.utils.tree import Node, toSExpr
from contextlib import contextmanager
from math import ceil
import inspect
import re
from pathlib import Path

K = TypeVar("K")
V = TypeVar("V")


# --
# ## Boilerplate
#
# This is a bit of a boilerplate for implicitly registering elements of a given
# type within a collection.
class Collection(Generic[K, V], dict[K, V]):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


@contextmanager
def declared():
    items: Collection[str, Any] = Collection()
    scope = inspect.currentframe().f_back.f_back
    l = {} | scope.f_locals
    yield items
    for k, v in scope.f_locals.items():
        if v is not l.get(k) and v is not items:
            items[k] = v


# --
# # Model


class Inline(NamedTuple):
    start: re.Pattern[str]
    end: Optional[re.Pattern[str]]


class Prefix(NamedTuple):
    text: re.Pattern[str]
    extract: Optional[Callable[[re.Match[str]], str]] = None


class Line(NamedTuple):
    start: Prefix


class Block(NamedTuple):
    start: Prefix
    end: Optional[Prefix] = None
    # Indicates that the blocks form a list together
    sequential: bool = False
    # Indicates that the block can be nested within another one
    nested: bool = False
    # Arguably, at that point we could probably make a class
    creator: Optional[Callable[["MatchedBlock", re.Match[str]], "MatchedBlock"]] = None


class Grammar(NamedTuple):
    blocks: dict[str, Block]
    lines: dict[str, Line]
    inlines: dict[str, Inline]


def inline(
    start: str | re.Pattern[str], end: Optional[str | re.Pattern[str]] = None
) -> Inline:
    re_start = re.compile(re.escape(start)) if isinstance(start, str) else start
    re_end = re.compile(re.escape(end)) if isinstance(end, str) else end
    return Inline(
        start=re_start,
        end=re_start if re_end is None else re_end,
    )


# NOTE: Compared to inline, `prefix(start)` takes a string that will be
# converted to regular expression.
def prefix(
    start: Optional[str] = None,
    indented: bool = False,
    extract: Optional[Callable[[re.Match[str]], str]] = None,
) -> Prefix:
    return Prefix(
        re.compile(
            (f"^(?P<indent>[ \\t]*)(?P<indented>{start})" if indented else f"^{start}")
            if start
            else r"^[ \t]*$"
        ),
        extract,
    )


def grammar(
    blocks: dict[str, Block], lines: dict[str, Line], inlines: dict[str, Inline]
) -> Grammar:
    return Grammar(blocks, lines, inlines)


# --
# # Grammar

# --
# Here we want to match anything like `_*`code`*_`
with declared() as Inlines:
    Strong = inline("**")
    Emphasis = inline("*")
    Term = inline("_")
    Code = inline("`")
    Quote = inline("<<", ">>")
    Link = inline("[", re.compile(r"\]\((?P<target>[^\)]*)\)"))
    Anchor = inline("[", "]")

with declared() as Microformats:
    Tag = inline(re.compile(r"#(?P<name>[\w\d\-_]+)"))
    Ref = inline(re.compile(r"#{(?P<name>[^}]+)}"))
    Email = inline(re.compile(r"\<(?P<email>[\w.\-_]+@[\w.\-_]+)\>"))
    URL = inline(re.compile(r"\<(?P<url>[A-z]+://[^\>]+)\>"))
    Date = inline(re.compile(r"\d\d\d\d\-[01]\d\-[0123]\d"))
    Time = inline(re.compile(r"[012]\d:[012345]\d:[012345]\d"))


def asSpaces(m: re.Match[str]) -> str:
    return len(m.group()) * " "


with declared() as Prefixes:
    TodoListItem = prefix(r"\[(?P<state>[ xX])\][ ]*", indented=True, extract=asSpaces)
    OrderedListItem = prefix(
        r"(?P<number>[0-9a-zA-Z])[\)\.][ ]*", indented=True, extract=asSpaces
    )
    UnorderedListItem = prefix("(?P<bullet>[-*])[ ]*", indented=True, extract=asSpaces)
    DefinitionItem = prefix(
        r"(?P<term>([^:]|:[^:])+)::[ ]*$", extract=lambda _: _.group()
    )
    Fence = prefix(r"```(?P<lang>.*)$")
    Meta = prefix("--[ ]*")
    Title = prefix("==+[ ]*")
    Comment = prefix("# --[ ]*")
    Heading = prefix("#+[ ]*")
    Comment = prefix("//[ ]*")
    Empty = prefix(r"[ \t]*$")


with declared() as Lines:
    Title = Line(Prefixes.Title)
    Heading = Line(Prefixes.Heading)
    Meta = Line(Prefixes.Meta)
    Comment = Line(Prefixes.Comment)

with declared() as Blocks:
    Empty = Block(start=Empty)
    Code = Block(
        start=Fence,
        end=Fence,
    )
    TodoListItem = Block(
        start=Prefixes.TodoListItem,
        sequential=True,
        nested=True,
    )
    OrderedListItem = Block(
        start=Prefixes.OrderedListItem,
        sequential=True,
        nested=True,
    )
    UnorderdedListItem = Block(
        start=Prefixes.UnorderedListItem,
        sequential=True,
        nested=True,
    )
    DefinitionListItem = Block(
        start=Prefixes.DefinitionItem,
        sequential=True,
        # No nesting for definition lists
    )


# This is an implicit end block, ie the next matching block will
# take over
# UnorderedListItem = Block(start=(Indent, "-"))


Nota = grammar(Blocks, Lines, Inlines)

# --
# ## Text Positions


class Position(NamedTuple):
    offset: int
    line: int | None
    column: int | None


class TextRange(NamedTuple):
    start: Position
    end: Position


class TextFragment(NamedTuple):
    text: str
    range: TextRange


# --
# ## Parsing


class MatchedBlock(NamedTuple):
    name: str
    block: Optional[Block | Line]
    lines: list[str]
    start: Optional[re.Match[str]] = None
    end: Optional[re.Match[str]] = None
    # NOTE: We should probably store the indentation there. It may be
    # re-calculated, but it's better to store it.


class MatchedText(NamedTuple):
    text: str


class MatchedInline(NamedTuple):
    name: str
    attrs: dict[str, str]
    children: list[Union[MatchedText, "MatchedInline"]]


def indentation(
    text: str | MatchedBlock,
    tabwidth: int = 4,
    start: int = 0,
    RE_NONTAB=re.compile(r"[^\t]"),
    RE_EMPTY=re.compile(r"^[ \t]*$"),
) -> int:
    """Returns the number of leading spaces in the given line.
    A tab will have the value given by the TAB_SIZE global."""
    if isinstance(text, MatchedBlock):
        prefix = (
            RE_NONTAB.sub(" ", text.start.groupdict().get("indented", ""))
            if text.start
            else None
        )
        head = text.lines[:4]
        return ceil(
            sum(
                indentation(
                    f"{prefix}{_}" if prefix else _, tabwidth=tabwidth, start=start
                )
                for _ in head
                if not RE_EMPTY.match(_)
            )
            / len(head)
        )
    else:
        count: int = start
        for char in text:
            if char == "\t":
                count += tabwidth - (count % tabwidth)
            elif char == " ":
                count += 1
            else:
                return count
        return count


def parseInlines(
    line: str,
    inlines: dict[str, Inline] = Microformats | Inlines,
    *,
    start: int = 0,
    end: Optional[int] = None,
    lineno: int = 0,
) -> Iterator[MatchedInline | MatchedText]:
    o: int = start
    n: int = end or len(line)
    while inlines and o < n:
        i: int = n
        # We iterate on the active parsers
        starts: dict[str, re.Match[str]] = {}
        ends: dict[str, re.Match[str]] = {}
        for k, v in inlines.items():
            # We look for as start match
            if m := v.start.search(line, o):
                starts[k] = m
                if not v.end:
                    # If the parser has no end, then it's a match and start[k] == end[k]
                    ends[k] = m
                elif (e := v.end.search(line, m.end())) and (e and e.end() <= n):
                    # We have an end match, which we register
                    ends[k] = e
                else:
                    # No end match, the parser becomes inactive
                    pass
        # We prune parsers that haven't matched
        inlines = {k: v for k, v in inlines.items() if k in ends}
        closest: Optional[str] = None
        for k, e in ends.items():
            if (j := starts[k].start()) < i:
                closest = k
                i = j
        if closest:
            # There is a closest match
            s = starts[closest].start()
            if o < s:
                yield MatchedText(line[o:s])
            attrs = starts[closest].groupdict() | ends[closest].groupdict()
            yield MatchedInline(
                closest,
                attrs,
                list(
                    parseInlines(
                        line,
                        # NOTE: We can pass inlines here as we would already know
                        # if there had been a match or not. We would also have an
                        # opportunity to reuse matches here.
                        inlines,
                        start=starts[closest].end(),
                        end=ends[closest].start(),
                        lineno=lineno,
                    )
                ),
            )
            o = ends[closest].end()
        else:
            yield MatchedText(line[o:n])
            o = n + 1
    if o < n:
        yield MatchedText(line[o:n])


def parseBlocks(
    input: Iterator[str],
    blocks: dict[str, Block | Line] = Lines | Blocks,
) -> Iterator[MatchedBlock]:
    """Takes a stream of lines and outputs matched blocks as they are parsed."""
    cur: Optional[MatchedBlock] = None
    for line in input:
        if cur and cur.block and isinstance(cur.block, Block) and cur.block.end:
            # The current block is an explicit block, so we end the block
            # when the end matches.
            if m := cur.block.end.text.match(line):
                # TODO: Maybe we should post-process the block
                cur.lines.append(line[: m.start()])
                yield cur._replace(end=m)
                cur = None
            else:
                cur.lines.append(line)
        else:
            matched: Optional[MatchedBlock] = None
            # Note that here the order of blocks matters, the first match
            # will take precedence over the other one.
            for k, b in blocks.items():
                if m := b.start.text.match(line):
                    if cur:
                        yield cur
                    t = line[m.end() :]
                    matched = MatchedBlock(
                        k, b, [f"{b.start.extract(m)}{t}" if b.start.extract else t], m
                    )
                    if isinstance(b, Block):
                        cur = matched
                    else:
                        yield matched
                        cur = None
                    break
            # If we haven't found a matched block, then we either create
            # a new text block or append to the current one.
            if not matched:
                if not cur or cur.name != "":
                    if cur:
                        yield cur
                    cur = MatchedBlock("", None, [line])
                else:
                    cur.lines.append(line)
    if cur:
        yield cur


def inlineToNode(inline: MatchedText | MatchedInline) -> Node:
    """Converts a matched text or inline to a corresponding node object."""
    match inline:
        case MatchedText(text):
            return Node("#text", {"value": text})
        case MatchedInline(name, attrs, children):
            return Node(name, attrs, [inlineToNode(_) for _ in children])


def parseLines(input: Iterator[str]) -> Node:
    """Main entry point for creating a tree of nodes from a stream of lines."""
    root: Node = Node("Nota")
    stack: list[tuple[int, Node]] = []
    node: Optional[Node] = None
    print("==== START")
    for b in parseBlocks(input):
        block = b.block if isinstance(b.block, Block) else None
        if block is Blocks.Empty:
            continue
        # We find the parent node
        ind = indentation(b) + (1 if block and block.nested else 0)
        print("-- Block", b.name, ind, repr("".join(b.lines)), indentation(b.lines[0]))
        while stack and stack[-1][0] >= ind:
            stack.pop()
        parent = stack[-1][1] if stack else None
        if block and block.sequential:
            parent_name = b.name.replace("Item", "")
            # If there is no parent, or the parent is not the one
            # we expect, we create a new item.
            if parent and parent.name != parent_name:
                stack.pop()
            parent = Node(parent_name)
            (stack[-1][1] if stack else root).append(parent)
            stack.append((ind, parent))
            print("XXX parent", parent, ind)
        # We create a node
        attrs = {
            "start": b.start.start() if b.start else None,
            "end": b.end.end() if b.end else b.start.end() if b.start else None,
        }
        if b.name:
            node = Node(
                b.name,
                attrs,
            )
            (parent or root).append(node)
        elif not node:
            node = Node("Paragraph", attrs)
            (parent or root).append(node)
        else:
            # Same node
            pass
        for _ in parseInlines("".join(b.lines)):
            node.append(inlineToNode(_))
    return root


# --
# ## Parsing passes

if __name__ == "__main__":
    import sys

    base = Path(__file__).absolute().parent.parent
    for arg in sys.argv[1:] or (base / "tests/data/nota-blocks.nd",):
        with open(arg) as f:
            doc = parseLines(f.readlines())
            print(toSExpr(doc))
            # print(doc.toPrimitive())
            # print(doc.toXML())

# EOF
