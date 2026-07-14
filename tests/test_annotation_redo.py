"""Unit tests for Sketch undo/redo (widgets.annotations)."""

from widgets.annotations import Sketch


def _add_created_stroke(sketch, frame, stroke_id, stroke_type="pencil"):
    """Mimic drawing a stroke: add it and record a 'create' undo action."""
    sketch.strokes.setdefault(frame, []).append(
        {"id": stroke_id, "type": stroke_type, "points": []}
    )
    sketch._record_action({"type": "create", "frame": frame, "stroke_id": stroke_id})


def _ids(sketch, frame):
    return [stroke["id"] for stroke in sketch.strokes.get(frame, [])]


def test_redo_restores_created_stroke(qapp):
    sketch = Sketch()
    _add_created_stroke(sketch, 1, "a")
    sketch.undo()
    assert 1 not in sketch.strokes
    sketch.redo()
    assert _ids(sketch, 1) == ["a"]


def test_new_action_clears_redo_stack(qapp):
    sketch = Sketch()
    _add_created_stroke(sketch, 1, "a")
    sketch.undo()
    assert sketch.redo_history  # there is something to redo
    _add_created_stroke(sketch, 2, "b")  # a fresh edit
    assert not sketch.redo_history  # ...invalidates redo
    sketch.redo()  # no-op
    assert 1 not in sketch.strokes


def test_multiple_undo_then_redo_sequence(qapp):
    sketch = Sketch()
    _add_created_stroke(sketch, 1, "a")
    _add_created_stroke(sketch, 1, "b")
    sketch.undo()  # remove b
    sketch.undo()  # remove a
    assert 1 not in sketch.strokes
    sketch.redo()  # restore a
    assert _ids(sketch, 1) == ["a"]
    sketch.redo()  # restore b
    assert _ids(sketch, 1) == ["a", "b"]


def test_redo_with_empty_stack_is_noop(qapp):
    sketch = Sketch()
    sketch.redo()  # must not raise
    assert sketch.strokes == {}


def test_erase_undo_and_redo(qapp):
    sketch = Sketch()
    sketch.strokes[3] = [{"id": "x", "type": "pencil"}]
    # Erase records the pre-erase snapshot, then clears the frame.
    sketch._record_action(
        {"type": "erase", "frame": 3, "strokes": [{"id": "x", "type": "pencil"}]}
    )
    sketch.strokes[3] = []
    sketch.undo()  # restores x
    assert _ids(sketch, 3) == ["x"]
    sketch.redo()  # re-applies the erase
    assert sketch.strokes.get(3) == []
