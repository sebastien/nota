from typing import Optional, Optional, Any, Union, Iterable, TypeVar, Generic
import html
import json

T = TypeVar('T')


# NOTE: This is copied from parsource, originally from tlang.
class Node(Generic[T]):
    """A node is an uniquely identified, named object with zero or one parent,
    a set of attributes and a list of children."""

    IDS = 0

    def __init__(self, name: str, attributes: Optional[dict[str, Union[str, int, float, tuple]]] = None):
        assert isinstance(
            name, str), f"Node name must be a string, got: {name}"
        self.name = name
        self.data: Optional[T] = None
        self.id = Node.IDS
        Node.IDS += 1
        self.parent: Optional['Node[T]'] = None
        # FIXME: This does not support namespaces for attributes
        self.attributes: dict[str, Any] = attributes if attributes else {}
        self._children: list['Node[T]'] = []
        self.metadata: Optional[dict[str, Any]] = None

    @property
    def head(self) -> Optional['Node[T]']:
        return self._children[0] if self._children else None

    @property
    def tail(self) -> list['Node[T]']:
        return self._children[1:]

    @property
    def children(self) -> list['Node[T]']:
        return self._children

    @property
    def count(self) -> int:
        return len(self._children)

    @property
    def root(self) -> Optional['Node[T]']:
        root = None
        parent = self.parent
        while parent:
            root = parent
            parent = parent.parent
        return root

    @property
    def isTree(self) -> bool:
        return not self.parent

    @property
    def isEmpty(self) -> bool:
        return self.isLeaf and not self.hasAttributes

    @property
    def isSubtree(self) -> bool:
        return bool(self.parent)

    @property
    def ancestors(self) -> Iterable['Node[T]']:
        node = self.parent
        while node:
            yield node
            node = node.parent

    @property
    def descendants(self) -> Iterable['Node[T]']:
        for child in self.children:
            yield child
            yield from child.descendants

    @property
    def previousSibling(self) -> Optional['Node[T]']:
        if not self.parent:
            return None
        siblings = self.parent.children
        i = siblings.index(self)
        return siblings[i - 1] if i > 0 else None

    @property
    def nextSibling(self) -> Optional['Node[T]']:
        if not self.parent:
            return None
        siblings = self.parent.children
        i = siblings.index(self)
        return siblings[i + 1] if i + 1 < len(siblings) else None

    @property
    def previousSiblings(self) -> Iterable['Node[T]']:
        if not self.parent:
            return ()
        children = self.parent.children
        i = children.index(self)
        assert i >= 0
        return reversed(children[0:i])

    @property
    def nextSiblings(self) -> Iterable['Node[T]']:
        if not self.parent:
            return ()
        children = self.parent.children
        i = children.index(self)
        assert i >= 0
        return children[i:]

    @property
    def firstChild(self) -> Optional['Node[T]']:
        return self._children[0] if self._children else None

    @property
    def lastChild(self) -> Optional['Node[T]']:
        return self._children[-1] if self._children else None

    @property
    def isLeaf(self) -> bool:
        return len(self._children) == 0

    @property
    def isNode(self) -> bool:
        return len(self._children) > 0

    @property
    def hasAttributes(self) -> bool:
        return len(self.attributes) > 0

    def hasAttribute(self, name: str) -> bool:
        return name in self.attributes

    def setAttribute(self, name, value=None):
        self.attributes[name] = value
        return self

    def getAttribute(self, name: str):
        return self.attributes.get(name)

    def removeAttribute(self, name):
        del self.attributes[name]
        return self

    def updateAttributes(self, attributes):
        self.attributes.update(attributes)
        return self

    def copy(self, depth=-1):
        """Does a deep copy of this node. If a depth is given, it will
        stop at the given depth."""
        node = Node(self.name)
        self.attributes = type(self.attributes)((k, v)
                                                for k, v in self.attributes.items())
        if depth != 0:
            for child in self._children:
                node.append(child.copy(depth - 1))
        return node

    def index(self, node=None) -> Optional[int]:
        if not node:
            return self.parent.index(self) if self.parent else None
        else:
            return self._children.index(node)

    def detach(self) -> 'Node[T]':
        if self.parent:
            self.parent.remove(self)
        return self

    def wrap(self, node: "Node") -> 'Node[T]':
        """Moves the current node into the given `node`, attaching the given
        `node` where the current node was in the parent."""
        parent = self.parent
        if parent:
            i = parent.index(self)
            parent.set(i, node)
        node.append(self)
        return self

    def absorb(self, node: "Node") -> 'Node[T]':
        """Detaches the given node and merges in its children and attributes."""
        node.detach()
        self.merge(node)
        return self

    def merge(self, node: 'Node[T]', attributes=True, replace=False) -> 'Node[T]':
        children = [_ for _ in node._children]
        if attributes:
            # TODO: We could do a smarter merge
            for k, v in node.attributes.items():
                if replace or k not in self.attributes:
                    self.attributes[k] = v
        for c in children:
            self.add(c.detach())
        return self

    def add(self, node: 'Node[T]') -> 'Node[T]':
        assert isinstance(node, Node), f"Expected a Node, got: {node}"
        assert not node.parent, "Cannot add node to {0}, it already has a parent: {1}".format(
            self, node)
        node.parent = self
        self._children.append(node)
        return self

    def set(self, index, node: 'Node[T]') -> 'Node[T]':
        assert isinstance(node, Node), f"Expected a Node, got: {node}"
        assert not node.parent, "Cannot set node to {0}, it already has a parent: {1}".format(
            self, node)
        n = len(self._children)
        if n == 0:
            return self.add(node)
        else:
            # NOTE: We don't want to use detach here
            i = min(max(0, n + index if index < 0 else index), n - 1)
            previous = self._children[i]
            self._children[i] = node
            previous.parent = None
            node.parent = self
            return node

    def setChildren(self, children: Iterable['Node[T]']) -> 'Node[T]':
        if self.children:
            for child in self.children:
                child.parent = None
            self._children = []
        for child in children:
            self.append(child)
        return self

    def append(self, node: 'Node[T]') -> 'Node[T]':
        return self.add(node)

    def extend(self, nodes: list['Node[T]']) -> 'Node[T]':
        for node in nodes:
            self.add(node.detach())
        return self

    def remove(self, node: 'Node[T]') -> 'Node[T]':
        assert node.parent is self, "Cannot remove node from {0}, it has a different parent: {1}".format(
            self, node.parent)
        node.parent = None
        self._children.remove(node)
        return node

    def insert(self, index: int, node: 'Node[T]') -> 'Node[T]':
        index = index if index >= 0 else len(self._children) + index
        assert index >= 0 and index <= len(
            self._children), "Index out of bounds {0} in: {1}".format(index, self)
        assert not node.parent, "Cannot add node to {0}, it already has a parent: {1}".format(
            self, node)
        node.parent = self
        if index == len(self._children):
            self._children.append(node)
        else:
            self._children.insert(index, node)
        return node

    def replaceWith(self, nodes: Union['Node[T]', list['Node[T]']]):
        nodes = [nodes] if isinstance(nodes, Node) else nodes
        index = self.index()
        if index is None:
            assert self.parent
            for child in self.children:
                self.parent.append(child)
        else:
            for i in range(len(nodes) - 1, -1, -1):
                if self.parent:
                    self.parent.insert(index, nodes[i])
        self.detach()
        return self

    def walk(self, functor=None, processor=None, filter=None) -> list[Any]:
        return list(self.iterWalk(functor=functor, processor=processor, filter=filter))

    def iterWalk(self, functor=None, processor=None, filter=None) -> Iterable[Any]:
        if (not functor) or functor(self) is not False:
            if (not filter) or filter(self):
                yield processor(self) if processor else self
            for c in self._children:
                yield from c.iterWalk(functor, processor, filter)

    def asDict(self):
        res: dict[str, Any] = {"id": self.id}
        if self.name:
            res["name"] = self.name
        if self.parent:
            res["parent"] = self.parent.id
        if self.attributes:
            res["attributes"] = self.attributes
        if self.metadata:
            res["metadata"] = self.metadata
        if self._children:
            res["children"] = [_.asDict() for _ in self._children]
        return res

    def iterXML(self, level=0, indent="", eol=False, notEmpty:Optional[list[str]]=None) -> Iterable[str]:
        if self.name == "#text" and "value" in self.attributes and len(self.attributes) == 1:
            yield html.escape(str(self.attributes["value"]))
        else:
            indent_prefix = "" * level
            name = "text" if self.name  == "#text" else self.name
            end = "\n" if eol else ""
            attributes = " ".join(
                f"{k}={json.dumps(v) if isinstance(v,str) else json.dumps(repr(v))}" for k, v in self.attributes.items())
            prefix = f"{name}{' ' if attributes else ''}{attributes}"
            if self._children or (notEmpty and self.name in notEmpty):
                yield f"{indent_prefix}<{prefix}>{end}"
                for child in self._children:
                    yield from child.iterXML(level+1, indent)
                yield f"{indent_prefix}</{name}>{end}"
            else:
                yield f"{indent_prefix}<{prefix} />{end}"
    def toXML(self, indent="") -> str:
        return "".join(self.iterXML(indent=indent))

    def toHTML(self, indent="") -> str:
        return "".join(self.iterXML(indent=indent, notEmpty=["ul", "div", "script", "span"]))

    def iterTDoc(self, level=0) -> Iterable[str]:
        attributes = " ".join(f"{k}={repr(v)}" for k,
                              v in self.attributes.items())
        yield f"{self.name or '──'} {attributes}"
        last_i = len(self.children) - 1
        for i, child in enumerate(self.children):
            for j, line in enumerate(child.iterTDoc(level + 1)):
                leader = ("└ " if i == last_i else "├ ") if j == 0 else (
                    "   " if i == last_i else "│  ")
                yield leader + line

    def toTDoc(self) -> str:
        return "\n".join(self.iterTDoc())

    def __getitem__(self, index: Union[int, str]):
        if isinstance(index, str):
            if index not in self.attributes:
                raise IndexError(f"Node has no attribute '{index}': {self}")
            else:
                return self.attributes[index]
        else:
            return self._children[index]

    # FIXME: Does not seem to work, should check
    def __contains__(self, value: Union[int, str, 'Node[T]']) -> bool:
        if isinstance(value, int):
            return value >= 0 and value < self.count
        elif isinstance(value, Node):
            return value in self._children
        elif isinstance(value, str):
            return value in self.attributes
        else:
            return False

    def __repr__(self):
        return f"<Node:{self.name} {' '.join(str(k)+'='+repr(v) for k,v in self.attributes.items())}{' …' + str(len(self.children)) if self._children else ''}>"


