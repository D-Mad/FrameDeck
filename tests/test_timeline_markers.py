"""Tests for the timeline's annotation markers.

The timeline is a plain QWidget, so these render it offscreen and probe the
actual pixels -- the assertions are about what a reviewer sees, not about what
the widget believes it stored.
"""

from types import SimpleNamespace

import pytest

import constants

from tests.helpers import probe_pixel
from widgets import MainWindow, notestore
from widgets.annotations import Sketch
from widgets.timeline import TimelineWidget


MARKER_Y = int(60 * 0.45) + 6  # inside the marker band


@pytest.fixture
def timeline(qapp):
    widget = TimelineWidget(None)
    widget.resize(900, 60)
    widget.set_range(1, 100)
    widget.set_current_frame(1)

    yield widget

    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def _marker_color(widget, frame):
    image = widget.grab().toImage()
    x = int(widget.frame_to_pos(frame))
    return probe_pixel(image, x, MARKER_Y)[:3]


class _MarkerSink:
    def set_annotated_frames(self, comments, drawings):
        self.comment_frames = set(comments)
        self.drawing_frames = set(drawings)


def _window_controller(source, sketch, entries):
    """Build only the controller surface refresh_timeline_markers requires."""
    timeline = _MarkerSink()
    window = SimpleNamespace(
        viewframe=SimpleNamespace(
            viewer=SimpleNamespace(annotations=sketch), timeline=timeline
        ),
        playlist_playback_active=True,
        playlist_entries=entries,
        current_source_filepath=source,
    )
    return window, timeline


def _entry(source, start, count):
    return {
        "context": {"media": source},
        "start": start,
        "end": start + count - 1,
        "count": count,
    }


# --------------------------------------------------------------------------- #
# What gets marked
# --------------------------------------------------------------------------- #
def test_a_commented_frame_is_marked(timeline):
    timeline.set_annotated_frames(comment_frames=[20], drawing_frames=[])

    assert _marker_color(timeline, 20) == constants.TIMELINE_COMMENT_MARKER_COLOR


def test_a_drawn_frame_is_marked_differently(timeline):
    timeline.set_annotated_frames(comment_frames=[], drawing_frames=[60])

    assert _marker_color(timeline, 60) == constants.TIMELINE_DRAWING_MARKER_COLOR


def test_a_frame_with_both_reads_as_a_comment(timeline):
    """The words are the reviewable part; the drawing marker must not hide them."""
    timeline.set_annotated_frames(comment_frames=[80], drawing_frames=[80])

    assert timeline.drawing_frames == set()  # subsumed, not drawn twice
    assert _marker_color(timeline, 80) == constants.TIMELINE_COMMENT_MARKER_COLOR


def test_an_unannotated_frame_is_not_marked(timeline):
    timeline.set_annotated_frames(comment_frames=[20], drawing_frames=[60])

    color = _marker_color(timeline, 40)

    assert color != constants.TIMELINE_COMMENT_MARKER_COLOR
    assert color != constants.TIMELINE_DRAWING_MARKER_COLOR


def test_clearing_the_markers_removes_them(timeline):
    timeline.set_annotated_frames(comment_frames=[20], drawing_frames=[])
    assert _marker_color(timeline, 20) == constants.TIMELINE_COMMENT_MARKER_COLOR

    timeline.set_annotated_frames(comment_frames=[], drawing_frames=[])

    assert _marker_color(timeline, 20) != constants.TIMELINE_COMMENT_MARKER_COLOR


# --------------------------------------------------------------------------- #
# Robustness
# --------------------------------------------------------------------------- #
def test_markers_outside_the_range_are_not_drawn(timeline):
    """A stale marker from a longer clip must not smear onto the edge."""
    timeline.set_annotated_frames(comment_frames=[500], drawing_frames=[-20])

    # Renders without error, and nothing lands at either end of the track.
    image = timeline.grab().toImage()
    left = probe_pixel(image, timeline.timeline_margin, MARKER_Y)[:3]
    right = probe_pixel(image, timeline.width() - timeline.timeline_margin, MARKER_Y)[:3]

    assert left != constants.TIMELINE_COMMENT_MARKER_COLOR
    assert right != constants.TIMELINE_COMMENT_MARKER_COLOR


def test_no_markers_renders_cleanly(timeline):
    timeline.set_annotated_frames(comment_frames=[], drawing_frames=[])

    assert timeline.comment_frames == set()
    assert timeline.drawing_frames == set()
    assert not timeline.grab().toImage().isNull()


def test_none_is_treated_as_empty(timeline):
    timeline.set_annotated_frames(None, None)

    assert timeline.comment_frames == set()
    assert timeline.drawing_frames == set()


def test_markers_accept_any_iterable(timeline):
    timeline.set_annotated_frames(comment_frames=(5, 6), drawing_frames=range(9, 11))

    assert timeline.comment_frames == {5, 6}
    assert timeline.drawing_frames == {9, 10}


def test_playlist_timeline_aggregates_active_memory_and_other_sidecars(
    tmp_path, monkeypatch, qapp
):
    monkeypatch.setenv("FRAMEDECK_PROFILE_ROOT", str(tmp_path))
    active_source = str(tmp_path / "active.mov")
    other_source = str(tmp_path / "other.mov")

    active = Sketch()
    active.comments[2] = [{"id": "active", "text": "memory edit"}]
    active.strokes[4] = [{"id": "draw-active", "type": "pencil"}]
    other = Sketch()
    other.comments[3] = [{"id": "other", "text": "saved note"}]
    other.strokes[8] = [{"id": "draw-other", "type": "pencil"}]
    notestore.save_notes(other_source, other)

    window, sink = _window_controller(
        active_source,
        active,
        [_entry(active_source, 1, 10), _entry(other_source, 11, 10)],
    )
    MainWindow.refresh_timeline_markers(window)

    assert sink.comment_frames == {2, 13}
    assert sink.drawing_frames == {4, 18}


def test_duplicate_playlist_shots_each_receive_the_source_markers(qapp):
    source = "same-shot.mov"
    sketch = Sketch()
    sketch.comments[2] = [{"id": "review", "text": "same source"}]
    sketch.strokes[6] = [{"id": "draw", "type": "pencil"}]
    window, sink = _window_controller(
        source,
        sketch,
        [_entry(source, 1, 10), _entry(source, 11, 10)],
    )

    MainWindow.refresh_timeline_markers(window)

    assert sink.comment_frames == {2, 12}
    assert sink.drawing_frames == {6, 16}


# --------------------------------------------------------------------------- #
# The playhead stays readable
# --------------------------------------------------------------------------- #
def test_the_playhead_is_drawn_over_a_marker_on_the_same_frame(timeline):
    """A note must never hide the frame the reviewer is actually sitting on."""
    timeline.set_current_frame(20)
    timeline.set_annotated_frames(comment_frames=[20], drawing_frames=[])

    image = timeline.grab().toImage()
    x = int(timeline.frame_to_pos(20))
    red, green, blue = probe_pixel(image, x, MARKER_Y)[:3]

    # The playhead is red; the marker is blue. Red wins on the shared pixel.
    assert red > green and red > blue
