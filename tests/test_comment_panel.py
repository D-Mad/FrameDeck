"""Tests for the comment sidebar and the viewer's comment pin tool."""

from PySide6 import QtCore
from PySide6 import QtGui

import pytest

from widgets.annotations import Sketch
from widgets.commentpanel import COMMENT_ROLE, FRAME_ROLE, CommentPanel


# Every panel built by a test is registered here and destroyed before the test
# ends. A top-level QWidget that survives into interpreter shutdown is torn down
# after the QApplication is already gone, which kills the process with an access
# violation -- intermittently, so it must be prevented rather than retried.
_PANELS = list()


@pytest.fixture(autouse=True)
def _destroy_panels(qapp):
    yield
    while _PANELS:
        panel = _PANELS.pop()
        panel.close()
        panel.deleteLater()
    qapp.processEvents()


def _new_panel():
    panel = CommentPanel(None)
    _PANELS.append(panel)
    return panel


def _panel(sketch, frame=None):
    panel = _new_panel()
    panel.set_sketch(sketch)
    if frame is not None:
        panel.set_current_frame(frame)
    return panel


def _rows(panel):
    """Return the tree as [(frame_label, [child_label, ...]), ...]."""
    tree = panel.commentTree
    rows = list()
    for index in range(tree.topLevelItemCount()):
        parent = tree.topLevelItem(index)
        children = [parent.child(i).text(0) for i in range(parent.childCount())]
        rows.append((parent.text(0), children))
    return rows


# --------------------------------------------------------------------------- #
# Rendering the sketch into the tree
# --------------------------------------------------------------------------- #
def test_panel_groups_comments_by_frame(qapp):
    sketch = Sketch()
    sketch.add_comment(12, "first on twelve")
    sketch.add_comment(12, "second on twelve")
    sketch.add_comment(3, "on three")

    panel = _panel(sketch)

    # Frames ascend regardless of insertion order.
    labels = [label for label, _children in _rows(panel)]
    assert labels == ["Frame 0003  (1)", "Frame 0012  (2)"]
    assert panel.titleLabel.text() == "Comments (3)"


def test_pinned_comments_are_numbered_like_their_markers(qapp):
    sketch = Sketch()
    sketch.add_comment(1, "frame level note")  # unpinned: no number
    sketch.add_comment(1, "first pin", x=0.2, y=0.2)
    sketch.add_comment(1, "second pin", x=0.8, y=0.8)

    _label, children = _rows(_panel(sketch))[0]

    # Numbering counts pinned comments only, matching draw_comment_pins().
    assert children == ["frame level note", "1. first pin", "2. second pin"]


def test_empty_sketch_renders_empty_tree(qapp):
    panel = _panel(Sketch())

    assert panel.commentTree.topLevelItemCount() == 0
    assert panel.titleLabel.text() == "Comments"
    assert panel.deleteButton.isEnabled() is False


def test_panel_without_sketch_does_not_crash(qapp):
    panel = _new_panel()
    panel.refresh()

    assert panel.commentTree.topLevelItemCount() == 0


# --------------------------------------------------------------------------- #
# Interaction
# --------------------------------------------------------------------------- #
def test_clicking_a_row_requests_a_seek(qapp):
    sketch = Sketch()
    sketch.add_comment(42, "seek me")
    panel = _panel(sketch)

    seeks = list()
    panel.seek_requested.connect(seeks.append)

    parent = panel.commentTree.topLevelItem(0)
    panel.commentTree.itemClicked.emit(parent.child(0), 0)
    panel.commentTree.itemClicked.emit(parent, 0)  # frame row seeks too

    assert seeks == [42, 42]


def test_checkbox_toggles_done_on_the_sketch(qapp):
    sketch = Sketch()
    comment = sketch.add_comment(5, "fix the edge")
    panel = _panel(sketch)

    changed = list()
    panel.comments_changed.connect(lambda: changed.append(True))

    child = panel.commentTree.topLevelItem(0).child(0)
    assert child.checkState(0) == QtCore.Qt.CheckState.Unchecked

    child.setCheckState(0, QtCore.Qt.CheckState.Checked)

    assert sketch.get_comments(5)[0]["done"] is True
    assert changed == [True]

    # The row must be restyled IN PLACE. Rebuilding the tree from inside
    # itemChanged destroys the item Qt is still emitting for -- a use-after-free
    # that crashes the process. Same object == no rebuild happened.
    assert panel.commentTree.topLevelItem(0).child(0) is child

    # It reflects the new state, and restyling did not re-emit as a user edit.
    assert child.checkState(0) == QtCore.Qt.CheckState.Checked
    assert child.font(0).strikeOut() is True
    assert changed == [True]

    # Unchecking flips it back.
    child.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
    assert sketch.get_comments(5)[0]["done"] is False
    assert child.font(0).strikeOut() is False
    assert changed == [True, True]

    assert comment["id"] == sketch.get_comments(5)[0]["id"]


def test_refresh_does_not_emit_comments_changed(qapp):
    """Rebuilding sets check states; that must not look like a user edit."""
    sketch = Sketch()
    done = sketch.add_comment(2, "already done")
    sketch.toggle_comment_done(2, done["id"])

    panel = _new_panel()
    changed = list()
    panel.comments_changed.connect(lambda: changed.append(True))

    panel.set_sketch(sketch)
    panel.refresh()

    assert changed == []


