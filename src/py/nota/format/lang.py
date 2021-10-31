from pathlib import Path
from typing import Optional, Callable, Any
from tree_sitter import Language, Node, Tree as TSBaseParser

# --
# # Programming Language Parsing
#
# This module uses Tree Sitter to take source code an identify the following:
#
# - The list of declarations (symbols) defined in the source code.
# - The dependencies of each declaration, ie. which symbols it uses.


# --
# Tree-Sitter needs to build binaries first, which is
# what we are doing here.

# NOTE: This only works when building from source
BASE_PATH = Path(__file__).parent.parent.parent.parent.parent
DEPS_PATH = BASE_PATH.joinpath("deps")
BUILD_PATH = BASE_PATH.joinpath("build")
LIBRARY_PATH = BUILD_PATH.joinpath("c'python-treesitter.so")
LANGUAGES = ["python", "javascript", "go"]
Language.build_library(
    str(LIBRARY_PATH),
    [f"{DEPS_PATH}/tree-sitter-{_}" for _ in LANGUAGES]
)


def extract(node: Node, text: str) -> str:
    return text[node.start_byte:node.end_byte]


# --
# ## Language Parser

class TSParser:
    def __init__(self, lang: str):
        self.lang = lang
        self.parser = TSBaseParser()
        self.tsLang = Language(LIBRARY_PATH, lang)
        self.parser.set_language(self.tsLang)

    def parse(self, code: str) -> Node:
        return self(code).root_node

    def sexp(self, code: str) -> str:
        return self.parse(code).sexp()

    def query(self, query: str, code: str) -> dict[str, str]:
        return dict((k, extract(v, code)) for v, k in self.tsLang.query(
            query).captures(self.parse(code)))

    def __call__(self, value: str) -> Tree:
        return self.parser.parse(bytes(value, "utf8"))


class Symbol:
    def __init__(self, name: str, parent: Optional[str] = None, scope: Optional['Scope'] = None):
        self.name = name
        self.parent = parent
        self.scope: Optional[Scope] = scope

    @property
    def range(self) -> tuple[int, int]:
        return self.scope.range if self.scope else (0, 0)

    # FIXME: This is costly so should be cached
    @property
    def inputs(self) -> set:
        refs = set()

        def walk(scope: Scope, depth: int):
            for ref, _ in scope.refs.items():
                if not scope.isDefined(ref):
                    refs.add(ref)
        if self.scope:
            self.scope.walk(walk)
        return refs

    def __repr__(self):
        return f"(symbol {self.name} {self.range} {self.inputs})"

    def asDict(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            parent=self.parent,
            range=self.range,
            inputs=[_ for _ in self.inputs],
            scope=self.scope.asDict() if self.scope else None,
        )


class Scope:
    def __init__(self, parent: Optional['Scope'] = None, type: Optional[str] = None):
        self.name: Optional[str] = None
        self.slots: dict[str, str] = {}
        self.refs: dict[str, str] = {}
        self.children: list[Scope] = []
        self.parent: Optional[Scope] = parent
        self.range: tuple[int, int] = (0, 0)
        self.type = type if type else "block"
        if parent:
            parent.children.append(self)

    @ property
    def qualname(self) -> Optional[str]:
        parent_name = self.parent.qualname if self.parent else None
        return None if not self.name else f"{parent_name}.{self.name}" if parent_name else self.name

    @ property
    def defs(self):
        return [_ for _ in self.slots]

    def isDefined(self, name: str) -> bool:
        return self.slots.get(name) == "def" or bool(self.parent and self.parent.isDefined(name))

    def derive(self, type: Optional[str] = None, range: Optional[tuple[int, int]] = None, name: Optional[str] = None) -> 'Scope':
        res = Scope(self)
        if name:
            res.name = name
        if type:
            res.type = type
        if range:
            res.range = range
        return res

    def walk(self, functor: Callable[[Node, int], None], depth: int = 0):
        functor(self, depth)
        for _ in self.children:
            _.walk(functor, depth+1)

    def asDict(self) -> dict[str, Any]:
        return dict(
            type=self.type,
            name=self.name,
            qualname=self.qualname,
            range=self.range,
            slots=self.slots,
            refs=self.refs,
            children=[_.asDict() for _ in self.children]
        )

# --
# ## Tree Processor


class TSProcessor:
    """Base class to write TreeSitter processors."""

    ALIASES = {
        "+": "plus",
        "-": "minus",
        "*": "times",
        "/": "slash",
        "**": "timetime",
        "^": "chevron",
    }

    @staticmethod
    def NodeKey(node: Node) -> str:
        """Returns a unique identifier for a given node. Unicity is within
        a tree."""
        return f"{node.type}:{node.start_byte}:{node.end_byte}"

    def __init__(self, parser: TSParser):
        self.parser = parser
        self.code = ""
        self.init()

    def init(self):
        pass

    def extract(self, node: Node) -> str:
        return extract(node, self.code)

    def on_node(self, node: Node, value: str, depth: int, breadth: int):
        print(f"node:{node.type} {depth}+{breadth}: {value}")

    def on_start(self):
        pass

    def on_end(self):
        pass

    def __call__(self, code: str):
        self.code = code
        tree = self.parser(code)
        cursor = tree.walk()
        depth = 0
        breadth = 0
        visited = set()
        on_exit = {}
        # NOTE: Not sure if we should call init there
        self.init()
        self.on_start()
        # This implements a depth-first traversal of the tree
        while True:
            node = cursor.node
            key = self.NodeKey(node)
            method_name = f"on_{node.type}"
            processor = getattr(self, method_name) if hasattr(
                self, method_name) else self.on_node
            exit_functor = processor(
                node, extract(node, code), depth, breadth)
            # We use functors as exit functions
            if exit_functor:
                if node.child_count > 0:
                    on_exit[key] = exit_functor
                else:
                    exit_functor(node)
            visited.add(sefl.NodeKey(node))
            if cursor.goto_first_child():
                breadth = 0
                depth += 1
            elif cursor.goto_next_sibling():
                breadth += 1
            else:
                # When we go up, we need to be careful.
                previous_key = self.NodeKey(cursor.node)
                while depth > 0:
                    previous_node = cursor.node
                    breadth = 0
                    cursor.goto_parent()
                    current_key = self.NodeKey(cursor.node)
                    if current_key == previous_key:
                        break
                    else:
                        # This is the on exit on the way up
                        if previous_key in on_exit:
                            on_exit[previous_key](previous_node)
                            del on_exit[previous_key]
                        previous_key = current_key
                    depth -= 1
                    # We skip the visited nodes
                    while (previous_key := self.NodeKey(cursor.node)) in visited:
                        # This is the on exit on the way to the next sibling
                        if previous_key in on_exit:
                            on_exit[previous_key](cursor.node)
                            del on_exit[previous_key]
                        if cursor.goto_next_sibling():
                            breadth += 1
                        else:
                            break
                    if self.NodeKey(cursor.node) not in visited:
                        break
                if self.NodeKey(cursor.node) in visited:
                    return self.on_end()

# --
# ## Global Parsers


def parse(path: Union[str, Path]):
    for p in path:
        print(p)


if __name__ == "__main__":
    import sys
    parse(sys.argv[1:])

# EOF
