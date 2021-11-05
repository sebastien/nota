import sys
import os
import re
import subprocess
from typing import Optional, Iterable
from ..model import NotePath, Reference
from ..format import nd
from ..utils import cli
from ..operations import Operations
from ..store import Store
from ..utils import indexing

ENCODING = sys.stdout.encoding

# --
# # Commands
#
# This is the main part of the module where we implement each command, along
# with its documentation and command line arguments.


class Context:

    def __init__(self):
        self.do = Operations(Store())
        self.editor = os.environ["EDITOR"] if "EDITOR" in os.environ else "vi"

    def edit(self, path: str):
        with self.do.editNote(path) as p:
            subprocess.run([self.editor, str(p)])

    def err(self, message: str):
        sys.stdout.write("[!] ")
        sys.stdout.write(message)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def out(self, message: str):
        sys.stdout.write(message)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def getNote(self, nameish: str) -> str:
        if RE_INT.match(nameish):
            notes = list(self.do.listNotes())
            indice = max(1, int(nameish)) - 1
            if indice >= 0 and indice < len(notes):
                return notes[indice]
            else:
                raise IndexError
        else:
            return nameish

    def displayEnumeratedList(self, items: Iterable[str]):
        if not items:
            self.err(f"No item found")
        else:
            for i, item in enumerate(items):
                self.out(f"[{i+1:2d}] {item}")


RE_INT = re.compile("^\d+$")


@cli.command("NAME", alias="e|ed")
def edit(context, name: str):
    """XXXX"""
    context.edit(context.getNote(name))


@cli.command("QUERY?", alias="l|ls")
def _list(context, query: Optional[str] = None):
    """XXXX"""
    context.displayEnumeratedList(context.do.listNotes())


@cli.command("QUERY", alias="q|s|search")
def find(context, query: str):
    """XXXX"""
    idx: dict[str, list[indexing.Entry]] = {}
    for note in context.do.listNotes():
        text = context.do.readNote(note)
        print(text)
        idx = indexing.index(text, note, idx)
    for score, entry in indexing.find(idx, query):
        context.out(
            f"[{round(score*100):3d}%] {entry.source}: {entry.original}")


@cli.command("TERM*", alias="i")
def index(context, query: str):
    """Lists all the entities defined in the content"""
    idx: dict[str, list[indexing.Entry]] = {}
    refs: dict[str, tuple[Reference, list[NotePath]]] = {}
    for note in context.do.listNotes():
        text = context.do.readNote(note)
        for ref in nd.references(text):
            if ref.value in refs:
                refs[ref.value][1].append(note)
            else:
                refs[ref.value] = (ref, [note])
    for key in sorted(refs):
        print(key, len(refs[key][1]), [_ for _ in refs[key][1]])


@ cli.command(alias="q|s", options=[
    cli.option("-c", "--created", help="Show notes by creation date"),
    cli.option("-r", "--read", help="Show recently accessed notes"),
    cli.option("-w", "--write", help="Show recently written/edited notes"),
    cli.option("-a", "--ascending", help="Shows results in ascending order"),
])
def recent(context, query):
    """Shows the recently accessed or edited notes."""
    pass


def run(args=sys.argv[1:]):
    return cli.run(args, name="nota", context=Context())


if __name__ == "__main__":
    sys.exit(run())

# EOF
