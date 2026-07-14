"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/pixmaps.py

Description:
    This module provides reusable Qt pixmap and icon wrapper classes used throughout the Review Player UI.

Responsibilities:
    - Load pixmaps from resources
    - Load pixmaps from URLs
    - Create reusable Qt icons
    - Provide fallback placeholder icons
    - Simplify icon/pixmap creation

Features:
    - Resource icon loading
    - URL image loading
    - Local image loading
    - Automatic fallback icons
    - QPixmap wrappers
    - QIcon wrappers

Architecture:
    Image Source
        ↓
    Pixmap Wrapper
        ↓
    Icon Generation
        ↓
    Qt Widgets/UI

Supported Sources:
    - Resource icons
    - Local file paths
    - HTTP/HTTPS URLs

Notes:
    This module is used by:
        - Playlist widgets
        - Buttons
        - Menus
        - Tree widgets
        - Viewer overlays
"""

from __future__ import absolute_import

import utils
import resources

from PySide6 import QtCore
from PySide6 import QtGui


def _draw_named_icon(name, size=64):
    """Draw FrameDeck's original line icon set without external image assets."""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    painter.scale(size / 64.0, size / 64.0)

    foreground = QtGui.QColor("#d6d8da")
    accent = QtGui.QColor("#a3abb2")
    warm = QtGui.QColor("#d3a347")
    pen = QtGui.QPen(foreground, 4.0, QtCore.Qt.PenStyle.SolidLine)
    pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

    def line(x1, y1, x2, y2):
        painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2))

    def path(points, closed=False):
        shape = QtGui.QPainterPath(QtCore.QPointF(*points[0]))
        for point in points[1:]:
            shape.lineTo(QtCore.QPointF(*point))
        if closed:
            shape.closeSubpath()
        painter.drawPath(shape)

    if name in {"framedeck", "motion-craft"}:
        painter.setPen(QtGui.QPen(accent, 4.5))
        painter.setBrush(QtGui.QColor("#2c3035"))
        painter.drawRoundedRect(QtCore.QRectF(8, 10, 48, 42), 8, 8)
        painter.setBrush(accent)
        path([(23, 20), (45, 31), (23, 42)], True)
        painter.setPen(QtGui.QPen(warm, 4))
        line(14, 55, 50, 55)
    elif name == "open":
        path([(8, 22), (25, 22), (30, 17), (55, 17), (55, 50), (8, 50)], True)
        painter.setPen(QtGui.QPen(accent, 4))
        line(32, 27, 32, 43); line(24, 35, 40, 35)
    elif name in {"backward", "forward"}:
        direction = -1 if name == "backward" else 1
        x = lambda value: 32 + direction * (value - 32)
        line(x(14), 15, x(14), 49)
        path([(x(48), 16), (x(24), 32), (x(48), 48)], True)
    elif name == "play":
        painter.setBrush(accent)
        painter.setPen(QtGui.QPen(accent, 3))
        path([(21, 13), (50, 32), (21, 51)], True)
    elif name == "pause":
        painter.setBrush(accent); painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QtCore.QRectF(18, 13, 10, 38), 3, 3)
        painter.drawRoundedRect(QtCore.QRectF(36, 13, 10, 38), 3, 3)
    elif name == "pencil":
        painter.setPen(QtGui.QPen(accent, 7, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap))
        line(17, 47, 47, 17)
        painter.setPen(QtGui.QPen(foreground, 3)); path([(13, 51), (17, 40), (24, 47)], True)
    elif name == "arrow":
        line(13, 49, 49, 13); line(32, 13, 49, 13); line(49, 13, 49, 30)
    elif name == "ellipse":
        painter.setPen(QtGui.QPen(accent, 4)); painter.drawEllipse(QtCore.QRectF(10, 17, 44, 30))
    elif name == "rectangle":
        painter.setPen(QtGui.QPen(accent, 4)); painter.drawRoundedRect(QtCore.QRectF(11, 15, 42, 34), 4, 4)
    elif name == "eraser":
        painter.setBrush(QtGui.QColor("#3a3f45")); path([(14, 42), (35, 15), (53, 30), (34, 51)], True)
        painter.setPen(QtGui.QPen(accent, 4)); line(26, 31, 42, 44)
    elif name == "txt":
        painter.setPen(QtGui.QPen(accent, 5)); line(13, 15, 51, 15); line(32, 15, 32, 51); line(22, 51, 42, 51)
    elif name == "navigate":
        painter.setPen(QtGui.QPen(accent, 4))
        path([(13, 9), (50, 31), (34, 35), (27, 52)], True)
        painter.setBrush(warm); painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QRectF(38, 39, 10, 10))
    elif name == "move":
        painter.setPen(QtGui.QPen(accent, 4)); line(32, 8, 32, 56); line(8, 32, 56, 32)
        path([(25, 15), (32, 8), (39, 15)]); path([(25, 49), (32, 56), (39, 49)])
        path([(15, 25), (8, 32), (15, 39)]); path([(49, 25), (56, 32), (49, 39)])
    elif name == "undo":
        painter.setPen(QtGui.QPen(accent, 4)); path([(12, 27), (22, 17), (22, 25)])
        painter.drawArc(QtCore.QRectF(18, 18, 35, 31), 25 * 16, 275 * 16)
    elif name == "redo":
        painter.save(); painter.translate(64, 0); painter.scale(-1, 1)
        painter.setPen(QtGui.QPen(accent, 4)); path([(12, 27), (22, 17), (22, 25)])
        painter.drawArc(QtCore.QRectF(18, 18, 35, 31), 25 * 16, 275 * 16)
        painter.restore()
    elif name in {"clear", "remove"}:
        painter.setPen(QtGui.QPen(warm, 4)); painter.drawEllipse(QtCore.QRectF(10, 10, 44, 44))
        line(21, 21, 43, 43); line(43, 21, 21, 43)
    elif name in {"render", "snapshot"}:
        painter.drawRoundedRect(QtCore.QRectF(9, 14, 46, 36), 5, 5)
        painter.setBrush(accent); painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QRectF(25, 22, 14, 14))
        painter.setPen(QtGui.QPen(warm, 4)); line(32, 38, 32, 56); path([(25, 49), (32, 56), (39, 49)])
    elif name == "export":
        painter.setPen(QtGui.QPen(accent, 4))
        painter.drawRoundedRect(QtCore.QRectF(8, 12, 48, 38), 5, 5)
        painter.setBrush(accent); painter.setPen(QtCore.Qt.PenStyle.NoPen)
        path([(22, 21), (39, 31), (22, 41)], True)
        painter.setPen(QtGui.QPen(warm, 4))
        line(35, 53, 54, 53); line(54, 53, 54, 38)
        path([(46, 43), (54, 35), (62, 43)])
    elif name == "attach":
        painter.setPen(QtGui.QPen(accent, 4)); painter.drawArc(QtCore.QRectF(15, 8, 34, 48), -35 * 16, 245 * 16)
        painter.drawArc(QtCore.QRectF(23, 14, 18, 34), -45 * 16, 235 * 16)
    elif name == "recaps":
        painter.setPen(QtGui.QPen(accent, 4)); path([(10, 13), (54, 13), (54, 44), (31, 44), (20, 54), (20, 44), (10, 44)], True)
        line(19, 24, 45, 24); line(19, 33, 38, 33)
    elif name == "theme":
        painter.setBrush(accent); painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QRectF(11, 11, 42, 42))
        painter.setBrush(QtGui.QColor("#191b1e")); painter.drawEllipse(QtCore.QRectF(26, 5, 38, 38))
    elif name == "ocio":
        painter.setPen(QtGui.QPen(accent, 4));
        painter.drawEllipse(QtCore.QRectF(8, 19, 26, 26)); painter.drawEllipse(QtCore.QRectF(30, 19, 26, 26)); painter.drawEllipse(QtCore.QRectF(19, 7, 26, 26))
    elif name == "gamma":
        painter.setPen(QtGui.QPen(accent, 4, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap))
        path([(10, 20), (20, 20), (30, 45), (43, 18), (54, 18)])
        painter.setPen(QtGui.QPen(warm, 3)); line(42, 18, 42, 49)
    elif name == "exposure":
        painter.setPen(QtGui.QPen(accent, 4))
        painter.drawEllipse(QtCore.QRectF(21, 21, 22, 22))
        for x1, y1, x2, y2 in ((32, 7, 32, 15), (32, 49, 32, 57), (7, 32, 15, 32), (49, 32, 57, 32)):
            line(x1, y1, x2, y2)
        painter.setPen(QtGui.QPen(warm, 3)); line(27, 32, 37, 32); line(32, 27, 32, 37)
    elif name == "help":
        painter.setPen(QtGui.QPen(accent, 4)); painter.drawEllipse(QtCore.QRectF(10, 10, 44, 44))
        painter.drawText(QtCore.QRectF(10, 8, 44, 47), QtCore.Qt.AlignmentFlag.AlignCenter, "?")
    elif name == "loop":
        painter.setPen(QtGui.QPen(accent, 4)); path([(12, 24), (20, 16), (46, 16), (53, 23)])
        path([(46, 11), (53, 23), (41, 23)]); path([(52, 40), (44, 48), (18, 48), (11, 41)])
        path([(18, 53), (11, 41), (23, 41)])
    elif name in {"display", "_display"}:
        painter.setPen(QtGui.QPen(accent, 4)); path([(7, 32), (17, 20), (32, 15), (47, 20), (57, 32), (47, 44), (32, 49), (17, 44)], True)
        painter.drawEllipse(QtCore.QRectF(25, 25, 14, 14))
    elif name == "volume":
        painter.setPen(QtGui.QPen(accent, 4)); path([(10, 26), (20, 26), (32, 16), (32, 48), (20, 38), (10, 38)], True)
        painter.drawArc(QtCore.QRectF(30, 19, 23, 26), -60 * 16, 120 * 16)
    else:
        painter.setPen(QtGui.QPen(accent, 4)); painter.drawRoundedRect(QtCore.QRectF(9, 12, 46, 40), 5, 5)
        line(17, 21, 47, 21); line(17, 43, 47, 43)
        painter.setBrush(warm); painter.setPen(QtCore.Qt.PenStyle.NoPen); painter.drawEllipse(QtCore.QRectF(27, 27, 10, 10))

    painter.end()
    return pixmap


