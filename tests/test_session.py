"""Tests for widgets.session (last-session path + window-geometry codec)."""

import json

from widgets import session


def test_last_session_path_is_profile_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    path = session.last_session_path()
    assert str(tmp_path) in str(path)
    assert path.name == "last_session.fdplaylist"
    assert path.parent.name == "framedeck"


def test_geometry_roundtrip(qapp):
    from PySide6.QtCore import QByteArray

    original = QByteArray(b"\x01\x02\x03 geometry-blob \xfe\xff")
    encoded = session.encode_geometry(original)
    assert isinstance(encoded, str)
    decoded = session.decode_geometry(encoded)
    assert bytes(decoded) == bytes(original)


def test_encode_none_and_decode_empty(qapp):
    assert session.encode_geometry(None) == ""
    assert bytes(session.decode_geometry("")) == b""
    assert bytes(session.decode_geometry(None)) == b""


def test_restore_is_opt_in_and_defaults_off(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    assert session.restore_enabled() is False

    assert session.set_restore_enabled(True) is True
    assert session.restore_enabled() is True
    document = json.loads(session.preferences_path().read_text(encoding="utf-8"))
    assert document["restore_last_session"] is True


def test_disabling_restore_removes_stale_session(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    path = session.last_session_path()
    path.parent.mkdir(parents=True)
    path.write_text("stale", encoding="utf-8")

    session.set_restore_enabled(False)
    assert session.restore_enabled() is False
    assert not path.exists()


def test_corrupt_preferences_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    path = session.preferences_path()
    path.parent.mkdir(parents=True)
    path.write_text("not json", encoding="utf-8")
    assert session.restore_enabled() is False
