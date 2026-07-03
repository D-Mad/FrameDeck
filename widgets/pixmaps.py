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

from PySide6 import QtGui


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

        # Initialize QPixmap
        super(NamePixmap, self).__init__()

        # Resolve Resource File Path
        self.filepath = resources.getIconFilepath(name)

        # Fallback To Unknown Icon
        if not utils.hasPathExists(self.filepath):
            self.filepath = resources.getIconFilepath("unknown")

        # Load Pixmap
        self.load(self.filepath)


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
