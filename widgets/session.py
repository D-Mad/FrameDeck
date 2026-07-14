"""Helpers for FrameDeck session/project persistence.

The session document format is shared by manually saved ``.fdplaylist`` files
and the auto-saved last session. These helpers cover the profile-scoped
last-session path and window-geometry (de)serialization; the MainWindow owns the
document assembly itself.
"""

import os
import json
from pathlib import Path


PREFERENCES_SCHEMA = "framedeck-preferences-v1"


def _profile_root():
    return os.environ.get("FRAMEDECK_PROFILE_ROOT") or str(Path.home() / "Documents")


def last_session_path():
    """Path of the auto-saved last session, under the profile directory."""
    return Path(_profile_root()) / "framedeck" / "last_session.fdplaylist"


def preferences_path():
    """Path of lightweight user preferences stored beside the session."""
    return Path(_profile_root()) / "framedeck" / "preferences.json"


def _read_preferences():
    path = preferences_path()
    try:
        with open(path, "r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError):
        return {}
    if not isinstance(document, dict) or document.get("schema") != PREFERENCES_SCHEMA:
        return {}
    return document


def restore_enabled():
    """Return the opt-in last-session restore preference (default: False)."""
    return _read_preferences().get("restore_last_session") is True


def set_restore_enabled(enabled):
    """Persist the restore preference and discard stale state when disabled."""
    enabled = bool(enabled)
    path = preferences_path()
    document = _read_preferences()
    document.update(
        {
            "schema": PREFERENCES_SCHEMA,
            "restore_last_session": enabled,
        }
    )
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

    if not enabled:
        remove_last_session()
    return enabled


def remove_last_session():
    """Remove stale auto-restore state without affecting manual playlists."""
    try:
        last_session_path().unlink(missing_ok=True)
    except OSError:
        return False
    return True


def encode_geometry(byte_array):
    """Encode a Qt ``saveGeometry()`` QByteArray as an ASCII base64 string."""
    if byte_array is None:
        return ""
    return bytes(byte_array.toBase64()).decode("ascii")


def decode_geometry(text):
    """Decode a base64 string back into a QByteArray for ``restoreGeometry()``."""
    from PySide6.QtCore import QByteArray

    if not text or not isinstance(text, str):
        return QByteArray()
    return QByteArray.fromBase64(text.encode("ascii"))