def test_delete_selected_removes_the_comment(qapp):
    sketch = Sketch()
    sketch.add_comment(7, "keep me")
    sketch.add_comment(7, "delete me")
    panel = _panel(sketch)

    changed = list()
    panel.comments_changed.connect(lambda: changed.append(True))

    victim = panel.commentTree.topLevelItem(0).child(1)
    victim.setSelected(True)
    panel.selection_changed()
    assert panel.deleteButton.isEnabled() is True

    panel.delete_selected()

    remaining = [comment["text"] for comment in sketch.get_comments(7)]
    assert remaining == ["keep me"]
    assert changed == [True]
    assert panel.deleteButton.isEnabled() is False


def test_selecting_a_frame_row_does_not_enable_delete(qapp):
    sketch = Sketch()
    sketch.add_comment(7, "a note")
    panel = _panel(sketch)

    panel.commentTree.topLevelItem(0).setSelected(True)
    panel.selection_changed()

    assert panel.selected_comment() is None
    assert panel.deleteButton.isEnabled() is False


def test_add_note_targets_the_current_frame(qapp):
    sketch = Sketch()
    panel = _panel(sketch, frame=9)

    changed = list()
    panel.comments_changed.connect(lambda: changed.append(True))

    panel.commentLineEdit.setText("  a note with padding  ")
    panel.add_note()

    assert [c["text"] for c in sketch.get_comments(9)] == ["a note with padding"]
    assert "x" not in sketch.get_comments(9)[0]  # frame-level, not pinned
    assert panel.commentLineEdit.text() == ""
    assert changed == [True]


def test_add_note_ignores_blank_text_and_missing_frame(qapp):
    sketch = Sketch()
    panel = _panel(sketch, frame=1)

    panel.commentLineEdit.setText("   ")
    panel.add_note()
    assert sketch.comment_count() == 0

    # No current frame: nothing to attach to.
    panel.set_current_frame(None)
    panel.commentLineEdit.setText("orphan")
    panel.add_note()
    assert sketch.comment_count() == 0
    assert panel.commentLineEdit.isEnabled() is False


def test_rows_carry_frame_and_comment_identity(qapp):
    sketch = Sketch()
    comment = sketch.add_comment(4, "identified")
    panel = _panel(sketch)

    parent = panel.commentTree.topLevelItem(0)
    child = parent.child(0)

    assert parent.data(0, FRAME_ROLE) == 4
    assert parent.data(0, COMMENT_ROLE) is None  # frame rows hold no comment
    assert child.data(0, FRAME_ROLE) == 4
    assert child.data(0, COMMENT_ROLE) == comment["id"]


# --------------------------------------------------------------------------- #
# The viewer's pin tool
#
# ViewerWidget is a QOpenGLWidget, and constructing one under the offscreen
# platform crashes Qt on teardown (access violation) roughly one run in three --
# it cannot create a GL context. So the real ViewerWidget.mousePressEvent is
# invoked against a stand-in carrying only the attributes that method reads.
# The code under test is the shipped code; only the GL shell is stubbed out.
# --------------------------------------------------------------------------- #
class _ViewerStub:
    """Minimal stand-in for ViewerWidget, holding a real Sketch."""

    def __init__(self):
        from widgets.viewer import ViewerWidget

        self.gamma_check_enabled = False
        self.exposure_check_enabled = False
        self.compare_enabled = False
        self.compare_qimage = None
        self.compare_mode = "wipe_vertical"
        self.display_rect = QtCore.QRect(0, 0, 200, 100)

        self.annotations = Sketch()
        self.annotations.set_frame(1)
        self.annotations.set_enabled(True)

        self.emitted = list()
        self.comment_requested = type(
            "_Signal", (), {"emit": lambda _self, value: self.emitted.append(value)}
        )()

        self.updates = 0

        # Bind the real implementations under test.
        self.mousePressEvent = ViewerWidget.mousePressEvent.__get__(self)
        self.widget_to_image_point = ViewerWidget.widget_to_image_point.__get__(self)

    def update(self):
        self.updates += 1


def _press(viewer, x, y, button=QtCore.Qt.MouseButton.LeftButton):
    event = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonPress,
        QtCore.QPointF(x, y),
        QtCore.QPointF(x, y),
        button,
        button,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    viewer.mousePressEvent(event)


def test_comment_tool_click_emits_the_hit_point(qapp):
    viewer = _ViewerStub()
    viewer.annotations.set_tool("comment")

    _press(viewer, 50, 25)

    assert len(viewer.emitted) == 1
    x, y = viewer.emitted[0]
    assert x == pytest.approx(0.25)
    assert y == pytest.approx(0.25)

    # The click must not become a stroke.
    assert viewer.annotations.strokes == {}
    assert viewer.annotations.drawing is False


def test_pencil_tool_still_draws(qapp):
    viewer = _ViewerStub()
    viewer.annotations.set_tool("pencil")

    _press(viewer, 50, 25)

    assert viewer.emitted == []
    assert len(viewer.annotations.strokes[1]) == 1
    assert viewer.annotations.strokes[1][0]["type"] == "pencil"


def test_comment_tool_never_creates_a_stroke(qapp):
    """Guard in the model itself, independent of the viewer.

    A {"type": "comment"} stroke would draw as nothing and would be silently
    dropped by erase(), which only re-appends stroke types it knows.
    """
    sketch = Sketch()
    sketch.set_frame(1)
    sketch.set_enabled(True)
    sketch.set_tool("comment")

    sketch.mousePressEvent((0.5, 0.5))
    sketch.mouseMoveEvent((0.6, 0.6))
    sketch.mouseReleaseEvent((0.7, 0.7))

    assert sketch.strokes == {}
    assert sketch.drawing is False
    assert sketch.undo_history == []
