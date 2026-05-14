import constants

from PySide6 import QtCore
from PySide6 import QtWidgets


class ContextCombobox(QtWidgets.QComboBox):
    def __init__(self, parent, **kwargs):
        super(ContextCombobox, self).__init__(parent)

        self.key = kwargs.get("key", "code")
        self.contextList = kwargs.get("contextList", list())

        if kwargs.get("tooltip"):
            self.setToolTip(kwargs["tooltip"])

        self.setItems(contextList=None)

        self.currentIndexChanged.connect(self.indexChange)

    def setItems(self, contextList=None):
        self.contextList = contextList or self.contextList
        if self.contextList:
            self.context = self.contextList[0]
            self.values = [x[self.key] for x in self.contextList]
        else:
            self.context = dict()
            self.values = list()

        self.clear()

        self.addItems(self.values)

    def getValue(self):
        return self.context

    def findByKey(self, value, key):
        result = next(filter(lambda x: x[key] == value, self.contextList), None)
        return result

    def setValue(self, value, **kwargs):
        value = 0 if value is None else value

        if isinstance(value, int):
            index = value
        elif isinstance(value, dict):
            if value in self.contextList:
                index = self.contextList.index(value)
            else:
                index = 0
        else:
            index = self.values.index(value) if value in self.values else 0

        self.setCurrentIndex(index)
        self.context = self.contextList[index]

    def indexChange(self, index):
        if not self.contextList:
            return
        self.context = self.contextList[index]


class FbsCombobox(ContextCombobox):

    fps_changed = QtCore.Signal(dict)

    def __init__(self, parent, **kwargs):

        kwargs["key"] = "code"
        kwargs["contextList"] = constants.FPS_VALUES

        super(FbsCombobox, self).__init__(parent, **kwargs)

        self.setToolTip("Frame Per Second")

        self.setValue(constants.DEFULT_FPS)

    def indexChange(self, index):
        super().indexChange(index)

        self.fps_changed.emit(self.context)


class AovsCombobox(QtWidgets.QComboBox):
    def __init__(self, parent, **kwargs):
        super(AovsCombobox, self).__init__(parent)

        self.setToolTip("Source Media Aovs")

        self.setMinimumSize(QtCore.QSize(150, 0))
        # sizepolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        # self.setSizePolicy(sizepolicy)

    def setAovs(self, aovs):
        aovs = aovs or list()

        self.clear()
        self.addItems(aovs)
        self.setEnabled(True if aovs else False)


if __name__ == "__main__":
    pass
