from typing import Iterable, Optional
from .model import Note
from .store import Store, EditSession


NotePath = str


class Operations:

    def __init__(self, store: Store):
        self.store = store

    def editNote(self, path: str) -> EditSession:
        return self.store.editNote(path)

    def hasNote(self, path: str) -> bool:
        pass

    def saveNote(self, note: Note) -> bool:
        pass

    def listNotes(self, path: Optional[str] = None) -> Iterable[NotePath]:
        yield from self.store.listNotes()

    def searchNotesTitle(self, query: str) -> Iterable[NotePath]:
        pass

    def searchNotesContent(self, query: str) -> Iterable[NotePath]:
        pass

# EOF
