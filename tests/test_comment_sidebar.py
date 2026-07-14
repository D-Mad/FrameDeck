"""Tests for the review-comment sidebar and viewer pin interaction."""

import pytest

from PySide6 import QtCore
from PySide6 import QtGui

from widgets.annotations import Sketch
from widgets.comments import CommentSidebar
from widgets.viewer import ViewerWidget
from tests.helpers import make_solid_mp4


@pytest.fixture
def sidebar(qapp):
    sketch = Sketch()
    sketch.add_comment(1, "opening note")
    done = sketch.add_comment(5, "resolved note", x=0.5, y=0.5)
    sketch.toggle_comment_done(5, done["id"])

    panel = CommentSidebar()
    panel.set_sketch(sketch)
    panel.set_source_available(True)
    panel.set_current_frame(1)
    return panel, sketch


def test_sidebar_lists_comments_and_filters_current_frame(sidebar):
    panel, _sketch = sidebar
    assert panel.commentTree.topLevelItemCount() == 2
    assert panel.countLabel.text() == "2"

    panel.scopeCombo.setCurrentIndex(panel.scopeCombo.findData("current"))
    assert panel.commentTree.topLevelItemCount() == 1
    assert panel.commentTree.topLevelItem(0).text(2) == "opening note"


def test_sidebar_filters_open_and_resolved(sidebar):
    panel, _sketch = sidebar
    panel.stateCombo.setCurrentIndex(panel.stateCombo.findData("open"))
    assert panel.commentTree.topLevelItemCount() == 1
    assert panel.commentTree.topLevelItem(0).text(0) == "OPEN"

    panel.stateCombo.setCurrentIndex(panel.stateCombo.findData("done"))
    assert panel.commentTree.topLevelItemCount() == 1
    assert panel.commentTree.topLevelItem(0).text(0) == "DONE"


def test_add_and_pin_requests_keep_editor_until_controller_confirms(sidebar):
    panel, _sketch = sidebar
    added = []
    pinned = []
    cancelled = []
    panel.add_requested.connect(added.append)
    panel.pin_requested.connect(pinned.append)
    panel.pin_cancel_requested.connect(lambda: cancelled.append(True))

    panel.editor.setPlainText("  inspect edge  ")
    panel.addButton.click()
    assert added == ["inspect edge"]
    assert panel.editor.toPlainText() == "  inspect edge  "

    panel.pinButton.click()
    assert pinned == ["inspect edge"]
    assert panel.pin_mode is True
    panel.pinButton.click()
    assert cancelled == [True]
    assert panel.pin_mode is False


def test_selected_comment_emits_navigation_and_resolve(sidebar):
    panel, _sketch = sidebar
    jumped = []
    toggled = []
    panel.jump_requested.connect(jumped.append)
    panel.done_requested.connect(lambda frame, comment_id: toggled.append((frame, comment_id)))

    item = panel.commentTree.topLevelItem(0)
    panel.commentTree.setCurrentItem(item)
    context = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
    panel.jumpButton.click()
    panel.resolveButton.click()

    assert jumped == [context["frame"]]
    assert toggled == [(context["frame"], context["id"])]


def test_no_source_disables_comment_creation(sidebar):
    panel, _sketch = sidebar
    panel.set_source_available(False)
    assert not panel.editor.isEnabled()
    assert not panel.addButton.isEnabled()
    assert not panel.pinButton.isEnabled()
    assert panel.frameLabel.text().endswith("NO MEDIA")


def test_viewer_pin_click_emits_normalized_image_coordinate(qapp):
    viewer = ViewerWidget()
    viewer.resize(200, 100)
    viewer.current_frame = 1
    viewer.display_rect = QtCore.QRectF(0, 0, 200, 100)
    received = []
    viewer.comment_pin_clicked.connect(lambda x, y: received.append((x, y)))
    viewer.set_comment_pin_mode(True)

    event = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonPress,
        QtCore.QPointF(50, 25),
        QtCore.QPointF(50, 25),
        QtCore.QPointF(50, 25),
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    viewer.mousePressEvent(event)

    assert received == pytest.approx([(0.25, 0.25)])
    assert event.isAccepted()


def test_main_window_adds_and_persists_sidebar_comment(
    tmp_path, monkeypatch, qapp
):
    from widgets import MainWindow
    from widgets import notestore

    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path / "profile"))
    source = make_solid_mp4(tmp_path / "review.mp4", frames=3)
    window = MainWindow()
    try:
        assert window.openMedia(str(source), add_to_playlist=False) is True
        assert window.commentSidebar.source_available is True
        assert window.actionComments.isChecked()
        assert not window.commentDock.isHidden()
        frame = window.viewframe.viewer.annotations.current_frame
        assert frame is not None

        window.add_frame_comment("controller note")
        assert window.viewframe.viewer.annotations.get_comments(frame)[0]["text"] == (
            "controller note"
        )
        assert notestore.notes_path_for(source).exists()

        window.commentSidebar.editor.setPlainText("pinned controller note")
        window.begin_pinned_comment("pinned controller note")
        assert window.viewframe.viewer.comment_pin_mode is True
        assert window.commentSidebar.pin_mode is True
        window.add_pinned_comment(0.2, 0.8)
        pinned = window.viewframe.viewer.annotations.get_comments(frame)[1]
        assert (pinned["x"], pinned["y"]) == (0.2, 0.8)
        assert window.viewframe.viewer.comment_pin_mode is False
        assert window.commentSidebar.editor.toPlainText() == ""
    finally:
        window.close()
        qapp.processEvents()