class NamePixmap(QtGui.QPixmap):
    """Pixmap wrapper using resource icon names.

    This class automatically resolves icon names from
    the Review Player resources/icons directory.

    Features:
        - Resource icon lookup
        - Automatic fallback icons
        - QPixmap loading

    Args:
        name (str):
            Icon name without extension.

    Example:
        >>> pixmap = NamePixmap("play")
        >>> pixmap = NamePixmap("unknown")
    """

    def __init__(self, name, **kwargs):
        """Initialize named pixmap.

        Args:
            name (str):
                Resource icon name.

            **kwargs:
                Reserved for future extension.
        """

        size = int(kwargs.get("size", 64))
        generated = _draw_named_icon(name, size=size)
        super(NamePixmap, self).__init__(generated)
        self.filepath = ""


class NamePixmapIcon(QtGui.QIcon):
    """QIcon wrapper using resource icon names.

    This class creates a Qt icon from a named
    Review Player resource icon.

    Features:
        - Resource icon lookup
        - Automatic pixmap conversion
        - QIcon creation

    Args:
        name (str):
            Resource icon name.

    Example:
        >>> icon = NamePixmapIcon("play")
    """

    def __init__(self, name, **kwargs):
        """Initialize named icon.

        Args:
            name (str):
                Resource icon name.

            **kwargs:
                Reserved for future extension.
        """

        # Initialize QIcon
        super(NamePixmapIcon, self).__init__()

        # Build Pixmap
        pixmap = NamePixmap(name)

        # Add Pixmap To Icon
        self.addPixmap(pixmap, QtGui.QIcon.Normal, QtGui.QIcon.Off)


