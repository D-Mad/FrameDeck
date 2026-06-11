"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.
Author: Subin. Gopi (subing85@gmail.com).
Description: Review Player Qt QLabel wrapper module.
WARNING! All changes made in this file will be lost when recompiling source file!

This module provides reusable QLabel-based widgets used throughout the Review Player UI.

Responsibilities:
    - Display copyright information
    - Display project thumbnails
    - Handle image previews
    - Provide reusable label widgets

Features:
    - Styled text labels
    - Thumbnail image display
    - URL image support
    - Local image support
    - Fixed-size preview labels
    - Smooth pixmap scaling

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
"""

from __future__ import absolute_import

import utils
import constants

from PySide6 import QtGui
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
    def __init__(self, parent, value, **kwargs):
        super(RightLabel, self).__init__(parent)

        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)

        self.setText(value)

    def setValue(self, value):
        self.setText(value)


class LeftLabel(RightLabel):
    def __init__(self, parent, value, **kwargs):
        super(LeftLabel, self).__init__(parent, value, **kwargs)

        self.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)


class ThicknesLabel(RightLabel):
    def __init__(self, parent, value, **kwargs):
        super(ThicknesLabel, self).__init__(parent, value, **kwargs)

        self.setMinimumSize(QtCore.QSize(63, 0))
        # self.setMaximumSize(QtCore.QSize(128, 72))


class ToolNameLabel(QtWidgets.QLabel):
    def __init__(self, parent, *args, **kwargs):
        super(ToolNameLabel, self).__init__(parent)

        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        if args:
            self.setText(args[0])

        self.setMinimumSize(QtCore.QSize(70, 0))
        self.setMaximumSize(QtCore.QSize(70, 16777215))

        self.setStyleSheet("background: transparent; border: none;color: rgb(85, 170, 255)")

        font = self.font()
        font.setBold(True)
        self.setFont(font)

    def setValue(self, enabled, value=None):
        if enabled and value:
            self.setText(value.capitalize())
        else:
            self.clear()


if __name__ == "__main__":
    pass
