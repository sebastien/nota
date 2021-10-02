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
        self.meta: dict[str, Any] = {}
        self.handlers: Optional[dict[str, Callable]] = None
        self.changed = time.time()
        self.childChanged = self.changed

    @property
    def name(self):
        return self._name or self.id

    @property
    def root(self) -> Optional['Node']:
        root = None
        while node := self.parent:
            root = node
        return root

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

    def remove(self, node: 'Node'):
        assert node.parent == self
        self._children.remove(node)
        node.parent = None
        return node

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

    def toPrimitive(self):
        return {
            "id": self.id,
            "meta": self.meta,
            "children": [_.toPrimitive() for _ in self.children],
        }

    def __str__(self):
        return f"<{self.__class__.__name__} id={self.id} {f'…{len(self.children)}>' if self.children else '/>'}"

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