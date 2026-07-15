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


def _read_document(source):
    """Return a validated note document for *source*, or ``None``.

    Keeping validation in one place lets lightweight timeline queries inspect
    sidecars without constructing or mutating a :class:`Sketch` instance.
    """
    if not source:
        return None

    path = notes_path_for(source)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError):
        return None

    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        return None

    saved_source = document.get("source")
    if not saved_source or os.path.normcase(os.path.abspath(str(saved_source))) != (
        os.path.normcase(os.path.abspath(str(source)))
    ):
        return None
    return document


def _populated_frame_keys(records):
    """Return integer frame keys whose record list is non-empty and valid."""
    frames = set()
    if not isinstance(records, dict):
        return frames
    for frame, items in records.items():
        if not isinstance(items, list) or not items:
            continue
        try:
            frames.add(int(frame))
        except (TypeError, ValueError):
            continue
    return frames


def annotation_frames(source):
    """Return ``(comment_frames, drawing_frames)`` without loading a sketch.

    Missing, corrupt, or foreign sidecars safely read as two empty sets. This is
    used to populate a playlist-wide timeline while only the active shot's full
    annotation payload remains in memory.
    """
    document = _read_document(source)
    if document is None:
        return set(), set()
    return (
        _populated_frame_keys(document.get("comments")),
        _populated_frame_keys(document.get("annotations")),
    )


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

    document = _read_document(source)
    if document is None:
        _clear(sketch)
        return False

    # "comments" is absent in sidecars written before comments existed.
    sketch.deserialize(document.get("annotations") or {})
    sketch.deserialize_comments(document.get("comments") or {})
    return True
