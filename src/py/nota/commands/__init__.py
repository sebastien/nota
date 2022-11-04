import sys
import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Iterable, Union
from ..model import NotePath, Reference
from ..format import nd
from difflib import get_close_matches
from ..utils import cli
from ..operations import CompositeOperator, LocalOperator, NOTE_TEMPLATE
from ..utils import indexing

ENCODING = sys.stdout.encoding
RE_NUMBER = re.compile(r"\d+")

# --
# # Commands
#
# This is the main part of the module where we implement each command, along
# with its documentation and command line arguments.


@contextmanager
def mktemp(*, prefix=Optional[str], contents: Optional[str] = None) -> str:
    fd, path = tempfile.mkstemp(suffix=".nd", prefix=prefix or "nota-", text=True)
    if contents:
        os.write(fd, bytes(contents, "utf8"))
    os.close(fd)
    try:
        yield path
    except Exception as e:
        raise e
    finally:
        os.unlink(path)


def key(text: str) -> str:
    return text.lower().strip()


class Color:
    RESET = "[0m[0m"
    LIGHT_GRAY = "[0m[00;37m"
    DARK_GRAY = "[0m[01;30m"
    BLACK = "[0m[00;30m"
    BLACK_BOLD = "[0m[01;30m"
    RED = "[0m[00;31m"
    RED_BOLD = "[0m[01;31m"
    GREEN = "[0m[00;32m"
    GREEN_BOLD = "[0m[01;32m"
    BLUE = "[0m[00;34m"
    BLUE_BOLD = "[0m[01;34m"
    MAGENTA = "[0m[00;35m"
    MAGENTA_BOLD = "[0m[01;35m"
    CYAN = "[0m[00;35m"
    CYAN_BOLD = "[0m[01;35m"
    YELLOW = "[0m[01;33m"
    YELLOW_BOLD = "[0m[01;33m"
    WHITE = "[0m[00;37m"
    WHITE_BOLD = "[0m[01;37m"


@dataclass
class Match:
    exact: Optional[str]
    like: list[str] = field(default_factory=list)
    subset: list[str] = field(default_factory=list)
    approximate: list[str] = field(default_factory=list)

    @property
    def head(self) -> Optional[str]:
        l = self.all
        return l[0] if l else None

    @property
    def all(self) -> list[str]:
        return (
            ([self.exact] if self.exact else [])
            + self.like
            + self.subset
            + self.approximate
        )


class Context:
    def __init__(self):
        self.do = CompositeOperator(LocalOperator())
        self.editor = os.environ["EDITOR"] if "EDITOR" in os.environ else "vi"

    def edit(self, path: NotePath) -> bool:
        contents = self.do.readNote(path) or NOTE_TEMPLATE
        # nosec - this is fine, as we're calling the user editor and it's
        with mktemp(
            prefix=f"nota-{os.path.basename(path).split('.')[0]}-", contents=contents
        ) as temp:
            subprocess.run([self.editor, temp], shell=False)
            with open(temp, "rt") as f:
                updated = f.read()
            if updated == contents:
                self.out(f" {Color.DARK_GRAY}No change to {path}{Color.RESET}")
                return False
            else:
                if self.do.writeNote(path, updated, contents):
                    self.out(f"Updated {Color.GREEN}{path}{Color.RESET}")
                    return True
                else:
                    self.error(f"Could not update {Color.RED}{path}{Color.RESET}")
                    return False

    def err(self, message: str):
        sys.stdout.write("[!] ")
        sys.stdout.write(message)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def info(self, message: str):
        return self.out(message)

    def tip(self, message: str):
        return self.out(f" 👉  {Color.BLUE}{message}{Color.RESET}")

    def out(self, message: str):
        sys.stdout.write(message)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def matchNotesWithName(self, name: str, notes: list[str]) -> Match:
        exact = []
        like = []
        subset = []
        rest = []
        for n in notes:
            if n == name:
                exact.append(n)
            elif key(n) == key(name):
                like.append(n)
            elif key(name) in key(n) or key(name) in key(n):
                subset.append(n)
            else:
                rest.append(n)
        return Match(
            exact[0] if exact else None, like, subset, get_close_matches(name, rest)
        )

    def findNodes(self, query: list[str]) -> Match:
        notelist = sorted(list(self.do.listNotes()))
        match = None
        for q in query:
            if isinstance(q, int) or RE_NUMBER.match(q):
                indice = max(1, int(q)) - 1
                if indice >= 0 and indice < len(notelist):
                    return Match(notelist[indice])
            match = self.matchNotesWithName(q, notelist)
            notelist = match.all
        return match or Match(None, approximate=notelist)

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

    #     def getNoteMetadata( self, name:str ): NoteMetadata
    #         pass

    def highlight(
        self,
        text: str,
        match: Optional[Union[list[str], str]] = None,
        color: str = Color.YELLOW,
    ) -> str:
        if match:
            # NOTE: This is not the right way to do it, but it works
            # for basic cases
            for m in (
                (match,) if isinstance(match, str) else sorted(match, reverse=True)
            ):
                if m in text:
                    return text.replace(m, f"{color}{m}{Color.RESET}")
            return text
        else:
            return f"{color}{text}{Color.RESET}"

    def enumerateNotes(self, notes: Iterable[str], match: Optional[str] = None):
        if not notes:
            self.err(f"No note found")
        else:
            all_notes = [_ for _ in notes]
            width = max(len(_) for _ in all_notes)
            for i, note in enumerate(all_notes):
                self.out(
                    f"[{i+1:2d}] {self.highlight(note.ljust(width), match, Color.GREEN)} {Color.DARK_GRAY}{self.do.pathNote(note) or ''}{Color.RESET}"
                )


