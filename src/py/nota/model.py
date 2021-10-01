from typing import NamedTuple


class Range(NamedTuple):
    start: int
    end: int


class Note:

    def __init__(self, path: str):
        self.path = path


class Region:

    def __init__(self, path: str, start: int, end: int):
        self.path = path
        self.range = Range(start, end)
