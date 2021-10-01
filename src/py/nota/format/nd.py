import re
from typing import NamedTuple, Optional


class Fragment:

    def __init__(self, source: str, start: int, end: int):
        self.source = source
        self.start = start
        self.end = end
        self._text = source[start:end]

    @property
    def text(self) -> str:
        return self._text

    def recognizes(self, regexp: re.Pattern, group: int = 0) -> Optional['Match']:
        text = self._text
        if match := regexp.search(text):
            o = self.start
            return Match(Fragment(self.source, o + match.start(group), o + match.end(group)), match)
        else:
            return None


class Match(NamedTuple):
    fragment: Fragment
    match: re.Match


class Inline:

    def __init__(self, regexp: str, multiline=True):
        self.expr = re.compile(regexp, re.MULTILINE if multiline else 0)


class Block:
    pass


INLINES = {
    "code": Inline(r"`(?P<content>[^\`]+)`"),
    "em": Inline(r"\*(?P<content>[^*]+)\*"),
    "term": Inline(r"_(?P<content>[^_]+)_"),
}
