"""Render a review report to PDF.

The artifact a supervisor actually hands over: the annotated frames, the notes
that go with them, and enough identification that the recipient knows which shot
and which version they are looking at.

Written with Qt's own QPdfWriter, so there is no new dependency -- Qt is already
required by the app, and it embeds its own fonts, so the text stays selectable
and searchable in the delivered file rather than being baked into the image.

The builder takes plain page dicts, not a player or a reader, so a report can be
laid out and verified without decoding anything.
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtGui

import constants

# Rendered at print resolution: a note pinned to a 4K plate has to stay legible
# when someone prints the page and marks it up by hand.
RESOLUTION_DPI = 150

# Page furniture, in device pixels at RESOLUTION_DPI.
MARGIN = 60
HEADER_HEIGHT = 70
FOOTER_HEIGHT = 40

ACCENT = QtGui.QColor(224, 174, 74)
INK = QtGui.QColor(24, 24, 24)
MUTED = QtGui.QColor(110, 110, 110)
RULE = QtGui.QColor(205, 205, 205)


def _font(size, bold=False):
    font = QtGui.QFont("Helvetica")
    font.setPointSizeF(size)
    font.setBold(bold)
    return font


def _page_rect(writer):
    """Return the printable area in device pixels."""
    return writer.pageLayout().paintRectPixels(writer.resolution())


def _draw_header(painter, rect, left_text, right_text):
    """Draw the running header and return the y below it."""
    painter.setFont(_font(13, bold=True))
    painter.setPen(INK)
    painter.drawText(
        QtCore.QRectF(rect.left(), rect.top(), rect.width() * 0.7, HEADER_HEIGHT),
        QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
        left_text,
    )

    painter.setFont(_font(10))
    painter.setPen(MUTED)
    painter.drawText(
        QtCore.QRectF(
            rect.left() + rect.width() * 0.7,
            rect.top(),
            rect.width() * 0.3,
            HEADER_HEIGHT,
        ),
        QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight,
        right_text,
    )

    baseline = rect.top() + HEADER_HEIGHT
    painter.setPen(QtGui.QPen(ACCENT, 2))
    painter.drawLine(rect.left(), baseline, rect.right(), baseline)

    return baseline + 24


def _draw_footer(painter, rect, text):
    painter.setFont(_font(8))
    painter.setPen(MUTED)
    painter.drawText(
        QtCore.QRectF(
            rect.left(),
            rect.bottom() - FOOTER_HEIGHT,
            rect.width(),
            FOOTER_HEIGHT,
        ),
        QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight,
        text,
    )


def _draw_cover(painter, rect, meta, pages):
    """Draw the summary page: what this is, and what is in it."""
    y = _draw_header(painter, rect, constants.VL_TOOL_NAME + " Review Notes", meta.get("date", ""))

    painter.setFont(_font(24, bold=True))
    painter.setPen(INK)
    painter.drawText(
        QtCore.QRectF(rect.left(), y, rect.width(), 50),
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
        meta.get("shot", "Untitled"),
    )
    y += 66

    rows = [
        ("Source", meta.get("source", "")),
        ("Frame rate", meta.get("fps", "")),
        ("Annotated frames", str(len(pages))),
        ("Comments", str(sum(len(page.get("comments") or []) for page in pages))),
    ]

    painter.setFont(_font(10))
    for label, value in rows:
        if not value:
            continue
        painter.setPen(MUTED)
        painter.drawText(
            QtCore.QRectF(rect.left(), y, 150, 26),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            label,
        )
        painter.setPen(INK)
        painter.drawText(
            QtCore.QRectF(rect.left() + 160, y, rect.width() - 160, 26),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            str(value),
        )
        y += 26

    y += 20
    painter.setPen(QtGui.QPen(RULE, 1))
    painter.drawLine(rect.left(), y, rect.right(), y)
    y += 20

    # Contents: every annotated frame, so the reader can find a note without
    # paging through the whole report.
    painter.setFont(_font(11, bold=True))
    painter.setPen(INK)
    painter.drawText(
        QtCore.QRectF(rect.left(), y, rect.width(), 26),
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
        "Contents",
    )
    y += 30

    painter.setFont(_font(9))
    for index, page in enumerate(pages, start=2):  # page 1 is this cover
        if y > rect.bottom() - FOOTER_HEIGHT - 20:
            break
        summary = _first_comment(page) or "{0} drawn note(s)".format(
            page.get("stroke_count", 0)
        )
        painter.setPen(MUTED)
        painter.drawText(
            QtCore.QRectF(rect.left(), y, 220, 22),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            "p{0}   Frame {1}   {2}".format(
                index,
                str(page["frame"]).zfill(constants.VL_FRAME_PADDING),
                page.get("timecode", ""),
            ),
        )
        painter.setPen(INK)
        painter.drawText(
            QtCore.QRectF(rect.left() + 240, y, rect.width() - 240, 22),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            summary,
        )
        y += 22


def _first_comment(page):
    comments = page.get("comments") or []
    return comments[0].get("text", "") if comments else ""


def _comment_text(comment):
    text = str(comment.get("text", ""))
    if comment.get("done"):
        text = "{0}   [resolved]".format(text)
    return text


def _comment_height(font, text, width):
    """Return enough vertical space to preserve a wrapped review comment."""
    flags = (
        int(QtCore.Qt.AlignmentFlag.AlignLeft)
        | int(QtCore.Qt.AlignmentFlag.AlignTop)
        | int(QtCore.Qt.TextFlag.TextWordWrap)
    )
    bounds = QtGui.QFontMetricsF(font).boundingRect(
        QtCore.QRectF(0, 0, max(1.0, width), 10000), flags, text
    )
    return max(26.0, bounds.height() + 8.0)


def _draw_frame_page(painter, rect, meta, page, number, total):
    """Draw one annotated frame with its notes underneath."""
    y = _draw_header(
        painter,
        rect,
        "{0}   Frame {1}".format(
            meta.get("shot", ""),
            str(page["frame"]).zfill(constants.VL_FRAME_PADDING),
        ),
        page.get("timecode", ""),
    )

    comments = page.get("comments") or []

    # The notes get the room they need; the frame takes what is left. Measure
    # wrapped text instead of assuming every note fits on one 24-pixel line.
    note_font = _font(9)
    comment_width = rect.width() - 32
    comment_heights = [
        _comment_height(note_font, _comment_text(comment), comment_width)
        for comment in comments
    ]
    available_height = rect.bottom() - FOOTER_HEIGHT - 20 - y
    desired_note_height = 30 + sum(comment_heights) if comments else 0
    note_height = min(
        max(0.0, available_height - 60.0),
        desired_note_height,
    )
    image_area = QtCore.QRectF(
        rect.left(),
        y,
        rect.width(),
        rect.bottom() - FOOTER_HEIGHT - 20 - note_height - y,
    )

    image = page.get("image")
    if image is not None and not image.isNull() and image_area.height() > 40:
        scaled = image.scaled(
            int(image_area.width()),
            int(image_area.height()),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        target = QtCore.QRectF(
            image_area.left() + (image_area.width() - scaled.width()) / 2.0,
            image_area.top(),
            scaled.width(),
            scaled.height(),
        )
        painter.drawImage(target, scaled)
        painter.setPen(QtGui.QPen(RULE, 1))
        painter.drawRect(target)

    if comments:
        y = rect.bottom() - FOOTER_HEIGHT - 20 - note_height
        painter.setFont(_font(10, bold=True))
        painter.setPen(INK)
        painter.drawText(
            QtCore.QRectF(rect.left(), y, rect.width(), 24),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            "Notes",
        )
        y += 26

        painter.setFont(note_font)
        pin = 0
        text_flags = (
            int(QtCore.Qt.AlignmentFlag.AlignLeft)
            | int(QtCore.Qt.AlignmentFlag.AlignTop)
            | int(QtCore.Qt.TextFlag.TextWordWrap)
        )
        for comment, row_height in zip(comments, comment_heights):
            if y + row_height > rect.bottom() - FOOTER_HEIGHT:
                break

            pinned = "x" in comment and "y" in comment
            if pinned:
                pin += 1

            # The marker number matches the pin drawn on the frame above, so a
            # note can be traced back to the exact spot it refers to.
            marker = "{0}.".format(pin) if pinned else "-"
            painter.setPen(ACCENT if pinned else MUTED)
            painter.drawText(
                QtCore.QRectF(rect.left(), y, 30, row_height),
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop,
                marker,
            )

            painter.setPen(INK)
            painter.drawText(
                QtCore.QRectF(rect.left() + 32, y, comment_width, row_height),
                text_flags,
                _comment_text(comment),
            )
            y += row_height

    _draw_footer(painter, rect, "Page {0} of {1}".format(number, total))


def build_report(filepath, pages, meta=None):
    """Write a review PDF.

    Args:
        filepath (str):
            Destination path.

        pages (list[dict]):
            One entry per annotated frame:
            ``{"frame": int, "timecode": str, "image": QImage,
               "comments": [comment dicts], "stroke_count": int}``

        meta (dict):
            ``{"shot": str, "source": str, "date": str, "fps": str}``

    Returns:
        int: The number of pages written (cover included).
    """

    meta = meta or dict()
    pages = list(pages or [])

    writer = QtGui.QPdfWriter(str(filepath))
    writer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QtGui.QPageLayout.Orientation.Landscape)
    writer.setResolution(RESOLUTION_DPI)
    writer.setTitle(
        "{0} review notes - {1}".format(
            constants.VL_TOOL_NAME, meta.get("shot", "Untitled")
        )
    )
    writer.setPageMargins(
        QtCore.QMarginsF(10, 10, 10, 10), QtGui.QPageLayout.Unit.Millimeter
    )

    painter = QtGui.QPainter()
    if not painter.begin(writer):
        raise OSError("Could not open the PDF for writing: {0}".format(filepath))

    total = len(pages) + 1

    try:
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = QtCore.QRectF(_page_rect(writer))

        _draw_cover(painter, rect, meta, pages)
        _draw_footer(painter, rect, "Page 1 of {0}".format(total))

        for index, page in enumerate(pages, start=2):
            writer.newPage()
            _draw_frame_page(painter, rect, meta, page, index, total)
    finally:
        painter.end()

    return total


if __name__ == "__main__":
    pass
