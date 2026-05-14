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
    def __init__(self, size, **kwargs):
        super(Font, self).__init__()

        if kwargs.get("spacing"):
            spacing = kwargs.get("spacing")
        else:
            spacing = constants.FONT_SPACING.get(size, 0)

        self.setPointSizeF(size)
        self.setBold(kwargs.get("bold", False))
        self.setItalic(kwargs.get("italic", False))
        self.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, spacing)

        self.setUnderline(kwargs.get("underline", False))
        self.setOverline(kwargs.get("overline", False))
        self.setStrikeOut(kwargs.get("strikeOut", False))

        self.setWordSpacing(kwargs.get("wordSpacing", 0))
        self.setStretch(kwargs.get("stretch", 0))

        self.setCapitalization(kwargs.get("capitalization", QtGui.QFont.MixedCase))

        if kwargs.get("weight"):
            self.setWeight(QtGui.QFont.Weight(75))

        if kwargs.get("family"):
            self.setFamily(kwargs.get("family"))


if __name__ == "__main__":
    pass
