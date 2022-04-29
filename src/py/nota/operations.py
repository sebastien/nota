from typing import ContextManager, Optional, Generic, TypeVar, Iterable
from pathlib import Path
from .model import Note, NotePath

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
    def __init__(self, path: Path):
        self.path = path

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
    def exists(self, path: str) -> bool:
        raise NotImplemented

    def read(self, path: str) -> str:
        raise NotImplemented

    def list(self, path: Optional[str]=None) -> Iterator[str]:
        raise NotImplemented


class StoreOperator(Operator):

    EXTENSION = ".nd"

    def __init__(self, store: Store):
        self.store = store

    def editNote(self, note: str) -> EditSession:
        return EditSession(self.notePath(note))

    def hasNote(self, note: str) -> bool:
        return self.store.exists(self.notePath(note))

    def readNote(self, note: str) -> str:
        return self.store.read(self.notePath(note))

    def listNotes(self, path: Optional[str] = None) -> Iterable[str]:
        return self.store.list(self.notePath(path) if path else None)

    def notePath(self, note: str) -> str:
        return f"{note}{self.EXTENSION}")


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


# EOF
