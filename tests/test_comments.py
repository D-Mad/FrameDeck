"""Tests for the comment model: CRUD, pin rendering, and sidecar persistence."""

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter, QPixmap

import constants
from tests.helpers import probe_pixel
from widgets import notestore
from widgets.annotations import Sketch


def _converter(width, height):
    def convert(point):
        return QPointF(point[0] * width, point[1] * height)

    return convert


def _render(sketch, width=200, height=200):
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(0, 0, 0))
    painter = QPainter(pixmap)
    try:
        sketch.draw(painter, point_converter=_converter(width, height))
    finally:
        painter.end()
    return pixmap.toImage()


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
def test_add_comment_frame_level_and_pinned(qapp):
    sketch = Sketch()

    plain = sketch.add_comment(10, "looks good")
    pinned = sketch.add_comment(10, "fix this edge", x=0.25, y=0.75)

    assert plain["text"] == "looks good"
    assert "x" not in plain  # frame-level note carries no pin
    assert (pinned["x"], pinned["y"]) == (0.25, 0.75)
    assert plain["done"] is False
    assert plain["timestamp"]
    assert len(sketch.get_comments(10)) == 2


def test_blank_comment_is_ignored(qapp):
    sketch = Sketch()
    assert sketch.add_comment(1, "   ") is None
    assert sketch.comment_count() == 0


def test_delete_and_toggle_done(qapp):
    sketch = Sketch()
    comment = sketch.add_comment(4, "note")

    assert sketch.toggle_comment_done(4, comment["id"]) is True
    assert sketch.get_comments(4)[0]["done"] is True
    assert sketch.toggle_comment_done(4, comment["id"]) is False

    assert sketch.delete_comment(4, comment["id"]) is True
    assert sketch.get_comments(4) == []
    assert 4 not in sketch.comments  # empty frame entry removed
    assert sketch.delete_comment(4, comment["id"]) is False  # already gone


def test_annotated_frames_unions_strokes_and_comments(qapp):
    sketch = Sketch()
    sketch.strokes[2] = [{"id": "s", "type": "pencil", "points": [(0.1, 0.1)]}]
    sketch.add_comment(7, "a note")
    sketch.add_comment(2, "same frame as a stroke")

    assert sketch.annotated_frames() == [2, 7]
    assert sketch.commented_frames() == [2, 7]
    assert sketch.comment_count() == 2


def test_clear_removes_comments_for_frame_only(qapp):
    sketch = Sketch()
    sketch.set_frame(3)
    sketch.add_comment(3, "on three")
    sketch.add_comment(9, "on nine")

    sketch.clear()
    assert sketch.get_comments(3) == []
    assert len(sketch.get_comments(9)) == 1

    sketch.clear_all()
    assert sketch.comment_count() == 0


# --------------------------------------------------------------------------- #
# Pin rendering (real pixels)
# --------------------------------------------------------------------------- #
def test_pinned_comment_draws_marker(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    sketch.add_comment(1, "here", x=0.5, y=0.5)

    image = _render(sketch)

    # Marker centre carries the pin colour (white number sits on top, so probe
    # slightly off-centre where the fill shows).
    red, green, blue, _a = probe_pixel(image, 100, 106)
    assert (red, green, blue) != (0, 0, 0)
    assert red > 150 and blue < 120  # reddish pin fill

    # Away from the pin the frame is untouched.
    assert probe_pixel(image, 10, 10)[:3] == (0, 0, 0)


def test_unpinned_comment_draws_nothing(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    sketch.add_comment(1, "frame level, no pin")

    image = _render(sketch)
    assert probe_pixel(image, 100, 100)[:3] == (0, 0, 0)


def test_done_pin_uses_distinct_colour(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    comment = sketch.add_comment(1, "done one", x=0.5, y=0.5)
    sketch.toggle_comment_done(1, comment["id"])

    red, green, _blue, _a = probe_pixel(_render(sketch), 100, 106)
    assert green > red  # green "done" fill, not the red default


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def test_comments_survive_sidecar_roundtrip(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    source = str(tmp_path / "shot.mov")

    original = Sketch()
    original.strokes[1] = [
        {"id": "s", "type": "pencil", "color": (255, 0, 0),
         "thickness": 2, "points": [(0.1, 0.2)]}
    ]
    original.add_comment(1, "pinned note", x=0.3, y=0.4)
    original.add_comment(5, "frame note")

    assert notestore.save_notes(source, original) is not None

    loaded = Sketch()
    assert notestore.load_notes(source, loaded) is True
    assert loaded.serialize_comments() == original.serialize_comments()
    assert loaded.strokes == original.strokes
    assert loaded.annotated_frames() == [1, 5]


def test_comment_only_sketch_still_writes_sidecar(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    source = str(tmp_path / "comment_only.mov")

    sketch = Sketch()
    sketch.add_comment(2, "no strokes, just a comment")

    assert notestore.save_notes(source, sketch) is not None  # must not be skipped

    loaded = Sketch()
    assert notestore.load_notes(source, loaded) is True
    assert loaded.get_comments(2)[0]["text"] == "no strokes, just a comment"


def test_old_sidecar_without_comments_key_loads(tmp_path, monkeypatch, qapp):
    import json

    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    source = str(tmp_path / "legacy.mov")

    path = notestore.notes_path_for(source)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": notestore.SCHEMA,
                "source": source,
                "annotations": {"3": [{"id": "s", "type": "pencil",
                                       "points": [[0.1, 0.2]]}]},
            }
        ),
        encoding="utf-8",
    )

    sketch = Sketch()
    assert notestore.load_notes(source, sketch) is True
    assert sketch.annotated_frames() == [3]
    assert sketch.comment_count() == 0  # absent "comments" key is fine


def test_load_missing_clears_comments_too(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    sketch = Sketch()
    sketch.add_comment(1, "stale")

    assert notestore.load_notes(str(tmp_path / "nope.mov"), sketch) is False
    assert sketch.comment_count() == 0
