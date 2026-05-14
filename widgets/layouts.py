from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets


class VerticalLayout(QtWidgets.QVBoxLayout):
    def __init__(self, parent, *args, **kwargs):
        super(VerticalLayout, self).__init__(parent)

        self.space = kwargs.get("space", 10)
        self.margins = kwargs.get("margins", (10, 10, 10, 10))

        self.setSpacing(self.space)
        self.setContentsMargins(*self.margins)

    def getChildren(self):
        children = list()

        for index in range(self.count()):
            widget = self.itemAt(index).widget()
            if not widget:
                continue
            children.append(widget)

        return children

    def clear(self):
        for child in self.getChildren():
            child.deleteLater()


class HorizontalLayout(QtWidgets.QHBoxLayout):
    def __init__(self, parent, *args, **kwargs):
        super(HorizontalLayout, self).__init__(parent)

        self.space = kwargs.get("space", 10)
        self.margins = kwargs.get("margins", (10, 10, 10, 10))

        self.setSpacing(self.space)
        self.setContentsMargins(*self.margins)

    def getChildren(self):
        children = list()

        for index in range(self.count()):
            widget = self.itemAt(index).widget()
            if not widget:
                continue
            children.append(widget)

        return children

    def clear(self):
        for child in self.getChildren():
            child.deleteLater()


class HorizontalSplitter(QtWidgets.QSplitter):
    def __init__(self, parent, **kwargs):
        super(HorizontalSplitter, self).__init__(parent)

        self.setOrientation(QtCore.Qt.Horizontal)


class HorizontalSpacer(QtWidgets.QSpacerItem):
    def __init__(self):
        super(HorizontalSpacer, self).__init__(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )


class VerticalSpacer(QtWidgets.QSpacerItem):
    def __init__(self):
        super(VerticalSpacer, self).__init__(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )


if __name__ == "__main__":
    pass
