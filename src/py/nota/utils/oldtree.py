from typing import Optional, Iterable, Callable, Any, cast
import time
import json

# # Tree Library
#
# Defines the fundamental building blocks for working with tree-like data.

__doc__ = """
Defines different types of nodes that can be used to work with tree-like
structures. Each tree structure supports a few useful features:

- event dispatching
- depth-first walking
- update and children updat timestamps (activated with `touch`).
"""


class Event:
    """Wraps some data and binds it to a name. An event is propagated up
    a tree until its `isPropagating` attribute is set to `False`."""

    def __init__(self, name: str, data: Optional[Any] = None):
        self.name = name
        self.data = data
        self.created = time.time()
        self.target: Optional['Node'] = None
        self.isPropagating: bool = True

    def stop(self):
        self.isPropagating = False
        return self

    def __str__(self):
        return f"<Event {self.name}={self.data}>"


class Node:
    """A basic implementation of a tree."""

    ID = 0
    SEPARATOR = "."

    def __init__(self, name: Optional[str] = None, data: Any = None):
        self.id: int = Node.ID
        Node.ID += 1
        self._name: Optional[str] = name
        self._children: list['Node'] = []
        self.parent: Optional['Node'] = None
        self.data = data
        self.attributes: dict[str, Any] = {}
        self.meta: dict[str, Any] = {}
        self.handlers: Optional[dict[str, Callable]] = None
        self.changed = time.time()
        self.childChanged = self.changed

    @property
    def name(self):
        return self._name or str(self.id)

    @property
    def root(self) -> Optional['Node']:
        root = None
        while node := self.parent:
            root = node
        return root

    @property
    def parentIndex(self) -> int:
        return self.parent.children.index(self) if self.parent else 0

    @property
    def cacheKey(self):
        """The key is used for caching."""
        return self.path

    @property
    def path(self):
        if self.parent:
            if self.parent.isRoot:
                return self.name
            else:
                return f"{self.parent.path}{self.SEPARATOR}{self.name}"
        else:
            return "#root"

    @property
    def depth(self) -> int:
        node = self
        depth = 0
        while node.parent:
            node = node.parent
            depth += 1
        return depth

    @property
    def root(self) -> 'Node':
        node = self
        while node.parent:
            node = node.parent
        return node

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
    def nextSibling(self) -> Optional['Node']:
        if not self.parent:
            return None
        children = self.parent.children
        i = children.index(self)
        assert i >= 0
        return children[i+1] if i + 1 < len(children) else None

    @property
    def previousSibling(self) -> Optional['Node']:
        if not self.parent:
            return None
        children = self.parent.children
        i = children.index(self)
        assert i >= 0
        return children[i-1] if i > 0 else None

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
    def leaves(self) -> Iterable['Node']:
        if not self.children:
            yield self
        else:
            for child in self.children:
                yield from child.leaves

    @property
    def isRoot(self) -> bool:
        return not self.parent

    @property
    def isLeaf(self) -> bool:
        return not self.children

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

    # NOTE: We use an accesor as filesystem nodes do not store children
    # in memory.
    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, children: list['Node']):
        self.clear()
        for child in children:
            self.add(child)

    def setMeta(self, meta):
        self.meta = meta
        return self

    def setData(self, data):
        self.data = data
        return self

    def on(self, event: str, callback: Callable):
        """Binds an event handler (`callback`) to the given even path. A
        handler can only be bound once."""
        self.handlers = self.handlers or {}
        handlers = self.handlers.setdefault(event, [])
        assert callback not in handlers, f"Registering callback twice in node {self}: {callback}"
        handlers.append(callback)
        return self

    def off(self, event: str, callback: Callable):
        """Unbinds an event handler (`callback`) from the given even path,
        which requires the event handler to have previously been bound."""
        handlers = self.handlers.get(event) if self.handlers else None
        if handlers:
            assert callback not in handlers, f"Callback not registered in node {self}: {callback}"
            handlers.remove(callback)
        return self

    def trigger(self, event: str, data=None) -> Event:
        """Creates a new event with the given name and data, dispatching it
        up."""
        event = Event(event, data)
        return self._dispatchEvent(event)

    def _dispatchEvent(self, event: Event):
        """Dispatches the event in this node, triggering any registered callback
        and propagating the even to the parent."""
        handlers = self.handlers.get(event.name, ()) if self.handlers else ()
        event.target = self
        for h in handlers:
            if h(event) is False:
                event.stop()
                break
        if event.isPropagating and self.parent:
            self.parent._dispatchEvent(event)
        return event

    def append(self, node: 'Node') -> 'Node':
        return self.add(node)

    def add(self, node: 'Node') -> 'Node':
        if node not in self.children:
            node.parent = self
            self.children.append(node)
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

    def remove(self, node: 'Node'):
        assert node.parent == self
        self._children.remove(node)
        node.parent = None
        return node

    def detach(self) -> 'Node':
        if self.parent:
            self.parent.remove(self)
        return self

    def index(self, node=None) -> Optional[int]:
        if not node:
            return self.parent.index(self) if self.parent else None
        else:
            return self._children.index(node)

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

    def touch(self):
        """Marks this node as changed, capturing the timestamp and
        propagating the change up."""
        changed = time.time()
        self.changed = changed
        for _ in self.ancestors:
            _.childChanged = max(changed, _.childChanged)
        return self

    def walk(self) -> Iterable['Node']:
        yield self
        for c in self.children:
            yield from c.walk()

    def copy(self, depth=-1):
        """Does a deep copy of this node. If a depth is given, it will
        stop at the given depth."""
        node = self.__class__(self.name)
        self.attributes = {k: v for k, v in self.attributes.items()}
        if depth != 0:
            for child in self._children:
                node.append(child.copy(depth - 1))
        return node

    def toPrimitive(self):
        return {
            "id": self.id,
            "meta": self.meta,
            "children": [_.toPrimitive() for _ in self.children],
        }

    def __repr__(self):
        name = f"name={self.name} id={self.id}" if self._name else f"id={self.id}"
        return f"<{self.__class__.__name__} {name} {f'…{len(self.children)}>' if self.children else '/>'}"

    def toASCII(self) -> str:
        return toASCII(self)


