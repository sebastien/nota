from tree_sitter import Language, Node, Tree, Parser
from pathlib import Path

# --
# Ensures that tree-sitter is working properly and that the grammars
# are also working properly.

# FROM: https://github.com/tree-sitter/py-tree-sitter

Language.build_library(
    # Store the library in the `build` directory
    'build/treesitter.so',

    # Include one or more languages
    [
        '.deps/src/tree-sitter-python',
    ]
)
PY_LANGUAGE = Language('build/treesitter.so', 'python')

# --
# ## Tree Processor


def node_key(node: Node) -> str:
    """Returns a unique identifier for a given node. Unicity is within
    a tree."""
    return f"{node.type}:{node.start_byte}:{node.end_byte}"


class Processor:
    """Base class to write TreeSitter processors."""

    ALIASES = {
        "+": "plus",
        "-": "minus",
        "*": "times",
        "/": "slash",
        "**": "timetime",
        "^": "chevron",
    }

    def __init__(self):
        self.init()
        self.source:bytes = b""

    def init(self):
        pass

    def text(self, node: Node) -> str:
        return str(self.source[node.start_byte:node.end_byte],"utf8")


    def on_node(self, node: Node, value:str, depth: int, breadth: int):
        print(f"node:{node.type} {depth}+{breadth}")

    def on_start(self):
        pass

    def on_end(self):
        pass

    def process(self, tree:Tree, source:bytes):
        cursor = tree.walk()
        self.source = source
        depth = 0
        breadth = 0
        visited = set()
        on_exit = {}
        # NOTE: Not sure if we should call init there
        self.on_start()
        # This implements a depth-first traversal of the tree
        while True:
            node = cursor.node
            key = node_key(node)
            method_name = f"on_{node.type}"
            processor = getattr(self, method_name) if hasattr(
                self, method_name) else self.on_node
            exit_functor = processor( node, self.text(node), depth, breadth)
            # We use functors as exit functions
            if exit_functor:
                if node.child_count > 0:
                    on_exit[key] = exit_functor
                else:
                    exit_functor(node)
            visited.add(node_key(node))
            if cursor.goto_first_child():
                breadth = 0
                depth += 1
            elif cursor.goto_next_sibling():
                breadth += 1
            else:
                # When we go up, we need to be careful.
                previous_key = node_key(cursor.node)
                while depth > 0:
                    previous_node = cursor.node
                    breadth = 0
                    cursor.goto_parent()
                    current_key = node_key(cursor.node)
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
                    while (previous_key := node_key(cursor.node)) in visited:
                        # This is the on exit on the way to the next sibling
                        if previous_key in on_exit:
                            on_exit[previous_key](cursor.node)
                            del on_exit[previous_key]
                        if cursor.goto_next_sibling():
                            breadth += 1
                        else:
                            break
                    if node_key(cursor.node) not in visited:
                        break
                if node_key(cursor.node) in visited:
                    return self.on_end()


class StructureProcessor(Processor):

    def init(self):
        self.mode = None
        self.defs = set()
        self.refs = set()

    # --
    # ### Definitions

    def on_function_definition(self, node: Node, value: str, depth: int, breadth: int):
        return self.on_definition(node, value, depth, breadth, "function")

    def on_class_definition(self, node: Node, value: str, depth: int, breadth: int):
        return self.on_definition(node, value, depth, breadth, "class")

    def on_assignment(self, node: Node, value: str, depth: int, breadth: int):
        # TODO: We're not handling the asssignment properly, ie.
        # class A:
        #   STATIC = 1
        #   SOMEVAR[1] = 10
        #   A,B = (10, 20)
        name_node = node.child_by_field_name("left")
        name = self.extract(name_node) if name_node else None
        self.scope = self.scope.derive(
            type=type, range=(node.start_byte, node.end_byte), name=name)

        def on_exit(_, self=self):
            self.scope = self.scope.parent
        return on_exit

    def on_definition(self, node: Node, value: str, depth: int, breadth: int, type: str = "block"):
        name_node = node.child_by_field_name("name")
        name = self.extract(name_node) if name_node else None
        self.scope = self.scope.derive(
            type=type, range=(node.start_byte, node.end_byte), name=name)
        self.mode = "def"

        def on_exit(_, self=self):
            self.scope = self.scope.parent
        return on_exit

    # --
    # ### References
    def on_identifier(self, node: Node, value: str, depth: int, breadth: int):
        if value not in self.scope.slots:
            if self.mode == "ref":
                self.scope.refs[value] = self.mode
            else:
                self.scope.slots[value] = self.mode

    def on_return_statement(self, node: Node, value: str, depth: int, breadth: int):
        return self.on_statement(node, value, depth, breadth)

    # NOTE: Assignments are contained in expressions, so maybe not ideal
    # def on_expression_statement(self, node: Node, value: str, depth: int, breadth: int):
    #     print("ON:EXPR", node.sexp())
    #     if self.scope.type != "module":
    #         return self.on_statement(node, value, depth, breadth)
    #     else:
    #         self.scope = self.scope.derive(
    #             type="expression", range=(node.start_byte, node.end_byte))
    #         self.mode = "def"
    #         self.on_statement(node, value, depth, breadth)

    #         def on_exit(_, self=self):
    #             self.scope = self.scope.parent
    #         return on_exit

    def on_statement(self, node: Node, value: str, depth: int, breadth: int):
        mode = self.mode
        self.mode = "ref"

        def on_exit(_):
            self.mode = mode
        return on_exit

    def on_binary_operator(self, node: Node, value: str, depth: int, breadth: int):
        mode = self.mode
        self.mode = "ref"

        def on_exit(_):
            self.mode = mode
        return on_exit

    def on_node(self, node: str, value: str, depth: int, breadth: int):
        pass


parser = Parser()
parser.set_language(PY_LANGUAGE)
with open(Path(__file__), "rb") as f:
    text = f.read()
    tree = parser.parse(text)

StructureProcessor().process(tree, text)
# EOF
