"""Tests for annotation persistence: Sketch serialize/deserialize + notestore."""

import json

from widgets import notestore
from widgets.annotations import Sketch


def _sketch_with_strokes():
    sketch = Sketch()
    sketch.set_frame(5)
    sketch.strokes[5] = [
        {
            "id": "a", "type": "pencil", "color": (255, 170, 0), "thickness": 3,
            "points": [(0.1, 0.2), (0.3, 0.4)],
        },
        {
            "id": "b", "type": "rectangle", "color": (0, 255, 0), "thickness": 2,
            "start": (0.2, 0.2), "end": (0.5, 0.6),
        },
    ]
    sketch.strokes[9] = [
        {
            "id": "t", "type": "txt", "color": (255, 255, 255),
            "position": (0.4, 0.5), "txt": "fix this",
        },
    ]
    return sketch


def test_serialize_deserialize_roundtrip_through_json(qapp):
    source = _sketch_with_strokes()
    # Force a real JSON round-trip (tuples -> lists -> tuples, int keys -> str).
    data = json.loads(json.dumps(source.serialize()))
    restored = Sketch()
    restored.deserialize(data)
    assert restored.strokes == source.strokes


def test_deserialize_resets_undo_and_redo(qapp):
    sketch = _sketch_with_strokes()
    sketch._record_action({"type": "create", "frame": 5, "stroke_id": "a"})
    sketch.undo()  # populates redo_history
    sketch.deserialize({"5": [{"id": "z", "type": "pencil", "points": [[0.1, 0.1]]}]})
    assert sketch.undo_history == []
    assert sketch.redo_history == []
    assert sketch.strokes[5][0]["points"] == [(0.1, 0.1)]  # list -> tuple


def test_notestore_save_and_load_roundtrip(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    source = str(tmp_path / "SHOT_010_comp_v001.mov")

    original = _sketch_with_strokes()
    path = notestore.save_notes(source, original)
    assert path is not None and path.exists()

    loaded_sketch = Sketch()
    assert notestore.load_notes(source, loaded_sketch) is True
    assert loaded_sketch.strokes == original.strokes


def test_notestore_empty_removes_sidecar(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    source = str(tmp_path / "clip.mov")

    path = notestore.save_notes(source, _sketch_with_strokes())
    assert path.exists()

    # Saving an empty sketch clears the stale sidecar.
    assert notestore.save_notes(source, Sketch()) is None
    assert not path.exists()


def test_notestore_load_missing_clears_sketch(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    sketch = _sketch_with_strokes()  # starts non-empty
    loaded = notestore.load_notes(str(tmp_path / "never_saved.mov"), sketch)
    assert loaded is False
    assert sketch.strokes == {}


def test_notes_path_is_stable_and_scoped_to_profile(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    source = str(tmp_path / "a" / "shot.mov")
    p1 = notestore.notes_path_for(source)
    p2 = notestore.notes_path_for(source)
    assert p1 == p2  # deterministic
    assert str(tmp_path) in str(p1)  # under the profile dir, not next to media
    assert p1.name.startswith("shot_") and p1.suffix == ".json"
