from typing import Iterable, Optional
from .operations import Operator

# --
# ## Git Operator
#
# The git operator is used to implement effects on the actions defined
# in Nota.
class Git(Operator):

    def __init__(self):
        pass

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
