"""Local project storage and serialized, atomic file writes."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import time

from progress_model import ProgressError, require, validate_tracker

try:
    import fcntl
except ImportError:
    fcntl = None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def reject_constant(value):
    raise ProgressError(f"invalid JSON constant: {value}")


def parse_json(content, label):
    try:
        return json.loads(content, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (ValueError, RecursionError, ProgressError) as error:
        raise ProgressError(f"{label}: {error}") from error


def read_json(path):
    require(path.is_file(), f"expected a regular file: {path}")
    return parse_json(path.read_text(encoding="utf-8"), path)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def atomic_write(path, content):
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class Store:
    def __init__(self, root):
        self.root = root.expanduser().resolve(strict=True)
        require(self.root.is_dir(), f"project root must be a directory: {self.root}")
        self.directory = self.root / ".progress"

    def check_directory(self):
        require(not self.directory.is_symlink(), f"expected a real directory: {self.directory}")
        require(not self.directory.exists() or self.directory.is_dir(),
                f"expected a directory: {self.directory}")

    def path(self, filename):
        self.check_directory()
        path = self.directory / filename
        require(not path.is_symlink() and (not path.exists() or path.is_file()),
                f"expected a regular file: {path}")
        return path

    def read(self, required=True):
        path = self.path("tasks.json")
        if path.exists():
            return validate_tracker(read_json(path))
        require(not required, f"no tracker at {path}. Initialize it with init --plan.")
        return None

    def write(self, tracker):
        path = self.path("tasks.json")
        atomic_write(path, json_text(tracker))
        return path

    def write_report(self, markdown):
        path = self.path("report.md")
        atomic_write(path, markdown)
        return path

    @contextmanager
    def locked(self, create=False):
        require(fcntl is not None, "writing requires POSIX file locking (macOS, Linux, or WSL)")
        self.check_directory()
        if create:
            self.directory.mkdir(exist_ok=True)
        else:
            require(self.directory.is_dir(), f"no tracker at {self.directory / 'tasks.json'}. Initialize it with init --plan.")
        # Keep the lock path stable. The OS releases the lock if a writer exits.
        with self.path(".lock").open("a+b") as handle:
            deadline = time.monotonic() + 5
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    require(time.monotonic() < deadline, "tracker is busy. Reread status and retry.")
                    time.sleep(0.05)
            yield
