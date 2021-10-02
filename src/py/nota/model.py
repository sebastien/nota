from enum import Enum
from dataclasses import dataclass


@dataclass
class Note:
    path: str


@dataclass
class Fragment:
    path: str
    start: int
    end: int


class ReferenceType(Enum):
    Tag = "tag"
    Entity = "entity"
    Link = "link"
    Term = "term"
    Date = "date"
    Time = "time"
    Datetime = "time"
    URL = "url"
    Email = "email"


@dataclass
class Reference:
    type: ReferenceType
    value: str


# EOF
