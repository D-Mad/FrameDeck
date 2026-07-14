"""Tests for the arrow annotation tool (creation, render, hit-test, erase)."""

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter, QPixmap

from tests.helpers import probe_pixel
from widgets.annotations import Sketch


def _converter(width, height):
    """Map normalized (0-1) stroke coords to device pixels."""
    def convert(point):
        return QPointF(point[0] * width, point[1] * height)

    return convert


def _arrow(start=(0.2, 0.5), end=(0.8, 0.5)):
    return {
        "id": "arrow-1", "type": "arrow", "color": (255, 0, 0),
        "thickness": 4, "start": start, "end": end,
    }


def _render(sketch, width=200, height=100):
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(0, 0, 0))
    painter = QPainter(pixmap)
    try:
        sketch.draw(painter, point_converter=_converter(width, height))
    finally:
        painter.end()
    return pixmap.toImage()


# --------------------------------------------------------------------------- #
# Creation via the drawing interaction
# --------------------------------------------------------------------------- #
def test_drag_creates_arrow_stroke(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    sketch.set_tool("arrow")

    sketch.mousePressEvent((0.1, 0.1))
    sketch.mouseMoveEvent((0.6, 0.4))
    sketch.mouseReleaseEvent((0.7, 0.5))

    strokes = sketch.strokes[1]
    assert len(strokes) == 1
    assert strokes[0]["type"] == "arrow"
    assert strokes[0]["start"] == (0.1, 0.1)
    assert strokes[0]["end"] == (0.7, 0.5)


# --------------------------------------------------------------------------- #
# Rendering (real pixels)
# --------------------------------------------------------------------------- #
def test_arrow_renders_shaft_and_head(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    sketch.strokes[1] = [_arrow(start=(0.2, 0.5), end=(0.8, 0.5))]

    image = _render(sketch)

    # Mid-shaft (100, 50) is drawn in the stroke colour.
    red, green, _blue, _a = probe_pixel(image, 100, 50)
    assert red > 150 and green < 80

    # Just behind the tip the filled arrowhead covers the axis.
    assert probe_pixel(image, 155, 50)[0] > 150

    # Untouched background stays black.
    assert probe_pixel(image, 5, 5)[0] < 50


def test_degenerate_arrow_does_not_raise(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    sketch.strokes[1] = [_arrow(start=(0.5, 0.5), end=(0.5, 0.5))]
    _render(sketch)  # zero-length arrow: no direction, must not raise


# --------------------------------------------------------------------------- #
# Hit-testing uses the shaft, not the bounding box
# --------------------------------------------------------------------------- #
def test_hit_arrow_on_shaft_and_not_in_bbox_corner(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    diagonal = _arrow(start=(0.2, 0.2), end=(0.8, 0.8))
    sketch.strokes[1] = [diagonal]

    # On the line.
    assert sketch.hit_arrow(diagonal, (0.5, 0.5)) is True
    # Inside the bounding box but far from the shaft -> must miss.
    assert sketch.hit_arrow(diagonal, (0.8, 0.2)) is False

    assert sketch.hit_stroke((0.5, 0.5)) is diagonal
    assert sketch.hit_stroke((0.8, 0.2)) is None


# --------------------------------------------------------------------------- #
# Erase must not silently drop arrows (unknown types were being discarded)
# --------------------------------------------------------------------------- #
def test_erase_keeps_arrow_when_not_hit(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    sketch.strokes[1] = [_arrow()]

    sketch.erase((0.9, 0.05))  # nowhere near the shaft
    assert len(sketch.strokes[1]) == 1  # regression: arrow used to be dropped


def test_erase_removes_arrow_when_hit(qapp):
    sketch = Sketch()
    sketch.set_frame(1)
    sketch.strokes[1] = [_arrow()]

    sketch.erase((0.5, 0.5))  # directly on the shaft
    assert sketch.strokes[1] == []


# --------------------------------------------------------------------------- #
# Move
# --------------------------------------------------------------------------- #
def test_move_translates_arrow_endpoints(qapp):
    sketch = Sketch()
    arrow = _arrow(start=(0.2, 0.2), end=(0.6, 0.4))

    sketch.move_stroke(arrow, 0.1, -0.05)

    rounded = lambda pair: (round(pair[0], 6), round(pair[1], 6))
    assert rounded(arrow["start"]) == (0.3, 0.15)
    assert rounded(arrow["end"]) == (0.7, 0.35)
