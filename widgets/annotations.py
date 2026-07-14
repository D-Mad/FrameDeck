"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/annotations.py

Description:
    Sketch drawing engine for frame-based annotation system.
    Managing a full interactive sketching system on top of frame-based image/video data. It handles:


Responsibilities:
    - Freehand drawing (pencil strokes)
    - Geometric shapes (rectangle, ellipse)
    - Text annotations
    - Stroke selection and transformation (move tool)
    - Erasing with spatial hit detection
    - Undo system with granular action tracking
    - Overlay / watermark rendering system
    - Stroke hit-testing for interaction
    - Frame-wise stroke storage and retrieval
    - Qt-based rendering using QPainter

Features:
    1. Multi-tool drawing system:
        - Pencil (freehand polyline)
        - Rectangle (drag-to-draw)
        - Ellipse (drag-to-draw)
        - Text insertion tool
        - Move/transform tool
        - Eraser tool

    2. Frame-based annotation model:
        - Each frame stores independent stroke collections
        - Efficient lookup via dictionary mapping

    3. Interactive editing:
        - Stroke selection (hit-testing)
        - Move transformation with delta tracking
        - Partial erasing of pencil strokes

    4. Rendering system:
        - Qt QPainter-based rendering pipeline
        - Stroke-specific renderers (pencil/shape/text)
        - Selection highlighting
        - Overlay rendering (HUD/watermarks)

    5. Undo system:
        - Action-based undo stack
        - Supports create, erase, and move operations
        - Frame-scoped restoration

    6. Overlay system:
        - Multi-position overlays (top/bottom/center variants)
        - Supports text + image overlays
        - Opacity and font styling control

Architecture:
    The system follows a **state-driven procedural architecture**:

    Sketch (Main Controller)
        |
        |-- Stroke Storage (self.strokes)
        |       Frame → List[Stroke]
        |
        |-- Interaction Layer
        |       mousePressEvent()
        |       mouseMoveEvent()
        |       mouseReleaseEvent()
        |
        |-- Tool System
        |       pencil / rectangle / ellipse / text / move / erase
        |
        |-- Rendering Layer
        |       draw()
        |       draw_pencil()
        |       draw_rectangle()
        |       draw_text()
        |
        |-- Utility Layer
        |       hit testing
        |       selection detection
        |       bounding box computation
        |
        |-- Undo System
        |       undo_history stack

Notes:
    - This system uses **dictionary-based stroke objects** for flexibility instead of strict classes (performance vs flexibility tradeoff).
    - Coordinates are stored in image space (not screen space) and optionally converted during rendering using `point_converter`.
    - Eraser uses geometric hit-testing rather than pixel manipulation, allowing resolution-independent editing.
    - Undo system is intentionally lightweight and snapshot-based for reliability (not delta-compressed).
    - Text rendering relies on QFontMetrics for bounding box calculation, ensuring accurate hit detection.
    - Overlay system is designed as a HUD layer independent of stroke data.

    - Keep stroke schema backward compatible (critical for saved projects)
    - Avoid changing coordinate system without migration plan
    - Undo stack may grow large in long sessions → consider pruning
    - Overlay system may be refactored into a separate module in future
    - Consider migrating stroke dicts → dataclass for long-term maintainability
