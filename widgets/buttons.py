# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt QButton wapper module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.menus import DisplayMenus
from widgets.pixmaps import NamePixmapIcon


class IconButton(QtWidgets.QPushButton):
    name = "icon"

    def __init__(self, parent, **kwargs):
        super(IconButton, self).__init__(parent)

        self.width = kwargs.get("width", 22)
        self.height = kwargs.get("height", 22)
        self.locked = False if kwargs.get("locked") == False else True

        if kwargs.get("tooltip"):
            self.setToolTip(kwargs["tooltip"])

        self.setFlat(True)

        icon = NamePixmapIcon(self.name)
        self.setIcon(icon)
        self.setIconSize(QtCore.QSize(self.width, self.height))

        if self.locked:
            self.setMinimumSize(QtCore.QSize(self.width, self.height))
            self.setMaximumSize(QtCore.QSize(self.width, self.height))


class OpenButton(IconButton):
    name = "open"


class BackwordButton(IconButton):
    name = "backward"


class PlayPauseButton(IconButton):
    name = "play"

    def switch(self, value):
        name = "pause" if value else self.name
        icon = NamePixmapIcon(name)
        self.setIcon(icon)
        self.setToolTip(name.capitalize())


class ForwardButton(IconButton):
    name = "forward"


class HelpButton(IconButton):
    name = "help"


class ToolButton(QtWidgets.QToolButton):

    name = "tool"

    def __init__(self, parent, **kwargs):
        super(ToolButton, self).__init__(parent)

        self.width = kwargs.get("width", 32)
        self.height = kwargs.get("height", 32)

        if kwargs.get("tooltip"):
            self.setToolTip(kwargs["tooltip"])

        self.setToolTip(kwargs.get("tooltip", "unknown"))

        icon = NamePixmapIcon(self.name)
        self.setIcon(icon)
        self.setIconSize(QtCore.QSize(self.width, self.height))

        self.setMinimumSize(QtCore.QSize(self.width, self.height))
        self.setMaximumSize(QtCore.QSize(self.width, self.height))


class LoopButton(ToolButton):
    name = "loop"

    def __init__(self, parent, **kwargs):
        super(LoopButton, self).__init__(parent, **kwargs)

        self.setCheckable(True)
        self.setChecked(False)


class DisplayMenuButton(ToolButton):
    name = "display"

    def __init__(self, parent, **kwargs):
        super(DisplayMenuButton, self).__init__(parent, **kwargs)

        self.menu = DisplayMenus(self)

        self.clicked.connect(self.contextMenu)

    def contextMenu(self):
        self.menu.exec(QtGui.QCursor.pos())


if __name__ == "__main__":
    pass