RE_INT = re.compile("^\d+$")

# TODO: Create should craeate something new
@cli.command("NAME", alias="c|new")
def create(context, name: str):
    """Creates a new note with the given name, which can contains '/'
    as path separator."""
    if RE_NUMBER.match(name):
        return context.error(f"Notes names cannot be a number: {name}")
    elif context.do.hasNote(name):
        context.info(f"Note {name} already exist, editing")
        return edit(context, name)
    else:
        return context.edit(name)


# TODO:  Edit should search if not alreayd available
# TODO: Create should craeate something new
@cli.command("NAME*", alias="e|ed")
def edit(context, name: list[str]):
    """Edits the given note"""
    match = context.findNodes(name)
    query = " ".join(name)
    if not name:
        context.enumerateNotes(context.do.listNotes())
    elif match.exact:
        context.info(f"Picked matching note {Color.BLUE}{match.exact}{Color.RESET}")
        context.edit(match.exact)
    elif len(match.subset) == 1:
        context.info(
            f"Picked close match {Color.BLUE}{match.subset[0]}{Color.RESET} for {Color.WHITE_BOLD}{query}{Color.RESET}"
        )
        if context.edit(note := match.subset[0]):
            context.info(f" ✍️  {Color.BLUE}Updated note{Color.RESET} {note}")
        else:
            context.info(f"{Color.DARK_GRAY}No change recorded.{Color.RESET}")
    elif len(match.like) == 1:
        context.info(
            f"Picked close match {Color.BLUE}{match.like[0]}{Color.RESET} for {Color.WHITE_BOLD}{query}{Color.RESET}"
        )
        context.edit(match.like[0])
    elif not match.all:
        context.info(
            f"━━━━ Could not find any match for {Color.GREEN_BOLD}{query}{Color.RESET}."
        )
        context.enumerateNotes(context.do.listNotes(), name)
    elif len(match.all) == 1:
        context.info(f"Editing close match '{match.head}' for '{query}'")
        context.edit(match.head)
    else:
        context.out(
            f"━━━━ Could not find an exact match for {Color.GREEN_BOLD}{query}{Color.RESET}, here are close matches:"
        )
        context.enumerateNotes(match.all, name)
        context.tip(f"Add the item number to the command to edit that note")


@cli.command("QUERY*", alias="l|ls")
def _list(context, query: Optional[str] = None):
    """Lists the available notes"""
    # TODO: Display note udpated
    context.enumerateNotes(context.findNodes(query).all, query)


@cli.command("QUERY", alias="q|s|search")
def find(context, query: str):
    """Find notes that contain data that matches the query"""
    idx: dict[str, list[indexing.Entry]] = {}
    # TODO: We could group by note
    # [ 40%] tools/nix-containers Package](https://gist.github.com/CMCDragonkai/b2337658ff40294d251cc79d12b34224),
    # [ 40%] tools/nix "https://github.com/NixOS/nixpkgs/archive/3590f02e7d5760e52072c1a729ee2250b5560746.tar.gz")
    #                  [NixOps](https://github.com/NixOS/nixops)
    # [100%] tools/git git
    #                  Git](https://cuddly-octo-palm-tree.com/posts/2021-09-19-git-elements/)
    #                  [SO](https://stackoverflow.com/questions/35738790/how-to-close-a-branch-in-git#35738879)
    # [100%] tools/nix-tips git

    for note in context.do.listNotes():
        text = context.do.readNote(note)
        idx = indexing.index(text, note, idx)
    for score, entry in indexing.find(idx, query):
        context.out(f"[{round(score*100):3d}%] {entry.source} {entry.original}")


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


@cli.command(
    alias="q|s",
    options=[
        cli.option("-c", "--created", help="Show notes by creation date"),
        cli.option("-r", "--read", help="Show recently accessed notes"),
        cli.option("-w", "--write", help="Show recently written/edited notes"),
        cli.option("-a", "--ascending", help="Shows results in ascending order"),
    ],
)
def recent(context, query):
    """Shows the recently accessed or edited notes."""
    pass


def run(args=sys.argv[1:]):
    return cli.run(args, name="nota", context=Context())


if __name__ == "__main__":
    sys.exit(run())

# EOF