"""

from __future__ import absolute_import

import copy
import datetime
import math
import uuid

import constants

from PySide6 import QtGui
from PySide6 import QtCore

from widgets.styles import Font
from widgets.styles import StrokePen


class Sketch(object):
    """
    Frame-based sketch stroke manager.

    This class stores freehand drawing strokes for each frame and provides methods for creating, editing, clearing, and rendering sketches.

    Notes:
        stroke points should be stored as normalized
        coordinates (0.0 - 1.0) relative to the displayed image.

    Example:
        {
            1001: [
                {
                    "color": (255, 0, 0),
                    "thickness": 3,
                    "points": [
                        (0.25, 0.50),
                        (0.30, 0.55)
                    ]
                }
            ]
        }
    """

    def __init__(self):
        """
        Initialize sketch manager.
        """

        # ----------------------------
        # Tool state
        # ----------------------------
        # Current active stroke tool.
        self.tool = "pencil"

        # ----------------------------
        # Frame state
        # ----------------------------
        # Current Active Frame
        self.current_frame = None

        # ----------------------------
        # Interaction state
        # ----------------------------
        # Global drawing enabled flag
        self.enabled = False

        # Mouse drag in progress
        self.drawing = False

        # Brush configuration, active brush color
        self.color = constants.DEFAULT_SKETCH_COLOR

        # ----------------------------
        # Brush configuration
        # ----------------------------
        # Active stroke thickness
        self.thickness = 3

        # Brush configuration, active eraser radius
        self.eraser_radius = 0.02

        # ----------------------------
        # Stroke tracking
        # ----------------------------
        # Currently drawing stroke
        self.current_shape = None

        # Legacy reference (unused in logic)
        self.current_stroke = None

        # Stroke selected for move
        self.selected_stroke = None

        # Drag start position
        self.move_start = None

        # Backup before move
        self.original_stroke = None

        # ----------------------------
        # Frame storage
        # ----------------------------
        # Stroke Storage
        self.strokes = dict()

        # Comment storage: frame -> list of comment dicts. Comments are text
        # notes, optionally pinned to a normalized (x, y) point on the frame.
        self.comments = dict()

        # ----------------------------
        # Image configuration
        # ----------------------------
        self.image_width = 1920
        self.image_height = 1080

        # ----------------------------
        # Text tool configuration
        # ----------------------------
        self.txt_font = None

        # ----------------------------
        # Temporary UI state
        # ----------------------------
        self.drag_start = None
        self.drag_end = None
        self.preview_shape = None

        # ----------------------------
        # Overlay system
        # ----------------------------
        self.overlays = {
            "top_left": dict(),
            "top_right": dict(),
            "top_center": dict(),
            "center": dict(),
            "bottom_left": dict(),
            "bottom_right": dict(),
            "bottom_center": dict(),
        }

        # ----------------------------
        # Undo system
        # ----------------------------
        self.undo_history = list()
        self.redo_history = list()

    def set_tool(self, tool):
        """
        Set active stroke tool.

        Args:
            tool (str):
                Tool name ("pencil", "eraser").
        """
        self.tool = tool

    def set_enabled(self, enabled):
        """
        Enable or disable stroke drawing.

        Args:
            enabled (bool): Pencil tool state.
        """

        self.enabled = enabled

    def set_frame(self, frame):
        """
        Set current active frame.

        Args:
            frame (int):
                Current frame number.
        """

        self.current_frame = frame

    def set_color(self, color):
        """
        Set active brush color.

        Args:
            color (tuple):
                RGB color tuple.
        """

        self.color = color or self.color

    def set_thickness(self, value):
        """
        Set active brush thickness.

        Args:
            value (int):
                Line thickness.
        """

        self.thickness = max(1, int(value))

    def set_eraser_radius(self, value):
        """
        Set eraser radius in image pixels.

        Args:
            value (int):
                Radius in pixels.

            5    # very small
            10   # small
            20   # medium
            40   # large
            80   # huge
        """

        self.eraser_radius = max(1, int(value))

    def set_image_size(self, width, height):
        """
        Store source image size.

        Args:
            width (int):
                Source image width.

            height (int):
                Source image height.
        """

        self.image_width = max(width, 1)
        self.image_height = max(height, 1)

    def set_txt_font(self, values):
        """
        Set text tool configuration.

        Args:
            values (dict): Font/text metadata.
        """

        self.txt_font = values

    def get_strokes(self):
        """
        Return strokes for current frame.

        Returns:
            list:
                Frame stroke list.
        """

        if self.current_frame is None:
            return list()

        return self.strokes.get(self.current_frame, list())

    def has_strokes(self):
        """
        Check whether current frame contains sketches.

        Returns:
            bool
        """

        if self.current_frame is None:
            return False

        return bool(self.strokes.get(self.current_frame))

    def frame_count(self):
        """
        Return number of annotated frames.

        Returns:
            int
        """

        return len(self.strokes)

    def annotated_frames(self):
        """Return sorted frames holding at least one stroke or comment."""
        frames = {frame for frame, strokes in self.strokes.items() if strokes}
        frames.update(
            frame for frame, comments in self.comments.items() if comments
        )
        return sorted(frames)

    # ----------------------------------------------------------------------- #
    # Comments
    # ----------------------------------------------------------------------- #
    def add_comment(self, frame, text, x=None, y=None):
        """Add a text comment to *frame*.

        Pass normalized ``x``/``y`` (0.0-1.0) to pin the comment to a point on
        the frame; omit them for a frame-level note. Empty text is ignored.

        Returns:
            dict | None: The stored comment, or None when *text* was blank.
        """

        text = str(text or "").strip()
        if not text:
            return None

        comment = {
            "id": self.generate_id(),
            "text": text,
            "timestamp": datetime.datetime.now().strftime(constants.DATE_TIME_FORMAT),
            "done": False,
        }

        if x is not None and y is not None:
            comment["x"] = max(0.0, min(1.0, float(x)))
            comment["y"] = max(0.0, min(1.0, float(y)))

        self.comments.setdefault(int(frame), list()).append(comment)
        return comment

    def get_comments(self, frame=None):
        """Return the comment list for *frame* (defaults to the current frame)."""
        if frame is None:
            frame = self.current_frame
        if frame is None:
            return list()
        return self.comments.get(int(frame), list())

    def delete_comment(self, frame, comment_id):
        """Remove a comment by id. Returns True when one was removed."""
        frame = int(frame)
        existing = self.comments.get(frame)
        if not existing:
            return False

        remaining = [
            comment for comment in existing if comment.get("id") != comment_id
        ]
        if len(remaining) == len(existing):
            return False

        if remaining:
            self.comments[frame] = remaining
        else:
            del self.comments[frame]
        return True

    def toggle_comment_done(self, frame, comment_id):
        """Flip a comment's done flag. Returns the new state, or None if absent."""
        for comment in self.comments.get(int(frame), list()):
            if comment.get("id") == comment_id:
                comment["done"] = not comment.get("done", False)
                return comment["done"]
        return None

    def commented_frames(self):
        """Return sorted frame numbers that hold at least one comment."""
        return sorted(
            frame for frame, comments in self.comments.items() if comments
        )

    def comment_count(self):
        """Return the total number of comments across every frame."""
        return sum(len(comments) for comments in self.comments.values())

    def draw_comment_pins(self, painter, point_converter=None):
        """Draw numbered markers for the current frame's pinned comments.

        Numbering follows the frame's comment order, so a marker's number
        matches its row in the comment list. Done comments use a distinct fill.
        """

        comments = self.get_comments()
        if not any("x" in comment and "y" in comment for comment in comments):
            return

        radius = constants.COMMENT_PIN_RADIUS

        painter.save()
        for number, comment in enumerate(comments, start=1):
            if "x" not in comment or "y" not in comment:
                continue
            point = (comment["x"], comment["y"])
            point = point_converter(point) if point_converter else QtCore.QPointF(*point)

            fill = (
                constants.COMMENT_PIN_DONE_COLOR
                if comment.get("done")
                else constants.COMMENT_PIN_COLOR
            )

            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 1.5))
            painter.setBrush(QtGui.QColor(*fill))
            painter.drawEllipse(point, radius, radius)

            font = painter.font()
            font.setBold(True)
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QtGui.QColor(255, 255, 255))
            painter.drawText(
                QtCore.QRectF(
                    point.x() - radius,
                    point.y() - radius,
                    radius * 2,
                    radius * 2,
                ),
                QtCore.Qt.AlignCenter,
                str(number),
            )
        painter.restore()

    def serialize_comments(self):
        """Return a JSON-serializable snapshot of every frame's comments."""
        return {
            str(frame): copy.deepcopy(comments)
            for frame, comments in self.comments.items()
            if comments
        }

    def deserialize_comments(self, data):
        """Replace all comments from a :meth:`serialize_comments` snapshot."""
        self.comments = dict()
        items = data.items() if isinstance(data, dict) else ()
        for frame_key, comments in items:
            try:
                frame = int(frame_key)
            except (TypeError, ValueError):
                continue
            if not isinstance(comments, list):
                continue
            restored = [
                dict(comment)
                for comment in comments
                if isinstance(comment, dict) and comment.get("text")
            ]
            if restored:
                self.comments[frame] = restored

    def serialize(self):
        """Return a JSON-serializable snapshot of every frame's strokes.

        Frame numbers become string keys (JSON object keys must be strings) and
        coordinate/color tuples serialize to lists. Empty frames are omitted.
        """
        return {
            str(frame): copy.deepcopy(strokes)
            for frame, strokes in self.strokes.items()
            if strokes
        }

    def deserialize(self, data):
        """Replace all strokes from a snapshot produced by :meth:`serialize`.

        Coordinate/color fields are converted back from lists to tuples so the
        loaded strokes render identically to freshly drawn ones. Undo/redo
        history is reset -- the loaded state becomes the new baseline.
        """
        self.strokes = dict()
        items = data.items() if isinstance(data, dict) else ()
        for frame_key, strokes in items:
            try:
                frame = int(frame_key)
            except (TypeError, ValueError):
                continue
            if not isinstance(strokes, list):
                continue
            restored = [
                self._restore_stroke(stroke)
                for stroke in strokes
                if isinstance(stroke, dict)
            ]
            if restored:
                self.strokes[frame] = restored
        self.undo_history.clear()
        self.redo_history.clear()

    @staticmethod
    def _restore_stroke(stroke):
        """Convert a stroke's JSON list coordinates/colour back to tuples."""
        restored = dict(stroke)
        points = restored.get("points")
        if isinstance(points, list):
            restored["points"] = [tuple(point) for point in points]
        for key in ("start", "end", "position", "move_start"):
            value = restored.get(key)
            if isinstance(value, list):
                restored[key] = tuple(value)
        color = restored.get("color")
        if isinstance(color, list):
            restored["color"] = tuple(color)
        return restored

    def generate_id(self):
        """
        Generate unique stroke ID.

        Returns:
            str: UUID string.
        """

        return str(uuid.uuid4())

    def mousePressEvent(self, point):
        """
        Handle mouse press event.

        Args:
            point (tuple): Cursor position.
        """

        if self.current_frame is None:
            return

        # Enable drag operation
        self.drawing = True

        # Move Tool
        if self.tool == "move":
            self.selected_stroke = self.hit_stroke(point)

            if self.selected_stroke:
                self.move_start = point
                self.original_stroke = copy.deepcopy(self.selected_stroke)

            return

        # Eraser
        if self.tool == "eraser":
            # Save current frame state ONCE
            self._record_action(
                {
                    "type": "erase",
                    "frame": self.current_frame,
                    "strokes": copy.deepcopy(self.strokes.get(self.current_frame, list())),
                }
            )

            self.drawing = True
            self.erase(point)

            return

        # Text
        if self.tool == "txt":
            if self.txt_font.get("txt"):
                stroke = self.txt_font.copy()

                stroke["id"] = self.generate_id()
                stroke["type"] = "txt"
                stroke["position"] = point

                self.strokes.setdefault(self.current_frame, [])
                self.strokes[self.current_frame].append(stroke)

                self._record_action(
                    {
                        "type": "create",
                        "frame": self.current_frame,
                        "stroke_id": stroke["id"],
                    }
                )

            return

        # Stroke (shapes)
        stroke = {
            "id": self.generate_id(),
            "type": self.tool,
            "color": self.color,
            "thickness": self.thickness,
        }

        # Pencil
        if self.tool == "pencil":
            stroke["points"] = [point]

        # Rectangle / Ellipse / Arrow
        elif self.tool in ["rectangle", "ellipse", "arrow"]:
            stroke["start"] = point
            stroke["end"] = point

        self.current_shape = stroke

        self.strokes.setdefault(self.current_frame, list())
        self.strokes[self.current_frame].append(stroke)

    def mouseMoveEvent(self, point):
        """
        Update current drawing operation.

        Args:
            point (tuple): Cursor position.
        """

        if not self.drawing:
            return

        # Move Tool
        if self.tool == "move":
            if not self.selected_stroke:
                return

            dx = point[0] - self.move_start[0]
            dy = point[1] - self.move_start[1]

            self.move_stroke(self.selected_stroke, dx, dy)
            self.move_start = point

            return

        # Eraser
        if self.tool == "eraser":
            self.erase(point)
            return

        if self.tool == "txt":
            return

        if not self.current_shape:
            return

        typed = self.current_shape["type"]

        # Pencil
        if typed == "pencil":
            self.current_shape["points"].append(point)

        # Rectangle / Ellipse / Arrow
        elif typed in ["rectangle", "ellipse", "arrow"]:
            self.current_shape["end"] = point

    def mouseReleaseEvent(self, point):
        """
        Finish drawing operation.

        Args:
            point (tuple): Cursor position.
        """

        if not self.drawing:
            return

        # Move Tool
        if self.tool == "move":

            if self.selected_stroke and self.original_stroke:
                self._record_action(
                    {
                        "type": "move",
                        "stroke_id": self.selected_stroke["id"],
                        "old_data": self.original_stroke,
                    }
                )

            self.selected_stroke = None
            self.original_stroke = None
            self.drawing = False

            return

        # Eraser
        if self.tool == "eraser":
            self.drawing = False
            return

        if self.tool == "txt":
            return

        # Final Shape Update
        if self.current_shape:
            typed = self.current_shape["type"]

            if typed in ["rectangle", "ellipse", "arrow"]:
                self.current_shape["end"] = point

            self._record_action(
                {
                    "type": "create",
                    "frame": self.current_frame,
                    "stroke_id": self.current_shape["id"],
                }
            )

        self.drawing = False
        self.current_shape = None

    def draw(self, painter, point_converter=None, rect=None):
        """
        Render all strokes for the current frame.

        This is the main rendering entry point. It iterates through all stored strokes and dispatches drawing to shape-specific renderers.

        Args:
            painter (QtGui.QPainter):
                Active Qt painter used for rendering.

            point_converter (callable, optional):
                Function to convert logical image coordinates to screen coordinates.

            rect (QtCore.QRect, optional):
                Viewport rectangle used for overlay rendering.

        Returns:
            None
        """

        # No frame selected → nothing to render
        if self.current_frame is None:
            return

        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)

        # Retrieve strokes for current frame
        strokes = self.get_strokes()

        for stroke in strokes:
            typed = stroke["type"]

            # Pencil
            if typed == "pencil":
                pen = StrokePen(stroke["color"], thickness=stroke["thickness"])
                painter.setPen(pen)
                self.draw_pencil(painter, stroke, point_converter)

            # Rectangle
            elif typed == "rectangle":
                pen = StrokePen(stroke["color"], thickness=stroke["thickness"])
                painter.setPen(pen)
                self.draw_rectangle(painter, stroke, point_converter)

            # Ellipse
            elif typed == "ellipse":
                pen = StrokePen(stroke["color"], thickness=stroke["thickness"])
                painter.setPen(pen)

                self.draw_ellipse(painter, stroke, point_converter)

            # Arrow
            elif typed == "arrow":
                pen = StrokePen(stroke["color"], thickness=stroke["thickness"])
                painter.setPen(pen)
                self.draw_arrow(painter, stroke, point_converter)

            # Text
            elif typed == "txt":
                self.draw_text(painter, stroke, point_converter)

            # Draw selection box for selected stroke
            if stroke is self.selected_stroke:
                self.draw_selection(painter, stroke, point_converter)

        # Draw pinned comment markers above the strokes
        self.draw_comment_pins(painter, point_converter)

        # Draw Watermarks
        if rect:
            self.draw_overlays(painter, rect)

    def draw_pencil(self, painter, stroke, point_converter=None):
        """
        Draw freehand pencil stroke as connected line segments.

        Args:
            painter (QtGui.QPainter):
                Active painter.

            stroke (dict):
                Stroke containing list of points.

            point_converter (callable, optional):
                Coordinate transformation function.

        Returns:
            None
        """
        points = stroke["points"]

        # Need at least 2 points to form a line
        if len(points) < 2:
            return

        # Draw segment-by-segment
        for index in range(len(points) - 1):
            point1 = points[index]
            point2 = points[index + 1]

            # Convert coordinates if needed
            if point_converter:
                point1 = point_converter(point1)
                point2 = point_converter(point2)

            painter.drawLine(point1, point2)

    def draw_ellipse(self, painter, stroke, point_converter=None):
        """
        Draw rectangular shape using start and end points.

        Args:
            painter (QtGui.QPainter): Active painter.
            stroke (dict): Stroke containing 'start' and 'end'.
            point_converter (callable, optional): Coordinate transform.

        Returns:
            None
        """

        point1 = stroke["start"]
        point2 = stroke["end"]

        # Convert coordinates if required
        if point_converter:
            point1 = point_converter(point1)
            point2 = point_converter(point2)

        # Normalize rectangle (handles drag direction)
        rect = QtCore.QRectF(point1, point2).normalized()

        painter.drawEllipse(rect)

    def draw_rectangle(self, painter, stroke, point_converter=None):
        """
        Draw ellipse shape using bounding rectangle.

        Args:
            painter (QtGui.QPainter): Active painter.
            stroke (dict): Stroke containing start/end points.
            point_converter (callable, optional): Coordinate transform.

        Returns:
            None
        """

        point1 = stroke["start"]
        point2 = stroke["end"]

        if point_converter:
            point1 = point_converter(point1)
            point2 = point_converter(point2)

        # Ellipse is defined by bounding rectangle
        rect = QtCore.QRectF(point1, point2).normalized()

        painter.drawRect(rect)

    def draw_arrow(self, painter, stroke, point_converter=None):
        """
        Draw an arrow: a straight shaft with a filled head at the end point.

        The head is sized from the shaft length in device space, so it stays
        proportional at any zoom level and never overwhelms a short arrow.

        Args:
            painter (QtGui.QPainter): Active painter.
            stroke (dict): Stroke containing start/end points.
            point_converter (callable, optional): Coordinate transform.

        Returns:
            None
        """

        point1 = stroke["start"]
        point2 = stroke["end"]

        if point_converter:
            point1 = point_converter(point1)
            point2 = point_converter(point2)

        # Shaft
        painter.drawLine(point1, point2)

        delta_x = point2.x() - point1.x()
        delta_y = point2.y() - point1.y()
        length = math.hypot(delta_x, delta_y)

        # Degenerate arrow (click without drag) has no direction to point in.
        if length <= 0.0:
            return

        head = min(20.0, length * 0.3)
        angle = math.atan2(delta_y, delta_x)
        spread = math.radians(25.0)

        left = QtCore.QPointF(
            point2.x() - head * math.cos(angle - spread),
            point2.y() - head * math.sin(angle - spread),
        )
        right = QtCore.QPointF(
            point2.x() - head * math.cos(angle + spread),
            point2.y() - head * math.sin(angle + spread),
        )

        path = QtGui.QPainterPath()
        path.moveTo(point2)
        path.lineTo(left)
        path.lineTo(right)
        path.closeSubpath()

        painter.fillPath(path, QtGui.QColor(*stroke["color"]))

    def draw_text(self, painter, stroke, point_converter=None):
        """
        Render text annotation on canvas.

        This method:
            - Configures QFont from stroke data
            - Computes text metrics
            - Stores bounding box for hit-testing
            - Draws text at specified position

        Args:
            painter (QtGui.QPainter): Active painter.
            stroke (dict): Text stroke dictionary.
            point_converter (callable, optional): Coordinate transform.

        Returns:
            None
        """

        # Text anchor position
        point = stroke["position"]

        if point_converter:
            draw_point = point_converter(point)
        else:
            draw_point = point

        # Font setup
        font = QtGui.QFont()

        font.setFamily(stroke.get("family", None))
        font.setPointSize(stroke.get("font_size", 24))
        font.setBold(stroke.get("bold", False))
        font.setItalic(stroke.get("italic", False))
        font.setUnderline(stroke.get("underline", False))
        font.setStrikeOut(stroke.get("strike_out", False))

        painter.setFont(font)

        # Font Metrics
        metrics = QtGui.QFontMetrics(font)
        text = stroke["txt"]

        width = metrics.horizontalAdvance(text)
        height = metrics.height()
        ascent = metrics.ascent()

        # Store bounds for hit-testing (important for selection)
        stroke["bounds"] = {
            "x": point[0],
            "y": point[1],
            "width": width,
            "height": height,
            "ascent": ascent,
        }

        # Draw
        painter.setPen(QtGui.QColor(*stroke["color"]))
        painter.drawText(draw_point, text)

    def erase(self, point):
        """
        Erase strokes based on proximity to pointer position.

        This method:
            - Checks all strokes in current frame
            - Removes or splits strokes depending on type
            - Uses geometric hit-testing instead of pixel deletion

        Args:
            point (tuple): Cursor position.

        Returns:
            None
        """

        strokes = self.get_strokes()

        if not strokes:
            return

        new_strokes = list()

        for stroke in strokes:
            typed = stroke.get("type", "pencil")

            # Pencil
            if typed == "pencil":
                new_strokes.extend(self.hit_pencil(stroke, point))

            # Rectangle
            elif typed == "rectangle":
                if not self.hit_rectangle(stroke, point):
                    new_strokes.append(stroke)

            # Ellipse
            elif typed == "ellipse":
                if not self.hit_ellipse(stroke, point):
                    new_strokes.append(stroke)

            # Arrow
            elif typed == "arrow":
                if not self.hit_arrow(stroke, point):
                    new_strokes.append(stroke)

            # Text
            elif typed == "txt":
                if not self.hit_txt(stroke, point):
                    new_strokes.append(stroke)

        # Replace frame strokes after erase operation
        self.strokes[self.current_frame] = new_strokes

    def move_stroke(self, stroke, dx, dy):
        """
        Translate a stroke by a delta offset.

        Supports:
            - Pencil strokes (list of points)
            - Rectangle/Ellipse (start/end)
            - Text (position)

        Args:
            stroke (dict): Stroke to move.
            dx (float): Delta X.
            dy (float): Delta Y.

        Returns:
            None
        """

        typed = stroke["type"]

        # Pencil
        if typed == "pencil":
            stroke["points"] = [(x + dx, y + dy) for x, y in stroke["points"]]

        # Shapes (Rectangle, Ellipse, Arrow)
        elif typed in ["rectangle", "ellipse", "arrow"]:
            x1, y1 = stroke["start"]
            x2, y2 = stroke["end"]

            stroke["start"] = (x1 + dx, y1 + dy)
            stroke["end"] = (x2 + dx, y2 + dy)

        # Text
        elif typed == "txt":
            x, y = stroke["position"]
            stroke["position"] = (x + dx, y + dy)

    def get_stroke_rect(self, stroke, point_converter=None):
        """
        Compute bounding rectangle of a stroke for selection and hit-testing.

        Supports:
            - Pencil (polyline bounds)
            - Rectangle / Ellipse (start-end bounds)
            - Text (font metrics bounds)

        Args:
            stroke (dict): Stroke data.
            point_converter (callable, optional): Coordinate transform.

        Returns:
            QtCore.QRectF: Bounding rectangle of stroke.
        """

        # Pencil
        if stroke["type"] == "pencil":
            points = stroke["points"]

            # Convert points if required
            converted = [point_converter(p) if point_converter else p for p in points]

            xs = [p.x() for p in converted]
            ys = [p.y() for p in converted]

            rect = QtCore.QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

            return rect

        # Shapes (Rectangle, Ellipse, Arrow)
        elif stroke["type"] in ["rectangle", "ellipse", "arrow"]:
            p1 = stroke["start"]
            p2 = stroke["end"]

            if point_converter:
                p1 = point_converter(p1)
                p2 = point_converter(p2)

            rect = QtCore.QRectF(p1, p2).normalized()

            return rect

        # Text
        elif stroke["type"] == "txt":
            point = stroke["position"]

            if point_converter:
                point = point_converter(point)

            font = QtGui.QFont()
            font.setPointSize(stroke.get("font_size", 24))

            metrics = QtGui.QFontMetrics(font)
            rect = metrics.boundingRect(stroke["txt"])

            # Align rect to text position (top-left baseline correction)
            rect.moveTo(point.x(), point.y() - rect.height())

            return QtCore.QRectF(rect)

    def draw_selection(self, painter, stroke, point_converter=None):
        """
        Draw selection outline around a stroke.

        Used when a stroke is active or selected.

        Args:
            painter (QtGui.QPainter): Active painter.
            stroke (dict): Selected stroke.
            point_converter (callable, optional): Coordinate transform.

        Returns:
            None
        """

        rect = self.get_stroke_rect(stroke, point_converter)

        if rect is None:
            return

        # Blue dashed selection pen
        pen = StrokePen(stroke["color"], thickness=2)
        painter.setPen(pen)
        painter.setPen(pen)
        painter.drawRect(rect)

    def _record_action(self, action):
        """Record an undoable action and invalidate the redo stack.

        Any new edit clears the redo history, matching standard undo/redo
        semantics -- you cannot redo past a fresh change.
        """
        self.undo_history.append(action)
        self.redo_history.clear()

    def undo(self):
        """
        Undo last action (create, move, erase).

        Undo system is snapshot-based and supports:
            - Create: remove stroke by ID
            - Move: restore previous stroke state
            - Erase: restore full frame snapshot

        The full pre-undo stroke state is captured onto the redo stack so the
        action can be reapplied by :meth:`redo`.

        Returns:
            None
        """

        if not self.undo_history:
            return

        action = self.undo_history.pop()

        # Snapshot the state we are about to leave so redo() can restore it.
        pre_undo = copy.deepcopy(self.strokes)

        # Create undo
        if action["type"] == "create":
            frame = action["frame"]
            stroke_id = action["stroke_id"]

            if frame in self.strokes:
                self.strokes[frame] = [
                    stroke for stroke in self.strokes[frame] if stroke["id"] != stroke_id
                ]

                # Remove frame entry if empty
                if not self.strokes[frame]:
                    del self.strokes[frame]

        # Move undo
        elif action["type"] == "move":
            stroke = self.find_stroke(action["stroke_id"])

            if stroke:
                stroke.clear()
                stroke.update(copy.deepcopy(action["old_data"]))

        # Erase undo
        elif action["type"] == "erase":
            self.strokes[action["frame"]] = copy.deepcopy(action["strokes"])

        self.redo_history.append({"action": action, "strokes": pre_undo})

    def redo(self):
        """
        Reapply the most recently undone action.

        Restores the stroke state captured by :meth:`undo` (mutating the
        existing ``strokes`` dict in place so held references stay valid) and
        pushes the action back onto the undo stack.

        Returns:
            None
        """

        if not self.redo_history:
            return

        entry = self.redo_history.pop()
        self.strokes.clear()
        self.strokes.update(copy.deepcopy(entry["strokes"]))
        self.undo_history.append(entry["action"])

    def find_stroke(self, stroke_id):
        """
        Find a stroke by its unique ID across all frames.

        Args:
            stroke_id (str): Stroke UUID.

        Returns:
            dict | None: Stroke if found, else None.
        """

        # Search all frames
        for frame_strokes in self.strokes.values():
            for stroke in frame_strokes:
                if stroke.get("id") == stroke_id:
                    return stroke

        return None

    def hit_pencil(self, stroke, point):
        """
        Erase logic for pencil strokes using segment splitting.

        This method:
            - Splits stroke into multiple segments
            - Removes points within eraser radius
            - Returns remaining stroke fragments

        Args:
            stroke (dict): Pencil stroke.
            point (tuple): Eraser position.

        Returns:
            list: New stroke fragments.
        """

        radius_x = self.eraser_radius / float(self.image_width)
        radius_y = self.eraser_radius / float(self.image_height)

        segments = list()
        current_segment = list()

        for p in stroke["points"]:
            dx = (p[0] - point[0]) / radius_x
            dy = (p[1] - point[1]) / radius_y

            inside = (dx * dx + dy * dy) <= 1.0

            if inside:
                # Flush current segment if valid
                if len(current_segment) > 1:
                    segments.append(
                        {
                            "id": self.generate_id(),
                            "type": "pencil",
                            "points": current_segment,
                            "color": stroke["color"],
                            "thickness": stroke["thickness"],
                        }
                    )
                current_segment = list()
            else:
                current_segment.append(p)

        # Add last segment
        if len(current_segment) > 1:
            segments.append(
                {
                    "id": self.generate_id(),
                    "type": "pencil",
                    "points": current_segment,
                    "color": stroke["color"],
                    "thickness": stroke["thickness"],
                }
            )

        return segments

    def hit_rectangle(self, stroke, point):
        """
        Check if a point lies inside a rectangle stroke.

        Args:
            stroke (dict): Rectangle stroke.
            point (tuple): Test point.

        Returns:
            bool: True if inside rectangle.
        """

        p1 = stroke["start"]
        p2 = stroke["end"]

        xmin = min(p1[0], p2[0])
        xmax = max(p1[0], p2[0])

        ymin = min(p1[1], p2[1])
        ymax = max(p1[1], p2[1])

        px, py = point

        return xmin <= px <= xmax and ymin <= py <= ymax

    def hit_ellipse(self, stroke, point):
        """
        Check if a point lies inside an ellipse stroke.

        Uses normalized ellipse equation:
            (x^2 / rx^2) + (y^2 / ry^2) <= 1

        Args:
            stroke (dict): Ellipse stroke.
            point (tuple): Test point.

        Returns:
            bool: True if inside ellipse.
        """

        p1 = stroke["start"]
        p2 = stroke["end"]

        cx = (p1[0] + p2[0]) * 0.5
        cy = (p1[1] + p2[1]) * 0.5

        rx = abs(p2[0] - p1[0]) * 0.5
        ry = abs(p2[1] - p1[1]) * 0.5

        if rx <= 0 or ry <= 0:
            return False

        px = point[0] - cx
        py = point[1] - cy

        value = ((px * px) / (rx * rx)) + ((py * py) / (ry * ry))

        return value <= 1.0

    def hit_txt(self, stroke, point):
        """
        Check if a point intersects a text stroke bounding box.

        Args:
            stroke (dict): Text stroke.
            point (tuple): Test point (normalized or image space).

        Returns:
            bool: True if inside text bounds.
        """

        bounds = stroke.get("bounds")

        if not bounds:
            return False

        # Convert mouse position to image space
        px = point[0] * self.image_width
        py = point[1] * self.image_height

        # Convert text origin to image space
        tx = bounds["x"] * self.image_width
        ty = bounds["y"] * self.image_height

        left = tx
        right = tx + bounds["width"]

        top = ty - bounds["ascent"]
        bottom = top + bounds["height"]

        return left <= px <= right and top <= py <= bottom

    def hit_stroke(self, point):
        """
        Detect which stroke is under cursor.

        Checks strokes in reverse order (top-most first).

        Args:
            point (tuple): Cursor position.

        Returns:
            dict | None: Hit stroke or None.
        """

        strokes = self.get_strokes()

        # Reverse for proper layering (last drawn = top)
        for stroke in reversed(strokes):
            typed = stroke["type"]

            if typed == "txt":
                if self.hit_txt(stroke, point):
                    return stroke

            elif typed == "rectangle":
                if self.hit_rectangle(stroke, point):
                    return stroke

            elif typed == "ellipse":
                if self.hit_ellipse(stroke, point):
                    return stroke

            elif typed == "arrow":
                if self.hit_arrow(stroke, point):
                    return stroke

            elif typed == "pencil":
                if self.hit_pencil_move(stroke, point):
                    return stroke
        return None

    def hit_arrow(self, stroke, point, radius=0.01):
        """
        Hit-test an arrow by proximity to its shaft.

        Measures the distance from *point* to the arrow's line segment (not its
        bounding box), so a diagonal arrow is only picked near the line itself.

        Args:
            stroke (dict): Arrow stroke with start/end points.
            point (tuple): Cursor position.
            radius (float): Pick tolerance in normalized units.

        Returns:
            bool: True if the point lies within *radius* of the shaft.
        """

        x1, y1 = stroke["start"]
        x2, y2 = stroke["end"]
        px, py = point[0], point[1]

        delta_x = x2 - x1
        delta_y = y2 - y1
        length_squared = delta_x * delta_x + delta_y * delta_y

        if length_squared <= 0.0:
            # Degenerate arrow: fall back to a point check.
            return ((px - x1) ** 2 + (py - y1) ** 2) <= radius * radius

        # Project onto the segment, clamped so the ends do not extend the pick.
        along = ((px - x1) * delta_x + (py - y1) * delta_y) / length_squared
        along = max(0.0, min(1.0, along))

        nearest_x = x1 + along * delta_x
        nearest_y = y1 + along * delta_y

        distance_squared = (px - nearest_x) ** 2 + (py - nearest_y) ** 2
        return distance_squared <= radius * radius

    def hit_pencil_move(self, stroke, point):
        """
        Hit-test for pencil stroke selection (move tool).

        Uses simple radius-based proximity check.

        Args:
            stroke (dict): Pencil stroke.
            point (tuple): Cursor position.

        Returns:
            bool: True if stroke is near point.
        """

        radius = 0.01

        for p in stroke["points"]:

            dx = p[0] - point[0]
            dy = p[1] - point[1]

            if (dx * dx + dy * dy) <= (radius * radius):
                return True

        return False

    def clear(self):
        """
        Remove all notes (strokes and comments) from the current frame.

        This does NOT affect other frames.

        Returns:
            None
        """
        if self.current_frame is None:
            return

        frame_strokes = self.strokes.get(self.current_frame)
        if frame_strokes:
            # Treat Clear Notes on Frame like an erase so strokes can be
            # undone/redone. Comments are managed as review records and are
            # intentionally outside the drawing undo stack.
            self._record_action(
                {
                    "type": "erase",
                    "frame": self.current_frame,
                    "strokes": copy.deepcopy(frame_strokes),
                }
            )
        self.strokes.pop(self.current_frame, None)
        self.comments.pop(self.current_frame, None)

    def clear_all(self):
        """
        Remove all notes (strokes and comments) from all frames.

        This resets the entire sketch system.

        Returns:
            None
        """

        self.strokes.clear()
        self.comments.clear()
        # A source change calls clear_all(); history from the previous source
        # must never be able to restore notes into the newly opened source.
        self.undo_history.clear()
        self.redo_history.clear()

    def draw_overlays(self, painter, rect):
        """
        Render all overlay groups on the canvas.

        Overlays are drawn based on predefined screen positions:
            - top_left, top_right, top_center
            - bottom_left, bottom_right, bottom_center
            - center

        Args:
            painter (QtGui.QPainter): Active Qt painter.
            rect (QtCore.QRect): Viewport or canvas bounds.

        Returns:
            None
        """

        # Iterate all overlay positions
        for position in self.overlays:
            self.draw_overlay_position(painter, rect, position)

    def set_overlays(self, watermarks):
        """
        Set multiple overlay configurations at once.

        This method is typically used to load watermark presets.

        Args:
            watermarks (dict):
                Dictionary structured as:
                {
                    position: [
                        {
                            "checked": bool,
                            "code": str,
                            ...
                        }
                    ]
                }

        Returns:
            None
        """
        for position, values in watermarks.items():
            for context in values:
                self.set_overlay(context["checked"], context["code"], position, context)

    def set_overlay(self, checked, key, position, context):
        """
        Add or update a single overlay entry.

        Overlays are grouped by screen position.

        Args:
            checked (bool): Enable/disable overlay.
            key (str): Unique overlay identifier.
            position (str): Screen position group.
            context (dict): Overlay configuration data.

        Returns:
            None
        """

        # Ensure position group exists
        if position not in self.overlays:
            self.overlays[position] = dict()

        # Ensure overlay key exists
        if key not in self.overlays[position]:
            self.overlays[position][key] = dict()

        # Store overlay configuration
        self.overlays[position][key] = context
        self.overlays[position][key]["checked"] = checked

    def draw_overlay_position(self, painter, rect, position):
        """
        Render all overlays for a specific screen position.

        Supports:
            - Image overlays
            - Text overlays
            - Alignment (left, center, right)
            - Vertical stacking direction

        Args:
            painter (QtGui.QPainter): Active painter.
            rect (QtCore.QRect): Canvas bounds.
            position (str): Overlay anchor position.

        Returns:
            None
        """

        overlays = self.overlays.get(position, dict())
        if not overlays:
            return

        # Font metrics for spacing calculations
        metrics = QtGui.QFontMetrics(painter.font())
        margin, spacing = 20, 20

        # Resolve overlay anchor position (position calculation)
        if position == "top_left":
            x = rect.left() + margin
            y = rect.top() + margin  # 40
            align = "left"
        elif position == "top_center":
            x = rect.center().x()
            y = rect.top() + margin  # 40
            align = "center"
        elif position == "top_right":
            x = rect.right() - margin
            y = rect.top() + margin  # 40
            align = "right"
        elif position == "bottom_left":
            x = rect.left() + margin
            y = rect.bottom() - margin  # 40
            align = "left"
        elif position == "bottom_center":
            x = rect.center().x()
            y = rect.bottom() - metrics.descent() - 10
            align = "center"
        elif position == "bottom_right":
            x = rect.right() - margin
            y = rect.bottom() - margin  # 40
            align = "right"
        elif position == "center":
            x = rect.center().x()
            y = rect.center().y()
            align = "center"
        else:
            return

        # Bottom positions stack upward
        reverse_vertical = position in ["bottom_left", "bottom_center", "bottom_right"]

        # Draw overlays
        for key, context in overlays.items():
            if not context.get("checked"):
                continue

            typed = context.get("type", "text")

            # Draw image overlay
            if typed == "image":
                pixmap = context["value"]
                scaled = pixmap.scaledToHeight(50, QtCore.Qt.SmoothTransformation)
                draw_x = x

                # Horizontal alignment
                if align == "center":
                    draw_x -= scaled.width() / 2
                elif align == "right":
                    draw_x -= scaled.width()

                # Vertical direction (TOP / BOTTOM DIRECTION)
                if reverse_vertical:
                    draw_y = y - scaled.height()
                else:
                    draw_y = y

                # Set overlay opacity
                opacity = context.get("opacity", 1.0)
                painter.setOpacity(opacity)

                # Draw image
                path = painter.drawPixmap(int(draw_x), int(draw_y), scaled)

                # Reset Opacity
                painter.setOpacity(1.0)

                # Vertical spacing offset
                offset = scaled.height() + 10

                if reverse_vertical:
                    y -= offset
                else:
                    y += offset

            # Draw text overlay
            else:
                # Dynamic overlay text
                if key == "frame":
                    text = f"Frame: {str(self.current_frame).zfill(constants.VL_FRAME_PADDING)}"

                elif key == "resolution":
                    text = f"{self.image_height} x {self.image_width}"
                else:
                    text = (
                        f"{context['label']}: {context['value']}"
                        if context.get("label")
                        else context["value"]
                    )

                # Create font
                font = Font(None, **context["font"])

                # Calculate text bounds
                path = QtGui.QPainterPath()
                path.addText(0, 0, font, text)

                bounds = path.boundingRect()
                text_width = bounds.width()

                draw_x = x

                # Horizontal alignment
                if align == "center":
                    draw_x -= text_width / 2
                elif align == "right":
                    draw_x -= text_width

                # Draw text
                self.draw_overlay_text(painter, draw_x, y, text, context["font"])

                # Vertical spacing
                offset = spacing + context["font"].get("spacing", 0)

                if reverse_vertical:
                    y -= offset
                else:
                    y += offset

    def draw_overlay_text(self, painter, x, y, text, font_data):
        """
        Render styled overlay text with stroke + fill support.

        Supports:
            - Fill color
            - Stroke outline
            - Opacity control
            - Font customization

        Args:
            painter (QtGui.QPainter): Active painter.
            x (float): X position.
            y (float): Y position.
            text (str): Text to render.
            font_data (dict): Font + style configuration.

        Returns:
            QtGui.QPainterPath: Rendered text path.
        """

        # Build font from configuration
        font = Font(None, **font_data)
        painter.setFont(font)

        # Text colors
        fill_color = QtGui.QColor(*font_data.get("fillColor", (255, 255, 255)))
        stroke_color = QtGui.QColor(*font_data.get("strokeColor", (0, 0, 0)))

        stroke_width = font_data.get("stroke", 2)

        # Build text path
        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)

        # Draw text stroke
        if stroke_width > 0:
            pen = StrokePen(stroke["color"], thickness=stroke_width)
            painter.setPen(pen)
            painter.strokePath(path, pen)

        # Set text opacity
        opacity = font_data.get("opacity", 1.0)
        painter.setOpacity(opacity)

        # Draw text fill
        painter.fillPath(path, fill_color)

        return path


if __name__ == "__main__":
    pass