def node(name: str, *children: Node, **attributes: Any):
    return Node(name, **attributes).setChildren(children)


def toASCIILines(node: Node, prefix="") -> Iterable[str]:
    # FIXME: It's ~OK but needs improvement
    p = "─┬" if node.children else "──"
    yield f"{prefix}{p} {node.name or ':root'}"
    last_child = len(node.children) - 1
    prefix = prefix.replace("├", "│").replace("└", " ")
    for i, child in enumerate(node.children):
        yield from toASCIILines(child, prefix + (" ├" if i < last_child else " └"))


def toSExprLines(node: Node, prefix="", suffix="") -> Iterable[str]:
    # FIXME: It's ~OK but needs improvement
    last_child = len(node.children) - 1
    suffix += ")" if last_child < 0 else ""
    if node.name == "#text":
        yield f"{prefix}({node.name or ':root'} {json.dumps(node.data)}{suffix}"
    else:
        yield f"{prefix}({node.name or ':root'}{suffix}"
    if last_child >= 0:
        child_prefix = " " * len(prefix)
        for i, child in enumerate(node.children):
            yield from toSExprLines(child, child_prefix + ("  " if i < last_child else "  "), ")" if i == last_child else "")


def toGraphvizLines(cls, root: Node) -> Iterable[str]:
    yield "digraph {"
    for node in root.walk():
        if node.name:
            yield f"  {node.id}[label={node.name}];"
        else:
            yield f"  {node.id};"
        for child in node.children:
            yield f"  {node.id}->{child.id};"
    yield "}"


def withNumbers(lines: Iterable[str]) -> Iterable[str]:
    for i, line in enumerate(lines):
        yield f"{i:03d} {line}"


def toText(lines: Iterable[str], numbers=False) -> str:
    return "\n".join(withNumbers(lines) if numbers else lines)


def toASCII(node: Node, numbers=False) -> str:
    return toText(toASCIILines(node), numbers=numbers)


def toSExpr(node: Node, numbers=False) -> str:
    return toText(toSExprLines(node), numbers=numbers)


def toGraphviz(node: Node, numbers=False) -> str:
    return toText(toGraphvizLines(node), numbers=numbers)

# EOF
