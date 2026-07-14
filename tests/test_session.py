"""Tests for widgets.session (last-session path + window-geometry codec)."""

import json

from widgets import session
from tests.helpers import make_solid_mp4


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


def test_empty_opted_in_session_removes_stale_restore(
    tmp_path, monkeypatch, qapp
):
    from widgets import MainWindow

    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path / "profile"))
    session.set_restore_enabled(True)
    stale = session.last_session_path()
    stale.write_text("stale", encoding="utf-8")

    window = MainWindow()
    try:
        assert window.auto_save_last_session() is False
        assert not stale.exists()
    finally:
        session.set_restore_enabled(False)
        window.close()
        qapp.processEvents()


def test_opted_in_session_roundtrip_restores_playlist_without_claiming_file(
    tmp_path, monkeypatch, qapp
):
    from widgets import MainWindow

    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path / "profile"))
    session.set_restore_enabled(True)
    media = make_solid_mp4(tmp_path / "session-shot.mp4", frames=3)

    first = MainWindow()
    second = None
    try:
        added = first.playlistWidget.add_local_media([str(media)])
        assert len(added) == 1
        first.playlistWidget.local_contexts = [
            first.playlistWidget._playlist_context(added[0])
        ]
        first.playlistWidget._refresh_local_playlist()
        assert first.openMedia(str(media), add_to_playlist=False) is True
        first.set_loop_mode("pingpong")
        assert first.auto_save_last_session() is True
        assert session.last_session_path().exists()

        first.close()
        qapp.processEvents()

        second = MainWindow()
        assert second.actionRestoreSession.isChecked()
        assert second.restore_last_session() is True
        assert len(second.playlistWidget.local_contexts) == 1
        assert second.current_source_filepath == str(media)
        assert second.loop_mode == "pingpong"
        assert second.current_playlist_path is None
        assert "last_session.fdplaylist" not in second.windowTitle()
    finally:
        session.set_restore_enabled(False)
        if second is not None:
            second.close()
        first.close()
        qapp.processEvents()
