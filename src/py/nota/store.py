from pathlib import Path
from typing import Optional, Iterable, Callable, ContextManager
import stat
import os
import shutil
from glob import glob


class AbstractStore:
    pass


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


class EditSession(ContextManager):

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(NOTE_TEMPLATE)
        return self.path

    def __exit__(self, type, value, traceback):
        pass


class Store(AbstractStore):

    EXTENSION = ".nd"

    def __init__(self):
        self.files = Files(Path.home() / ".nota")

    @property
    def base(self) -> Path:
        return self.files.path

    def editNote(self, note: str) -> EditSession:
        return EditSession(self.notePath(note))

    def hasNote(self, note: str) -> bool:
        return self.notePath(note).exists()

    def readNote(self, note: str) -> str:
        return self.notePath(note).read_text()

    def listNotes(self) -> Iterable[str]:
        n = 0 - len(self.EXTENSION)
        return (str(_.relative_to(self.base))[:n] for _ in self.files.walk(lambda _: _.suffix == self.EXTENSION))

    def notePath(self, note: str) -> Path:
        return (self.base / f"{note}{self.EXTENSION}").absolute()


class Files:
    """A simple wrapper around the filesystem to easily store and
    query files."""

    def __init__(self, path: Path):
        self.path: Path = path

    def mode(self, path: Path) -> bool:
        """Ensures that the given path has the correct mode"""
        # SEE: https://stackoverflow.com/questions/5337070/how-can-i-get-the-unix-permission-mask-from-a-file
        mode = 0o700 if path.is_dir() else (
            0o644 if str(path).endswith(".pub") else 0o0600)
        current_mode = os.stat(path)[stat.ST_MODE]
        if current_mode & 0o777 != mode:
            target_mode = current_mode & 0o777000 | mode
            os.chmod(path, target_mode)
            return True
        else:
            return False

    def fix(self, path: Optional[Path] = None, mode=True, empty=True) -> bool:
        path = path or self.path
        empty_dirs = []
        changed = False
        for dirpath, dirnames, filenames in os.walk(path):
            dp = Path(dirpath)
            is_empty = True
            for _ in dirnames:
                is_empty = False
                if mode:
                    changed = changed or self.mode(dp.joinpath(_))
            for _ in filenames:
                is_empty = False
                if mode:
                    changed = changed or self.mode(dp.joinpath(_))
            if is_empty:
                empty_dirs.append(dp)
        if empty:
            for path in sorted(empty_dirs, reverse=True):
                if not path:
                    continue
                if os.path.exists(path):
                    os.rmdir(path)
                    changed = True
        return changed

    def write(self, path: str, content: bytes) -> Path:
        stored_path = self.normalize(path)
        if not (parent := stored_path.parent).exists():
            parent.mkdir(parents=True)
        fd = os.open(stored_path, os.O_WRONLY | os.O_TRUNC |
                     os.O_CREAT | os.O_DSYNC)
        os.write(fd, content)
        os.close(fd)
        # We set the file mode correctly, based on what it is
        self.mode(stored_path)
        return stored_path

    def read(self, path: str) -> bytes:
        # NOTE: We don't need buffer writes, we assume secrets are small-ish
        stored_path = self.normalize(path)
        fd = os.open(stored_path, os.O_RDONLY | os.O_RSYNC)
        data: list[bytes] = []
        while True:
            # 256Kb buffers should be enough
            t = os.read(fd, 256_000)
            if not t:
                break
            else:
                data.append(t)
        os.close(fd)
        return data[0] if len(data) == 1 else b"".join(data)

    def exists(self, path: str) -> bool:
        return self.normalize(path).exists()

    def glob(self, prefix: str, suffix: Optional[str] = None) -> Iterable[str]:
        stored_prefix = str(self.normalize(prefix))
        if suffix:
            for match in glob(f"{stored_prefix}/*{suffix}"):
                yield match.split(stored_prefix, 1)[-1].rsplit(suffix, 1)[0][1:]
        else:
            for match in glob(f"{stored_prefix}/*"):
                yield match.split(stored_prefix, 1)[-1][1:]

    def walk(self, predicate: Callable[[Path], bool], prefix: Optional[str] = None) -> Iterable[Path]:
        base = (self.path / prefix) if prefix else self.path
        for root, _, filenames in os.walk(base):
            root_path = Path(root)
            for n in filenames:
                p = root_path / n
                if predicate(p):
                    yield p

    def unlink(self, path: str) -> bool:
        stored_path = self.normalize(path)
        if os.path.exists(stored_path):
            os.unlink(stored_path)
            return True
        else:
            return False

    def rmdir(self, path: str) -> bool:
        stored_path = self.normalize(path)
        if os.path.exists(stored_path) and os.path.isdir(stored_path):
            try:
                os.rmdir(stored_path)
                return True
            except OSError:
                return False
        else:
            return True

    def normalize(self, path: str) -> Path:
        """Ensures that the paths are normalized. This may create collisions"""
        return self.path / path

    def clear(self):
        """This clears the entire store... use with caution!"""
        if self.path != Path("~").expanduser() and self.path != Path("/"):
            shutil.rmtree(self.path)
        else:
            raise RuntimeError(
                f"Clearing the store would be too dangerous: {self.path}")

# EOF
