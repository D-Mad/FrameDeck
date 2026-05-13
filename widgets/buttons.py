from PySide6 import QtCore
from PySide6 import QtWidgets


from widgets.pixmaps import NamePixmapIcon


class IconButton(QtWidgets.QPushButton):
    name = "icon"

    def __init__(self, parent, **kwargs):
        super(IconButton, self).__init__(parent)

        self.width = kwargs.get("width", 22)
        self.height = kwargs.get("height", 22)
        self.locked = False if kwargs.get("locked") == False else True

        self.setToolTip(kwargs.get("toolTip", "unknown"))
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
        icon = "pause" if value else self.name
        icon = NamePixmapIcon(icon)
        self.setIcon(icon)


class ForwardButton(IconButton):
    name = "forward"


class HelpButton(IconButton):
    name = "help"


class LoopButton(QtWidgets.QToolButton):
    name = "loop"

    def __init__(self, parent, **kwargs):
        super(LoopButton, self).__init__(parent)

        self.width = kwargs.get("width", 42)
        self.height = kwargs.get("height", 32)

        self.setToolTip("Loop the timeline")

        icon = NamePixmapIcon(self.name)
        self.setIcon(icon)
        self.setIconSize(QtCore.QSize(self.width, self.height))

        self.setMinimumSize(QtCore.QSize(self.width, self.height))
        self.setMaximumSize(QtCore.QSize(self.width, self.height))

        self.setCheckable(True)
        self.setChecked(False)


class TextButton(QtWidgets.QToolButton):

    def __init__(self, parent, *args, **kwargs):
        super(TextButton, self).__init__(parent)

        self.setText(args[0])

        if kwargs.get("toolTip"):
            self.setToolTip(kwargs["toolTip"])
