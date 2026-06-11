"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/styles.py

Description:
    This module provides reusable Qt styling utilities used throughout the Review Player application.

Responsibilities:
    - Apply global application themes
    - Configure reusable fonts
    - Centralize typography settings
    - Simplify Qt stylesheet management

Features:
    - Dark/light theme support
    - qdarktheme integration
    - Custom QFont wrapper
    - Typography customization
    - Font capitalization control
    - Font spacing support

Architecture:
    Theme Configuration
        ↓
    Qt Stylesheet
        ↓
    UI Widgets

    Font Configuration
        ↓
    QFont Wrapper
        ↓
    Widget Typography

Notes:
    This module is used by:
        - Viewer widgets
        - Timeline widgets
        - Menus
        - Buttons
        - Playlist widgets
        - Overlay systems
"""

from __future__ import absolute_import

import qdarktheme

import constants
import resources

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets


class SetStylesheet(object):
    """Qt stylesheet application helper.

    This helper applies application-wide themes
    using qdarktheme.

    Supported Themes:
        - dark
        - light

    Features:
        - Global stylesheet setup
        - Dynamic theme switching
        - qdarktheme integration

    Args:
        parent (QWidget):
            Target widget/application.

    Keyword Args:
        theme (str):
            Theme name.

    Example:
        >>> SetStylesheet(app, theme="dark")
    """

    def __init__(self, parent, **kwargs):
        """Initialize stylesheet helper.

        Args:
            parent (QWidget):
                Target widget/application.

            **kwargs:
                Additional options.

        Keyword Args:
            theme (str):
                Theme name.
        """

        # Initialize Base Object
        super(SetStylesheet, self).__init__()

        # Resolve Theme
        theme = kwargs.get("theme") or constants.GUI_THEMES[0]

        # Apply Stylesheet
        parent.setStyleSheet(qdarktheme.load_stylesheet(theme))


class Font(QtGui.QFont):
    """Custom QFont wrapper.

    This class provides a centralized typography wrapper for Review Player UI components.

    Features:
        - Font family control
        - Font sizing
        - Bold/italic support
        - Text capitalization
        - Letter spacing
        - Word spacing
        - Font stretching
        - Underline/overline support

    Args:
        sizes (int):
            Font size.

    Keyword Args:
        family (str):
            Font family.

        bold (bool):
            Enable bold font.

        italic (bool):
            Enable italic font.

        underline (bool):
            Enable underline.

        overline (bool):
            Enable overline.

        strikeOut (bool):
            Enable strikeout.

        spacing (float):
            Letter spacing.

        wordSpacing (float):
            Word spacing.

        stretch (int):
            Font stretch value.

        capitalization (str):
            Text capitalization mode.

        weight (bool):
            Enable font weight.

    Example:
        >>> font = Font(12, family="Arial", bold=True)
        >>> widget.setFont(font)
    """

    def __init__(self, sizes, **kwargs):
        """Initialize custom font.

        Args:
            sizes (int):
                Font size.

            **kwargs:
                Additional font options.
        """

        # Initialize QFont
        super(Font, self).__init__()

        # Capitalization Mapping
        self.capitalizations = {
            # Default Mixed Case (0)
            "mixedCase": QtGui.QFont.MixedCase,
            # ALL UPPERCASE (1)
            "allUppercase": QtGui.QFont.AllUppercase,
            # all lowercase (2)
            "allLowercase": QtGui.QFont.AllLowercase,
            # Small Caps (3)
            "smallCaps": QtGui.QFont.SmallCaps,
            # Capitalize Words (4)
            "capitalize": QtGui.QFont.Capitalize,
        }

        # Font Size
        self.setPointSize(sizes or kwargs.get("size", 10))
        self.setPixelSize(sizes or kwargs.get("size", 10))

        # Font Family
        self.setFamily(kwargs.get("family", "Arial"))

        # Font Style
        self.setBold(kwargs.get("bold", False))
        self.setItalic(kwargs.get("italic", False))

        # Decoration Styles
        self.setUnderline(kwargs.get("underline", False))
        self.setOverline(kwargs.get("overline", False))
        self.setStrikeOut(kwargs.get("strikeOut", False))

        # Word Spacing
        self.setWordSpacing(kwargs.get("wordSpacing", 0))

        # Letter Spacing
        self.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, kwargs.get("spacing", 0))

        # Stretch
        self.setStretch(kwargs.get("stretch", 0))

        # Capitalization
        capitalization = kwargs.get("capitalization", "mixedCase")
        self.setCapitalization(self.capitalizations[capitalization])

        # Font Weight
        if kwargs.get("weight"):
            self.setWeight(QtGui.QFont.Weight(75))


if __name__ == "__main__":
    pass