class NamedNode(Node):
    """Named nodes make trees where children are named instead
    of being anonymous and indexed. This structure makes it easy to
    implement registries and filesystem-like hierarchies."""

    def __init__(self, name: Optional[str] = None, parent: Optional['NamedNode'] = None):
        super().__init__(name)
        self._children: dict[str, 'NamedNode'] = dict()
        self.parent: Optional['NamedNode'] = None
        # We bind the node if a parent was set
        if parent:
            assert name, "Cannot set a parent without setting a name."
            parent.set(name, self)

    @property
    def children(self):
        return list(self._children.values())

    @children.setter
    def children(self, children):
        self.clear()
        for child in children:
            assert child.name, "When setting a name, children must already be named"
            self.set(child.name, child)

    def rename(self, name: str):
        if self.parent:
            self.parent.set(name, self)
        else:
            self._name = name
        return self

    def removeAt(self, name: str):
        raise NotImplementedError

    def clear(self):
        return [child.detach() for child in self.children]

    def remove(self, node: 'NamedNode'):
        assert node.parent == self
        assert self._children[node.name] == node
        del self._children[node.name]
        node.parent = None
        return node

    def detach(self):
        return self.parent.remove(self) if self.parent else self

    def add(self, node: 'Node') -> 'NamedNode':
        assert isinstance(
            node, NamedNode), "NamedNode can only take a compatible subclass"
        assert node.name, "Node can only be added if named"
        return self.set(node.name, node)

    def set(self, key: str, node: 'NamedNode') -> 'NamedNode':
        assert key, f"Cannot set node with key '{key}' in: {self.path}"
        # We remove the previous child, if any
        previous = self._children.get(key)
        if previous:
            previous.detach()
        # We bind the node first
        node._name = key
        node.parent = self
        # And we assign it
        self._children[key] = node
        return node

    def has(self, key: str) -> bool:
        return key in self._children

    def get(self, key: str) -> Optional['NamedNode']:
        return self._children[key] if key in self._children else None

    def resolve(self, path: str, strict=True) -> Optional['NamedNode']:
        context: NamedNode = self
        for k in path.split(self.SEPARATOR):
            if not context.has(k):
                return None if strict else context
            else:
                context = cast(NamedNode, context.get(k))
        return context

    def ensure(self, path: str) -> 'NamedNode':
        context: NamedNode = self
        for k in path.split(self.SEPARATOR):
            if not context:
                break
            elif not k:
                # TODO: This should be a warning here
                continue
            elif not context.has(k):
                context = context.set(k, self.__class__(name=k))
                assert not context or context.parent, f"Created node should have parent {context}"
            else:
                context = cast(NamedNode, context.get(k))
                assert not context or context.parent, f"Retrieved node should have parent {context}"
        return context

    def walk(self) -> Iterable['NamedNode']:
        yield self
        for c in self.children:
            yield from c.walk()

    def toPrimitive(self):
        res = super().toPrimitive()
        res["name"] = self.name
        return res

    def __getitem__(self, name: str):
        return self.children[name]

    def __str__(self):
        return f"<NamedNode:{self.name}:{self.id} +{len(self.children)}>"


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
