"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/labels.py

Description:
    This module provides reusable QLabel-based widgets used throughout the Review Player UI.

Responsibilities:
    - Display copyright information
    - Display project thumbnails
    - Handle image previews
    - Provide reusable label widgets
    - Display aligned text labels.
    - Display tool status information.
    - Display annotation thickness values.
    - Provide consistent label styling.

Features:
    - Styled text labels
    - Thumbnail image display
    - URL image support
    - Local image support
    - Fixed-size preview labels
    - Smooth pixmap scaling
    - Left-aligned labels.
    - Right-aligned labels.
    - Fixed-width thickness labels.
    - Active tool name display labels.

Architecture:
    Data/Input
        ↓
    QLabel Wrapper
        ↓
    Pixmap/Text Rendering
        ↓
    Qt UI Display

Notes:
    This module is used by:
        - Playlist panels
        - Project viewers
        - Information panels
        - Footer/status areas

    - Designed for toolbar and panel interfaces.
    - Provides consistent alignment and styling.
    - Lightweight wrappers around QLabel.
"""

from __future__ import absolute_import

import constants

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.styles import Font
from widgets.pixmaps import PathPixmap


class CopyrightLabel(QtWidgets.QLabel):
    """Styled copyright label widget.

    This widget displays the application copyright information using centralized typography settings.

    Features:
        - Styled font rendering
        - Right-aligned display
        - Fixed-height label
        - Global constants integration

    Args:
        parent (QWidget):
            Parent widget.

    Example:
        >>> label = CopyrightLabel(self)
    """

    def __init__(self, parent, **kwargs):
        """Initialize copyright label.

        Args:
            parent (QWidget):
                Parent widget.

            **kwargs:
                Reserved for future extension.
        """

        # Initialize QLabel
        super(CopyrightLabel, self).__init__(parent)

        # Configure Font
        font = Font(constants.AVERAGE_FONT_SIZE, family=constants.FONT_FAMILY, bold=True)
        self.setFont(font)

        # Text Alignment
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)

        # Set Copyright Text
        self.setText(constants.COPYRIGHT_LABEL)

        # Configure Size Policy
        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        self.setSizePolicy(sizepolicy)


class ProjectIconLabel(QtWidgets.QLabel):
    """Project thumbnail preview label.

    This widget displays project or version preview thumbnails using local files or URLs.

    Features:
        - Thumbnail preview display
        - URL image loading
        - Local image loading
        - Smooth pixmap scaling
        - Fixed preview size

    Args:
        parent (QWidget):
            Parent widget.

    Example:
        >>> label = ProjectIconLabel(self)
        >>> label.setThumbnail("/tmp/image.png")
        >>> label.setThumbnail("https://server/image.jpg")
    """

    def __init__(self, parent, **kwargs):
        """Initialize project icon label.

        Args:
            parent (QWidget):
                Parent widget.

            **kwargs:
                Reserved for future extension.
        """

        # Initialize QLabel
        super(ProjectIconLabel, self).__init__(parent)

        # Thumbnail Size
        self.size = 128, 72

        # Configure Fixed Size
        self.setMinimumSize(QtCore.QSize(128, 72))
        self.setMaximumSize(QtCore.QSize(128, 72))

        # Configure Size Policy
        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
        )
        self.setSizePolicy(sizepolicy)

    def setThumbnail(self, filepath):
        """Set thumbnail preview image.

        Supports:
            - HTTP/HTTPS URLs
            - Local image paths

        The image is automatically scaled to fit
        the label size while preserving aspect ratio.

        Args:
            filepath (str):
                Local file path or URL.

        Example:
            >>> label.setThumbnail("/tmp/image.png")
            >>> label.setThumbnail("https://server/image.jpg")
        """

        # Load Pixmap
        pixmaps = PathPixmap(filepath)

        # Scale Pixmap
        if not pixmaps.isNull():
            pixmaps = pixmaps.scaled(
                *self.size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )

        # Apply Pixmap To Label
        self.setPixmap(pixmaps)

        # Disable Stretch Scaling
        self.setScaledContents(False)


class RightLabel(QtWidgets.QLabel):
    """
    Right-aligned text label.

    Provides a QLabel configured for displaying text aligned to the right side of the widget.
    """

    def __init__(self, parent, value, **kwargs):
        """
        Initialize right-aligned label.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            value (str):
                Initial label text.

            **kwargs:
                Additional optional arguments.
        """

        # Initialize QLabel
        super(RightLabel, self).__init__(parent)

        # Apply right alignment
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)

        # Set initial text
        self.setText(value)

    def setValue(self, value):
        """
        Update label text.

        Args:
            value (str):
                New label text.
        """

        self.setText(value)

    def setFonts(self, size, family, bold):
        font = Font(size, family=family, bold=bold)
        self.setFont(font)


class LeftLabel(RightLabel):
    """
    Left-aligned text label.

    Extends RightLabel and overrides alignment to display text on the left side of the widget.
    """

    def __init__(self, parent, value, **kwargs):
        """
        Initialize left-aligned label.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            value (str):
                Initial label text.

            **kwargs:
                Additional optional arguments.
        """

        # Initialize base label
        super(LeftLabel, self).__init__(parent, value, **kwargs)

        # Apply left alignment
        self.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)


class ThicknesLabel(RightLabel):
    """
    Thickness value label.

    Specialized label used for displaying brush or pen thickness values within the application UI.
    """

    def __init__(self, parent, value, **kwargs):
        """
        Initialize thickness label.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            value (str):
                Initial label text.

            **kwargs:
                Additional optional arguments.
        """

        # Initialize base label
        super(ThicknesLabel, self).__init__(parent, value, **kwargs)

        # Tooltip
        self.setToolTip("Strokes Thicknes")

        # Fixed minimum width for value display
        self.setMinimumSize(QtCore.QSize(63, 0))

    def setValue(self, value):
        """
        Update label text and tooltip.

        Args:
            value (str):
                New label text.
        """

        super().setValue(value)

        # Get current Tooltip
        tooltip = "Eraser Radius" if value == "Radius" else "Strokes Thicknes"

        # Set Tooltip
        self.setToolTip(tooltip)


class ToolNameLabel(QtWidgets.QLabel):
    """
    Active tool display label.

    Displays the currently selected tool name in the annotation toolbar.
    """

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize tool name label.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            *args:
                Optional initial label text.

            **kwargs:
                Additional optional arguments.
        """

        # Initialize QLabel
        super(ToolNameLabel, self).__init__(parent)

        # Tooltip
        self.setToolTip("Current Active Tool Name")

        # Center align text
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Set initial value
        if args:
            self.setText(args[0])

        # Fixed display width
        self.setMinimumSize(QtCore.QSize(70, 0))
        self.setMaximumSize(QtCore.QSize(70, 16777215))

        # Custom appearance
        self.setStyleSheet("background: transparent; border: none;color: rgb(85, 170, 255)")

        # Bold font
        font = self.font()
        font.setBold(True)
        self.setFont(font)

    def setValue(self, enabled, value=None):
        """
        Update displayed tool name.

        Args:
            enabled (bool):
                Whether the tool is active.

            value (str, optional):
                Tool name to display.
        """

        # Display active tool name
        if enabled and value:
            self.setText(value.capitalize())
        # Clear when disabled
        else:
            self.clear()


class ImageViewLabel(QtWidgets.QLabel):

    clicked = QtCore.Signal(PathPixmap)  # Define a custom signal for clicks

    def __init__(self, parent, filepath, **kwargs):
        super(ImageViewLabel, self).__init__(parent)

        self.filepath = filepath
        self.pixmap = None

        self.width = kwargs.get("width") or 200
        self.height = kwargs.get("height") or 112

        self.setThumbnail()
        self.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.setScaledContents(False)

    def setThumbnail(self, filepath=None):
        filepath = filepath or self.filepath

        if not filepath:
            return

        self.pixmap = PathPixmap(filepath)

        if self.pixmap.isNull():
            return

        self.resized_pixmap = self.pixmap.scaled(
            self.width, self.height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )

        self.setPixmap(self.resized_pixmap)
        self.setScaledContents(False)

    def mousePressEvent(self, event):
        # Emit the custom clicked signal when the label is clicked
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.pixmap)
        super().mousePressEvent(event)


if __name__ == "__main__":
    pass
