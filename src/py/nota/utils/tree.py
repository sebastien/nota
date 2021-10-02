from typing import Optional, Optional, Any, List, Dict, Union, Iterable
import json


# NOTE: This is copied from parsource, originally from tlang.
class Node:
    """A node is an uniquely identified, named object with zero or one parent,
    a set of attributes and a list of children."""

    IDS = 0

    def __init__(self, name: str, **attributes):
        assert isinstance(
            name, str), f"Node name must be a string, got: {name}"
        self.name = name
        self.id = Node.IDS
        Node.IDS += 1
        self.parent: Optional['Node'] = None
        # FIXME: This does not support namespaces for attributes
        self.attributes: Dict[str, Any] = attributes
        self._children: List['Node'] = []
        self.metadata: Optional[Dict[str, Any]] = None

    @property
    def head(self) -> Optional['Node']:
        return self._children[0] if self._children else None

    @property
    def tail(self) -> List['Node']:
        return self._children[1:]

    @property
    def children(self) -> List['Node']:
        return self._children

    @property
    def count(self) -> int:
        return len(self._children)

    @property
    def root(self) -> Optional['Node']:
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
    def ancestors(self) -> Iterable['Node']:
        node = self.parent
        while node:
            yield node
            node = node.parent

    @property
    def descendants(self) -> Iterable['Node']:
        for child in self.children:
            yield child
            yield from child.descendants

    @property
    def previousSibling(self) -> Optional['Node']:
        if not self.parent:
            return None
        siblings = self.parent.children
        i = siblings.index(self)
        return siblings[i - 1] if i > 0 else None

    @property
    def nextSibling(self) -> Optional['Node']:
        if not self.parent:
            return None
        siblings = self.parent.children
        i = siblings.index(self)
        return siblings[i + 1] if i + 1 < len(siblings) else None

    @property
    def previousSiblings(self) -> Iterable['Node']:
        if not self.parent:
            return ()
        children = self.parent.children
        i = children.index(self)
        assert i >= 0
        return reversed(children[0:i])

    @property
    def nextSiblings(self) -> Iterable['Node']:
        if not self.parent:
            return ()
        children = self.parent.children
        i = children.index(self)
        assert i >= 0
        return children[i:]

    @property
    def firstChild(self) -> Optional['Node']:
        return self._children[0] if self._children else None

    @property
    def lastChild(self) -> Optional['Node']:
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

    def detach(self) -> 'Node':
        if self.parent:
            self.parent.remove(self)
        return self

    def wrap(self, node: "Node") -> 'Node':
        """Moves the current node into the given `node`, attaching the given
        `node` where the current node was in the parent."""
        parent = self.parent
        if parent:
            i = parent.index(self)
            parent.set(i, node)
        node.append(self)
        return self

    def absorb(self, node: "Node") -> 'Node':
        """Detaches the given node and merges in its children and attributes."""
        node.detach()
        self.merge(node)
        return self

    def merge(self, node: 'Node', attributes=True, replace=False) -> 'Node':
        children = [_ for _ in node._children]
        if attributes:
            # TODO: We could do a smarter merge
            for k, v in node.attributes.items():
                if replace or k not in self.attributes:
                    self.attributes[k] = v
        for c in children:
            self.add(c.detach())
        return self

    def add(self, node: 'Node') -> 'Node':
        assert isinstance(node, Node), f"Expected a Node, got: {node}"
        assert not node.parent, "Cannot add node to {0}, it already has a parent: {1}".format(
            self, node)
        node.parent = self
        self._children.append(node)
        return node

    def set(self, index, node: 'Node') -> 'Node':
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

    def setChildren(self, children: Iterable['Node']):
        if self.children:
            for child in self.children:
                child.parent = None
            self._children = []
        for child in children:
            self.append(child)
        return self

    def append(self, node: 'Node') -> 'Node':
        return self.add(node)

    def extend(self, nodes: List['Node']) -> 'Node':
        for node in nodes:
            self.add(node.detach())
        return self

    def remove(self, node: 'Node') -> 'Node':
        assert node.parent is self, "Cannot remove node from {0}, it has a different parent: {1}".format(
            self, node.parent)
        node.parent = None
        self._children.remove(node)
        return node

    def insert(self, index: int, node: 'Node') -> 'Node':
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

    def replaceWith(self, nodes: Union['Node', List['Node']]):
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

    def walk(self, functor=None, processor=None) -> List[Any]:
        p = processor or (lambda _: _)
        return list(p(_) for _ in self.iterWalk(functor))

    def iterWalk(self, functor=None):
        if (not functor) or functor(self) is not False:
            yield self
            for c in self._children:
                yield from c.iterWalk(functor)

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

    def iterXML(self) -> Iterable[str]:
        stop = False
        if self.name == "text":
            if "value" in self.attributes and len(self.attributes) == 1:
                yield str(self.attributes["value"])
                stop = True
            elif not self.attributes:
                yield ""
                stop = True
        if not stop:
            attributes = " ".join(
                f"{k}={json.dumps(v) if isinstance(v,str) else json.dumps(json.dumps(v))}" for k, v in self.attributes.items())
            prefix = f"{self.name}{' ' if attributes else ''}{attributes}"
            if not self._children:
                yield f"<{prefix} />"
            else:
                yield f"<{prefix}>"
                for child in self._children:
                    yield from child.iterXML()
                yield f"</{self.name}>"

    def toXML(self) -> str:
        return "".join(self.iterXML())

    def iterTDoc(self, level=0) -> Iterable[str]:
        attributes = " ".join(f"{k}={repr(v)}" for k,
                              v in self.attributes.items())
        yield f"{self.name or 'â'} {attributes}"
        last_i = len(self.children) - 1
        for i, child in enumerate(self.children):
            for j, line in enumerate(child.iterTDoc(level + 1)):
                leader = ("ââ " if i == last_i else "ââ ") if j == 0 else (
                    "   " if i == last_i else "â  ")
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
    def __contains__(self, value: Union[int, str, 'Node']) -> bool:
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
        if isinstance(node, NamedNode):
            yield f"  {node.id}[label={json.dumps(node.path or ':root')}];"
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
