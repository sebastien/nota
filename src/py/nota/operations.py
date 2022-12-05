from typing import (
    ContextManager,
    Optional,
    Generic,
    TypeVar,
    Optional,
    Iterable,
    Iterator,
    Callable,
    Union,
)
from pathlib import Path
from .model import Note, NotePath
import os

T = TypeVar("T")

NOTE_TEMPLATE = """
# Note title

--- tags: meta, code design

Microformats:

- A `#hashtag` to reference a topic
- An `[internal reference]`
- Things `@thing`
- Terms `_term_`
- Date `2021-09-09`
- Times `10:00:20`
- Datetimes `2021-09-09T10:00:20`

Bookmarks:

--- url
https://github.com/sebastien/nota
Write some description and just mention
the #cool #tag

Just make sure you close with a `---`
---


--- snippet

```
Put your code in there
```

and  you can interleave with comments and description

"""


class OperationException(Exception):
    pass


class NoteChangedError(OperationException):
    def __init__(self, path: str):
        super(f"Note has has change: {path}")
        self.path = path


class Operator:
    def hasNote(self, path: NotePath) -> bool:
        raise NotImplementedError

    def readNote(self, path: NotePath) -> Optional[str]:
        raise NotImplementedError

    def writeNote(self, path: NotePath, updated: str, original: Optional[str]) -> bool:
        raise NotImplementedError

    def pathNote(self, path: NotePath) -> Optional[str]:
        raise NotImplementedError

    def listNotes(self) -> Iterable[NotePath]:
        raise NotImplementedError

    def searchNotesTitle(self, query: str) -> Iterable[NotePath]:
        raise NotImplementedError

    def searchNotesContent(self, query: str) -> Iterable[NotePath]:
        raise NotImplementedError


class Store:
    def exists(self, path: NotePath) -> bool:
        """Tells if the given path exists"""
        raise NotImplementedError

    def read(self, path: NotePath) -> Optional[str]:
        """Reads the data from the given path."""
        raise NotImplementedError

    def write(self, path: NotePath, updated: str, original: Optional[str]) -> bool:
        """Writes the data to the given path."""
        raise NotImplementedError

    def list(self) -> Iterator[NotePath]:
        """Lists all the notes in the store"""
        raise NotImplementedError

    def pathNote(self, note: NotePath) -> str:
        raise NotImplementedError

    def notePath(self, path: str) -> NotePath:
        raise NotImplementedError


class LocalStore(Store):
    """Implements a local store"""

    EXTENSION = ".nd"

    def __init__(
        self,
        base: Union[Path, str] = Path(
            os.path.expandvars(os.getenv("NOTA_HOME", "$HOME/.nota"))
        ),
    ):
        self.base: Path = Path(base).absolute()
        if not self.base.exists():
            raise RuntimeError(f"Store path does not exsits: {base}")

    def exists(self, path: NotePath) -> bool:
        """Tells if the given path exists"""
        return (self.base / path).exists()

    def read(self, path: NotePath) -> Optional[str]:
        """Reads the data from the given path."""
        actual = self.pathNote(path)
        if os.path.exists(actual):
            with open(actual, "rt") as f:
                return f.read()
        else:
            return None

    def write(
        self, path: NotePath, contents: str, original: Optional[str] = None
    ) -> bool:
        """Writes the contents to the note."""
        actual_path = self.pathNote(path)
        if original and os.path.exists(actual_path):
            with open(actual_path, "rt") as f:
                if f.read() != original:
                    raise NoteChangedError(path)

        with open(actual_path, "wt") as f:
            f.write(contents)
        return True

    def list(self) -> Iterator[str]:
        # FIXME: This does not make sense, what if path is partial?
        for root, _, files in os.walk(self.base):
            for f in files:
                if f.endswith(self.EXTENSION):
                    # FIXME: Is we should make sure this is really relative to the
                    yield self.notePath(f"{root}/{f}")

    def pathNote(self, note: NotePath) -> str:
        return str(self.base / f"{note}{self.EXTENSION}")

    def notePath(self, path: str) -> NotePath:
        res = str(path)
        base = f"{self.base}/"
        if not path.startswith(base):
            raise RuntimeError("Path should start with '{base}', got: {path}")
        if not path.endswith(self.EXTENSION):
            raise RuntimeError("Path should end with '{self.EXTENSION}', got: {path}")
        return res[len(base) : -len(self.EXTENSION)]


class LocalOperator(Operator):
    def __init__(self, store: Optional[Store] = None):
        self.store: Store = store if store else LocalStore()

    def hasNote(self, path: NotePath) -> bool:
        return self.store.exists(path)

    def readNote(self, path: NotePath) -> Optional[str]:
        return self.store.read(path)

    def writeNote(self, path: NotePath, updated: str, original: Optional[str]) -> bool:
        return self.store.write(path, updated, original)

    def listNotes(self) -> Iterable[NotePath]:
        return self.store.list()

    def pathNote(self, path: NotePath) -> Optional[str]:
        return self.store.pathNote(path)


# --
# ## Git Operator
#
# The git operator is used to implement effects on the actions defined
# in Nota.
class GitOperator(Operator):
    def __init__(self):
        pass

    def hasNote(self, path: NotePath) -> bool:
        raise NotImplementedError

    def readNote(self, path: NotePath) -> str:
        raise NotImplementedError

    def listNotes(self) -> Iterable[NotePath]:
        raise NotImplementedError

    def searchNotesTitle(self, query: str) -> Iterable[NotePath]:
        raise NotImplementedError

    def searchNotesContent(self, query: str) -> Iterable[NotePath]:
        raise NotImplementedError


class CompositeOperator(Operator):
    def __init__(self, *delegates: Operator):
        self.delegates = delegates

    def hasNote(self, path: NotePath) -> bool:
        return [_.hasNote(path) for _ in self.delegates][0]

    def readNote(self, path: NotePath) -> Optional[str]:
        return [_.readNote(path) for _ in self.delegates][0]

    def writeNote(self, path: NotePath, updated: str, original: Optional[str]) -> bool:
        return [_.writeNote(path, updated, original) for _ in self.delegates][0]

    def listNotes(self) -> Iterable[NotePath]:
        return [_.listNotes() for _ in self.delegates][0]

    def pathNote(self, path: NotePath) -> Optional[str]:
        return [_.pathNote(path) for _ in self.delegates][0]

    def searchNotesTitle(self, query: str) -> Iterable[NotePath]:
        return [_.searchNotesTitle(query) for _ in self.delegates][0]

    def searchNotesContent(self, query: str) -> Iterable[NotePath]:
        return [_.searchNotesContent(query) for _ in self.delegates][0]


# EOF
