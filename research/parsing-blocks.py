from nota.utils.parsing import Fragment, Pattern, parse, indentation
from nota.format.nd import structure, tree
import re


patterns = {
        "cell" : Pattern(
            re.compile(r"(?P<indent>[ \t]*)(#[ ]*--[ \t]*(?P<header>[^\n]*)\n)(?P<body>[ \t]*#[^\n]*\n)*", re.MULTILINE)),
        "def": Pattern(
            re.compile(r"(?P<indent>[ \t]*)(?P<type>class|def)[ ]+(?P<name>[^ \t\n]+)")),

        "assign": Pattern(
            re.compile(r"(?P<indent>[ \t]*)(?P<lhs>\w[^=\n]*)[ ]+="))
 }

text = open(__file__.replace(".py", ".txt")).read()
for name, match  in parse(patterns, text):
    indent = indentation(match.match.group("indent"))

node = tree(structure(text, patterns))
print (node.toTDoc())

# EOF