class PixmapIcon(QtGui.QIcon):
    """QIcon wrapper from existing pixmap.

    This helper converts an existing QPixmap into
    a reusable Qt icon.

    Args:
        pixmap (QPixmap):
            Source pixmap.

    Example:
        >>> icon = PixmapIcon(pixmap)
    """

    def __init__(self, pixmap, **kwargs):
        """Initialize pixmap icon.

        Args:
            pixmap (QPixmap):
                Source pixmap.

            **kwargs:
                Reserved for future extension.
        """

        # Initialize QIcon
        super(PixmapIcon, self).__init__()

        # Add Pixmap To Icon
        self.addPixmap(pixmap, QtGui.QIcon.Normal, QtGui.QIcon.Off)


class PathPixmap(QtGui.QPixmap):
    """Pixmap wrapper for local files and URLs.

    Supports:
        - Local image paths
        - HTTP/HTTPS image URLs

    Features:
        - Automatic URL detection
        - Remote image downloading
        - Local file loading

    Args:
        filepath (str):
            Local path or URL.

    Example:
        >>> pixmap = PathPixmap("/tmp/image.png")
        >>> pixmap = PathPixmap("https://server/image.jpg")
    """

    def __init__(self, filepath, **kwargs):
        """Initialize path pixmap.

        Args:
            filepath (str):
                Local image path or URL.

            **kwargs:
                Reserved for future extension.
        """

        # Initialize QPixmap
        super(PathPixmap, self).__init__()

        if utils.isUrl(filepath):  # Load Remote Image
            self.loadFromData(utils.getUrlContent(filepath))
        else:  # Load Local Image
            self.load(filepath)


if __name__ == "__main__":
    pass
