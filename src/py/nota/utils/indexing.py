import re
import unicodedata
from typing import NamedTuple, Iterable, Optional

RE_SPACES = re.compile(r"[\s\t\n]+")
RE_INDEXABLE = re.compile(r"[^\s]+")
RE_NOALPHANUM = re.compile(r"[^A-Za-z0-9]+")


def nounicode(atom: str) -> str:
    """Returns the non-unicode version of the gien value"""
    return unicodedata.normalize("NFKD", atom)


def alphanum(value: str) -> str:
    """Replaces non-alphanumeric values with _"""
    return RE_NOALPHANUM.sub("_", value)


def keyword(atom: str) -> str:
    """Returns a lower case version"""
    return RE_SPACES.sub(" ", (atom or "").lower()).strip()


def normalize(atom: str) -> str:
    return keyword(alphanum(nounicode(atom)))


class Entry(NamedTuple):
    source: str
    original: str
    start: int
    end: int


class Match(NamedTuple):
    score: float
    entry: Entry


# TODO: FZF Algo -- https://github.com/junegunn/fzf/blob/master/src/algo/algo.go
def index(text: str, source: str, index: Optional[dict[str, list[Entry]]] = None) -> dict[str, list[Entry]]:
    res: dict[str, list[Entry]] = {} if index is None else index
    for match in RE_INDEXABLE.finditer(text):
        if len(match.group()) > 2:
            entry = normalize(match.group())
            res.setdefault(entry, []).append(
                Entry(source, match.group(), match.start(), match.end()))
    return res


def matches(index: dict[str, list[Entry]], query: str) -> Iterable[Match]:
    q = normalize(query)
    matched: list[tuple[Entry, int]] = []
    for key, entries in index.items():
        for entry in entries:
            if query == entry.original:
                score = 1.0
            elif query == key:
                score = 0.8
            elif q == key:
                score = 0.6
            elif query in entry.original:
                score = 0.4
            elif query in key:
                score = 0.2
            elif q in key:
                score = 0.1
            else:
                score = 0
            if score:
                yield Match(score, entry)


def find(index: dict[str, list[Entry]], query: str) -> Iterable[Match]:
    yield from sorted(matches(index, query), key=lambda _: (_.score, _.entry.start))


with open("/home/sebastien/.nota/tools/git.nd", "rt") as f:
    idx = index(f.read(), "tools/git")
    print(list(find(idx, "as")))

# EOF
