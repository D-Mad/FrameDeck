"""Persist per-source annotation notes to JSON sidecar files.

Notes live under the FrameDeck profile directory (not next to the media), keyed
by a short hash of the absolute source path, so pencil/text annotations survive
closing and reopening a source or a whole session.

The store is intentionally decoupled from the Sketch widget: it only calls the
pure ``serialize`` / ``deserialize`` methods, so it is straightforward to test.
"""

import hashlib
import json
import os
from pathlib import Path

SCHEMA = "framedeck-notes-v1"


def _profile_root():
    return os.environ.get("FRAMEDECK_PROFILE_ROOT") or str(Path.home() / "Documents")


def notes_dir():
    """Return the directory that holds note sidecars (not created here)."""
    return Path(_profile_root()) / "framedeck" / "notes"


def notes_path_for(source):
    """Return the sidecar path for a given media source path."""
    absolute = os.path.abspath(str(source))
    digest = hashlib.sha256(
        os.path.normcase(absolute).encode("utf-8")
    ).hexdigest()[:16]
    # Keep the filename comfortably below Windows path component limits. The
    # digest, not the readable stem, is the source identity.
    stem = Path(absolute).stem[:80] or "media"
    return notes_dir() / f"{stem}_{digest}.fdnotes.json"


def _clear(sketch):
    """Reset a sketch to an empty, defined state (strokes and comments)."""
    sketch.deserialize({})
    sketch.deserialize_comments({})


def save_notes(source, sketch):
    """Write *sketch*'s strokes and comments to *source*'s sidecar.

    An empty annotation set removes any existing sidecar so a later load starts
    clean. Returns the sidecar path when written, else ``None``.
    """
    if not source:
        return None

    path = notes_path_for(source)
    data = sketch.serialize()
    comments = sketch.serialize_comments()

    if not data and not comments:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
        return None

    document = {
        "schema": SCHEMA,
        "source": os.path.abspath(str(source)),
        "annotations": data,
        "comments": comments,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(temporary, "w", encoding="utf-8") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_notes(source, sketch):
    """Load *source*'s sidecar (strokes and comments) into *sketch*.

    Always leaves *sketch* in a defined state: if there is no sidecar (or it is
    unreadable/foreign) the sketch is cleared. Returns ``True`` when notes were
    loaded from a valid sidecar.
    """
    if not source:
        _clear(sketch)
        return False

    path = notes_path_for(source)
    if not path.exists():
        _clear(sketch)
        return False

    try:
        with open(path, "r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError):
        _clear(sketch)
        return False

    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        _clear(sketch)
        return False

    saved_source = document.get("source")
    if not saved_source or os.path.normcase(os.path.abspath(str(saved_source))) != (
        os.path.normcase(os.path.abspath(str(source)))
    ):
        _clear(sketch)
        return False

    # "comments" is absent in sidecars written before comments existed.
    sketch.deserialize(document.get("annotations") or {})
    sketch.deserialize_comments(document.get("comments") or {})
    return True
