from typing import ContextManager, Optional, Generic, TypeVar, Iterable, Iterator, Union
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


class Session(ContextManager, Generic[T]):
    def __init__(self, path: NotePath):
        self.path = path

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass


class EditSession(Session):
    def __init__(self, path: Path, onEnd: Optional[Callback[[Path]], None] = None):
        assert isinstance(path, Path), f"Expected path, got: {path}"
        self.path: Path = path
        self.onEnd: Optional[Callback[[Path], None]] = onEnd

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(NOTE_TEMPLATE)
        return self.path

    def __exit__(self, type, value, traceback):
        pass


class Operator:
    def editNote(self, path: NotePath) -> Session[NotePath]:
        raise NotImplemented

    def hasNote(self, path: NotePath) -> bool:
        raise NotImplemented

    def readNote(self, note: Note) -> str:
        raise NotImplemented

    def listNotes(self, path: Optional[str] = None) -> Iterable[NotePath]:
        raise NotImplemented

    def searchNotesTitle(self, query: str) -> Iterable[NotePath]:
        raise NotImplemented

    def searchNotesContent(self, query: str) -> Iterable[NotePath]:
        raise NotImplemented


class Operations(Operator):
    def __init__(self, *delegates: Operator):
        self.delegates = delegates

    def editNote(self, path: NotePath) -> Session[NotePath]:
        return [_.editNote(path) for _ in self.delegates][0]

    def hasNote(self, path: NotePath) -> bool:
        return [_.hasNote(path) for _ in self.delegates][0]

    def readNote(self, note: Note) -> str:
        return [_.readNote(note) for _ in self.delegates][0]

    def listNotes(self, path: Optional[str] = None) -> Iterable[NotePath]:
        return [_.listNotes(path) for _ in self.delegates][0]

    def searchNotesTitle(self, query: str) -> Iterable[NotePath]:
        return [_.searchNotesTitle(query) for _ in self.delegates][0]

    def searchNotesContent(self, query: str) -> Iterable[NotePath]:
        return [_.searchNotesContent(query) for _ in self.delegates][0]


class Store:
    def edit(self, note: str):
        return EditSession(self.store.openNote(self.notePath(note)))

    def exists(self, path: str) -> bool:
        """Tells if the given path exists"""
        raise NotImplementedError

    def read(self, path: str) -> str:
        """Reads the data from the given path."""
        raise NotImplementedError

    def list(self, path: Optional[str] = None) -> Iterator[str]:
        """Reads the notes at the given path."""
        raise NotImplementedError


class LocalStore(Store):
    """Implements a local store"""

    def __init__(
        self,
        base: Union[Path, str] = Path(
            os.path.expandvars(os.getenv("NOTA_HOME", "$HOME/.nota"))
        ),
    ):
        self.base: Path = Path(base).absolute()
        if not self.base.exists():
            raise RuntimeError(f"Store path does not exsits: {base}")

    def exists(self, path: str) -> bool:
        """Tells if the given path exists"""
        return (self.base / path).exists()

    def read(self, path: str) -> Optional[str]:
        """Reads the data from the given path."""
        return (
            (local_path).read_text()
            if (local_path := self.base / path).exists()
            else None
        )

    def list(self, path: Optional[str] = None) -> Iterator[str]:
        for root, _, files in os.walk(self.base / path if path else self.base):
            for f in files:
                if f.endswith(".nd"):
                    yield f"{root}/{f}"


class StoreOperator(Operator):

    EXTENSION = ".nd"

    def __init__(self, store: Optional[Store] = None):
        self.store: Store = store if store else LocalStore()

    def editNote(self, note: str) -> EditSession:
        return EditSession(self.store.openNote(self.notePath(note)))

    def hasNote(self, note: str) -> bool:
        return self.store.exists(self.notePath(note))

    def readNote(self, note: str) -> str:
        return self.store.read(self.notePath(note))

    def listNotes(self, path: Optional[str] = None) -> Iterable[str]:
        return self.store.list(self.notePath(path) if path else None)

    def notePath(self, note: str) -> str:
        return f"{note}{self.EXTENSION}"


# --
# ## Git Operator
#
# The git operator is used to implement effects on the actions defined
# in Nota.
class GitOperator(Operator):
    def __init__(self):
        pass

    # TODO: This should be store-specific
    def editNote(self, path: NotePath) -> EditSession:
        raise NotImplementedError

    def hasNote(self, path: NotePath) -> bool:
        raise NotImplementedError

    def readNote(self, note: Note) -> str:
        raise NotImplementedError

    def listNotes(self, path: Optional[str] = None) -> Iterable[NotePath]:
        raise NotImplementedError

    def searchNotesTitle(self, query: str) -> Iterable[NotePath]:
        raise NotImplementedError

    def searchNotesContent(self, query: str) -> Iterable[NotePath]:
        raise NotImplementedError


# EOF
