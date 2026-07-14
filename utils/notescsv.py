"""Export a Sketch's notes (comments and drawings) to CSV.

The CSV is the hand-off artifact: a supervisor's notes leaving FrameDeck for a
spreadsheet, a tracker import, or an email. It is deliberately flat -- one row
per note -- so it opens cleanly anywhere.

Rows are ordered by frame ascending, and within a frame the comments come first
(they carry the words) followed by the drawings in the order they were made.

Coordinates are the normalized (0.0-1.0) image-space values the annotations are
stored in, so they stay meaningful regardless of the resolution the note was
made at. Blank means "not applicable": a freehand scribble has no text, a
frame-level comment has no pin.

This module is pure: no Qt, no filesystem assumptions beyond the path it is
handed, so the row-building is testable on its own.
"""

from __future__ import absolute_import

import csv

import constants

from utils import timecode

COLUMNS = [
    "frame",
    "timecode",
    "type",
    "content",
    "color",
    "x",
    "y",
    "done",
    "timestamp",
]

# Stroke kinds whose extent is described by a start/end pair.
_SHAPE_TYPES = ("rectangle", "ellipse", "arrow")


def _hex_color(color):
    """Return ``#rrggbb`` for an (r, g, b) tuple, or "" when there is none."""
    if not color:
        return ""
    try:
        red, green, blue = (int(channel) for channel in tuple(color)[:3])
    except (TypeError, ValueError):
        return ""
    return "#{0:02x}{1:02x}{2:02x}".format(red & 255, green & 255, blue & 255)


def _round(value):
    """Round a normalized coordinate for display, or "" when absent."""
    if value is None:
        return ""
    return round(float(value), 4)


def _stroke_anchor(stroke):
    """Return the (x, y) that best locates a stroke on the frame.

    Pencil strokes are polylines with no single origin, so their first point is
    used -- it is where the reviewer started drawing, which is the part they
    were pointing at.
    """
    kind = stroke.get("type")

    if kind == "pencil":
        points = stroke.get("points") or []
        return points[0] if points else (None, None)

    if kind in _SHAPE_TYPES:
        return stroke.get("start") or (None, None)

    if kind == "txt":
        return stroke.get("position") or (None, None)

    return (None, None)


def _stroke_content(stroke):
    """Return the human-readable payload of a stroke ("" for pure drawings)."""
    if stroke.get("type") == "txt":
        return stroke.get("txt", "")
    return ""


def build_rows(sketch, fps=0):
    """Return the CSV rows for every note held by *sketch*.

    Args:
        sketch (Sketch):
            The annotation store to export.

        fps (float):
            Frame rate used for the timecode column. When it is unusable the
            timecode degrades to a frame label rather than failing the export.

    Returns:
        list[dict]: One row per comment and per drawing, keyed by COLUMNS.
    """

    rows = list()

    for frame in sketch.annotated_frames():
        # Timecode counts from zero; FrameDeck's timeline starts at VL_START_FRAME.
        zero_based = max(0, int(frame) - constants.VL_START_FRAME)
        code = timecode.frame_to_timecode(zero_based, fps)

        for comment in sketch.get_comments(frame):
            rows.append(
                {
                    "frame": int(frame),
                    "timecode": code,
                    "type": "comment",
                    "content": comment.get("text", ""),
                    "color": "",
                    "x": _round(comment.get("x")),
                    "y": _round(comment.get("y")),
                    "done": "yes" if comment.get("done") else "no",
                    "timestamp": comment.get("timestamp", ""),
                }
            )

        for stroke in sketch.strokes.get(frame, list()):
            x, y = _stroke_anchor(stroke)
            rows.append(
                {
                    "frame": int(frame),
                    "timecode": code,
                    "type": stroke.get("type", ""),
                    "content": _stroke_content(stroke),
                    "color": _hex_color(stroke.get("color")),
                    "x": _round(x),
                    "y": _round(y),
                    "done": "",
                    "timestamp": "",
                }
            )

    return rows


def write_csv(filepath, sketch, fps=0):
    """Write *sketch*'s notes to *filepath* as CSV.

    Returns:
        int: The number of note rows written (excluding the header).
    """

    rows = build_rows(sketch, fps)

    # newline="" is required on Windows, else csv writes \r\r\n line endings.
    with open(filepath, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


if __name__ == "__main__":
    pass
