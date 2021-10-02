from typing import NamedTuple, Optional, Iterable
import re


class Fragment:

    def __init__(self, source: str, start: int, end: int):
        self.source = source
        self.start = start
        self.end = end
        self.eos = len(source)
        self._text = source[start:end]

    @property
    def text(self) -> str:
        return self._text

    def to(self, offset: int) -> Optional['Fragment']:
        size = self.end - self.start
        return None if offset >= self.eos else Fragment(self.source, offset, min(self.eos, offset + size))

    def shift(self, amount: int) -> Optional['Fragment']:
        return None if self.end == self.eos else Fragment(self.source, self.start + amount, min(self.eos, self.end + amount))

    def __repr__(self):
        return f"Fragment(start={self.start}, end={self.end}, text={repr(self.text)})"


class Match(NamedTuple):
    name: Optional[str]
    type: Optional[str]
    fragment: Fragment
    match: re.Match


class Pattern:

    def __init__(self, regexp: re.Pattern, name: Optional[str] = None, type: Optional[str] = None):
        self.regexp = regexp
        self.name = name
        self.type = type

    def recognizes(self, fragment: Fragment) -> Optional['Match']:
        text = fragment._text
        if match := self.regexp.search(text):
            o = fragment.start
            return Match(self.name, self.type, Fragment(fragment.source, o + match.start(0), o + match.end(0)), match)
        else:
            return None


def parse(patterns: dict[str, Pattern], text: str, lookahead: int = 80*20) -> Iterable[tuple[str, Match]]:
    """Takes a set of named patterns and yields a stream of `(name,match)` couples."""
    fragment: Optional[Fragment] = Fragment(text, 0, lookahead)
    while fragment:
        match_end = 0
        matched_pairs = sorted(
            (_ for _ in ((k, p.recognizes(fragment))
                         for k, p in patterns.items()) if _[1]),
            key=lambda _: _[1].fragment.start)
        for k, match in matched_pairs:
            match_end = max(match.fragment.end, match_end)
            if match:
                yield k, match
        fragment = fragment.to(
            match_end) if match_end else fragment.shift(lookahead)

# EOF
