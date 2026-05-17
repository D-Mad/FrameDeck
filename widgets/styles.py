# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt Styles and QFont wapper module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

import constants
import qdarktheme

import resources

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets


class SetStylesheet(object):
    def __init__(self, parent, **kwargs):
        super(SetStylesheet, self).__init__()
        theme = kwargs.get("theme") or constants.GUI_THEMES[0]

        parent.setStyleSheet(qdarktheme.load_stylesheet(theme))


class Font(QtGui.QFont):
    def __init__(self, sizes, **kwargs):
        super(Font, self).__init__()

        self.capitalizations = {
            "mixedCase": QtGui.QFont.MixedCase,  # 0 This is the normal text rendering option where no capitalization change is applied.
            "allUppercase": QtGui.QFont.AllUppercase,  # 1 his alters the text to be rendered in all uppercase type.
            "allLowercase": QtGui.QFont.AllLowercase,  # 2 This alters the text to be rendered in all lowercase type.
            "smallCaps": QtGui.QFont.SmallCaps,  # 3 This alters the text to be rendered in small-caps type.
            "capitalize": QtGui.QFont.Capitalize,  # 4 This alters the text to be rendered with the first character of each word as an uppercase character.
        }

        self.setPointSizeF(sizes or kwargs.get("size", 10))
        self.setFamily(kwargs.get("family", "Arial"))
        self.setBold(kwargs.get("bold", False))
        self.setItalic(kwargs.get("italic", False))

        self.setUnderline(kwargs.get("underline", False))
        self.setOverline(kwargs.get("overline", False))
        self.setStrikeOut(kwargs.get("strikeOut", False))
        self.setWordSpacing(kwargs.get("wordSpacing", 0))
        self.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, kwargs.get("spacing", 0))

        self.setStretch(kwargs.get("stretch", 0))

        capitalization = kwargs.get("capitalization", "mixedCase")
        self.setCapitalization(self.capitalizations[capitalization])

        if kwargs.get("weight"):
            self.setWeight(QtGui.QFont.Weight(75))


if __name__ == "__main__":
    pass
