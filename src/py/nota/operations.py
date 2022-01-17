from typing import ContextManager, Optional, Generic, TypeVar, Iterable
from .model import Note, NotePath

T = TypeVar('T')


class Session(ContextManager, Generic[T]):

    def __init__(self, path: NotePath):
        self.path = path

    def __enter__(self):
        pass

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

    def __init__(self, *delegates:Operator):
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

# EOF
