from typing import NamedTuple, Optional, Iterable, Hashable
import re

# --
# ## Ad-hoc Parsing
#
# This module defines primitive for ad-hoc, grammar-less, "cherry picking"
# parsing of text. Patterns match fragments looking aheadin the text
# stream.

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

def indentation(line: str, tabsize=4) -> int:
    """Returns the indentation level of the given `line`, expanding tabs
    to spaces."""
    indent = 0
    for c in line:
        if c == ' ':
            indent += 1
        elif c == '\t':
            indent += tabsize - (indent % tabsize)
        else:
            break
    return indent


def parse(patterns: dict[Hashable, Pattern], text: str, lookahead: int = 80*20) -> Iterable[tuple[str, Match]]:
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
